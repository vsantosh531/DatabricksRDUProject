# Enterprise Semantic Layer Infrastructure — Multi-Workspace Reference

Companion to `docs/semantic_layer_platform_architecture.md` (the single-team,
single-workspace design). This doc covers what changes and what gets added
when the semantic layer needs to serve **multiple teams across multiple
Databricks workspaces** — the full enterprise setup checklist.

The single fact that drives most of the design below: **Unity Catalog
objects (catalogs, schemas, tables, metric views, grants) live at the
metastore level and can be shared across every workspace bound to that
metastore. Workspace objects (Jobs, Genie spaces, AI/BI Dashboards, SQL
alerts) are scoped to one workspace and must be explicitly deployed to
each one.** Nearly every section below is a consequence of that split.

---

## 1. Metastore & workspace topology

- **Metastore**: one per region (occasionally one per compliance boundary,
  e.g. a regulated business unit that must be isolated). Minimize metastore
  count — Databricks' own guidance is against a metastore-per-team model.
- **Workspaces**: choose the splitting axis deliberately.

| Axis | When to use it |
|---|---|
| **By environment** (dev / staging / prod) | Baseline for every org — required |
| **By function** (Engineering workspace running ETL jobs/pipelines vs. Analytics/BI workspace running SQL warehouses, Genie, dashboards — per environment) | Add once job compute and interactive BI usage contend for quota, or the two personas need different admin/network policy |
| **By domain/business unit** | Add only if the domain needs its own network boundary, admin delegation, or compliance boundary — not merely for a sense of ownership. Otherwise domains stay as catalogs/schemas inside shared workspaces |

Recommendation: environment-based workspaces first, function split second,
domain split only when isolation is a real requirement — each additional
workspace multiplies CI/CD and governance surface area.

- **Catalog-to-workspace binding**: bind each catalog to only the workspaces
  allowed to see it (e.g. the `prod` catalog bound to prod workspace(s) only,
  invisible from dev). This is the enforced isolation boundary that a
  single-workspace setup can't provide — grants alone aren't the whole
  control at this scale, the binding is.

---

## 2. UC object model vs. workspace object model

| | Scope | Deployment implication |
|---|---|---|
| Catalogs, schemas, tables, **metric views**, grants | Metastore-wide | Deploy once per environment (catalog); any bound workspace can query immediately, no redeployment per workspace |
| Jobs, **Genie spaces**, AI/BI Dashboards, SQL alerts | Single workspace | Must be explicitly deployed to **every** workspace that needs them, even within the same environment if function/domain-split |

The most common failure mode at this scale: a metric view definition changes
and deploys cleanly to the prod catalog, but the prod Genie space or
dashboard — a separate, workspace-scoped object — still points at the old
version because nobody redeployed it. Design the CI/CD pipeline (§4) to
treat these as two distinct deploy steps, not one.

---

## 3. Infrastructure-as-Code layering

Two tools, two owners — Terraform's scope grows substantially at this scale.

| Terraform (account-level; platform team) | Databricks Asset Bundles (workspace-level; domain teams) |
|---|---|
| Workspace creation/config per environment (+ function) | Jobs (bronze → silver → gold → semantic-deploy) |
| Metastore attachment, catalog-to-workspace bindings | Metric view deploy tasks |
| SCIM connector configuration (IdP → account console) | Genie space definitions |
| Network config (PrivateLink/VNet injection, esp. prod) | AI/BI dashboards |
| Account-level budgets & alerts | Domain-owned grants within their schema |

Bundle targets map to `(workspace host, catalog, service-principal
credential)` triples — one target per environment, or per environment ×
function if workspaces are split that way.

---

## 4. CI/CD pipeline across workspaces

Same validate → dev → staging → prod shape as the single-workspace design,
but each stage now targets a **different workspace host**, not just a
different catalog:

