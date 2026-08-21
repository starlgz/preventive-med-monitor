import pytest
from app.rules.major_matcher import MajorMatcher
from app.rules.bianzhi_evaluator import BianzhiEvaluator
from app.extractors.talent_policy import TalentPolicyExtractor
from app.extractors.pitfall_extractor import PitfallExtractor
from app.sources.registry import SourceRegistry

def test_cdc_sources_expansion():
    """验证新增重点省份疾控中心与卫健委官方源"""
    registry = SourceRegistry.discover_and_register()
    
    assert "sichuan_cdc" in registry
    assert "chongqing_cdc" in registry
    assert "guizhou_cdc" in registry
    assert "yunnan_cdc" in registry
    assert "guangxi_cdc" in registry
    assert "hainan_cdc" in registry
    assert "liaoning_cdc" in registry
    assert "jilin_cdc" in registry
    assert "heilongjiang_cdc" in registry
    assert "jiangxi_wsjkw" in registry
    assert "shaanxi_wsjkw" in registry
    assert "shanxi_wsjkw" in registry

    sc_cdc = registry["sichuan_cdc"]
    assert sc_cdc.province == "四川"
    assert "疾病预防控制中心" in sc_cdc.name

    cq_cdc = registry["chongqing_cdc"]
    assert cq_cdc.province == "重庆"
    assert "疾病预防控制中心" in cq_cdc.name

    hlj_cdc = registry["heilongjiang_cdc"]
    assert hlj_cdc.province == "黑龙江"

def test_fine_grained_specialty_sub_disciplines():
    """验证预防医学二级/细分专业与交叉学科匹配"""
    r1 = MajorMatcher.match(major_raw="卫生毒理学与分子毒理", job_name="毒理室业务骨干")
    assert r1["match_level"] == 4
    assert "卫生毒理学" in r1["sub_disciplines"]

    r2 = MajorMatcher.match(major_raw="全球健康学与卫生应急管理", job_name="疾控应急处置专员")
    assert r2["match_level"] in [4, 5]
    assert "全球健康学" in r2["sub_disciplines"] or "社会医学与卫生事业管理" in r2["sub_disciplines"]

    r3 = MajorMatcher.match(major_raw="少儿卫生与妇幼保健学", job_name="妇幼保健医师")
    assert r3["match_level"] == 5
    assert "儿少卫生与妇幼保健学" in r3["sub_disciplines"]

def test_talent_policy_allowance_and_exemptions():
    """验证人才引进政策免笔试、安家费数值解析与S级评定"""
    text = """
    【重点疾控中心2026年高层次人才引进公告】
    对预防医学、流行病学相关专业博士研究生开辟绿色通道，免笔试直接考核聘用。
    享受全额拨款事业编制，发放一次性安家费30万元，提供科研启动经费20万元。
    提供人才周转公寓，协助解决子女入学。
    """
    res = TalentPolicyExtractor.extract_talent_policies(text=text, job_title="公卫骨干", requirements="博士")
    assert res["is_talent_intro"] is True
    assert res["is_no_written_exam"] is True
    assert res["policy_tier"] == "S"
    assert res["housing_subsidy_amt"] == 300000
    assert res["research_fund_amt"] == 200000
    assert "住房保障" in res["special_benefits"]
    assert "子女入学" in res["special_benefits"]

def test_bianzhi_confidence_weighting():
    """验证编制多维置信度引擎及证据链"""
    text = "本批次拟公开招聘疾控专业技术人员20名，全部录用人员纳入财政全额拨款实名制事业编制管理。"
    res = BianzhiEvaluator.evaluate(
        text=text,
        job_name="公共卫生检验医师",
        source_name="四川省疾病预防控制中心公开招聘公告"
    )
    assert res["bianzhi_type"] == "全额事业编"
    assert res["confidence"] >= 0.85
    assert "实名制编制" in res["evidence_chain"] or "全额拨款事业单位" in res["evidence_chain"]

def test_pitfall_extractor_safety():
    """验证排坑预警引擎"""
    text = "录用人员实行劳动合同制管理，与第三方人力资源公司签订劳务派遣合同，最低服务期5年，违约赔偿金5万元。"
    pitfalls = PitfallExtractor.extract(text=text)
    assert len(pitfalls) > 0
    full_str = str(pitfalls)
    assert "服务期" in full_str or "违约" in full_str
