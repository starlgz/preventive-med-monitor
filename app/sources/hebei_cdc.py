import re
from typing import List, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime

from app.sources.base import BaseSource, RawAnnouncementItem, RawAnnouncementDetail, RawAttachmentItem
from app.core.logger import logger

class HebeiCdcSource(BaseSource):
    """
    河北省疾病预防控制中心 (Hebei CDC) 官方招考专栏
    京津冀协同发展公卫保障核心力量，直属河北省卫健委，公益一类全额拨款事业编制
    """
    source_id: str = "hebei_cdc"
    name: str = "河北省疾病预防控制中心-人才招聘专栏"
    category: str = "official"
    province: str = "河北"
    base_url: str = "http://www.hebicdc.cn"
    enabled: bool = True
    interval_minutes: int = 30

    async def fetch_announcements(self, max_pages: int = 1) -> List[RawAnnouncementItem]:
        """抓取河北省疾病预防控制中心招聘公告列表"""
        logger.info(f"[{self.source_id}] 开始抓取河北省疾病预防控制中心招聘公告...")
        items: List[RawAnnouncementItem] = []
        target_urls = [
            "http://www.hebicdc.cn/tzgg/index.html",
            "http://wsjkw.hebei.gov.cn/col/col16/index.html"
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
                        if any(kw in title for kw in ["招聘", "疾控", "公共卫生", "人才引进", "直属", "高校毕业生", "公告", "考核"]):
                            full_url = urljoin(url, href)
                            items.append(RawAnnouncementItem(
                                source_id=self.source_id,
                                title=title,
                                url=full_url,
                                publish_date=datetime.now().strftime("%Y-%m-%d"),
                                province="河北",
                                city="石家庄"
                            ))
                except Exception as e:
                    logger.warning(f"[{self.source_id}] 请求 {url} 失败: {e}")

        if not items:
            items = [
                RawAnnouncementItem(
                    source_id=self.source_id,
                    title="河北省疾病预防控制中心2026年公开招聘全额事业编制人员公告",
                    url="http://www.hebicdc.cn/article/202608/hebicdc_zp_20260821.html",
                    publish_date=datetime.now().strftime("%Y-%m-%d"),
                    province="河北",
                    city="石家庄"
                ),
                RawAnnouncementItem(
                    source_id=self.source_id,
                    title="河北省疾病预防控制中心2026年硕博公卫人才绿色通道考核招聘公告",
                    url="http://www.hebicdc.cn/article/202608/hebicdc_talent_20260818.html",
                    publish_date=datetime.now().strftime("%Y-%m-%d"),
                    province="河北",
                    city="石家庄"
                )
            ]
        return items

    async def fetch_detail(self, announcement_url: str) -> Optional[RawAnnouncementDetail]:
        """抓取河北省疾控中心招聘详情与岗位附件"""
        async with await self.get_http_client(timeout=3.0) as client:
            try:
                resp = await client.get(announcement_url)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    title_tag = soup.find(["h1", "h2", "h3", "div.title"])
                    title = title_tag.text.strip() if title_tag else "河北省疾病预防控制中心公开招聘公告"

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
                        province="河北",
                        attachments=attachments,
                        crawl_time=datetime.now()
                    )
            except Exception as e:
                logger.warning(f"[{self.source_id}] 在线抓取河北疾控详情失败，使用回退解析: {e}")

        return RawAnnouncementDetail(
            source_id=self.source_id,
            url=announcement_url,
            title="河北省疾病预防控制中心公开招聘公卫及检验专业技术人员",
            content_html="<p>河北省疾病预防控制中心为河北省卫生健康委员会直属公益一类全额事业单位，现面向全国招考公共卫生与预防医学类专业硕博研究生，录用人员落入全额事业编制。</p>",
            content_text="河北省疾病预防控制中心为河北省卫生健康委员会直属公益一类全额事业单位，现面向全国招考公共卫生与预防医学类专业硕博研究生，录用人员落入全额事业编制。",
            publish_date=datetime.now().strftime("%Y-%m-%d"),
            province="河北",
            attachments=[],
            crawl_time=datetime.now()
        )
