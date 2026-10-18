import logging
import os
from pathlib import Path

import azure.functions as func
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient
from ingest_core import run_ingest

app = func.FunctionApp()


class BlobLake:
    """LakeStore backed by one blob container, using the app's managed identity."""

    def __init__(self, account_url: str, container: str) -> None:
        service = BlobServiceClient(account_url, credential=DefaultAzureCredential())
        self._container = service.get_container_client(container)

    def exists(self, path: str) -> bool:
        return self._container.get_blob_client(path).exists()

    def upload_file(self, path: str, local_path: Path) -> None:
        with local_path.open("rb") as stream:
            self._container.upload_blob(path, stream, overwrite=True, max_concurrency=4)

    def upload_text(self, path: str, text: str) -> None:
        self._container.upload_blob(path, text.encode("utf-8"), overwrite=True)


# The schedule comes from the INGEST_SCHEDULE app setting (a six-field NCRONTAB).
@app.timer_trigger(schedule="%INGEST_SCHEDULE%", arg_name="timer", run_on_startup=False)
def ingest_nsw_sales(timer: func.TimerRequest) -> None:
    lake = BlobLake(os.environ["LAKE_ACCOUNT_URL"], os.environ.get("RAW_CONTAINER", "raw"))
    result = run_ingest(os.environ["SOURCE_URL"], lake)
    logging.getLogger("ingest").info("ingest result: %s", result)
