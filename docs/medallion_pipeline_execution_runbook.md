# Medallion Pipeline Execution Runbook

How to run all 32 notebooks across bronze, silver, and gold in the correct
order, using the Databricks CLI. Implements the ordering statement in
`docs/ingestion_architecture.md` ("A Databricks Workflow runs the bronze
notebooks, then silver, then gold") with actual commands — that doc
explains *why* the pipeline is shaped this way; this one is *how* to
actually run it end to end. This manual path has since been superseded by
a real orchestration job (`resources/medallion_pipeline_job.yml`,
deployed via `databricks bundle deploy`) — kept here as the reference for
what that job's tasks actually do, and as a fallback if you need to run a
subset by hand.

Each tier depends on state the previous tier created — don't skip ahead.

---

## Prerequisites

- Databricks CLI installed and authenticated (`databricks auth profiles`
  should show `DEFAULT` as `Valid: YES`).
- The ingestion volume already has source folders landed — confirm with
  `databricks fs ls dbfs:/Volumes/workspace/landing/raw -p DEFAULT`. If a
  source folder is missing or empty, that source's acquisition step (see
  `docs/ingestion_architecture.md`) needs to run first; this runbook
  assumes acquisition already happened, not that it's part of this flow.

## Where to run these commands

A terminal on your own computer — Terminal.app, iTerm, or a VS Code
terminal panel all work identically. Not a notebook, not the Databricks
web UI, not CI.

## How to run these instructions

- Run tier by tier, top to bottom: all of bronze, then all of silver,
  then gold in the specific order given (not any order) — gold has a real
  dependency chain the other two tiers don't.
- Every command uses `-p DEFAULT`; substitute your profile name if
  different.
- `jobs submit` waits for completion by default (no `--no-wait`), so
  looping through a tier's notebooks sequentially is naturally safe —
  each finishes before the next starts.
- Commands are safe to re-run — `workspace import --overwrite` replaces
  cleanly, and a re-run job submission doesn't duplicate anything.

---

## The three tiers, in order

**Bronze (13 notebooks) — independent of each other, any order within the
tier, but the whole tier must finish before silver starts:**

```
01_bronze_fhfa            02_bronze_redfin         03_bronze_fred
04_bronze_census          05_bronze_wake           06_bronze_nc_parcels
06_bronze_realtor         07_bronze_census_housing 07_bronze_zillow_rent
08_bronze_bps             08_ingest_zillow_direct  09_bronze_bls_laus
10_bronze_fred_indicators
```

**Silver (12 notebooks) — independent of each other (confirmed by
grepping for cross-references to other silver tables — none exist), any
order within the tier, but the whole tier must finish before gold starts:**

```
20_silver_dim_geography      21_silver_dim_metro       22_silver_dim_date
23_silver_home_prices        24_silver_market_activity 25_silver_rentals
26_silver_demographics       27_silver_economic_indicators
28_silver_building_permits   29_silver_parcel_sales
30_silver_data_quality_log   32_silver_rent_index
```

**Gold (7 notebooks) — real dependency chain, confirmed by grepping which
gold tables each notebook reads. Run in this exact order:**

```
40_gold_county_market_monthly    (foundation, no gold dependency)
41_gold_affordability_monthly    (needs 40)
42_gold_rent_vs_buy               (needs 41)
43_gold_market_health_score       (needs 40 + 41)
44_gold_supply_demand_signals     (needs 40)
45_gold_assessor_vs_market        (independent)
46_gold_zip_hotspots              (independent)
```

The numeric filenames already encode this correctly — running 40 through
46 in order satisfies every dependency.

---

## CLI execution pattern

```bash
run_notebook() {
  local nb=$1
  databricks workspace import "/Workspace/Users/venkatana.kanchibhotla@gmail.com/$nb" \
    --file "notebooks/$nb.py" --language PYTHON --format SOURCE --overwrite -p DEFAULT
  databricks jobs submit --json "{
    \"run_name\": \"$nb\",
    \"tasks\": [{\"task_key\": \"run\", \"notebook_task\": {\"notebook_path\": \"/Workspace/Users/venkatana.kanchibhotla@gmail.com/$nb\"}}]
  }" -p DEFAULT
}

# Bronze
for nb in 01_bronze_fhfa 02_bronze_redfin 03_bronze_fred 04_bronze_census \
          05_bronze_wake 06_bronze_nc_parcels 06_bronze_realtor \
          07_bronze_census_housing 07_bronze_zillow_rent \
          08_bronze_bps 08_ingest_zillow_direct 09_bronze_bls_laus \
          10_bronze_fred_indicators; do
  run_notebook "$nb"
done

# Silver — only start after every bronze run above has completed
for nb in 20_silver_dim_geography 21_silver_dim_metro 22_silver_dim_date \
          23_silver_home_prices 24_silver_market_activity 25_silver_rentals \
          26_silver_demographics 27_silver_economic_indicators \
          28_silver_building_permits 29_silver_parcel_sales \
          30_silver_data_quality_log 32_silver_rent_index; do
  run_notebook "$nb"
done

# Gold — order matters here, don't reorder this list
for nb in 40_gold_county_market_monthly 41_gold_affordability_monthly \
          42_gold_rent_vs_buy 43_gold_market_health_score \
          44_gold_supply_demand_signals 45_gold_assessor_vs_market \
          46_gold_zip_hotspots; do
  run_notebook "$nb"
done
```

Run the three blocks as separate steps (not pasted as one script and
walked away from) — confirm each tier actually succeeded before starting
the next, since a silent bronze failure would make every downstream silver
and gold notebook run against stale or missing data without erroring
obviously.

---

## Superseded by a real orchestration job

Running this by hand every time was exactly the case for a proper
orchestration Job — that's now built: `resources/medallion_pipeline_job.yml`,
deployed via `databricks bundle deploy`. It's 33 tasks total: a
`pipeline_task` that triggers `events_medallion` first (a scheduling
dependency, not a data one today — see the job file's comments), then all
13 bronze tasks in parallel, 12 silver tasks each gated on every bronze
task, and the 7 gold tasks in the exact dependency chain confirmed above.
Trigger it with `databricks jobs run-now <job_id>` instead of the manual
loops in this doc. This runbook stays as the reference for what each task
actually does and as a fallback for running a subset by hand.
