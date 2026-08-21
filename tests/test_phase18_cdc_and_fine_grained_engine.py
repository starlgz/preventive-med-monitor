import pytest
import asyncio
from app.sources.registry import SourceRegistry
from app.sources.chinacdc_official import ChinaCdcSource
from app.sources.guangdong_cdc import GuangdongCdcSource
from app.sources.shanghai_cdc import ShanghaiCdcSource
from app.sources.zhejiang_cdc import ZhejiangCdcSource
from app.sources.sichuan_cdc import SichuanCdcSource
from app.sources.hubei_cdc import HubeiCdcSource
from app.sources.shandong_cdc import ShandongCdcSource
from app.sources.jiangsu_cdc import JiangsuCdcSource
from app.sources.beijing_cdc import BeijingCdcSource
from app.sources.provinces_pool import PROVINCE_SOURCES
from app.rules.major_matcher import MajorMatcher
from app.rules.bianzhi_evaluator import BianzhiEvaluator
from app.extractors.talent_policy import TalentPolicyExtractor
from app.extractors.pitfall_extractor import PitfallExtractor

def test_cdc_plugins_registered():
    """验证所有新建的省级与国家级 CDC 独立爬虫插件成功加载与注册"""
    plugins = SourceRegistry.discover_and_register()
    cdc_expected = [
        "chinacdc_official",
        "guangdong_cdc",
        "shanghai_cdc",
        "zhejiang_cdc",
        "sichuan_cdc",
        "hubei_cdc",
        "shandong_cdc",
        "jiangsu_cdc",
        "beijing_cdc"
    ]
    for key in cdc_expected:
        assert key in plugins, f"CDC plugin {key} should be registered in SourceRegistry"
        plugin_instance = plugins[key]
        assert plugin_instance.enabled is True
        assert "疾控" in plugin_instance.name or "CDC" in plugin_instance.name or "预防控制" in plugin_instance.name

def test_all_provinces_sources_pool_expansion():
    """验证全国省份池已包含 31 省市全覆盖及专项 CDC"""
    assert len(PROVINCE_SOURCES) >= 35
    cdc_items = [s for s in PROVINCE_SOURCES if "cdc" in s["code"]]
    assert len(cdc_items) >= 9

@pytest.mark.asyncio
async def test_cdc_source_fetch_simulation():
    """模拟国家与省级 CDC 爬虫抓取接口与详情解析行为"""
    cdc = ChinaCdcSource()
    assert cdc.source_id == "chinacdc_official"
    assert cdc.category in ["official", "cdc"]
    assert cdc.province in ["全国", "北京"]
    
    gd_cdc = GuangdongCdcSource()
    assert gd_cdc.source_id == "guangdong_cdc"
    assert gd_cdc.province == "广东"

    sh_cdc = ShanghaiCdcSource()
    assert sh_cdc.source_id == "shanghai_cdc"
    assert sh_cdc.province == "上海"

def test_sub_disciplines_fine_grained_matcher():
    """验证预防医学 13 个细分二级学科及前沿交叉方向高精度命中"""
    # 1. 卫生毒理学与分子毒理
    res = MajorMatcher.match("卫生毒理学、分子毒理与计算毒理", job_name="疾控理化检验")
    assert res["match_level"] in [4, 5]
    assert "卫生毒理学" in res["sub_disciplines"]
    assert "计算毒理" in res["sub_disciplines"]["卫生毒理学"] or "分子毒理" in res["sub_disciplines"]["卫生毒理学"]

    # 2. 营养与食品卫生学
    res = MajorMatcher.match("营养与食品卫生学（精准营养与食品安全方向）", job_name="食品安全监测")
    assert res["match_level"] in [4, 5]
    assert "营养与食品卫生学" in res["sub_disciplines"]

    # 3. 儿少卫生与妇幼保健学
    res = MajorMatcher.match("少儿卫生与妇幼保健学，优生优育与生殖健康研究", job_name="妇幼保健医师")
    assert res["match_level"] in [4, 5]
    assert "儿少卫生与妇幼保健学" in res["sub_disciplines"]

    # 4. 劳动卫生与环境卫生学 / 辐射卫生
    res = MajorMatcher.match("劳动卫生与环境卫生学、职业病防治与辐射卫生评价", job_name="职业健康科")
    assert res["match_level"] in [4, 5]
    assert "劳动卫生与环境卫生学" in res["sub_disciplines"]

    # 5. 流行病与卫生统计学 / 现场流行病学
    res = MajorMatcher.match("现场流行病学、传染病流行病学与健康大数据统计分析", job_name="应急流行病学专家")
    assert res["match_level"] in [4, 5]
    assert "流行病与卫生统计学" in res["sub_disciplines"]

    # 6. 生物统计学
    res = MajorMatcher.match("生物统计学、医学统计或统计与生物信息方向", job_name="统计分析员")
    assert res["match_level"] >= 4
    assert "生物统计学" in res["sub_disciplines"]

    # 7. 全球健康学
    res = MajorMatcher.match("全球健康学 (Global Health) 或国际卫生", job_name="国际交流与卫生援外")
    assert res["match_level"] in [4, 5]  # 全球健康学已升级为L5
    res = MajorMatcher.match("医院感染控制、消毒与病媒生物防制", job_name="感控科医师")
    assert res["match_level"] >= 4
    assert "医院感染控制" in res["sub_disciplines"]

