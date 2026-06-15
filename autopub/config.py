from __future__ import annotations

from dataclasses import dataclass, field
import os
from pathlib import Path
import tomllib
from typing import Any


@dataclass(slots=True)
class PlatformConfig:
    name: str
    enabled: bool = True
    cookie: str = ""
    csrf_token: str = ""
    referer: str = ""
    endpoints: dict[str, str] = field(default_factory=dict)
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class GithubConfig:
    branch: str = "main"
    remote: str = ""
    push: bool = True
    init_if_missing: bool = True


@dataclass(slots=True)
class AppConfig:
    platforms: dict[str, PlatformConfig] = field(default_factory=dict)
    github: GithubConfig = field(default_factory=GithubConfig)
    posts_dir: str = "posts"


DEFAULT_ENDPOINTS = {
    "csdn": {
        "save": "https://bizapi.csdn.net/blog-console-api/v1/postedit/saveArticle",
        "publish": "https://bizapi.csdn.net/blog-console-api/v1/postedit/saveArticle",
    },
    "juejin": {
        "create": "https://api.juejin.cn/content_api/v1/article_draft/create",
        "update": "https://api.juejin.cn/content_api/v1/article_draft/update",
        "publish": "https://api.juejin.cn/content_api/v1/article/publish",
    },
}


def load_config(path: str | Path = "autopub.toml") -> AppConfig:
    config_path = Path(os.environ.get("AUTOPUB_CONFIG", path))
    raw: dict[str, Any] = {}
    if config_path.exists():
        raw = tomllib.loads(config_path.read_text(encoding="utf-8"))

    github_raw = raw.get("github", {})
    github = GithubConfig(
        branch=str(os.getenv("GITHUB_BRANCH") or github_raw.get("branch") or "main"),
        remote=str(os.getenv("GITHUB_REMOTE") or github_raw.get("remote") or ""),
        push=bool(github_raw.get("push", True)),
        init_if_missing=bool(github_raw.get("init_if_missing", True)),
    )

    platforms: dict[str, PlatformConfig] = {}
    raw_platforms = raw.get("platforms", {})
    for name in ("csdn", "juejin"):
        section = dict(raw_platforms.get(name, {}))
        endpoints = dict(DEFAULT_ENDPOINTS[name])
        for key in list(section):
            if key.endswith("_endpoint"):
                endpoints[key.removesuffix("_endpoint")] = str(section.pop(key))

        cookie_env = f"{name.upper()}_COOKIE"
        csrf_env = f"{name.upper()}_CSRF_TOKEN"
        platforms[name] = PlatformConfig(
            name=name,
            enabled=bool(section.pop("enabled", True)),
            cookie=str(os.getenv(cookie_env) or section.pop("cookie", "")),
            csrf_token=str(os.getenv(csrf_env) or section.pop("csrf_token", "")),
            referer=str(section.pop("referer", "")),
            endpoints=endpoints,
            extra=section,
        )

    posts_dir = str(raw.get("tool", {}).get("autopub", {}).get("posts_dir", "posts"))
    return AppConfig(platforms=platforms, github=github, posts_dir=posts_dir)
