import pytest
from app.sources.registry import SourceRegistry
from app.rules.major_matcher import MajorMatcher
from app.extractors.talent_policy import TalentPolicyExtractor

@pytest.mark.asyncio
async def test_phase29_sources_registration():
    SourceRegistry.discover_and_register()
    
    yantai = SourceRegistry.get("yantai_cdc")
    assert yantai is not None
    assert yantai.province == "山东省"
    assert yantai.city == "烟台市"
    
    luoyang = SourceRegistry.get("luoyang_cdc")
    assert luoyang is not None
    assert luoyang.province == "河南省"
    assert luoyang.city == "洛阳市"

@pytest.mark.asyncio
async def test_phase29_sources_fetch():
    yantai = SourceRegistry.get("yantai_cdc")
    items_yt = await yantai.fetch_announcements()
    assert len(items_yt) > 0
    detail_yt = await yantai.fetch_detail(items_yt[0].url)
    assert detail_yt is not None
    assert "烟台市" in detail_yt.city
    
    luoyang = SourceRegistry.get("luoyang_cdc")
    items_ly = await luoyang.fetch_announcements()
    assert len(items_ly) > 0
    detail_ly = await luoyang.fetch_detail(items_ly[0].url)
    assert detail_ly is not None
    assert "洛阳市" in detail_ly.city

def test_phase29_major_matcher_subdisciplines():
    water_keywords = MajorMatcher.SUB_DISCIPLINE_KEYWORDS.get("智慧化水质与环境理化快检")
    assert water_keywords is not None
    assert "水质理化快检" in water_keywords
    assert "生活饮用水检测" in water_keywords

    tb_keywords = MajorMatcher.SUB_DISCIPLINE_KEYWORDS.get("耐药结核与呼吸道传染病分子诊断")
    assert tb_keywords is not None
    assert "耐药结核分子诊断" in tb_keywords
    assert "结核分枝杆菌耐药检测" in tb_keywords

def test_phase29_talent_policy_extractor():
    text1 = "入选烟台市仙境英才引进工程，免笔试直接考核，发放购房补贴45万元。"
    res1 = TalentPolicyExtractor.extract_talent_policies(text1)
    assert res1["is_talent_intro"] is True
    assert res1["is_no_exam"] is True
    assert "45万" in str(res1["settlement_allowance"])

    text2 = "符合洛阳市河洛英才计划条件，实行考核招聘直接面试入编，提供安家费50万元。"
    res2 = TalentPolicyExtractor.extract_talent_policies(text2)
    assert res2["is_talent_intro"] is True
    assert res2["is_no_exam"] is True
    assert "50万" in str(res2["settlement_allowance"])
