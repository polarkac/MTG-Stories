from __future__ import annotations

import json
from pathlib import Path


def load_manifest(path: Path | None) -> dict[str, dict]:
    if not path or not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    items = data.get("scraped_items", data) if isinstance(data, dict) else {}
    return {str(item.get("output_file", "")): item for item in items.values() if isinstance(item, dict)}


def manifest_item_for(path: Path, items: dict[str, dict]) -> dict | None:
    normalized = path.as_posix().lower()
    for key, item in items.items():
        if Path(key.replace("\\", "/")).as_posix().lower() == normalized:
            return item
        output = item.get("output_file")
        if output and Path(output.replace("\\", "/")).name.lower() == path.name.lower():
            return item
    return None


def write_manifest(path: Path, records: list[dict]) -> None:
    payload = {
        "version": 1,
        "updated_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        "items": records,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
