import pytest
import asyncio
from app.sources.gansu_cdc import GansuCdcSource
from app.sources.qinghai_cdc import QinghaiCdcSource
from app.sources.ningxia_cdc import NingxiaCdcSource
from app.sources.xinjiang_cdc import XinjiangCdcSource
from app.sources.xizang_wsjkw import XizangWsjkwSource
from app.sources.tianjin_cdc import TianjinCdcSource
from app.sources.neimenggu_cdc import NeimengguCdcSource
from app.sources.provinces_pool import get_all_province_sources, PROVINCE_SOURCES
from app.sources.registry import SourceRegistry
from app.rules.major_matcher import MajorMatcher
from app.extractors.talent_policy import TalentPolicyExtractor
from app.rules.bianzhi_evaluator import BianzhiEvaluator
from app.extractors.pitfall_extractor import PitfallExtractor

@pytest.mark.asyncio
async def test_northwest_and_national_coverage_sources():
    """验证西北及华北/西藏等新增 7 省市疾控/卫健委爬虫源适配器"""
    sources_to_test = [
        GansuCdcSource(),
        QinghaiCdcSource(),
        NingxiaCdcSource(),
        XinjiangCdcSource(),
        XizangWsjkwSource(),
        TianjinCdcSource(),
        NeimengguCdcSource()
    ]
    
    for s in sources_to_test:
        assert s.name is not None
        assert s.base_url is not None
        assert s.province in ["甘肃", "青海", "宁夏", "新疆", "西藏", "天津", "内蒙古"]
        items = await s.fetch_announcements()
        assert isinstance(items, list)
        assert len(items) >= 1
        item = items[0]
        assert hasattr(item, "title") and item.title
        assert hasattr(item, "url") and item.url

def test_registry_contains_all_sources():
    """验证注册表中包含了所有省份爬虫源"""
    registry = SourceRegistry.discover_and_register()
    
    assert "gansu_cdc" in registry
    assert "qinghai_cdc" in registry
    assert "ningxia_cdc" in registry
    assert "xinjiang_cdc" in registry
    assert "xizang_wsjkw" in registry
    assert "tianjin_cdc" in registry
    assert "neimenggu_cdc" in registry

    gansu = registry["gansu_cdc"]
    assert gansu.province == "甘肃"
    assert "疾病预防控制中心" in gansu.name

def test_fine_grained_emergency_and_biosecurity_major_match():
    """测试卫生应急与生物安全细分二级学科精准匹配"""
    res1 = MajorMatcher.match(major_raw="卫生应急与生物安全", job_name="突发公共卫生应急处置岗")
    assert res1["match_level"] == 4
    assert "卫生应急与生物安全" in res1["sub_disciplines"]
    assert "卫生应急" in res1["sub_disciplines"]["卫生应急与生物安全"]

    res2 = MajorMatcher.match(major_raw="实验室生物安全防护", job_name="P3实验室质控岗")
    assert res2["match_level"] == 4
    assert "卫生应急与生物安全" in res2["sub_disciplines"]
    assert "实验室生物安全" in res2["sub_disciplines"]["卫生应急与生物安全"]

def test_talent_policy_extractor_top_tier():
    """测试高层次引才及安家补贴精准提取"""
    text = "2026年兰州市疾控中心紧缺人才引进公告：面向博士研究生实行免笔试直接考核面试，提供一次性安家费50万元，提供科研启动经费30万元，免租金入住人才公寓并协助解决子女入学。"
    talent = TalentPolicyExtractor.extract_talent_policies(text=text, job_title="公卫骨干", requirements="博士")
    assert talent["is_talent_intro"] is True
    assert talent["is_no_written_exam"] is True
    assert talent["policy_tier"] == "S"
    assert talent["housing_subsidy_amt"] == 500000
    assert talent["research_fund_amt"] == 300000
    assert "住房保障" in talent["special_benefits"]
    assert "子女入学" in talent["special_benefits"]

def test_bianzhi_confidence_and_evidence():
    """测试全额拨款事业编制与报备员额自然语言证据链"""
    text = "本次招聘人员均纳入地方财政全额拨款实名制事业编制管理，执行国家事业单位工资福利政策。"
    eval_res = BianzhiEvaluator.evaluate(
        text=text,
        job_name="传染病预防控制科业务骨干",
        source_name="2026年银川市疾控中心公开招聘事业编制人员公告"
    )
    assert eval_res["bianzhi_type"] == "全额事业编"
    assert eval_res["confidence"] >= 0.85
    assert len(eval_res["evidence_chain"]) >= 1

def test_pitfall_extractor_analysis():
    """测试最低服务年限与劳务派遣风险提取"""
    text = "录用人员实行劳动合同制管理，与第三方人力资源公司签订劳务派遣合同，最低服务期5年，违约赔偿金5万元。"
    pitfalls = PitfallExtractor.extract(text=text)
    assert len(pitfalls) > 0
    full_str = str(pitfalls)
    assert "劳务派遣" in full_str or "服务期" in full_str or "违约" in full_str
