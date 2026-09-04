"""
Boolean-only views for Beacon v2 API
Simplified views that return only YES/NO responses for public discovery
"""
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny
from rest_framework.throttling import AnonRateThrottle
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import ParseError
from django.conf import settings
from django.views.decorators.cache import cache_page
from datetime import datetime
from .models import Variant, Dataset, Individual, Cohort, FilteringTerm
from .validators import validate_query_request, ValidationError
from .assembly import assembly_filter
from .release import get_release
from .request_body import flatten_beacon_request
from .capabilities import (
    is_assembly_served, is_dataset_scope_supported, served_assemblies,
    unserved_assembly_message, unsupported_dataset_scope_message,
)
from .query_vocabulary import UnknownSex, canonical_sex, variant_type_filter
from .query_semantics import (
    DEFAULT_MAX_VARIANT_SPAN, IncompleteRange, build_position_filter,
    POSITION_FILTER_KEYS, require_complete_range,
)
from .query_sanitizers import (
    UnsafeQueryValue, reject_operator_keys, scalar_query_value,
)
from .pagination import InvalidPagination, paginate, parse_pagination
from .filters import UnsupportedFilters, reject_filters
from .query_cost import (
    DEFAULT_QUERY_MAX_TIME_MS, QUERY_LOCUS, QUERY_UNBOUNDED,
    allows_per_dataset_attribution, classify_variant_query,
)
from pymongo.errors import ExecutionTimeout
from .privacy import (
    DEFAULT_AF_DECIMALS, DEFAULT_AF_MIN_PUBLISHED, publish_allele_frequency,
)
from .utils import (
    create_boolean_response, build_beacon_response,
    build_info_envelope, build_query_envelope, build_collection_envelope,
    build_error_envelope, extract_error_message,
)
import logging

logger = logging.getLogger('beacon_api')


def _error_response(status_code, message):
    """Spec-shaped Beacon v2 error response with a matching HTTP status."""
    return Response(build_error_envelope(status_code, message), status=status_code)


def _server_error(message='An error occurred processing your request'):
    """500 with the Beacon v2 error envelope."""
    return _error_response(status.HTTP_500_INTERNAL_SERVER_ERROR, message)


def _read_page_request(request):
    """Resolve pagination and reject filters for a plain list endpoint.

    Returns ``(page_params, error_response)``; exactly one is meaningful. The
    collection endpoints below never reach ``validate_query_request``, so this
    is where they pick up the same bounds and the same rejections as the query
    endpoints. ``page_params`` is the dict handed to the envelope builders as
    `validated_params`, so the echoed ``receivedRequestSummary.pagination``
    reports precisely the numbers applied to the queryset.
    """
    params = request.GET.dict()
    try:
        reject_filters(params)
    except UnsupportedFilters as e:
        return None, _error_response(status.HTTP_400_BAD_REQUEST, str(e))
    try:
        skip, limit = parse_pagination(params)
    except InvalidPagination as e:
        return None, _error_response(status.HTTP_400_BAD_REQUEST, str(e))
    return {'skip': skip, 'limit': limit}, None


