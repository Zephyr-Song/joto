from __future__ import annotations

import argparse
from pathlib import Path
import shutil
from typing import Iterable

from .config import AppConfig, load_config
from .github_sync import sync_to_github
from .http import HttpClient
from .markdown import load_article
from .platforms import PUBLISHERS


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "init":
        return command_init()

    config = load_config(getattr(args, "config", "autopub.toml"))
    if args.command == "list":
        return command_list(config)
    if args.command == "check-config":
        return command_check_config(config)
    if args.command == "publish":
        return command_publish(args, config)
    if args.command == "sync":
        return command_sync(args, config)
    parser.print_help()
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="autopub", description="自动发布 CSDN 和掘金文章")
    parser.add_argument("--config", default="autopub.toml", help="配置文件路径")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("init", help="生成配置和示例文章")
    sub.add_parser("list", help="列出 posts 里的文章")
    sub.add_parser("check-config", help="检查本地发布配置")

    publish = sub.add_parser("publish", help="发布一篇 Markdown 文章")
    publish.add_argument("article", help="文章路径")
    publish.add_argument(
        "--platform",
        choices=["all", "csdn", "juejin"],
        default="all",
        help="发布平台",
    )
    publish.add_argument(
        "--action",
        choices=["draft", "publish"],
        default="draft",
        help="保存草稿或直接发布",
    )
    publish.add_argument("--dry-run", action="store_true", help="只生成请求预览，不真正发布")
    publish.add_argument("--sync", action="store_true", help="发布后同步到 GitHub")
    publish.add_argument("--message", default="Sync posts", help="Git 提交信息")

    sync = sub.add_parser("sync", help="提交并推送到 GitHub")
    sync.add_argument("--message", default="Sync posts", help="Git 提交信息")
    sync.add_argument("--no-push", action="store_true", help="只提交，不推送")
    return parser


def command_init() -> int:
    if not Path("autopub.toml").exists() and Path("config.example.toml").exists():
        shutil.copyfile("config.example.toml", "autopub.toml")
        print("已生成 autopub.toml")
    Path("posts").mkdir(exist_ok=True)
    print("初始化完成")
    return 0


def command_list(config: AppConfig) -> int:
    posts = sorted(Path(config.posts_dir).glob("*.md"))
    if not posts:
        print("posts 文件夹里还没有 Markdown 文章")
        return 0
    for post in posts:
        article = load_article(post)
        print(f"- {post}: {article.title} [{', '.join(article.platforms)}]")
    return 0


def command_check_config(config: AppConfig) -> int:
    for name, platform in config.platforms.items():
        status = "启用" if platform.enabled else "停用"
        cookie = "已配置 Cookie" if platform.cookie else "缺少 Cookie"
        print(f"{name}: {status}, {cookie}")
    remote = config.github.remote or "(使用现有 origin；如没有则只本地提交)"
    print(f"github: branch={config.github.branch}, remote={remote}")
    return 0


def command_publish(args: argparse.Namespace, config: AppConfig) -> int:
    article = load_article(Path(args.article))
    selected = select_platforms(args.platform, article.platforms)
    client = HttpClient()
    failed = False

    for name in selected:
        platform_config = config.platforms[name]
        if not platform_config.enabled:
            print(f"{name}: 已跳过，配置中未启用")
            continue
        publisher = PUBLISHERS[name](platform_config, client=client)
        result = publisher.publish(article, args.action, dry_run=args.dry_run)
        ok = "OK" if result.ok else "FAIL"
        print(f"{name}: {ok} - {result.message}")
        if result.data.get("dry_run"):
            print(f"  请求预览: {result.data['outbox']}")
        failed = failed or not result.ok

    if args.sync and not failed:
        sync_args = argparse.Namespace(message=args.message, no_push=False)
        return command_sync(sync_args, config)
    return 1 if failed else 0


def command_sync(args: argparse.Namespace, config: AppConfig) -> int:
    if args.no_push:
        config.github.push = False
    result = sync_to_github(config.github, args.message)
    print(result.message)
    return 0 if result.ok else 1


def select_platforms(platform: str, article_platforms: Iterable[str]) -> list[str]:
    if platform != "all":
        return [platform]
    selected = [item for item in article_platforms if item in PUBLISHERS]
    return selected or list(PUBLISHERS)
