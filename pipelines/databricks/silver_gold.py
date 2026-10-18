# Databricks notebook source
# Silver and gold: run the shared SQL (src/au_sold_prices/pipeline/sql) on Spark.
# The same SQL runs locally on DuckDB, so logic is tested once with synthetic data.

# COMMAND ----------

import os
import sys

# The bundle syncs src/ next to pipelines/ (see databricks.yml).
sys.path.append(os.path.abspath("../../src"))

from au_sold_prices.pipeline.runner import Schemas, run_gold, run_silver

dbutils.widgets.text("catalog", "ausold")
catalog = dbutils.widgets.get("catalog")
schemas = Schemas(bronze=f"{catalog}.bronze", silver=f"{catalog}.silver", gold=f"{catalog}.gold")

# COMMAND ----------

run_silver(spark.sql, schemas, "spark")

# COMMAND ----------

as_of = run_gold(spark.sql, lambda query: spark.sql(query).first()[0], schemas, "spark")
print(f"gold built, data as of {as_of}")

# COMMAND ----------

# Fail the run (and trigger the alert) if the data looks broken.
counts = spark.sql(
    f"SELECT (SELECT count(*) FROM {schemas.gold}.property) AS properties, "
    f"(SELECT count(*) FROM {schemas.gold}.sale) AS sales, "
    f"(SELECT count(*) FROM {schemas.silver}.sales_rejected) AS rejected, "
    f"(SELECT count(*) FROM {schemas.silver}.sales_typed) AS typed"
).first()
assert counts.properties > 0 and counts.sales >= counts.properties, counts
assert counts.rejected <= 0.01 * counts.typed, f"too many rejected rows: {counts}"