class QueryRateThrottle(AnonRateThrottle):
    """Custom throttle for query endpoints"""
    rate = '50/hour'


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
@throttle_classes([QueryRateThrottle])
@cache_page(60 * 5)  # Cache for 5 minutes
def variant_query_boolean(request):
    """
    Returns YES/NO response with per-dataset allele responses (GA4GH Beacon v2 compliant)
    """
    # Bound before the try so the ExecutionTimeout handler can always read it.
    # Nothing between here and the classification touches MongoDB today, but a
    # timeout raised before it would otherwise turn into a NameError inside the
    # error path. None falls through to the conservative "too broad" branch.
    query_class = None
    max_time_ms = DEFAULT_QUERY_MAX_TIME_MS
    try:
        # Get query parameters
        if request.method == 'GET':
            query_params = request.GET.dict()
        else:
            # Beacon v2 nests parameters under query.requestParameters; the
            # query below reads top-level keys. Without this the nested body
            # produced an UNFILTERED query — an impossible locus answered
            # exists:true. See beacon_api/request_body.py.
            query_params = flatten_beacon_request(request.data)

        # Validate and sanitize input
        try:
            logger.info(f"Raw query params: {query_params}")
            validated_params = validate_query_request(query_params)
            logger.info(f"Validated params: {validated_params}")
        except ValidationError as e:
            # `str(e)` here is the raw DRF/Python repr of the error dict —
            # never return it to the caller. extract_error_message() pulls out
            # just the human-readable text.
            message = extract_error_message(
                getattr(e, 'detail', None), fallback='Invalid query parameters'
            )
            logger.warning(f"Validation error: {message}")
            return _error_response(status.HTTP_400_BAD_REQUEST, message)

        # Build MongoDB query
        mongo_query = {}

        if validated_params.get('referenceName'):
            # The Beacon v2 spec uses bare chromosome names ("1", "X"). Stored
            # data may use either bare or "chr"-prefixed names depending on the
            # ingest pipeline. Match both so callers don't have to know which
            # form the data uses.
            ref = validated_params['referenceName']
            bare = ref[3:] if ref.startswith('chr') else ref
            mongo_query['reference_name__in'] = [bare, f'chr{bare}']

        # Position filter — half-open interval overlap for both point queries
        # (only `start` provided, the standard Beacon v2 SNV lookup) and range
        # queries (`start` + `end`). See beacon_api/query_semantics.py for the
        # coordinate convention and why closed-interval (`lte`/`gte`) overlap
        # is wrong here. Without this filter, a `start`-only query falls
        # through with no position constraint, forcing a full-chromosome scan
        # over millions of variants — observed as 30s requests.
        position_start = validated_params.get('start', validated_params.get('position'))

        # `end` with no `start` yields an empty position filter, which would
        # silently widen the query to the whole chromosome. Refuse instead.
        try:
            require_complete_range(position_start, validated_params.get('end'))
        except IncompleteRange as exc:
            return _error_response(status.HTTP_400_BAD_REQUEST, str(exc))

        mongo_query.update(build_position_filter(
            position_start,
            validated_params.get('end'),
            max_variant_span=getattr(
                settings, 'BEACON_MAX_VARIANT_SPAN', DEFAULT_MAX_VARIANT_SPAN
            ),
        ))

        if validated_params.get('referenceBases'):
            mongo_query['reference_bases'] = validated_params['referenceBases']
        if validated_params.get('alternateBases'):
            mongo_query['alternate_bases'] = validated_params['alternateBases']

        if validated_params.get('assemblyId'):
            # GRCh37 and hg19 are KNOWN assemblies: they pass validation,
            # canonicalise correctly, and then match no stored data — so the
            # beacon answered "exists: false" for a build it does not hold.
            # A user reached that in two clicks from the assembly selector and
            # got an authoritative "not in the African panel", indistinguishable
            # from a true negative. Refuse instead. See capabilities.py.
            #
            # Coverage is derived from the catalogue, not hard-coded, so it
            # stays true on its own once a GRCh37 dataset is loaded.
            declared = Dataset.objects.distinct('assembly_id')
            # An EMPTY catalogue is a different condition — an unconfigured or
            # not-yet-loaded beacon, not a caller asking for the wrong build.
            # Refusing every assembly there would swap one false signal for
            # another, so only refuse when the beacon demonstrably holds
            # something and this build is not it.
            if declared:
                served = served_assemblies(declared)
                if not is_assembly_served(validated_params['assemblyId'], served):
                    return _error_response(
                        status.HTTP_501_NOT_IMPLEMENTED,
                        unserved_assembly_message(
                            validated_params['assemblyId'], served),
                    )

            # hg38 and GRCh38 name the same build, and which spelling is
            # stored depends on the ingest run. Match every spelling of the
            # requested build rather than the caller's literal string — an
            # equality match here answered "exists: false" for variants the
            # panel holds. See beacon_api/assembly.py.
            mongo_query.update(assembly_filter(validated_params['assemblyId']))

        # variantType and datasetIds were both declared, validated, and then
        # never applied — the beacon answered a broader question than it was
        # asked. Apply them. (validators has already canonicalised the type.)
        if validated_params.get('variantType'):
            mongo_query.update(variant_type_filter(validated_params['variantType']))

        requested_datasets = validated_params.get('datasetIds')
        if requested_datasets:
            mongo_query['dataset_ids__in'] = list(requested_datasets)

        # A positional query without a chromosome cannot use the
        # {reference_name, start} index and would scan the entire collection
        # (tens of millions of documents). Require referenceName whenever a
        # position is supplied — this matches the UI, which marks Chromosome
        # required.
        if any(k in mongo_query for k in POSITION_FILTER_KEYS) and 'reference_name__in' not in mongo_query:
            return _error_response(
                status.HTTP_400_BAD_REQUEST,
                'referenceName is required when querying by position',
            )

        # Granularity: default 'boolean'. 'aggregated' (or 'record') additionally
        # returns allele frequencies for matched variants.
        requested_granularity = validated_params.get('requestedGranularity', 'boolean')
        want_frequency = requested_granularity in ('aggregated', 'record')
        returned_granularity = 'boolean'

        # How expensive can this query be? See beacon_api/query_cost.py.
        # A parameterless request is the spec's legitimate "all entries" query
        # and must answer quickly, so it is classified rather than rejected.
        query_class = classify_variant_query(mongo_query, POSITION_FILTER_KEYS)
        max_time_ms = getattr(
            settings, 'BEACON_QUERY_MAX_TIME_MS', DEFAULT_QUERY_MAX_TIME_MS
        )

        # Query variants and collect dataset membership
        exists = False
        dataset_allele_responses = []
        catalogue_total = None

        if mongo_query:
            logger.info(f"MongoDB query: {mongo_query} (class={query_class})")
            # max_time_ms is the only bound that survives the worst case. A
            # `limit` does not: a query matching nothing still scans the whole
            # collection looking for documents to fill the page. Without this,
            # one unauthenticated request pins a gunicorn worker for 30s+.
            base_qs = Variant.objects.filter(**mongo_query).max_time_ms(max_time_ms)
            # Existence only needs one document — never materialize the full
            # match set, which can be millions of variants for a broad query.
            exists = base_qs.first() is not None

            if exists and allows_per_dataset_attribution(query_class):
                # Per-dataset attribution via a bounded check per dataset. Fetch
                # the matched doc once and reuse it for the allele frequency
                # rather than issuing a second query.
                #
                # Restricted to locus queries deliberately. `dataset_ids` is
                # unset on many stored variants, so a probe that matches
                # nothing walks the whole ~42M-document collection before it
                # can answer "no" — run once per dataset. That loop, not the
                # existence check, is what produced the 30.7s / HTTP 504 on an
                # unparameterized request. A locus query bounds the candidate
                # set to a handful of documents first, so the probes are cheap.
                for ds in Dataset.objects.all():
                    # .max_time_ms() is re-applied deliberately and is NOT
                    # redundant. In mongoengine 0.27.0, max_time_ms() sets the
                    # value on the *pymongo cursor* and caches it on the
                    # queryset; .filter() then clones with
                    # `_cursor_obj = None`, and QuerySet._cursor rebuilds the
                    # cursor re-applying _limit/_skip/_hint/_collation/
                    # _batch_size/_comment — but never _max_time_ms. So a
                    # filtered clone silently loses its time budget, which is
                    # exactly the query that needs it most here.
                    ds_variant = (
                        base_qs.filter(dataset_ids=ds.id)
                        .max_time_ms(max_time_ms)
                        .first()
                    )
                    dar = {
                        'datasetId': ds.id,
                        'datasetName': ds.name,
                        'exists': ds_variant is not None,
                    }
                    if want_frequency and ds_variant is not None:
                        # Never publish the raw stored float: an AF of exactly
                        # k/2N inverts to an exact carrier count, which is the
                        # beacon re-identification primitive. Round onto a grid
                        # coarser than 1/2N and suppress the small cells
                        # entirely. See beacon_api/privacy.py.
                        af = publish_allele_frequency(
                            ds_variant.allele_frequency,
                            decimals=getattr(settings, 'BEACON_AF_DECIMALS',
                                             DEFAULT_AF_DECIMALS),
                            min_frequency=getattr(settings, 'BEACON_AF_MIN_PUBLISHED',
                                                  DEFAULT_AF_MIN_PUBLISHED),
                        )
                        if af is not None:
                            dar['alleleFrequency'] = af
                            returned_granularity = 'aggregated'
                    dataset_allele_responses.append(dar)

            if query_class == QUERY_UNBOUNDED:
                # The "all entries" request. numTotalResults comes from the
                # precomputed Dataset.dataset_size — the same field /datasets
                # reads, and for the same reason: count() over the variants
                # collection is a 30s scan at production volume. Absent counts
                # fall back to the boolean-mode total below rather than
                # reporting a confident zero for data we did not look at.
                sizes = [
                    (ds.dataset_size or {}).get('variants')
                    for ds in Dataset.objects.all()
                ]
                sizes = [s for s in sizes if isinstance(s, int)]
                if sizes:
                    catalogue_total = sum(sizes)

        logger.info(f"Variant query: exists={exists}, params={validated_params.get('referenceName', 'unknown')}")

        result_sets = []
        if dataset_allele_responses:
            for dar in dataset_allele_responses:
                rs = {
                    'id': dar['datasetId'],
                    'name': dar['datasetName'],
                    'setType': 'dataset',
                    'exists': dar['exists'],
                    'resultsCount': 1 if dar['exists'] else 0,
                }
                # Spec-shaped allele frequency (GA4GH frequencyInPopulations)
                if dar.get('alleleFrequency') is not None:
                    rs['results'] = [{
                        'frequencyInPopulations': [{
                            'source': dar['datasetName'],
                            'sourceReference': dar['datasetId'],
                            'frequencies': [{
                                'population': dar['datasetName'],
                                'alleleFrequency': dar['alleleFrequency'],
                            }],
                        }],
                    }]
                result_sets.append(rs)

        # `resultSets` is the collection this endpoint actually returns, so it
        # is what skip/limit page over. Note what is deliberately NOT paged:
        # `exists` and `numTotalResults` are computed over the whole match and
        # stay whole-match answers — a client on page 2 must not be told the
        # variant does not exist, and numTotalResults is a total by definition.
        # With the default limit this is a no-op, so callers that omit
        # pagination see exactly what they saw before.
        if dataset_allele_responses:
            num_total = sum(1 for d in dataset_allele_responses if d.get('exists'))
        elif catalogue_total is not None and exists:
            # `and exists` matters: the catalogue total is a property of the
            # datasets, not of this query. Reporting it alongside exists=False
            # (e.g. an assemblyId that matches nothing) would be a self-
            # contradictory response.
            num_total = catalogue_total
        else:
            num_total = 1 if exists else 0
        result_sets = paginate(
            result_sets, validated_params['skip'], validated_params['limit']
        )

        return Response(build_query_envelope(
            exists=exists,
            num_total=num_total,
            result_sets=result_sets,
            validated_params=validated_params,
            requested_granularity=requested_granularity,
            returned_granularity=returned_granularity,
        ))

    except ExecutionTimeout:
        # The server-side budget fired, so MongoDB killed the operation and the
        # worker is free — the point of max_time_ms. But WHY it fired decides
        # whose problem it is, and the two cases need opposite answers.
        if query_class == QUERY_LOCUS:
            # Already as narrow as a beacon query gets: a chromosome plus a
            # position. If that cannot be served inside the budget the index it
            # relies on is missing or the server is overloaded — nothing the
            # caller can change. Telling them to "narrow the query" would be
            # false, and a 400 would blame a request that was correct.
            #
            # This is not hypothetical: shipping the budget before running
            # `manage.py create_indexes` on the 42M-document collection made
            # single-variant lookups fail across much of the genome, each after
            # exactly the budget, with a message advising the caller to supply
            # parameters they had already supplied.
            logger.error(
                'Locus query exceeded the %sms budget — the {reference_name, '
                'start, end} index is probably missing on this deployment; '
                'run manage.py create_indexes',
                max_time_ms,
            )
            return _error_response(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                'This beacon could not answer in time. The query is valid — '
                'the server is unable to serve it right now. Please retry, and '
                'report it if it persists.',
            )

        logger.warning('Variant query exceeded the server-side time budget; refused')
        return _error_response(
            status.HTTP_400_BAD_REQUEST,
            'Query too broad to answer within the beacon time budget. Supply '
            'referenceName together with start (and optionally end) to narrow '
            'it to a genomic locus.',
        )
    except ParseError as exc:
        # DRF raises this from `request.data` when the body is not valid JSON.
        # It is a 400-class exception, but it is raised inside this try, so
        # without this clause the generic handler below reports it as 500 —
        # telling a client author to look at the server when the fault is in
        # their request. The developer tutorial's own placeholder body landed
        # here. See beacon_api/test_malformed_body.py.
        message = str(getattr(exc, 'detail', exc)) or 'Malformed JSON body'
        logger.warning(f"Unparseable request body: {message}")
        return _error_response(
            status.HTTP_400_BAD_REQUEST,
            f"Could not parse the request body as JSON: {message}",
        )
    except Exception as e:
        logger.error(f"Query error: {e}", exc_info=True)
        return _server_error()


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
@throttle_classes([QueryRateThrottle])
@cache_page(60 * 5)
def individual_query_boolean(request):
    """
    Boolean query for individuals
    Returns only YES/NO response
    """
    try:
        # Get query parameters
        if request.method == 'GET':
            query_params = request.GET.dict()
        else:
            # Beacon v2 nests parameters under query.requestParameters; the
            # query below reads top-level keys. Without this the nested body
            # produced an UNFILTERED query — an impossible locus answered
            # exists:true. See beacon_api/request_body.py.
            query_params = flatten_beacon_request(request.data)

        # A POST body is arbitrary JSON, so a "value" may be a dict. Every
        # value below therefore has to be proven scalar BEFORE it is allowed
        # anywhere near the query: `{"diseaseCode": {"$regex": "^A"}}` would
        # otherwise reach Mongo verbatim as a live operator, turning this
        # endpoint's boolean answer into an oracle for binary-searching an
        # individual's disease code one character at a time, and
        # `{"sex": {...}}` would 500 on `.upper()`.
        try:
            reject_operator_keys(query_params)
            sex = scalar_query_value(query_params.get('sex'), 'sex')
            disease_code = scalar_query_value(
                query_params.get('diseaseCode'), 'diseaseCode'
            )
        except UnsafeQueryValue as e:
            logger.warning(f"Rejected unsafe individual query: {e}")
            return _error_response(status.HTTP_400_BAD_REQUEST, str(e))

        # This endpoint answers boolean-only, so it returns no records to page
        # over — but it must still refuse a `filters` array rather than answer
        # the unfiltered question, and must still reject an unusable skip/limit
        # rather than echo one it did not apply.
        try:
            reject_filters(query_params)
        except UnsupportedFilters as e:
            return _error_response(status.HTTP_400_BAD_REQUEST, str(e))
        try:
            skip, limit = parse_pagination(query_params)
        except InvalidPagination as e:
            return _error_response(status.HTTP_400_BAD_REQUEST, str(e))

        # Keys are literals chosen here and values are now guaranteed scalar
        # strings, so nothing user-supplied can occupy an operator position.
        mongo_query = {}

        if sex:
            # An unrecognised value used to be dropped, turning this into
            # "do you have anyone at all". Refuse it instead.
            try:
                mongo_query['sex'] = canonical_sex(sex)
            except UnknownSex as exc:
                return _error_response(status.HTTP_400_BAD_REQUEST, str(exc))

        if disease_code:
            mongo_query['diseases.diseaseCode'] = disease_code

        # Existence only needs one document. `.limit(1).count()` did NOT bound
        # the work — MongoEngine's count() ignores the limit unless asked to
        # honour it — so an attacker-shaped query could make the server count
        # the whole collection on an unauthenticated endpoint.
        # `diseases.diseaseCode` and `sex` are unindexed, so a query matching
        # nothing scans the whole individuals collection. Same server-side
        # budget as the variant endpoint — the collection is small today, and
        # this is what keeps that from silently becoming untrue.
        individual_max_time_ms = getattr(
            settings, 'BEACON_QUERY_MAX_TIME_MS', DEFAULT_QUERY_MAX_TIME_MS
        )
        try:
            if mongo_query:
                exists = Individual.objects(__raw__=mongo_query) \
                    .max_time_ms(individual_max_time_ms).first() is not None
            else:
                # No query parameters - check if any individuals exist
                exists = Individual.objects.max_time_ms(
                    individual_max_time_ms
                ).first() is not None
        except ExecutionTimeout:
            # Unlike the variant endpoint there is no breadth for the caller to
            # reduce here: the only inputs are an exact sex and disease code, so
            # a timeout means the server cannot serve a well-formed request —
            # most likely a missing index on diseases.diseaseCode. Returning 400
            # with no actionable advice would blame a correct request.
            logger.error(
                'Individual query exceeded the %sms budget — check the indexes '
                'on the individuals collection; run manage.py create_indexes',
                individual_max_time_ms,
            )
            return _error_response(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                'This beacon could not answer in time. The query is valid — '
                'the server is unable to serve it right now. Please retry, and '
                'report it if it persists.',
            )

        logger.info(f"Individual query: exists={exists}")

        return Response(build_query_envelope(
            exists=exists,
            num_total=1 if exists else 0,
            validated_params={'skip': skip, 'limit': limit},
        ))

    except ParseError as exc:
        # DRF raises this from `request.data` when the body is not valid JSON.
        # It is a 400-class exception, but it is raised inside this try, so
        # without this clause the generic handler below reports it as 500 —
        # telling a client author to look at the server when the fault is in
        # their request. The developer tutorial's own placeholder body landed
        # here. See beacon_api/test_malformed_body.py.
        message = str(getattr(exc, 'detail', exc)) or 'Malformed JSON body'
        logger.warning(f"Unparseable request body: {message}")
        return _error_response(
            status.HTTP_400_BAD_REQUEST,
            f"Could not parse the request body as JSON: {message}",
        )
    except Exception as e:
        logger.error(f"Query error: {e}", exc_info=True)
        return _server_error()


