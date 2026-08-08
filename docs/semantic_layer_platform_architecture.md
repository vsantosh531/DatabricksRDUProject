# Semantic Layer Platform Architecture — Free Edition Reference

Multi-team semantic-layer infrastructure for Unity Catalog metric views: CI/CD,
access control, usage tracking, performance monitoring, and cost (quota)
monitoring — scoped to what's actually available on **Databricks Free
Edition** (single workspace, single auto-provisioned metastore,
serverless-only, quota-bound rather than billed) with **GitHub** as the
CI/CD system. Companion to `docs/bi_serving_layer.md` (the two BI serving
approaches) and `docs/enterprise_semantic_layer_infra.md` (the full
multi-workspace version to grow into once this tier is outgrown).

Free Edition forces one structural decision that shapes every section below:
**there is one workspace and one metastore**, so "environments" can only be
simulated as separate **catalogs**, never separate workspaces. Everything
here is designed so it carries forward unchanged on upgrade — see "Upgrade
path" at the end.

---

## Feasibility at a glance

Confirm the "verify" rows in your own account/workspace console before
designing around them — don't build a section of this plan on a capability
you haven't checked.

| Capability | Free Edition status |
|---|---|
| DABs for metric views/jobs | Fully available — workspace-scoped, no account features needed |
| Terraform for catalogs/schemas/grants | Available, workspace-scoped only — no account-level metastore/workspace provisioning needed since the metastore is auto-provisioned |
| Multi-environment topology | Simulated via catalogs in the one workspace, not real workspace isolation |
| CI/CD pipeline (validate → deploy) | Fully available — GitHub Actions + Databricks CLI, same pattern as the existing `weekly-acquisition.yml` |
| Approval gates | Via GitHub Environments (required reviewers), not a Databricks-native gate |
| UC grants / access control | Fully available |
| SCIM / IdP-synced groups | **Verify** — unlikely on this tier; default to manual group creation in the workspace admin console |
| Genie spaces | Available — confirmed (serverless SQL is included in Free Edition) |
| Genie space export/import as versioned config | **Verify** before designing an automated migration flow around it |
| Service principals / OAuth M2M / OIDC federation for CI | **Verify** — fall back to a dedicated (non-personal) PAT if unavailable |
| System tables (`access.audit`, `query.history`, lineage) | **Verify enablement** on your metastore before building dashboards on them |
| `system.billing.usage` / dollar cost monitoring | Likely not meaningful — Free Edition is quota-based, not billed |
| Account-level Budgets & Alerts | Likely unavailable — no billing to budget against |

---

## 1. Foundation layer — who owns what

Two IaC tools, both scoped down to a single workspace on this tier.

