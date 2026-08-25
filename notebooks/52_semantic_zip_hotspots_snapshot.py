# Databricks notebook source
# MAGIC %md
# MAGIC # 52 - Semantic: ZIP Hotspots Metrics Snapshot
# MAGIC
# MAGIC Materializes one grain (latest quarter, by ZIP) of
# MAGIC workspace.gold.zip_hotspots_metric_view into a physical Delta
# MAGIC table, so it can be synced to Lakebase — metric views can't be
# MAGIC synced directly. See docs/metric_view_lakebase_api_architecture.md.

# COMMAND ----------

spark.sql("""
CREATE SCHEMA IF NOT EXISTS workspace.semantic
""")

spark.sql("""
CREATE OR REPLACE TABLE workspace.semantic.zip_hotspots_metrics_snapshot AS
SELECT
    zip,
    zip_name,
    MEASURE(avg_days_on_market)    AS avg_days_on_market,
    MEASURE(total_active_listings) AS total_active_listings,
    MEASURE(price_reduction_rate)  AS price_reduction_rate,
    CURRENT_TIMESTAMP()            AS snapshot_generated_at
FROM workspace.gold.zip_hotspots_metric_view
WHERE quarter_start = (
    SELECT MAX(quarter_start) FROM workspace.gold.zip_hotspots WHERE is_current = true
)
GROUP BY ALL
""")

print("Snapshot written: workspace.semantic.zip_hotspots_metrics_snapshot")