# Beacon v2 Handover — Implementation Guide

> **Status:** implemented (boolean / public profile) · **Last updated:** 2026-05-06
> **Scope:** this document covers handover for the AfriGen-D public Beacon
> only. Secure-mode handovers (DRS, htsget) are out of scope and remain a
> future feature — see *Extending* below.

## What handover is (in 30 seconds)

In Beacon v2, a query response can carry **handover links** — pointers to
where the underlying data, or actions on that data, can be obtained. The
spec defines two scopes:

| Scope | Field | Applied to |
| --- | --- | --- |
| Top-level | `response.beaconHandovers` | Every query response |
| Per-result | `resultsHandover` (inside each result) | A single record |

Use top-level for things that don't vary per query (DAC application URL,
service tutorial, contact). Use per-result for variant-specific links
(DRS object IDs for that variant, htsget streaming URLs, etc.).

## What this Beacon does

The AfriGen-D Beacon is **read-only and download-disabled**. The reference
panel cannot be exported, and there is no Data Access Committee
application process. The data is usable only through the **AfriGen-D
Federated Imputation Service**, which runs imputation jobs against the
panel without exposing raw genotypes.

Therefore the handover is a **single top-level link** that directs
discoverers from "yes, this variant exists" → "use it via the federated
imputation service":

```text
"beaconHandovers": [
  {
    "handoverType": {
      "id": "CUSTOM:FEDERATED_IMPUTATION",
      "label": "AfriGen-D Federated Imputation Service"
    },
    "url": "https://fedimpute.afrigen-d.org",
    "note": "The underlying genomic data is not available for download..."
  }
]
```

The full `note` text is defined in
`beacon_api/utils.py :: build_default_handovers()` and is delivered
verbatim in the API response.

## Why this design

- **Top-level, not per-result.** The handover URL doesn't change per
  variant, so per-result entries would just duplicate the same payload.
- **`CUSTOM:` namespace.** No GA4GH/EFO ontology term cleanly describes
  "federated imputation service link." Progenetix and EGA use the same
  `CUSTOM:` pattern for their non-ontology handovers; the verifier
  accepts it.
- **Settings-driven.** The URL is a config value, not a literal — operators
  can flip it via environment variable without code changes.
- **Wired in the envelope helper, not the views.** Every entry-type
  endpoint (`/g_variants`, `/individuals`, `/biosamples`, …) reuses
  `build_query_envelope()`, so handover propagates everywhere
  automatically.

## Files and call graph

| File / symbol | Role |
| --- | --- |
| `settings_boolean.py` :: `BEACON_IMPUTATION_URL` | Configurable URL |
| `utils.py` :: `build_default_handovers()` | Builds the handover list |
| `utils.py` :: `build_query_envelope()` | Embeds list in envelope |
| `views_boolean.py` (query views) | Calls `build_query_envelope(...)` |

```text
GET /api/g_variants?...           [or any other entry-type query]
        │
        ▼
views_boolean.py
  variant_query_boolean()         # builds result_sets
        │
        ▼
utils.py  build_query_envelope()  # embeds:
        │                         #   response.resultSets       ← from view
        │                         #   response.beaconHandovers  ← below
        ▼
utils.py  build_default_handovers()
  reads settings.BEACON_IMPUTATION_URL
  returns [{handoverType, url, note}]
```

## Configuration

Environment variable, read on Django startup:

```bash
# .env.boolean (or .env.production for secure mode when wired)
BEACON_IMPUTATION_URL=https://fedimpute.afrigen-d.org   # default
```

To **disable handover entirely** (e.g., during local debugging where
`fedimpute.afrigen-d.org` would be misleading):

```bash
BEACON_IMPUTATION_URL=
```

`build_default_handovers()` returns `[]` when the URL is empty/unset; the
verifier still passes (the field is present and is a list).

## Verification

After a code change or deploy, confirm the handover is present in live
responses:

```bash
# Top-level handover should appear in the result
URL='https://beacon.afrigen-d.org/api/g_variants'
Q='referenceName=11&start=5246696&referenceBases=A&alternateBases=T'
curl -s "$URL?$Q" | jq '.response.beaconHandovers'
```

Expected: a JSON array containing a single object with `handoverType`,
`url`, and `note` fields.

