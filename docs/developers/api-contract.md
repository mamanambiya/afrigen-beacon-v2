# The API contract

What the beacon actually returns, and the trap in it.

## The envelope

Every data endpoint returns the GA4GH Beacon v2 envelope — three top-level keys:

```text
{
  "meta":            { "beaconId": "org.afrigen-d.beacon", "apiVersion": "v2.0.0", ... },
  "responseSummary": { "exists": false, "numTotalResults": 0 },
  "response":        { "resultSets": [], "beaconHandovers": [ ... ] }
}
```

## The trap: `exists` is not at the top level

**The answer lives at `responseSummary.exists`.** There is no top-level
`exists` field and there never has been on this deployment.

Several documents in this repository show client examples that parse one —
`docs/BOOLEAN_MODE.md` and `docs/API_REFERENCE.md` both do, in bash, JavaScript
and Python. The bash form is the dangerous one:

```bash
# WRONG — this is in the repo's own docs
exists=$(echo "$response" | jq -r '.exists')     # always null
[ "$exists" = "true" ] && echo FOUND || echo "NOT FOUND"
```

`jq` yields `null`, the test never fires, and the script prints **NOT FOUND for
every locus** including ones the beacon holds. It fails silently and looks like
a scientific result. The JavaScript form fails the same way; the Python form at
least raises `KeyError`.

```bash
# RIGHT
exists=$(echo "$response" | jq -r '.responseSummary.exists')
```

The envelope was introduced deliberately on 2026-05-02 for spec conformance;
the client examples were never updated. Verified still wrong on 2026-08-19.

## `numTotalResults` is not a variant count

You will see this:

```json
{"exists": true, "numTotalResults": 0}
```

That is not a contradiction in your data. Under some paths the counter reports
matching *datasets* rather than matching variants. **Never infer absence from
`numTotalResults`.** Read `exists`.

## `beaconHandovers` is nested where the spec does not put it

The spec places `beaconHandovers` at the top level of the response. This beacon
returns it inside `response`:

```text
"response": { "resultSets": [], "beaconHandovers": [ {"id": "CUSTOM:FEDERATED_IMPUTATION", ...} ] }
```

A spec-conformant client looking at the top level will not find it — which
means the federated-imputation handover, the beacon's only onward route to the
underlying data, is invisible to exactly the clients most likely to look.

## Coordinates

Variants are stored **0-based half-open**, as produced by the VCF transform:

```text
start = POS - 1
end   = POS - 1 + len(REF)
```

so a stored variant occupies `[start, end)`. Two half-open intervals overlap
iff `a < d AND b > c`, which in Mongo terms is `start__lt` / `end__gt`. This is
implemented in `beacon_api/query_semantics.py` and pinned by 24 tests including
a contrast suite that goes red if anyone reverts it to closed-interval
comparisons.

**A VCF POS is 1-based.** If you paste a coordinate from a VCF or a paper
without subtracting one, you will get a confident, wrong `false`.

## Chromosome and assembly vocabulary

Chromosomes may be stored as `1` or `chr1` depending on the ingest run, and
the query path matches both. Assembly spellings are canonicalised the same way
(`beacon_api/assembly.py`), so `hg38` and `GRCh38` return the same answer and an
unrecognised assembly is refused rather than answered. See Step 9 of
[tutorial-zero-to-beacon.md](tutorial-zero-to-beacon.md) for why that matters.

## POST is currently broken

A spec-shaped POST body returns HTTP 400 with "Invalid characters detected in
query". The sanitizer stringifies nested values before pattern-matching, and the
Python repr of a dict contains quotes that match its own injection pattern. GET
is unaffected, which is why this has gone unnoticed in production.

A tested fix exists on branch `fix/sanitizer-nested-post-body`, unmerged.
**Use GET until it lands.**

## Endpoints

```text
GET  /api/                      beacon info
GET  /api/service-info          GA4GH service info
GET  /api/configuration
GET  /api/entry_types
GET  /api/map
GET  /api/health
GET/POST /api/g_variants        variant query
GET/POST /api/query/individuals individual query
GET  /api/datasets
GET  /api/individuals           list  (see note)
GET  /api/biosamples            list
GET  /api/cohorts               list
GET  /api/analyses              list
GET  /api/filtering_terms
```

Two of these currently answer a constant empty result regardless of input:
`/api/individuals` (use `/api/query/individuals`) and
`/api/datasets/{id}/{entry_type}`. Both return an authoritative-looking `false`
rather than an error, so do not treat their answers as data.
