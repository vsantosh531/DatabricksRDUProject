# Semantic Layer Execution Runbook

Every command needed to stand up the semantic layer on this Databricks Free
Edition workspace, in the order they must run. Companion to
`docs/semantic_layer_platform_architecture.md` (the design this implements)
and `docs/semantic_layer_explained_simply.md` (the plain-language version).

Run these yourself, phase by phase — each phase depends on the state the
previous one created, so don't skip ahead.

---

## Prerequisites

- Databricks CLI installed and on `PATH` (`databricks --version`).
- An authenticated profile in `~/.databrickscfg` (`databricks auth profiles`
  — this runbook uses `-p DEFAULT` throughout; substitute your profile name
  if different).
- You're a workspace admin, or have `CREATE_CATALOG`/`CREATE_SCHEMA`
  privilege on the metastore.
- A SQL warehouse exists in the workspace (`databricks warehouses list`).

## Where to run these commands

Run every command in this runbook from a **terminal on your own computer**
— not inside a Databricks notebook, not the Databricks web UI, and not
GitHub Actions. Any terminal app works (Terminal.app or iTerm on macOS,
Windows Terminal/WSL on Windows). You don't need to `cd` into this repo
first — none of Phase 0's commands touch local files (Phase 2 is the first
one that writes a local `.sql` file, and even then it can live anywhere).

On this project's machine, the CLI is already installed and authenticated —
confirmed via `databricks --version` and `databricks auth profiles`, with a
valid `DEFAULT` profile pointing at the workspace. If that's your machine
too, open a terminal and start pasting Phase 0 commands right away.

Setting up fresh on a different machine instead:
1. Install the CLI: `curl -fsSL https://raw.githubusercontent.com/databricks/setup-cli/main/install.sh | sh` (or `brew install databricks` on macOS).
2. Authenticate: `databricks auth login --host <your-workspace-url>` — opens
   a browser to log in and writes a profile into `~/.databrickscfg`.
3. Confirm it worked: `databricks auth profiles` should show your profile
   with `Valid: YES`.

## How to run these instructions

- Run commands **top to bottom, one at a time** — later phases reference
  objects (catalogs, warehouse IDs, service principal IDs) created by
  earlier ones.
- Every command below includes `-p DEFAULT`. If your profile has a
  different name, replace it everywhere.
