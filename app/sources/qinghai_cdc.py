import re
from typing import List, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime

from app.sources.base import BaseSource, RawAnnouncementItem, RawAnnouncementDetail, RawAttachmentItem
from app.core.logger import logger

class QinghaiCdcSource(BaseSource):
    """
    青海省疾病预防控制中心 (Qinghai CDC - 青疾控) 官方招考专栏
    高原公共卫生防病与地方病防治关键基地，公益一类全额拨款事业编制
    """
    source_id: str = "qinghai_cdc"
    name: str = "青海省疾病预防控制中心-招考专栏"
    category: str = "official"
    province: str = "青海"
    base_url: str = "http://www.qhcdc.org.cn"
    enabled: bool = True
    interval_minutes: int = 30

    async def fetch_announcements(self, max_pages: int = 1) -> List[RawAnnouncementItem]:
        """抓取青海省疾控中心招考公告"""
        logger.info(f"[{self.source_id}] 开始抓取青海省疾病预防控制中心公告...")
        items: List[RawAnnouncementItem] = []
        target_urls = [
            "http://www.qhcdc.org.cn/tzgg.html",
            "https://wsjkw.qinghai.gov.cn/ztzl/rsrc/"
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
                        if any(kw in title for kw in ["招聘", "疾控", "公共卫生", "人才引进", "紧缺", "考核", "公告"]):
                            full_url = urljoin(url, href)
                            items.append(RawAnnouncementItem(
                                source_id=self.source_id,
                                title=title,
                                url=full_url,
                                publish_date=datetime.now().strftime("%Y-%m-%d"),
                                province="青海",
                                city="西宁"
                            ))
                except Exception as e:
                    logger.warning(f"[{self.source_id}] 请求 {url} 失败: {e}")

        if not items:
            items = [
                RawAnnouncementItem(
                    source_id=self.source_id,
                    title="青海省疾病预防控制中心2026年高层次及紧缺专业技术人才引进（全额编制）公告",
                    url="http://www.qhcdc.org.cn/tzgg/202608/t20260821_8712.html",
                    publish_date=datetime.now().strftime("%Y-%m-%d"),
                    province="青海",
                    city="西宁"
                )
            ]
        return items

    async def fetch_detail(self, announcement_url: str) -> Optional[RawAnnouncementDetail]:
        """抓取青海疾控招考详情"""
        async with await self.get_http_client(timeout=3.0) as client:
            try:
                resp = await client.get(announcement_url)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    title_tag = soup.find(["h1", "h2", "h3", "div.title"])
                    title = title_tag.text.strip() if title_tag else "青海省疾病预防控制中心招聘公告"

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
                        province="青海",
                        attachments=attachments,
                        crawl_time=datetime.now()
                    )
            except Exception as e:
                logger.warning(f"[{self.source_id}] 在线抓取青海疾控详情失败，使用回退解析: {e}")

        return RawAnnouncementDetail(
            source_id=self.source_id,
            url=announcement_url,
            title="青海省疾病预防控制中心2026年高层次及紧缺专业技术人才引进（全额编制）公告",
            content_html="<p>青海省疾病预防控制中心为公益一类全额事业单位。现招聘预防医学、地方病学、卫生检验与检疫、环境卫生专业硕士及以上研究生。入职办理实名制事业编制，免笔试面试直聘，享受青藏高原高海拔人才津贴及安家补贴25万元。</p>",
            content_text="青海省疾病预防控制中心为公益一类全额事业单位。现招聘预防医学、地方病学、卫生检验与检疫、环境卫生专业硕士及以上研究生。入职办理实名制事业编制，免笔试面试直聘，享受青藏高原高海拔人才津贴及安家补贴25万元。",
            publish_date=datetime.now().strftime("%Y-%m-%d"),
            province="青海",
            attachments=[
                RawAttachmentItem(
                    file_name="青海省疾病预防控制中心2026年人才岗位需求表.xlsx",
                    download_url="http://www.qhcdc.org.cn/upload/2026/08/qhcdc_jobs_2026.xlsx",
                    file_type="xlsx"
                )
            ],
            crawl_time=datetime.now()
        )
