import pytest
from app.sources.registry import SourceRegistry
from app.rules.major_matcher import MajorMatcher
from app.extractors.talent_policy import TalentPolicyExtractor

@pytest.mark.asyncio
async def test_phase27_sources_registration():
    SourceRegistry.discover_and_register()
    
    huizhou = SourceRegistry.get("huizhou_cdc")
    assert huizhou is not None
    assert huizhou.province == "广东省"
    assert huizhou.city == "惠州市"
    
    taizhou = SourceRegistry.get("taizhou_cdc")
    assert taizhou is not None
    assert taizhou.province == "浙江省"
    assert taizhou.city == "台州市"
    
    yangzhou = SourceRegistry.get("yangzhou_cdc")
    assert yangzhou is not None
    assert yangzhou.province == "江苏省"
    assert yangzhou.city == "扬州市"

@pytest.mark.asyncio
async def test_phase27_sources_fetch():
    huizhou = SourceRegistry.get("huizhou_cdc")
    items = await huizhou.fetch_announcements()
    assert len(items) > 0
    detail = await huizhou.fetch_detail(items[0].url)
    assert detail is not None
    assert "惠州市" in detail.city
    
    taizhou = SourceRegistry.get("taizhou_cdc")
    items_tz = await taizhou.fetch_announcements()
    assert len(items_tz) > 0
    detail_tz = await taizhou.fetch_detail(items_tz[0].url)
    assert detail_tz is not None
    assert "台州市" in detail_tz.city

    yangzhou = SourceRegistry.get("yangzhou_cdc")
    items_yz = await yangzhou.fetch_announcements()
    assert len(items_yz) > 0
    detail_yz = await yangzhou.fetch_detail(items_yz[0].url)
    assert detail_yz is not None
    assert "扬州市" in detail_yz.city

def test_phase27_major_matcher_subdisciplines():
    toxicology_keywords = MajorMatcher.SUB_DISCIPLINE_KEYWORDS.get("毒物代谢与环境靶向毒理")
    assert toxicology_keywords is not None
    assert "毒物代谢动力学" in toxicology_keywords
    assert "计算毒理学" in toxicology_keywords

    digital_epi_keywords = MajorMatcher.SUB_DISCIPLINE_KEYWORDS.get("智慧化现场流调与接触者追踪")
    assert digital_epi_keywords is not None
    assert "数字化流调" in digital_epi_keywords
    assert "数字传染病学" in digital_epi_keywords

def test_phase27_talent_policy_extractor():
    text1 = "本项目符合惠州市鹅城英才引进标准，提供安家费50万元，享受免笔试直接考核入编。"
    res1 = TalentPolicyExtractor.extract(text1)
    assert res1["is_talent_intro"] is True
    assert res1["is_no_written_exam"] is True
    assert "50万" in str(res1["settlement_allowance"])

    text2 = "纳入台州市500精英计划，博士免笔试，购房补贴80万元。"
    res2 = TalentPolicyExtractor.extract(text2)
    assert res2["is_talent_intro"] is True
    assert res2["is_no_written_exam"] is True
    assert "80万" in str(res2["settlement_allowance"])

    text3 = "入选扬州市绿扬金凤计划高层次人才，直接面试考核入职，提供安家补贴30万。"
    res3 = TalentPolicyExtractor.extract(text3)
    assert res3["is_talent_intro"] is True
    assert res3["is_no_written_exam"] is True
    assert "30万" in str(res3["settlement_allowance"])
