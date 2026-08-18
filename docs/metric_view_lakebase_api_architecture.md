# Metric View → Lakebase → API — Architecture

Exposing this project's Unity Catalog metric view through a low-latency
HTTP API, backed by Databricks Lakebase (managed Postgres), on Databricks
Free Edition. Companion to
`docs/metric_view_lakebase_api_execution_runbook.md` (the implement/test
steps) and a third consumption surface alongside the two described in
`docs/bi_serving_layer.md`.

---

## The core tradeoff — read this before building anything

`workspace.gold.zip_hotspots_metric_view` can answer *any* `MEASURE()`
query at *any* grain its dimensions allow (`zip`, `zip_name`,
`quarter_start`) — that's the entire point of a metric view, proven
directly in `docs/semantic_layer_execution_runbook.md` Phase 2a (the same
ratio measure re-aggregates correctly whether grouped by ZIP or by
quarter).

Lakebase's Reverse ETL only syncs **physical Delta tables**, never a
metric view directly — confirmed against the live account and the
Lakebase skill's own reference docs, which describe sync sources purely
in terms of `source_table_full_name` pointing at a Delta table, with no
mention of metric views or `MEASURE()` anywhere. A metric view is a
virtual, computed-at-query-time object; Reverse ETL needs something with
rows already sitting on disk.

**So the only way to bridge them is to pick one grain, materialize it into
a physical Delta table, and sync that.** Once it's in Lakebase, the API
serves only that one baked-in grain. If a consumer wants a different
slice, that's a new snapshot table and a new sync — not a parameter on the
existing one. Re-aggregation safety, the entire value proposition of a
metric view, is gone the moment the snapshot lands. This is a real,
permanent limitation of this pattern, not a temporary one to work around
later.

**A second, easy-to-miss corollary:** `workspace.gold.zip_hotspots` is
*already* a physical Delta table. If the snapshot's chosen grain matches
the gold table's own grain (zip × quarter), the metric view adds nothing
to this pipeline — syncing `gold.zip_hotspots` directly would be simpler
and the metric view would be pure overhead. The snapshot only earns its
keep when the chosen API grain is a genuine **re-aggregation** the metric
view computes and the sync job would otherwise have to reimplement by
hand.

**The grain this design uses**: latest quarter only, by `zip_name` —
collapsing away the `quarter_start` dimension. That's a real aggregation
(`MEASURE(price_reduction_rate)` etc. re-summed across whatever the latest
quarter's rows are), not a copy of the source table's existing grain, so
it's an honest demonstration of the pattern rather than a decorative one.

---

## Architecture

```
workspace.gold.zip_hotspots_metric_view   (UC metric view, any grain, live)
              |
              | scheduled job task, after gold refresh
              v
workspace.semantic.zip_hotspots_metrics_snapshot   (physical Delta table,
              |                                      one row per ZIP,
              |                                      latest quarter only)
              | Lakebase Reverse ETL — Triggered sync
              v
Lakebase Postgres project — synced table (public schema)
              |
              | Lakebase Data API (PostgREST-compatible HTTP CRUD)
              v
        API consumer (GET only)
```

Two objects carry the whole design: the **snapshot table** (a normal
Delta table, owned and refreshed by the existing pipeline) and the
**Lakebase project** (a small, mostly-idle Postgres instance whose only
job is to mirror that one table and answer HTTP requests against it).

---

## Why the Lakebase Data API, not a custom app

Lakebase ships a built-in **Data API** — a PostgREST-compatible HTTP CRUD
layer over Postgres tables, with OAuth bearer auth and row-level security,
confirmed via the Lakebase skill's connectivity reference. For this case
— one small read-only table, no joins, no auth requirement beyond "call it
with a token" — it gets there with **zero custom backend code**.

The alternative, a custom Databricks App (Python/FastAPI or Node) with the
`lakebase` feature, is real and already proven to work on this account —
there's an existing working app, `invoice-generator-poc`, using exactly
that deploy pattern. It buys joins across multiple tables, custom auth
(API keys, rate limiting for external/non-Databricks-identity consumers),
and response shaping. None of that is a stated requirement here, so it's
documented as the upgrade path, not the default — build it only when a
real requirement shows up that RLS + PostgREST genuinely can't express.

---

## Free Edition sizing

- **Endpoint**: resize down to **0.5 / 0.5 CU** immediately after project
  creation (the default is 1 CU min/max) — this workload is a handful of
  rows behind low-traffic reads, matching the quota-consciousness theme in
  every other doc in this set.
- **Scale-to-zero**: leave the default 5-minute timeout. Cold-start
  reconnect logic is required either way (Data API and any future app
  connection both need retry-on-wake), and 5 minutes avoids waking on
  every trickle of traffic.
- **No extra branch**: skip creating a dev/test branch. Copy-on-write
  branching earns its cost on larger, riskier schema work than a
  single-table read replica of a snapshot table — working directly
  against `production` is cheaper here.
- **One database**: keep the auto-provisioned default (`databricks_postgres`).

---

## Sync mode: Triggered, not Continuous or Snapshot

- **Continuous** is wrong regardless of tier — it burns quota keeping a
  table fresh in near-real-time when the source only changes at the
  pipeline's weekly cadence.
- **Snapshot** (one-time full copy, no CDF) is the simplest match to "the
  source table is fully overwritten every run," but the exact resync
  command needs verifying live before relying on it operationally — see
  the runbook's Phase 0.
- **Triggered** needs Change Data Feed enabled on the snapshot table but
  has an unambiguous "run again on a schedule" story, and since the source
  table is tiny, its throughput ceiling is irrelevant. This is the
  default; fall back to Snapshot only if Phase 0's verification shows a
  clean resync path and Triggered proves awkward in practice.

Run the sync as a job task immediately after the snapshot task, not on an
independent schedule — this keeps Lakebase's copy tied 1:1 to real
pipeline runs instead of drifting out of sync with them.

---

## Out of scope (explicitly deferred)

- **Serving multiple grains.** One snapshot, one grain. A second grain is
  a second notebook task and a second synced table — this design doesn't
  try to generalize "any grain," since that generalized capability is
  what the live metric view over the SQL warehouse already is, at higher
  latency.
- **Historical/time-series drill-down through the API.** The snapshot is
  latest-quarter-only by construction. Per-ZIP quarterly history stays on
  the live metric view via SQL warehouse, not this API, unless the grain
  is deliberately widened later — which reopens the tradeoff above.
- **Write-back from the API into the lakehouse.** No POST/PATCH/DELETE
  support is treated as real — Reverse ETL owns this table; any write
  through the API would just be overwritten on the next Triggered sync.
- **CI/CD automation of this pipeline** (bundling the snapshot job,
  synced table, and Data API config as DABs). Build it manually once
  first, matching how this repo sequenced the semantic layer itself.
- **Auth/access hardening beyond one demo consumer role.** No per-tenant
  RLS design, no rate limiting, no API gateway.
- **Generalizing to every metric view in the semantic layer.** Scoped to
  `zip_hotspots_metric_view` only — extending the pattern elsewhere
  repeats this recipe, it isn't new design work.
- **Failure alerting** (sync failures, job failures, Data API errors) —
  a real gap once this leaves demo status, named here rather than
  silently assumed away.

---

## Related documents

- `docs/metric_view_lakebase_api_execution_runbook.md` — the phased
  implement/test steps for this design.
- `docs/semantic_layer_execution_runbook.md` — the metric view's own
  deployment and the re-aggregation proof this design depends on.
- `docs/bi_serving_layer.md` — the two existing consumption surfaces this
  is a third option alongside.
