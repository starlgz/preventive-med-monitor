import pytest
from app.sources.registry import SourceRegistry
from app.rules.major_matcher import MajorMatcher
from app.extractors.talent_policy import TalentPolicyExtractor

@pytest.mark.asyncio
async def test_phase30_sources_registration():
    SourceRegistry.discover_and_register()
    
    weifang = SourceRegistry.get("weifang_cdc")
    assert weifang is not None
    assert weifang.province == "山东省"
    assert weifang.city == "潍坊市"
    
    baoding = SourceRegistry.get("baoding_cdc")
    assert baoding is not None
    assert baoding.province == "河北省"
    assert baoding.city == "保定市"

@pytest.mark.asyncio
async def test_phase30_sources_fetch():
    weifang = SourceRegistry.get("weifang_cdc")
    items_wf = await weifang.fetch_announcements()
    assert len(items_wf) > 0
    detail_wf = await weifang.fetch_detail(items_wf[0].url)
    assert detail_wf is not None
    assert "潍坊市" in detail_wf.city
    
    baoding = SourceRegistry.get("baoding_cdc")
    items_bd = await baoding.fetch_announcements()
    assert len(items_bd) > 0
    detail_bd = await baoding.fetch_detail(items_bd[0].url)
    assert detail_bd is not None
    assert "保定市" in detail_bd.city

def test_phase30_major_matcher_subdisciplines():
    poison_keywords = MajorMatcher.SUB_DISCIPLINE_KEYWORDS.get("突发中毒应急与毒物快速筛查")
    assert poison_keywords is not None
    assert "突发中毒应急" in poison_keywords
    assert "毒物快速筛查" in poison_keywords

    rad_keywords = MajorMatcher.SUB_DISCIPLINE_KEYWORDS.get("辐射危害监测与放射卫生防护")
    assert rad_keywords is not None
    assert "辐射危害监测" in rad_keywords
    assert "放射卫生防护" in rad_keywords

    # Level 4 / 5 matching check
    m1 = MajorMatcher.match("突发中毒应急检测岗")
    assert m1["match_level"] in [4, 5]

def test_phase30_talent_policy_extractor():
    text1 = "入选潍坊市鸢都英才工程，免笔试直接考核，发放购房补贴50万元。"
    res1 = TalentPolicyExtractor.extract_talent_policies(text1)
    assert res1["is_talent_intro"] is True
    assert res1["is_no_exam"] is True
    assert "50万" in str(res1["settlement_allowance"])

    text2 = "符合保定市保定英才计划条件，实行考核招聘直接面试入编，提供安家费40万元。"
    res2 = TalentPolicyExtractor.extract_talent_policies(text2)
    assert res2["is_talent_intro"] is True
    assert res2["is_no_exam"] is True
    assert "40万" in str(res2["settlement_allowance"])
