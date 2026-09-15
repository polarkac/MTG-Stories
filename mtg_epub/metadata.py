from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

from .models import StoryMetadata


def _string_value(content: str, key: str) -> str | None:
    match = re.search(rf"\b{re.escape(key)}\s*:\s*\"([^\"]*)\"", content)
    return match.group(1).strip() if match else None


def _title_from_conf(content: str) -> str | None:
    marker = "#show: doc => conf"
    start = content.find(marker)
    if start < 0:
        return None
    opening = content.find("(", start + len(marker))
    if opening < 0:
        return None
    match = re.match(r"\s*\(\s*\"([^\"]*)\"", content[opening:])
    return match.group(1).strip() if match else None


def _date_from_content(content: str) -> str | None:
    match = re.search(
        r"(?:story_date|date)\s*:\s*datetime\s*\(\s*day:\s*(\d+),\s*month:\s*(\d+),\s*year:\s*(\d+)",
        content,
    )
    if not match:
        return None
    try:
        return datetime(
            int(match.group(3)), int(match.group(2)), int(match.group(1))
        ).date().isoformat()
    except ValueError:
        return None


def _cover_candidates(typ_path: Path) -> list[Path]:
    directories = [typ_path.parent / typ_path.stem, typ_path.parent / "images", typ_path.parent]
    candidates: list[Path] = []
    for directory in directories:
        if directory.is_dir():
            candidates.extend(
                image for image in directory.iterdir()
                if image.is_file() and image.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
            )
        if candidates:
            break
    return sorted(candidates, key=lambda path: path.name.lower())


def extract_metadata(typ_path: Path, manifest_item: dict | None = None) -> StoryMetadata:
    content = typ_path.read_text(encoding="utf-8", errors="replace")
    manifest_item = manifest_item or {}
    clean_name = re.sub(r"^\d+[\s_-]*", "", typ_path.stem).replace("-", ": ")
    parent_name = re.sub(r"^\d+[\s_-]*", "", typ_path.parent.name).strip(" -")
    number_match = re.match(r"^(\d+)", typ_path.stem)

    title = manifest_item.get("title") or _title_from_conf(content) or clean_name
    set_name = manifest_item.get("set_name") or _string_value(content, "set_name") or parent_name
    author = manifest_item.get("author") or _string_value(content, "author") or "Wizards of the Coast"
    story_date = manifest_item.get("date") or _date_from_content(content)
    if not story_date:
        story_date = datetime.now(timezone.utc).date().isoformat()
    series_index = int(manifest_item.get("series_index") or (number_match.group(1) if number_match else 1))
    cover = manifest_item.get("cover_image")
    cover_path = Path(cover) if cover else (_cover_candidates(typ_path)[0] if _cover_candidates(typ_path) else None)

    return StoryMetadata(
        title=title,
        set_name=set_name or "Magic: The Gathering Stories",
        author=author,
        date=story_date,
        series=manifest_item.get("series") or set_name,
        series_index=series_index,
        source_file=typ_path,
        cover_image=cover_path,
        story_id=manifest_item.get("id"),
    )
