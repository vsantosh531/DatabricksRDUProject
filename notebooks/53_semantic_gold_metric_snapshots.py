# Databricks notebook source
# MAGIC %md
# MAGIC # 53 - Semantic: Gold Metric View Snapshots (full history)
# MAGIC
# MAGIC Materializes full history (every county_fips x date_key row, not just
# MAGIC the latest) from the 4 metric views built in
# MAGIC `47_gold_metric_views.py` into physical Delta tables in
# MAGIC `workspace.semantic`, so they can be synced to Lakebase — metric
# MAGIC views can't be synced directly (same reason
# MAGIC `52_semantic_zip_hotspots_snapshot.py` exists for zip_hotspots, which
# MAGIC snapshots only the latest quarter; these keep full history instead,
# MAGIC since the API needs to serve time series, not just current values).
# MAGIC
# MAGIC Each snapshot's primary key for Lakebase sync is the composite
# MAGIC `(county_fips, date_key)` — every source table shares that grain.

# COMMAND ----------

spark.sql("CREATE SCHEMA IF NOT EXISTS workspace.semantic")

# COMMAND ----------

# MAGIC %md
# MAGIC ## county_market_snapshot

# COMMAND ----------

spark.sql("""
CREATE OR REPLACE TABLE workspace.semantic.county_market_snapshot AS
SELECT
    county_fips,
    date_key,
    MEASURE(avg_median_sale_price)   AS avg_median_sale_price,
    MEASURE(avg_median_list_price)   AS avg_median_list_price,
    MEASURE(avg_hpi_index)           AS avg_hpi_index,
    MEASURE(avg_list_vs_sale_gap)    AS avg_list_vs_sale_gap,
    MEASURE(total_active_listings)   AS total_active_listings,
    MEASURE(total_new_listings)      AS total_new_listings,
    MEASURE(total_pending_listings)  AS total_pending_listings,
    MEASURE(pending_to_active_ratio) AS pending_to_active_ratio,
    MEASURE(avg_months_of_supply)    AS avg_months_of_supply,
    MEASURE(avg_days_on_market)      AS avg_days_on_market,
    MEASURE(avg_sale_to_list_ratio)  AS avg_sale_to_list_ratio,
    MEASURE(avg_sold_above_list_pct) AS avg_sold_above_list_pct,
    MEASURE(avg_price_per_sqft)      AS avg_price_per_sqft,
    MEASURE(avg_price_mom)           AS avg_price_mom,
    MEASURE(avg_price_yoy)           AS avg_price_yoy,
    MEASURE(county_month_count)      AS county_month_count,
    CURRENT_TIMESTAMP()              AS snapshot_generated_at
FROM workspace.gold.county_market_monthly_metric_view
GROUP BY ALL
""")

print("Snapshot written: workspace.semantic.county_market_snapshot")

# COMMAND ----------

# MAGIC %md
# MAGIC ## affordability_snapshot

# COMMAND ----------

spark.sql("""
CREATE OR REPLACE TABLE workspace.semantic.affordability_snapshot AS
SELECT
    county_fips,
    date_key,
    MEASURE(avg_median_sale_price)     AS avg_median_sale_price,
    MEASURE(avg_mortgage_rate)         AS avg_mortgage_rate,
    MEASURE(avg_median_income)         AS avg_median_income,
    MEASURE(avg_monthly_payment)       AS avg_monthly_payment,
    MEASURE(avg_affordability_index)   AS avg_affordability_index,
    MEASURE(avg_price_to_income_ratio) AS avg_price_to_income_ratio,
    MEASURE(county_month_count)        AS county_month_count,
    CURRENT_TIMESTAMP()                AS snapshot_generated_at
FROM workspace.gold.affordability_monthly_metric_view
GROUP BY ALL
""")

print("Snapshot written: workspace.semantic.affordability_snapshot")

# COMMAND ----------

# MAGIC %md
# MAGIC ## market_health_snapshot

# COMMAND ----------

spark.sql("""
CREATE OR REPLACE TABLE workspace.semantic.market_health_snapshot AS
SELECT
    county_fips,
    date_key,
    MEASURE(avg_days_on_market)       AS avg_days_on_market,
    MEASURE(avg_sale_to_list_ratio)   AS avg_sale_to_list_ratio,
    MEASURE(avg_months_of_supply)     AS avg_months_of_supply,
    MEASURE(avg_price_yoy)            AS avg_price_yoy,
    MEASURE(avg_affordability_index)  AS avg_affordability_index,
    MEASURE(avg_dom_score)            AS avg_dom_score,
    MEASURE(avg_sale_to_list_score)   AS avg_sale_to_list_score,
    MEASURE(avg_supply_score)         AS avg_supply_score,
    MEASURE(avg_momentum_score)       AS avg_momentum_score,
    MEASURE(avg_affordability_score)  AS avg_affordability_score,
    MEASURE(avg_market_health_score)  AS avg_market_health_score,
    MEASURE(max_market_health_score)  AS max_market_health_score,
    MEASURE(county_month_count)       AS county_month_count,
    CURRENT_TIMESTAMP()               AS snapshot_generated_at
FROM workspace.gold.market_health_score_metric_view
GROUP BY ALL
""")

print("Snapshot written: workspace.semantic.market_health_snapshot")

# COMMAND ----------

# MAGIC %md
# MAGIC ## supply_demand_snapshot

# COMMAND ----------

spark.sql("""
CREATE OR REPLACE TABLE workspace.semantic.supply_demand_snapshot AS
SELECT
    county_fips,
    date_key,
    MEASURE(total_single_family_units)    AS total_single_family_units,
    MEASURE(total_multi_family_units)     AS total_multi_family_units,
    MEASURE(total_units_permitted)        AS total_units_permitted,
    MEASURE(multi_family_share)           AS multi_family_share,
    MEASURE(avg_county_unemployment_rate) AS avg_county_unemployment_rate,
    MEASURE(avg_mortgage_rate)            AS avg_mortgage_rate,
    MEASURE(avg_median_sale_price)        AS avg_median_sale_price,
    MEASURE(total_active_listings)        AS total_active_listings,
    MEASURE(avg_months_of_supply)         AS avg_months_of_supply,
    MEASURE(avg_price_yoy)                AS avg_price_yoy,
    MEASURE(avg_national_housing_starts)  AS avg_national_housing_starts,
    MEASURE(avg_nc_building_permits)      AS avg_nc_building_permits,
    MEASURE(county_month_count)           AS county_month_count,
    CURRENT_TIMESTAMP()                   AS snapshot_generated_at
FROM workspace.gold.supply_demand_signals_metric_view
GROUP BY ALL
""")

print("Snapshot written: workspace.semantic.supply_demand_snapshot")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Enable Change Data Feed (required for Lakebase Triggered/Continuous sync)

# COMMAND ----------

for tbl in [
    "county_market_snapshot",
    "affordability_snapshot",
    "market_health_snapshot",
    "supply_demand_snapshot",
]:
    spark.sql(f"""
    ALTER TABLE workspace.semantic.{tbl}
    SET TBLPROPERTIES (delta.enableChangeDataFeed = true)
    """)
    print(f"CDF enabled: workspace.semantic.{tbl}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Row-count sanity check

# COMMAND ----------

for tbl in [
    "county_market_snapshot",
    "affordability_snapshot",
    "market_health_snapshot",
    "supply_demand_snapshot",
]:
    n = spark.table(f"workspace.semantic.{tbl}").count()
    print(f"{tbl}: {n} rows")