- Some commands print values you need later (a `statement_id`, a service
  principal's `id`/`applicationId`, an OAuth `secret`). **Copy these down
  as you go** — several are shown only once.
- Commands are safe to re-run if they fail partway (`create` commands will
  simply error "already exists" rather than duplicate anything) — re-running
  is the normal way to recover from a typo, not something to avoid.
- Phase 5 has no CLI commands by design — it's done in the Databricks UI.
- Replace the literal warehouse ID (`95643b36f69a05e2`) with your own from
  the Phase 0 `warehouses list` output if it differs.

---

## Phase 0 — Verify what your workspace actually supports

```bash
# Confirm your identity and group membership (are you admin?)
databricks current-user me -p DEFAULT

# List existing catalogs — see what's already there before creating anything
databricks catalogs list -p DEFAULT

# List SQL warehouses — note the warehouse ID, you'll need it below
databricks warehouses list -p DEFAULT

# Check whether system schemas (usage/audit/billing tracking) are enabled
databricks schemas list system -p DEFAULT

# See what's already in your main working catalog
databricks schemas list workspace -p DEFAULT

# Check if service principals are supported (needed later for CI auth)
databricks service-principals list -p DEFAULT

# Check existing groups (needed later for access control)
databricks groups list -p DEFAULT

# List your gold tables — these are the metric view sources
databricks tables list workspace gold -p DEFAULT

# Inspect any existing metric view to learn from its structure
databricks tables get workspace.gold.zip_hotspots_metric_view -p DEFAULT
```

**Checkpoint:** you should know — your admin status, your warehouse ID,
whether system schemas are enabled, and the names of your gold tables —
before moving on.

---

## Phase 1 — Catalog foundation (simulated dev/prod environments)

```bash
# Create the two environment catalogs
databricks catalogs create dev  -p DEFAULT
databricks catalogs create prod -p DEFAULT

# Create the semantic schema inside each — this is where metric views live
databricks schemas create semantic dev  -p DEFAULT
databricks schemas create semantic prod -p DEFAULT

# Verify both exist
databricks catalogs list -p DEFAULT
databricks schemas list dev  -p DEFAULT
databricks schemas list prod -p DEFAULT
```

**Checkpoint:** `dev.semantic` and `prod.semantic` both exist and are empty.

---

## Phase 2 — Author and deploy your first governed metric view

```bash
# The warehouse is likely stopped — start it before running any SQL
databricks warehouses start <YOUR_WAREHOUSE_ID> -p DEFAULT
```

Write the metric view to a local file named `dev_metric.sql`:

```sql
CREATE OR REPLACE VIEW dev.semantic.zip_hotspots_metrics
WITH METRICS
LANGUAGE YAML
AS $$
version: 1.1
source: workspace.gold.zip_hotspots
filter: is_current = true
dimensions:
  - name: zip
    expr: zip
    comment: "5-digit ZIP code"
  - name: zip_name
    expr: zip_name
    comment: "Human-readable ZIP area name"
  - name: quarter_start
    expr: quarter_start
    comment: "Calendar quarter start date"
measures:
  - name: avg_days_on_market
    expr: AVG(median_dom)
    comment: "Average median days-on-market"
  - name: total_active_listings
    expr: SUM(active_listing_count)
    comment: "Total active listings in the period"
  - name: price_reduction_rate
    expr: "SUM(price_reduced_count) / NULLIF(SUM(active_listing_count), 0)"
    comment: "Share of active listings with a price reduction"
$$
```

```bash
# Deploy it (async — returns a statement_id immediately)
databricks experimental aitools tools statement submit --file dev_metric.sql --warehouse <YOUR_WAREHOUSE_ID> -p DEFAULT

# Check the deploy result using the statement_id it returned
databricks experimental aitools tools statement get <STATEMENT_ID> -p DEFAULT

# Query it to prove MEASURE() works — the whole point of a metric view
databricks experimental aitools tools query --warehouse <YOUR_WAREHOUSE_ID> -p DEFAULT \
  "SELECT zip_name, MEASURE(avg_days_on_market) AS avg_dom, MEASURE(total_active_listings) AS active FROM dev.semantic.zip_hotspots_metrics GROUP BY ALL ORDER BY active DESC LIMIT 10"
```

Once the query returns correct results, repeat the same `CREATE OR REPLACE`
against `prod.semantic.zip_hotspots_metrics` (swap `dev` for `prod` in the
SQL file, submit again).

**Checkpoint:** `MEASURE()` queries against both `dev.semantic` and
`prod.semantic` return correct, matching numbers.

---

## Phase 3 — CI foundation (a dedicated identity for automated deploys)

```bash
# Create a service principal instead of using your personal login for CI
databricks service-principals create --display-name "semantic-layer-ci" -p DEFAULT
# note the returned "id" (numeric) and "applicationId" (UUID)

# Generate an OAuth secret for it — this becomes your CI credential
databricks service-principal-secrets-proxy create <SERVICE_PRINCIPAL_ID> -p DEFAULT
# note the returned "secret" value — shown only once, save it now
```

In the GitHub UI (not the CLI): go to **Settings → Secrets and variables →
Actions** on your repo, and add:
- `DATABRICKS_CLIENT_ID` = the `applicationId` from above
- `DATABRICKS_CLIENT_SECRET` = the `secret` from above

**Checkpoint:** two new GitHub repo secrets exist, distinct from your
personal `DATABRICKS_TOKEN`.

---

## Phase 4 — Access control

```bash
# Create the consumer group
databricks groups create --display-name semantic-consumers -p DEFAULT

# Grant it access to the catalog and schema (hierarchy: catalog -> schema -> view)
databricks grants update catalog prod --json '{
  "changes": [{"principal": "semantic-consumers", "add": ["USE_CATALOG"]}]
}' -p DEFAULT

databricks grants update schema prod.semantic --json '{
  "changes": [{"principal": "semantic-consumers", "add": ["USE_SCHEMA"]}]
}' -p DEFAULT

databricks grants update table prod.semantic.zip_hotspots_metrics --json '{
  "changes": [{"principal": "semantic-consumers", "add": ["SELECT"]}]
}' -p DEFAULT

# Confirm the group can query the view but NOT the underlying gold table:
databricks grants get table workspace.gold.zip_hotspots -p DEFAULT
# semantic-consumers should NOT appear in this output
```

**Checkpoint:** `semantic-consumers` has `SELECT` on the metric view and no
access at all to the source gold table.

---

## Phase 5 — Genie (manual, via the workspace UI)

No CLI commands — this is done in the Databricks UI:

1. Go to **New → Genie Space**.
2. Attach `prod.semantic.zip_hotspots_metrics` as the data source.
3. Add 3–5 curated sample questions (e.g. "which ZIP has the highest active
   listings this quarter?").
4. Test each question and confirm the answer matches a manual query.

**Checkpoint:** the Genie space answers your curated questions correctly.

---

## Phase 6 — Observability

```bash
# Explore what's actually in the audit log so far
databricks experimental aitools tools query --warehouse <YOUR_WAREHOUSE_ID> -p DEFAULT \
  "SELECT event_time, user_identity.email, action_name FROM system.access.audit ORDER BY event_time DESC LIMIT 20"

# Explore query history for anything hitting your new semantic schema
databricks experimental aitools tools query --warehouse <YOUR_WAREHOUSE_ID> -p DEFAULT \
  "SELECT statement_text, warehouse_id, total_duration_ms FROM system.query.history WHERE statement_text LIKE '%semantic%' ORDER BY start_time DESC LIMIT 20"
```

**Checkpoint:** you can see your own Phase 2 queries in the audit/query
history output — proof the system tables are live and usable.

---

## Phase 7 — Quota / compute usage check

```bash
databricks experimental aitools tools query --warehouse <YOUR_WAREHOUSE_ID> -p DEFAULT \
  "SELECT * FROM system.compute.warehouse_events ORDER BY event_time DESC LIMIT 20"
```

**Checkpoint:** you can see warehouse start/stop events, confirming this is
a viable place to watch compute usage against Free Edition's quota limits
going forward.

---

## Troubleshooting notes

- **`statement submit` never seems to finish** — it's async by design; poll
  with `statement get <id>` rather than expecting immediate output.
- **`grants update` errors "principal not found"** — the group/service
  principal name must match exactly what `groups list`/`service-principals
  list` shows; typos are the most common cause.
- **Warehouse queries fail with a timeout** — confirm the warehouse is
  `RUNNING`, not `STOPPED` (`databricks warehouses list -p DEFAULT`) before
  retrying.
- **`aitools` commands not found** — they're experimental CLI subcommands;
  confirm with `databricks experimental aitools tools --help`. If missing on
  your CLI version, fall back to the Databricks SQL Editor UI to run the
  same SQL manually.
