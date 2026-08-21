import pytest
import asyncio
from app.sources.registry import SourceRegistry
from app.sources.liaoning_wsjkw import LiaoningWsjkwSource
from app.sources.jilin_wsjkw import JilinWsjkwSource
from app.sources.heilongjiang_rsks import HeilongjiangRsksSource
from app.sources.neimenggu_rsks import NeimengguRsksSource
from app.sources.gansu_rsks import GansuRsksSource
from app.sources.xinjiang_rsks import XinjiangRsksSource
from app.sources.qinghai_wsjkw import QinghaiWsjkwSource
from app.sources.ningxia_rsks import NingxiaRsksSource
from app.rules.major_matcher import MajorMatcher
from app.rules.bianzhi_evaluator import BianzhiEvaluator
from app.extractors.talent_policy import TalentPolicyExtractor

@pytest.mark.asyncio
async def test_all_31_provinces_pool_and_registry():
    """测试全国 31 省市 official 招考插件和省池覆盖率"""
    plugins = SourceRegistry.discover_and_register()
    assert len(plugins) >= 40
    
    # 验证新上线的 8 个省份插件是否已正确挂载
    new_source_ids = [
        "liaoning_wsjkw", "jilin_wsjkw", "heilongjiang_rsks",
        "neimenggu_rsks", "gansu_rsks", "xinjiang_rsks",
        "qinghai_wsjkw", "ningxia_rsks"
    ]
    for sid in new_source_ids:
        assert sid in plugins
        p = SourceRegistry.get(sid)
        assert p is not None
        assert p.province != ""

@pytest.mark.asyncio
async def test_new_provincial_crawler_plugins_execution():
    """测试新增加的西北与东北等各省爬虫抓取逻辑与兜底数据解析"""
    test_plugins = [
        LiaoningWsjkwSource(),
        JilinWsjkwSource(),
        HeilongjiangRsksSource(),
        NeimengguRsksSource(),
        GansuRsksSource(),
        XinjiangRsksSource(),
        QinghaiWsjkwSource(),
        NingxiaRsksSource()
    ]
    
    for plugin in test_plugins:
        items = await plugin.fetch_announcements(max_pages=1)
        assert len(items) >= 1
        item = items[0]
        assert item.title != ""
        assert item.source_id == plugin.source_id
        assert item.province == plugin.province
        
        detail = await plugin.fetch_detail(item.url)
        assert detail is not None
        assert detail.title != ""
        assert len(detail.content_text) > 20
        assert len(detail.attachments) >= 1

def test_major_sub_disciplines_and_five_star_matrix():
    """测试预防医学核心、细分二级学科、国标代码与学历识别"""
    # 5星：直接命中核心预防医学或国标代码
    res_yufang = MajorMatcher.match("预防医学", unit_type="疾控中心", job_name="传染病防治岗")
    assert res_yufang["match_level"] == 5
    assert "预防医学" in res_yufang["matched_codes"]
    
    # 5星：卫生检验与检疫
    res_weijian = MajorMatcher.match("卫生检验与检疫 (100402TK)")
    assert res_weijian["match_level"] == 5
    assert "卫生检验与检疫" in res_weijian["sub_disciplines"]

    # 4星：二级学科（流行病与卫生统计学、劳动卫生与环境卫生学、营养与食品卫生学、卫生毒理学）
    res_liuxing = MajorMatcher.match("流行病与卫生统计学", unit_type="疾控中心", job_name="现场流行病学专家")
    assert res_liuxing["match_level"] == 4
    assert "流行病与卫生统计学" in res_liuxing["sub_disciplines"]

    res_tox = MajorMatcher.match("要求取得卫生毒理学或食品毒理博士学位")
    assert res_tox["match_level"] == 4
    assert "卫生毒理学" in res_tox["sub_disciplines"]
    assert res_tox["degree_req"]["min_degree"] == "博士"

    # 3星：公卫大类/医学检验
    res_class = MajorMatcher.match("公共卫生类、医学检验技术", unit_type="疾控中心")
    assert res_class["match_level"] == 3

    # 1星：明确非公卫
    res_exclude = MajorMatcher.match("汉语言文学、会计学、软件工程")
    assert res_exclude["match_level"] == 1

def test_bianzhi_confidence_and_evidence_chain():
    """测试编制研判引擎对于全额事业编、报备员额、合同制与劳务派遣的证据链与置信度"""
    # 全额实名制事业编
    r_shiye = BianzhiEvaluator.evaluate(
        job_name="公卫医师",
        unit_name="辽宁省疾病预防控制中心",
        announcement_title="辽宁省疾病预防控制中心2026年公开招聘工作人员公告",
        announcement_text="本次招聘纳入事业单位财政全额拨款实名制事业编制管理。"
    )
    assert r_shiye["is_bianzhi"] == 1
    assert r_shiye["bianzhi_type"] == "全额事业编"
    assert r_shiye["confidence"] >= 0.85
    assert "实名制编制" in r_shiye["evidence_chain"] or "全额拨款事业单位" in r_shiye["evidence_chain"]

    # 报备员额 / 备案制
    r_beian = BianzhiEvaluator.evaluate(
        job_name="临床营养医师",
        unit_name="某省人民医院",
        unit_type="综合医院/专科医院",
        announcement_title="2026年工作人员招聘公告",
        announcement_text="录用人员实行公立医院人员总量控制与报备员额制管理。"
    )
    assert r_beian["is_bianzhi"] == 2
    assert r_beian["bianzhi_type"] == "报备员额"
    assert r_beian["confidence"] >= 0.7

    # 劳务派遣
    r_dispatch = BianzhiEvaluator.evaluate(
        job_name="采样辅助岗",
        unit_name="某区疾控中心",
        announcement_title="2026年劳务派遣人员招聘启事",
        announcement_text="本岗位采用第三方劳务派遣形式用工，由人力资源公司签订劳动合同，不占事业编制。"
    )
    assert r_dispatch["is_bianzhi"] == 0
    assert r_dispatch["bianzhi_type"] == "合同制"
    assert r_dispatch["confidence"] >= 0.95

def test_talent_policy_advanced_extraction():
    """测试高层次人才引进、免笔试绿色通道、安家补贴与科研启动金提取"""
    sample_text = """
    【人才引进绿色通道】
    新疆疾控中心面向全球引进流行病与卫生统计学高层次紧缺人才。
    一、待遇保障：
    1. 简化考试程序，免笔试直接面谈考核入编。
    2. 提供一次性安家费最高达30万元。
    3. 配套科研启动经费20万元。
    4. 提供免租人才公寓，协助解决子女优质入学及落户。
    """
    policy = TalentPolicyExtractor.extract_talent_policies(sample_text)
    assert policy["is_talent_intro"] is True
    assert policy["is_no_written_exam"] is True
    assert "30万" in policy["settlement_allowance"] or "30万元" in policy["settlement_allowance"]
    assert "20万" in policy["research_fund"] or "20万元" in policy["research_fund"]
    assert policy["has_housing_or_subsidy"] is True
    assert policy["policy_tier"] == "S"
