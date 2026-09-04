# Getting started

If you have not run the stack before, do
[tutorial-zero-to-beacon.md](tutorial-zero-to-beacon.md) first — it takes about
15 minutes and ends with a beacon answering real queries. This page is the
condensed version plus what you need on day two.

## The short version

```bash
git clone https://github.com/AfriGen-D/variant-checker-beacon.git
cd variant-checker-beacon
cp .env.example .env.boolean
sed -i '' 's/^SECURE_SSL_REDIRECT=True/SECURE_SSL_REDIRECT=False/' .env.boolean
docker compose -f compose/docker-compose.dev.yml up -d --build mongodb redis beacon-api
docker compose -f compose/docker-compose.dev.yml exec -T beacon-api \
  python manage.py load_boolean_test_data --settings=beacon_project.settings_boolean
curl -s http://localhost:8000/api/health
```

Three things bite everyone on the first run, all explained in the tutorial:
`.env.boolean` is gitignored so a clone does not have it; `.env.example` sets
`SECURE_SSL_REDIRECT=True`, which 301s every local request into the void; and an
env change needs `--force-recreate`, not `restart`.

## Repository layout

| Path | What it is |
| --- | --- |
| `beacon_api/` | The API. Models, views, validators, query semantics. |
| `beacon_project/` | Django settings and URL configuration. |
| `frontend/` | Next.js 14 App Router UI, TypeScript, Tailwind. |
| `afrigend-beacon2-tools/` | VCF to Beacon transformation and import tooling. |
| `nextflow/` | Bulk ingestion pipeline. |
| `compose/` | Docker Compose stacks. |
| `docs/` | Documentation, including this folder. |

## Two modes, one codebase

**Boolean mode** is what runs in production and what the tutorial starts.
Public, no authentication, answers yes/no. `settings_boolean.py`,
`views_boolean.py`, `urls_boolean.py`.

**Secure mode** (`settings_secure.py`, `views.py`) is incomplete and should not
be deployed. It advertises GA4GH AAI that does not exist in the codebase, and
its audit findings are unresolved. Note that `manage.py` and `wsgi.py` default
to a settings module routing to secure mode with `AllowAny` — so pass
`--settings=` deliberately on every management command, as the tutorial does.

## Running the frontend

```bash
cd frontend
npm ci
npm run dev
```

The dev server listens on `http://localhost:3000`.

The UI calls the API via relative `/api/...` paths. Locally you need either a
proxy or an API base pointed at `http://localhost:8000`; read
`frontend/src/lib/api/client.ts` for what the code actually consults rather
than assuming.

Gates CI enforces on the frontend:

```bash
npm run type-check
npm run lint
```

`type-check` runs `tsc --noEmit`; `lint` runs `eslint .`.

`npm run test:ci` exists and runs Jest against **zero test files** — there are
none in the repository. Do not read a pass from it as coverage.

## Everyday commands

Tail the API logs:

```bash
docker compose -f compose/docker-compose.dev.yml logs -f beacon-api
```

Get a shell in the API container:

```bash
docker compose -f compose/docker-compose.dev.yml exec beacon-api sh
```

Open the Mongo shell. The 5.0 image ships the legacy `mongo` client —
`mongosh` does not exist on it:

```bash
docker compose -f compose/docker-compose.dev.yml exec mongodb mongo beacon_db
```

Clear the response cache after changing API output:

```bash
docker compose -f compose/docker-compose.dev.yml exec redis redis-cli FLUSHDB
```

Create the indexes the query paths need. Safe to re-run:

```bash
docker compose -f compose/docker-compose.dev.yml exec beacon-api python manage.py create_indexes --settings=beacon_project.settings_boolean
```

Stop everything. Add `-v` to drop the database volume as well:

```bash
docker compose -f compose/docker-compose.dev.yml down
```

Redis caches responses for five minutes. If you change a response shape and the
output does not move, flush before you start debugging.

## Python versions

The backend pins **Django 4.0.10**, held there by `django-mongoengine`. Django
4.0 imports `cgi`, which Python removed in 3.13 — so anything importing Django
needs **Python 3.9 to 3.12**. CI uses 3.9.

The query-correctness suites deliberately import none of that and run on any
Python 3. See [testing.md](testing.md).

## Next

- [architecture.md](architecture.md) — how a query becomes an answer
- [testing.md](testing.md) — what gates a merge
- [api-contract.md](api-contract.md) — the response envelope
- [contributing.md](contributing.md) — branches, commits, PRs
