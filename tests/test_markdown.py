from pathlib import Path
import tempfile
import unittest

from autopub.markdown import load_article, split_front_matter


class MarkdownTests(unittest.TestCase):
    def test_parse_front_matter_arrays(self) -> None:
        metadata, content = split_front_matter(
            "---\n"
            "title: Hello\n"
            "tags: [Python, 自动化]\n"
            "platforms:\n"
            "  - csdn\n"
            "  - juejin\n"
            "---\n"
            "# Body\n"
        )
        self.assertEqual(metadata["title"], "Hello")
        self.assertEqual(metadata["tags"], ["Python", "自动化"])
        self.assertEqual(metadata["platforms"], ["csdn", "juejin"])
        self.assertEqual(content, "# Body\n")

    def test_load_article_uses_h1_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "post.md"
            path.write_text("# Fallback Title\n\nbody", encoding="utf-8")
            article = load_article(path)
        self.assertEqual(article.title, "Fallback Title")
        self.assertEqual(article.brief, "Fallback Title body")


if __name__ == "__main__":
    unittest.main()