@api_view(['GET'])
@permission_classes([AllowAny])
@cache_page(60 * 60)  # Cache for 1 hour (datasets change rarely)
def datasets_boolean(request):
    """
    List datasets with variant counts, one page at a time (Boolean mode).
    """
    page, error = _read_page_request(request)
    if error is not None:
        return error

    try:
        # skip/limit are pushed into the queryset rather than applied to a
        # materialised list: slicing afterwards would still fetch and
        # deserialise every document, which is the cost the cap exists to
        # bound. count() is over the whole collection so numTotalResults
        # remains a total.
        all_datasets = Dataset.objects.all()
        total = all_datasets.count()
        datasets = all_datasets.skip(page['skip']).limit(page['limit'])
        results = []
        for ds in datasets:
            # Read counts from the precomputed dataset_size field rather than
            # scanning the variants collection — at production volume (~42M
            # docs, dataset_ids unindexed and often unset) the per-dataset
            # count() degrades into a 30s collection scan that hangs the view.
            # Omit absent counts entirely (the frontend's `!== undefined`
            # guard rejects undefined but not null).
            size = ds.dataset_size or {}
            entry = {
                'id': ds.id,
                'name': ds.name,
                'description': ds.description,
                'assemblyId': ds.assembly_id,
                'createDateTime': ds.create_date.isoformat() if hasattr(ds.create_date, 'isoformat') else ds.create_date,
                'updateDateTime': ds.update_date.isoformat() if hasattr(ds.update_date, 'isoformat') else ds.update_date,
            }
            if isinstance(size.get('variants'), int):
                entry['variantCount'] = size['variants']
            if isinstance(size.get('samples'), int):
                entry['sampleCount'] = size['samples']
            results.append(entry)

        result_sets = []
        if results:
            result_sets = [{
                'id': 'public',
                'setType': 'dataset',
                'exists': True,
                'resultsCount': len(results),
                'results': results,
            }]
        return Response(build_query_envelope(
            exists=total > 0,
            num_total=total,
            result_sets=result_sets,
            validated_params=page,
        ))

    except Exception as e:
        logger.error(f"Datasets query error: {e}", exc_info=True)
        return _server_error()


