# RDU Metrics API — dedicated routes

FastAPI Databricks App serving all 5 gold-layer metrics through
hand-written, per-view routes with typed Pydantic response models —
the comparison case for `apps/metrics-api-generic`'s single parameterized
route. Data comes from Lakebase Postgres synced tables (`semantic.*` on
the `rdu-metrics-api` project) via a direct `psycopg2` connection — not
the SQL warehouse, and not Lakebase's Data API/PostgREST layer (that
layer hit an unresolved `authenticator` role-grant gap; direct Postgres
connections sidestep it entirely). Same underlying `run_table_query()`
query mechanics as the generic app; the only real difference under test
is routing/typing style.

## Endpoints

- `GET /api/county-market`
- `GET /api/affordability`
- `GET /api/market-health`
- `GET /api/supply-demand`
- `GET /api/zip-hotspots`
- `GET /health`

Each route returns `list[<ViewName>Row]` (see `models.py`) — FastAPI
validates the response shape per route and documents it individually at
`/docs`, unlike the generic app's one loosely-typed response.

## Auth

`db.py` mints a fresh Lakebase OAuth token per request via
`WorkspaceClient().postgres.generate_database_credential()` and connects
as `DATABRICKS_CLIENT_ID` (the deployed app's own service principal,
auto-injected — already registered as a Postgres role on `rdu-metrics-api`
with `SELECT` on all 5 synced tables). Locally it falls back to your own
Databricks identity.

## Local run

```bash
pip install -r requirements.txt
uvicorn app:app --reload
```

Requires an authenticated `~/.databrickscfg` profile. Swagger UI at
`http://localhost:8000/docs`.

## Deploy

```bash
databricks apps create metrics-api-dedicated
databricks workspace mkdirs /Workspace/Users/venkatana.kanchibhotla@gmail.com/apps/metrics-api-dedicated
databricks workspace import-dir . \
  /Workspace/Users/venkatana.kanchibhotla@gmail.com/apps/metrics-api-dedicated --overwrite
databricks apps deploy metrics-api-dedicated \
  --source-code-path /Workspace/Users/venkatana.kanchibhotla@gmail.com/apps/metrics-api-dedicated
```

No app resource attachment needed — `db.py` talks to Lakebase directly via
the app's own service principal, already granted access on the Postgres
side (`databricks postgres create-role` + `GRANT SELECT`).

Redeploy: re-run `import-dir ... --overwrite` then `apps deploy` again,
check `databricks apps logs metrics-api-dedicated`.
