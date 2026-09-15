from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class StoryMetadata:
    title: str
    set_name: str
    author: str
    date: str
    series: str
    series_index: int
    source_file: Path
    cover_image: Path | None = None
    story_id: str | None = None

    def as_json(self) -> dict[str, Any]:
        data = asdict(self)
        data["source_file"] = str(self.source_file)
        data["cover_image"] = str(self.cover_image) if self.cover_image else None
        return data


@dataclass
class ConversionResult:
    source: Path
    output: Path
    success: bool
    status: str
    duration_seconds: float = 0.0
    error: str | None = None
    skipped: bool = False

    def as_json(self) -> dict[str, Any]:
        return {
            "source": str(self.source),
            "output": str(self.output),
            "success": self.success,
            "status": self.status,
            "duration_seconds": round(self.duration_seconds, 3),
            "error": self.error,
            "skipped": self.skipped,
        }
