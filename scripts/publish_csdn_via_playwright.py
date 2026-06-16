from __future__ import annotations

from pathlib import Path
import json
import re
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import markdown as md
from autopub.config import load_config
from autopub.markdown import load_article
from playwright.sync_api import sync_playwright


def parse_cookie_string(raw: str) -> list[dict[str, object]]:
    cookies: list[dict[str, object]] = []
    for part in raw.split(";"):
        item = part.strip()
        if not item or "=" not in item:
            continue
        name, value = item.split("=", 1)
        cookies.append(
            {
                "name": name.strip(),
                "value": value.strip(),
                "domain": ".csdn.net",
                "path": "/",
                "secure": True,
            }
        )
    return cookies


def body_markdown_to_html(text: str) -> str:
    return md.markdown(
        text,
        extensions=["extra", "sane_lists", "nl2br"],
        output_format="html5",
    )


def clean_summary(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()[:180]


def main(article_path: str) -> int:
    cfg = load_config()
    article = load_article(Path(article_path))
    html = body_markdown_to_html(article.content)
    summary = clean_summary(article.brief)
    out = Path("C:/tmp/csdn-publish")
    out.mkdir(parents=True, exist_ok=True)

    state: dict[str, object] = {
        "article": article_path,
        "title": article.title,
        "summary": summary,
        "started_at": time.time(),
    }

    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel="msedge", headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 1400})
        context.add_cookies(parse_cookie_string(cfg.platforms["csdn"].cookie))
        page = context.new_page()

        responses: list[dict[str, object]] = []

        def on_response(resp):
            url = resp.url
            if "blog-console-api" in url or "saveArticle" in url:
                try:
                    body = resp.text()
                except Exception as exc:  # pragma: no cover
                    body = str(exc)
                responses.append({"url": url, "status": resp.status, "body": body[:2000]})

        page.on("response", on_response)
        page.goto("https://mp.csdn.net/mp_blog/creation/editor", wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(8000)

        dismiss_tip = page.get_by_text("不再出现")
        if dismiss_tip.count():
            try:
                if dismiss_tip.first.is_visible():
                    dismiss_tip.first.click(timeout=1000)
                    page.wait_for_timeout(1000)
            except Exception:
                pass

        continue_edit = page.get_by_text("继续编辑")
        if continue_edit.count():
            try:
                if continue_edit.first.is_visible():
                    continue_edit.first.click(timeout=3000)
                    page.wait_for_timeout(5000)
            except Exception:
                pass

        title = page.locator("textarea.el_mcm-textarea__inner").first
        title.click()
        title.fill(article.title)
        page.wait_for_timeout(500)

        page.evaluate(
            """(payload) => {
                const instances = Object.values(window.CKEDITOR?.instances || {});
                if (!instances.length) {
                    throw new Error('CKEditor instance not found');
                }
                instances[0].setData(payload.html);
            }""",
            {"html": html},
        )
        page.wait_for_timeout(1500)

        summary_box = page.locator("textarea[placeholder*='摘要']").first
        summary_box.click()
        summary_box.fill(summary)
        page.wait_for_timeout(500)

        page.screenshot(path=str(out / "before-publish.png"), full_page=True)

        publish_button = page.get_by_role("button", name="发布博客")
        publish_button.click()
        page.wait_for_timeout(6000)

        # Some flows show a second confirm button.
        confirm_candidates = [
            page.get_by_role("button", name="确认发布"),
            page.get_by_role("button", name="确认"),
            page.get_by_role("button", name="发布"),
        ]
        for locator in confirm_candidates:
            if locator.count():
                try:
                    locator.first.click(timeout=1000)
                    page.wait_for_timeout(4000)
                    break
                except Exception:
                    pass

        page.screenshot(path=str(out / "after-publish.png"), full_page=True)

        state["final_url"] = page.url
        state["responses"] = responses
        state["body_text_sample"] = re.sub(r"\s+", " ", page.locator("body").inner_text())[:4000]
        try:
            state["title_value"] = title.input_value(timeout=1000)
        except Exception:
            state["title_value"] = article.title

        verify = context.new_page()
        verify.goto("https://blog.csdn.net/song_zephyr", wait_until="domcontentloaded", timeout=45000)
        verify.wait_for_timeout(5000)
        state["verify_url"] = verify.url
        state["verify_contains_title"] = article.title in verify.locator("body").inner_text()
        verify.screenshot(path=str(out / "verify.png"), full_page=True)

        browser.close()

    (out / "result.json").write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    print(out / "result.json")
    return 0


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "posts/enterprise-knowledge-base-governance-for-dify-deployment.md"
    raise SystemExit(main(target))
