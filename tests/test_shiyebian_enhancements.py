import pytest
from app.sources.shiyebian import ShiyebianSource, SHIYEBIAN_PROVINCES, ShiyebianProvinceSource

def test_shiyebian_provinces_definition():
    assert len(SHIYEBIAN_PROVINCES) == 32
    assert ("shandong", "山东") in SHIYEBIAN_PROVINCES
    assert ("jiangsu", "江苏") in SHIYEBIAN_PROVINCES
    assert ("sichuan", "四川") in SHIYEBIAN_PROVINCES

@pytest.mark.asyncio
async def test_shiyebian_detail_parsing_mock(monkeypatch):
    source = ShiyebianSource()
    sample_html = """
    <html>
    <head><title>2026年青岛市卫生健康委员会直属事业单位招聘高层次人才公告</title></head>
    <body>
        <div class="ws-position">首页 &gt; 山东事业单位招聘 &gt; 青岛事业单位招聘</div>
        <div class="ws-info">2026-08-21 15:30:00 医疗卫生</div>
        <div class="ws-content">
            <p>为进一步加强卫生人才队伍建设，现招聘相关人员。</p>
            <p><a href="/e/down/download.php?url=/forum/2026/08/21/test12345.xlsx">岗位计划表.xlsx (20KB)</a></p>
            <p><a href="/app/download.html">下载事业编APP刷题</a></p>
        </div>
    </body>
    </html>
    """

    class MockResponse:
        status_code = 200
        text = sample_html

    class MockClient:
        async def __aenter__(self):
            return self
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass
        async def get(self, url):
            return MockResponse()

    async def mock_get_http_client(timeout=5.0):
        return MockClient()

    monkeypatch.setattr(source, "get_http_client", mock_get_http_client)

    detail = await source.fetch_detail("https://www.shiyebian.com/xinxi/12345.html")
    assert detail is not None
    assert detail.province == "山东"
    assert detail.city == "青岛"
    assert detail.publish_date == "2026-08-21"
    assert len(detail.attachments) == 1
    assert detail.attachments[0].file_name == "岗位计划表.xlsx (20KB)"
    assert detail.attachments[0].file_type == "xlsx"
    assert "https://www.shiyebian.com/e/down/download.php" in detail.attachments[0].download_url

@pytest.mark.asyncio
async def test_shiyebian_province_source_mock(monkeypatch):
    prov_source = ShiyebianProvinceSource("jiangsu", "江苏")
    list_html = """
    <html>
    <body>
        <div class="ws-list">
            <a href="/xinxi/99881.html">2026年南京市疾控中心招聘公告</a>
            <a href="/xinxi/99882.html">2026年苏州市疾控中心招聘公告</a>
            <a href="/other/about.html">关于我们</a>
        </div>
    </body>
    </html>
    """
    class MockResponse:
        status_code = 200
        text = list_html

    class MockClient:
        async def __aenter__(self):
            return self
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass
        async def get(self, url):
            return MockResponse()

    async def mock_get_http_client(timeout=5.0):
        return MockClient()

    monkeypatch.setattr(prov_source, "get_http_client", mock_get_http_client)
    items = await prov_source.fetch_announcements()
    assert len(items) == 2
    assert items[0].province == "江苏"
    assert items[0].url == "https://www.shiyebian.com/xinxi/99881.html"

def test_major_matcher_vocational_and_pitfall_extraction():
    from app.rules.major_matcher import MajorMatcher
    from app.extractors.pitfall_extractor import PitfallExtractor

    # 1. 验证专科预防医学代码 (520601) 穿透与五星量化
    res_voc = MajorMatcher.calculate_match_score(
        major_raw="要求专业为520601预防医学或公共卫生管理",
        unit_type="疾控中心",
        job_name="免规科流调员",
        unit_name="某市疾病预防控制中心"
    )
    assert res_voc["match_level"] == 5
    assert "520601" in res_voc["matched_codes"]
    assert "流行病与卫生统计学" in res_voc["sub_disciplines"]
    assert "疾病控制与应急处置" in res_voc["sub_disciplines"]

    # 2. 验证避坑引擎识别应届生限制与基层经验限制
    res_pitfall_fresh = PitfallExtractor.analyze(
        job_desc="公卫医师岗，面向2026年应届毕业生招聘，最低服务期5年",
        announcement_text="本市户籍优先"
    )
    tags = [p["tag"] for p in res_pitfall_fresh["pitfall_items"]]
    assert "限高校应届毕业生" in tags
    assert "最低服务期5年" in tags
    assert "限本地户籍/生源" in tags


