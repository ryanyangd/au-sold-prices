#!/usr/bin/env python3
"""Upload a local cleaned-NSW CSV into a deployed environment's Databricks volume (raw zone).

Use it for the first load, or when the public source is stale or blocked. Then run the
"Data refresh" workflow (or the Databricks job). The file never enters git.

    az login
    python scripts/upload_csv.py dev data/nsw-property-sales-data-updated20260914.csv

Needs: pip install databricks-sdk, and Contributor on the environment's Databricks workspace.
The volume is created by the first pipeline run; this script creates it if it is missing.
"""

import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path


def az_output(*args: str) -> str:
    return subprocess.run(["az", *args], check=True, capture_output=True, text=True).stdout.strip()


def main() -> int:
    if len(sys.argv) != 3 or sys.argv[1] not in ("dev", "prod"):
        print(__doc__, file=sys.stderr)
        return 2
    environment, csv_path = sys.argv[1], Path(sys.argv[2])
    if not csv_path.is_file():
        print(f"No such file: {csv_path}", file=sys.stderr)
        return 1
    with csv_path.open("rb") as handle:
        if b"Property locality" not in handle.readline():
            print("Not a cleaned NSW sales CSV (header missing).", file=sys.stderr)
            return 1

    from databricks.sdk import WorkspaceClient

    outputs = json.loads(
        az_output(
            "deployment", "sub", "show", "-n", f"ausold-{environment}",
            "--query", "properties.outputs", "-o", "json",
        )
    )
    catalog = outputs["databricksCatalog"]["value"]
    workspace = WorkspaceClient(
        host=f"https://{outputs['databricksWorkspaceUrl']['value']}",
        azure_workspace_resource_id=outputs["databricksWorkspaceId"]["value"],
        auth_type="azure-cli",
    )

    stamp = (re.findall(r"\d{8}", csv_path.name) or [datetime.now(timezone.utc).strftime("%Y%m%d")])[-1]
    root = f"/Volumes/{catalog}/bronze/raw/nsw_psi/{stamp}"
    if not _exists(workspace.schemas.get, f"{catalog}.bronze"):
        workspace.schemas.create(name="bronze", catalog_name=catalog)
    if not _exists(workspace.volumes.read, f"{catalog}.bronze.raw"):
        workspace.volumes.create(catalog, "bronze", "raw", volume_type="MANAGED")

    print(f"Uploading to {root}/data.csv ...")
    with csv_path.open("rb") as handle:
        workspace.files.upload(f"{root}/data.csv", handle, overwrite=True)
    manifest = {"source": "manual-upload", "file": csv_path.name}
    workspace.files.upload(f"{root}/_manifest.json", BytesIO(json.dumps(manifest).encode()), overwrite=True)
    print("Done. Run the Data refresh workflow next.")
    return 0


def _exists(getter, name: str) -> bool:
    try:
        getter(name)
        return True
    except Exception:  # noqa: BLE001 - any "not found" style error means: create it
        return False


if __name__ == "__main__":
    sys.exit(main())
