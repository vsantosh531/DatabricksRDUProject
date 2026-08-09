# Semantic Layer Execution Runbook

Every command needed to stand up the semantic layer on this Databricks Free
Edition workspace, in the order they must run. Companion to
`docs/semantic_layer_platform_architecture.md` (the design this implements)
and `docs/semantic_layer_explained_simply.md` (the plain-language version).

Run these yourself, phase by phase — each phase depends on the state the
previous one created, so don't skip ahead. Lettered sub-phases (2a, 3a, 5a)
don't change the main sequence — they're checkpoints that prove the *why*
behind the phase before it, not new dependencies.

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
- Phases 5 and 5a have no CLI commands by design — they're done in the
  Databricks UI.
- Replace the literal warehouse ID (`95643b36f69a05e2`) with your own from
  the Phase 0 `warehouses list` output if it differs.
- Catalogs are named `rdu_dev` and `rdu_prod` throughout — project-specific
  names rather than generic `dev`/`prod`, matching this project's existing
  `bronze`/`silver`/`gold` naming under the `workspace` catalog.

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
databricks catalogs create rdu_dev  -p DEFAULT
databricks catalogs create rdu_prod -p DEFAULT

# Create the semantic schema inside each — this is where metric views live
databricks schemas create semantic rdu_dev  -p DEFAULT
databricks schemas create semantic rdu_prod -p DEFAULT

# Verify both exist
databricks catalogs list -p DEFAULT
databricks schemas list rdu_dev  -p DEFAULT
databricks schemas list rdu_prod -p DEFAULT
```

> **`catalogs create` fails on this tier — do it in the UI instead.** Two
> CLI errors show up in sequence: first "Metastore storage root URL does not
> exist," and even passing `--storage-root` explicitly (reusing the value
> from `databricks catalogs get workspace -p DEFAULT`) hits a second wall:
> "Please use the UI to create a catalog with Default Storage." This
> metastore requires Default Storage catalogs to be created through the UI
> — there's no CLI override. Create both catalogs there instead:
> 1. Open the workspace in a browser → **Catalog** (left sidebar) →
>    **Create Catalog**.
> 2. Name it `rdu_dev`, leave Default Storage selected, click **Create**.
> 3. Repeat for `rdu_prod`.
>
> Already created them as `dev`/`prod`? Rename in place instead of
> recreating:
> ```bash
> databricks catalogs update dev  --new-name rdu_dev  -p DEFAULT
> databricks catalogs update prod --new-name rdu_prod -p DEFAULT
> ```
>
> Once both exist, switch back to the CLI for everything else in this
> runbook — schemas, grants, and metric view deploys all work fine from the
> terminal; it's only catalog creation itself that's UI-only here.

**Checkpoint:** `rdu_dev.semantic` and `rdu_prod.semantic` both exist and
are empty.

---

## Phase 2 — Author and deploy your first governed metric view

```bash
# The warehouse is likely stopped — start it before running any SQL
databricks warehouses start <YOUR_WAREHOUSE_ID> -p DEFAULT
```

Write the metric view to a local file named `dev_metric.sql`:

```sql
CREATE OR REPLACE VIEW rdu_dev.semantic.zip_hotspots_metrics
WITH METRICS
LANGUAGE YAML
AS $$
version: 1.1
comment: "ZIP-level quarterly market hotspot metrics"
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
  "SELECT zip_name, MEASURE(avg_days_on_market) AS avg_dom, MEASURE(total_active_listings) AS active FROM rdu_dev.semantic.zip_hotspots_metrics GROUP BY ALL ORDER BY active DESC LIMIT 10"

