# Enterprise Semantic Layer Platform — Jira Backlog (Two-Workspace Profile)

Ready-to-copy Initiative → Epic → Story hierarchy for Jira. Each issue
includes description, labels, priority, dependencies, links, acceptance
criteria, and a Definition-of-Done checklist. Codes (E0-S1, etc.) are for
cross-referencing dependencies before real Jira keys exist — replace with
actual keys once created, and set "Depends on" as Jira issue links (`blocks`/
`is blocked by`) and "Links" as `relates to`.

**This is an adapted copy of `docs/semantic_layer_jira_backlog.md`**, for
the specific deployment profile in
`docs/enterprise_semantic_layer_execution_runbook.md`: two workspaces
(`dev`, `prod`, no staging), a monorepo, catalog/schema/grants managed
through Databricks Asset Bundles rather than Terraform, and access
provisioning as an external Okta SCIM dependency. The original backlog
describes a more general dev/staging/prod, Terraform-heavy profile — use
that one if your deployment matches it instead. Changes from the original,
concretely:
1. Every staging-specific story is merged into its dev/prod equivalent or
   marked removed (kept as a stub so cross-references elsewhere resolve).
2. E2-S3/E2-S4 moved from Terraform to DAB resources for catalog/schema/
   grants — Terraform is scoped to just workspace binding.
3. A new story (E1-S6) tracks the Okta SCIM dependency, previously untracked.

Companion docs: `docs/semantic_layer_north_star.md`,
`docs/enterprise_semantic_layer_infra.md`,
`docs/semantic_layer_platform_architecture.md`,
`docs/enterprise_semantic_layer_execution_runbook.md`.

---

## INIT-1: Enterprise Multi-Workspace Semantic Layer Platform

**Type:** Initiative
**Labels:** `semantic-layer`, `platform`, `unity-catalog`
**Priority:** High
**Depends on:** None (top-level)
**Links:** Parent of E0–E9

**Description:** Governed Unity Catalog metric views serving multiple domain
teams across dev/prod (two-workspace profile, no staging), proven via a
fast end-to-end demo (Epic 0), then hardened to production.

**Acceptance Criteria:**
- A working demo exists and has been reviewed by leadership.
- At least two domains have certified metric views live in prod.
- CI/CD, observability, and governance are operating without manual
  intervention for routine changes.

**Checklist:**
- [ ] North Star doc reviewed and signed off by stakeholders
- [ ] Epic 0 demo delivered
- [ ] Epics 1–9 scoped and prioritized against the roadmap
- [ ] Success metrics from the North Star doc being tracked

---

## EPIC E0: Proof of Value — End-to-End Semantic Layer Demo

**Type:** Epic
**Labels:** `demo`, `semantic-layer`, `metric-view`
**Priority:** High
**Depends on:** None — uses existing access/gold tables
**Links:** Informs E1–E9; blocks nothing

**Description:** Deliver a live, working example of the semantic layer —
from governed data to a trustworthy business answer — within days, so
leadership sees the approach working end-to-end before committing to the
full rollout.

**Acceptance Criteria (epic exit criteria):**
- One metric view is deployed and queryable via `MEASURE()`.
- One consumption surface (Genie space or AI/BI dashboard) shows correct
  results sourced from that view.
- Demo has been dry-run successfully at least once before the live review.

**Checklist:**
- [ ] Demo data source confirmed
- [ ] Metric view authored, deployed, and validated
- [ ] Consumption surface built and populated with sample questions/tiles
- [ ] Dry run completed
- [ ] Leadership review scheduled

### E0-S1: Confirm source gold table for the demo metric
**Type:** Story | **Epic Link:** E0 | **Points:** 1 | **Priority:** High
**Labels:** `demo`, `data-discovery`
**Depends on:** — | **Links:** blocks E0-S2

**Description:** Identify and validate one existing gold table (e.g.
`gold.county_market_monthly`) as the data source for the demo metric view.

**Acceptance Criteria:**
- Table identified, schema confirmed via `DESCRIBE TABLE EXTENDED`.
- Grain and `is_current`/soft-delete filter columns documented.
- Row count and freshness sanity-checked.

**Checklist:**
- [ ] Table selected and access confirmed
- [ ] Schema and grain documented
- [ ] Sample query run successfully

### E0-S2: Author one metric view YAML
**Type:** Story | **Epic Link:** E0 | **Points:** 3 | **Priority:** High
**Labels:** `demo`, `metric-view`, `yaml`
**Depends on:** E0-S1 | **Links:** blocks E0-S3

**Description:** Write metric view YAML (2–3 dimensions, 3–5 measures)
sourced from the table confirmed in E0-S1, including the `filter` for the
soft-delete/current-flag column.

**Acceptance Criteria:**
- YAML validates against metric view v1.1 syntax.
- Each measure has a `comment`.
- `filter` excludes non-current/soft-deleted rows.

**Checklist:**
- [ ] Dimensions defined
- [ ] Measures defined with comments
- [ ] Filter clause added
- [ ] YAML lints clean

### E0-S3: Deploy metric view using existing access
**Type:** Story | **Epic Link:** E0 | **Points:** 2 | **Priority:** High
**Labels:** `demo`, `deployment`, `unity-catalog`
**Depends on:** E0-S2 | **Links:** blocks E0-S4, E0-S5

**Description:** Deploy the metric view via CLI/DAB into the existing
catalog, reusing already-provisioned access — no new grants required.

**Acceptance Criteria:**
- `CREATE OR REPLACE VIEW ... WITH METRICS LANGUAGE YAML` succeeds.
- View appears in Catalog Explorer with correct owner.

**Checklist:**
- [ ] Deploy command run successfully
- [ ] View visible in Catalog Explorer
- [ ] Deployment logged/recorded for repeatability

### E0-S4: Validate `MEASURE()` query correctness
**Type:** Story | **Epic Link:** E0 | **Points:** 2 | **Priority:** High
**Labels:** `demo`, `testing`, `metric-view`
**Depends on:** E0-S3 | **Links:** blocks E0-S7

**Description:** Confirm each measure returns correct values at the
declared grain, spot-checked against a manual query on the source table.

**Acceptance Criteria:**
- Every measure queried via `MEASURE()` at least once.
- Results match a manually written equivalent query within rounding
  tolerance.

**Checklist:**
- [ ] Test queries written for each measure
- [ ] Results cross-checked against source table
- [ ] Discrepancies (if any) resolved

### E0-S5: Stand up a minimal Genie space or AI/BI dashboard
**Type:** Story | **Epic Link:** E0 | **Points:** 3 | **Priority:** High
**Labels:** `demo`, `genie`, `ai-bi`
**Depends on:** E0-S3 | **Links:** blocks E0-S6

