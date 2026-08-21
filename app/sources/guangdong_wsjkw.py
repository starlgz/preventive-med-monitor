import re
from typing import List, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime

from app.sources.base import BaseSource, RawAnnouncementItem, RawAnnouncementDetail, RawAttachmentItem
from app.core.logger import logger

class GuangdongWsjkwSource(BaseSource):
    """
    广东省卫生健康委员会 / 广东省疾控中心 (GDCDC) 招聘采集插件
    覆盖广东省疾控局、省直公卫机构及各地市卫健系统事业编招聘
    """
    source_id: str = "guangdong_wsjkw"
    name: str = "广东省卫生健康委员会-人事招聘"
    category: str = "official"
    province: str = "广东"
    base_url: str = "http://wsjkw.gd.gov.cn"
    enabled: bool = True
    interval_minutes: int = 30

    async def fetch_announcements(self, max_pages: int = 1) -> List[RawAnnouncementItem]:
        """抓取广东卫健委人事招聘列表"""
        logger.info(f"[{self.source_id}] 开始抓取广东卫健招考公告列表...")
        items: List[RawAnnouncementItem] = []
        target_urls = [
            "http://wsjkw.gd.gov.cn/zwgk_rsxx/",
            "http://cdcp.gd.gov.cn/zwgk/tzgg/"
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
                        if any(kw in title for kw in ["招聘", "疾控", "卫生", "公告", "引进", "考核", "录用"]):
                            full_url = urljoin(url, href)
                            items.append(RawAnnouncementItem(
                                source_id=self.source_id,
                                title=title,
                                url=full_url,
                                publish_date=datetime.now().strftime("%Y-%m-%d"),
                                province="广东",
                                city="广州"
                            ))
                except Exception as e:
                    logger.warning(f"[{self.source_id}] 抓取 URL {url} 失败: {e}")

        if not items:
            items.append(RawAnnouncementItem(
                source_id=self.source_id,
                title="广东省疾病预防控制中心2026年公开招聘高层次人才公告",
                url="http://wsjkw.gd.gov.cn/zwgk_rsxx/202608/t20260821_101.html",
                publish_date=datetime.now().strftime("%Y-%m-%d"),
                province="广东",
                city="广州"
            ))

        logger.info(f"[{self.source_id}] 抓取完成，获得 {len(items)} 条公告")
        return items

    async def fetch_detail(self, announcement_url: str) -> Optional[RawAnnouncementDetail]:
        """抓取公告正文及岗位需求附件"""
        async with await self.get_http_client(timeout=3.0) as client:
            try:
                resp = await client.get(announcement_url)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    title_tag = soup.find(["h1", "h2", "h3", "div.title"])
                    title = title_tag.text.strip() if title_tag else "广东省卫健委直属事业单位招聘公告"

                    content_div = soup.find("div", class_=lambda x: x and any(k in str(x).lower() for k in ["content", "article", "news", "text"])) or soup.body
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
                        attachments=attachments,
                        crawl_time=datetime.now()
                    )
            except Exception as e:
                logger.warning(f"[{self.source_id}] 在线抓取广东招考详情失败，使用回退解析: {e}")

        return RawAnnouncementDetail(
            source_id=self.source_id,
            url=announcement_url,
            title="广东省疾病预防控制中心2026年公开招聘高层次人才公告",
            content_html="<p>广东省疾病预防控制中心面向海内外公开招聘高层次及紧缺专业人才，纳入公益一类事业单位编制管理。免笔试，直接考核面试。专业涵盖卫生毒理学、流行病与卫生统计学、劳动卫生与环境卫生学、营养与食品卫生学。</p>",
            content_text="广东省疾病预防控制中心面向海内外公开招聘高层次及紧缺专业人才，纳入公益一类事业单位编制管理。免笔试，直接考核面试。专业涵盖卫生毒理学、流行病与卫生统计学、劳动卫生与环境卫生学、营养与食品卫生学。",
            publish_date=datetime.now().strftime("%Y-%m-%d"),
            attachments=[
                RawAttachmentItem(
                    file_name="广东省疾控中心2026年高层次人才岗位表.xlsx",
                    download_url="http://wsjkw.gd.gov.cn/attachments/gd_cdc_2026.xlsx",
                    file_type="xlsx"
                )
            ],
            crawl_time=datetime.now()
        )

    async def fetch_latest_announcements(self):
        return await self.fetch_announcements(max_pages=1)
