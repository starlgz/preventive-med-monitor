import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.sources.registry import SourceRegistry
from app.sources.shaanxi_cdc import ShaanxiCdcSource
from app.sources.hebei_cdc import HebeiCdcSource
from app.sources.shanxi_cdc import ShanxiCdcSource
from app.sources.jiangxi_cdc import JiangxiCdcSource
from app.rules.major_matcher import MajorMatcher
from app.extractors.talent_policy import TalentPolicyExtractor
from app.rules.bianzhi_evaluator import BianzhiEvaluator


class TestPhase19NewProvincesAndAdvancedEngines:
    """第十九阶段：扩展北方/中部/西北省份CDC插件、多级细分专业子学科图谱、顶格引才与编制研判验证"""

    def test_sources_registry_new_cdc_plugins(self):
        """验证新加入的陕西、河北、山西、江西疾控爬虫注册"""
        plugins = SourceRegistry.discover_and_register()
        
        expected_plugins = [
            "shaanxi_cdc",
            "hebei_cdc",
            "shanxi_cdc",
            "jiangxi_cdc",
            "guangdong_cdc",
            "sichuan_cdc",
            "shandong_cdc",
            "jiangsu_cdc",
            "zhejiang_cdc",
            "hubei_cdc",
            "beijing_cdc",
            "shanghai_cdc"
        ]
        for p in expected_plugins:
            assert p in plugins, f"插件 {p} 应该被自动注册"
            inst = plugins[p]
            assert inst.province != ""
            assert any(k in inst.name for k in ["CDC", "疾控", "疾病预防控制"])

    @pytest.mark.asyncio
    async def test_new_cdc_scrapers_mock_or_structure(self):
        """验证新增 CDC 爬虫实例的基础属性与解析结构"""
        sources = [
            ShaanxiCdcSource(),
            HebeiCdcSource(),
            ShanxiCdcSource(),
            JiangxiCdcSource()
        ]
        for src in sources:
            assert src.source_id != ""
            assert src.province in ["陕西", "河北", "山西", "江西", "陕西省", "河北省", "山西省", "江西省"]
            assert src.base_url.startswith("http")

    def test_sub_discipline_keyword_extraction(self):
        """测试二级学科细分专业词谱提取（毒理学、营养与食品、儿少妇幼、劳卫环卫、流病统计等）"""
        # 测试 1: 卫生毒理学与分子毒理
        text1 = "招聘公共卫生医师1名，要求研究生学历，分子毒理与计算毒理方向优先，代码100405。"
        res1 = MajorMatcher.match(major_raw=text1, job_name="公卫医师")
        assert res1["match_level"] in [4, 5]
        assert "卫生毒理学" in res1["sub_disciplines"]
        assert any("毒理" in kw for kw in res1["sub_disciplines"]["卫生毒理学"])

        # 测试 2: 营养与食品卫生学
        text2 = "食品安全监测岗：营养与食品卫生学、食品毒理与安全、临床营养学专业，硕士及以上。"
        res2 = MajorMatcher.match(major_raw=text2, job_name="食品安全监测岗")
        assert res2["match_level"] == 4
        assert "营养与食品卫生学" in res2["sub_disciplines"]
        assert res2["degree_req"]["min_degree"] == "硕士"

        # 测试 3: 儿少卫生与妇幼保健学
        text3 = "妇幼保健中心：儿少卫生与妇幼保健学、优生优育、儿童保健专业，本科及以上。"
        res3 = MajorMatcher.match(major_raw=text3, job_name="妇女儿童保健科医师")
        assert res3["match_level"] == 5
        assert "儿少卫生与妇幼保健学" in res3["sub_disciplines"]

        # 测试 4: 劳动卫生与环境卫生学、放射卫生
        text4 = "职业病防治院：劳动卫生与环境卫生学、职业卫生评价、放射卫生方向。"
        res4 = MajorMatcher.match(major_raw=text4, job_name="理化评价科")
        assert res4["match_level"] == 4
        assert "劳动卫生与环境卫生学" in res4["sub_disciplines"]

        # 测试 5: 现场流行病与传染病动力学建模
        text5 = "疾控应急中心：流行病与卫生统计学、现场流行病学、传染病动力学建模方向，博士研究生。"
        res5 = MajorMatcher.match(major_raw=text5, job_name="应急流行病学专家")
        assert res5["match_level"] == 4
        assert "流行病与卫生统计学" in res5["sub_disciplines"]
        assert res5["degree_req"]["min_degree"] == "博士"

    def test_talent_policy_top_tier_and_benefits(self):
        """测试高层次引才政策顶格评级与安家补贴解析"""
        text = """
        【高层次紧缺人才引进公告】
        1. 针对公共卫生与预防医学博士研究生开通人才直通车，免笔试直接面试考核入围。
        2. 给予一次性安家费50万元，提供科研启动经费30万元。
        3. 落实全额事业编制，提供免租人才公寓，协助解决配偶工作及子女优质入学。
        """
        policy = TalentPolicyExtractor.extract(text=text, job_name="公卫学科带头人")
        assert policy["is_talent_intro"] is True
        assert policy["is_no_written_exam"] is True
        assert policy["tier"] in ["S", "A"]
        assert policy["settlement_allowance"] is not None
        assert "50" in policy["settlement_allowance"]
        assert policy["research_fund"] is not None
        assert "30" in policy["research_fund"]
        assert "住房保障" in policy["special_benefits"]
        assert "子女入学" in policy["special_benefits"]
        assert "解决编制" in policy["special_benefits"]

    def test_bianzhi_evaluator_cdc_and_hospital_nuance(self):
        """测试编制研判引擎对疾控全额编与公立医院备案制的区分"""
        # CDC 统一招考全额编
        cdc_text = "2026年某省疾病预防控制中心统一公开招聘工作人员公告，公益一类事业单位，纳入实名制事业编制管理。"
        res_cdc = BianzhiEvaluator.evaluate(
            job_name="传染病防制科公卫医师",
            unit_name="省疾病预防控制中心",
            unit_type="疾控中心",
            announcement_title="统一公开招聘工作人员公告",
            announcement_text=cdc_text
        )
        assert res_cdc["is_bianzhi"] == 1
        assert res_cdc["bianzhi_type"] == "全额事业编"
        assert res_cdc["confidence"] >= 0.85

        # 医院人员总量备案制
        hosp_text = "某三甲公立医院招聘通知，录用人员实行公立医院人员总量控制与备案制管理。"
        res_hosp = BianzhiEvaluator.evaluate(
            job_name="院感防制专员",
            unit_name="市第一人民医院",
            unit_type="综合医院/专科医院",
            announcement_title="公开招聘人员简章",
            announcement_text=hosp_text
        )
        assert res_hosp["is_bianzhi"] == 2
        assert res_hosp["bianzhi_type"] == "报备员额"
        assert res_hosp["confidence"] >= 0.7

    @pytest.mark.asyncio
    async def test_dashboard_api_stats_and_charts(self):
        """测试 Web Dashboard API 统计与图表接口"""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp_stats = await client.get("/api/v1/dashboard/stats")
            assert resp_stats.status_code == 200
            data_stats = resp_stats.json()
            assert "total_jobs" in data_stats
            assert "five_star_jobs" in data_stats
            assert "total_sources" in data_stats

            resp_charts = await client.get("/api/v1/dashboard/charts")
            assert resp_charts.status_code == 200
            data_charts = resp_charts.json()
            assert "province_distribution" in data_charts
            assert "star_distribution" in data_charts
            assert "bianzhi_distribution" in data_charts