**Description:** Build one consumption surface (Genie space **or** AI/BI
dashboard — pick one for the demo) pointed at the deployed metric view.

**Acceptance Criteria:**
- Surface successfully queries the metric view.
- At least one visual/answer renders correctly with real data.

**Checklist:**
- [ ] Surface created and connected to the metric view
- [ ] At least one working visual/answer confirmed

### E0-S6: Curate 3–5 sample questions/tiles
**Type:** Story | **Epic Link:** E0 | **Points:** 2 | **Priority:** Medium
**Labels:** `demo`, `genie`, `content`
**Depends on:** E0-S5 | **Links:** blocks E0-S7

**Description:** Prepare the walkthrough narrative — curated Genie sample
questions or dashboard tiles that tell a clear story for the review.

**Acceptance Criteria:**
- 3–5 questions/tiles selected, each returning a correct, presentable
  answer.

**Checklist:**
- [ ] Questions/tiles drafted
- [ ] Each verified against the metric view
- [ ] Narrative order decided for the walkthrough

### E0-S7: Dry-run the demo
**Type:** Story | **Epic Link:** E0 | **Points:** 1 | **Priority:** High
**Labels:** `demo`, `readiness`
**Depends on:** E0-S4, E0-S6 | **Links:** blocks E1-S1

**Description:** Full rehearsal of the demo end to end before the live
leadership review.

**Acceptance Criteria:**
- Full walkthrough completed without errors.
- Fallback plan noted for any flaky step (e.g. warehouse cold start).

**Checklist:**
- [ ] Rehearsal completed
- [ ] Timing checked (fits the review slot)
- [ ] Known risks/fallbacks documented

---

## EPIC E1: Environment Topology Hardening

**Type:** Epic
**Labels:** `platform`, `unity-catalog`, `topology`
**Priority:** High
**Depends on:** E0
**Links:** Blocks E2, E9

**Description:** Expand from the demo's single catalog to real dev/prod
isolation (two-workspace profile — no staging), with catalog-to-workspace
bindings enforcing boundaries.

**Acceptance Criteria (epic exit criteria):**
- Dev and prod workspaces exist and are attached to the metastore.
- Catalogs are bound so prod is invisible from dev and vice versa.
- Topology decision is documented and agreed by the platform owner.

**Checklist:**
- [ ] Topology decision documented
- [ ] Dev and prod workspaces confirmed attached to metastore
- [ ] Catalog-to-workspace bindings configured and verified
- [ ] Okta SCIM dependency filed (E1-S6)

### E1-S1: Document topology decision
**Type:** Story | **Epic Link:** E1 | **Points:** 2 | **Priority:** High
**Labels:** `platform`, `documentation`, `topology`
**Depends on:** E0-S7 | **Links:** blocks E1-S2

**Description:** Decide and document the workspace-splitting axis
(environment / function / domain) with rationale, per
`docs/enterprise_semantic_layer_infra.md` §1. For this profile, the
decision is already made — two workspaces, environment-split, no
function/domain split — so this story documents the rationale for that
choice rather than evaluating from scratch.

**Acceptance Criteria:**
- Decision recorded with explicit rationale and rejected alternatives.
- Reviewed by platform owner.

**Checklist:**
- [ ] Options evaluated (environment/function/domain)
- [ ] Decision documented
- [ ] Reviewed and approved

### E1-S2: Confirm dev and prod workspaces attached to metastore
**Type:** Story | **Epic Link:** E1 | **Points:** 2 | **Priority:** High
**Labels:** `platform`, `workspace`
**Depends on:** E1-S1 | **Links:** blocks E1-S4, E9-S1, E9-S2

**Description:** Confirm both workspaces (`dev`, `prod`) already exist and
are attached to the shared metastore — this profile assumes workspaces are
pre-provisioned, not created here (per
`docs/enterprise_semantic_layer_execution_runbook.md` Prerequisites).
Replaces the original backlog's separate staging/prod provisioning stories.

**Acceptance Criteria:**
- Both workspaces confirmed attached to the metastore, admin access tested.

**Checklist:**
- [ ] Dev workspace attachment confirmed
- [ ] Prod workspace attachment confirmed
- [ ] Admin access tested for both

### E1-S3: ~~Provision/confirm prod workspace~~ — merged into E1-S2
**Removed for this profile.** Folded into E1-S2, which now covers both
`dev` and `prod`. Kept as a placeholder code only so any external
cross-reference to "E1-S3" resolves to "see E1-S2" — don't create a Jira
ticket for this one.

### E1-S4: Configure catalog-to-workspace bindings
**Type:** Story | **Epic Link:** E1 | **Points:** 3 | **Priority:** High
**Labels:** `platform`, `unity-catalog`, `security`, `terraform`
**Depends on:** E1-S2 | **Links:** blocks E2-S6, E2-S7, E4-S1, E9-S1, E9-S2

**Description:** Bind each catalog to only the workspace allowed to see it
(`prod` catalog bound to the `prod` workspace only, and vice versa),
enforcing the isolation boundary grants alone can't provide. This is
Terraform-only — confirmed absent from the DAB `Catalog` resource schema,
unlike catalog/schema/grants themselves (see E2-S3).

**Acceptance Criteria:**
- Prod catalog is verifiably invisible from the dev workspace, and vice
  versa.
- Binding configuration is captured in Terraform, not done via console only.

**Checklist:**
- [ ] Bindings configured for both workspaces
- [ ] Cross-workspace visibility tested and confirmed blocked
- [ ] Bindings captured as code
- [ ] Ownership boundary documented: Terraform owns the binding, DABs own
      catalog/schema/grant creation — not both

### E1-S5: (Conditional) Provision function-split workspaces
**Type:** Story | **Epic Link:** E1 | **Points:** 5 | **Priority:** Low
**Labels:** `platform`, `workspace`, `optional`
**Depends on:** E1-S4 | **Links:** none

**Description:** Provision separate Engineering vs. Analytics/BI workspaces
per environment — only if job-compute/interactive-BI quota contention or
differing admin/network policy needs justify it.

**Acceptance Criteria:**
- Justification documented before work begins.
- If built: both workspaces attached to metastore, bindings updated
  accordingly.

**Checklist:**
- [ ] Justification reviewed and approved
- [ ] Workspaces provisioned (if approved)
- [ ] Bindings updated

### E1-S6: File Okta SCIM access-provisioning dependency
**Type:** Story | **Epic Link:** E1 | **Points:** 2 | **Priority:** High
**Labels:** `access`, `dependency`, `external-team`
**Depends on:** — | **Links:** blocks E2-S4

