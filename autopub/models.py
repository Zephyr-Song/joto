from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Any


@dataclass(slots=True)
class Article:
    path: Path
    title: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def slug(self) -> str:
        return str(self.metadata.get("slug") or self.path.stem)

    @property
    def tags(self) -> list[str]:
        value = self.metadata.get("tags", [])
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        return []

    @property
    def platforms(self) -> list[str]:
        value = self.metadata.get("platforms", ["csdn", "juejin"])
        if isinstance(value, str):
            return [item.strip().lower() for item in value.split(",") if item.strip()]
        if isinstance(value, list):
            return [str(item).strip().lower() for item in value if str(item).strip()]
        return ["csdn", "juejin"]

    @property
    def brief(self) -> str:
        description = self.metadata.get("description")
        if description:
            return str(description).strip()
        text = re.sub(r"```.*?```", "", self.content, flags=re.S)
        text = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", text)
        text = re.sub(r"\[[^\]]+\]\([^)]+\)", "", text)
        text = re.sub(r"[#>*_`~-]+", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:180]


@dataclass(slots=True)
class PublishResult:
    platform: str
    action: str
    ok: bool
    message: str
    data: dict[str, Any] = field(default_factory=dict)
