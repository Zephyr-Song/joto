from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import html
import json
import re
import time
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, quote, urlparse
from urllib.request import Request, urlopen


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)
DEFAULT_REPLY = (
    "我们在做 AI 网络运维、AI 护栏和企业私有化交付相关方案。"
    "如果你们也有类似需要，可以私聊我聊聊具体场景。"
)
BUSINESS_TERMS = (
    "AI网络运维",
    "AI 运维",
    "AIOps",
    "NetOps",
    "网络自动化",
    "网络运维",
    "故障诊断",
    "拓扑",
    "巡检",
    "告警",
    "SRE",
    "企业 IT",
    "Dify",
    "私有化",
    "知识库",
    "RAG",
    "Agent",
    "AI护栏",
    "安全护栏",
    "大模型安全",
    "权限",
    "审计",
)
INTENT_TERMS = (
    "有没有",
    "想问",
    "请问",
    "怎么",
    "如何",
    "求助",
    "需要",
    "想",
    "公司",
    "企业",
    "部署",
    "对接",
    "方案",
    "报价",
    "多少钱",
    "供应商",
    "客户",
    "项目",
    "落地",
)
SKIP_USER_PATTERNS = ("AI视频总结", "课代表")
SKIP_MESSAGE_PATTERNS = ("AI课代表总结", "课代表总结")


@dataclass(slots=True)
class Video:
    bvid: str
    title: str = ""
    url: str = ""


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Find Bilibili comments that may match JOTO business leads.",
    )
    parser.add_argument("--keyword", action="append", default=[], help="Bilibili search keyword")
    parser.add_argument("--video", action="append", default=[], help="Bilibili BV id or video URL")
    parser.add_argument("--video-file", help="newline separated BV ids or Bilibili URLs")
    parser.add_argument("--max-videos", type=int, default=5)
    parser.add_argument("--comments-per-video", type=int, default=30)
    parser.add_argument("--min-score", type=int, default=2)
    parser.add_argument("--reply", default=DEFAULT_REPLY)
    parser.add_argument("--out", default=".commentops/leads/bilibili-leads.json")
    args = parser.parse_args()

    videos = collect_videos(args)
    if not videos:
        print("No videos found. Pass --video/--video-file, or retry --keyword later.")
        return 1

    leads: list[dict[str, Any]] = []
    for video in videos[: args.max_videos]:
        try:
            resolved = resolve_video(video.bvid)
            comments = fetch_comments(resolved.bvid, limit=args.comments_per_video)
        except Exception as exc:
            print(f"skip {video.bvid}: {exc}")
            continue

        for comment in comments:
            score, matched = score_comment(comment["message"])
            if should_skip_comment(comment):
                continue
            if score < args.min_score:
                continue
            leads.append(
                {
                    "platform": "bilibili",
                    "video_bvid": resolved.bvid,
                    "video_title": resolved.title,
                    "video_url": resolved.url,
                    "comment_url": f"{resolved.url}#reply{comment['rpid']}",
                    "comment": comment,
                    "score": score,
                    "matched_terms": matched,
                    "reply_draft": args.reply,
                    "status": "needs_human_review",
                }
            )
        time.sleep(0.8)

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "business_terms": list(BUSINESS_TERMS),
        "intent_terms": list(INTENT_TERMS),
        "videos_scanned": [video.bvid for video in videos[: args.max_videos]],
        "leads": sorted(leads, key=lambda item: item["score"], reverse=True),
    }
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path = out_path.with_suffix(".md")
    md_path.write_text(render_review_sheet(output), encoding="utf-8")

    print(f"scanned_videos={len(output['videos_scanned'])}")
    print(f"leads={len(output['leads'])}")
    print(f"json={out_path}")
    print(f"review_sheet={md_path}")
    return 0


def collect_videos(args: argparse.Namespace) -> list[Video]:
    candidates: list[str] = []
    candidates.extend(args.video)
    if args.video_file:
        candidates.extend(
            line.strip()
            for line in Path(args.video_file).read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.strip().startswith("#")
        )

    videos = [Video(extract_bvid(item), url=normalize_video_url(extract_bvid(item))) for item in candidates]
    for keyword in args.keyword:
        videos.extend(search_videos(keyword, limit=args.max_videos))
        time.sleep(0.8)
    return dedupe_videos(videos)


def search_videos(keyword: str, limit: int = 5) -> list[Video]:
    url = (
        "https://api.bilibili.com/x/web-interface/search/type"
        f"?search_type=video&keyword={quote(keyword)}&page=1"
    )
    try:
        payload = request_json(url, referer="https://search.bilibili.com/")
    except Exception as exc:
        print(f"search failed for {keyword!r}: {exc}")
        return []

    if payload.get("code") != 0:
        print(f"search failed for {keyword!r}: {payload.get('message') or payload}")
        return []

    videos: list[Video] = []
    for item in (payload.get("data") or {}).get("result") or []:
        bvid = item.get("bvid")
        if not bvid:
            continue
        title = strip_html(str(item.get("title", "")))
        videos.append(Video(bvid=bvid, title=title, url=normalize_video_url(bvid)))
        if len(videos) >= limit:
            break
    return videos


