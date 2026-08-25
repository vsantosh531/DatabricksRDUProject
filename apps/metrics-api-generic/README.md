# RDU Metrics API — generic

FastAPI Databricks App serving all 5 gold-layer metrics through one
parameterized route, driven by `registry.py`. Data comes from Lakebase
Postgres synced tables (`semantic.*` on the `rdu-metrics-api` project) via
a direct `psycopg2` connection — not the SQL warehouse, and not Lakebase's
Data API/PostgREST layer (that layer hit an unresolved `authenticator`
role-grant gap; direct Postgres connections sidestep it entirely). Each
metric view's gold-table data was pre-aggregated once via a UC metric view
and materialized into these tables (`notebooks/47_gold_metric_views.py`,
`notebooks/53_semantic_gold_metric_snapshots.py`), then Reverse-ETL synced
into Postgres — the API itself does plain `SELECT`s, no aggregation.

## Endpoints

- `GET /api/metrics` — list available metrics (short name, backing table,
  dimensions, measures).
- `GET /api/metrics/{view_name}?dimensions=a,b&measures=c,d&limit=500` —
  query one metric. `view_name` is one of the short names from
  `/api/metrics` (`county-market`, `affordability`, `market-health`,
  `supply-demand`, `zip-hotspots`). `dimensions`/`measures` default to the
  view's full set and are validated against the registry — unknown values
  return 400, unknown `view_name` returns 404.
- `GET /health`

## Auth

`db.py` mints a fresh Lakebase OAuth token per request via
`WorkspaceClient().postgres.generate_database_credential()` and connects
as `DATABRICKS_CLIENT_ID` (the deployed app's own service principal,
auto-injected — already registered as a Postgres role on `rdu-metrics-api`
with `SELECT` on all 5 synced tables). Locally it falls back to your own
Databricks identity. Minting a token per request avoids the 1-hour
token-refresh/connection-pool complexity a long-lived pool would need —
fine for this traffic level, worth revisiting if request volume grows.

## Local run

```bash
pip install -r requirements.txt
uvicorn app:app --reload
```

Requires an authenticated `~/.databrickscfg` profile. Swagger UI at
`http://localhost:8000/docs`.

## Deploy

```bash
databricks apps create metrics-api-generic
databricks workspace mkdirs /Workspace/Users/venkatana.kanchibhotla@gmail.com/apps/metrics-api-generic
databricks workspace import-dir . \
  /Workspace/Users/venkatana.kanchibhotla@gmail.com/apps/metrics-api-generic --overwrite
databricks apps deploy metrics-api-generic \
  --source-code-path /Workspace/Users/venkatana.kanchibhotla@gmail.com/apps/metrics-api-generic
```

No app resource attachment needed — `db.py` talks to Lakebase directly via
the app's own service principal, already granted access on the Postgres
side (`databricks postgres create-role` + `GRANT SELECT`).

Redeploy: re-run `import-dir ... --overwrite` then `apps deploy` again,
check `databricks apps logs metrics-api-generic`.
