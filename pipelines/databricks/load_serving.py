# Databricks notebook source
# Serving load: copy gold tables into Postgres (schema swap, so readers never see a partial load).
# Needs a secret scope `ausold` with key `database-url` (a Key Vault-backed scope is recommended)
# and network access from the cluster to the Postgres server.

# COMMAND ----------

# MAGIC %pip install "psycopg[binary]>=3.1"

# COMMAND ----------

import os
import sys

sys.path.append(os.path.abspath("../../src"))

from au_sold_prices.pipeline.serving import rebuild_serving

dbutils.widgets.text("catalog", "ausold")
dbutils.widgets.text("grant_select_to", "")
catalog = dbutils.widgets.get("catalog")
database_url = dbutils.secrets.get("ausold", "database-url")


def read_rows(table, columns):
    frame = spark.table(f"{catalog}.gold.{table}").select(*columns)
    for row in frame.toLocalIterator():
        yield tuple(row)


counts = rebuild_serving(database_url, read_rows, dbutils.widgets.get("grant_select_to") or None)
print(counts)
