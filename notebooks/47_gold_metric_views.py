# Databricks notebook source
# MAGIC %md
# MAGIC # 47 - Gold: Metric Views (county_market_monthly, affordability_monthly,
# MAGIC # market_health_score, supply_demand_signals)
# MAGIC
# MAGIC Governed Unity Catalog metric views over the 4 remaining SCD2 gold marts,
# MAGIC following the exact pattern already proven in
# MAGIC `workspace.gold.zip_hotspots_metric_view` (confirmed live via
# MAGIC `SHOW CREATE TABLE`): `version: 1.1`, a top-level `filter: is_current =
# MAGIC true` (not a per-measure filter), plain-column dimensions, and
# MAGIC `MEASURE()`-compatible aggregate expressions.
# MAGIC
# MAGIC **Views created:**
# MAGIC - gold.county_market_monthly_metric_view
# MAGIC - gold.affordability_monthly_metric_view
# MAGIC - gold.market_health_score_metric_view
# MAGIC - gold.supply_demand_signals_metric_view
# MAGIC
# MAGIC **Dimensions:** all four tables share `county_fips` + `date_key` as their
# MAGIC SCD2 grain, same shape as `zip_hotspots`.
# MAGIC
# MAGIC **Note on AVG measures:** `AVG` over an already-aggregated per-row column
# MAGIC (e.g. `median_sale_price`, itself a monthly county aggregate) re-averages
# MAGIC unweighted across whatever grain a query groups by — not a defect, just
# MAGIC not population-weighted. Worth remembering when reading results grouped
# MAGIC above the county/month grain.

# COMMAND ----------

CATALOG = "workspace"
GOLD = "gold"

# COMMAND ----------

# MAGIC %md
# MAGIC ## county_market_monthly_metric_view

# COMMAND ----------

county_market_monthly_yaml = """
version: 1.1

source: workspace.gold.county_market_monthly

filter: is_current = true

dimensions:
  - name: county_fips
    expr: county_fips
    comment: County FIPS code
    display_name: County FIPS

  - name: date_key
    expr: date_key
    comment: Month of the observation
    display_name: Date

measures:
  - name: avg_median_sale_price
    expr: AVG(median_sale_price)
    comment: Average of monthly median sale price
    display_name: Avg Median Sale Price

  - name: avg_median_list_price
    expr: AVG(median_list_price)
    comment: Average of monthly median list price
    display_name: Avg Median List Price

  - name: avg_hpi_index
    expr: AVG(hpi_index)
    comment: Average House Price Index
    display_name: Avg HPI Index

  - name: avg_list_vs_sale_gap
    expr: AVG(list_vs_sale_gap)
    comment: Average gap between list price and sale price
    display_name: Avg List vs Sale Gap

  - name: total_active_listings
    expr: SUM(active_listings)
    comment: Total active listings across the grouped period
    display_name: Total Active Listings

  - name: total_new_listings
    expr: SUM(new_listings)
    comment: Total new listings across the grouped period
    display_name: Total New Listings

  - name: total_pending_listings
    expr: SUM(pending_listings)
    comment: Total pending listings across the grouped period
    display_name: Total Pending Listings

  - name: pending_to_active_ratio
    expr: "SUM(pending_listings) / NULLIF(SUM(active_listings), 0)"
    comment: Pending listings relative to active inventory
    display_name: Pending to Active Ratio
    format:
      type: percentage
      decimal_places:
        type: exact
        places: 1

  - name: avg_months_of_supply
    expr: AVG(months_of_supply)
    comment: Average months of housing supply
    display_name: Avg Months of Supply

  - name: avg_days_on_market
    expr: AVG(median_dom)
    comment: Average days on market
    display_name: Avg Days on Market

  - name: avg_sale_to_list_ratio
    expr: AVG(sale_to_list_ratio)
    comment: Average sale-to-list price ratio
    display_name: Avg Sale to List Ratio

  - name: avg_sold_above_list_pct
    expr: AVG(sold_above_list_pct)
    comment: Average percent of homes sold above list price
    display_name: Avg Sold Above List Pct

  - name: avg_price_per_sqft
    expr: AVG(price_per_sqft)
    comment: Average price per square foot
    display_name: Avg Price per Sqft

  - name: avg_price_mom
    expr: AVG(price_mom)
    comment: Average month-over-month price change
    display_name: Avg Price MoM

  - name: avg_price_yoy
    expr: AVG(price_yoy)
    comment: Average year-over-year price change
    display_name: Avg Price YoY

  - name: county_month_count
    expr: COUNT(1)
    comment: Number of county-month rows in the group
    display_name: County-Month Count
"""

