"""Address query normalisation for typeahead search."""

import re

MAX_QUERY_LENGTH = 100

# Long street-type words -> the abbreviations used in the source data.
STREET_ABBREVIATIONS = {
    "street": "st", "road": "rd", "avenue": "ave", "drive": "dr", "place": "pl",
    "crescent": "cres", "close": "cl", "parade": "pde", "circuit": "cct", "court": "ct",
    "boulevard": "bvd", "boulevarde": "bvd", "terrace": "tce", "grove": "gr",
    "highway": "hwy", "glade": "gld", "parkway": "pkwy",
}  # fmt: skip

UNIT_PREFIX = re.compile(r"^(?:unit|apt|apartment|u)\s*(\d+[a-z]?)[\s,/]+(\d.*)$")
STATE_SUFFIX = re.compile(r"\s+nsw$")


def normalise_query(raw: str) -> str:
    text = raw.lower()[:MAX_QUERY_LENGTH]
    text = re.sub(r"[,.]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    text = UNIT_PREFIX.sub(r"\1/\2", text)
    text = STATE_SUFFIX.sub("", text)
    return " ".join(STREET_ABBREVIATIONS.get(token, token) for token in text.split(" "))


def escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", r"\%").replace("_", r"\_")