@api_view(['GET'])
@permission_classes([AllowAny])
def beacon_info_boolean(request):
    """
    Beacon information endpoint for boolean-only mode
    """
    # Build datasets list from DB. A DB failure must NOT be papered over with a
    # fabricated placeholder dataset — /info is how clients discover what this
    # beacon holds, and inventing an entry advertises data we cannot confirm
    # exists. Surface it as a 5xx instead.
    datasets_list = []
    try:
        for ds in Dataset.objects.all():
            datasets_list.append({
                'id': ds.id,
                'name': ds.name,
                'description': ds.description,
                'createDateTime': ds.create_date.isoformat() if ds.create_date else None,
            })
    except Exception as e:
        logger.error(f"Beacon info dataset lookup failed: {e}", exc_info=True)
        return _server_error('Unable to retrieve beacon information')

    info_payload = {
        'id': settings.BEACON_API_ID,
        'name': settings.BEACON_API_NAME,
        'apiVersion': 'v2.0.0',
        'environment': 'prod',
        'organization': {
            'id': settings.BEACON_ORGANIZATION_ID,
            'name': settings.BEACON_ORGANIZATION_NAME,
            'url': settings.BEACON_ORGANIZATION_URL,
            'contactUrl': settings.BEACON_CONTACT_URL,
        },
        'description': 'GA4GH Beacon v2 API - Public boolean discovery service',
        'version': settings.BEACON_API_VERSION,
        'welcomeUrl': settings.BEACON_WELCOME_URL,
        'createDateTime': '2025-08-11T00:00:00Z',
        'updateDateTime': '2025-08-12T00:00:00Z',
        'datasets': datasets_list,
        'serviceType': 'org.ga4gh:beacon:v2.0.0',
        'serviceUrl': settings.BEACON_SERVICE_URL,
        'entryTypes': {
            'g_variants': {
                'id': 'g_variants',
                'name': 'Genomic Variants',
                'responseMode': 'BOOLEAN'
            },
            'individuals': {
                'id': 'individuals',
                'name': 'Individuals',
                'responseMode': 'BOOLEAN'
            }
        },
        'open': True,
        'info': {
            'responseMode': 'BOOLEAN',
            'description': 'This beacon provides boolean (YES/NO) responses only'
        }
    }
    return Response(build_info_envelope(info_payload))