**Description:** Access provisioning is Okta-sourced via SCIM, owned by the
Okta team — not built by this workstream. File the request on day 1, in
parallel with the rest of this epic: the Databricks SCIM integration
confirmed configured, the `semantic-consumers` group created and populated,
and explicit confirmation that group *removals* propagate (deprovisioning),
not just additions. See
`docs/enterprise_semantic_layer_execution_runbook.md` Phase E1 for the
exact request and test steps. Previously untracked in this backlog — the
original assumed access was "already provisioned" without a story to make
that assumption concrete or trackable.

**Acceptance Criteria:**
- `semantic-consumers` group visible in Databricks with expected membership.
- Both the add-path and the remove/deprovisioning-path tested and confirmed
  working — not just the add-path.

**Checklist:**
- [ ] Dependency request filed with the Okta team
- [ ] Group appears in Databricks, membership confirmed
- [ ] Add-test passed
- [ ] Remove/deprovisioning-test passed — don't skip this half
- [ ] Group is never created or modified via Terraform/DABs — Okta/SCIM
      owns it exclusively

---

## EPIC E2: Platform Enablement — Bundle & IaC

**Type:** Epic
**Labels:** `platform`, `iac`, `terraform`, `databricks-bundle`
**Priority:** High
**Depends on:** E1-S4
**Links:** Blocks E3, E6, E7

**Description:** Formalize the demo's ad hoc deploy into a reusable,
IaC-driven bundle template that every domain team scaffolds from. Catalog/
schema/grant provisioning lives in the bundle itself (DABs), confirmed to
support these as native resource types; Terraform is scoped narrowly to
the one thing DABs can't do — catalog-to-workspace binding (E1-S4).

**Acceptance Criteria (epic exit criteria):**
- A bundle template exists and successfully scaffolds a new project.
- Catalog/schema/grants deploy through the bundle, not console clicks.
- Existing access grants are codified in the bundle, referencing the
  Okta-synced group name — not recreated.

**Checklist:**
- [ ] Terraform scoped to workspace binding only
- [ ] DAB catalog/schema/grants resources authored
- [ ] Bundle template built and tested
- [ ] Compute strategy defined

### E2-S1: Set up Terraform project structure
**Type:** Story | **Epic Link:** E2 | **Points:** 3 | **Priority:** High
**Labels:** `iac`, `terraform`
**Depends on:** E1-S4 | **Links:** blocks E2-S2, E2-S3, E9-S4

**Description:** Scaffold the Terraform project (providers, state backend,
module structure) for account/workspace-level resources.

**Acceptance Criteria:**
- `terraform init`/`plan` run cleanly against the target workspace.
- Remote state configured (not local state).

**Checklist:**
- [ ] Provider and backend configured
- [ ] Module directory structure created
- [ ] `plan` runs cleanly with no errors

### E2-S2: Author Terraform for workspace binding (scoped down)
**Type:** Story | **Epic Link:** E2 | **Points:** 3 | **Priority:** Medium
**Labels:** `iac`, `terraform`, `workspace`
**Depends on:** E2-S1 | **Links:** blocks E2-S5, E4-S7

**Description:** Terraform now covers only the catalog-to-workspace
binding (E1-S4) — not workspace creation (workspaces are pre-provisioned
per this profile) and not catalog/schema/grants (moved to DABs, see
E2-S3). Reduced scope and points from the original backlog's broader
workspace-config module.

**Acceptance Criteria:**
- `terraform apply` sets the binding without manual console changes
  required afterward.
- Applied successfully to both `dev` and `prod`.

**Checklist:**
- [ ] Binding resource authored and parameterized
- [ ] Applied to dev
- [ ] Applied to prod
- [ ] Documented usage/variables

### E2-S3: Author DAB resources for catalog, schema, and grants
**Type:** Story | **Epic Link:** E2 | **Points:** 3 | **Priority:** Medium
**Labels:** `iac`, `databricks-bundle`, `unity-catalog`
**Depends on:** E2-S1 | **Links:** blocks E2-S4, E2-S5

**Description:** Define catalog/schema/grant resources in
`resources/catalogs_schemas.yml`, deployed via the bundle — **not**
Terraform. Confirmed via `databricks bundle schema` that `catalogs` and
`schemas` are native DAB resource types with `name`/`comment`/`grants`
fields; this was previously assumed to require Terraform, which was
inaccurate.

**Acceptance Criteria:**
- Bundle resources create catalog + domain schema matching the topology
  decision (E1-S1).
- `databricks bundle validate` passes for both `dev` and `prod` targets.

**Checklist:**
- [ ] `resources/catalogs_schemas.yml` authored
- [ ] Applied for at least one domain schema
- [ ] `bundle validate` passes for both targets
- [ ] Confirmed no dual ownership with the Terraform binding resource
      (E1-S4) — one tool creates the catalog, the other only references it

### E2-S4: Codify existing access grants in the bundle
**Type:** Story | **Epic Link:** E2 | **Points:** 3 | **Priority:** Medium
**Labels:** `iac`, `databricks-bundle`, `access`
**Depends on:** E2-S3, E1-S6 | **Links:** none

**Description:** Express grants on catalogs/schemas as DAB `grants` blocks
(not Terraform), referencing the exact Okta-synced group name from E1-S6.
Grants can't be codified before E1-S6's dependency is delivered — the
group has to exist first.

**Acceptance Criteria:**
- Grants in `resources/catalogs_schemas.yml` reference the Okta-synced
  group name exactly, character for character.
- Grant structure matches the layered model (domain schema → consumer
  `SELECT` on views only).

**Checklist:**
- [ ] Existing grants inventoried
- [ ] Grants expressed as DAB `grants` blocks
- [ ] Verified group name matches what Okta SCIM actually synced (E1-S6)

### E2-S5: Build the platform-owned DAB template
**Type:** Story | **Epic Link:** E2 | **Points:** 5 | **Priority:** High
**Labels:** `platform`, `databricks-bundle`, `template`
**Depends on:** E2-S2, E2-S3 | **Links:** blocks E2-S6, E3-S1, E6-S3, E7-S1

**Description:** Build the reusable Databricks Asset Bundle template
(`databricks bundle init` template) with standard folder layout for
metric-view YAML, CI pipeline definitions, parity-test scaffold, and grant
scripts.

**Acceptance Criteria:**
- Running `databricks bundle init` against the template scaffolds a working
  project in under 5 minutes.
- Required semantic metadata and naming-convention checks are pre-wired.

