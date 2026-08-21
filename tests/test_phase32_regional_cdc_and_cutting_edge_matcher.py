import pytest
from app.sources.registry import SourceRegistry
from app.rules.major_matcher import MajorMatcher
from app.extractors.talent_policy import TalentPolicyExtractor

@pytest.mark.asyncio
async def test_phase32_sources_registration():
    SourceRegistry.discover_and_register()
    
    jining = SourceRegistry.get("jining_cdc")
    assert jining is not None
    assert jining.province == "山东省"
    assert jining.city == "济宁市"
    
    handan = SourceRegistry.get("handan_cdc")
    assert handan is not None
    assert handan.province == "河北省"
    assert handan.city == "邯郸市"

@pytest.mark.asyncio
async def test_phase32_sources_fetch():
    jining = SourceRegistry.get("jining_cdc")
    items_jn = await jining.fetch_announcements()
    assert len(items_jn) > 0
    detail_jn = await jining.fetch_detail(items_jn[0].url)
    assert detail_jn is not None
    assert "济宁市" in detail_jn.city
    
    handan = SourceRegistry.get("handan_cdc")
    items_hd = await handan.fetch_announcements()
    assert len(items_hd) > 0
    detail_hd = await handan.fetch_detail(items_hd[0].url)
    assert detail_hd is not None
    assert "邯郸市" in detail_hd.city

def test_phase32_major_matcher_subdisciplines():
    spatial_keywords = MajorMatcher.SUB_DISCIPLINE_KEYWORDS.get("空间流行病学与疾病制图")
    assert spatial_keywords is not None
    assert "空间流行病学" in spatial_keywords
    assert "疾病制图" in spatial_keywords

    ms_keywords = MajorMatcher.SUB_DISCIPLINE_KEYWORDS.get("病原质谱快速鉴定与色谱分析")
    assert ms_keywords is not None
    assert "病原质谱快速鉴定" in ms_keywords
    assert "MALDI-TOF质谱" in ms_keywords

    # Level 4 / 5 matching check
    m1 = MajorMatcher.match("空间流行病学与疾病制图业务骨干")
    assert m1["match_level"] in [4, 5]
    assert "空间流行病学与疾病制图" in m1["sub_disciplines"]

    m2 = MajorMatcher.match("病原质谱快速鉴定与色谱分析检验岗")
    assert m2["match_level"] in [4, 5]
    assert "病原质谱快速鉴定与色谱分析" in m2["sub_disciplines"]

def test_phase32_talent_policy_extractor():
    text1 = "入选济宁市圣地英才/太白英才计划，免笔试直接考核入编，发放安家补贴35万元。"
    res1 = TalentPolicyExtractor.extract_talent_policies(text1)
    assert res1["is_talent_intro"] is True
    assert res1["is_no_exam"] is True
    assert "35万" in str(res1["settlement_allowance"])

    text2 = "符合邯郸市赵都英才引进条件，实行免笔试考核招聘，提供安家补贴40万元。"
    res2 = TalentPolicyExtractor.extract_talent_policies(text2)
    assert res2["is_talent_intro"] is True
    assert res2["is_no_exam"] is True
    assert "40万" in str(res2["settlement_allowance"])
