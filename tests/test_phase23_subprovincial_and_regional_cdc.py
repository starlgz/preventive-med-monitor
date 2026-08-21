import pytest
from app.sources.registry import SourceRegistry
from app.rules.major_matcher import MajorMatcher
from app.rules.bianzhi_evaluator import BianzhiEvaluator
from app.extractors.talent_policy import TalentPolicyExtractor

# 直接导入各新增插件以验证注册正常
from app.sources.jinan_cdc import JinanCdcSource
from app.sources.shenyang_cdc import ShenyangCdcSource
from app.sources.harbin_cdc import HarbinCdcSource
from app.sources.changchun_cdc import ChangchunCdcSource
from app.sources.suzhou_cdc import SuzhouCdcSource
from app.sources.changsha_cdc import ChangshaCdcSource
from app.sources.hefei_cdc import HefeiCdcSource
from app.sources.fuzhou_cdc import FuzhouCdcSource


def test_new_subprovincial_and_regional_sources_registered():
    """验证新扩展的副省级与重点区域疾控中心数据源正确注册到 SourceRegistry"""
    plugins_dict = SourceRegistry.discover_and_register()

    expected_sources = [
        "jinan_cdc",
        "shenyang_cdc",
        "harbin_cdc",
        "changchun_cdc",
        "suzhou_cdc",
        "changsha_cdc",
        "hefei_cdc",
        "fuzhou_cdc"
    ]

    for s in expected_sources:
        assert s in plugins_dict, f"Plugin {s} should be registered in SourceRegistry"


def test_new_sources_instance_attributes():
    """验证新增疾控数据源实例属性（province, city, source_id）正确"""
    checks = [
        (JinanCdcSource, "jinan_cdc", "山东省", "济南市"),
        (ShenyangCdcSource, "shenyang_cdc", "辽宁省", "沈阳市"),
        (HarbinCdcSource, "harbin_cdc", "黑龙江省", "哈尔滨市"),
        (ChangchunCdcSource, "changchun_cdc", "吉林省", "长春市"),
        (SuzhouCdcSource, "suzhou_cdc", "江苏省", "苏州市"),
        (ChangshaCdcSource, "changsha_cdc", "湖南省", "长沙市"),
        (HefeiCdcSource, "hefei_cdc", "安徽省", "合肥市"),
        (FuzhouCdcSource, "fuzhou_cdc", "福建省", "福州市"),
    ]
    for cls, sid, province, city in checks:
        inst = cls()
        assert inst.source_id == sid, f"{cls.__name__} source_id mismatch"
        assert inst.province == province, f"{cls.__name__} province mismatch"
        assert inst.city == city, f"{cls.__name__} city mismatch"


@pytest.mark.asyncio
async def test_new_sources_fetch_mock_announcements():
    """验证新增疾控爬虫数据源 fetch_announcements 返回合法结构（含降级回退数据）"""
    plugins_dict = SourceRegistry.discover_and_register()
    new_sources = [
        "jinan_cdc", "shenyang_cdc", "harbin_cdc", "changchun_cdc",
        "suzhou_cdc", "changsha_cdc", "hefei_cdc", "fuzhou_cdc"
    ]

    for s_id in new_sources:
        inst = plugins_dict.get(s_id)
        assert inst is not None, f"{s_id} not found in registry"
        items = await inst.fetch_announcements()
        assert isinstance(items, list), f"{s_id} should return a list"
        assert len(items) >= 1, f"{s_id} should return at least 1 fallback item"
        first = items[0]
        assert hasattr(first, "title"), f"{s_id}: item missing title"
        assert hasattr(first, "url"), f"{s_id}: item missing url"
        # source_id 字段（RawAnnouncementItem 中用 source_id）
        actual_sid = getattr(first, "source_id", None) or getattr(first, "source", None)
        assert actual_sid == s_id, f"{s_id}: source_id field mismatch, got {actual_sid!r}"
        assert first.url.startswith("http"), f"{s_id}: url should start with http"


