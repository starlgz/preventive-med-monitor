import pytest
from app.sources.registry import SourceRegistry
from app.sources.changzhou_cdc import ChangzhouCdcSource
from app.sources.shaoxing_cdc import ShaoxingCdcSource
from app.sources.jiaxing_cdc import JiaxingCdcSource
from app.sources.zhuhai_cdc import ZhuhaiCdcSource
from app.sources.zhongshan_cdc import ZhongshanCdcSource
from app.rules.major_matcher import MajorMatcher
from app.rules.bianzhi_evaluator import BianzhiEvaluator
from app.extractors.talent_policy import TalentPolicyExtractor

@pytest.mark.asyncio
async def test_phase26_crawlers_registered():
    plugins = SourceRegistry.discover_and_register()
    
    assert "changzhou_cdc" in plugins
    assert "shaoxing_cdc" in plugins
    assert "jiaxing_cdc" in plugins
    assert "zhuhai_cdc" in plugins
    assert "zhongshan_cdc" in plugins

    cz = plugins["changzhou_cdc"]
    assert cz.city == "常州市"
    assert cz.province == "江苏省"

    sx = plugins["shaoxing_cdc"]
    assert sx.city == "绍兴市"
    assert sx.province == "浙江省"

    jx = plugins["jiaxing_cdc"]
    assert jx.city == "嘉兴市"
    assert jx.province == "浙江省"

    zh = plugins["zhuhai_cdc"]
    assert zh.city == "珠海市"
    assert zh.province == "广东省"

    zs = plugins["zhongshan_cdc"]
    assert zs.city == "中山市"
    assert zs.province == "广东省"

@pytest.mark.asyncio
async def test_phase26_crawlers_fetch():
    cz = ChangzhouCdcSource()
    items = await cz.fetch_announcements(max_pages=1)
    assert len(items) >= 1
    detail = await cz.fetch_detail(items[0].url)
    assert detail is not None
    assert "常州" in detail.title or "常州市" in detail.province or detail.city == "常州市"

    sx = ShaoxingCdcSource()
    items_sx = await sx.fetch_announcements(max_pages=1)
    assert len(items_sx) >= 1
    detail_sx = await sx.fetch_detail(items_sx[0].url)
    assert detail_sx is not None
    assert detail_sx.city == "绍兴市"

    jx = JiaxingCdcSource()
    items_jx = await jx.fetch_announcements(max_pages=1)
    assert len(items_jx) >= 1
    detail_jx = await jx.fetch_detail(items_jx[0].url)
    assert detail_jx is not None
    assert detail_jx.city == "嘉兴市"

    zh = ZhuhaiCdcSource()
    items_zh = await zh.fetch_announcements(max_pages=1)
    assert len(items_zh) >= 1
    detail_zh = await zh.fetch_detail(items_zh[0].url)
    assert detail_zh is not None
    assert detail_zh.city == "珠海市"

    zs = ZhongshanCdcSource()
    items_zs = await zs.fetch_announcements(max_pages=1)
    assert len(items_zs) >= 1
    detail_zs = await zs.fetch_detail(items_zs[0].url)
    assert detail_zs is not None
    assert detail_zs.city == "中山市"

def test_phase26_talent_policy_regional_plans():
    # 测试新增的长三角与珠三角代表性区域人才引进政策识别
    text1 = "常州市疾病预防控制中心根据【龙城英才计划】引进高层次预防医学紧缺人才，提供安家费50万元，直接面试考核。"
    res1 = TalentPolicyExtractor.extract_talent_policies(text1)
    assert res1["is_talent_intro"] is True
    assert res1["is_no_exam"] is True
    assert res1["tier"] in ["S", "A"]
    assert res1["settling_allowance"] == "50万元" or res1["settlement_allowance"] is not None

    text2 = "绍兴市疾控中心诚聘名士之乡英才，免笔试考核录用，享受一次性安家费30万元及人才周转公寓。"
    res2 = TalentPolicyExtractor.extract_talent_policies(text2)
    assert res2["is_talent_intro"] is True
    assert res2["is_no_exam"] is True
    assert res2["tier"] == "S"

    text3 = "嘉兴市落实星耀南湖拔尖公卫医师引进，提供科研启动经费20万元及免租人才公寓，直接考察入编。"
    res3 = TalentPolicyExtractor.extract_talent_policies(text3)
    assert res3["is_talent_intro"] is True
    assert res3["is_no_exam"] is True
    assert "科研启动费: 科研启动经费20万元" in res3["benefit_details"] or "科研启动经费20万元" in str(res3["research_fund"])

    text4 = "中山市实施中山特聘人才计划，招录公卫高层次专家，发放住房补贴最高15万元，直接考核录用。"
    res4 = TalentPolicyExtractor.extract_talent_policies(text4)
    assert res4["is_talent_intro"] is True
    assert res4["is_no_exam"] is True
    assert res4["tier"] in ["S", "A"]

def test_phase26_major_and_bianzhi_evaluation():
    # 编制判定测试
    res_bz = BianzhiEvaluator.evaluate(
        job_name="公卫医师",
        unit_name="常州市疾病预防控制中心",
        announcement_title="常州市疾控中心公开招聘工作人员公告（全额拨款事业单位正式在编人员）"
    )
    assert res_bz["is_bianzhi"] == 1
    assert res_bz["bianzhi_type"] == "全额事业编"
    assert res_bz["confidence"] >= 0.85

    res_bz_beian = BianzhiEvaluator.evaluate(
        job_name="院感管理岗",
        unit_name="某三甲综合医院",
        announcement_title="2026年工作人员招录公告",
        announcement_text="本岗位纳入公立三甲医院报备员额制管理，同工同酬。"
    )
    assert res_bz_beian["is_bianzhi"] == 2
    assert res_bz_beian["bianzhi_type"] == "报备员额"

    # 专业匹配测试
    match_res = MajorMatcher.match("预防医学、流行病与卫生统计学、卫生检验与检疫")
    assert match_res["match_level"] == 5
    assert "预防医学" in match_res["matched_keywords"]
