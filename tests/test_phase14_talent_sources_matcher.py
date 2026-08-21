import pytest
from app.sources.registry import SourceRegistry
from app.sources.guangdong_wsjkw import GuangdongWsjkwSource
from app.sources.sichuan_wsjkw import SichuanWsjkwSource
from app.sources.beijing_wsjkw import BeijingWsjkwSource
from app.rules.major_matcher import MajorMatcher
from app.extractors.talent_policy import TalentPolicyExtractor
from app.rules.bianzhi_evaluator import BianzhiEvaluator

@pytest.mark.asyncio
async def test_sources_registration_and_fetch():
    # 测试注册中心热加载
    plugins = SourceRegistry.discover_and_register()
    assert "guangdong_wsjkw" in plugins
    assert "sichuan_wsjkw" in plugins
    assert "beijing_wsjkw" in plugins

    # 验证广东卫健源
    gd_source = plugins["guangdong_wsjkw"]
    items = await gd_source.fetch_announcements()
    assert len(items) > 0
    detail = await gd_source.fetch_detail(items[0].url)
    assert detail is not None
    assert "广东" in detail.title or "广东" in detail.content_text

    # 验证四川卫健源
    sc_source = plugins["sichuan_wsjkw"]
    items_sc = await sc_source.fetch_announcements()
    assert len(items_sc) > 0
    detail_sc = await sc_source.fetch_detail(items_sc[0].url)
    assert detail_sc is not None
    assert len(detail_sc.attachments) > 0

    # 验证北京卫健源
    bj_source = plugins["beijing_wsjkw"]
    items_bj = await bj_source.fetch_announcements()
    assert len(items_bj) > 0
    detail_bj = await bj_source.fetch_detail(items_bj[0].url)
    assert detail_bj is not None
    assert "北京" in detail_bj.title or "北京" in detail_bj.content_text

def test_major_matcher_enhanced_disciplines_and_degrees():
    # 1. 卫生毒理学五星/四星与细分提取
    res_tox = MajorMatcher.match("卫生毒理学、毒理检验方向", job_name="理化检验科业务骨干")
    assert res_tox["match_level"] in [4, 5]
    assert "卫生毒理学" in res_tox["sub_disciplines"]
    assert "卫生毒理" in res_tox["sub_disciplines"]["卫生毒理学"]

    # 2. 儿少卫生与妇幼保健学
    res_mch = MajorMatcher.match("儿少卫生与妇幼保健学，少儿卫生方向", job_name="妇女儿童保健科医师")
    assert res_mch["match_level"] == 5
    assert "儿少卫生与妇幼保健学" in res_mch["sub_disciplines"]

    # 3. 劳动卫生与环境卫生学
    res_occ = MajorMatcher.match("劳动卫生与环境卫生学、职业卫生", job_name="公卫医师")
    assert res_occ["match_level"] == 4
    assert "劳动卫生与环境卫生学" in res_occ["sub_disciplines"]

    # 4. 学历层级提取
    res_deg = MajorMatcher.match("预防医学（限博士研究生学历，取得博士学位）", job_name="科研岗")
    assert res_deg["match_level"] == 5
    assert res_deg["degree_req"]["min_degree"] == "博士"
    assert "博士" in res_deg["degree_req"]["matched_degrees"]

    # 5. 专硕与代码匹配
    res_mph = MajorMatcher.match("公共卫生硕士(MPH)，专业代码：1053", job_name="流行病调查员")
    assert res_mph["match_level"] == 4

def test_talent_policy_extractor_full():
    text_sample = """
    本次招聘为高层次人才引进专项计划，实行免笔试直接考核面试流程。
    符合条件的高校博士毕业生可享受安家费最高达50万元，提供科研启动经费30万元。
    单位落实全额事业编制，解决北京户口，协助解决子女入学并提供人才周转房。
    """
    res = TalentPolicyExtractor.extract_talent_policies(text_sample, job_title="疾控中心公卫医师")
    assert res["is_talent_intro"] is True
    assert res["is_no_written_exam"] is True
    assert res["exam_form"] == "免笔试/直接考核"
    assert "50万" in res["settlement_allowance"] or "50万元" in res["settlement_allowance"]
    assert "30万" in res["research_fund"] or "30万元" in res["research_fund"]
    assert "户口解决" in res["special_benefits"]
    assert "解决编制" in res["special_benefits"]
    assert "子女入学" in res["special_benefits"]
    assert res["policy_tier"] == "S"

def test_bianzhi_confidence_engine_with_evidence():
    # 结合自然语言证据链的编制置信度判定测试
    context = "本单位系公益一类全额拨款事业单位，招聘人员纳入用人单位事业编制实名制管理，依法签订聘用合同。"
    evaluator = BianzhiEvaluator()
    res = evaluator.evaluate(job_name="理化检验岗", unit_name="某省疾病预防控制中心", announcement_text=context)
    assert res["bianzhi_type"] == "全额事业编"
    assert res["confidence"] >= 0.90
    assert len(res["evidence_chain"]) > 0
    assert any("全额" in e or "公益一类" in e for e in res["evidence_chain"])
