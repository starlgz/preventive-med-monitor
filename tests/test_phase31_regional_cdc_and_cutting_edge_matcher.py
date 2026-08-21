import pytest
from app.sources.registry import SourceRegistry
from app.rules.major_matcher import MajorMatcher
from app.extractors.talent_policy import TalentPolicyExtractor

@pytest.mark.asyncio
async def test_phase31_sources_registration():
    SourceRegistry.discover_and_register()
    
    linyi = SourceRegistry.get("linyi_cdc")
    assert linyi is not None
    assert linyi.province == "山东省"
    assert linyi.city == "临沂市"
    
    tangshan = SourceRegistry.get("tangshan_cdc")
    assert tangshan is not None
    assert tangshan.province == "河北省"
    assert tangshan.city == "唐山市"

@pytest.mark.asyncio
async def test_phase31_sources_fetch():
    linyi = SourceRegistry.get("linyi_cdc")
    items_ly = await linyi.fetch_announcements()
    assert len(items_ly) > 0
    detail_ly = await linyi.fetch_detail(items_ly[0].url)
    assert detail_ly is not None
    assert "临沂市" in detail_ly.city
    
    tangshan = SourceRegistry.get("tangshan_cdc")
    items_ts = await tangshan.fetch_announcements()
    assert len(items_ts) > 0
    detail_ts = await tangshan.fetch_detail(items_ts[0].url)
    assert detail_ts is not None
    assert "唐山市" in detail_ts.city

def test_phase31_major_matcher_subdisciplines():
    exp_keywords = MajorMatcher.SUB_DISCIPLINE_KEYWORDS.get("环境暴露组学与健康风险评估")
    assert exp_keywords is not None
    assert "环境暴露组学" in exp_keywords
    assert "健康风险评估" in exp_keywords

    disinfect_keywords = MajorMatcher.SUB_DISCIPLINE_KEYWORDS.get("消毒学与院感传播阻断")
    assert disinfect_keywords is not None
    assert "消毒学" in disinfect_keywords
    assert "院感传播阻断" in disinfect_keywords

    # Level 4 / 5 matching check
    m1 = MajorMatcher.match("环境暴露组学与健康风险评估研究岗")
    assert m1["match_level"] in [4, 5]
    assert "环境暴露组学与健康风险评估" in m1["sub_disciplines"]

    m2 = MajorMatcher.match("消毒学与院感传播阻断技术岗")
    assert m2["match_level"] in [4, 5]
    assert "消毒学与院感传播阻断" in m2["sub_disciplines"]

def test_phase31_talent_policy_extractor():
    text1 = "入选临沂市沂蒙英才计划，免笔试直接考核入编，发放安家费与购房补贴40万元。"
    res1 = TalentPolicyExtractor.extract_talent_policies(text1)
    assert res1["is_talent_intro"] is True
    assert res1["is_no_exam"] is True
    assert "40万" in str(res1["settlement_allowance"])

    text2 = "符合唐山市凤凰英才引进条件，实行免笔试考核招聘，提供安家补贴50万元。"
    res2 = TalentPolicyExtractor.extract_talent_policies(text2)
    assert res2["is_talent_intro"] is True
    assert res2["is_no_exam"] is True
    assert "50万" in str(res2["settlement_allowance"])
