"""
Generic Dynamic Crawler Engine (低代码通用爬虫引擎)
支持基于 JSON/Dict 规则动态抓取 HTML、JSON API 或 RSS 列表与详情。
"""
import asyncio
import json
import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin
import xml.etree.ElementTree as ET

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class GenericCrawlerEngine:
    """
    通用低代码爬虫引擎
    """
    def __init__(self, timeout: float = 15.0):
        self.timeout = timeout
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/json,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }

    async def fetch_url(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        json_body: Optional[Dict[str, Any]] = None
    ) -> httpx.Response:
        req_headers = dict(self.headers)
        if headers:
            req_headers.update(headers)

        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True, verify=False) as client:
            if method.upper() == "POST":
                if json_body is not None:
                    resp = await client.post(url, headers=req_headers, params=params, json=json_body)
                else:
                    resp = await client.post(url, headers=req_headers, params=params, data=data)
            else:
                resp = await client.get(url, headers=req_headers, params=params)
            
            # 智能字符集编码修复 (GBK / GB2312 / GB18030 自动回退)
            if resp.encoding is None or resp.encoding.lower() in ("iso-8859-1", "ascii"):
                ct = resp.headers.get("content-type", "").lower()
                if "gb2312" in ct or "gbk" in ct or "gb18030" in ct:
                    resp.encoding = "gb18030"
                else:
                    resp.encoding = "utf-8"
            return resp

    def _extract_by_selector(self, elem: Any, selector_expr: str) -> Optional[str]:
        """
        支持语法:
        - 'a::text' -> 提取标签文本
        - 'a::attr(href)' -> 提取属性
        - 'a' -> 默认提取文本
        """
        if not selector_expr or not elem:
            return None

        attr_match = re.search(r'::attr\(([^)]+)\)', selector_expr)
        clean_css = re.sub(r'::.*$', '', selector_expr).strip()
        target = elem.select_one(clean_css) if clean_css else elem

        if not target:
            return None

        if attr_match:
            attr_name = attr_match.group(1).strip()
            val = target.get(attr_name)
            return str(val).strip() if val else None
        
        # 提取文本
        return target.get_text(strip=True)

    def parse_html_list(self, html_text: str, base_url: str, rule: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        解析 HTML 网页列表
        """
        soup = BeautifulSoup(html_text, "html.parser")
        list_rule = rule.get("list_extractor", {})
        item_sel = list_rule.get("item_selector", "li")
        title_sel = list_rule.get("title_selector", "a::text")
        url_sel = list_rule.get("url_selector", "a::attr(href)")
        date_sel = list_rule.get("date_selector")

        results = []
        items = soup.select(item_sel)
        for item in items:
            title = self._extract_by_selector(item, title_sel)
            link = self._extract_by_selector(item, url_sel)
            date_str = self._extract_by_selector(item, date_sel) if date_sel else None

            if not title or not link:
                continue

            full_url = urljoin(base_url, link)
            results.append({
                "title": title.strip(),
                "url": full_url,
                "date": date_str.strip() if date_str else None,
                "raw_html": str(item)
            })
        return results

    def parse_json_api(self, json_data: Any, base_url: str, rule: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        解析 JSON API 响应
        """
        list_rule = rule.get("list_extractor", {})
        items_path = list_rule.get("item_selector") or list_rule.get("items_path", "data.list")
        title_key = list_rule.get("title_selector") or list_rule.get("title_key", "title")
        url_key = list_rule.get("url_selector") or list_rule.get("url_key", "url")
        url_prefix = list_rule.get("url_prefix", "")
        date_key = list_rule.get("date_selector") or list_rule.get("date_key", "publish_date")

        # 遍历 JSON 路径
        curr = json_data
        for p in items_path.split("."):
            if isinstance(curr, dict) and p in curr:
                curr = curr[p]
            elif isinstance(curr, list) and p.isdigit():
                idx = int(p)
                if 0 <= idx < len(curr):
                    curr = curr[idx]
            else:
                curr = []
                break

        results = []
        if isinstance(curr, list):
            for row in curr:
                if not isinstance(row, dict):
                    continue
                title = row.get(title_key)
                raw_link = row.get(url_key)
                date_val = row.get(date_key)
                if not title or not raw_link:
                    continue

                if url_prefix:
                    full_url = f"{url_prefix.rstrip('/')}/{str(raw_link).lstrip('/')}"
                elif str(raw_link).startswith("http"):
                    full_url = str(raw_link)
                else:
                    full_url = str(raw_link)

                results.append({
                    "title": str(title).strip(),
                    "url": full_url,
                    "date": str(date_val).strip() if date_val else None,
                    "extra_data": row
                })
        return results

    def parse_rss(self, xml_text: str, base_url: str, rule: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        解析 RSS/XML 订阅源
        """
        results = []
        try:
            root = ET.fromstring(xml_text)
            for item in root.findall(".//item"):
                title_elem = item.find("title")
                link_elem = item.find("link")
                pub_elem = item.find("pubDate")
                if title_elem is not None and title_elem.text:
                    title = title_elem.text.strip()
                    link = link_elem.text.strip() if link_elem is not None and link_elem.text else ""
                    date_val = pub_elem.text.strip() if pub_elem is not None and pub_elem.text else None
                    if link:
                        results.append({
                            "title": title,
                            "url": urljoin(base_url, link),
                            "date": date_val
                        })
        except Exception as e:
            logger.error(f"Error parsing RSS: {e}")
        return results

    async def execute_crawl(self, rule: Dict[str, Any], max_items: int = 10) -> Dict[str, Any]:
        """
        统一执行抓取 (支持沙箱测试与生产轮询)
        """
        start_time = datetime.now()
        protocol = rule.get("protocol", "html_list") # html_list | json_api | rss
        req_conf = rule.get("request", {})
        url = req_conf.get("url", "")
        method = req_conf.get("method", "GET")
        headers = req_conf.get("headers", {})
        params = req_conf.get("params", {})
        data = req_conf.get("data", {})
        json_body = req_conf.get("json_body")

        if not url:
            raise ValueError("URL 不能为空")

        resp = await self.fetch_url(
            url=url,
            method=method,
            headers=headers,
            params=params,
            data=data,
            json_body=json_body
        )

        cost_ms = int((datetime.now() - start_time).total_seconds() * 1000)

        items = []
        if protocol == "html_list":
            items = self.parse_html_list(resp.text, base_url=str(resp.url), rule=rule)
        elif protocol == "json_api":
            try:
                jdata = resp.json()
                items = self.parse_json_api(jdata, base_url=str(resp.url), rule=rule)
            except Exception as e:
                raise ValueError(f"解析 JSON API 失败: {str(e)}")
        elif protocol == "rss":
            items = self.parse_rss(resp.text, base_url=str(resp.url), rule=rule)
        else:
            raise NotImplementedError(f"不支持的协议类型: {protocol}")

        return {
            "status_code": resp.status_code,
            "cost_ms": cost_ms,
            "total_extracted": len(items),
            "items": items[:max_items]
        }
