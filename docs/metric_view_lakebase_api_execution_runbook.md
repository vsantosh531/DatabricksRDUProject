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

**In the Databricks UI instead:**
1. Left sidebar → **Lakebase** (or under a **Compute**/**Postgres**
   grouping, depending on workspace version — Lakebase is a newer, Beta
   product area and its exact nav placement isn't something this session
   verified live) → **Create project** / **New database**.
2. Project ID: `rdu-metrics-api`. Display name: `RDU Metrics API`. Create.
3. This auto-creates a `production` branch and a `primary` endpoint —
   open the project page, find the **Compute**/**Endpoints** tab.
4. Edit the primary endpoint → set both **Min Compute Units** and **Max
   Compute Units** to `0.5` → Save.

**[verify]** the exact left-nav label — try "Lakebase" first; if not
present, check under a general "Compute" or "Data" section.

---

## Phase 4 — Sync the snapshot table into Lakebase

Enable Change Data Feed on the source table (required for Triggered sync):

```sql
ALTER TABLE workspace.semantic.zip_hotspots_metrics_snapshot
SET TBLPROPERTIES (delta.enableChangeDataFeed = true)
```

```bash
databricks postgres create-synced-table \
  workspace.semantic.zip_hotspots_metrics \
  --json '{
    "spec": {
      "source_table_full_name": "workspace.semantic.zip_hotspots_metrics_snapshot",
      "target_endpoint": "projects/rdu-metrics-api/branches/<BRANCH_ID>/endpoints/<ENDPOINT_ID>",
      "primary_key_columns": ["zip"]
    }
  }' \
  --profile DEFAULT
```

**[verify]** the exact `spec` field names above before running for real —
`create-synced-table -h` confirms the command and its positional
`SYNCED_TABLE_ID` (`{catalog}.{schema}.{table}` — this becomes both a UC
entity and the Postgres table name), but did not enumerate the full
`--json` spec schema in this session. If the fields above are rejected,
check `databricks api get /api/2.0/... ` schema docs or the Databricks
REST API reference for the exact `SyncedTableSpec` shape rather than
guessing further field names.

**Sync mode: Triggered**, not Continuous (wrong given weekly source
cadence — burns quota keeping near-real-time freshness nothing needs) or
Snapshot (simpler, but this session didn't confirm a clean resync command
for it). Run this sync step as the job task immediately after Phase 1/2's
snapshot task — don't give it an independent schedule.

**Checkpoint:** row count in the Postgres-side synced table matches the
Delta source table's row count (query both and compare).

**In the Databricks UI instead:**
1. **Enable CDF**: **SQL Editor** (left sidebar) → new query → paste the
   `ALTER TABLE ... SET TBLPROPERTIES` statement above → pick a warehouse
   → **Run**.
2. **Create the synced table**: either from **Catalog** →
   `zip_hotspots_metrics_snapshot` → an action menu offering "Sync to
   Lakebase" / "Create synced table", or from the Lakebase project page →
   a **Tables** or **Synced Tables** tab → **Create synced table** /
   **Sync a table**. Either entry point should prompt for: source table
   (`workspace.semantic.zip_hotspots_metrics_snapshot`), target
   project/database, primary key column (`zip`), and sync mode — pick
   **Triggered**, same reasoning as the CLI path (Continuous wastes quota
   on data that only changes weekly; Snapshot's resync story is unclear).
3. Create, then wait for the initial sync to complete (shown as a status
   on the synced table's page).

**[verify]** the exact entry point (Catalog Explorer table menu vs.
Lakebase project page) — this session couldn't confirm which one this
workspace version surfaces; check both.

---

## Phase 5 — Data API access

No dedicated CLI command enables the Data API — confirmed via
`databricks postgres -h`, which lists infrastructure management commands
only and explicitly says "to query or modify data, use the Data API or
direct SQL connections," implying it's available by default once the
project/synced table exist. **[verify]** in the project's UI page whether
any toggle is needed to activate it, since this session found no CLI
command for it either way.

Create a read-only consumer role:

```bash
databricks postgres create-role -h   # confirm exact syntax before running
```

Then, connected via `psql` or the SQL editor (using
`generate-database-credential` for a short-lived OAuth token per the
Lakebase skill's connectivity reference):

```sql
CREATE ROLE api_consumer LOGIN;
GRANT USAGE ON SCHEMA public TO api_consumer;
GRANT SELECT ON zip_hotspots_metrics TO api_consumer;
-- Deliberately no INSERT/UPDATE/DELETE — Reverse ETL owns this table;
-- any write via the Data API would be silently overwritten on the next sync.
```

Test both directions:

```bash
# Should succeed and return rows
curl -H "Authorization: Bearer $TOKEN" \
  "$DATA_API_URL/public/zip_hotspots_metrics?zip=eq.27601"

# Should be REJECTED — this proves the write-lockout is real, not assumed
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"zip": "99999", "zip_name": "test"}' \
  "$DATA_API_URL/public/zip_hotspots_metrics"
```

**Checkpoint:** the GET returns the expected row, and the POST is rejected
with a permissions error — not silently accepted.

**In the Databricks UI instead:**
1. **Enable the Data API**: Lakebase project page → a **Data API** tab —
   toggle it on if there's a switch, or it may simply display an endpoint
   URL once the project exists (this session couldn't confirm which, per
   the CLI phase's same open question). Copy the shown URL as
   `$DATA_API_URL`.
2. **Create the role and grants**: open **SQL Editor**, connect it to the
   Lakebase database (workspaces with Lakebase typically let you pick a
   Postgres/Lakebase connection alongside SQL warehouses in the editor's
   connection dropdown), and run the `CREATE ROLE` / `GRANT` statements
   there instead of via `psql`.
3. **Testing the endpoint** stays outside the Databricks UI either way —
   `curl`, a browser fetch, or an API client like Postman/Insomnia. There
   isn't a Databricks-UI way to send a raw HTTP request to your own Data
   API; this step is identical whether you did Phases 1–4 via CLI or UI.

**[verify]** whether the Data API tab requires an explicit enable action
or is on by default — same unresolved question as the CLI phase.

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