**Checklist:**
- [ ] Folder layout defined
- [ ] CI scaffold included
- [ ] Parity-test stub included
- [ ] Template tested by scaffolding a fresh project

### E2-S6: Define bundle target mapping per environment
**Type:** Story | **Epic Link:** E2 | **Points:** 3 | **Priority:** High
**Labels:** `databricks-bundle`, `ci-cd`
**Depends on:** E2-S5, E1-S4 | **Links:** blocks E3-S1

**Description:** Define `databricks.yml` targets — workspace host, catalog,
service-principal credential — one per environment.

**Acceptance Criteria:**
- `bundle validate` passes for each target.
- Each target deploys to the correct, isolated workspace/catalog.

**Checklist:**
- [ ] Dev target defined and validated
- [ ] Prod target defined and validated

### E2-S7: Configure SQL warehouse compute strategy
**Type:** Story | **Epic Link:** E2 | **Points:** 3 | **Priority:** Medium
**Labels:** `compute`, `performance`, `cost`
**Depends on:** E1-S4 | **Links:** blocks E2-S8

**Description:** Serverless SQL warehouses sized per domain/workload tier
(interactive vs. batch/refresh), not one shared warehouse for everything.

**Acceptance Criteria:**
- At least two warehouse tiers exist (interactive, batch/refresh).
- Sizing documented with rationale.

**Checklist:**
- [ ] Warehouse tiers defined
- [ ] Sizing documented
- [ ] Verified queries route to the correct tier

### E2-S8: Separate job compute from interactive SQL compute
**Type:** Story | **Epic Link:** E2 | **Points:** 2 | **Priority:** Medium
**Labels:** `compute`, `medallion-pipeline`
**Depends on:** E2-S7 | **Links:** none

**Description:** Ensure medallion pipeline (bronze→silver→gold) and
materialization refresh jobs run on separate compute from interactive
semantic-layer queries.

**Acceptance Criteria:**
- Job compute and SQL warehouse compute are billed/monitored separately.

**Checklist:**
- [ ] Job compute confirmed separate from SQL warehouses
- [ ] Verified in cost/usage dashboard once E4 is built

---

## EPIC E3: CI/CD Pipeline Across Workspaces

**Type:** Epic
**Labels:** `ci-cd`, `platform`, `testing`
**Priority:** High
**Depends on:** E2-S6
**Links:** Blocks E6, E8

**Description:** Add the validate → dev → prod promotion pipeline with an
approval gate that the demo skipped. No staging stage in this profile —
`dev` deploy and smoke testing happen in the same pipeline run that used to
target staging.

**Acceptance Criteria (epic exit criteria):**
- A PR through this pipeline deploys to dev automatically and to prod only
  after explicit approval.
- Parity tests block merge on failure, with no override path.

**Checklist:**
- [ ] PR validate + dev deploy stage built
- [ ] Smoke tests wired into the dev deploy stage
- [ ] Prod deploy with approval gate built

### E3-S1: Build PR validate + dev deploy stage
**Type:** Story | **Epic Link:** E3 | **Points:** 5 | **Priority:** High
**Labels:** `ci-cd`, `testing`
**Depends on:** E2-S6 | **Links:** blocks E3-S2, E3-S4, E3-S6, E8-S1, E8-S5

**Description:** On PR open: `bundle validate`, YAML lint/naming check,
deploy to dev, run parity tests, check semantic-metadata completeness —
absorbs what the original backlog split into a separate "staging deploy"
story (E3-S3, removed for this profile); dev serves that role here.

**Acceptance Criteria:**
- A PR with a broken metric view fails the check and cannot merge.
- A PR with a valid change passes and deploys to dev automatically.

**Checklist:**
- [ ] Validate step added
- [ ] Lint step added
- [ ] Dev deploy step added (UC layer + workspace layer, both verified)
- [ ] Parity test step added
- [ ] Verified with a deliberately broken PR

### E3-S2: Configure CODEOWNERS + platform review gate
**Type:** Story | **Epic Link:** E3 | **Points:** 2 | **Priority:** Medium
**Labels:** `ci-cd`, `governance`, `monorepo`
**Depends on:** E3-S1 | **Links:** none

**Description:** Domain owners approve changes to their own metric views;
platform owner required only when shared CI files are touched.

**Acceptance Criteria:**
- CODEOWNERS file routes review correctly for at least two domain paths.

**Checklist:**
- [ ] CODEOWNERS file created
- [ ] Domain paths mapped to domain reviewers
- [ ] Shared CI paths mapped to platform reviewer

### E3-S3: ~~Build staging auto-deploy on merge~~ — merged into E3-S1
**Removed for this profile.** No staging workspace exists; the dev deploy
in E3-S1 (triggered on PR, not just merge) covers what this story used to
do. Kept as a placeholder code only so any external cross-reference to
"E3-S3" resolves to "see E3-S1."

### E3-S4: Implement smoke tests
**Type:** Story | **Epic Link:** E3 | **Points:** 3 | **Priority:** High
**Labels:** `ci-cd`, `testing`
**Depends on:** E3-S1 | **Links:** blocks E3-S5, E8-S4

**Description:** After dev deploy, query every measure at every declared
grain to catch broken definitions before prod.

**Acceptance Criteria:**
- Smoke test suite runs automatically post-deploy and fails the pipeline
  on any measure error.

**Checklist:**
- [ ] Smoke test script written
- [ ] Wired into the dev deploy step
- [ ] Verified with a deliberately broken measure

### E3-S5: Build prod deploy with manual approval gate
**Type:** Story | **Epic Link:** E3 | **Points:** 5 | **Priority:** High
**Labels:** `ci-cd`, `access`, `release`
**Depends on:** E3-S4 | **Links:** blocks E1(complete)/E5-S1/E6-S1/E7-S1/E8-S1

**Description:** Tag/release-triggered prod deploy behind a required
reviewer gate; applies `SELECT`-only grants to consumer groups; base gold
tables never granted directly.

**Acceptance Criteria:**
- Prod deploy cannot proceed without an approval from a required reviewer.
- Post-deploy, consumer group has `SELECT` on the view only, confirmed via
  `SHOW GRANTS`.

**Checklist:**
- [ ] Approval gate configured (e.g. GitHub Environment / equivalent)
- [ ] Grant application step added
- [ ] Verified consumer cannot query gold table directly

### E3-S6: Implement two-layer deploy distinction
**Type:** Story | **Epic Link:** E3 | **Points:** 3 | **Priority:** Medium
**Labels:** `ci-cd`, `genie`, `ai-bi`
**Depends on:** E3-S1 | **Links:** none

