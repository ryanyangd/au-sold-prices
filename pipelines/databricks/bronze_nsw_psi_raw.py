# Databricks notebook source
# Bronze: load the raw NSW sales CSV from the lake with Auto Loader.
# Columns stay strings and rows are untouched; only names are made safe for Delta and
# lineage columns are added. Typing, cleaning and dedupe happen in Silver.

# COMMAND ----------

import re

from pyspark.sql import functions as F

dbutils.widgets.text("lake_account", "")
dbutils.widgets.text("catalog", "ausold")

lake_account = dbutils.widgets.get("lake_account")
catalog = dbutils.widgets.get("catalog")
source_path = f"abfss://raw@{lake_account}.dfs.core.windows.net/nsw_psi/*/data.csv"
checkpoint = f"abfss://lakehouse@{lake_account}.dfs.core.windows.net/_checkpoints/bronze_nsw_psi_raw"
target = f"{catalog}.bronze.nsw_psi_raw"

spark.sql(f"CREATE SCHEMA IF NOT EXISTS {catalog}.bronze")

# COMMAND ----------


def snake(name: str) -> str:
    return re.sub(r"_+", "_", re.sub(r"[^0-9a-z]+", "_", name.lower())).strip("_")


raw = (
    spark.readStream.format("cloudFiles")
    .option("cloudFiles.format", "csv")
    .option("cloudFiles.inferColumnTypes", "false")
    .option("header", "true")
    .option("multiLine", "false")
    .load(source_path)
)

bronze = (
    raw.toDF(*[snake(c) for c in raw.columns])
    .withColumn("_source_file", F.col("_metadata.file_path"))
    .withColumn("_source_version", F.regexp_extract(F.col("_metadata.file_path"), r"nsw_psi/(\d{8})/", 1))
    .withColumn("_ingested_at", F.current_timestamp())
)

# COMMAND ----------

(
    bronze.writeStream.option("checkpointLocation", checkpoint)
    .option("mergeSchema", "true")
    .trigger(availableNow=True)
    .toTable(target)
    .awaitTermination()
)