spark.sql(f"""
CREATE OR REPLACE VIEW {CATALOG}.{GOLD}.county_market_monthly_metric_view
WITH METRICS
LANGUAGE YAML
AS $${county_market_monthly_yaml}$$
""")

print("Created gold.county_market_monthly_metric_view")

# COMMAND ----------

display(spark.sql(f"""
SELECT county_fips, MEASURE(avg_median_sale_price) AS avg_price,
       MEASURE(total_active_listings) AS active
FROM {CATALOG}.{GOLD}.county_market_monthly_metric_view
GROUP BY ALL ORDER BY ALL
"""))

# COMMAND ----------

# MAGIC %md
# MAGIC ## affordability_monthly_metric_view

# COMMAND ----------

affordability_monthly_yaml = """
version: 1.1

source: workspace.gold.affordability_monthly

filter: is_current = true

dimensions:
  - name: county_fips
    expr: county_fips
    comment: County FIPS code
    display_name: County FIPS

  - name: date_key
    expr: date_key
    comment: Month of the observation
    display_name: Date

measures:
  - name: avg_median_sale_price
    expr: AVG(median_sale_price)
    comment: Average of monthly median sale price
    display_name: Avg Median Sale Price

  - name: avg_mortgage_rate
    expr: AVG(mortgage_rate)
    comment: Average 30-year mortgage rate
    display_name: Avg Mortgage Rate

  - name: avg_median_income
    expr: AVG(median_income)
    comment: Average median household income
    display_name: Avg Median Income

  - name: avg_monthly_payment
    expr: AVG(est_monthly_payment)
    comment: Average estimated monthly mortgage payment
    display_name: Avg Monthly Payment

  - name: avg_affordability_index
    expr: AVG(affordability_index)
    comment: Average affordability index
    display_name: Avg Affordability Index

  - name: avg_price_to_income_ratio
    expr: AVG(price_to_income_ratio)
    comment: Average price-to-income ratio
    display_name: Avg Price to Income Ratio

  - name: county_month_count
    expr: COUNT(1)
    comment: Number of county-month rows in the group
    display_name: County-Month Count
"""

spark.sql(f"""
CREATE OR REPLACE VIEW {CATALOG}.{GOLD}.affordability_monthly_metric_view
WITH METRICS
LANGUAGE YAML
AS $${affordability_monthly_yaml}$$
""")

print("Created gold.affordability_monthly_metric_view")

# COMMAND ----------

display(spark.sql(f"""
SELECT county_fips, MEASURE(avg_affordability_index) AS avg_afford
FROM {CATALOG}.{GOLD}.affordability_monthly_metric_view
GROUP BY ALL ORDER BY ALL
"""))

# COMMAND ----------

# MAGIC %md
# MAGIC ## market_health_score_metric_view

# COMMAND ----------

market_health_score_yaml = """
version: 1.1

source: workspace.gold.market_health_score

filter: is_current = true

dimensions:
  - name: county_fips
    expr: county_fips
    comment: County FIPS code
    display_name: County FIPS

  - name: date_key
    expr: date_key
    comment: Month of the observation
    display_name: Date

measures:
  - name: avg_days_on_market
    expr: AVG(median_dom)
    comment: Average days on market
    display_name: Avg Days on Market

  - name: avg_sale_to_list_ratio
    expr: AVG(sale_to_list_ratio)
    comment: Average sale-to-list price ratio
    display_name: Avg Sale to List Ratio

  - name: avg_months_of_supply
    expr: AVG(months_of_supply)
    comment: Average months of housing supply
    display_name: Avg Months of Supply

  - name: avg_price_yoy
    expr: AVG(price_yoy)
    comment: Average year-over-year price change
    display_name: Avg Price YoY

  - name: avg_affordability_index
    expr: AVG(affordability_index)
    comment: Average affordability index
    display_name: Avg Affordability Index

  - name: avg_dom_score
    expr: AVG(dom_score)
    comment: Average days-on-market sub-score
    display_name: Avg DOM Score

  - name: avg_sale_to_list_score
    expr: AVG(sale_to_list_score)
    comment: Average sale-to-list sub-score
    display_name: Avg Sale to List Score

  - name: avg_supply_score
    expr: AVG(supply_score)
    comment: Average supply sub-score
    display_name: Avg Supply Score

  - name: avg_momentum_score
    expr: AVG(momentum_score)
    comment: Average momentum sub-score
    display_name: Avg Momentum Score

  - name: avg_affordability_score
    expr: AVG(affordability_score)
    comment: Average affordability sub-score
    display_name: Avg Affordability Score

  - name: avg_market_health_score
    expr: AVG(market_health_score)
    comment: Average composite market health score
    display_name: Avg Market Health Score

  - name: max_market_health_score
    expr: MAX(market_health_score)
    comment: Maximum composite market health score in the group
    display_name: Max Market Health Score

  - name: county_month_count
    expr: COUNT(1)
    comment: Number of county-month rows in the group
    display_name: County-Month Count
"""

