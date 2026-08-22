import pytest
from app.sources.anhui_wsjkw import AnhuiWsjkwSource
from app.sources.fujian_rsks import FujianRsksSource
from app.sources.chongqing_rsks import ChongqingRsksSource
from app.sources.provinces_pool import get_all_province_sources
from app.rules.major_matcher import MajorMatcher
from app.rules.bianzhi_evaluator import BianzhiEvaluator
from app.extractors.talent_policy import TalentPolicyExtractor

@pytest.mark.asyncio
async def test_crawler_sources_expanded():
    """测试新增的安徽、福建、重庆招考源插件基础解析"""
    # 1. 安徽卫健委
    anhui = AnhuiWsjkwSource()
    assert anhui.source_id == "anhui_wsjkw"
    assert anhui.province == "安徽"
    anhui_items = await anhui.fetch_latest_announcements()
    assert isinstance(anhui_items, list)
    assert len(anhui_items) > 0
    assert any("疾控" in item.title or "预防" in item.title for item in anhui_items)

    # 2. 福建人事考试网
    fujian = FujianRsksSource()
    assert fujian.source_id == "fujian_rsks"
    assert fujian.province == "福建"
    fujian_items = await fujian.fetch_latest_announcements()
    assert isinstance(fujian_items, list)
    assert len(fujian_items) > 0

    # 3. 重庆人社
    chongqing = ChongqingRsksSource()
    assert chongqing.source_id == "chongqing_rsks"
    assert chongqing.province == "重庆"
    cq_items = await chongqing.fetch_latest_announcements()
    assert isinstance(cq_items, list)
    assert len(cq_items) > 0

    # 4. 省份源池
    sources = get_all_province_sources()
    assert len(sources) >= 31

def test_major_sub_disciplines_matching():
    """测试预防医学细分专业与学科的高精度匹配"""
    # 毒理学
    m1 = MajorMatcher.match("卫生毒理学、毒物检验分析")
    assert m1["match_level"] == 4
    assert "卫生毒理学" in m1["sub_disciplines"]
    
    # 营养与食品卫生
    m2 = MajorMatcher.match("营养与食品卫生学、食品安全")
    assert m2["match_level"] == 4
    assert "营养与食品卫生学" in m2["sub_disciplines"]

    # 儿少与妇幼保健
    m3 = MajorMatcher.match("儿少卫生与妇幼保健学")
    assert m3["match_level"] == 4
    assert "儿少卫生与妇幼保健学" in m3["sub_disciplines"]

    # 流行病与卫生统计学
    m4 = MajorMatcher.match("流行病与卫生统计学")
    assert m4["match_level"] == 4

    # 劳动卫生与环境卫生学
    m5 = MajorMatcher.match("劳动卫生与环境卫生学")
    assert m5["match_level"] == 4

    # 非公卫专业排除
    m6 = MajorMatcher.match("计算机科学与技术、汉语言文学")
    assert m6["match_level"] == 1

def test_bianzhi_deep_evidence_chain():
    """测试升级后的编制判定置信度与证据链"""
    # 1. 劳务派遣
    res_dispatch = BianzhiEvaluator.evaluate(
        job_name="消毒专员",
        unit_name="某市疾控中心",
        other_requirements="劳务派遣用工，与第三方劳务公司签订劳动合同"
    )
    assert res_dispatch["is_bianzhi"] == 0
    assert res_dispatch["bianzhi_type"] == "合同制"
    assert res_dispatch["confidence"] >= 0.95
    assert "劳务派遣" in res_dispatch["evidence_chain"]

    # 2. 报备员额
    res_beian = BianzhiEvaluator.evaluate(
        job_name="院感质控科医师",
        unit_name="某三甲医院",
        other_requirements="按报备员额制管理，享受在编人员同等待遇同工同酬"
    )
    assert res_beian["is_bianzhi"] == 2
    assert res_beian["bianzhi_type"] == "报备员额"
    assert "报备员额" in res_beian["evidence_chain"]

    # 3. 正式事业编制
    res_formal = BianzhiEvaluator.evaluate(
        job_name="公卫医师",
        unit_name="成都市疾病预防控制中心",
        unit_type="疾控中心",
        announcement_title="成都市疾病预防控制中心2026年公开招聘事业单位工作人员公告"
    )
    assert res_formal["is_bianzhi"] == 1
    assert res_formal["confidence"] >= 0.6

def test_talent_policy_extraction():
    """测试高层次人才引进与免笔试补贴解析"""
    content = "针对博士研究生、公卫领军人才实行直接考核，免笔试。录用后给予安家费60万元，科研启动经费50万元，提供人才公寓，协调解决配偶工作。"
    res = TalentPolicyExtractor.extract_talent_policy(
        title="2026年疾控中心高层次紧缺急需人才引进公告",
        content=content
    )
    assert res["is_talent_introduction"] is True
    assert res["is_exam_exempt"] is True
    assert "安家费" in res["benefit_details"]
    assert "科研启动费" in res["benefit_details"]
    assert "解决配偶工作及子女优质入学" in res["benefits"]
