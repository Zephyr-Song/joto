from scripts.bilibili_lead_finder import classify_comment, extract_bvid, score_comment, should_skip_comment


def test_extract_bvid_from_url() -> None:
    assert extract_bvid("https://www.bilibili.com/video/BV1JATRzsEvN/?spm_id_from=333") == "BV1JATRzsEvN"


def test_score_comment_matches_business_need() -> None:
    score, matched = score_comment("公司想做 Dify 私有化知识库部署，有没有成熟方案？")
    classification = classify_comment("公司想做 Dify 私有化知识库部署，有没有成熟方案？")

    assert score >= 5
    assert "Dify" in matched
    assert "私有化" in matched
    assert "方案" in matched
    assert classification["demand_signals"]
    assert classification["lead_level"] == "medium"


def test_score_comment_avoids_weak_need_substrings() -> None:
    score, matched = score_comment("隐藏专业术语，直接说白话需求，让大模型推导子命令")
    classification = classify_comment("隐藏专业术语，直接说白话需求，让大模型推导子命令")

    assert "需要" not in matched
    assert score < 2
    assert classification["lead_level"] == "topic_only"


def test_topic_only_comment_has_no_demand_signals() -> None:
    classification = classify_comment("知识库可以推导出交换机子命令")

    assert classification["score"] == 2
    assert classification["matched_terms"] == ["知识库"]
    assert classification["demand_signals"] == []
    assert classification["lead_level"] == "topic_only"


def test_high_intent_comment_is_high_level() -> None:
    classification = classify_comment("公司想采购 Dify 私有化部署方案，能报价吗？")

    assert "采购" in classification["demand_signals"]
    assert "报价" in classification["demand_signals"]
    assert classification["lead_level"] == "high"


def test_skip_ai_summary_comment() -> None:
    assert should_skip_comment({"user": "AI视频总结", "message": "AI课代表总结：AIOps 很重要"})