def test_enhanced_major_matcher_public_health_frontiers():
    """测试前沿公共卫生专业与细分方向的 5 星匹配精准度"""
    # 1. 全球健康学 / 跨境卫生检疫
    res_global = MajorMatcher.match(major_raw="全球健康学与跨境卫生检疫", job_name="国际卫生应急处置岗")
    assert res_global["match_level"] == 5, f"全球健康学 expected level 5, got {res_global['match_level']}"
    assert any("全球健康" in str(c) for c in res_global["matched_codes"])

    # 2. 现场流行病学 (FETP)
    res_fetp = MajorMatcher.match(major_raw="现场流行病学", job_name="突发疫情流调溯源专员")
    assert res_fetp["match_level"] == 5, f"现场流行病学 expected level 5, got {res_fetp['match_level']}"

    # 3. 病原微生物基因组学
    res_p3 = MajorMatcher.match(major_raw="病原微生物基因组学", job_name="P3实验室高通量测序分析岗")
    assert res_p3["match_level"] == 5, f"病原微生物基因组学 expected level 5, got {res_p3['match_level']}"

    # 4. 病媒生物防制
    res_vector = MajorMatcher.match(major_raw="病媒生物防制", job_name="登革热媒介伊蚊控制岗")
    assert res_vector["match_level"] == 5, f"病媒生物防制 expected level 5, got {res_vector['match_level']}"

    # 5. 食品安全风险监测
    res_food = MajorMatcher.match(major_raw="食品安全风险监测", job_name="理化检验与营养干预岗")
    assert res_food["match_level"] == 5, f"食品安全风险监测 expected level 5, got {res_food['match_level']}"


def test_enhanced_bianzhi_evaluator_subtypes():
    """测试编制研判引擎针对入编直聘公告的高置信度识别"""
    res1 = BianzhiEvaluator.evaluate(
        job_name="公共卫生卓越学者（入编）",
        unit_name="济南市疾病预防控制中心",
        announcement_title="济南市疾控中心2026年高层次人才直聘事业单位编制公告",
        announcement_text="录用人员纳入实名制事业编制，享受公益一类全额拨款事业单位在编人员待遇。"
    )
    assert res1["is_bianzhi"] == 1
    assert res1["confidence"] >= 0.85
    assert res1["bianzhi_type"] in ("全额事业编", "全额拨款事业编", "事业编制")

    res2 = BianzhiEvaluator.evaluate(
        job_name="分子流调博士后研究员",
        unit_name="苏州市疾病预防控制中心",
        announcement_title="苏州市疾控中心卓越公卫学者招聘",
        announcement_text="本岗位实行卓越公卫学者入编保障，进站即落实全额事业编制，出站留编。"
    )
    assert res2["is_bianzhi"] == 1
    assert res2["confidence"] >= 0.85


def test_enhanced_talent_policy_extractor_regional_plans():
    """测试地方特色公卫人才计划与免笔试直聘抽取，验证实际返回字段"""
    text = (
        "苏州市疾控中心启动姑苏卫生人才专项，拟选聘高层次流行病学带头人。"
        "本次招聘简化考试程序，实行免笔试直接面试考核。"
        "入选者提供一次性安家费80万元，提供科研启动经费150万元，"
        "免租人才公寓一套，并协助解决配偶工作及子女优质入学。"
    )
    talent_res = TalentPolicyExtractor.extract_talent_policies(text=text)

    assert talent_res["is_no_exam"] is True
    assert talent_res["is_talent_intro"] is True
    # settlement_allowance 字段
    assert talent_res.get("settlement_allowance") is not None
    # 实际金额字段：housing_subsidy_amt (int)
    assert talent_res.get("housing_subsidy_amt") == 800000
    # 科研经费金额字段：research_fund_amt (int)
    assert talent_res.get("research_fund_amt") == 1500000
    # 特殊福利
    special = talent_res.get("special_benefits", [])
    assert "住房保障" in special
    assert "子女入学" in special
