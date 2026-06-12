from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess

from .config import GithubConfig


@dataclass(slots=True)
class GitSyncResult:
    ok: bool
    message: str
    pushed: bool = False


def sync_to_github(config: GithubConfig, message: str = "Sync posts") -> GitSyncResult:
    root = Path.cwd()
    if not (root / ".git").exists():
        if not config.init_if_missing:
            return GitSyncResult(False, "当前文件夹还不是 Git 仓库")
        run(["git", "init"])

    ensure_branch(config.branch)
    if config.remote:
        ensure_origin(config.remote)

    run(["git", "add", "-A"])
    commit = subprocess.run(
        ["git", "commit", "-m", message],
        cwd=root,
        text=True,
        capture_output=True,
    )
    if commit.returncode != 0 and "nothing to commit" not in (
        commit.stdout + commit.stderr
    ).lower():
        return GitSyncResult(False, (commit.stderr or commit.stdout).strip())

    origin = current_origin()
    if config.push and origin:
        push = subprocess.run(
            ["git", "push", "-u", "origin", config.branch],
            cwd=root,
            text=True,
            capture_output=True,
        )
        if push.returncode != 0:
            return GitSyncResult(False, (push.stderr or push.stdout).strip())
        return GitSyncResult(True, "已提交并推送到 GitHub", pushed=True)

    if origin:
        return GitSyncResult(True, "已提交；配置关闭了推送", pushed=False)
    return GitSyncResult(True, "已提交；尚未设置 GitHub 远程仓库，未推送", pushed=False)


def ensure_branch(branch: str) -> None:
    current = run(["git", "branch", "--show-current"], check=False).stdout.strip()
    if current != branch:
        run(["git", "checkout", "-B", branch])


def ensure_origin(remote: str) -> None:
    existing = current_origin()
    if not existing:
        run(["git", "remote", "add", "origin", remote])
    elif existing != remote:
        run(["git", "remote", "set-url", "origin", remote])


def current_origin() -> str:
    result = run(["git", "remote", "get-url", "origin"], check=False)
    if result.returncode == 0:
        return result.stdout.strip()
    return ""


def run(args: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(args, cwd=Path.cwd(), text=True, capture_output=True)
    if check and result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout).strip())
    return result
