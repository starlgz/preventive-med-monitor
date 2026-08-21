import pytest
import asyncio
from app.sources.registry import SourceRegistry, get_source_by_key, list_all_sources
from app.sources.shenzhen_cdc import ShenzhenCdcSource
from app.sources.guangzhou_cdc import GuangzhouCdcSource
from app.sources.hangzhou_cdc import HangzhouCdcSource
from app.sources.nanjing_cdc import NanjingCdcSource
from app.sources.wuhan_cdc import WuhanCdcSource
from app.sources.chengdu_cdc import ChengduCdcSource
from app.sources.qingdao_cdc import QingdaoCdcSource
from app.sources.xian_cdc import XianCdcSource
from app.rules.major_matcher import MajorMatcher
from app.rules.bianzhi_evaluator import BianzhiEvaluator
from app.extractors.talent_policy import TalentPolicyExtractor
from app.extractors.pitfall_extractor import PitfallExtractor

@pytest.mark.asyncio
async def test_subprovincial_cdc_sources_registered():
    """测试副省级城市及计划单列市疾控中心爬虫插件注册完整性"""
    SourceRegistry._plugins.clear()
    plugins = SourceRegistry.discover_and_register()
    
    expected_cdc_sources = [
        "shenzhen_cdc",
        "guangzhou_cdc",
        "hangzhou_cdc",
        "nanjing_cdc",
        "wuhan_cdc",
        "chengdu_cdc",
        "qingdao_cdc",
        "xian_cdc",
    ]
    for src_id in expected_cdc_sources:
        assert src_id in plugins, f"Source {src_id} must be in SourceRegistry"
        source_instance = SourceRegistry.get(src_id)
        assert source_instance is not None
        assert "疾病预防控制中心" in source_instance.name

    assert get_source_by_key("shenzhen_cdc") is not None
    assert len(list_all_sources()) >= 30

@pytest.mark.asyncio
async def test_subprovincial_sources_mock_fetch():
    """测试副省级城市疾控中心源 mock fetch_announcements 流程与结构输出"""
    sources = [
        ShenzhenCdcSource(),
        GuangzhouCdcSource(),
        HangzhouCdcSource(),
        NanjingCdcSource(),
        WuhanCdcSource(),
        ChengduCdcSource(),
        QingdaoCdcSource(),
        XianCdcSource()
    ]
    for src in sources:
        assert src.name is not None
        assert src.base_url is not None
        items = await src.fetch_announcements()
        assert isinstance(items, list)
        assert len(items) > 0
        item = items[0]
        assert hasattr(item, "title") and item.title
        assert hasattr(item, "url") and item.url
        assert "疾控" in item.title or "疾病预防控制" in item.title or "卫生" in item.title

def test_fine_grained_disciplines_and_frontier_areas():
    """测试预防医学前沿细分领域与新兴公卫专业的高精度五星级判定"""
    # 放射卫生与辐射防护
    res_rad = MajorMatcher.match("放射卫生与辐射防护专业，主要从事核辐射与放射诊疗防护监测")
    assert res_rad["match_level"] == 4
    assert "放射卫生与辐射防护" in res_rad["sub_disciplines"]
    assert "放射卫生" in res_rad["sub_disciplines"]["放射卫生与辐射防护"]

    # 海关国境卫生检疫
    res_port = MajorMatcher.match("海关口岸卫生检疫与传染病监测控制")
    assert res_port["match_level"] == 4
    assert any("国境卫生检疫" in k or "口岸" in k for k in res_port["sub_disciplines"].keys())

    # 卫生技术评估 / 循证公共卫生
    res_hta = MajorMatcher.match("卫生技术评估与循证公共卫生政策研究岗")
    assert res_hta["match_level"] == 4
    assert any("循证" in k or "卫生技术评估" in k for k in res_hta["sub_disciplines"].keys())

    # 健康大数据
    res_data = MajorMatcher.match("健康医疗大数据与卫生信息学")
    assert res_data["match_level"] == 4
    assert any("信息" in k or "数据" in k or "统计" in k for k in res_data["sub_disciplines"].keys())

def test_enhanced_bianzhi_confidence_and_evidence():
    """测试高精度编制判定引擎（全额、财政补助、差额、备案制与合同制排他）"""
    # 全额拨款
    eval_quan_e = BianzhiEvaluator.evaluate(
        text="经省编办批准，本次招聘人员纳入全额拨款事业单位编制管理，享受财政全额核拨经费保障。"
    )
    assert eval_quan_e["is_bianzhi"] == 1
    assert "全额" in eval_quan_e["bianzhi_type"]
    assert eval_quan_e["confidence"] >= 0.85
    assert len(eval_quan_e["evidence_chain"]) > 0

    # 财政补助事业编制
    eval_sub = BianzhiEvaluator.evaluate(
        text="聘用人员纳入同级财政补助事业单位正式编制，办理事业单位聘用及实名制入编手续。"
    )
    assert eval_sub["is_bianzhi"] == 1
    assert eval_sub["confidence"] >= 0.85

    # 差额/自收自支
    eval_chae = BianzhiEvaluator.evaluate(
        text="本次招聘岗位为差额拨款事业编制，执行事业单位差额补助人事管理规定。"
    )
    assert eval_chae["is_bianzhi"] == 1
    assert "差额" in eval_chae["bianzhi_type"]

    # 劳务派遣与外包
    eval_dispatch = BianzhiEvaluator.evaluate(
        text="录用人员与第三方人力资源公司签订劳动合同，采取劳务派遣形式派驻至单位工作。"
    )
    assert eval_dispatch["is_bianzhi"] == 0
    assert eval_dispatch["confidence"] >= 0.95
    assert "合同制" in eval_dispatch["bianzhi_type"] or "派遣" in eval_dispatch["bianzhi_evidence"]

def test_talent_policy_extended_recognition():
    """测试高层次人才免笔试、急需紧缺专项与安家费提取"""
    text = "面向全国公开引进高层次紧缺公卫博士，免笔试直接考核面试，录用即提供安家补贴50万元、科研启动经费30万元，提供人才公寓及子女入学便利。"
    res = TalentPolicyExtractor.extract_talent_policies(text=text)
    assert res["is_talent_intro"] is True
    assert res["is_no_written_exam"] is True
    assert res["policy_tier"] in ["S", "A", "B", "C"]
    assert res["housing_subsidy_amt"] == 500000.0
    assert res["research_fund_amt"] == 300000.0
    assert "住房保障" in res["special_benefits"] or "人才公寓" in res["benefits_summary"]

def test_pitfall_extractor_expansion():
    """测试避坑指南解析器对服务期、脱密期、违约赔偿金等条款的提取"""
    req_text = "新进人员须签订5年服务期协议，服务期内不得提出辞职或调动。在岗期间涉密人员脱密期为2年。违约须支付赔偿金10万元。"
    pitfalls = PitfallExtractor.extract(text=req_text)
    assert len(pitfalls) > 0
    full_str = str(pitfalls)
    assert "5年" in full_str or "服务期" in full_str or "违约" in full_str
