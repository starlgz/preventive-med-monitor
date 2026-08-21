import pytest
from app.sources.registry import SourceRegistry
from app.rules.major_matcher import MajorMatcher
from app.rules.bianzhi_evaluator import BianzhiEvaluator
from app.extractors.pitfall_extractor import PitfallExtractor
from app.extractors.talent_policy import TalentPolicyExtractor

from app.sources.wuxi_cdc import WuxiCdcSource
from app.sources.wenzhou_cdc import WenzhouCdcSource
from app.sources.foshan_cdc import FoshanCdcSource
from app.sources.dongguan_cdc import DongguanCdcSource
from app.sources.nantong_cdc import NantongCdcSource


def test_phase25_new_city_cdc_sources_registered():
    """验证本轮新增的 5 个万亿级/核心地级市疾控数据源正确注册到 SourceRegistry"""
    plugins_dict = SourceRegistry.discover_and_register()

    expected = [
        "wuxi_cdc",
        "wenzhou_cdc",
        "foshan_cdc",
        "dongguan_cdc",
        "nantong_cdc",
    ]
    for s in expected:
        assert s in plugins_dict, f"Plugin {s} should be registered in SourceRegistry"


def test_phase25_new_sources_instance_attributes():
    """验证新增疾控数据源实例属性（province, city, source_id）正确"""
    checks = [
        (WuxiCdcSource, "wuxi_cdc", "江苏省", "无锡市"),
        (WenzhouCdcSource, "wenzhou_cdc", "浙江省", "温州市"),
        (FoshanCdcSource, "foshan_cdc", "广东省", "佛山市"),
        (DongguanCdcSource, "dongguan_cdc", "广东省", "东莞市"),
        (NantongCdcSource, "nantong_cdc", "江苏省", "南通市"),
    ]
    for cls, sid, province, city in checks:
        inst = cls()
        assert inst.source_id == sid
        assert inst.province == province
        assert inst.city == city


@pytest.mark.asyncio
async def test_phase25_new_sources_fetch_mock_announcements():
    """验证新增疾控爬虫数据源 fetch_announcements 返回合法结构（含降级回退数据）"""
    plugins_dict = SourceRegistry.discover_and_register()
    new_sources = [
        "wuxi_cdc", "wenzhou_cdc", "foshan_cdc",
        "dongguan_cdc", "nantong_cdc",
    ]

    for s_id in new_sources:
        inst = plugins_dict.get(s_id)
        assert inst is not None, f"{s_id} not found in registry"
        items = await inst.fetch_announcements()
        assert isinstance(items, list), f"{s_id} should return a list"
        assert len(items) >= 1, f"{s_id} should return at least 1 fallback item"
        first = items[0]
        assert hasattr(first, "title")
        assert hasattr(first, "url")
        actual_sid = getattr(first, "source_id", None) or getattr(first, "source", None)
        assert actual_sid == s_id, f"{s_id}: source_id mismatch, got {actual_sid!r}"
        assert first.url.startswith("http")


def test_phase25_major_matcher_expansion():
    """验证专业匹配引擎对放射核化应急、环境暴露、多点触发预警与口岸检疫的识别与5星打分"""
    cases = [
        ("放射卫生检测", 5),
        ("核化生防护与检测", 5),
        ("多点触发预警", 5),
        ("智慧化疾控监测", 5),
        ("口岸传染病排查", 5),
        ("出入境检疫查验", 5),
        ("环境健康影响评价", 5),
        ("职业病危害因素监测", 5),
    ]
    for major_raw, expected_level in cases:
        res = MajorMatcher.match(major_raw=major_raw, job_name="疾控业务岗")
        assert res["match_level"] == expected_level, \
            f"{major_raw} expected level {expected_level}, got {res['match_level']}"

    text = "面向放射卫生检测、多点触发预警、国境卫生检疫和口岸传染病排查的技术人员"
    sub = MajorMatcher.find_sub_disciplines(text)
    assert "放射卫生与核化应急监测" in sub
    assert "智慧化多点触发预警" in sub
    assert "跨境与海关口岸传染病检疫" in sub


def test_phase25_bianzhi_pool_and_regional_center():
    """验证人才周转池编制及区域公卫中心编制的研判准确性"""
    res1 = BianzhiEvaluator.evaluate(
        job_name="公卫医师",
        unit_name="无锡市疾病预防控制中心",
        announcement_text="享受人才周转池事业编制，统一办理事业单位实名制入编手续"
    )
    assert res1["is_bianzhi"] == 1
    assert res1["bianzhi_type"] in ("全额事业编", "全额拨款事业编", "事业编制")
    assert res1["confidence"] >= 0.85

    res2 = BianzhiEvaluator.evaluate(
        job_name="高层次公卫骨干",
        unit_name="国家区域公共卫生中心",
        announcement_text="由国家区域公共卫生中心带编直聘，享受专项编制保障"
    )
    assert res2["is_bianzhi"] == 1
    assert res2["bianzhi_type"] in ("全额事业编", "全额拨款事业编", "事业编制")
    assert res2["confidence"] >= 0.85


def test_phase25_pitfall_and_talent_policy():
    """验证避坑提取器对基层调配、字字相符红线及新人才计划政策的提取"""
    pit_text = "聘用人员须服从偏远基层乡镇分院轮岗调配；报名专业名称须与毕业证一致且与目录字字相符，自设二级学科或研究方向不作为专业依据"
    pit_res = PitfallExtractor.analyze(text=pit_text)
    assert any("派驻风险" in p for p in pit_res.get("pitfalls", []))
    assert any("审核严格" in p for p in pit_res.get("pitfalls", []))
    assert len(pit_res.get("pitfalls", [])) >= 2

    talent_text = "入选无锡太湖人才计划或温州瓯越英才计划，给予安家费50万元，提供免租人才公寓，免笔试直接考核入编"
    talent_res = TalentPolicyExtractor.extract(text=talent_text)
    assert talent_res.get("is_talent_intro") is True
    assert talent_res.get("settlement_allowance") is not None or talent_res.get("is_no_exam") is True
