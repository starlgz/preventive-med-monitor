import pytest
from app.sources.registry import SourceRegistry
from app.sources.guizhou_wsjkw import GuizhouWsjkwSource
from app.sources.yunnan_wsjkw import YunnanWsjkwSource
from app.sources.jiangxi_wsjkw import JiangxiWsjkwSource
from app.rules.bianzhi_evaluator import BianzhiEvaluator
from app.extractors.talent_policy import TalentPolicyExtractor

@pytest.mark.asyncio
async def test_sources_registration_and_metadata():
    registry = SourceRegistry.discover_and_register()
    assert "guizhou_wsjkw_custom" in registry or "guizhou_wsjkw" in registry
    assert "yunnan_wsjkw" in registry
    assert "jiangxi_wsjkw" in registry
    
    gz_src = GuizhouWsjkwSource()
    assert gz_src.province == "贵州"
    assert gz_src.category == "official"
    
    yn_src = YunnanWsjkwSource()
    assert yn_src.province == "云南"
    
    jx_src = JiangxiWsjkwSource()
    assert jx_src.province == "江西"

def test_bianzhi_evidence_chain_and_weights():
    evaluator = BianzhiEvaluator()
    res = evaluator.evaluate(
        job_name="公共卫生医师",
        unit_name="江西省疾病预防控制中心",
        announcement_text="本中心为全额拨款公益一类事业单位，办理实名制事业编制入编手续。"
    )
    assert res["is_bianzhi"] == 1
    assert res["bianzhi_type"] == "全额事业编"
    assert "全额拨款事业单位" in res["evidence_chain"] or "事业编制" in res["evidence_chain"]
    assert res["confidence"] >= 0.8
    assert "实名制" in res["bianzhi_evidence"] or "全额" in res["bianzhi_evidence"]

def test_talent_policy_structured_extraction():
    sample_text = """
    招聘高层次紧缺专业人才公告：
    针对流行病与卫生统计学、卫生毒理学博士研究生，实行免笔试直接考核面试招聘。
    入职提供安家费50万元，科研启动经费30万元，免费提供人才公寓一套，协助解决子女入学及配偶工作随迁。
    """
    res = TalentPolicyExtractor.extract(sample_text, job_name="学科带头人")
    assert res["is_talent_intro"] is True
    assert res["has_housing_or_subsidy"] is True
    assert "免笔试" in res["highlights"]
    assert res["settling_allowance"] == "50万元" or "50万" in str(res["settling_allowance"])
    assert res["research_fund"] == "30万元" or "30万" in str(res["research_fund"])
    assert res["talent_level"] in ["高层次人才", "紧缺人才", "领军人才", "博士研究生"]