```
PR  -> validate (bundle validate, lint, parity tests, dev-workspace deploy)
     -> CODEOWNERS + platform review (if shared CI files touched)
merge -> staging workspace deploy
       - UC-layer: metric view + grants
       - workspace-layer: Genie space + dashboards redeployed
       - smoke test: every measure queried at every declared grain
release/tag -> manual approval gate -> prod workspace deploy
             - same two-layer deploy as staging
             - grants: consumers get SELECT on the view only
             - base gold tables never granted to consumers directly
```

- **One OIDC-federated service principal per environment workspace** — no
  long-lived PATs. Workload identity federation between the CI system and
  the cloud IAM / Databricks account replaces stored credentials entirely.
- **Least privilege per SP**: scoped to `CREATE`/`MODIFY` within its
  environment's semantic schema only; grant-management stays in Terraform.
- **Runtime secrets** (external system credentials, storage credentials) go
  through Databricks secret scopes backed by the cloud provider's secrets
  manager (Key Vault / Secrets Manager) — not CI-system secrets, which
  should only hold the OIDC trust configuration.

---

## 5. Identity & access control at scale

- **SCIM sync from the corporate IdP** (Okta / Azure AD / Ping) into the
  account console — group membership becomes IdP-driven, so an org change
  (onboarding, offboarding, team move) propagates correctly across every
  workspace and catalog at once instead of manual per-workspace admin.
