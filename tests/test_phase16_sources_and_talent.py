import pytest
from app.sources.hebei_wsjkw import HebeiWsjkwSource
from app.sources.shanghai_rsj import ShanghaiRsjSource
from app.sources.shanxi_wsjkw import ShanxiWsjkwSource
from app.sources.fujian_wsjkw import FujianWsjkwSource
from app.sources.shaanxi_rsks import ShaanxiRsksSource
from app.sources.tianjin_rsks import TianjinRsksSource
from app.sources.chongqing_rsks import ChongqingRsksSource
from app.sources.hainan_wsjkw import HainanWsjkwSource
from app.sources.guangxi_rsks import GuangxiRsksSource
from app.sources.registry import SourceRegistry
from app.extractors.talent_policy import TalentPolicyExtractor
from app.rules.major_matcher import MajorMatcher

@pytest.mark.asyncio
async def test_new_provincial_sources_plugins():
    """测试第16期新上线的专属省份招考爬虫插件"""
    plugins = [
        (HebeiWsjkwSource(), "hebei_wsjkw", "河北"),
        (ShanghaiRsjSource(), "shanghai_rsj", "上海"),
        (ShanxiWsjkwSource(), "shanxi_wsjkw", "山西"),
        (FujianWsjkwSource(), "fujian_wsjkw", "福建"),
        (ShaanxiRsksSource(), "shaanxi_rsks", "陕西"),
        (TianjinRsksSource(), "tianjin_rsks", "天津"),
        (ChongqingRsksSource(), "chongqing_rsks", "重庆"),
        (HainanWsjkwSource(), "hainan_wsjkw", "海南"),
        (GuangxiRsksSource(), "guangxi_rsks", "广西"),
    ]
    for p, expected_id, expected_prov in plugins:
        assert p.source_id == expected_id
        assert p.province == expected_prov
        announcements = await p.fetch_announcements(max_pages=1)
        assert isinstance(announcements, list)
        assert len(announcements) > 0
        assert any(ann.province == expected_prov for ann in announcements)
        # 验证详情抓取
        detail = await p.fetch_detail(announcements[0].url)
        assert detail is not None
        assert detail.province == expected_prov

def test_source_registry_auto_discovery():
    """验证插件注册中心自动发现与注册"""
    registered = SourceRegistry.discover_and_register()
    assert "hebei_wsjkw" in registered
    assert "shanghai_rsj" in registered
    assert "shanxi_wsjkw" in registered
    assert "fujian_wsjkw" in registered
    assert "shaanxi_rsks" in registered
    assert "tianjin_rsks" in registered
    assert "chongqing_rsks" in registered
    assert "hainan_wsjkw" in registered
    assert "guangxi_rsks" in registered

def test_enhanced_subdisciplines_matching():
    """测试预防医学二级学科与交叉学科的精准判定"""
    # 卫生检验与检疫
    m_weijian = MajorMatcher.match("卫生检验与检疫技术、理化检验")
    assert m_weijian["match_level"] == 5
    assert "卫生检验与检疫" in m_weijian["sub_disciplines"]

    # 卫生监督
    m_jiandu = MajorMatcher.match("卫生监督与行政执法")
    assert m_jiandu["match_level"] == 5
    assert "卫生监督" in m_jiandu["sub_disciplines"]

    # 生物统计学
    m_biostat = MajorMatcher.match("生物统计学与生物信息学")
    assert m_biostat["match_level"] == 4
    assert "生物统计学" in m_biostat["sub_disciplines"]

    # 全球卫生 / 全球健康
    m_global = MajorMatcher.match("全球健康学 (Global Health)")
    assert m_global["match_level"] == 4
    assert "全球健康学" in m_global["sub_disciplines"]

    # 医院感染控制
    m_yuangan = MajorMatcher.match("医院感染管理与控制、院感")
    assert m_yuangan["match_level"] == 4
    assert "医院感染控制" in m_yuangan["sub_disciplines"]

def test_talent_policy_structured_tags():
    """测试人才政策多维度标签与提取结果"""
    sample_text = """
    2026年某省疾病预防控制中心公开考核招聘急需紧缺高层次人才公告。
    本次招聘采取直接考核面试，免笔试。
    对引进的博士研究生、公共卫生学科带头人，给予一次性安家费80万元，
    提供科研启动经费100万元，配租人才周转公寓，解决配偶工作及子女优质入学。
    """
    res = TalentPolicyExtractor.extract_talent_policies(
        text=sample_text,
        job_title="公共卫生学术带头人",
        requirements="预防医学博士研究生"
    )
    assert res["is_talent_intro"] is True
    assert res["is_no_written_exam"] is True
    assert res["policy_tier"] == "S"
    assert "免笔试" in res["tags"]
    assert "安家补贴" in res["tags"]
    assert "科研经费" in res["tags"]
    assert "住房保障" in res["tags"]
    assert "子女入学" in res["tags"]
    assert res["settling_allowance"] == "80万元"
    assert res["research_fund"] == "100万元"
