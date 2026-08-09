# Enterprise Semantic Layer Execution Runbook (Multi-Workspace)

Implementation and test steps for `docs/enterprise_semantic_layer_infra.md`
§14 (walking-skeleton, demo-first rollout), scoped to a concrete, simplified
topology: **two Databricks workspaces** (`dev`, `prod`), both bound to one
shared Unity Catalog metastore, and a **monorepo** in GitHub. No staging
workspace — CI/CD promotes directly from `dev` to `prod`, gated by required
review.

Companion to `docs/semantic_layer_execution_runbook.md` (the Free Edition,
single-workspace version this graduates from) and
`docs/semantic_layer_jira_backlog.md` (the story-level backlog these phases
implement — Epic codes below match it exactly).

## Verification status — read this first

Unlike the Free Edition runbook, **none of this was run against a live
environment** — this session only has access to a single Free Edition
workspace, and multi-workspace mechanics (catalog-to-workspace binding,
OIDC federation, a second workspace, cloud IAM) can't be exercised here.
Everything below uses documented, standard Terraform/Databricks/GitHub
Actions patterns, but a few specifics need confirming against current docs
before you run them for real — each is flagged inline with **[verify]**.
Don't treat those as settled; treat everything else as a solid starting
point.

One correction to carry over from the Free Edition runbook: the "catalog
creation fails, use the UI" issue documented there was specific to that
Free Edition metastore's storage configuration. On a standard paid account,
`terraform apply` creating a catalog with an explicit `storage_root` (or a
pre-configured default storage credential) typically works without the UI
detour — don't assume that limitation carries over here.

---

## Prerequisites

- Two Databricks workspaces already provisioned (`dev`, `prod`), both
  attached to the same regional Unity Catalog metastore — confirm with
  a metastore admin, not assumed.
- Databricks **account admin** access (account console), needed for
  catalog-to-workspace bindings and service-principal federation.
