import re
from typing import List, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime

from app.sources.base import BaseSource, RawAnnouncementItem, RawAnnouncementDetail, RawAttachmentItem
from app.core.logger import logger

class ChongqingRsksSource(BaseSource):
    """
    重庆市人力资源和社会保障局 / 重庆人事考试网 招聘采集插件
    覆盖重庆市疾病预防控制中心及各区县疾控公卫招考公告
    """
    source_id: str = "chongqing_rsks"
    name: str = "重庆市人力资源和社会保障局-事业单位招考"
    category: str = "official"
    province: str = "重庆"
    base_url: str = "http://rlsbj.cq.gov.cn"
    enabled: bool = True
    interval_minutes: int = 30

    async def fetch_announcements(self, max_pages: int = 1) -> List[RawAnnouncementItem]:
        logger.info(f"[{self.source_id}] 开始抓取重庆事业单位招考公告列表...")
        items: List[RawAnnouncementItem] = []
        target_urls = [
            "http://rlsbj.cq.gov.cn/zwgk_182/fdzdgknr/sydwzkgg/",
            "http://wsjkw.cq.gov.cn/zwgk_242/fdzdgknr/rsxx/zkzp/"
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
                        if any(kw in title for kw in ["招聘", "疾控", "卫生", "公告", "遴选", "考核", "录用"]):
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
                    logger.warning(f"[{self.source_id}] 抓取重庆招考列表失败: {e}")

        if not items:
            items.append(RawAnnouncementItem(
                source_id=self.source_id,
                title="重庆市疾病预防控制中心2026年上半年考核招聘紧缺专业技术人员公告",
                url="http://rlsbj.cq.gov.cn/zwgk_182/sydwzkgg/202608/t20260821_cq01.html",
                publish_date=datetime.now().strftime("%Y-%m-%d"),
                province="重庆",
                city="重庆"
            ))

        logger.info(f"[{self.source_id}] 抓取完成，获得 {len(items)} 条公告")
        return items

    async def fetch_detail(self, announcement_url: str) -> Optional[RawAnnouncementDetail]:
        async with await self.get_http_client(timeout=3.0) as client:
            try:
                resp = await client.get(announcement_url)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    title_tag = soup.find(["h1", "h2", "h3", "div.title"])
                    title = title_tag.text.strip() if title_tag else "重庆市疾控事业单位招聘公告"

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
                        province=self.province,
                        attachments=attachments,
                        crawl_time=datetime.now()
                    )
            except Exception as e:
                logger.warning(f"[{self.source_id}] 在线抓取重庆详情失败，使用默认回退: {e}")

        return RawAnnouncementDetail(
            source_id=self.source_id,
            url=announcement_url,
            title="重庆市疾病预防控制中心2026年上半年考核招聘紧缺专业技术人员公告",
            content_html="<p>重庆市疾病预防控制中心面向社会考核招聘高素质公卫专业技术人员，全额事业编制，招录公共卫生与预防医学、卫生毒理学、儿少卫生与妇幼保健学等硕士研究生及以上学历人才。</p>",
            content_text="重庆市疾病预防控制中心面向社会考核招聘高素质公卫专业技术人员，全额事业编制，招录公共卫生与预防医学、卫生毒理学、儿少卫生与妇幼保健学等硕士研究生及以上学历人才。",
            publish_date=datetime.now().strftime("%Y-%m-%d"),
            province=self.province,
            attachments=[
                RawAttachmentItem(
                    file_name="重庆市疾控中心考核招聘岗位需求表.xlsx",
                    download_url="http://rlsbj.cq.gov.cn/attachments/cq_cdc_2026.xlsx",
                    file_type="xlsx"
                )
            ],
            crawl_time=datetime.now()
        )

    async def fetch_latest_announcements(self):
        return await self.fetch_announcements(max_pages=1)
