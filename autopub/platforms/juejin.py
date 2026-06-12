from __future__ import annotations

from typing import Any

from ..models import Article, PublishResult
from .base import BasePublisher


class JuejinPublisher(BasePublisher):
    platform = "juejin"

    def publish(self, article: Article, action: str, dry_run: bool = False) -> PublishResult:
        if not self.config.cookie and not dry_run:
            return PublishResult(self.platform, action, False, "缺少 JUEJIN_COOKIE")

        draft_payload = self.build_draft_payload(article)
        draft_id = str(article.metadata.get("juejin_draft_id") or "").strip()
        endpoint = "update" if draft_id else "create"
        if draft_id:
            draft_payload["id"] = draft_id

        try:
            draft_response = self.post(endpoint, draft_payload, dry_run)
            if action == "draft":
                return PublishResult(self.platform, action, True, "草稿已保存", draft_response)

            publish_payload = self.build_publish_payload(draft_response, draft_id)
            publish_response = self.post("publish", publish_payload, dry_run)
            return PublishResult(self.platform, action, True, "文章已发布", publish_response)
        except Exception as exc:
            return PublishResult(self.platform, action, False, str(exc))

    def build_draft_payload(self, article: Article) -> dict[str, Any]:
        metadata = article.metadata
        return {
            "category_id": str(
                metadata.get("juejin_category_id")
                or self.config.extra.get("default_category_id")
                or ""
            ),
            "tag_ids": metadata.get("juejin_tag_ids")
            or self.config.extra.get("default_tag_ids")
            or [],
            "link_url": str(metadata.get("canonical_url") or ""),
            "cover_image": str(metadata.get("cover") or ""),
            "title": article.title,
            "brief_content": article.brief,
            "edit_type": 10,
            "html_content": "deprecated",
            "mark_content": article.content,
            "theme_ids": metadata.get("juejin_theme_ids") or [],
            "pics": metadata.get("pics") or [],
        }

    def build_publish_payload(
        self,
        draft_response: dict[str, Any],
        fallback_draft_id: str,
    ) -> dict[str, Any]:
        data = draft_response.get("data") if isinstance(draft_response, dict) else {}
        draft_id = fallback_draft_id
        if isinstance(data, dict):
            draft_id = str(data.get("id") or data.get("draft_id") or fallback_draft_id)
        return {"draft_id": draft_id, "sync_to_org": False}
