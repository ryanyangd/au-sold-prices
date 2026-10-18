# Databricks notebook source
# Ingest: download the source archive into a Unity Catalog volume (the raw zone).
# Skips the download when this source version is already there. If the source is unreachable
# but an earlier file (or a manual upload) exists, the pipeline continues with that file.

# COMMAND ----------

import glob
import os
import sys

sys.path.append(os.path.abspath("../../src"))

from au_sold_prices.pipeline.ingest import IngestError, PathStore, run_ingest

dbutils.widgets.text("catalog", "")
dbutils.widgets.text("source_url", "https://nswpropertysalesdata.com/data/archive.zip")

catalog = dbutils.widgets.get("catalog")
source_url = dbutils.widgets.get("source_url")
assert catalog, "catalog widget is required"

spark.sql(f"CREATE SCHEMA IF NOT EXISTS {catalog}.bronze")
spark.sql(f"CREATE VOLUME IF NOT EXISTS {catalog}.bronze.raw")
root = f"/Volumes/{catalog}/bronze/raw"

# COMMAND ----------

try:
    result = run_ingest(source_url, PathStore(root))
    print(result)
    if result["stale"]:
        print("WARNING: the source has not been updated for over 14 days")
except IngestError as exc:
    existing = glob.glob(f"{root}/nsw_psi/*/_manifest.json")
    if not existing:
        raise
    print(f"WARNING: download failed ({exc}); continuing with {len(existing)} existing file(s)")
