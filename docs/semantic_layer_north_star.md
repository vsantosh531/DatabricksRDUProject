# Semantic Layer Platform — North Star

A one-page reference for **why** this initiative exists and what "done"
looks like. Stable, stakeholder-facing, rarely edited. For **how** to build
it, see `docs/semantic_layer_platform_architecture.md` (single-workspace
design) and `docs/enterprise_semantic_layer_infra.md` (multi-workspace,
enterprise design) — this document links out to those rather than
duplicating their detail.

---

## Vision

One governed semantic layer, defined once in Unity Catalog, consumed
identically by every dashboard, Genie space, and BI tool — so "what's our
months of supply this quarter" gets the same answer whether it's asked in
Power BI, an AI/BI dashboard, or a natural-language Genie question.

---

## Business value

This isn't infrastructure for its own sake — each piece maps to a cost the
organization is already paying without it:

- **Fewer "whose number is right" meetings.** Every duplicate metric
  definition (one in a Power BI DAX measure, one in a notebook, one in a
  Genie space) is a future reconciliation argument. A single governed
  definition removes the argument at the source instead of resolving it
  after the fact in a meeting.
- **Faster self-service, less BI backlog.** Business users get answers from
  Genie directly instead of filing a ticket and waiting for an analyst to
  write SQL — the analyst's time shifts from repetitive report requests to
  higher-value work.
- **Metric logic written once, not N times.** Without a semantic layer, the
  same ratio (months of supply, price-to-income, affordability index) gets
  reimplemented per dashboard, per tool, per team — each copy a chance to
  drift. One governed definition is less code to write and less code to
  keep correct.
- **Lower compliance and audit cost.** Centralized grants, an audit trail
  (`system.access.audit`), and PII masking at the source mean an access
  review or a compliance audit is a query against system tables, not a
  multi-week manual survey of who has access to what.
- **Faster time-to-value for new teams.** A domain team onboarding through
  the shared template and CI pipeline gets to a governed, production metric
  view in roughly a sprint (see the rollout in the infra doc) instead of
  building their own BI stack from scratch.
- **Spend visibility instead of surprise bills.** Usage-informed
  materialization and tag-based cost attribution mean compute spend is
  traceable to the team and metric driving it, not discovered after the
  fact on an invoice.
- **Bad numbers caught before they reach a decision-maker.** Parity and
  regression testing on every metric-view change catches silent drift in
  CI — the alternative is an executive making a call off a dashboard number
  that quietly stopped matching the source system.
- **Reuse compounds — the platform is a one-time cost, not a recurring one.**
  Building the shared template, CI/CD pipeline, and access model costs
  roughly 4–5 sprints, once (see the Jira backlog's E0–E3 estimates). Every
  domain after the first onboards in roughly a sprint through the exact
  same pipeline, unchanged — and observability, cost attribution, and
  governance review need **zero additional setup per domain**, since
  they're built against the shared metastore, not rebuilt per team. The
  fifth domain onboarded isn't proportionally more expensive than the
  second, which is the actual test of "platform" versus "one-off project."

---

## Problem / why now

Two BI surfaces (an external enterprise BI tool and Databricks-native AI/BI)
reading the same gold tables independently is a governance gap waiting to
open: nothing currently stops the same KPI from being defined twice, slightly
differently, in each. Genie amplifies this — the easier it becomes for
non-engineers to author a metric conversationally, the more entry points
exist for that drift to happen, unless every entry point converges on the
same reviewed, tested definition.

---

## Guiding principles

- **Unity Catalog is the single source of truth** for metric definitions —
  not a dashboard's local calculated field, not a Genie-specific answer.
- **Consumers never touch gold tables directly** — `SELECT` is granted on
  the metric view, not the source table, so the semantic layer is the
  access path, not an optional convenience.
- **Genie is an authoring UX, not a deployment path** — every
  Genie-assisted metric view converges on the same PR/CI gate as
  hand-written YAML before it reaches staging or prod.
- **Environments are catalogs; workspaces are blast-radius boundaries** —
  the two are independent axes, sized to the org's actual isolation needs,
  not conflated.
- **Every certified measure has a parity test** against an independent
  source of truth, run on every change — not just at creation.
- **Metadata is not optional** — `comment`/`synonyms`/`format` are required
  on every measure, because they're what makes Genie's answers trustworthy,
  not documentation for its own sake.

---

## Target end-state

A regional metastore serving environment-scoped workspaces, each catalog
bound only to the workspaces allowed to see it; domain teams authoring
metric views (YAML or Genie-assisted) through a shared bundle template and
CI/CD pipeline; certified views feeding AI/BI dashboards, Genie spaces, and
external BI identically; usage, performance, and cost observable from one
set of dashboards over Unity Catalog system tables. Full detail:
`docs/enterprise_semantic_layer_infra.md`.

---

## Success metrics

- % of production dashboards and Genie answers backed by a **certified**
  metric view (target: rising toward 100% for the domains onboarded).
- Time to onboard a new domain team to a live, governed metric view (target:
  ~1 sprint once the template/pipeline are proven).
- Parity/regression test pass rate on metric-view changes (target: 100% —
  a failing parity test should always block merge, never be overridden).
- Count of shadow-metric duplicates caught by the semantic layer council
  before reaching the prod catalog namespace (a *rising* early count is
  healthy — it means the review gate is working; the target over time is a
  falling count as domains internalize the registry).
- Materialized metric views with near-zero query volume (target: trending to
  zero — each one is unreviewed spend).

---

## Scope for v1

**In**: one pilot domain live end-to-end (metric views, CI/CD, observability,
Genie space), the shared bundle template, the CI/CD pipeline with parity
testing, basic usage/cost observability.

**Out for v1** (explicitly deferred, not forgotten): row/column-level
security beyond the pilot's needs, a second domain onboarded, materialization
tuning beyond the pilot's dashboards, the full semantic layer council
process (a lightweight version is enough until a third domain joins).

---

## Roadmap at a glance

A fast walking-skeleton demo (days, not sprints) → Topology hardening →
Platform enablement (template + CI/CD) → Second domain onboarded, in
parallel with observability and governance stand-up → Hardening (lifecycle
processes). Real sequencing, sprint estimates, and the access-last
alternative live in `docs/enterprise_semantic_layer_infra.md` §14; the
story-level backlog is in `docs/semantic_layer_jira_backlog.md`.

---

## Ownership

- **Platform team** — metastore/workspace topology, the bundle template, the
  CI/CD pipeline, observability dashboards.
- **Domain teams** — their own metric views, Genie space content, responding
  to their CI's parity-test failures.
- **Semantic layer council** — reviews new certified metrics for
  duplication before they enter the shared prod namespace.

---

## Related documents

- `docs/bi_serving_layer.md` — the two BI serving approaches this platform
  supports.
- `docs/semantic_layer_platform_architecture.md` — single-workspace /
  Databricks Free Edition implementation reference.
- `docs/enterprise_semantic_layer_infra.md` — multi-workspace enterprise
  implementation reference, including the sprint estimate and the
  access-last rollout variant.