# Confirm the top-level comment landed on the view object itself
databricks tables get rdu_dev.semantic.zip_hotspots_metrics -p DEFAULT
# look for "comment": "ZIP-level quarterly market hotspot metrics" in the output
```

Once the query returns correct results, repeat the same `CREATE OR REPLACE`
against `rdu_prod.semantic.zip_hotspots_metrics` (swap `rdu_dev` for
`rdu_prod` in the SQL file, submit again).

**Checkpoint:** `MEASURE()` queries against both `rdu_dev.semantic` and
`rdu_prod.semantic` return correct, matching numbers, and the view's comment
is visible via `tables get`.

---

## Phase 2a — Prove why a metric view beats a plain view

This is the actual point of everything above — don't skip it. A metric view
is only worth the extra ceremony if its measures stay correct no matter what
grain you query at. Prove that, then prove it agrees with hand-written SQL.

Save this as `grain_check.sql`:

```sql
SELECT quarter_start,
       MEASURE(price_reduction_rate) AS price_reduction_rate,
       MEASURE(total_active_listings) AS active
FROM rdu_dev.semantic.zip_hotspots_metrics
GROUP BY ALL
ORDER BY quarter_start
```

Save this as `manual_check.sql` — the same ratio, hand-written directly
against the source gold table, at the same grain:

```sql
SELECT quarter_start,
       SUM(price_reduced_count) / NULLIF(SUM(active_listing_count), 0) AS price_reduction_rate_manual,
       SUM(active_listing_count) AS active_manual
FROM workspace.gold.zip_hotspots
WHERE is_current = true
GROUP BY quarter_start
ORDER BY quarter_start
```

```bash
# Query the metric view at a totally different grain than Phase 2 used
databricks experimental aitools tools query --warehouse <YOUR_WAREHOUSE_ID> -p DEFAULT --file grain_check.sql

# Now the naive hand-written equivalent — this is a parity test, done by eye
databricks experimental aitools tools query --warehouse <YOUR_WAREHOUSE_ID> -p DEFAULT --file manual_check.sql
```

**Checkpoint:** `price_reduction_rate` (metric view) and
`price_reduction_rate_manual` (hand-written) match, row for row, even though
Phase 2 grouped by `zip_name` and this grouped by `quarter_start` instead.
That's the property metric views exist to guarantee — a plain view with a
baked-in `GROUP BY` couldn't safely re-aggregate like this.

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

## Phase 3a — Verify the service principal actually works

A credential you haven't tested is a credential you don't actually have yet.
Prove it locally first, then prove it works from CI — don't wire it into a
real deploy pipeline on faith.

**Local check**, without touching `~/.databrickscfg`:

```bash
export DATABRICKS_HOST="<your-workspace-url>"
export DATABRICKS_CLIENT_ID="<applicationId from Phase 3>"
export DATABRICKS_CLIENT_SECRET="<secret from Phase 3>"

databricks current-user me
# the output should identify the service principal, not your personal user

unset DATABRICKS_HOST DATABRICKS_CLIENT_ID DATABRICKS_CLIENT_SECRET
```

**CI check** — save this as `.github/workflows/verify-sp.yml`:

```yaml
name: verify-sp
on:
  workflow_dispatch: {}

jobs:
  verify:
    runs-on: ubuntu-latest
    steps:
      - name: Install Databricks CLI
        run: |
          curl -fsSL https://raw.githubusercontent.com/databricks/setup-cli/main/install.sh | sh

      - name: Verify service principal auth
        env:
          DATABRICKS_HOST: ${{ secrets.DATABRICKS_HOST }}
          DATABRICKS_CLIENT_ID: ${{ secrets.DATABRICKS_CLIENT_ID }}
          DATABRICKS_CLIENT_SECRET: ${{ secrets.DATABRICKS_CLIENT_SECRET }}
        run: databricks current-user me
```

Commit and push it, then run it manually: repo → **Actions** tab →
**verify-sp** → **Run workflow**.

**Checkpoint:** the workflow run succeeds and its log shows the service
principal's identity — proof the credential works from CI, before you ever
depend on it for a real deploy.

---

## Phase 4 — Access control

```bash
# Create the consumer group
databricks groups create --display-name semantic-consumers -p DEFAULT

# Grant it access to the catalog and schema (hierarchy: catalog -> schema -> view)
databricks grants update catalog rdu_prod --json '{
  "changes": [{"principal": "semantic-consumers", "add": ["USE_CATALOG"]}]
}' -p DEFAULT

databricks grants update schema rdu_prod.semantic --json '{
  "changes": [{"principal": "semantic-consumers", "add": ["USE_SCHEMA"]}]
}' -p DEFAULT

