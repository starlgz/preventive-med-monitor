import pytest
import pytest_asyncio
import json
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from app.engine.generic_crawler import GenericCrawlerEngine
from app.models.entities import CustomSource
from app.core.database import AsyncSessionLocal
from sqlalchemy import select, delete

@pytest.mark.asyncio
async def test_generic_crawler_html_parsing():
    """测试 HTML 列表解析引擎与 CSS 选择器提取"""
    sample_html = """
    <html>
      <body>
        <div class="news-wrap">
          <ul class="list">
            <li class="item">
              <a href="/jobs/2026/08/01.html">2026年某某市疾病预防控制中心公开招聘工作人员公告</a>
              <span class="pub-time">2026-08-20</span>
            </li>
            <li class="item">
              <a href="http://other.gov.cn/notice/02.html">某区卫生健康局招聘公共卫生专业技术人员公告</a>
              <span class="pub-time">2026-08-19</span>
            </li>
          </ul>
        </div>
      </body>
    </html>
    """
    engine = GenericCrawlerEngine()
    
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = sample_html.encode("utf-8")
    mock_resp.text = sample_html
    mock_resp.url = httpx.URL("http://example.cdc.gov.cn/jobs")
    mock_resp.headers = {"content-type": "text/html; charset=utf-8"}
    
    rule = {
        "protocol": "html_list",
        "request": {
            "url": "http://example.cdc.gov.cn/jobs",
            "method": "GET"
        },
        "list_extractor": {
            "item_selector": "ul.list > li.item",
            "title_selector": "a::text",
            "url_selector": "a::attr(href)",
            "date_selector": "span.pub-time::text"
        }
    }
    
    with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = mock_resp
        res = await engine.execute_crawl(rule, max_items=5)
        
        assert res["status_code"] == 200
        assert res["total_extracted"] == 2
        items = res["items"]
        assert len(items) == 2
        assert "某某市疾病预防控制中心" in items[0]["title"]
        assert items[0]["url"] == "http://example.cdc.gov.cn/jobs/2026/08/01.html"
        assert items[0]["date"] == "2026-08-20"
        assert items[1]["url"] == "http://other.gov.cn/notice/02.html"

@pytest.mark.asyncio
async def test_generic_crawler_json_api():
    """测试 JSON API 接口协议解析"""
    sample_json = {
        "code": 0,
        "data": {
            "records": [
                {
                    "noticeTitle": "2026年公卫医师招聘公告",
                    "articleId": "1001",
                    "createTime": "2026-08-21 09:00:00"
                }
            ]
        }
    }
    engine = GenericCrawlerEngine()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = json.dumps(sample_json).encode("utf-8")
    mock_resp.text = json.dumps(sample_json)
    mock_resp.url = httpx.URL("http://api.example.gov.cn/notices")
    mock_resp.json = MagicMock(return_value=sample_json)
    mock_resp.headers = {"content-type": "application/json"}
    
    rule = {
        "protocol": "json_api",
        "request": {
            "url": "http://api.example.gov.cn/notices",
            "method": "POST"
        },
        "list_extractor": {
            "item_selector": "data.records",
            "title_selector": "noticeTitle",
            "url_selector": "articleId",
            "date_selector": "createTime"
        }
    }
    
    with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = mock_resp
        res = await engine.execute_crawl(rule, max_items=5)
        
        assert res["status_code"] == 200
        assert res["total_extracted"] == 1
        assert "公卫医师招聘公告" in res["items"][0]["title"]
        assert res["items"][0]["url"] == "1001"
        assert "2026-08-21" in res["items"][0]["date"]

@pytest.mark.asyncio
async def test_generic_crawler_rss():
    """测试 RSS/XML 订阅源解析"""
    sample_rss = """<?xml version="1.0" encoding="utf-8"?>
    <rss version="2.0">
      <channel>
        <title>卫生招聘RSS</title>
        <item>
          <title>2026年疾控招聘公告</title>
          <link>http://cdc.org/1.html</link>
          <pubDate>2026-08-21</pubDate>
        </item>
      </channel>
    </rss>
    """
    engine = GenericCrawlerEngine()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = sample_rss.encode("utf-8")
    mock_resp.text = sample_rss
    mock_resp.url = httpx.URL("http://cdc.org/rss.xml")
    mock_resp.headers = {"content-type": "application/xml"}
    
    rule = {
        "protocol": "rss",
        "request": {
            "url": "http://cdc.org/rss.xml",
            "method": "GET"
        },
        "list_extractor": {}
    }
    
    with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = mock_resp
        res = await engine.execute_crawl(rule, max_items=5)
        assert res["status_code"] == 200
        assert res["total_extracted"] == 1
        assert res["items"][0]["title"] == "2026年疾控招聘公告"
        assert res["items"][0]["url"] == "http://cdc.org/1.html"

@pytest.mark.asyncio
async def test_custom_sources_crud_and_scheduler_integration():
    """测试自定义爬虫 ORM CRUD 与调度器执行流程"""
    from app.scheduler.manager import scheduler_manager
    test_key = "test_pytest_custom_cdc"
    
    async with AsyncSessionLocal() as session:
        # 清理旧数据
        await session.execute(delete(CustomSource).where(CustomSource.source_key == test_key))
        await session.commit()
        
        # 插入测试源
        cs = CustomSource(
            source_key=test_key,
            name="Pytest测试自定义疾控",
            province="四川",
            protocol="html_list",
            rule_json=json.dumps({
                "protocol": "html_list",
                "request": {"url": "http://mock-test.gov.cn/jobs", "method": "GET"},
                "list_extractor": {
                    "item_selector": "li",
                    "title_selector": "a::text",
                    "url_selector": "a::attr(href)",
                    "date_selector": "span::text"
                }
            }),
            is_active=1
        )
        session.add(cs)
        await session.commit()
        await session.refresh(cs)
        cs_id = cs.id
    
    # Mock 执行调度
    with patch.object(GenericCrawlerEngine, "execute_crawl", new_callable=AsyncMock) as mock_crawl:
        mock_crawl.return_value = {
            "status_code": 200,
            "cost_ms": 120,
            "total_extracted": 1,
            "items": [{
                "title": "2026成都市疾控预防医学招聘公告",
                "url": f"http://mock-test.gov.cn/jobs/{test_key}_1.html",
                "date": "2026-08-21",
                "content": "招聘预防医学专业事业编制人员"
            }]
        }
        run_res = await scheduler_manager.run_custom_source(cs_id)
        assert run_res["status"] == "SUCCESS"
        assert run_res["items_found"] == 1
        
    # 清理测试数据
    async with AsyncSessionLocal() as session:
        await session.execute(delete(CustomSource).where(CustomSource.source_key == test_key))
        await session.commit()
