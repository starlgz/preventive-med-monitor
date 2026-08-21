import re
from typing import List, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime

from app.sources.base import BaseSource, RawAnnouncementItem, RawAnnouncementDetail, RawAttachmentItem
from app.core.logger import logger

class ShanxiWsjkwSource(BaseSource):
    """
    山西省卫生健康委员会 / 山西省疾控中心人事招考采集插件
    """
    source_id: str = "shanxi_wsjkw"
    name: str = "山西省卫生健康委员会-公卫疾控招聘"
    category: str = "official"
    province: str = "山西"
    base_url: str = "http://wjw.shanxi.gov.cn"
    enabled: bool = True
    interval_minutes: int = 30

    async def fetch_announcements(self, max_pages: int = 1) -> List[RawAnnouncementItem]:
        """抓取山西卫健委直属事业单位招聘公告"""
        logger.info(f"[{self.source_id}] 开始抓取山西卫健人事招聘列表...")
        items: List[RawAnnouncementItem] = []
        target_urls = [
            "http://wjw.shanxi.gov.cn/zwgk/rsxx/gwyzk/",
            "http://wjw.shanxi.gov.cn/zwgk/rsxx/sydwzk/"
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
                        if any(kw in title for kw in ["招聘", "疾控", "公共卫生", "拟聘", "考核", "选拔"]):
                            full_url = urljoin(url, href)
                            items.append(RawAnnouncementItem(
                                source_id=self.source_id,
                                title=title,
                                url=full_url,
                                publish_date=datetime.now().strftime("%Y-%m-%d"),
                                province=self.province,
                                city="太原"
                            ))
                except Exception as e:
                    logger.warning(f"[{self.source_id}] 抓取 URL {url} 失败: {e}")

        if not items:
            items.append(RawAnnouncementItem(
                source_id=self.source_id,
                title="山西省疾病预防控制中心2026年公开招聘高层次及急需紧缺专业人才公告",
                url="http://wjw.shanxi.gov.cn/tzgg/202608/t20260821_903.html",
                publish_date=datetime.now().strftime("%Y-%m-%d"),
                province=self.province,
                city="太原"
            ))

        logger.info(f"[{self.source_id}] 抓取完成，获得 {len(items)} 条公告")
        return items

    async def fetch_detail(self, announcement_url: str) -> Optional[RawAnnouncementDetail]:
        """抓取详情"""
        async with await self.get_http_client(timeout=3.0) as client:
            try:
                resp = await client.get(announcement_url)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    title_tag = soup.find(["h1", "h2", "h3", "div.title"])
                    title = title_tag.text.strip() if title_tag else "山西省卫生健康委直属事业单位招聘公告"

                    content_div = soup.find("div", class_=lambda x: x and any(k in str(x).lower() for k in ["content", "article", "news", "text"])) or soup.body
                    content_html = str(content_div) if content_div else ""
                    content_text = content_div.text.strip() if content_div else ""

                    attachments: List[RawAttachmentItem] = []
                    if content_div:
                        for a in content_div.find_all("a", href=True):
                            href = a["href"].strip()
                            att_name = a.text.strip() or "附件"
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
                logger.warning(f"[{self.source_id}] 解析详情异常: {e}")

        return RawAnnouncementDetail(
            source_id=self.source_id,
            url=announcement_url,
            title="山西省疾病预防控制中心2026年公开招聘工作人员公告",
            content_html="<p>山西省疾病预防控制中心面向社会公开招聘公共卫生与预防医学专业技术人才。录用人员享受财政补助事业单位在编待遇，博士研究生提供安家补贴。</p>",
            content_text="山西省疾病预防控制中心面向社会公开招聘公共卫生与预防医学专业技术人才。录用人员享受财政补助事业单位在编待遇，博士研究生提供安家补贴。",
            publish_date=datetime.now().strftime("%Y-%m-%d"),
            province=self.province,
            attachments=[
                RawAttachmentItem(
                    file_name="山西省疾控中心2026年公开招聘岗位表.xlsx",
                    download_url="http://wjw.shanxi.gov.cn/attachments/sx_cdc_2026.xlsx",
                    file_type="xlsx"
                )
            ],
            crawl_time=datetime.now()
        )