databricks grants update table rdu_prod.semantic.zip_hotspots_metrics --json '{
  "changes": [{"principal": "semantic-consumers", "add": ["SELECT"]}]
}' -p DEFAULT

# Read back the full grant tree you just built, one level at a time
databricks grants get catalog rdu_prod -p DEFAULT
databricks grants get schema rdu_prod.semantic -p DEFAULT
databricks grants get table rdu_prod.semantic.zip_hotspots_metrics -p DEFAULT

# Confirm the group can query the view but NOT the underlying gold table:
databricks grants get table workspace.gold.zip_hotspots -p DEFAULT
# semantic-consumers should NOT appear in this output
```

**Checkpoint:** the three `grants get` calls show `semantic-consumers` with
exactly `USE_CATALOG` → `USE_SCHEMA` → `SELECT`, and it's absent entirely
from the gold table's grants.

---

## Phase 5 — Genie (manual, via the workspace UI)

No CLI commands — this is done in the Databricks UI:

1. Go to **New → Genie Space**.
2. Attach `rdu_prod.semantic.zip_hotspots_metrics` as the data source.
3. Add 3–5 curated sample questions (e.g. "which ZIP has the highest active
   listings this quarter?").
4. Test each question and confirm the answer matches a manual query.

**Checkpoint:** the Genie space answers your curated questions correctly.

---

## Phase 5a — AI/BI Dashboard (the second consumption surface)

This project's whole design point is one governed definition serving two
surfaces that agree. Genie alone doesn't prove that — you need a second
surface reading the same view.

1. Go to **New → Dashboard**.
2. Add `rdu_prod.semantic.zip_hotspots_metrics` as a dataset.
3. Add one visual — e.g. a bar chart of `MEASURE(total_active_listings)` by
   `zip_name`.
4. Ask Genie (Phase 5) the equivalent question and compare the number it
   gives you against the dashboard tile.

**Checkpoint:** the dashboard tile and the Genie answer show the *same*
number for the same question — the actual payoff of a governed semantic
layer, seen directly rather than taken on faith.

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

**Checkpoint:** you can see your own Phase 2/2a/5a queries in the
audit/query history output — proof the system tables are live and usable.

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

## Phase 8 — Cleanup / teardown

Nothing above tears itself down. On a quota-bound tier, clean up what you're
not actively using — and knowing how to undo each phase is what makes it
safe to redo one that went wrong.

```bash
# Stop burning quota — the warehouse has been running since Phase 2
databricks warehouses stop <YOUR_WAREHOUSE_ID> -p DEFAULT

# Drop the metric views
databricks experimental aitools tools query --warehouse <YOUR_WAREHOUSE_ID> -p DEFAULT \
  "DROP VIEW IF EXISTS rdu_dev.semantic.zip_hotspots_metrics"
databricks experimental aitools tools query --warehouse <YOUR_WAREHOUSE_ID> -p DEFAULT \
  "DROP VIEW IF EXISTS rdu_prod.semantic.zip_hotspots_metrics"

# Drop the schemas and catalogs
databricks schemas delete rdu_dev.semantic  -p DEFAULT
databricks schemas delete rdu_prod.semantic -p DEFAULT
databricks catalogs delete rdu_dev  -p DEFAULT
databricks catalogs delete rdu_prod -p DEFAULT

# Remove the access-control group
databricks groups delete <GROUP_ID> -p DEFAULT

# Remove the CI service principal (also invalidates its secret)
databricks service-principals delete <SERVICE_PRINCIPAL_ID> -p DEFAULT
```

Also remove manually, in the GitHub UI: the `DATABRICKS_CLIENT_ID` /
`DATABRICKS_CLIENT_SECRET` repo secrets (Settings → Secrets and variables →
Actions), and delete the Genie space and dashboard from Phases 5/5a if you
don't want them lingering. The `verify-sp.yml` workflow is harmless to leave
— it does nothing unless manually triggered.

**Checkpoint:** `databricks catalogs list -p DEFAULT` no longer shows
`rdu_dev`/`rdu_prod`, and the warehouse shows `STOPPED`.

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
