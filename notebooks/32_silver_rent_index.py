# Databricks notebook source
# MAGIC %md
# MAGIC # 32 - Silver: rent_index
# MAGIC
# MAGIC **Role:** Zillow ZORI unpivoted to long format, mapped to county FIPS
# MAGIC and ZIP codes for the RDU area.
# MAGIC
# MAGIC **Tables written:**
# MAGIC - silver.rent_index_county  — (county_fips, date_key, zori)
# MAGIC - silver.rent_index_zip     — (zip, date_key, zori)
# MAGIC
# MAGIC **gold.rent_vs_buy** reads from rent_index_county.
# MAGIC **gold.zip_hotspots** can optionally join rent_index_zip.

# COMMAND ----------

from pyspark.sql import functions as F

CATALOG = "workspace"
SILVER  = f"{CATALOG}.silver"
BRONZE  = f"{CATALOG}.bronze"

# RDU county name fragments → FIPS (Zillow uses full "Wake County" style names)
RDU_COUNTY_FIPS = {
    "Wake":      "37183",
    "Durham":    "37063",
    "Orange":    "37135",
    "Johnston":  "37101",
    "Chatham":   "37037",
    "Franklin":  "37069",
    "Granville": "37077",
    "Person":    "37145",
}

# COMMAND ----------

# MAGIC %md
# MAGIC ## Part 1 — County ZORI: unpivot + FIPS mapping

# COMMAND ----------

county_bronze = spark.table(f"{BRONZE}.zillow_zori_county")

# Identify metadata vs date columns
META_COLS = ["RegionID", "SizeRank", "RegionName", "RegionType",
             "StateName", "State", "Metro", "CountyName"]
meta_cols  = [c for c in county_bronze.columns if c in META_COLS]
date_cols  = [c for c in county_bronze.columns if c not in META_COLS
              and len(c) == 7 and c[4] == "-"]   # YYYY-MM pattern

print(f"Metadata columns: {len(meta_cols)}")
print(f"Date columns: {len(date_cols)}  ({date_cols[0]} → {date_cols[-1]})")

# COMMAND ----------

# Unpivot wide → long using stack()
stack_expr = (
    f"stack({len(date_cols)}, "
    + ", ".join([f"'{c}', `{c}`" for c in date_cols])
    + ") AS (month_str, zori)"
)

county_long = (county_bronze
    .selectExpr(*[f"`{c}`" for c in meta_cols], stack_expr)
    .filter("zori IS NOT NULL")
    .withColumn("zori",    F.col("zori").cast("double"))
    .withColumn("date_key", F.to_date(F.concat_ws("-", F.col("month_str"), F.lit("01"))))
    .drop("month_str"))

# COMMAND ----------

# Map county name → FIPS using contains() — handles "Wake County", "Wake", etc.
fips_expr = F.lit(None).cast("string")
for name, fips in RDU_COUNTY_FIPS.items():
    fips_expr = F.when(F.col("RegionName").contains(name), fips).otherwise(fips_expr)

county_rdu = (county_long
    .withColumn("county_fips", fips_expr)
    .filter(F.col("county_fips").isNotNull())
    .select(
        F.col("county_fips"),
        F.col("date_key"),
        F.round(F.col("zori"), 2).alias("zori"),
        F.col("RegionName").alias("region_name"),
        F.current_timestamp().alias("_ingested_at"),
    )
    .orderBy("county_fips", "date_key"))

print(f"RDU county rent rows: {county_rdu.count()}")
display(county_rdu.limit(10))

# COMMAND ----------

(county_rdu.write
 .format("delta")
 .mode("overwrite")
 .option("overwriteSchema", "true")
 .saveAsTable(f"{SILVER}.rent_index_county"))

print("Wrote silver.rent_index_county")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Part 2 — ZIP ZORI: unpivot + filter to NC ZIPs

# COMMAND ----------

zip_bronze = spark.table(f"{BRONZE}.zillow_zori_zip")

ZIP_META_COLS = ["RegionID", "SizeRank", "RegionName", "RegionType",
                 "StateName", "State", "Metro", "City", "CountyName"]
zip_meta  = [c for c in zip_bronze.columns if c in ZIP_META_COLS]
zip_dates = [c for c in zip_bronze.columns if c not in ZIP_META_COLS
             and len(c) == 7 and c[4] == "-"]

print(f"ZIP date columns: {len(zip_dates)}  ({zip_dates[0]} → {zip_dates[-1]})")

# COMMAND ----------

zip_stack = (
    f"stack({len(zip_dates)}, "
    + ", ".join([f"'{c}', `{c}`" for c in zip_dates])
    + ") AS (month_str, zori)"
)

zip_long = (zip_bronze
    .selectExpr(*[f"`{c}`" for c in zip_meta], zip_stack)
    .filter("zori IS NOT NULL")
    .withColumn("zori",     F.col("zori").cast("double"))
    .withColumn("date_key", F.to_date(F.concat_ws("-", F.col("month_str"), F.lit("01"))))
    .drop("month_str")
    .select(
        F.col("RegionName").alias("zip"),
        F.col("date_key"),
        F.round(F.col("zori"), 2).alias("zori"),
        F.col("City").alias("city"),
        F.col("CountyName").alias("county_name"),
        F.current_timestamp().alias("_ingested_at"),
    ))

print(f"NC ZIP rent rows: {zip_long.count()}")
display(zip_long.orderBy(F.col("date_key").desc()).limit(10))

# COMMAND ----------

(zip_long.write
 .format("delta")
 .mode("overwrite")
 .option("overwriteSchema", "true")
 .saveAsTable(f"{SILVER}.rent_index_zip"))

print("Wrote silver.rent_index_zip")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Validation

# COMMAND ----------

display(
    spark.table(f"{SILVER}.rent_index_county")
    .filter(F.col("date_key") >= "2022-01-01")
    .groupBy("county_fips", "region_name")
    .agg(
        F.count("*").alias("months"),
        F.round(F.avg("zori"), 0).alias("avg_zori"),
        F.max("date_key").alias("latest_month"),
    )
    .orderBy("county_fips"))
