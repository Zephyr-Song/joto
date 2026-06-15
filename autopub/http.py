from __future__ import annotations

import json
from pathlib import Path
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class HttpClient:
    def __init__(self, outbox_dir: Path = Path(".autopub/outbox")) -> None:
        self.outbox_dir = outbox_dir

    def post_json(
        self,
        *,
        platform: str,
        url: str,
        payload: dict[str, Any],
        headers: dict[str, str],
        dry_run: bool = False,
    ) -> dict[str, Any]:
        if dry_run:
            return self.write_dry_run(platform, url, payload, headers)

        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = Request(url, data=body, method="POST")
        for key, value in headers.items():
            if value:
                request.add_header(key, value)
        if not has_header(headers, "Content-Type"):
            request.add_header("Content-Type", "application/json;charset=UTF-8")
        if not has_header(headers, "Accept"):
            request.add_header("Accept", "application/json, text/plain, */*")
        request.add_header(
            "User-Agent",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "KHTML, like Gecko Chrome/125 Safari/537.36",
        )

        try:
            with urlopen(request, timeout=30) as response:
                raw = response.read().decode("utf-8", errors="replace")
        except HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"HTTP {exc.code}: {raw[:500]}") from exc
        except URLError as exc:
            raise RuntimeError(f"网络请求失败: {exc}") from exc

        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"raw": raw}

    def write_dry_run(
        self,
        platform: str,
        url: str,
        payload: dict[str, Any],
        headers: dict[str, str],
    ) -> dict[str, Any]:
        self.outbox_dir.mkdir(parents=True, exist_ok=True)
        safe_headers = {
            key: (
                "<hidden>"
                if key.lower() in {"cookie", "authorization", "x-ca-signature"}
                else value
            )
            for key, value in headers.items()
        }
        record = {
            "platform": platform,
            "url": url,
            "headers": safe_headers,
            "payload": payload,
        }
        filename = f"{int(time.time())}-{platform}.json"
        path = self.outbox_dir / filename
        path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"dry_run": True, "outbox": str(path)}


def has_header(headers: dict[str, str], name: str) -> bool:
    wanted = name.lower()
    return any(key.lower() == wanted and bool(value) for key, value in headers.items())