| Layer | Scope | Tool | Owner |
|---|---|---|---|
| Catalog/schema/grant structure | Workspace-scoped (the one workspace's auto-provisioned metastore) | **Terraform** (`databricks` provider, workspace-level auth) | Platform-minded owner (may be one person on a small team) |
| Workspace content | Jobs, metric views, Genie spaces, dashboards | **Databricks Asset Bundles (DABs)** | Domain/analytics contributors |

No account-level Terraform is needed — there's no metastore to provision, no
workspace bindings, no budgets to configure. Terraform's whole job here is
catalogs, schemas, and grants inside the one workspace.

**Environment topology — forced, not chosen:**
Since there's one workspace, "dev/staging/prod" can only be **catalogs**,
never separate workspaces. Given Free Edition's quota limits, a pragmatic
**two-tier default (`dev`, `prod`)** is usually enough; add a `staging`
catalog only if usage patterns justify the extra quota spend. This is the
same catalog-per-environment pattern recommended at enterprise scale — Free
Edition just removes the "workspace-per-environment" alternative entirely.

---

## 2. Reusability layer — a consistent starting point for every contributor

Applies with almost no change from the general design:

- **A bundle template** (`databricks bundle init` with a custom template) —
  even for a small team, scaffolding a new metric-view project from a
  template beats copy-pasting an existing one, and it's what lets the
  structure carry forward unchanged when the team grows.
- **A single repo is fine at this scale** — a monorepo with domain-scoped
  folders under `semantic/` is simpler than multiple repos while the team is
  small; CODEOWNERS is worth adding as soon as more than one person can
  merge, even before it's strictly necessary.
- **Standards encoded in the template**: required semantic metadata
  (`comment`, `synonyms`, `format` on every measure), required `filter` for
  soft-delete/current-flag columns (this repo's `is_current` pattern),
  naming convention (`<domain>_metrics`), a mandatory parity-test stub.

---

## 3. Authoring — including the Genie path

Genie is confirmed available on Free Edition and remains an **authoring UX,
not a deployment path** — it must converge on the same review gate as
hand-written YAML.

1. **YAML-first** — write metric view YAML directly in the repo.
2. **Genie-assisted** — build or refine a metric view conversationally
   against the **`dev` catalog**, then commit the exported definition into
   the same repo structure as path 1.

Both land as a pull request and pass through the CI gate in §4 before
reaching `prod`. One Free Edition–specific caveat: automated export/import
of Genie space configuration (instructions, sample questions, verified
queries) as versioned artifacts needs verifying on this tier (see feasibility
table). If it isn't available, the fallback is manually recreating the Genie
space against the `prod` catalog once its metric views are stable, treating
the `dev`-catalog Genie space as the authoring sandbox rather than something
promoted automatically.

---

## 4. CI/CD flow

```
Author (YAML or Genie export)
    |
    v
Pull Request  ------------------> CI: validate stage
    |                              - bundle validate
    |                              - YAML lint / naming convention check
    |                              - deploy to the `dev` catalog (same workspace)
    |                              - parity tests (metric view vs. source-of-truth logic)
    |                              - semantic-metadata completeness check
    v
CODEOWNERS review (once more than one contributor merges)
    |
    v
Merge to main -------------------> CD: (optional) redeploy `dev`, smoke test
    |                              - query each measure at each declared grain
    v
GitHub Environment approval gate -> CD: deploy to `prod` catalog (tag/release-triggered)
   (required reviewers, substitutes    - grants applied (consumer groups get SELECT on view only)
    for a Databricks-native gate)      - base gold tables locked down (no direct grant to consumers)
```

The key difference from the general design: **every stage targets the same
workspace host**, only the `catalog` bundle variable changes between `dev`
and `prod` targets. That's what "simulated environments" means concretely.

Mechanics to get right even at this scale:
- **Auth**: reuse the existing `DATABRICKS_HOST`/`DATABRICKS_TOKEN` secrets
  pattern from `weekly-acquisition.yml`, but prefer a **dedicated,
  non-personal token** over a personal PAT if service principals/OAuth M2M
  are available on the account (verify first) — don't tie CI's identity to
  one person's login.
- **Approval gate**: GitHub Environments with required reviewers on the
  `prod` target is the direct substitute for a formal Databricks-side change
  gate, and it's fully available regardless of tier.
- **Parity tests are still the real quality gate** — every measure with an
  independent source of truth (e.g. `utils/financial_calcs.py`) gets a CI
  test asserting agreement, catching semantic drift before it reaches a
  dashboard or Genie answer.

---

## 5. Access control model

Same layering principle, adjusted for what's manageable on this tier:

- **Domain-scoped schemas** inside the single catalog per environment:
  `<env>.semantic.<domain>`.
- **Consumers get `SELECT` on the metric view only**, never on the
  underlying gold tables — this holds regardless of tier and shouldn't be
  skipped even at small scale.
- **Groups created manually** in the workspace admin console (SCIM/IdP sync
  is unlikely to be available — verify, but plan for manual group management
  as the default).
- **Honest limitation to flag**: with one workspace, `dev` and `prod` share
  the same admin/network boundary — isolation is enforced by catalog grants
  only, not by a separate workspace or network perimeter. A compromised
  deploy credential threatens both environments equally. This is the
  concrete cost of Free Edition's single-workspace constraint, and it's the
  first thing that changes on upgrade (see "Upgrade path").

---

## 6. Usage tracking

Same design as the general architecture, **gated on confirming system
schemas are enabled** on this metastore first (see feasibility table) — don't
build dashboards against tables that may not be populating.

If enabled:
- `system.access.audit` — every read against a metric view, by principal,
  timestamp.
- `system.query.history` — query-level detail, including Genie-generated
  queries and AI/BI dashboard refreshes.
- `system.access.table_lineage` / `column_lineage` — which dashboards, Genie
  spaces, and queries consume which metric view, for impact analysis before
  changing a definition.

If not enabled on this tier, this section is blocked until either the
schemas can be turned on or the workspace upgrades — don't substitute a
partial/manual tracking scheme that will be thrown away later; wait and
build it once, correctly.

---

## 7. Performance monitoring

Same verification caveat as §6 applies to the system-table-based pieces.
What's available regardless:

- **SQL warehouse Monitoring tab** — queueing/scaling behavior for the
  serverless warehouse serving the semantic layer, no system tables required.
- **Materialization job health**: for metric views with `materialization`
  enabled, track refresh job runs directly via job run history in the
  workspace UI/API even if the Lakeflow Jobs system tables aren't confirmed
  available.
- **Free Edition–specific concern**: quota-limited compute means
  performance monitoring here is as much about **staying inside quota** as
  about latency — watch job/query volume against Free Edition limits, not
  just response time.
- **What to materialize**: keep it minimal on this tier — materializing
  consumes quota, so reserve it for metric views backing a genuinely
  frequently-refreshed dashboard or Genie space, not by default.

---

## 8. Quota / cost monitoring

Reframed from the general design's dollar-cost model, since Free Edition is
**quota-based, not billed**:

- `system.billing.usage` and account-level Budgets & Alerts are likely
  **not available or not meaningful** on this tier (verify) — don't build
  the chargeback/showback design from the general architecture here.
- Instead, track: serverless compute quota consumption, storage quota, and
  job-run counts against Free Edition's published limits, via a lightweight
  scheduled check (a small notebook/job) that surfaces the trend rather than
  a real-time dollar figure.
- Cross-reference materialization schedules against actual usage (§6, once
  available) — a materialized metric view nobody queries is pure quota spend
  with no benefit, same principle as the dollar-cost version, just against a
  different resource.

---

## 9. Operating model

Scaled down, same principles:

- **One owner (or a small platform-minded group)** holds the bundle
  template, the shared CI workflow files, the catalog/grant structure, and
  the standards contract — even if that's one or two people rather than a
  dedicated platform team.
- **Contributors own their domain's metric views** and respond to their own
  CI parity-test failures.
- **A generated metric registry** — even at small scale, a scheduled job
  reading `INFORMATION_SCHEMA` for all metric views and publishing owner,
  domain, grain, and last-used status is worth having early; it's what
  prevents duplicate metric definitions once more than one or two people are
  contributing.
- **Deprecation policy**: once §6 is available, flag zero-usage views for
  review rather than keeping them indefinitely.

---

## Sequenced implementation process

**Phase 0 — Confirm what the tier actually gives you.** Check the account
console for service principal / OAuth M2M availability, whether system
schemas (`access`, `query`, `lineage`) are enabled on your metastore, and
whether Genie space export/import is exposed. This gates decisions in
Phases 3, 5, and 6.

**Phase 1 — Catalog foundation.** Create `dev` and `prod` catalogs (add
`staging` later only if justified) and the semantic schemas inside them, via
Terraform, applied through the same GitHub Actions + secrets pattern already
proven in `weekly-acquisition.yml`.

**Phase 2 — Bundle structure.** Move the metric view out of a notebook into
`semantic/*.yaml` as source of truth; add `databricks.yml` with `dev` and
`prod` targets pointing at the same workspace host with different `catalog`
variables.

**Phase 3 — CI pipeline.** PR → validate + deploy to `dev` automatically;
merge to `main` → deploy to `prod` gated behind a GitHub Environment with
required reviewers. Prefer a dedicated non-personal credential over a
personal PAT if Phase 0 confirms one is available.

**Phase 4 — Access control.** Create workspace groups by hand; grant
`SELECT` on semantic views only; revoke direct grants on gold tables. Fully
available regardless of Phase 0's findings — don't defer this one.

**Phase 5 — Genie.** Stand up Genie space(s) against the `prod` catalog's
semantic views once stable; automate promotion only if Phase 0 confirmed
export/import support, otherwise recreate manually.

**Phase 6 — Observability.** Build the usage dashboard only if Phase 0
confirmed system schemas are enabled; otherwise this phase stays blocked.

**Phase 7 — Quota monitoring.** Track compute/storage/job-run quota
consumption on a schedule, in place of the dollar-budget pattern.

**Phase 8 — Upgrade path.** When the team outgrows Free Edition, add real
account-level Terraform (metastore/workspace/SCIM/budgets), optionally move
from catalog-per-environment to workspace-per-environment if compliance
requires it, and swap the deploy credential for a properly federated service
principal. Everything from Phases 1–4 was built as bundle targets/variables
rather than hardcoded, so it carries forward unchanged — see
`docs/enterprise_semantic_layer_infra.md` for the full target-state design.