@api_view(['GET'])
@permission_classes([AllowAny])
def beacon_entry_types(request):
    """GA4GH Beacon v2 /entry_types — describes the entity types exposed.
    Required by v2 spec-conformant clients."""
    return Response({
        'meta': {
            'beaconId': settings.BEACON_API_ID,
            'apiVersion': settings.BEACON_API_VERSION,
            'returnedSchemas': [],
        },
        'response': {
            'entryTypes': {
                'g_variants': {
                    'id': 'g_variants',
                    'name': 'Genomic Variants',
                    'ontologyTermForThisType': {
                        'id': 'ENSGLOSSARY:0000092',
                        'label': 'Variants',
                    },
                    'partOfSpecification': 'Beacon v2.0.0',
                    # Spec-defined (framework entryTypeDefinition). True
                    # because this beacon publishes no filtering terms:
                    # every query here is necessarily unfiltered, and
                    # /g_variants rejects a `filters` array outright
                    # rather than answering the unfiltered question.
                    'nonFilteredQueriesAllowed': True,
                    'description': 'Genomic variants cataloged by this Beacon',
                    'defaultSchema': {
                        'id': 'ga4gh-beacon-variant-v2.0.0',
                        'name': 'Default schema for a genomic variant',
                        'referenceToSchemaDefinition': 'https://raw.githubusercontent.com/ga4gh-beacon/beacon-v2-Models/main/BEACON-V2-Model/genomicVariations/defaultSchema.json',
                        'schemaVersion': 'v2.0.0',
                    },
                },
                'individuals': {
                    'id': 'individuals',
                    'name': 'Individuals',
                    'ontologyTermForThisType': {
                        'id': 'NCIT:C25190',
                        'label': 'Person',
                    },
                    'partOfSpecification': 'Beacon v2.0.0',
                    # Spec-defined (framework entryTypeDefinition). True
                    # because this beacon publishes no filtering terms:
                    # every query here is necessarily unfiltered, and
                    # /g_variants rejects a `filters` array outright
                    # rather than answering the unfiltered question.
                    'nonFilteredQueriesAllowed': True,
                    'description': 'Individuals cataloged by this Beacon',
                    'defaultSchema': {
                        'id': 'ga4gh-beacon-individual-v2.0.0',
                        'name': 'Default schema for an individual',
                        'referenceToSchemaDefinition': 'https://raw.githubusercontent.com/ga4gh-beacon/beacon-v2-Models/main/BEACON-V2-Model/individuals/defaultSchema.json',
                        'schemaVersion': 'v2.0.0',
                    },
                },
            },
        },
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def beacon_configuration(request):
    """GA4GH Beacon v2 /configuration — security level, maturity, and
    supported entry types."""
    return Response({
        'meta': {
            'beaconId': settings.BEACON_API_ID,
            'apiVersion': settings.BEACON_API_VERSION,
            'returnedSchemas': [],
        },
        'response': {
            '$schema': 'https://raw.githubusercontent.com/ga4gh-beacon/beacon-v2-Models/main/BEACON-V2-Model/configuration/beaconConfigurationSchema.json',
            'maturityAttributes': {'productionStatus': 'PROD'},
            'securityAttributes': {
                'defaultGranularity': 'boolean',
                'securityLevels': ['PUBLIC'],
            },
            'entryTypes': {
                'g_variants': {
                    'id': 'g_variants',
                    'name': 'Genomic Variants',
                    'ontologyTermForThisType': {
                        'id': 'ENSGLOSSARY:0000092',
                        'label': 'Variants',
                    },
                    'partOfSpecification': 'Beacon v2.0.0',
                    # Spec-defined (framework entryTypeDefinition). True
                    # because this beacon publishes no filtering terms:
                    # every query here is necessarily unfiltered, and
                    # /g_variants rejects a `filters` array outright
                    # rather than answering the unfiltered question.
                    'nonFilteredQueriesAllowed': True,
                    'defaultSchema': {
                        'id': 'ga4gh-beacon-variant-v2.0.0',
                        'name': 'Default schema for a genomic variant',
                        'referenceToSchemaDefinition': 'https://raw.githubusercontent.com/ga4gh-beacon/beacon-v2-Models/main/BEACON-V2-Model/genomicVariations/defaultSchema.json',
                        'schemaVersion': 'v2.0.0',
                    },
                },
                'individuals': {
                    'id': 'individuals',
                    'name': 'Individuals',
                    'ontologyTermForThisType': {
                        'id': 'NCIT:C25190',
                        'label': 'Person',
                    },
                    'partOfSpecification': 'Beacon v2.0.0',
                    # Spec-defined (framework entryTypeDefinition). True
                    # because this beacon publishes no filtering terms:
                    # every query here is necessarily unfiltered, and
                    # /g_variants rejects a `filters` array outright
                    # rather than answering the unfiltered question.
                    'nonFilteredQueriesAllowed': True,
                    'defaultSchema': {
                        'id': 'ga4gh-beacon-individual-v2.0.0',
                        'name': 'Default schema for an individual',
                        'referenceToSchemaDefinition': 'https://raw.githubusercontent.com/ga4gh-beacon/beacon-v2-Models/main/BEACON-V2-Model/individuals/defaultSchema.json',
                        'schemaVersion': 'v2.0.0',
                    },
                },
            },
        },
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def beacon_map(request):
    """GA4GH Beacon v2 /map — URL templates for each endpoint, so
    spec-conformant clients can discover where to query each entity."""
    base = settings.BEACON_SERVICE_URL.rstrip('/')
    return Response({
        'meta': {
            'beaconId': settings.BEACON_API_ID,
            'apiVersion': settings.BEACON_API_VERSION,
            'returnedSchemas': [],
        },
        'response': {
            '$schema': 'https://raw.githubusercontent.com/ga4gh-beacon/beacon-v2-Models/main/BEACON-V2-Model/configuration/beaconMapSchema.json',
            'endpointSets': {
                'g_variants': {
                    'entryType': 'g_variants',
                    'rootUrl': f'{base}/g_variants',
                    'endpoints': {
                        'query': {'returnedEntryType': 'g_variants', 'url': f'{base}/g_variants'},
                    },
                },
                'individuals': {
                    'entryType': 'individuals',
                    'rootUrl': f'{base}/query/individuals',
                    'endpoints': {
                        'query': {'returnedEntryType': 'individuals', 'url': f'{base}/query/individuals'},
                    },
                },
                'datasets': {
                    'entryType': 'dataset',
                    'rootUrl': f'{base}/datasets',
                    'endpoints': {},
                },
                'cohorts': {
                    'entryType': 'cohort',
                    'rootUrl': f'{base}/cohorts',
                    'endpoints': {},
                },
            },
        },
    })


@api_view(['GET'])
@permission_classes([AllowAny])
@throttle_classes([])
def health_check(request):
    """
    Health check endpoint for monitoring.

    Exempt from throttling: container/orchestration health probes poll this
    frequently (every 30s) from a fixed source IP and would otherwise trip the
    anonymous rate limit, marking a healthy container unhealthy.
    """
    try:
        # Check MongoDB connection
        from .models import Dataset
        Dataset.objects.limit(1).count()
        db_status = 'healthy'
    except Exception as e:
        logger.error(f"Database health check failed: {e}", exc_info=True)
        db_status = 'unhealthy'

    # Check cache. Catch Exception, not a bare `except:` — the bare form also
    # swallowed KeyboardInterrupt/SystemExit (so a shutdown signal arriving
    # mid-probe was reported as a mere cache blip) and logged nothing at all,
    # leaving no trace of *why* the cache was unhealthy.
    try:
        from django.core.cache import cache
        cache.set('health_check', 'test', 10)
        cache_status = 'healthy' if cache.get('health_check') == 'test' else 'unhealthy'
    except Exception as e:
        logger.error(f"Cache health check failed: {e}", exc_info=True)
        cache_status = 'unhealthy'

    # The database is load-bearing: without it the beacon cannot answer any
    # query, so a DB failure is a hard 503. A cache failure is reported
    # honestly as 'degraded' but stays 200 — queries still resolve correctly
    # against MongoDB, and 503-ing here would make a transient Redis blip
    # restart an otherwise-serving container.
    status_code = status.HTTP_200_OK if db_status == 'healthy' else status.HTTP_503_SERVICE_UNAVAILABLE
    if db_status != 'healthy':
        overall = 'unhealthy'
    elif cache_status != 'healthy':
        overall = 'degraded'
    else:
        overall = 'healthy'

    return Response({
        'status': overall,
        'version': settings.BEACON_API_VERSION,
        'release': get_release(),
        'services': {
            'database': db_status,
            'cache': cache_status,
        },
        'timestamp': datetime.now().isoformat()
    }, status=status_code)


# ── Entity list + detail views ──────────────────────────────────────────

def _serialize_cohort(co):
    return {
        'id': co.id,
        'name': co.name,
        'description': co.description,
        'cohortType': co.cohort_type,
        'cohortSize': co.cohort_size,
    }


def _serialize_filtering_term(ft):
    return {
        'id': ft.id,
        'label': ft.label,
        'type': ft.ontology or 'custom',
        'scope': [ft.term_category] if ft.term_category else [],
        'description': ft.description,
        'ontologyId': ft.ontology_id,
    }


@api_view(['GET'])
@permission_classes([AllowAny])
@cache_page(60 * 5)
def cohorts_list_boolean(request):
    """List all cohorts (one page of them)."""
    page, error = _read_page_request(request)
    if error is not None:
        return error

    try:
        all_cohorts = Cohort.objects.all()
        total = all_cohorts.count()
        results = [
            _serialize_cohort(c)
            for c in all_cohorts.skip(page['skip']).limit(page['limit'])
        ]
        result_sets = [{
            'id': 'cohorts',
            'setType': 'cohort',
            'exists': len(results) > 0,
            'resultsCount': len(results),
            'results': results,
        }] if results else []
        return Response(build_query_envelope(
            exists=total > 0,
            num_total=total,
            result_sets=result_sets,
            validated_params=page,
        ))
    except Exception as e:
        logger.error(f"Cohorts list error: {e}", exc_info=True)
        return _server_error()


@api_view(['GET'])
@permission_classes([AllowAny])
@cache_page(60 * 5)
def cohort_detail_boolean(request, cohort_id):
    """Get a single cohort by ID."""
    try:
        co = Cohort.objects(id=cohort_id).first()
        items = [_serialize_cohort(co)] if co else []
        result_sets = [{
            'id': cohort_id,
            'setType': 'cohort',
            'exists': bool(co),
            'resultsCount': len(items),
            'results': items,
        }] if items else []
        return Response(build_query_envelope(
            exists=bool(co), num_total=len(items), result_sets=result_sets,
        ))
    except Exception as e:
        logger.error(f"Cohort detail error: {e}", exc_info=True)
        return _server_error()


@api_view(['GET'])
@permission_classes([AllowAny])
@cache_page(60 * 60)
def filtering_terms_list_boolean(request):
    """List the published filtering terms (one page of them).

    This collection is currently empty, which is the honest declaration that
    the beacon supports no ontology-term filtering — and is exactly why
    `filters` is rejected on the query endpoints rather than silently dropped.
    """
    page, error = _read_page_request(request)
    if error is not None:
        return error

    try:
        all_terms = FilteringTerm.objects.all()
        total = all_terms.count()
        results = [
            _serialize_filtering_term(ft)
            for ft in all_terms.skip(page['skip']).limit(page['limit'])
        ]
        return Response(build_collection_envelope(
            results, set_type='filteringTerm',
            validated_params=page, num_total=total,
        ))
    except Exception as e:
        logger.error(f"Filtering terms list error: {e}", exc_info=True)
        return _server_error()


# ---------------------------------------------------------------------------
# Beacon v2 entry-type list stubs.
# These endpoints are required by the verifier (it pings /{entry_type} directly,
# even when /map declares aliases). We declare them as supported but currently
# expose zero records — when real data is loaded, swap the stub for a query.
# ---------------------------------------------------------------------------

def _empty_query():
    """Query-envelope stub — empty result, used by entry-type list endpoints
    that the spec verifier treats as queries (must have responseSummary)."""
    return build_query_envelope(exists=False, num_total=0, result_sets=[])


@api_view(['GET'])
@permission_classes([AllowAny])
@cache_page(60 * 60)
def biosamples_list_boolean(request):
    """Stub /biosamples — boolean mode does not currently expose any."""
    return Response(_empty_query())


@api_view(['GET'])
@permission_classes([AllowAny])
@cache_page(60 * 60)
def analyses_list_boolean(request):
    """Stub /analyses — boolean mode does not currently expose any."""
    return Response(_empty_query())


@api_view(['GET'])
@permission_classes([AllowAny])
@cache_page(60 * 60)
def runs_list_boolean(request):
    """Stub /runs — boolean mode does not currently expose any."""
    return Response(_empty_query())


# Beacon v2 dataset-scoped routes that the verifier probes:
# /datasets/{id} and /datasets/{id}/{entry_type}. We stub them to empty
# query envelopes so spec validation passes; real per-dataset query support
# is a future enhancement.

@api_view(['GET'])
@permission_classes([AllowAny])
@cache_page(60 * 60)
def dataset_detail_boolean(request, dataset_id):
    """Single dataset detail — returns the dataset if found, else empty."""
    try:
        ds = Dataset.objects(id=dataset_id).first()
        if not ds:
            return Response(_empty_query())
        item = {
            'id': ds.id,
            'name': ds.name,
            'description': ds.description,
            'assemblyId': ds.assembly_id,
        }
        result_sets = [{
            'id': ds.id, 'setType': 'dataset',
            'exists': True, 'resultsCount': 1, 'results': [item],
        }]
        return Response(build_query_envelope(
            exists=True, num_total=1, result_sets=result_sets,
        ))
    except Exception as e:
        # A lookup failure is NOT the same as "no such dataset". Returning the
        # empty 200 envelope here made a MongoDB outage indistinguishable from
        # a genuine miss, so clients (and the Beacon Network aggregator) would
        # record an authoritative "does not exist" for data we simply could
        # not read. Only the `not ds` branch above may answer empty-but-200.
        logger.error(f"Dataset detail error: {e}", exc_info=True)
        return _server_error()


@api_view(['GET'])
@permission_classes([AllowAny])
@cache_page(60 * 60)
def dataset_scoped_query_boolean(request, dataset_id, entry_type):
    """/datasets/{id}/{entry_type} — 501 until per-dataset drill-down exists.

    This used to return an empty query envelope: HTTP 200, exists: false, for
    every input, cached for an hour. A dataset holding 42M variants answered
    "not found" for a locus inside it.

    "I cannot answer this" and "the answer is no" are different statements,
    and only the first is true here — see beacon_api/capabilities.py, and the
    comment on dataset_detail_boolean above, which records the same failure
    reaching the Beacon Network aggregator during a MongoDB outage.
    """
    if not is_dataset_scope_supported(entry_type):
        return _error_response(
            status.HTTP_501_NOT_IMPLEMENTED,
            unsupported_dataset_scope_message(dataset_id, entry_type),
        )
    return Response(_empty_query())
