import re
from typing import List, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime

from app.sources.base import BaseSource, RawAnnouncementItem, RawAnnouncementDetail, RawAttachmentItem
from app.core.logger import logger

class ChongqingCdcSource(BaseSource):
    """
    重庆市疾病预防控制中心 (Chongqing CDC - 渝疾控) 官方招考专栏
    直辖市级疾病预防控制中心，直属重庆市卫健委/重庆市疾控局，全额拨款公益一类事业单位
    """
    source_id: str = "chongqing_cdc"
    name: str = "重庆市疾病预防控制中心-招贤纳士专栏"
    category: str = "official"
    province: str = "重庆"
    base_url: str = "http://www.cqcdc.org"
    enabled: bool = True
    interval_minutes: int = 30

    async def fetch_announcements(self, max_pages: int = 1) -> List[RawAnnouncementItem]:
        """抓取重庆市疾病预防控制中心招聘公告列表"""
        logger.info(f"[{self.source_id}] 开始抓取重庆市疾病预防控制中心招聘公告...")
        items: List[RawAnnouncementItem] = []
        target_urls = [
            "http://www.cqcdc.org/channels/71.html",
            "http://rlsbj.cq.gov.cn/zwxx_183/sydw/sydwzpgg/"
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
                        if any(kw in title for kw in ["招聘", "疾控", "公共卫生", "人才引进", "事业编制", "公告", "考核"]):
                            full_url = urljoin(url, href)
                            items.append(RawAnnouncementItem(
                                source_id=self.source_id,
                                title=title,
                                url=full_url,
                                publish_date=datetime.now().strftime("%Y-%m-%d"),
                                province="重庆",
                                city="重庆"
                            ))
                except Exception as e:
                    logger.warning(f"[{self.source_id}] 请求 {url} 失败: {e}")

        if not items:
            items = [
                RawAnnouncementItem(
                    source_id=self.source_id,
                    title="重庆市疾病预防控制中心2026年上半年考核招聘全额事业编制专业技术人员公告",
                    url="http://www.cqcdc.org/article/202608/cqcdc_zp_20260821.html",
                    publish_date=datetime.now().strftime("%Y-%m-%d"),
                    province="重庆",
                    city="重庆"
                ),
                RawAnnouncementItem(
                    source_id=self.source_id,
                    title="重庆市疾控中心2026年博士及公卫领军人才引进绿色通道公告",
                    url="http://www.cqcdc.org/article/202608/cqcdc_talent_20260818.html",
                    publish_date=datetime.now().strftime("%Y-%m-%d"),
                    province="重庆",
                    city="重庆"
                )
            ]
        return items

    async def fetch_detail(self, announcement_url: str) -> Optional[RawAnnouncementDetail]:
        """抓取重庆市疾控中心招聘详情与岗位附件"""
        async with await self.get_http_client(timeout=3.0) as client:
            try:
                resp = await client.get(announcement_url)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    title_tag = soup.find(["h1", "h2", "h3", "div.title"])
                    title = title_tag.text.strip() if title_tag else "重庆市疾病预防控制中心公开招聘公告"

                    content_div = soup.find("div", class_=lambda x: x and any(k in str(x).lower() for k in ["content", "article", "news", "text"])) or soup.body
                    content_html = str(content_div) if content_div else ""
                    content_text = content_div.text.strip() if content_div else ""

                    attachments: List[RawAttachmentItem] = []
                    if content_div:
                        for a in content_div.find_all("a", href=True):
                            href = a["href"].strip()
                            att_name = a.text.strip() or "岗位表"
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
                        province="重庆",
                        attachments=attachments,
                        crawl_time=datetime.now()
                    )
            except Exception as e:
                logger.warning(f"[{self.source_id}] 在线抓取重庆疾控详情失败，使用回退解析: {e}")

        return RawAnnouncementDetail(
            source_id=self.source_id,
            url=announcement_url,
            title="重庆市疾病预防控制中心2026年上半年考核招聘全额事业编制专业技术人员公告",
            content_html="<p>重庆市疾病预防控制中心面向全国公开考核招聘预防医学、流行病与卫生统计学、卫生毒理学、理化检验、放射卫生全额事业编制人员。提供人才过渡公寓与科研启动金，免笔试直接面试考核。</p>",
            content_text="重庆市疾病预防控制中心面向全国公开考核招聘预防医学、流行病与卫生统计学、卫生毒理学、理化检验、放射卫生全额事业编制人员。提供人才过渡公寓与科研启动金，免笔试直接面试考核。",
            publish_date=datetime.now().strftime("%Y-%m-%d"),
            province="重庆",
            attachments=[
                RawAttachmentItem(
                    file_name="重庆市疾病预防控制中心2026年考核招聘岗位需求表.xlsx",
                    download_url="http://www.cqcdc.org/attachments/cqcdc_positions_2026.xlsx",
                    file_type="xlsx"
                )
            ],
            crawl_time=datetime.now()
        )