**Description:** Explicitly separate UC-object deploy (metric view, grants)
from workspace-object deploy (Genie space, dashboards) in the pipeline, so
a metric-view change doesn't silently leave Genie/dashboards stale.

**Acceptance Criteria:**
- Pipeline logs/reports show both deploy steps as distinct, independently
  verifiable stages.

**Checklist:**
- [ ] Steps split in pipeline definition
- [ ] Each step's success/failure independently visible
- [ ] Tested a metric-view-only change to confirm workspace layer flagged if stale

### E3-S7: Wire CI auth to existing service principals
**Type:** Story | **Epic Link:** E3 | **Points:** 2 | **Priority:** High
**Labels:** `ci-cd`, `access`, `security`
**Depends on:** E3-S1 | **Links:** none

**Description:** Reuse the already-provisioned service principals/access
model for CI authentication — no new credential build required.

**Acceptance Criteria:**
- CI pipeline authenticates successfully using existing SPs, scoped
  per-environment.
- No personal PATs used in the pipeline.

**Checklist:**
- [ ] SP credentials wired into CI secrets
- [ ] Verified least-privilege scope per environment
- [ ] Confirmed no personal tokens in use

---

## EPIC E4: Observability — Usage, Performance, Cost

**Type:** Epic
**Labels:** `observability`, `system-tables`, `monitoring`, `cost`
**Priority:** Medium
**Depends on:** E1-S4
**Links:** Runs parallel with E5, E6; feeds E5-S4, E8-S3, E8-S9

**Description:** One set of dashboards over the shared metastore's system
tables covering usage/adoption, performance, and cost — built once, not
per workspace.

**Acceptance Criteria (epic exit criteria):**
- Usage, performance, and cost dashboards are live and refreshing.
- Dashboards correctly attribute activity by `workspace_id` and
  domain/environment tags.

**Checklist:**
- [ ] System schemas confirmed enabled
- [ ] Usage dashboard built
- [ ] Performance dashboard built
- [ ] Cost dashboard built
- [ ] Budgets/alerts configured

### E4-S1: Verify/enable UC system schemas
**Type:** Story | **Epic Link:** E4 | **Points:** 2 | **Priority:** High
**Labels:** `observability`, `system-tables`
**Depends on:** E1-S4 | **Links:** blocks E4-S2, E4-S3, E4-S4, E4-S5

**Description:** Confirm `access`, `query`, `lineage`, and `billing` system
schemas are enabled on the metastore before building dashboards on them.

**Acceptance Criteria:**
- Each required system table returns data when queried directly.

**Checklist:**
- [ ] `system.access.audit` confirmed populated
- [ ] `system.query.history` confirmed populated
- [ ] Lineage tables confirmed populated
- [ ] `system.billing.usage` confirmed populated (or noted unavailable)

### E4-S2: Build usage/adoption dashboard
**Type:** Story | **Epic Link:** E4 | **Points:** 5 | **Priority:** Medium
**Labels:** `observability`, `ai-bi`, `system-tables`
**Depends on:** E4-S1 | **Links:** blocks E5-S3, E6-S6, E8-S3

**Description:** Dashboard on `system.access.audit` and
`table_lineage`/`column_lineage` showing who queries which metric view,
from which workspace.

**Acceptance Criteria:**
- Dashboard shows at least one real query event from the E0 demo view.
- Lineage view correctly links a metric view to its consuming dashboard.

**Checklist:**
- [ ] Dashboard built as a metric view over system tables
- [ ] Usage-by-domain breakdown included
- [ ] Lineage panel included

### E4-S3: Build performance dashboard
**Type:** Story | **Epic Link:** E4 | **Points:** 5 | **Priority:** Medium
**Labels:** `observability`, `performance`, `system-tables`
**Depends on:** E4-S1 | **Links:** none

**Description:** Dashboard on `system.query.history` and
`system.compute.warehouse_events` filtered to semantic-schema statements.

**Acceptance Criteria:**
- p95 latency visible per warehouse serving the semantic layer.

**Checklist:**
- [ ] Dashboard built
- [ ] Filtered to semantic-schema statements
- [ ] p95 latency alert configured

### E4-S4: Build materialization refresh health monitoring
**Type:** Story | **Epic Link:** E4 | **Points:** 3 | **Priority:** Medium
**Labels:** `observability`, `materialization`, `alerting`
**Depends on:** E4-S1 | **Links:** blocks E8-S9

**Description:** Track materialized metric view refresh job runs; alert on
missed/failed refreshes.

**Acceptance Criteria:**
- A deliberately failed refresh triggers an alert within an agreed SLA.

**Checklist:**
- [ ] Refresh job history tracked
- [ ] Alert configured on failure
- [ ] Tested with a simulated failure

### E4-S5: Build cost dashboard
**Type:** Story | **Epic Link:** E4 | **Points:** 5 | **Priority:** Medium
**Labels:** `observability`, `cost`, `system-tables`
**Depends on:** E4-S1 | **Links:** blocks E4-S6

**Description:** Dashboard on `system.billing.usage` joined to list prices,
sliced by `domain`/`environment`/`cost_center` tags.

**Acceptance Criteria:**
- Spend attributable to at least one domain via tags.

**Checklist:**
- [ ] Dashboard built
- [ ] Tag-based slicing verified
- [ ] Reviewed with platform owner

### E4-S6: Configure account-level budgets & alerts
**Type:** Story | **Epic Link:** E4 | **Points:** 3 | **Priority:** Medium
**Labels:** `cost`, `alerting`
**Depends on:** E4-S5 | **Links:** none

**Description:** Budgets and alerts on the semantic-layer scope, paging the
platform team before a runaway query/job becomes a surprise bill.

**Acceptance Criteria:**
- Budget threshold configured and alert delivery tested.

**Checklist:**
- [ ] Budget configured
- [ ] Alert recipient(s) confirmed
- [ ] Test alert fired successfully

### E4-S7: Enforce tagging policy
**Type:** Story | **Epic Link:** E4 | **Points:** 3 | **Priority:** Medium
**Labels:** `cost`, `governance`, `terraform`
**Depends on:** E2-S2 | **Links:** blocks E4-S5

**Description:** Require `domain`/`environment`/`cost_center` tags on every
job/warehouse/bundle deployment via policy, not naming convention.

**Acceptance Criteria:**
- An untagged deployment attempt is rejected.

**Checklist:**
- [ ] Policy defined (cluster/warehouse policy or equivalent)
- [ ] Enforcement tested with an untagged deploy
- [ ] Existing resources retrofitted with tags

---

## EPIC E5: Governance Operating Model

