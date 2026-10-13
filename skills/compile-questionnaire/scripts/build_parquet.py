import csv
import re
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

import pyarrow as pa
import pyarrow.parquet as pq


ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "data" / "model_cutoffs.csv"
OUTPUT = ROOT / "data" / "model_cutoffs.parquet"
DATE = r"\d{4}-\d{2}-\d{2}"
PATTERN = re.compile(rf"(?:={DATE}|>{DATE}|<{DATE}|>{DATE}&<{DATE})$")


def validate_expression(value: str) -> None:
    if not PATTERN.fullmatch(value):
        raise ValueError(f"Invalid cutoff expression: {value}")
    dates = [date.fromisoformat(item) for item in re.findall(DATE, value)]
    if len(dates) == 2 and dates[0] >= dates[1]:
        raise ValueError(f"Empty date interval: {value}")


with SOURCE.open(newline="", encoding="utf-8") as handle:
    records = list(csv.DictReader(handle))

seen = set()
for row in records:
    key = (row["provider"], row["model_id"])
    if key in seen:
        raise ValueError(f"Duplicate model: {key}")
    seen.add(key)
    validate_expression(row["cutoff"])
    if row["training_data_cutoff"]:
        validate_expression(row["training_data_cutoff"])
    if not urlparse(row["evidence_url"]).scheme == "https":
        raise ValueError(f"Invalid evidence URL: {key}")

schema = pa.schema(
    [
        ("provider", pa.string()),
        ("model_id", pa.string()),
        ("cutoff", pa.string()),
        ("cutoff_basis", pa.string()),
        ("training_data_cutoff", pa.string()),
        ("evidence_url", pa.string()),
        ("corroboration_url", pa.string()),
        ("evidence_note", pa.string()),
    ]
)
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
pq.write_table(pa.Table.from_pylist(records, schema=schema), OUTPUT, compression="zstd")
print(f"Wrote {len(records)} rows to {OUTPUT}")
