# Databricks notebook source
# MAGIC %md
# MAGIC # 07 - Bronze: Zillow ZORI (Observed Rent Index)
# MAGIC
# MAGIC **Layer:** Bronze
# MAGIC **Source:** Zillow Research public CSVs — no auth required.
# MAGIC - County_ZORI_AllHomesPlusMultifamily_Smoothed.csv
# MAGIC - Zip_ZORI_AllHomesPlusMultifamily_Smoothed.csv
# MAGIC
# MAGIC **Format:** Wide — each date is its own column (YYYY-MM).
# MAGIC Bronze keeps the wide format (close to raw). Silver unpivots.
# MAGIC
# MAGIC **ZORI definition:** Zillow Observed Rent Index — median observed monthly
# MAGIC rent ($/month) for all homes and multifamily units, seasonally adjusted
# MAGIC and smoothed. Comparable to what a renter would actually pay today.

# COMMAND ----------

from pyspark.sql import functions as F

CATALOG       = "workspace"
BRONZE_SCHEMA = "bronze"
COUNTY_FILE   = "/Volumes/workspace/landing/raw/zillow/zori_county.csv"
ZIP_FILE      = "/Volumes/workspace/landing/raw/zillow/zori_zip.csv"

spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.{BRONZE_SCHEMA}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## County-level ZORI

# COMMAND ----------

county_raw = (spark.read
              .option("header", "true")
              .option("inferSchema", "false")   # keep all date cols as string
              .csv(COUNTY_FILE))

print("=== County ZORI columns (first 15) ===")
for c in county_raw.columns[:15]:
    print(" ", c)
print(f"  ... ({len(county_raw.columns)} total columns)")
print(f"\nRow count (all states): {county_raw.count()}")

# Filter to NC only in bronze to keep table small
county_nc = county_raw.filter(F.col("State") == "NC")
print(f"NC rows: {county_nc.count()}")

# COMMAND ----------

(county_nc.write
 .format("delta")
 .mode("overwrite")
 .option("overwriteSchema", "true")
 .saveAsTable(f"{CATALOG}.{BRONZE_SCHEMA}.zillow_zori_county"))

print("Wrote bronze.zillow_zori_county")
display(county_nc.select(county_nc.columns[:10]).limit(5))

# COMMAND ----------

# MAGIC %md
# MAGIC ## ZIP-level ZORI

# COMMAND ----------

zip_raw = (spark.read
           .option("header", "true")
           .option("inferSchema", "false")
           .csv(ZIP_FILE))

print("=== ZIP ZORI columns (first 15) ===")
for c in zip_raw.columns[:15]:
    print(" ", c)
print(f"  ... ({len(zip_raw.columns)} total columns)")

# Filter to NC ZIPs
zip_nc = zip_raw.filter(F.col("State") == "NC")
print(f"NC ZIP rows: {zip_nc.count()}")

# COMMAND ----------

(zip_nc.write
 .format("delta")
 .mode("overwrite")
 .option("overwriteSchema", "true")
 .saveAsTable(f"{CATALOG}.{BRONZE_SCHEMA}.zillow_zori_zip"))

print("Wrote bronze.zillow_zori_zip")
display(zip_nc.select(zip_nc.columns[:10]).limit(5))