- Cloud provider IAM admin access (this project is AWS-hosted; substitute
  Azure AD app federated credentials or GCP workload identity federation
  if different — the pattern is equivalent, syntax isn't).
- Terraform installed, with the `databricks` provider configured for
  workspace-level auth against both `dev` and `prod`.
- GitHub repo admin access (Settings → Environments, Settings → Secrets).
- Databricks CLI installed, with profiles `dev` and `prod` configured in
  `~/.databrickscfg` pointing at each workspace.

## Repo layout (monorepo)

```
repo/
├── databricks.yml                    # DAB: dev + prod targets
├── semantic/
│   ├── housing/*.yaml                # pilot domain's metric views
│   └── finance/*.yaml                # second domain (Phase E6)
├── resources/
│   └── semantic_deploy_job.yml       # job task deploying semantic/*.yaml
├── terraform/
│   ├── providers.tf
│   ├── catalogs.tf                   # catalog + workspace binding + schemas
│   ├── grants.tf
│   └── service_principals.tf
├── tests/
│   └── test_metric_parity.py         # parity tests, wired into CI
└── .github/workflows/
    ├── semantic-layer-ci.yml         # validate -> dev -> prod
    └── verify-sp.yml
```

## Topology recap

- **One metastore**, already exists, both workspaces attached to it.
- **One catalog per workspace**: `dev` catalog bound only to the `dev`
  workspace; `prod` catalog bound only to the `prod` workspace
  (`isolation_mode = "ISOLATED"` plus an explicit workspace binding —
  this is the actual isolation boundary, not just a naming convention).
- **One schema per domain**, inside each catalog: `dev.housing`,
  `prod.housing`, later `dev.finance`, `prod.finance` — matches
  `docs/semantic_layer_platform_architecture.md` §5's "domain-owned schema
  inside a platform-owned catalog."

---

## Phase E0 — Walking skeleton demo *(critical path)*

**Goal:** prove the concept in the `dev` workspace before building anything
else — same purpose as the Free Edition runbook's Phase 0–2, just pointed
at a real dev workspace instead of a catalog inside one shared workspace.

**Implement:**
1. Confirm the `dev` profile works: `databricks current-user me -p dev`.
2. Create (or confirm) the `housing` schema in the `dev` catalog — via
   Terraform if the catalog already exists, or the UI if bootstrapping
   from nothing (see the verification-status note above on why the CLI
   path should work here even though it didn't on Free Edition).
3. Author one metric view YAML, same syntax as
   `docs/semantic_layer_execution_runbook.md` Phase 2, sourced from your
   actual gold table (e.g. `<gold_catalog>.gold.zip_hotspots`).
4. Deploy it via the stable **Statement Execution API**, not an
   experimental CLI helper — this is meant to model production practice:
   ```bash
   databricks api post /api/2.0/sql/statements --json @deploy_metric.json -p dev
   ```
   where `deploy_metric.json` wraps the `CREATE OR REPLACE VIEW ...` SQL
   and a `warehouse_id`. **[verify]** exact JSON payload shape against the
   current Statement Execution API docs.
5. Stand up one consumption surface (Genie space or AI/BI dashboard) in
   the `dev` workspace against `dev.housing.market_metrics`.

**Test:**
- Run a `MEASURE()` query against the deployed view; confirm correct
  output.
- Confirm the Genie/dashboard surface shows the same numbers.
- This is the artifact for the leadership demo from
  `docs/semantic_layer_north_star.md` — rehearse it once before showing it.

---

## Phase E1 — Topology hardening *(critical path)*

**Goal:** make the catalog isolation real, not assumed.

**Implement** (Terraform):
```hcl
resource "databricks_catalog" "dev" {
  name           = "dev"
  comment        = "Environment catalog: dev"
  isolation_mode = "ISOLATED"
}

resource "databricks_catalog" "prod" {
  name           = "prod"
  comment        = "Environment catalog: prod"
  isolation_mode = "ISOLATED"
}

resource "databricks_workspace_binding" "dev_binding" {
  securable_name = databricks_catalog.dev.name
  workspace_id   = var.dev_workspace_id
}

resource "databricks_workspace_binding" "prod_binding" {
  securable_name = databricks_catalog.prod.name
  workspace_id   = var.prod_workspace_id
}

resource "databricks_schema" "dev_housing" {
  catalog_name = databricks_catalog.dev.name
  name         = "housing"
}

resource "databricks_schema" "prod_housing" {
  catalog_name = databricks_catalog.prod.name
  name         = "housing"
}
```
**[verify]** the exact resource name (`databricks_workspace_binding` vs.
`databricks_catalog_workspace_binding`) and its required arguments against
the current `databricks` Terraform provider docs before applying — provider
resource names shift between versions.

**Test:**
- `terraform plan` shows the expected 6 resources; `terraform apply`
  succeeds.
- From the `dev` profile: `databricks catalogs list -p dev` — `prod` should
  **not** appear.
- From the `prod` profile: `databricks catalogs list -p prod` — `dev`
  should **not** appear.
- If either catalog is visible from the wrong workspace, the binding
  didn't take — stop here and fix it before continuing; nothing downstream
  is safe to build on an unverified isolation boundary.

---

## Phase E2 — Platform enablement *(critical path)*

**Goal:** the reusable bundle template and IaC that Phase E6's second
domain will scaffold from.

**Implement:**
- `databricks.yml` with two targets:
  ```yaml
  bundle:
    name: rdu-semantic-layer
  targets:
    dev:
      default: true
      workspace: {host: <dev-workspace-url>}
      variables: {catalog: dev}
    prod:
      workspace: {host: <prod-workspace-url>}
      variables: {catalog: prod}
  ```
- `resources/semantic_deploy_job.yml`: a job task running a small deploy
  script that reads every `semantic/<domain>/*.yaml`, wraps each in
  `CREATE OR REPLACE VIEW {{catalog}}.{{domain}}.{{view_name}} WITH METRICS
  LANGUAGE YAML AS $$ ... $$`, and submits it via the Statement Execution
  API against the target's warehouse.
- SQL warehouse strategy: two `databricks_sql_endpoint` (serverless)
  resources — one interactive-tier, one batch/refresh-tier — per §7 of the
  infra doc, so materialization jobs don't contend with live dashboard
  queries.

**Test:**
- `databricks bundle validate -t dev` and `-t prod` both pass.
- `databricks bundle deploy -t dev` succeeds; confirm the job appears in
  the `dev` workspace's Jobs UI.
- Manually trigger the deploy job once; confirm `dev.housing.market_metrics`
  is re-created without error (idempotency check — this is the job Phase
  E3's CI will call, so it needs to work standalone first).

---

## Phase E3 — CI/CD pipeline *(critical path)*

**Goal:** PR → validate → `dev` deploy (automatic) → required review →
`prod` deploy. No staging stage, per this topology.

**Implement — auth (pick one, in order of rigor):**
1. **OIDC federation (preferred, harder to verify here)**: an AWS IAM role
   with a trust policy scoped to `token.actions.githubusercontent.com` and
   this repo/branch, federated to a Databricks service principal via the
   account console's Federation policies. **[verify]** the exact
   Databricks-side federation policy setup — I haven't tested this flow in
   this session and the CLI/API surface for it deserves a docs check before
   you build on it.
2. **Service principal + secret (proven, same pattern as the Free Edition
   runbook's Phase 3)**: create a dedicated SP, generate an OAuth secret,
   store as `DATABRICKS_CLIENT_ID`/`DATABRICKS_CLIENT_SECRET` in GitHub
   repo secrets. Use this as the safe default; upgrade to OIDC once
   verified.

**Implement — workflow** (`.github/workflows/semantic-layer-ci.yml`):
```yaml
name: semantic-layer-ci
on:
  pull_request:
    paths: ["semantic/**"]
  push:
    branches: [main]
    paths: ["semantic/**"]

jobs:
  validate-and-deploy-dev:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
      - run: curl -fsSL https://raw.githubusercontent.com/databricks/setup-cli/main/install.sh | sh
      - env:
          DATABRICKS_HOST: ${{ secrets.DEV_DATABRICKS_HOST }}
          DATABRICKS_CLIENT_ID: ${{ secrets.DATABRICKS_CLIENT_ID }}
          DATABRICKS_CLIENT_SECRET: ${{ secrets.DATABRICKS_CLIENT_SECRET }}
        run: |
          databricks bundle validate -t dev
          databricks bundle deploy -t dev
          pytest tests/test_metric_parity.py --target dev

  deploy-prod:
    needs: validate-and-deploy-dev
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    environment: prod   # GitHub Environment with required reviewers
    steps:
      - uses: actions/checkout@v5
      - run: curl -fsSL https://raw.githubusercontent.com/databricks/setup-cli/main/install.sh | sh
      - env:
          DATABRICKS_HOST: ${{ secrets.PROD_DATABRICKS_HOST }}
          DATABRICKS_CLIENT_ID: ${{ secrets.DATABRICKS_CLIENT_ID }}
          DATABRICKS_CLIENT_SECRET: ${{ secrets.DATABRICKS_CLIENT_SECRET }}
        run: databricks bundle deploy -t prod
```
- In GitHub: **Settings → Environments → New environment → `prod`**, add
  required reviewers. This is what makes the second job pause for approval.
- Add a `CODEOWNERS` file mapping `semantic/housing/` and `semantic/finance/`
  to their respective domain team reviewers.

**Test:**
1. Open a PR editing a file under `semantic/housing/`. Confirm
   `validate-and-deploy-dev` runs and deploys to `dev` automatically.
2. Deliberately break the YAML (bad measure syntax) in a second PR; confirm
   the job fails and merge is blocked.
3. Merge the good PR to `main`; confirm `deploy-prod` starts but **pauses**
   waiting for a required reviewer.
4. Approve it; confirm the view updates in the `prod` catalog.
5. Confirm the whole loop end to end: a change only reaches `prod` after
   passing dev deploy, parity tests, and human approval — no path skips any
   of the three.

---

## Phase E4 — Observability *(parallel, start once E1 lands)*

**Goal:** one dashboard covering both workspaces, since system tables are
metastore-scoped.

**Implement:**
- Query `system.access.audit` and `system.query.history`, filtered to
  `dev.housing.*`/`prod.housing.*` object names, building a metric view
  over them (same pattern eaten as your own dog food).
- Build one AI/BI dashboard from that metric view.

**Test:**
- Run a query from the `dev` profile and one from the `prod` profile.
- Confirm both show up in the dashboard, distinguishable by
  `workspace_id` — this is the proof that observability doesn't need to be
  rebuilt per workspace, only filtered.

---

## Phase E5 — Governance *(parallel, needs E3's prod pipeline)*

**Implement:**
- A scheduled job querying `INFORMATION_SCHEMA` across **both** `dev` and
  `prod` catalogs, publishing owner/domain/grain/last-used/materialization
  status per certified metric view.
- A short written process for the semantic layer council: who reviews,
  what SLA, what they check against the registry.

**Test:**
- Confirm the registry lists `housing.market_metrics` with correct catalog
  attribution for both `dev` and `prod` rows.
- Run a mock council review against the Phase E0 view — treat it as the
  first real review, not a formality.

---

## Phase E6 — Second domain onboarding *(critical path)*

**Goal:** prove the template and pipeline generalize beyond the pilot
domain — the actual test of "platform," not "one-off project."

**Implement:**
1. Add `semantic/finance/*.yaml` in the same monorepo.
2. Add matching Terraform: `databricks_schema` for `dev.finance` and
   `prod.finance`.
3. Add a `CODEOWNERS` entry for the finance domain team.
4. Open a PR — **no changes to the CI workflow itself should be needed.**

**Test:**
- If the PR deploys through the exact same `semantic-layer-ci.yml` without
  modification, the platform generalizes. If it needed a pipeline change,
  something in E2/E3 was accidentally domain-specific — go back and fix
  that before onboarding a third domain.

---

## Phase E7 — Disaster recovery *(parallel, lower priority)*

**Implement:**
- Document the recovery procedure: re-run `terraform apply` +
  `databricks bundle deploy` against a fresh scratch catalog/workspace.

**Test:**
- Actually do it: point Terraform + the bundle at a scratch catalog (not
  `dev`/`prod`), apply, deploy, and diff the resulting schema/views against
  the real `dev` catalog. This is the only way to know the recovery
  procedure isn't aspirational.

---

## Phase E8 — Lifecycle & maintenance *(parallel, ongoing)*

**Implement:**
- `tests/test_metric_parity.py`: for each metric with an independent
  source of truth, assert the metric view's `MEASURE()` output matches.
  Wire it into `semantic-layer-ci.yml` (already referenced above).
- A schema-contract test added to the **gold pipeline's own CI** (not this
  repo's semantic pipeline) that fails if a gold-table change would break
  a declared metric view's expected columns.

**Test:**
- Intentionally introduce a parity mismatch (edit a measure's expression
  without updating its test); confirm CI fails and blocks merge.
- Intentionally rename a gold column the pilot metric view depends on in a
  test branch of the gold pipeline; confirm the schema-contract test there
  fails before it can ship.

---

## Phase E9 — Network & security *(parallel, verify overlap with existing access first)*

**Implement:**
- PrivateLink/VPC endpoint for both workspaces (cloud-specific Terraform;
  **[verify]** exact resource block against your cloud provider's current
  Databricks PrivateLink setup docs — this varies by cloud and account
  type more than anything else in this runbook).
- Secret scope backed by the cloud secrets manager for any external system
  credentials the gold pipeline needs — not CI-system secrets.

**Test:**
- Confirm, via your cloud provider's network flow logs (not a Databricks
  command — this is cloud-side verification), that SQL warehouse traffic
  for both workspaces stays off the public internet.
- Confirm a credential stored in the secret scope is retrievable from a
  notebook (`dbutils.secrets.get`) but not visible in plaintext anywhere in
  the job logs.

---

## Closing checklist

Before calling this "done" for the two-domain milestone:
- [ ] E0–E3 critical path complete, second domain (E6) live in prod
- [ ] E1's isolation test (catalog invisible from the wrong workspace)
      passed, not skipped
- [ ] E3's full loop tested with a deliberately broken PR, not just a
      working one
- [ ] E7's recovery procedure actually executed once, not just documented
- [ ] Every **[verify]** flag in this doc has been checked against current
      docs and either confirmed or replaced with the correct syntax