def resolve_video(bvid: str) -> Video:
    payload = request_json(f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}")
    if payload.get("code") != 0:
        raise RuntimeError(payload.get("message") or payload)
    data = payload["data"]
    resolved = str(data.get("bvid") or bvid)
    return Video(
        bvid=resolved,
        title=str(data.get("title", "")),
        url=normalize_video_url(resolved),
    )


def fetch_comments(bvid: str, limit: int = 30) -> list[dict[str, Any]]:
    video = request_json(f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}")["data"]
    aid = int(video["aid"])
    comments: list[dict[str, Any]] = []
    page = 1
    page_size = min(max(limit, 1), 20)

    while len(comments) < limit:
        payload = request_json(
            "https://api.bilibili.com/x/v2/reply"
            f"?type=1&oid={aid}&sort=2&ps={page_size}&pn={page}"
        )
        if payload.get("code") != 0:
            raise RuntimeError(payload.get("message") or payload)
        replies = (payload.get("data") or {}).get("replies") or []
        if not replies:
            break
        for item in replies:
            comments.append(normalize_reply(item))
            if len(comments) >= limit:
                break
        page += 1
        time.sleep(0.5)
    return comments


def score_comment(message: str) -> tuple[int, list[str]]:
    text = message.lower()
    compact_text = text.replace(" ", "")
    matched: list[str] = []
    score = 0
    for term in BUSINESS_TERMS:
        if term.lower().replace(" ", "") in compact_text:
            matched.append(term)
            score += 2
    for term in INTENT_TERMS:
        if term in ("需要", "想") and not is_strong_intent(text, term):
            continue
        if term.lower() in text:
            matched.append(term)
            score += 1
    return score, matched


def is_strong_intent(text: str, term: str) -> bool:
    if term == "需要":
        return any(phrase in text for phrase in ("我需要", "公司需要", "企业需要", "客户需要", "是否需要", "需要部署", "需要对接"))
    if term == "想":
        return any(phrase in text for phrase in ("我想", "想问", "想做", "想了解", "想部署"))
    return True


def should_skip_comment(comment: dict[str, Any]) -> bool:
    user = str(comment.get("user") or "")
    message = str(comment.get("message") or "")
    return any(pattern in user for pattern in SKIP_USER_PATTERNS) or any(
        pattern in message for pattern in SKIP_MESSAGE_PATTERNS
    )


def normalize_reply(item: dict[str, Any]) -> dict[str, Any]:
    member = item.get("member") or {}
    content = item.get("content") or {}
    ctime = item.get("ctime")
    created_at = ""
    if isinstance(ctime, int):
        created_at = datetime.fromtimestamp(ctime, tz=timezone.utc).isoformat()
    return {
        "rpid": item.get("rpid"),
        "uid": member.get("mid"),
        "user": member.get("uname"),
        "message": content.get("message", ""),
        "like": item.get("like", 0),
        "reply_count": item.get("rcount", 0),
        "created_at": created_at,
    }


def request_json(url: str, referer: str = "https://www.bilibili.com/") -> dict[str, Any]:
    request = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Referer": referer,
            "Accept": "application/json,text/plain,*/*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        },
    )
    with urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def extract_bvid(target: str) -> str:
    target = target.strip()
    if re.fullmatch(r"BV[0-9A-Za-z]+", target):
        return target
    parsed = urlparse(target)
    candidates = [part for part in parsed.path.split("/") if part]
    query = parse_qs(parsed.query)
    candidates.extend(value for values in query.values() for value in values)
    for candidate in candidates:
        match = re.search(r"(BV[0-9A-Za-z]+)", candidate)
        if match:
            return match.group(1)
    raise ValueError(f"could not find BV id in {target!r}")


def normalize_video_url(bvid: str) -> str:
    return f"https://www.bilibili.com/video/{bvid}/"


def dedupe_videos(videos: list[Video]) -> list[Video]:
    seen: set[str] = set()
    unique: list[Video] = []
    for video in videos:
        if video.bvid in seen:
            continue
        seen.add(video.bvid)
        unique.append(video)
    return unique


def strip_html(value: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", value))


def render_review_sheet(output: dict[str, Any]) -> str:
    lines = [
        "# Bilibili Lead Review Sheet",
        "",
        f"Generated: {output['generated_at']}",
        f"Videos scanned: {len(output['videos_scanned'])}",
        f"Leads: {len(output['leads'])}",
        "",
    ]
    for index, lead in enumerate(output["leads"], start=1):
        comment = lead["comment"]
        lines.extend(
            [
                f"## {index}. Score {lead['score']} - {comment['user']}",
                "",
                f"- Video: [{lead['video_title']}]({lead['video_url']})",
                f"- Comment: {lead['comment_url']}",
                f"- Matched: {', '.join(lead['matched_terms'])}",
                f"- Status: {lead['status']}",
                "",
                "Comment:",
                "",
                f"> {comment['message']}",
                "",
                "Reply draft:",
                "",
                f"> {lead['reply_draft']}",
                "",
            ]
        )
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
