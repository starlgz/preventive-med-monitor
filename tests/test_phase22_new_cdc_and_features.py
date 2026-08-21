import pytest
from app.sources.registry import SourceRegistry
from app.sources.xiamen_cdc import XiamenCdcSource
from app.sources.dalian_cdc import DalianCdcSource
from app.sources.ningbo_cdc import NingboCdcSource
from app.rules.major_matcher import MajorMatcher
from app.rules.bianzhi_evaluator import BianzhiEvaluator
from app.extractors.talent_policy import TalentPolicyExtractor

@pytest.mark.asyncio
async def test_new_city_cdc_plugins_registered():
    sources = SourceRegistry.discover_and_register()
    
    assert "xiamen_cdc" in sources
    assert "dalian_cdc" in sources
    assert "ningbo_cdc" in sources
    
    xm = sources["xiamen_cdc"]
    assert isinstance(xm, XiamenCdcSource)
    assert xm.province == "福建省"
    assert xm.city == "厦门市"
    
    dl = sources["dalian_cdc"]
    assert isinstance(dl, DalianCdcSource)
    assert dl.province == "辽宁省"
    assert dl.city == "大连市"

    nb = sources["ningbo_cdc"]
    assert isinstance(nb, NingboCdcSource)
    assert nb.province == "浙江省"
    assert nb.city == "宁波市"

def test_ai_and_emergency_subdisciplines_matching():
    text1 = "招聘医学人工智能与公卫大数据分析研究人员，负责智慧公卫建模"
    match1 = MajorMatcher.match(major_raw=text1, unit_type="疾控中心", job_name="智慧公卫岗")
    assert "医学与公卫人工智能" in match1["sub_disciplines"]
    assert match1["match_level"] >= 3

    text2 = "公卫应急与突发公共卫生事件理化快检技术员，要求精通卫生化验"
    match2 = MajorMatcher.match(major_raw=text2, unit_type="疾控中心", job_name="应急检测岗")
    assert "公卫应急与卫生化验" in match2["sub_disciplines"]
    assert match2["match_level"] >= 4

def test_enhanced_bianzhi_and_talent_policy():
    res = BianzhiEvaluator.evaluate(
        job_name="理化检验科技术骨干",
        unit_name="大连市疾病预防控制中心",
        unit_type="疾控中心",
        announcement_title="大连市疾病预防控制中心2026年全额事业编制高层次人才招聘",
        announcement_text="本次招聘人员均纳入财政全额拨款事业编制管理，提供人才公寓和30万元安家补贴。"
    )
    assert res["is_bianzhi"] == 1
    assert res["bianzhi_type"] == "全额事业编"
    assert res["confidence"] >= 0.85
    
    talent = TalentPolicyExtractor.extract_talent_policies(
        text="本次招聘属于高层次人才引进，免笔试直接考核面试，提供科研启动费50万元，安家费30万元，保障子女入学。"
    )
    assert talent["tier"] == "S"
    assert talent["is_no_exam"] is True
    assert talent["is_talent_intro"] is True
    assert "科研启动费" in talent["allowance_summary"]
