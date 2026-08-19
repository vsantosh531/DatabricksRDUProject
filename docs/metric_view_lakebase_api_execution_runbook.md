# Metric View → Lakebase → API — Execution Runbook

Phased implement/test steps for
`docs/metric_view_lakebase_api_architecture.md`. Run these yourself, in
order — each phase depends on state the previous one created. Companion to
`docs/semantic_layer_execution_runbook.md` (same style: checkpoints, real
commands verified live against this account, honest `[verify]` flags where
something genuinely wasn't confirmed).

## Where and how to run these commands

Same as `docs/semantic_layer_execution_runbook.md`: a terminal on your own
computer, `-p DEFAULT` profile (already authenticated on this account),
not a notebook or the web UI except where a phase says otherwise.

**UI alternative, with an honesty caveat.** Each phase below now also has
an "**In the Databricks UI instead:**" block. One real difference from
everything else in this doc: the CLI commands were run live against this
account and verified; the UI steps were not — this session has no browser
access, so they're standard Databricks product navigation, not
click-by-click confirmed the same way. Menu labels can drift between
workspace versions; if a label doesn't match what's described, look for
the nearest equivalent rather than assuming the feature moved.

---

## Phase 0 — Verify the Lakebase CLI surface

Both `databricks postgres` and `databricks database` CLI groups exist on
this account and **both** expose synced-table commands — confirmed live,
not assumed:

```bash
databricks postgres -h        # create-synced-table (Beta)
databricks database -h        # create-synced-database-table (Public Preview)
```

**This runbook uses the `postgres` group throughout**, since it's the same
group used for `create-project` — keeping the whole pipeline in one
consistent command family rather than mixing `postgres`-created projects
with `database`-group table commands, which weren't confirmed
interoperable in this session (docs-only scope — no live provisioning was
done to test the mix).

```bash
# Confirm the metric view's current dimensions/measures before writing
# any SQL against it — don't rely on names from this doc going stale
databricks tables get workspace.gold.zip_hotspots_metric_view -p DEFAULT
```

At the time this runbook was written, the confirmed dimensions were `zip`,
`zip_name`, `quarter_start`, and confirmed measures included
`avg_days_on_market`, `total_active_listings`, `price_reduction_rate`,
`total_new_listings`, `inventory_turnover_rate`, `avg_listings_per_zip`,
`net_inventory_change`, `count`.

**Checkpoint:** you know which CLI group you're using and have the current,
real measure names in hand — not the ones printed in this doc if they've
since changed.

**In the Databricks UI instead:** open **Catalog** (left sidebar) →
navigate `workspace` → `gold` → `zip_hotspots_metric_view`. The object's
detail page shows its dimensions and measures directly (metric views
render their YAML/column structure in Catalog Explorer) — no CLI needed
for this check. The CLI-group discovery part of this phase (`postgres` vs
`database`) has no UI equivalent — it's purely a CLI concern, skip it if
you're staying in the UI throughout.

---

## Phase 1 — Snapshot the metric view into a physical table

The metric view can answer any grain; Lakebase can only sync a table. This
phase picks one grain — latest quarter, by ZIP — and materializes it.

Save as `notebooks/52_semantic_zip_hotspots_snapshot.py` (next free number
after `50_gold_metric_view.py` / `51_gold_aibi_queries.py`):

```python
# Databricks notebook source
# MAGIC %md
# MAGIC # 52 - Semantic: ZIP Hotspots Metrics Snapshot
# MAGIC
# MAGIC Materializes one grain (latest quarter, by ZIP) of
# MAGIC workspace.gold.zip_hotspots_metric_view into a physical Delta
# MAGIC table, so it can be synced to Lakebase — metric views can't be
# MAGIC synced directly. See docs/metric_view_lakebase_api_architecture.md.

# COMMAND ----------

spark.sql("""
CREATE SCHEMA IF NOT EXISTS workspace.semantic
""")

spark.sql("""
CREATE OR REPLACE TABLE workspace.semantic.zip_hotspots_metrics_snapshot AS
SELECT
    zip,
    zip_name,
    MEASURE(avg_days_on_market)    AS avg_days_on_market,
    MEASURE(total_active_listings) AS total_active_listings,
    MEASURE(price_reduction_rate)  AS price_reduction_rate,
    CURRENT_TIMESTAMP()            AS snapshot_generated_at
FROM workspace.gold.zip_hotspots_metric_view
WHERE quarter_start = (
    SELECT MAX(quarter_start) FROM workspace.gold.zip_hotspots WHERE is_current = true
)
GROUP BY ALL
""")

print("Snapshot written: workspace.semantic.zip_hotspots_metrics_snapshot")
```

Run it manually once (Databricks UI or `databricks jobs run-now` against an
ad hoc single-notebook job — this phase is about proving the SQL works,
not wiring it into the pipeline yet).

```bash
# Confirm it landed and has one row per ZIP
databricks tables get workspace.semantic.zip_hotspots_metrics_snapshot -p DEFAULT
```

**Full overwrite every run** (`CREATE OR REPLACE TABLE`) — the table is
tiny (one row per ZIP), so there's no benefit to incremental merge logic.

**Checkpoint:** the snapshot table exists, has one row per ZIP, and its
`price_reduction_rate` values match what you'd get querying the metric
view directly at this grain (spot-check 2–3 rows by hand).

**In the Databricks UI instead:**
1. **Workspace** (left sidebar) → your user folder → **Create → Notebook**.
2. Name it `52_semantic_zip_hotspots_snapshot`, language **Python**.
3. Paste the code block above into the first cell.
4. Leave compute on serverless (the account default) and click **Run all**.
5. Verify: **Catalog** → `workspace` → `semantic` →
   `zip_hotspots_metrics_snapshot` → the **Sample Data** tab previews rows
   directly, same check as the CLI's `tables get`.

---

## Phase 2 — Wire the snapshot into the existing pipeline job

**Already done, not still a manual step.** `resources/medallion_pipeline_job.yml`
now includes `52_semantic_zip_hotspots_snapshot` as a task depending on
`46_gold_zip_hotspots`, deployed via `databricks bundle deploy`. What
follows is the UI-only path for reference — e.g. if you're managing a job
outside this bundle, or want to see it without opening the YAML.

**In the Databricks UI instead:**
1. **Workflows** (left sidebar) → open **RDU Medallion Pipeline**
   (`events_medallion -> bronze -> silver -> gold`).
2. The **Tasks** tab shows the graph — `52_semantic_zip_hotspots_snapshot`
   already sits after `46_gold_zip_hotspots` with an arrow between them;
   nothing to add.
3. To build this by hand in a different job instead: **Tasks** tab → **+
   Add task** → Type **Notebook** → path to
   `52_semantic_zip_hotspots_snapshot` → **Depends on** → select the task
   that refreshes `gold.zip_hotspots` → **Create task**.

**Checkpoint:** the job's task graph shows the snapshot task with exactly
one incoming dependency — the gold-refresh task — not zero (which would
mean it runs on its own schedule against possibly-stale gold data) and not
many (which would just be extra, unneeded waiting).

---

## Phase 3 — Provision the Lakebase project

```bash
databricks postgres create-project rdu-metrics-api \
  --json '{"spec": {"display_name": "RDU Metrics API"}}' \
  --profile DEFAULT
```

This auto-provisions a `production` branch and a `primary` read-write
endpoint at 1 CU min/max with scale-to-zero on by default.

```bash
# Get the branch and endpoint IDs
databricks postgres list-branches projects/rdu-metrics-api -p DEFAULT
databricks postgres list-endpoints projects/rdu-metrics-api/branches/<BRANCH_ID> -p DEFAULT
```

Resize down immediately — this workload doesn't need 1 CU:

```bash
databricks postgres update-endpoint \
  projects/rdu-metrics-api/branches/<BRANCH_ID>/endpoints/<ENDPOINT_ID> \
  "spec.autoscaling_limit_min_cu,spec.autoscaling_limit_max_cu" \
  --json '{"spec": {"autoscaling_limit_min_cu": 0.5, "autoscaling_limit_max_cu": 0.5}}' \
  --profile DEFAULT
```

No extra branch, no extra database — use the auto-provisioned
`production` branch and `databricks_postgres` database as-is.

**[verify]** whether this Free Edition account has a Lakebase-specific
quota (compute-hours, storage cap, project-count cap) beyond what
`list-projects` succeeding tells you — that wasn't confirmed in this
session and could push the sizing above smaller or larger.

**Checkpoint:** `list-endpoints` shows 0.5/0.5 CU, scale-to-zero enabled.

**In the Databricks UI instead** — corrected against the official
Databricks docs (docs.databricks.com/aws/en/oltp/projects/get-started and
.../manage-computes) after an earlier draft of this section guessed wrong
and sent someone down a dead end. The endpoint settings live under the
**branch**, not directly on the project page — that's the part the
earlier guess missed:

1. **App switcher** (top of the Databricks UI) → **Lakebase Postgres** app.
2. Select **Autoscaling** (the tier `create-project` provisions by
   default) → this is also where **New project** lives, if creating one
   from scratch instead of the CLI.
3. Open the project (**rdu-metrics-api**) → **Branches** page → select
   the branch (**production**).
4. Open its **Computes** tab → click **Edit** on the compute → adjust the
   autoscaling min/max CU (or fixed size) → **Save**.

Equivalent CLI path, already verified working against this real project:

```bash
# Auto-created names are literally "production" and "primary"
databricks postgres list-branches projects/rdu-metrics-api -p DEFAULT
databricks postgres list-endpoints projects/rdu-metrics-api/branches/production -p DEFAULT

databricks postgres update-endpoint \
  projects/rdu-metrics-api/branches/production/endpoints/primary \
  "spec.autoscaling_limit_min_cu,spec.autoscaling_limit_max_cu" \
  --json '{"spec": {"autoscaling_limit_min_cu": 0.5, "autoscaling_limit_max_cu": 0.5}}' \
  -p DEFAULT
```

Confirm via the same `list-endpoints` call — `autoscaling_limit_min_cu`/
`max_cu` should read `0.5` in the response.

---

## Phase 4 — Sync the snapshot table into Lakebase

**This phase touches two different SQL systems — know which one each
command runs against.** `TBLPROPERTIES` and `delta.enableChangeDataFeed`
are Delta Lake/Databricks-specific syntax; plain PostgreSQL has never heard
of either and will fail with a `syntax error at or near "TBLPROPERTIES"`
(`SQLSTATE 42601`) if you paste it into a Postgres/Lakebase connection —
that exact mistake happened while writing this runbook. If you still have
a Lakebase SQL connection open from Phase 3, switch back to a Databricks
SQL warehouse connection before running the first command below.

**① Databricks SQL (Delta/UC side)** — enable Change Data Feed on the
source table (required for Triggered sync). Run this in the Databricks
**SQL Editor** with a Databricks SQL warehouse selected, or via the CLI
against a warehouse (`databricks experimental aitools tools query
--warehouse <WAREHOUSE_ID> -p DEFAULT "..."`) — **not** through a Postgres
connection:

```sql
ALTER TABLE workspace.semantic.zip_hotspots_metrics_snapshot
SET TBLPROPERTIES (delta.enableChangeDataFeed = true)
```

**② Databricks CLI** (`postgres` command group — this one manages Lakebase
infrastructure via the Databricks control plane, not a direct Postgres SQL
connection, so it's unambiguous which system it targets). **This exact
command is confirmed working** — verified live against `rdu-metrics-api`,
reaching `SYNCED_TABLE_ONLINE_NO_PENDING_UPDATE` in about 7 seconds:

```bash
databricks postgres create-synced-table \
  workspace.semantic.zip_hotspots_metrics \
  --json '{
    "spec": {
      "branch": "projects/rdu-metrics-api/branches/production",
      "postgres_database": "databricks_postgres",
      "source_table_full_name": "workspace.semantic.zip_hotspots_metrics_snapshot",
      "primary_key_columns": ["zip"],
      "scheduling_policy": "TRIGGERED"
    }
  }' \
  -p DEFAULT
```

**How this schema was actually resolved**, since it took several wrong
guesses to get here and the path matters for the next Beta API this
happens with: the `--json` payload is the `SyncedTable` object directly
(`spec` at the top level, no extra wrapper) — the resource name/ID goes in
the positional argument, not the JSON body. `spec.branch` needs the
**full** resource path (`projects/{id}/branches/{branch_id}`, not just
`production`) or the API rejects it with "expects
'projects/{project_id}/branches/{branch_id}' format". `spec.postgres_database`
is the plain Postgres database name (`databricks_postgres`), not a
resource path. None of this was guessable from the CLI's own `-h` output
or from official docs pages this session could actually fetch (several
returned only a title, JS-rendered) — what actually resolved it was
installing `databricks-sdk` locally (`pip install databricks-sdk`) and
introspecting the real dataclass:
```python
from databricks.sdk.service import postgres
import dataclasses, inspect
[f.name for f in dataclasses.fields(postgres.SyncedTableSyncedTableSpec)]
inspect.signature(postgres.PostgresAPI.create_synced_table)
```
That's the reliable fallback for any Beta Lakebase API command whose
`--json` schema isn't otherwise discoverable — don't keep guessing against
the live API once a couple of attempts fail; introspect the SDK instead.

Check status:
```bash
databricks postgres get-synced-table synced_tables/workspace.semantic.zip_hotspots_metrics -p DEFAULT
```
Target state: `SYNCED_TABLE_ONLINE_NO_PENDING_UPDATE` (Triggered mode's
"synced and idle" state). Failure states to watch for:
`SYNCED_TABLE_OFFLINE_FAILED`, `SYNCED_TABLE_ONLINE_PIPELINE_FAILED`.

No `[verify]` flag needed here anymore — the schema above is confirmed
working, not guessed (see "how this schema was actually resolved" above).

**Sync mode: Triggered**, not Continuous (wrong given weekly source
cadence — burns quota keeping near-real-time freshness nothing needs) or
Snapshot (simpler, but this session didn't confirm a clean resync command
for it). Run this sync step as the job task immediately after Phase 1/2's
snapshot task — don't give it an independent schedule.

**Checkpoint:** `get-synced-table` reports `detailed_state:
SYNCED_TABLE_ONLINE_NO_PENDING_UPDATE` — confirmed live, sync completed in
~7 seconds. Cross-checking the actual row count between the Delta source
and the Postgres-side table happens naturally in Phase 5's GET test.

**UI path not available on this account — use the CLI for this step,
full stop.** Three things were tried and none held up: (1) the official
docs' Catalog Explorer steps
(docs.databricks.com/aws/en/oltp/projects/reverse-etl) didn't match what
was actually visible on this workspace; (2) the Free Edition limitations
page doesn't mention synced tables either way; (3) the "Previews" menu
this kind of Beta feature is normally gated behind
(username → Previews, per docs.databricks.com/aws/en/admin/workspace-settings/manage-previews)
**doesn't even appear** in this account's UI. That third result is the
most telling — it points to a genuine Free Edition UI gap (the CLI/API
shipped, the UI wizard hasn't, and there's no toggle to find because
there's nothing to toggle), consistent with the same CLI-works/UI-doesn't
asymmetry seen elsewhere on this tier (catalog creation was the reverse
case — UI-only, CLI failed).

**Use the CLI command in the block above**
(`databricks postgres create-synced-table`) — confirmed to exist on this
account and the same tool that already worked for project creation and
endpoint resizing.

Documented UI steps, kept for reference in case they match a different
workspace version:
1. **Enable CDF**: **SQL Editor** → new query → paste the
   `ALTER TABLE ... SET TBLPROPERTIES` statement above → pick a Databricks
   SQL warehouse → **Run**.
2. **Catalog** → `workspace` → `semantic` →
   `zip_hotspots_metrics_snapshot` → open the table's detail page.
3. Look for a **Create** button → **Synced table** option.
4. If found, the dialog should prompt for: synced table name, **Database
   type** = **Lakebase Serverless (Autoscaling)**, **Sync mode** =
   **Triggered**, project/branch/database, and a **Primary key** field to
   verify (`zip`).
5. If step 3's **Create** button isn't there, or has no **Synced table**
   option, stop guessing at the UI and use the CLI path instead.

---

## Phase 5 — Data API access

**Enabling it needs the UI, confirmed** — the Data API's enable step and
its URL are UI-only per official docs
(learn.microsoft.com/en-us/azure/databricks/oltp/projects/data-api), with
no CLI/API alternative documented. Unlike the earlier phases, this one
actually worked: **Lakebase project page → Data API tab → Enable Data
API** produced a real URL —
`https://<endpoint-host>/api/2.0/workspace/<workspace_id>/rest/<postgres_database>`
(e.g. `.../rest/databricks_postgres`). Note this is *derivable*, contrary
to what the docs implied — it's just the endpoint's own host (from
`list-endpoints`) plus your workspace ID plus the Postgres database name.

**Native login is off on this project** (`enable_pg_native_login: false`,
confirmed via `get-project`). The `CREATE ROLE ... LOGIN` SQL from earlier
drafts of this doc does not work here — roles must be OAuth-backed,
created via `databricks postgres create-role`, not raw SQL. Confirmed
working, using a dedicated service principal as the consumer identity:

```bash
# 1. Create the consumer identity
databricks service-principals create --display-name "lakebase-api-consumer" -p DEFAULT
databricks service-principal-secrets-proxy create <SP_ID> -p DEFAULT
# note applicationId and secret

# 2. Register it as a Postgres role (OAuth-backed, not native login)
databricks postgres create-role projects/rdu-metrics-api/branches/production \
  --role-id <SP_APPLICATION_ID> \
  --json '{"spec": {"identity_type": "SERVICE_PRINCIPAL", "postgres_role": "<SP_APPLICATION_ID>", "auth_method": "LAKEBASE_OAUTH_V1"}}' \
  -p DEFAULT
# confirmed: role created with bypassrls/createdb/createrole all false — least privilege by default
```

**Grant `SELECT`, connecting as an already-privileged identity** — the
project owner's role already has `DATABRICKS_SUPERUSER` membership by
default (confirmed via `list-roles`), so use your own identity to grant
the new role access, not the new role itself:

```bash
pip install psycopg2-binary
```
```python
import psycopg2
token = ...  # from `databricks postgres generate-database-credential
             # projects/rdu-metrics-api/branches/production/endpoints/primary -p DEFAULT`

conn = psycopg2.connect(
    host="<endpoint-host-from-list-endpoints>",
    port=5432, dbname="databricks_postgres",
    user="<your-databricks-email>", password=token, sslmode="require",
)
conn.autocommit = True
cur = conn.cursor()
cur.execute('GRANT USAGE ON SCHEMA semantic TO "<SP_APPLICATION_ID>"')
cur.execute('GRANT SELECT ON semantic.zip_hotspots_metrics TO "<SP_APPLICATION_ID>"')
# Deliberately no INSERT/UPDATE/DELETE — Reverse ETL owns this table;
# any write via the Data API would be silently overwritten on the next sync.
```

**Real, important correction: the synced table's schema is `semantic`,
not `public`** — it mirrors the source Unity Catalog schema name, not a
default `public` schema. Confirmed by listing `information_schema.tables`
directly; row count matched the Delta source exactly (736 = 736).

**Getting an OAuth token for the service principal** (client credentials
grant, no browser needed):

```bash
curl -X POST "https://<workspace-host>/oidc/v1/token" \
  -u "<SP_APPLICATION_ID>:<SP_SECRET>" \
  -d "grant_type=client_credentials&scope=all-apis"
# use the returned access_token as the Bearer token below
```

**Checkpoint reached, Data API call itself unresolved.** Everything above
is confirmed working — sync, grants, both a user's and a service
principal's OAuth tokens accepted by the server (structured PostgREST
errors come back, not auth failures). What's **not** resolved: the exact
URL path / schema-exposure convention this account's Data API proxy
expects. Every combination tried
(`$DATA_API_URL/semantic/zip_hotspots_metrics`,
`Accept-Profile: semantic` header with `/zip_hotspots_metrics`, and
several more) returned `PGRST106 "Invalid schema: unknown"` — with the
hint suspiciously echoing back whatever schema name was just requested,
which looks like a broken hint template rather than real validation.
Hitting the bare base URL with no trailing slash produced a *different*
error (`PGRST205`, "could not find the table" — using the whole proxy
path as a table lookup), confirming the routing behaves inconsistently
rather than just rejecting an invalid name.

**Confirmed, not just suspected: the hint is not real validation
feedback.** Also tried `schema.table` and `catalog.schema.table` as
single dotted path segments (matching the naming convention used
everywhere else in this API, e.g. the synced table's own resource name)
— both rejected identically, with the hint again exactly echoing back
whatever was sent (`semantic.zip_hotspots_metrics`, then
`workspace.semantic.zip_hotspots_metrics`). Four structurally different,
individually reasonable URL shapes all produced the same "echo the input
back as the only exposed schema" behavior. That rules out "wrong naming
convention" as the explanation — this is a genuine bug or platform
limitation on this tier, not a syntax this session hasn't guessed yet.
**Stop here; raise with Databricks support or the community forum**
rather than continuing to try URL variations.

---

## Phase 6 — Teardown

```bash
databricks postgres delete-synced-table workspace.semantic.zip_hotspots_metrics -p DEFAULT
databricks postgres delete-project projects/rdu-metrics-api -p DEFAULT
```

```sql
DROP TABLE IF EXISTS workspace.semantic.zip_hotspots_metrics_snapshot
```

Also remove the job task added in Phase 2.

**In the Databricks UI instead:**
1. Lakebase project page → **Synced Tables** tab → find
   `zip_hotspots_metrics` → delete.
2. Same project page → **Settings** → **Delete project**.
3. **Catalog** → `workspace` → `semantic` →
   `zip_hotspots_metrics_snapshot` → **⋮** menu → **Delete**.
4. **Workflows** → **RDU Medallion Pipeline** → **Tasks** tab → select
   `52_semantic_zip_hotspots_snapshot` → remove it, or remove the task
   from `resources/medallion_pipeline_job.yml` and `databricks bundle
   deploy` again — the bundle is the source of truth for this job, so a
   UI-only removal will be overwritten by the next deploy unless the YAML
   is updated too.

---

## Troubleshooting notes

- **`create-project` or `create-synced-table` times out** — these are
  long-running operations; use `--no-wait` and poll with `get-operation`
  rather than assuming failure.
- **Synced table row count doesn't match source** — confirm the sync mode
  actually ran (Triggered syncs don't happen automatically on a timer;
  something has to trigger them — likely the job task from Phase 2/4, or
  a manual re-run of the create/update command; this wasn't fully
  resolved live in this session, treat as a `[verify]` if it comes up).
- **`permission denied for schema public`** — same failure mode
  documented in the Lakebase skill for Databricks Apps: whichever
  identity created the synced table owns its schema; a different
  identity (e.g. your personal login vs. the sync pipeline's identity)
  won't have access without an explicit grant.
- **Data API returns 404 for a table that exists in Postgres** — the
  schema/table may not be exposed to PostgREST yet; check the project's
  Data API configuration in the UI per the Phase 5 verify flag.
- **Cold-start delay on first request after scale-to-zero** — compute
  wakes in roughly 100ms per the Lakebase skill's docs; implement retry
  logic in any real client rather than treating the first failed request
  as an error.
