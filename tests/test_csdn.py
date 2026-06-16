import unittest
from pathlib import Path

from autopub.config import PlatformConfig
from autopub.models import Article
from autopub.platforms.csdn import CsdnPublisher


class StubClient:
    def __init__(self, response):
        self.response = response

    def post_json(self, **kwargs):
        return self.response


def make_config() -> PlatformConfig:
    return PlatformConfig(
        name="csdn",
        cookie="cookie",
        referer="https://mp.csdn.net/mp_blog/creation/editor",
        endpoints={"save": "https://example.com/save", "publish": "https://example.com/publish"},
    )


def make_article() -> Article:
    return Article(
        path=Path("posts/test.md"),
        title="Test",
        content="# Test\n\nbody",
        metadata={"description": "desc", "tags": ["AI"], "csdn_categories": ["人工智能"]},
    )


class CsdnPublisherTests(unittest.TestCase):
    def test_publish_requires_article_reference_for_success(self) -> None:
        publisher = CsdnPublisher(
            make_config(),
            client=StubClient({"code": 200, "data": "成功", "msg": "success"}),
        )

        result = publisher.publish(make_article(), "publish")

        self.assertFalse(result.ok)
        self.assertIn("未返回文章 ID 或 URL", result.message)

    def test_publish_accepts_response_with_article_id(self) -> None:
        publisher = CsdnPublisher(
            make_config(),
            client=StubClient({"code": 200, "data": {"article_id": "12345"}, "msg": "success"}),
        )

        result = publisher.publish(make_article(), "publish")

        self.assertTrue(result.ok)
        self.assertEqual(result.message, "文章已发布")


if __name__ == "__main__":
    unittest.main()