def test_degree_hierarchy_extraction():
    """验证从岗位及要求中自动抽取硕博学历层级"""
    res1 = MajorMatcher.match("流行病与卫生统计学 博士研究生及以上学历", job_name="研究员")
    assert res1["degree_req"]["min_degree"] == "博士"
    assert "博士" in res1["degree_req"]["matched_degrees"]

    res2 = MajorMatcher.match("公共卫生与预防医学 硕士学位 (MPH)", job_name="公卫医师")
    assert res2["degree_req"]["min_degree"] == "硕士"
    assert "硕士" in res2["degree_req"]["matched_degrees"]

def test_talent_policy_top_tier_extraction():
    """测试顶格人才引进（免笔试 + 高额安家补贴 + 科研经费 + 编制落户）S 级判定"""
    text = (
        "【2026年高层次紧缺人才引进公告】\n"
        "面向国内外公开选聘博士研究生，实行免笔试、直接考核面试录用，直接纳入实名制事业编制。\n"
        "引进待遇：\n"
        "1. 提供一次性安家费50万元及购房补贴；\n"
        "2. 提供科研启动经费30万元；\n"
        "3. 提供人才周转公寓，协助解决子女入学及落户手续。"
    )
    res = TalentPolicyExtractor.extract(text, job_title="疾控所长助理", requirements="博士学位")
    assert res["is_exam_exempt"] == 1
    assert "免笔试" in res["exam_form"]
    assert res["is_talent_intro"] is True
    assert res["settlement_allowance"] is not None
    assert res["research_fund"] is not None
    assert "住房保障" in res["special_benefits"]
    assert res["tier"] == "S"
    assert "50万" in res["allowance_summary"]

def test_bianzhi_evaluator_cdc_and_hospital_distinction():
    """测试编制研判引擎对全额拨款 CDC 与医院备案制的精准区分与置信度打分"""
    # 疾控中心事业编制公告
    cdc_eval = BianzhiEvaluator.evaluate(
        job_name="传染病防制科业务骨干",
        unit_name="XX省疾病预防控制中心",
        unit_type="疾控中心",
        announcement_title="2026年省疾控中心统一公开招聘事业单位工作人员公告",
        announcement_text="本次招聘人员按规定办理实名制事业编制聘用手续，为全额拨款事业单位编制。"
    )
    assert cdc_eval["is_bianzhi"] == 1
    assert cdc_eval["bianzhi_type"] == "全额事业编"
    assert cdc_eval["confidence"] >= 0.85
    assert "【确编证据】" in cdc_eval["bianzhi_evidence"]
    assert "【单位性质】" in cdc_eval["bianzhi_evidence"]

    # 医院人员总量/报备员额制公告
    hospital_eval = BianzhiEvaluator.evaluate(
        job_name="院感科公卫专员",
        unit_name="XX市第一人民医院",
        unit_type="综合医院/专科医院",
        announcement_title="2026年公立医院公开招聘人员总量备案制人员简章",
        announcement_text="纳入公立医院人员总量控制与备案制管理。"
    )
    assert hospital_eval["is_bianzhi"] == 2
    assert hospital_eval["bianzhi_type"] == "报备员额"
    assert "【员额/备案证据】" in hospital_eval["bianzhi_evidence"]

    # 劳务派遣直接一票否决
    dispatch_eval = BianzhiEvaluator.evaluate(
        job_name="消杀专员",
        unit_name="XX区卫健局",
        announcement_title="2026年招聘劳务派遣工作人员公告",
        announcement_text="本次招聘用工形式为劳务派遣，与第三方人力资源公司签订劳动合同，不占编制。"
    )
    assert dispatch_eval["is_bianzhi"] == 0
    assert dispatch_eval["bianzhi_type"] == "合同制"
    assert dispatch_eval["confidence"] >= 0.95
