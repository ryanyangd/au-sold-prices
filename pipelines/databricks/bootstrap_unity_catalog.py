"""Idempotent Unity Catalog setup for a fresh workspace: storage credential, external locations
and the `ausold` catalog. Run by the deploy workflow as the identity that created the workspace.

Environment: DATABRICKS_HOST + auth (e.g. DATABRICKS_AUTH_TYPE=azure-cli), LAKE_ACCOUNT,
ACCESS_CONNECTOR_ID, and optionally CATALOG (default "ausold").

If this lacks permission (the identity is not a metastore admin), grant it or follow the manual
steps in infra/README.md; the script reports which call failed.
"""

import os
import sys

from databricks.sdk import WorkspaceClient
from databricks.sdk.errors import NotFound, ResourceAlreadyExists
from databricks.sdk.service.catalog import AzureManagedIdentityRequest


def ensure(kind: str, create, get):
    try:
        get()
        print(f"{kind}: exists")
    except NotFound:
        try:
            create()
            print(f"{kind}: created")
        except ResourceAlreadyExists:
            print(f"{kind}: exists")


def main() -> int:
    account = os.environ["LAKE_ACCOUNT"]
    connector_id = os.environ["ACCESS_CONNECTOR_ID"]
    catalog = os.environ.get("CATALOG", "ausold")
    workspace = WorkspaceClient()

    if workspace.metastores.current().metastore_id is None:
        print("This workspace has no Unity Catalog metastore; attach one first.", file=sys.stderr)
        return 1

    credential = "ausold_lake"
    ensure(
        "storage credential",
        lambda: workspace.storage_credentials.create(
            name=credential,
            azure_managed_identity=AzureManagedIdentityRequest(access_connector_id=connector_id),
        ),
        lambda: workspace.storage_credentials.get(credential),
    )

    urls = {}
    for container in ("raw", "lakehouse"):
        name = f"ausold_{container}"
        urls[container] = f"abfss://{container}@{account}.dfs.core.windows.net/"
        ensure(
            f"external location {name}",
            lambda name=name, container=container: workspace.external_locations.create(
                name=name, url=urls[container], credential_name=credential
            ),
            lambda name=name: workspace.external_locations.get(name),
        )

    ensure(
        f"catalog {catalog}",
        lambda: workspace.catalogs.create(name=catalog, storage_root=urls["lakehouse"]),
        lambda: workspace.catalogs.get(catalog),
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
