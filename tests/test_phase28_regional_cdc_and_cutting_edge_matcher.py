import pytest
from app.sources.registry import SourceRegistry
from app.rules.major_matcher import MajorMatcher
from app.extractors.talent_policy import TalentPolicyExtractor

@pytest.mark.asyncio
async def test_phase28_sources_registration():
    SourceRegistry.discover_and_register()
    
    xuzhou = SourceRegistry.get("xuzhou_cdc")
    assert xuzhou is not None
    assert xuzhou.province == "江苏省"
    assert xuzhou.city == "徐州市"
    
    jinhua = SourceRegistry.get("jinhua_cdc")
    assert jinhua is not None
    assert jinhua.province == "浙江省"
    assert jinhua.city == "金华市"
    
    jiangmen = SourceRegistry.get("jiangmen_cdc")
    assert jiangmen is not None
    assert jiangmen.province == "广东省"
    assert jiangmen.city == "江门市"

@pytest.mark.asyncio
async def test_phase28_sources_fetch():
    xuzhou = SourceRegistry.get("xuzhou_cdc")
    items_xz = await xuzhou.fetch_announcements()
    assert len(items_xz) > 0
    detail_xz = await xuzhou.fetch_detail(items_xz[0].url)
    assert detail_xz is not None
    assert "徐州市" in detail_xz.city
    
    jinhua = SourceRegistry.get("jinhua_cdc")
    items_jh = await jinhua.fetch_announcements()
    assert len(items_jh) > 0
    detail_jh = await jinhua.fetch_detail(items_jh[0].url)
    assert detail_jh is not None
    assert "金华市" in detail_jh.city

    jiangmen = SourceRegistry.get("jiangmen_cdc")
    items_jm = await jiangmen.fetch_announcements()
    assert len(items_jm) > 0
    detail_jm = await jiangmen.fetch_detail(items_jm[0].url)
    assert detail_jm is not None
    assert "江门市" in detail_jm.city

def test_phase28_major_matcher_subdisciplines():
    pollutant_keywords = MajorMatcher.SUB_DISCIPLINE_KEYWORDS.get("新污染物健康风险与暴露组学")
    assert pollutant_keywords is not None
    assert "新污染物" in pollutant_keywords
    assert "环境暴露组学" in pollutant_keywords

    pathogen_keywords = MajorMatcher.SUB_DISCIPLINE_KEYWORDS.get("高通量病原宏基因组学与分子溯源")
    assert pathogen_keywords is not None
    assert "mNGS" in pathogen_keywords
    assert "分子溯源分析" in pathogen_keywords

def test_phase28_talent_policy_extractor():
    text1 = "本项目符合徐州市彭城英才引进标准，提供安家费60万元，实行直接面试考核入编。"
    res1 = TalentPolicyExtractor.extract_talent_policies(text1)
    assert res1["is_talent_intro"] is True
    assert res1["is_no_exam"] is True
    assert "60万" in str(res1["settlement_allowance"])

    text2 = "纳入金华市双龙引才计划，博士免笔试，购房补贴50万元。"
    res2 = TalentPolicyExtractor.extract_talent_policies(text2)
    assert res2["is_talent_intro"] is True
    assert res2["is_no_exam"] is True
    assert "50万" in str(res2["settlement_allowance"])

    text3 = "入选江门市侨都英才计划高层次人才，直接考核录用，提供安家补贴40万。"
    res3 = TalentPolicyExtractor.extract_talent_policies(text3)
    assert res3["is_talent_intro"] is True
    assert res3["is_no_exam"] is True
    assert "40万" in str(res3["settlement_allowance"])