**Type:** Epic
**Labels:** `governance`, `metric-registry`
**Priority:** Medium
**Depends on:** E3-S5
**Links:** Gates E6-S4; feeds E8-S2, E8-S6

**Description:** Prevent shadow metrics once more than one domain is
authoring metric views independently.

**Acceptance Criteria (epic exit criteria):**
- A council review process exists and has approved at least one new
  certified metric.
- The metric registry dashboard is live and lists every certified view.

**Checklist:**
- [ ] RACI defined
- [ ] Council stood up
- [ ] Metric registry job built
- [ ] Deprecation policy defined

### E5-S1: Define platform vs. domain team ownership RACI
**Type:** Story | **Epic Link:** E5 | **Points:** 2 | **Priority:** Medium
**Labels:** `governance`, `documentation`
**Depends on:** E3-S5 | **Links:** blocks E5-S2

**Description:** Document who owns what — metastore/topology/CI vs.
domain metric views/Genie content.

**Acceptance Criteria:**
- RACI reviewed and agreed by platform and at least one domain team.

**Checklist:**
- [ ] Draft RACI written
- [ ] Reviewed with stakeholders
- [ ] Published/linked from onboarding runbook

### E5-S2: Stand up the semantic layer council
**Type:** Story | **Epic Link:** E5 | **Points:** 3 | **Priority:** Medium
**Labels:** `governance`, `process`
**Depends on:** E5-S1 | **Links:** blocks E6-S4, E8-S2, E8-S6, E8-S7

**Description:** Small cross-domain review function approving new
certified metric views before they enter the shared prod namespace.

**Acceptance Criteria:**
- Council membership defined; review cadence/SLA agreed.

