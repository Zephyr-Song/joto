from __future__ import annotations

import base64
import hashlib
import hmac
from typing import Any
from urllib.parse import parse_qsl, urlsplit
import uuid

from ..models import Article, PublishResult
from .base import BasePublisher


class CsdnPublisher(BasePublisher):
    platform = "csdn"
    gateway_key = "203803574"
    gateway_secret = "9znpamsyl2c7cdrr9sas0le9vbc3r6ba"

    def publish(self, article: Article, action: str, dry_run: bool = False) -> PublishResult:
        if not self.config.cookie and not dry_run:
            return PublishResult(self.platform, action, False, "缺少 CSDN_COOKIE")

        endpoint = "publish" if action == "publish" else "save"
        payload = self.build_payload(article, action)
        try:
            response = self.post(endpoint, payload, dry_run)
            if not dry_run and response.get("code") not in (None, 200):
                message = str(response.get("msg") or response.get("message") or response)
                return PublishResult(self.platform, action, False, message, response)
            message = "文章已发布" if action == "publish" else "草稿已保存"
            return PublishResult(self.platform, action, True, message, response)
        except Exception as exc:
            return PublishResult(self.platform, action, False, str(exc))

    def build_payload(self, article: Article, action: str) -> dict[str, object]:
        metadata = article.metadata
        categories = metadata.get("csdn_categories") or metadata.get("categories") or []
        if isinstance(categories, str):
            categories = [categories]
        categories_text = ",".join(str(category) for category in categories if category)

        return {
            "article_id": str(metadata.get("csdn_article_id") or ""),
            "title": article.title,
            "description": article.brief,
            "content": article.content,
            "markdowncontent": article.content,
            "tags": ",".join(article.tags),
            "categories": categories_text,
            "type": str(metadata.get("csdn_type") or "original"),
            "status": 1 if action == "publish" else 0,
            "readType": str(metadata.get("csdn_read_type") or "public"),
            "cover_images": [metadata["cover"]] if metadata.get("cover") else [],
            "reason": "",
            "resource_url": str(metadata.get("canonical_url") or ""),
        }

    def post(
        self,
        endpoint_name: str,
        payload: dict[str, Any],
        dry_run: bool,
    ) -> dict[str, Any]:
        url = self.config.endpoints[endpoint_name]
        headers = self.headers()
        self.apply_gateway_signature(headers, "POST", url)
        return self.client.post_json(
            platform=self.platform,
            url=url,
            payload=payload,
            headers=headers,
            dry_run=dry_run,
        )

    def apply_gateway_signature(self, headers: dict[str, str], method: str, url: str) -> None:
        headers.pop("X-Ca-Signature", None)
        headers.pop("X-Ca-Signature-Headers", None)
        headers["Accept"] = headers.get("Accept") or "application/json, text/plain, */*"
        headers["Content-Type"] = headers.get("Content-Type") or "application/json;"
        headers["X-Ca-Key"] = self.gateway_key
        headers["X-Ca-Nonce"] = str(uuid.uuid4())
        headers["X-Ca-Stage"] = headers.get("X-Ca-Stage", "")

        signature = build_csdn_signature(
            method=method,
            url=url,
            accept=headers["Accept"],
            content_type=headers["Content-Type"],
            date=headers.get("date", ""),
            headers=headers,
            app_secret=self.gateway_secret,
        )
        headers["X-Ca-Signature"] = signature
        headers["X-Ca-Signature-Headers"] = "x-ca-key,x-ca-nonce"


def build_csdn_signature(
    *,
    method: str,
    url: str,
    accept: str,
    content_type: str,
    date: str,
    headers: dict[str, str],
    app_secret: str,
) -> str:
    parts = [
        method.upper(),
        accept,
        "",
        content_type,
        date,
    ]

    signed_headers = {
        key.lower(): value
        for key, value in headers.items()
        if key.lower() in {"x-ca-key", "x-ca-nonce"}
    }
    for key in sorted(signed_headers):
        parts.append(f"{key}:{signed_headers[key]}")

    parts.append(canonical_csdn_url(url))
    string_to_sign = "\n".join(parts)
    digest = hmac.new(
        app_secret.encode("utf-8"),
        string_to_sign.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return base64.b64encode(digest).decode("ascii")


def canonical_csdn_url(url: str) -> str:
    parsed = urlsplit(url)
    path = parsed.path or "/"
    params = parse_qsl(parsed.query, keep_blank_values=True)
    if not params:
        return path

    query = "&".join(
        f"{key}={value}" if value or value == "0" else key
        for key, value in sorted(params)
        if key != "undefined"
    )
    return f"{path}?{query}" if query else path
