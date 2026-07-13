from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
from typing import Any


RUNTIME_DEBUG_ROOT = Path(__file__).resolve().parents[2] / "runtime" / "search_debug"


class SearchDebugWriter:
    """Persist intermediate recruiter search artifacts for debugging."""

    def __init__(self, enabled: bool, root: Path = RUNTIME_DEBUG_ROOT) -> None:
        self.enabled = enabled
        self.root = root
        self.search_dir: Path | None = None

        if self.enabled:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            self.search_dir = self.root / f"search_{timestamp}"
            self.search_dir.mkdir(parents=True, exist_ok=True)

    def write_text(self, filename: str, content: str | None) -> None:
        if not self.enabled or self.search_dir is None:
            return
        (self.search_dir / filename).write_text(str(content or ""), encoding="utf-8")

    def write_json(self, filename: str, content: Any) -> None:
        if not self.enabled or self.search_dir is None:
            return
        (self.search_dir / filename).write_text(
            json.dumps(content, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )

    def finalize_report(self, sections: dict[str, Any]) -> None:
        if not self.enabled or self.search_dir is None:
            return

        lines = [
            "=" * 54,
            "Recruiter Search Debug",
            "=" * 54,
            "",
        ]
        for title, value in sections.items():
            lines.extend([title, "-" * 25])
            if isinstance(value, (dict, list)):
                lines.append(json.dumps(value, indent=2, ensure_ascii=False, default=str))
            else:
                lines.append(str(value or ""))
            lines.append("")
        lines.append("=" * 54)
        self.write_text("debug_report.txt", "\n".join(lines))

    @property
    def path(self) -> str | None:
        return str(self.search_dir) if self.search_dir else None
