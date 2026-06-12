from __future__ import annotations

from ..models import Article, PublishResult
from .base import BasePublisher


class CsdnPublisher(BasePublisher):
    platform = "csdn"

    def publish(self, article: Article, action: str, dry_run: bool = False) -> PublishResult:
        if not self.config.cookie and not dry_run:
            return PublishResult(self.platform, action, False, "缺少 CSDN_COOKIE")

        endpoint = "publish" if action == "publish" else "save"
        payload = self.build_payload(article, action)
        try:
            response = self.post(endpoint, payload, dry_run)
            message = "文章已发布" if action == "publish" else "草稿已保存"
            return PublishResult(self.platform, action, True, message, response)
        except Exception as exc:
            return PublishResult(self.platform, action, False, str(exc))

    def build_payload(self, article: Article, action: str) -> dict[str, object]:
        metadata = article.metadata
        categories = metadata.get("csdn_categories") or metadata.get("categories") or []
        if isinstance(categories, str):
            categories = [categories]

        return {
            "article_id": str(metadata.get("csdn_article_id") or ""),
            "title": article.title,
            "description": article.brief,
            "content": article.content,
            "markdowncontent": article.content,
            "tags": ",".join(article.tags),
            "categories": categories,
            "type": str(metadata.get("csdn_type") or "original"),
            "status": 1 if action == "publish" else 0,
            "readType": str(metadata.get("csdn_read_type") or "public"),
            "cover_images": [metadata["cover"]] if metadata.get("cover") else [],
            "reason": "",
            "resource_url": str(metadata.get("canonical_url") or ""),
        }
