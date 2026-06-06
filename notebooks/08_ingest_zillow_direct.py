# Databricks notebook source
# MAGIC %md
# MAGIC # 08 - Ingest: Zillow ZORI direct download into volume
# MAGIC
# MAGIC **Why this notebook exists:**
# MAGIC Zillow's CDN (CloudFlare) blocks GitHub Actions IP ranges, so the weekly
# MAGIC acquisition workflow cannot download ZORI files. Classic Databricks compute
# MAGIC clusters have unrestricted outbound internet, so this notebook fetches
# MAGIC directly into the volume.
# MAGIC
# MAGIC **Run cadence:** Monthly — Zillow publishes new ZORI data once a month.
# MAGIC Run this notebook manually, then re-run 07_bronze_zillow_rent and
# MAGIC 32_silver_rent_index to refresh the gold layer.
# MAGIC
# MAGIC **Writes to:**
# MAGIC - /Volumes/workspace/landing/raw/zillow/zori_county.csv
# MAGIC - /Volumes/workspace/landing/raw/zillow/zori_zip.csv

# COMMAND ----------

import os
import requests

VOLUME_PATH = "/Volumes/workspace/landing/raw/zillow"
os.makedirs(VOLUME_PATH, exist_ok=True)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Referer":         "https://www.zillow.com/research/data/",
    "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

SOURCES = [
    {
        "name": "zori_county",
        "url":  "https://files.zillowstatic.com/research/public_csvs/zori/County_ZORI_AllHomesPlusMultifamily_Smoothed.csv",
        "out":  f"{VOLUME_PATH}/zori_county.csv",
    },
    {
        "name": "zori_zip",
        "url":  "https://files.zillowstatic.com/research/public_csvs/zori/Zip_ZORI_AllHomesPlusMultifamily_Smoothed.csv",
        "out":  f"{VOLUME_PATH}/zori_zip.csv",
    },
]

# COMMAND ----------

for src in SOURCES:
    print(f"Downloading {src['name']}...")
    r = requests.get(src["url"], headers=HEADERS, timeout=300)
    r.raise_for_status()
    with open(src["out"], "wb") as f:
        f.write(r.content)
    size_mb = len(r.content) / 1_048_576
    print(f"  -> {src['out']}  ({size_mb:.1f} MB)")

print("\nDone. Run 07_bronze_zillow_rent -> 32_silver_rent_index -> 42_gold_rent_vs_buy next.")

# COMMAND ----------

# Verify files landed correctly
for src in SOURCES:
    size = os.path.getsize(src["out"])
    print(f"{src['name']}: {size:,} bytes  at  {src['out']}")