If it returns `[]`:

1. Check the env var: `docker exec beacon-api-boolean env | grep IMPUTATION`
2. Check Redis hasn't cached a pre-handover response:
   `docker exec beacon-redis redis-cli FLUSHDB`
3. Restart the API container:
   `docker compose -f docker-compose-boolean-ssl.yml up -d \
   --no-deps beacon-api-boolean`

## Spec conformance

The current EGA verifier (v0.3.3) treats `beaconHandovers` as optional —
the AfriGen-D Beacon was 17/17 PASS *before* handover was populated. After
handover, it remains 17/17 PASS. To re-confirm:

```bash
docker run --rm beacon-verifier:latest https://beacon.afrigen-d.org/api/
```

(Or against the API-only sidecar:
`https://api-beacon.afrigen-d.dev/api/`.)

## Extending

### Adding new top-level handover entries

Edit `build_default_handovers()` in `beacon_api/utils.py`. Append entries
to the returned list. Each entry must have `handoverType.{id,label}` and
`url`; `note` is optional but recommended.

Example — adding a tutorial link alongside the imputation service:

```python
return [
    {
        'handoverType': {'id': 'CUSTOM:FEDERATED_IMPUTATION', ...},
        'url': imputation_url,
        'note': '...',
    },
    {
        'handoverType': {
            'id': 'CUSTOM:DOCUMENTATION',
            'label': 'AfriGen-D Beacon documentation',
        },
        'url': 'https://docs.afrigen-d.org/beacon/',
        'note': 'Tutorial and query examples.',
    },
]
```

### Adding per-result handovers

For variant-specific links (e.g., a DRS download URL for the BAM
containing carriers of *that* allele), the handover must be attached
inside each `result_sets[].results[]` entry rather than at the top level.
This requires changes in the view layer — the place where each result is
constructed.

The boolean profile currently doesn't return per-variant results
(`resultsCount: 1` with no detail), so per-result handover is only
relevant when **secure mode** is wired up. At that point the pattern
is:

```python
result_sets.append({
    'id': dataset.id,
    'setType': 'dataset',
    'exists': True,
    'resultsCount': N,
    'results': [
        {
            ...variant data...,
            'resultsHandover': [
                {
                    'handoverType': {
                        'id': 'EFO:0004157',  # BAM file
                        'label': 'BAM file',
                    },
                    'url': f'https://drs.afrigen-d.org/objects/{drs_id}',
                },
            ],
        },
    ],
})
```

### Differentiating handover by authentication

The boolean profile is unauthenticated, so a single public handover is
correct. When secure mode is added (see
`docs/GA4GH_AAI_IMPLEMENTATION_PLAN.md`), `build_default_handovers()`
should accept a `request` argument (or a parsed identity object) and
branch:

- **Anonymous** → public handover (current behaviour)
- **Authenticated researcher with active visa** → public handover *plus*
  DRS / htsget URLs
- **DAC member** → public handover *plus* governance dashboard URL

Keep the helper signature stable when this lands —
`build_query_envelope()` is called from many views and shouldn't have to
care about identity itself.

## Caveats

- **Caching.** Responses are cached in Redis with a 5-minute TTL
  (`@cache_page(60 * 5)` decorators). After a handover change, cached
  responses won't reflect the new payload until either the TTL expires
  or `FLUSHDB` is run.
- **Verifier blind spot.** The current verifier doesn't validate handover
  semantics — it only checks the field is present and is a list. A
  malformed entry (missing `url`, wrong types) will pass the verifier
  but break downstream tools that follow the spec strictly.
- **Note length.** Some Beacon UIs render the `note` as a tooltip; very
  long notes get truncated. The current note (~60 words) is at the upper
  end of "still readable." Don't expand unless you know the consuming UI
  handles it.

## See also

- `beacon_api/utils.py` — helper implementations
- `docs/SPEC_CONFORMANCE.md` — verifier results and history
- `docs/GA4GH_AAI_IMPLEMENTATION_PLAN.md` — the secure-mode plan that
  will trigger per-result and identity-aware handovers
- Beacon v2 spec, *Framework / Handovers*:
  [docs.genomebeacons.org/framework/#handover](https://docs.genomebeacons.org/framework/#handover)