- **Layered grant model** (same principle as single-workspace, now applied
  per catalog-per-environment): domain-owned schema inside a platform-owned
  catalog; consumers get `SELECT` on the metric view only; deploy identity
  (CI's SP) and query identity (human/Genie) stay separate principals.
- **Row filters and column masks** on gold tables for PII/regulated fields —
  applied at the table level so every metric view built on top inherits the
  restriction automatically rather than reimplementing it per view.
- **Attribute-based tagging** (data classification tags on columns/tables)
  feeds both the masking policies above and the discovery experience in
  Catalog Explorer/Genie — worth setting up before the catalog grows past a
  size where manual classification is tractable.

---

## 6. Network & security

- **PrivateLink / VNet injection** per workspace, at minimum for prod — keep
  data-plane traffic off the public internet.
- **Workspace-level network policies** consistent with the topology in §1
  (e.g. dev workspace may have looser egress than prod, matching this repo's
  existing precedent of splitting internet-facing acquisition out of
  Databricks entirely).
- **CI authentication** via OIDC federation (§4), eliminating stored
  Databricks credentials in the CI system as an attack surface.
- **Audit trail**: `system.access.audit` (see §8) is the source for security
  review of who accessed what, across every workspace on the metastore.

---

## 7. Compute strategy

- **SQL warehouses**: serverless as the default for semantic-layer query
  serving (dashboards, Genie, ad hoc analyst SQL) — matches the persona split
  in §1 if Engineering/Analytics workspaces are separated. Size/scale
  warehouses per domain or per workload tier (interactive vs. batch/refresh)
  rather than one shared warehouse for everything, to keep cost attribution
  in §9 clean and to prevent one domain's heavy Genie usage from starving
  another's dashboard.
- **Job compute** for the medallion pipeline (bronze → silver → gold) and for
  metric-view/materialization refresh jobs stays separate from interactive
  SQL compute — different scaling profile, different cost bucket.
- **Materialization** for metric views backing high-traffic dashboards/Genie
  spaces; leave exploratory/ad hoc views virtual. Revisit materialization
  schedules against actual usage data (§8) rather than provisioning by guess.

---

## 8. Observability — usage, performance, cost

This is where multi-workspace is genuinely *easier* than a single-workspace
setup: **system tables are scoped to the metastore, not the workspace**, and
carry a `workspace_id` column, so one set of dashboards covers every
workspace bound to the metastore.

| Concern | Source | Notes |
|---|---|---|
| Usage / adoption | `system.access.audit`, `system.access.table_lineage`/`column_lineage` | Who queries which metric view, from which workspace; lineage into dashboards/Genie spaces for impact analysis |
| Performance | `system.query.history`, `system.compute.warehouse_events`, Lakeflow Jobs system tables (materialization refresh health) | Filter to semantic-schema statements; alert on p95 latency and failed/missed materialization refreshes |
| Cost | `system.billing.usage` joined to list prices, sliced by enforced `domain`/`environment`/`cost_center` tags | Account-level Budgets & Alerts are fully functional at this scale (unlike a quota-based free tier) |

Build these once against the shared metastore; don't rebuild per workspace.

---

## 9. Governance operating model

- **Platform team** owns: metastore, workspace provisioning, catalog
  bindings, SCIM, network, account-level Terraform, the bundle template, the
  observability dashboards.
- **Domain teams** own: their schema's metric views, their Genie space
  content, responding to their own CI parity-test failures.
- **Semantic layer council / Center of Excellence** — a small cross-domain
  review function that approves *new certified* metric views before they
  enter the shared prod catalog namespace, checked against a generated
  metric registry for near-duplicates. Necessary once more than a couple of
  domains author independently (including via Genie); without it, "shadow
  metrics" — several slightly different definitions of the same KPI — is the
  predictable failure mode.
- **Generated metric registry**: a scheduled job reading UC
  `INFORMATION_SCHEMA`/system tables, publishing owner, domain, grain,
  last-used, and materialization status for every certified metric view.
- **Deprecation policy**: metric views with zero usage in
  `system.access.audit` over N days get flagged for owner review.

---

## 10. Onboarding runbook (new domain team joining the platform)

1. Platform team provisions the domain's schema inside the appropriate
   catalog(s) (dev/staging/prod) and the corresponding IdP-synced group(s).
2. Domain team scaffolds their repo from the shared bundle template
   (`databricks bundle init` against the platform template).
3. Domain team authors metric views (YAML or Genie-assisted against their
   dev catalog sandbox) and opens a PR.
4. CI validates, deploys to dev, runs parity tests — domain team iterates.
5. On merge, auto-deploy to staging; smoke tests confirm every measure at
   every declared grain.
6. Semantic layer council reviews any *new certified* metric before prod
   promotion, checking the metric registry for overlap.
7. Tagged release deploys to prod (UC layer + Genie/dashboard workspace
   layer); grants applied, base gold tables locked to the domain's own
   pipeline identity only.
8. Domain's metric views, usage, and cost now appear automatically in the
   shared observability dashboards (§8) — no separate setup needed.

---

## 11. Disaster recovery & continuity

- **UC metadata** (catalogs, schemas, grants, metric view definitions) is
  managed as code (Terraform + DABs) — recovery is redeploying from the repo
  to a new metastore/workspace, not restoring a backup, provided the repo is
  the actual source of truth (no console-drift).
- **Underlying gold/silver/bronze data** durability is the medallion
  pipeline's existing storage layer concern, not new for the semantic layer
  — the semantic layer adds no new data-durability surface, only metadata,
  which is why keeping it IaC-driven matters.
- **Cross-region/multi-metastore failover** is a genuine architectural
  decision with real tradeoffs specific to the organization's compliance and
  RTO/RPO requirements — treat as a dedicated design exercise with the
  platform/security team rather than a default in this doc.

---

## 12. Metric view lifecycle & maintenance

Sections 1–11 cover standing the platform up. This section covers what keeps
a metric view correct and trusted for the years it stays in production after
that — day-2 operations, not provisioning.

**Schema drift & breaking-change management**
When a source gold table adds, renames, drops a column, or changes grain,
the metric view built on it can silently break or silently misreport. Add a
schema-contract test to the *gold pipeline's own* CI that fails if a change
would break a declared downstream metric view's expected columns, and
require gold-table owners to notify semantic-layer owners before a breaking
change ships — not after a dashboard goes wrong.

**Metric versioning, not silent redefinition**
Business-logic versioning is distinct from environment promotion. If a
measure's definition must change in a way that alters historical numbers,
ship the new definition alongside the old (e.g. `Total Revenue` and
`Total Revenue (v2)`), give consumers a deprecation window, then remove the
old one. Never redefine a measure name in place — that breaks trust
invisibly, since the same dashboard tile silently starts meaning something
different.

**Change-impact analysis on edits to existing views**
§9's council reviews *new* certified metrics for duplicates; edits to
*existing* live metric views need a separate gate. Before merging a change,
pull the view's consumers from `system.access.table_lineage`/
`column_lineage` and require sign-off from affected dashboard/Genie-space
owners as part of the PR.

**A layered test strategy, not just "parity tests"**
Treat metric-view testing as a pyramid, run on every PR that touches a view:
YAML lint/schema validation → deploy-and-query smoke test → parity against
the source-of-truth logic → **regression** (output diffed against the last
release on the same input, to catch silent drift) → consumer-level (Genie's
verified queries and dashboard visuals still resolve correctly).

**Semantic metadata upkeep**
`comment`/`synonyms`/`format` decay as people add measures without
documenting them once initial launch pressure is gone. A CI lint step that
fails on undocumented measures/dimensions keeps this from rotting silently —
distinct from requiring it once at creation.

**Certification tier workflow**
Define an explicit promotion path — experimental → verified → certified —
using Catalog Explorer's certification/trust badges, with stated criteria
for each tier (test coverage, documentation completeness, usage history).
Gives consumers a visible trust signal and gives the council in §9 a
concrete gate to apply, rather than a binary "is it in prod."

**Concrete deprecation/sunset steps**
§9 flags zero-usage views for review; turn that detection into an actual
workflow: mark deprecated in metadata → surface a warning in Genie/
dashboards referencing it → notify lineage-derived consumers → grace period
→ drop. A detection rule alone isn't a process.

**Performance tuning as an ongoing activity**
Periodically revisit, from `system.query.history`, which dimensions/measures
are actually queried together — use it to inform gold-table clustering keys,
to check whether materialization windows still match real usage, and to
decide whether a view has accumulated enough measures/joins that it should
split. This is recurring, not a one-time sizing decision at launch.

**Ownership transitions**
The metric registry's owner field (§9) needs to stay current, not be set
once at creation. Tie it to the repo's CODEOWNERS and require an explicit
handoff step on reorg or departure so metric views don't end up orphaned.

**Downstream consumer notifications**
On merge of any change to a live metric view, notify its consumers (derived
from lineage) — a CI hook posting to the owning teams closes the loop with
the change-impact gate above, so people learn about a change from a
notification instead of a broken dashboard.

**Freshness/quality signal surfaced with the metric**
Tie the existing `silver.data_quality_log` pattern in this repo (or the
materialization refresh health from §7) into the metric view's presentation
layer, so a stale or low-quality upstream load is visible to whoever's
looking at the number — not only to the pipeline's own internal monitoring.

---

## Sequenced rollout (from single-workspace to enterprise multi-workspace)

1. **Metastore & workspace provisioning** — confirm/create the regional
   metastore; provision dev/staging/prod workspaces (function split only if
   justified); set up catalog-to-workspace bindings.
2. **Identity foundation** — SCIM connector from IdP to account console;
   recreate existing groups as IdP-synced groups.
3. **Network & secrets** — PrivateLink/VNet per workspace as required,
   secret scopes backed by cloud secrets manager, OIDC federation for CI
   service principals (one per environment workspace).
4. **Extend the bundle** — add workspace-per-environment targets; add the
   Genie-space/dashboard deploy tasks that now need per-workspace
   redeployment alongside the UC-layer deploy.
5. **Extend CI/CD** — promotion pipeline deploys to a new workspace host per
   stage, not just a new catalog; two-layer deploy (UC objects + workspace
   objects) at each stage.
6. **Observability** — build usage/performance/cost dashboards once against
   the shared metastore's system tables, sliced by `workspace_id` and tags.
7. **Stand up governance** — semantic layer council + generated metric
   registry, before onboarding a third or fourth domain team.
8. **Onboarding runbook** — use §10 to bring each subsequent domain team on
   in a repeatable way.
9. **Lifecycle processes** — wire in the §12 practices (schema-contract
   tests, regression testing, deprecation workflow, lineage-driven change
   notifications) before the first live metric view accumulates real
   downstream dependents, not after.

---

## 13. Alternate rollout: access-last sequencing (monorepo)

The default rollout above treats identity/access (§5) as an early
prerequisite — grants need groups to assign to as each catalog/schema is
created. Some organizations instead want the fine-grained access model
(SCIM, layered grants, least-privilege service principals, row/column
security) deferred to the end, building the rest of the platform first under
a single broad-scope bootstrap credential. This is workable in a **monorepo**
specifically, because CODEOWNERS + PR review substitutes as an interim,
soft access control while UC-level grants aren't yet locked down.

One clarification before the sequence: "access-last" cannot mean zero
access to start — creating catalogs, deploying bundles, and running CI all
require *some* credential with broad admin rights. What's deferred is
replacing that bootstrap credential with the real, scoped-down model from
§5 and §3's OIDC federation.

| # | Phase | What changed from the default order |
|---|---|---|
| 1 | **Metastore & workspace provisioning** | Unchanged — still first, done under the bootstrap admin credential |
| 2 | **Monorepo & bundle scaffolding** | Moved up (was implicit in §3/§10). One repo, domain-scoped folders, bundle template, dev/staging/prod targets |
| 3 | **CI/CD pipeline, provisional auth** | Moved up from the default §5. Build the full validate → dev → staging → prod pipeline now, but with **one broad-scope credential across every stage**, explicitly flagged as provisional and slated for replacement in phase 9 |
| 4 | **Author & prove out metric views + Genie content** | New. Get the semantic layer working end to end across the monorepo. CODEOWNERS + PR review is the interim access control — path-based review substitutes for UC-level domain isolation while that isolation doesn't exist yet |
| 5 | **Observability (usage, performance, cost)** | Moved up from the default §6, deliberately *before* locking access down. `system.access.audit` and lineage capture real usage during the open-access build phase — evidence for the grant model instead of a guess |
| 6 | **Governance operating model (council + metric registry)** | Moved up from the default §9. Use the phase-5 usage data to catch shadow/duplicate metrics and settle real domain boundaries before they're hardened into grants — cheaper to fix a boundary now than after it's access-controlled |
| 7 | **Lifecycle processes** | Moved up from §12. Easier to bake into CI while the pipeline is still one credential and one repo, before phase 9 adds the deploy-identity-vs-query-identity distinction |
| 8 | **Onboarding runbook** | Finalized now, written to forward-reference the access-request step about to exist in phase 9 |
| 9 | **Access management (deferred, now last)** | See breakdown below |

**Phase 9 breakdown:**

1. **Identity foundation** — SCIM connector + groups, sized from the real
   usage data gathered in phase 5 instead of a priori assumptions.
2. **Layered grant model** — domain-owned schemas, `SELECT`-only grants on
   metric views, revoke direct gold-table access.
3. **Least-privilege service principals** — replace the single provisional
   CI credential from phase 3 with per-environment scoped SPs; test against
   dev and staging before cutting prod over.
4. **Network & secrets hardening** — OIDC federation replacing the
   provisional token, secret scopes backed by the cloud secrets manager,
   PrivateLink/VNet.
5. **Row/column security & attribute tagging** for PII/regulated fields.
6. **Cutover verification** — before revoking the original bootstrap
   credential, diff the new scoped grants against the phase-5 usage data to
   confirm every real consumer is still covered. Revoke broad access only
   after that check passes, not on a fixed date.

**The risk worth naming**: this ordering is a legitimate "get it working,
then govern it" pattern, but it's also the classic setup for silent breakage
on cutover — something built or tested in phases 2–8 quietly depends on the
broad bootstrap credential, and revoking it in phase 9 breaks that thing
with no warning. The mitigation is step 6 above: don't cut over on a fixed
date — roll the scoped grants out **in parallel** with the broad credential,
verify coverage against the observability data, and only then retire it.
That verification step is what makes deferring access safe rather than just
convenient.
