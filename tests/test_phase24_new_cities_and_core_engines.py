import pytest
from app.sources.registry import SourceRegistry
from app.rules.major_matcher import MajorMatcher
from app.rules.bianzhi_evaluator import BianzhiEvaluator

# 直接导入新增数据源插件以验证可导入且注册正常
from app.sources.nanning_cdc import NanningCdcSource
from app.sources.kunming_cdc import KunmingCdcSource
from app.sources.taiyuan_cdc import TaiyuanCdcSource
from app.sources.zhengzhou_cdc import ZhengzhouCdcSource
from app.sources.shijiazhuang_cdc import ShijiazhuangCdcSource


def test_phase24_new_city_cdc_sources_registered():
    """验证本轮新增的 5 个城市疾控数据源正确注册到 SourceRegistry"""
    plugins_dict = SourceRegistry.discover_and_register()

    expected = [
        "nanning_cdc",
        "kunming_cdc",
        "taiyuan_cdc",
        "zhengzhou_cdc",
        "shijiazhuang_cdc",
    ]
    for s in expected:
        assert s in plugins_dict, f"Plugin {s} should be registered in SourceRegistry"


def test_phase24_new_sources_instance_attributes():
    """验证新增疾控数据源实例属性（province, city, source_id）正确"""
    checks = [
        (NanningCdcSource, "nanning_cdc", "广西壮族自治区", "南宁市"),
        (KunmingCdcSource, "kunming_cdc", "云南省", "昆明市"),
        (TaiyuanCdcSource, "taiyuan_cdc", "山西省", "太原市"),
        (ZhengzhouCdcSource, "zhengzhou_cdc", "河南省", "郑州市"),
        (ShijiazhuangCdcSource, "shijiazhuang_cdc", "河北省", "石家庄市"),
    ]
    for cls, sid, province, city in checks:
        inst = cls()
        assert inst.source_id == sid
        assert inst.province == province
        assert inst.city == city


@pytest.mark.asyncio
async def test_phase24_new_sources_fetch_mock_announcements():
    """验证新增疾控爬虫数据源 fetch_announcements 返回合法结构（含降级回退数据）"""
    plugins_dict = SourceRegistry.discover_and_register()
    new_sources = [
        "nanning_cdc", "kunming_cdc", "taiyuan_cdc",
        "zhengzhou_cdc", "shijiazhuang_cdc",
    ]

    for s_id in new_sources:
        inst = plugins_dict.get(s_id)
        assert inst is not None, f"{s_id} not found in registry"
        items = await inst.fetch_announcements()
        assert isinstance(items, list), f"{s_id} should return a list"
        assert len(items) >= 1, f"{s_id} should return at least 1 fallback item"
        first = items[0]
        assert hasattr(first, "title")
        assert hasattr(first, "url")
        actual_sid = getattr(first, "source_id", None) or getattr(first, "source", None)
        assert actual_sid == s_id, f"{s_id}: source_id mismatch, got {actual_sid!r}"
        assert first.url.startswith("http")


def test_phase24_major_matcher_new_core_patterns():
    """测试预防医学细分方向新增 5 星匹配：规培、免疫规划、结核/艾滋病、地方病、危害因素监测等"""
    cases = [
        ("公共卫生医师规范化培训", 5),
        ("公卫医师规培", 5),
        ("免疫规划与疫苗管理", 5),
        ("结核病防治", 5),
        ("艾滋病防治", 5),
        ("地方病防治", 5),
        ("慢性病综合防控", 5),
        ("健康危害因素监测", 5),
        ("职业健康监护", 5),
        ("健康中国行动", 5),
    ]
    for major_raw, expected_level in cases:
        res = MajorMatcher.match(major_raw=major_raw, job_name="疾控业务岗")
        assert res["match_level"] == expected_level, \
            f"{major_raw} expected level {expected_level}, got {res['match_level']}"


def test_phase24_major_matcher_sub_discipline_expansion():
    """验证新增细分专业子学科正确被 find_sub_disciplines 识别"""
    text = "面向免疫规划与疫苗管理、结核病防治、健康危害因素监测的岗位"
    sub = MajorMatcher.find_sub_disciplines(text)
    assert "免疫规划与疫苗管理" in sub
    assert "重大传染病与结核艾滋病防治" in sub
    assert "健康危害因素监测与化学毒物检测" in sub


def test_phase24_bianzhi_oriented_binding():
    """测试编制判定引擎对订单定向/公费公卫医师入编项目的高置信度识别"""
    res = BianzhiEvaluator.evaluate(
        job_name="农村订单定向公卫医师岗",
        unit_name="石家庄市某乡镇卫生院",
        announcement_title="河北省农村订单定向免费公卫医师培养安置公告",
        announcement_text=(
            "本项目为订单定向培养公费公卫医师，毕业考核合格后按专项编制保障入编安置，"
            "纳入全额事业编制实名制管理，服务基层卫生健康事业。"
        ),
    )
    assert res["is_bianzhi"] == 1
    assert res["confidence"] >= 0.8
    assert res["bianzhi_type"] in ("全额事业编", "全额拨款事业编", "事业编制")


def test_phase24_bianzhi_special_quota_binding():
    """测试周转/专项编制保障的强确编识别"""
    res = BianzhiEvaluator.evaluate(
        job_name="疾控专项技术岗",
        unit_name="郑州疾病预防控制中心",
        announcement_text=(
            "该岗位由市编制部门核定的专项编制保障，实行周转编制管理，"
            "面向预防医学专业应届毕业生公开招聘。"
        ),
    )
    assert res["is_bianzhi"] == 1
    assert res["confidence"] >= 0.7