**Checklist:**
- [ ] Members identified
- [ ] Review process/SLA documented
- [ ] First review conducted (can be E0's demo metric, retroactively)

### E5-S3: Build the generated metric registry job
**Type:** Story | **Epic Link:** E5 | **Points:** 5 | **Priority:** Medium
**Labels:** `governance`, `automation`, `system-tables`
**Depends on:** E4-S2 | **Links:** blocks E5-S4

**Description:** Scheduled job reading `INFORMATION_SCHEMA`/system tables,
publishing owner, domain, grain, last-used, and materialization status for
every certified metric view.

**Acceptance Criteria:**
- Registry dashboard lists the E0 demo view with correct metadata.
- Job runs on a schedule without manual trigger.

**Checklist:**
- [ ] Job authored
- [ ] Scheduled
- [ ] Dashboard/report published
- [ ] Verified against a known metric view

### E5-S4: Define and implement the deprecation policy
**Type:** Story | **Epic Link:** E5 | **Points:** 3 | **Priority:** Low
**Labels:** `governance`, `lifecycle`
**Depends on:** E5-S3 | **Links:** blocks E8-S7

**Description:** Metric views with zero usage in `system.access.audit`
over N days flagged in the registry dashboard for owner review.

**Acceptance Criteria:**
- Policy threshold (N days) agreed and documented.
- Flagging logic tested against a deliberately unused view.

**Checklist:**
- [ ] Threshold defined
- [ ] Flagging logic implemented
- [ ] Tested with a zero-usage view

---

## EPIC E6: Domain Onboarding & Runbook

**Type:** Epic
**Labels:** `onboarding`, `domain-rollout`
**Priority:** Medium
**Depends on:** E3-S5, E5-S2
**Links:** Consumes E2-S5; validated by E4-S2

**Description:** Bring a second domain onto the platform using what the
demo and pipeline proved, producing a repeatable runbook.

**Acceptance Criteria (epic exit criteria):**
- A second domain has a certified metric view live in prod.
- Onboarding took roughly the time estimated in the runbook (~1 sprint).

**Checklist:**
- [ ] Runbook written
- [ ] Second domain onboarded end-to-end
- [ ] Runbook updated with real learnings from the onboarding

### E6-S1: Write onboarding runbook
**Type:** Story | **Epic Link:** E6 | **Points:** 2 | **Priority:** Medium
**Labels:** `onboarding`, `documentation`
**Depends on:** E3-S5 | **Links:** blocks E6-S2

**Description:** Document the onboarding steps based on demo and pipeline
learnings, per `docs/enterprise_semantic_layer_infra.md` §10.

**Acceptance Criteria:**
- Runbook covers schema provisioning through prod go-live.

**Checklist:**
- [ ] Draft written
- [ ] Reviewed by platform owner
- [ ] Published

### E6-S2: Onboard second domain — provision schema
**Type:** Story | **Epic Link:** E6 | **Points:** 2 | **Priority:** Medium
**Labels:** `onboarding`, `unity-catalog`
**Depends on:** E6-S1 | **Links:** blocks E6-S3

**Description:** Provision the second domain's schema, reusing the
existing access model (no new grant work required).

**Acceptance Criteria:**
- Schema exists in dev and prod catalogs per topology.

**Checklist:**
- [ ] Schema provisioned in each environment
- [ ] Access confirmed for the domain team

### E6-S3: Onboard second domain — scaffold repo from template
**Type:** Story | **Epic Link:** E6 | **Points:** 2 | **Priority:** Medium
**Labels:** `onboarding`, `databricks-bundle`
**Depends on:** E2-S5, E6-S2 | **Links:** blocks E6-S4

**Description:** Scaffold the second domain's metric-view project from
the shared bundle template.

**Acceptance Criteria:**
- `databricks bundle init` produces a working project structure for the
  new domain.

**Checklist:**
- [ ] Repo/folder scaffolded
- [ ] Bundle validates for the new domain's targets

### E6-S4: Onboard second domain — author/deploy first certified metric view
**Type:** Story | **Epic Link:** E6 | **Points:** 5 | **Priority:** Medium
**Labels:** `onboarding`, `metric-view`, `governance`
**Depends on:** E5-S2, E6-S3 | **Links:** blocks E6-S5, E6-S6

**Description:** Author, test, and promote the second domain's first
metric view through the full CI/CD pipeline and council review.

**Acceptance Criteria:**
- View passes parity/regression tests and council review.
- View is live in prod with correct grants.

**Checklist:**
- [ ] Metric view authored
- [ ] PR passed CI, reviewed, merged
- [ ] Council reviewed and approved
- [ ] Deployed to prod

### E6-S5: Onboard second domain — stand up Genie space
**Type:** Story | **Epic Link:** E6 | **Points:** 3 | **Priority:** Medium
**Labels:** `onboarding`, `genie`
**Depends on:** E6-S4 | **Links:** none

**Description:** Stand up the second domain's Genie space with curated
verified questions against their new metric view.

**Acceptance Criteria:**
- Genie space answers at least 3 curated questions correctly.

**Checklist:**
- [ ] Genie space created
- [ ] Questions curated and verified
- [ ] Reviewed with domain team

### E6-S6: Validate second domain appears in observability dashboards
**Type:** Story | **Epic Link:** E6 | **Points:** 2 | **Priority:** Low
**Labels:** `onboarding`, `observability`
**Depends on:** E4-S2, E6-S4 | **Links:** none

**Description:** Confirm the new domain's metric view usage/cost appears
automatically in the shared observability dashboards — no separate setup
needed.

**Acceptance Criteria:**
- New domain visible in usage dashboard within 24 hours of first query.

**Checklist:**
- [ ] Confirmed domain appears in usage dashboard
- [ ] Confirmed domain appears in cost dashboard

---

## EPIC E7: Disaster Recovery & Continuity

**Type:** Epic
**Labels:** `dr`, `resilience`, `iac`
**Priority:** Low
**Depends on:** E2-S5
**Links:** Independent of E4–E6; parallelizable

**Description:** Confirm the platform recovers from code, not backups —
UC metadata is redeployable from the repo.

**Acceptance Criteria (epic exit criteria):**
- A recovery test in a scratch environment succeeds using only the repo's
  Terraform + DABs.

**Checklist:**
- [ ] Recovery procedure documented
- [ ] Recovery tested in a scratch environment
- [ ] Multi-region failover scoped (not necessarily built)

### E7-S1: Document DR recovery procedure
**Type:** Story | **Epic Link:** E7 | **Points:** 3 | **Priority:** Low
**Labels:** `dr`, `documentation`
**Depends on:** E2-S5 | **Links:** blocks E7-S2

**Description:** Document the steps to redeploy UC metadata (catalogs,
schemas, grants, metric views) from the repo to a new metastore/workspace.

**Acceptance Criteria:**
- Procedure is specific enough to follow without tribal knowledge.

**Checklist:**
- [ ] Procedure drafted
- [ ] Reviewed by platform owner

### E7-S2: Test UC metadata recovery in a scratch environment
**Type:** Story | **Epic Link:** E7 | **Points:** 5 | **Priority:** Low
**Labels:** `dr`, `testing`
**Depends on:** E7-S1 | **Links:** none

**Description:** Actually run the documented recovery procedure against a
scratch metastore/workspace to verify it works.

**Acceptance Criteria:**
- Scratch environment ends up with matching catalogs/schemas/metric views,
  verified by comparison.

**Checklist:**
- [ ] Scratch environment provisioned
- [ ] Recovery procedure executed
- [ ] Output compared against source environment

### E7-S3: Scope cross-region/multi-metastore failover requirements
**Type:** Story | **Epic Link:** E7 | **Points:** 3 | **Priority:** Low
**Labels:** `dr`, `design`
**Depends on:** E7-S1 | **Links:** none

**Description:** Design exercise with platform/security team — RTO/RPO
requirements, compliance drivers — not a default build.

**Acceptance Criteria:**
- Written scoping doc with a go/no-go recommendation.

**Checklist:**
- [ ] Requirements gathered from security/compliance
- [ ] Scoping doc written
- [ ] Recommendation presented to platform owner

---

## EPIC E8: Metric View Lifecycle & Maintenance

**Type:** Epic
**Labels:** `lifecycle`, `testing`, `governance`
**Priority:** Medium
**Depends on:** E3-S5, E6-S4
**Links:** Ongoing; feeds back into E3, E5

**Description:** Keep metric views correct and trusted for the years they
stay in production — day-2 operations, not provisioning.

**Acceptance Criteria (epic exit criteria):**
- Every metric-view PR runs the full test pyramid (lint → smoke → parity →
  regression → consumer-level).
- A deprecation workflow and consumer-notification hook are live.

**Checklist:**
- [ ] Schema-contract tests added to gold pipeline CI
- [ ] Versioning policy documented
- [ ] Change-impact analysis wired into PR process
- [ ] Certification tiers defined
- [ ] Deprecation workflow automated

### E8-S1: Add schema-contract tests to the gold pipeline's CI
**Type:** Story | **Epic Link:** E8 | **Points:** 5 | **Priority:** High
**Labels:** `lifecycle`, `testing`, `data-quality`
**Depends on:** E3-S1 | **Links:** none

**Description:** Fail the gold pipeline's own CI if a change would break a
declared downstream metric view's expected columns.

**Acceptance Criteria:**
- A deliberately breaking gold-schema change fails CI before merge.

**Checklist:**
- [ ] Expected-schema contract defined per metric view
- [ ] Test wired into gold pipeline CI
- [ ] Verified with a deliberate breaking change

### E8-S2: Define the metric versioning policy
**Type:** Story | **Epic Link:** E8 | **Points:** 2 | **Priority:** Medium
**Labels:** `lifecycle`, `documentation`
**Depends on:** E5-S2 | **Links:** none

**Description:** Document the additive-first pattern (ship `v2` alongside
the old measure, deprecation window, then remove) — never redefine a
measure name in place.

**Acceptance Criteria:**
- Policy documented and referenced in the bundle template's standards.

**Checklist:**
- [ ] Policy drafted
- [ ] Reviewed by council
- [ ] Linked from template/onboarding docs

### E8-S3: Build change-impact analysis using lineage
**Type:** Story | **Epic Link:** E8 | **Points:** 5 | **Priority:** Medium
**Labels:** `lifecycle`, `lineage`, `governance`
**Depends on:** E4-S2 | **Links:** blocks E8-S8

**Description:** Before merging an edit to an existing live metric view,
pull its consumers from lineage tables and require sign-off from affected
owners as part of the PR.

**Acceptance Criteria:**
- A PR editing a view with known consumers surfaces those consumers
  automatically.

**Checklist:**
- [ ] Lineage lookup automated (script/CI step)
- [ ] Sign-off requirement wired into PR template/process
- [ ] Tested against the E0 demo view once it has a consumer

### E8-S4: Implement the layered test pyramid
**Type:** Story | **Epic Link:** E8 | **Points:** 5 | **Priority:** High
**Labels:** `lifecycle`, `testing`
**Depends on:** E3-S4 | **Links:** none

**Description:** Lint → deploy-and-query smoke test → parity → regression
(diff vs. last release) → consumer-level (Genie/dashboard checks) — run on
every PR touching a metric view.

**Acceptance Criteria:**
- All five layers run automatically on a metric-view PR.
- A regression (silent output change) is caught before merge.

**Checklist:**
- [ ] Lint layer wired
- [ ] Smoke layer wired
- [ ] Parity layer wired
- [ ] Regression layer wired
- [ ] Consumer-level layer wired

### E8-S5: Add CI lint for semantic metadata completeness
**Type:** Story | **Epic Link:** E8 | **Points:** 3 | **Priority:** Medium
**Labels:** `lifecycle`, `ci-cd`, `documentation`
**Depends on:** E3-S1 | **Links:** none

**Description:** Fail CI on measures/dimensions missing
`comment`/`synonyms`/`format`, preventing metadata decay after initial
launch.

**Acceptance Criteria:**
- A PR adding an undocumented measure fails the lint step.

**Checklist:**
- [ ] Lint rule implemented
- [ ] Wired into PR validate stage
- [ ] Tested with a deliberately undocumented measure

### E8-S6: Define the certification tier workflow
**Type:** Story | **Epic Link:** E8 | **Points:** 3 | **Priority:** Low
**Labels:** `lifecycle`, `governance`
**Depends on:** E5-S2 | **Links:** none

**Description:** Experimental → verified → certified promotion path using
Catalog Explorer's trust badges, with stated criteria per tier.

**Acceptance Criteria:**
- Criteria documented; at least one view promoted through all three tiers.

**Checklist:**
- [ ] Tier criteria documented
- [ ] Badging applied in Catalog Explorer
- [ ] E0 demo view promoted through tiers as a test case

### E8-S7: Implement the deprecation/sunset workflow
**Type:** Story | **Epic Link:** E8 | **Points:** 5 | **Priority:** Low
**Labels:** `lifecycle`, `automation`, `governance`
**Depends on:** E5-S4 | **Links:** none

**Description:** Mark deprecated in metadata → surface a warning in
Genie/dashboards → notify lineage-derived consumers → grace period → drop.

**Acceptance Criteria:**
- A deprecated view shows a visible warning to consumers before removal.

**Checklist:**
- [ ] Deprecation metadata flag implemented
- [ ] Warning surfaced in Genie/dashboard
- [ ] Notification step implemented
- [ ] Grace-period + drop process documented and tested

### E8-S8: Build downstream consumer notification hook
**Type:** Story | **Epic Link:** E8 | **Points:** 3 | **Priority:** Medium
**Labels:** `lifecycle`, `automation`, `lineage`
**Depends on:** E8-S3 | **Links:** none

**Description:** On merge of any change to a live metric view, notify its
consumers (derived from lineage) via a CI hook.

**Acceptance Criteria:**
- A merge to a view with known consumers triggers a notification
  (e.g. Slack/Teams/email) to the owning team.

**Checklist:**
- [ ] Notification hook implemented
- [ ] Tested against a known consumer
- [ ] Delivery confirmed

### E8-S9: Surface data freshness/quality signal in the presentation layer
**Type:** Story | **Epic Link:** E8 | **Points:** 3 | **Priority:** Low
**Labels:** `lifecycle`, `data-quality`
**Depends on:** E4-S4 | **Links:** none

**Description:** Tie `silver.data_quality_log` (this repo's existing
pattern) or materialization refresh health into the metric view's
presentation layer, so staleness is visible to consumers, not just to
pipeline monitoring.

**Acceptance Criteria:**
- A stale/failed upstream load is visibly flagged on the dashboard/Genie
  surface.

**Checklist:**
- [ ] Freshness signal source identified
- [ ] Surfaced in dashboard/Genie presentation
- [ ] Tested with a simulated stale load

---

## EPIC E9: Network & Security Hardening

**Type:** Epic
**Labels:** `network`, `security`
**Priority:** Medium — verify overlap with existing access before scheduling
**Depends on:** E1-S4
**Links:** Independent of E4–E8; parallelizable with E2

**Description:** Only if not already covered by existing access
provisioning — verify scope before scheduling this epic's work.

**Acceptance Criteria (epic exit criteria):**
- Prod data-plane traffic confirmed off the public internet.
- Secrets for external/storage credentials are in a proper secret store,
  not CI-system secrets.

**Checklist:**
- [ ] Overlap with existing access model verified
- [ ] PrivateLink/VNet configured for prod
- [ ] Egress policy defined per environment
- [ ] Secret scopes configured

### E9-S1: Configure PrivateLink/VNet for prod
**Type:** Story | **Epic Link:** E9 | **Points:** 5 | **Priority:** Medium
**Labels:** `network`, `security`
**Depends on:** E1-S2 | **Links:** blocks E9-S3

**Description:** Keep prod data-plane traffic off the public internet.

**Acceptance Criteria:**
- Network path verified private (no public egress for data-plane traffic).

**Checklist:**
- [ ] PrivateLink/VNet injection configured
- [ ] Verified via network test
- [ ] Documented

### E9-S2: Configure PrivateLink/VNet for dev
**Type:** Story | **Epic Link:** E9 | **Points:** 3 | **Priority:** Low
**Labels:** `network`, `security`
**Depends on:** E1-S2 | **Links:** blocks E9-S3

**Description:** Same as E9-S1, for `dev` — may use a looser policy than
prod. No staging environment in this profile.

**Acceptance Criteria:**
- Network path configured and documented for dev.

**Checklist:**
- [ ] Configured for dev
- [ ] Documented differences from prod policy

### E9-S3: Define workspace-level network egress policy per environment
**Type:** Story | **Epic Link:** E9 | **Points:** 3 | **Priority:** Low
**Labels:** `network`, `security`, `documentation`
**Depends on:** E9-S1, E9-S2 | **Links:** none

**Description:** Document egress rules per environment, consistent with
this repo's existing precedent of splitting internet-facing acquisition
out of Databricks entirely.

**Acceptance Criteria:**
- Policy documented and matches actual configured behavior.

**Checklist:**
- [ ] Policy documented
- [ ] Verified against actual network config

### E9-S4: Configure secret scopes backed by cloud secrets manager
**Type:** Story | **Epic Link:** E9 | **Points:** 3 | **Priority:** Medium
**Labels:** `security`, `secrets`
**Depends on:** E2-S1 | **Links:** none

**Description:** External system and storage credentials go through
Databricks secret scopes backed by Key Vault/Secrets Manager — not CI
secrets, which hold only OIDC trust config.

**Acceptance Criteria:**
- No raw credentials present in CI system secrets beyond OIDC trust
  configuration.

**Checklist:**
- [ ] Secret scope(s) created
- [ ] Backed by cloud secrets manager
- [ ] CI secrets audited to confirm no leftover raw credentials

---

## Epic-level dependency chain

```
E0 → E1 → E2 → E3 → E5 → E6
              ↓         ↑
             E4 ────────┘
              ↓
             E8
E1 → E9 (parallel with E2)
E2 → E7 (parallel with E3+)
```
