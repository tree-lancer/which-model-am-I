import csv
import json
from pathlib import Path

root = Path(__file__).resolve().parents[3]
with (root / "data/model_cutoffs.csv").open(newline="", encoding="utf-8") as source:
    rows = list(csv.DictReader(source))
catalog = [
    {
        "provider": row["provider"],
        "modelId": row["model_id"],
        "cutoff": row["cutoff"],
        "basis": row["cutoff_basis"],
        "evidenceUrl": row["evidence_url"],
    }
    for row in rows
]
(root / "data/model_catalog.json").write_text(
    json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
print(f"Wrote {len(catalog)} catalog entries")
