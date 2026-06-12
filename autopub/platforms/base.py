from __future__ import annotations

from typing import Any

from ..config import PlatformConfig
from ..http import HttpClient
from ..models import Article, PublishResult


class BasePublisher:
    platform = "base"

    def __init__(self, config: PlatformConfig, client: HttpClient | None = None) -> None:
        self.config = config
        self.client = client or HttpClient()

    def publish(self, article: Article, action: str, dry_run: bool = False) -> PublishResult:
        raise NotImplementedError

    def headers(self) -> dict[str, str]:
        return {
            "Cookie": self.config.cookie,
            "Referer": self.config.referer,
            "Origin": origin_from_referer(self.config.referer),
            "X-CSRF-Token": self.config.csrf_token,
            "X-Csrf-Token": self.config.csrf_token,
        }

    def post(
        self,
        endpoint_name: str,
        payload: dict[str, Any],
        dry_run: bool,
    ) -> dict[str, Any]:
        url = self.config.endpoints[endpoint_name]
        return self.client.post_json(
            platform=self.platform,
            url=url,
            payload=payload,
            headers=self.headers(),
            dry_run=dry_run,
        )


def origin_from_referer(referer: str) -> str:
    if not referer.startswith("http"):
        return ""
    parts = referer.split("/", 3)
    return "/".join(parts[:3])