spark.sql(f"""
CREATE OR REPLACE VIEW {CATALOG}.{GOLD}.market_health_score_metric_view
WITH METRICS
LANGUAGE YAML
AS $${market_health_score_yaml}$$
""")

print("Created gold.market_health_score_metric_view")

# COMMAND ----------

display(spark.sql(f"""
SELECT county_fips, MEASURE(avg_market_health_score) AS avg_health
FROM {CATALOG}.{GOLD}.market_health_score_metric_view
GROUP BY ALL ORDER BY ALL
"""))

# COMMAND ----------

# MAGIC %md
# MAGIC ## supply_demand_signals_metric_view

# COMMAND ----------

supply_demand_signals_yaml = """
version: 1.1

source: workspace.gold.supply_demand_signals

filter: is_current = true

dimensions:
  - name: county_fips
    expr: county_fips
    comment: County FIPS code
    display_name: County FIPS

  - name: date_key
    expr: date_key
    comment: Month of the observation
    display_name: Date

measures:
  - name: total_single_family_units
    expr: SUM(single_family_units)
    comment: Total single-family units permitted
    display_name: Total Single-Family Units

  - name: total_multi_family_units
    expr: SUM(multi_family_units)
    comment: Total multi-family units permitted
    display_name: Total Multi-Family Units

  - name: total_units_permitted
    expr: SUM(total_units_permitted)
    comment: Total units permitted
    display_name: Total Units Permitted

  - name: multi_family_share
    expr: "SUM(multi_family_units) / NULLIF(SUM(total_units_permitted), 0)"
    comment: Multi-family units as a share of all permitted units
    display_name: Multi-Family Share
    format:
      type: percentage
      decimal_places:
        type: exact
        places: 1

  - name: avg_county_unemployment_rate
    expr: AVG(county_unemployment_rate)
    comment: Average county unemployment rate
    display_name: Avg Unemployment Rate

  - name: avg_mortgage_rate
    expr: AVG(mortgage_rate)
    comment: Average 30-year mortgage rate
    display_name: Avg Mortgage Rate

  - name: avg_median_sale_price
    expr: AVG(median_sale_price)
    comment: Average of monthly median sale price
    display_name: Avg Median Sale Price

  - name: total_active_listings
    expr: SUM(active_listings)
    comment: Total active listings across the grouped period
    display_name: Total Active Listings

  - name: avg_months_of_supply
    expr: AVG(months_of_supply)
    comment: Average months of housing supply
    display_name: Avg Months of Supply

  - name: avg_price_yoy
    expr: AVG(price_yoy)
    comment: Average year-over-year price change
    display_name: Avg Price YoY

  - name: avg_national_housing_starts
    expr: AVG(national_housing_starts)
    comment: Average national housing starts
    display_name: Avg National Housing Starts

  - name: avg_nc_building_permits
    expr: AVG(nc_building_permits)
    comment: Average NC statewide building permits
    display_name: Avg NC Building Permits

  - name: county_month_count
    expr: COUNT(1)
    comment: Number of county-month rows in the group
    display_name: County-Month Count
"""

spark.sql(f"""
CREATE OR REPLACE VIEW {CATALOG}.{GOLD}.supply_demand_signals_metric_view
WITH METRICS
LANGUAGE YAML
AS $${supply_demand_signals_yaml}$$
""")

print("Created gold.supply_demand_signals_metric_view")

# COMMAND ----------

display(spark.sql(f"""
SELECT county_fips, MEASURE(total_units_permitted) AS units, MEASURE(multi_family_share) AS mf_share
FROM {CATALOG}.{GOLD}.supply_demand_signals_metric_view
GROUP BY ALL ORDER BY ALL
"""))
