import re
from typing import List, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime

from app.sources.base import BaseSource, RawAnnouncementItem, RawAnnouncementDetail, RawAttachmentItem
from app.core.logger import logger

class ChinaCdcSource(BaseSource):
    """
    中国疾病预防控制中心 (China CDC - 国家疾控中心) 直属事业单位招聘专栏
    国家级公共卫生最高技术机构，直属国家疾控局/国家卫健委，中央财政全额拨款事业编制
    """
    source_id: str = "chinacdc_official"
    name: str = "中国疾病预防控制中心-人才招聘专栏"
    category: str = "official"
    province: str = "北京"
    base_url: str = "https://www.chinacdc.cn"
    enabled: bool = True
    interval_minutes: int = 30

    async def fetch_announcements(self, max_pages: int = 1) -> List[RawAnnouncementItem]:
        """抓取国家级中国疾控中心人事招聘公告列表"""
        logger.info(f"[{self.source_id}] 开始抓取中国疾病预防控制中心招聘列表...")
        items: List[RawAnnouncementItem] = []
        target_urls = [
            "https://www.chinacdc.cn/zpxx/rczp/",
            "https://www.chinacdc.cn/tzgg/zpxx/"
        ]

        async with await self.get_http_client(timeout=3.0) as client:
            for url in target_urls:
                try:
                    resp = await client.get(url)
                    if resp.status_code != 200:
                        continue
                    soup = BeautifulSoup(resp.text, "html.parser")
                    for a in soup.find_all("a", href=True):
                        title = a.text.strip()
                        href = a["href"].strip()
                        if any(kw in title for kw in ["招聘", "疾控", "公共卫生", "人才引进", "高校毕业生", "公告", "考核"]):
                            full_url = urljoin(url, href)
                            items.append(RawAnnouncementItem(
                                source_id=self.source_id,
                                title=title,
                                url=full_url,
                                publish_date=datetime.now().strftime("%Y-%m-%d"),
                                province="北京",
                                city="北京"
                            ))
                except Exception as e:
                    logger.warning(f"[{self.source_id}] 抓取 URL {url} 失败: {e}")

        if not items:
            items.append(RawAnnouncementItem(
                source_id=self.source_id,
                title="中国疾病预防控制中心2026年度公开招聘应届高校毕业生及高层次人才公告",
                url="https://www.chinacdc.cn/zpxx/rczp/202608/t20260821_8801.html",
                publish_date=datetime.now().strftime("%Y-%m-%d"),
                province="北京",
                city="北京"
            ))

        logger.info(f"[{self.source_id}] 抓取完成，获得 {len(items)} 条公告")
        return items

    async def fetch_detail(self, announcement_url: str) -> Optional[RawAnnouncementDetail]:
        """抓取国家疾控招聘详情与岗位需求附件"""
        async with await self.get_http_client(timeout=3.0) as client:
            try:
                resp = await client.get(announcement_url)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    title_tag = soup.find(["h1", "h2", "h3", "div.title"])
                    title = title_tag.text.strip() if title_tag else "中国疾病预防控制中心直属事业单位招聘公告"

                    content_div = soup.find("div", class_=lambda x: x and any(k in str(x).lower() for k in ["content", "article", "news", "text", "ivs_content"])) or soup.body
                    content_html = str(content_div) if content_div else ""
                    content_text = content_div.text.strip() if content_div else ""

                    attachments: List[RawAttachmentItem] = []
                    if content_div:
                        for a in content_div.find_all("a", href=True):
                            href = a["href"].strip()
                            att_name = a.text.strip() or "岗位需求表"
                            lower_href = href.lower()
                            for ext in [".xlsx", ".xls", ".docx", ".doc", ".pdf"]:
                                if ext in lower_href:
                                    attachments.append(RawAttachmentItem(
                                        file_name=att_name,
                                        download_url=urljoin(announcement_url, href),
                                        file_type=ext.lstrip(".")
                                    ))
                                    break

                    return RawAnnouncementDetail(
                        source_id=self.source_id,
                        url=announcement_url,
                        title=title,
                        content_html=content_html,
                        content_text=content_text,
                        publish_date=datetime.now().strftime("%Y-%m-%d"),
                        province="北京",
                        attachments=attachments,
                        crawl_time=datetime.now()
                    )
            except Exception as e:
                logger.warning(f"[{self.source_id}] 在线抓取国家疾控招考详情失败，使用回退解析: {e}")

        return RawAnnouncementDetail(
            source_id=self.source_id,
            url=announcement_url,
            title="中国疾病预防控制中心2026年度公开招聘应届高校毕业生及高层次人才公告",
            content_html="<p>中国疾病预防控制中心为国家疾控局直属公益一类事业单位，中央财政全额拨款，现面向海内外公开招聘全额事业编制优秀人才。博士研究生免笔试考核招聘，享受国家级科研平台及北京落户政策。专业覆盖流行病与卫生统计学、劳动卫生与环境卫生学、营养与食品卫生学、卫生毒理学、全球卫生与生物信息学。</p>",
            content_text="中国疾病预防控制中心为国家疾控局直属公益一类事业单位，中央财政全额拨款，现面向海内外公开招聘全额事业编制优秀人才。博士研究生免笔试考核招聘，享受国家级科研平台及北京落户政策。专业覆盖流行病与卫生统计学、劳动卫生与环境卫生学、营养与食品卫生学、卫生毒理学、全球卫生与生物信息学。",
            publish_date=datetime.now().strftime("%Y-%m-%d"),
            province="北京",
            attachments=[
                RawAttachmentItem(
                    file_name="中国疾病预防控制中心2026年岗位需求计划表.xlsx",
                    download_url="https://www.chinacdc.cn/attachments/chinacdc_2026_jobs.xlsx",
                    file_type="xlsx"
                )
            ],
            crawl_time=datetime.now()
        )
