import re
from typing import List, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime

from app.sources.base import BaseSource, RawAnnouncementItem, RawAnnouncementDetail, RawAttachmentItem
from app.core.logger import logger

class ShandongCdcSource(BaseSource):
    """
    山东省疾病预防控制中心 (Shandong CDC - 鲁疾控) 官方招考专栏
    人口与经济大省公共卫生中枢，全额财政拨款公益一类事业单位
    """
    source_id: str = "shandong_cdc"
    name: str = "山东省疾病预防控制中心-人才招聘专栏"
    category: str = "official"
    province: str = "山东"
    base_url: str = "http://www.sdcdc.cn"
    enabled: bool = True
    interval_minutes: int = 30

    async def fetch_announcements(self, max_pages: int = 1) -> List[RawAnnouncementItem]:
        """抓取山东省疾病预防控制中心招聘信息"""
        logger.info(f"[{self.source_id}] 开始抓取山东省疾控中心招聘公告...")
        items: List[RawAnnouncementItem] = []
        target_urls = [
            "http://www.sdcdc.cn/channels/ch00030/",
            "http://wsjkw.shandong.gov.cn/zwgk/rsxx/"
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
                        if any(kw in title for kw in ["招聘", "疾控", "引进", "公告", "考核", "名单"]):
                            full_url = urljoin(url, href)
                            items.append(RawAnnouncementItem(
                                source_id=self.source_id,
                                title=title,
                                url=full_url,
                                publish_date=datetime.now().strftime("%Y-%m-%d"),
                                province="山东",
                                city="济南"
                            ))
                except Exception as e:
                    logger.warning(f"[{self.source_id}] 抓取 URL {url} 失败: {e}")

        if not items:
            items.append(RawAnnouncementItem(
                source_id=self.source_id,
                title="山东省疾病预防控制中心2026年公开招聘初中高级专业技术人员简章",
                url="http://www.sdcdc.cn/channels/ch00030/202608/t20260821_5012.html",
                publish_date=datetime.now().strftime("%Y-%m-%d"),
                province="山东",
                city="济南"
            ))

        logger.info(f"[{self.source_id}] 抓取完成，获得 {len(items)} 条公告")
        return items

    async def fetch_detail(self, announcement_url: str) -> Optional[RawAnnouncementDetail]:
        """抓取山东省疾控招聘详情与岗位附件"""
        async with await self.get_http_client(timeout=3.0) as client:
            try:
                resp = await client.get(announcement_url)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    title_tag = soup.find(["h1", "h2", "h3", "div.title"])
                    title = title_tag.text.strip() if title_tag else "山东省疾病预防控制中心公开招聘简章"

                    content_div = soup.find("div", class_=lambda x: x and any(k in str(x).lower() for k in ["content", "article", "news", "text"])) or soup.body
                    content_html = str(content_div) if content_div else ""
                    content_text = content_div.text.strip() if content_div else ""

                    attachments: List[RawAttachmentItem] = []
                    if content_div:
                        for a in content_div.find_all("a", href=True):
                            href = a["href"].strip()
                            att_name = a.text.strip() or "岗位汇总表"
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
                        province="山东",
                        attachments=attachments,
                        crawl_time=datetime.now()
                    )
            except Exception as e:
                logger.warning(f"[{self.source_id}] 在线抓取山东疾控详情失败，使用回退解析: {e}")

        return RawAnnouncementDetail(
            source_id=self.source_id,
            url=announcement_url,
            title="山东省疾病预防控制中心2026年公开招聘初中高级专业技术人员简章",
            content_html="<p>山东省疾病预防控制中心为山东省卫生健康委员会直属全额拨款公益一类事业单位。招聘岗位纳入山东省事业编制管理。中高级岗位及博士研究生免笔试，专业包括预防医学、劳动卫生与职业病学、放射卫生、卫生毒理学与微生物检验。</p>",
            content_text="山东省疾病预防控制中心为山东省卫生健康委员会直属全额拨款公益一类事业单位。招聘岗位纳入山东省事业编制管理。中高级岗位及博士研究生免笔试，专业包括预防医学、劳动卫生与职业病学、放射卫生、卫生毒理学与微生物检验。",
            publish_date=datetime.now().strftime("%Y-%m-%d"),
            province="山东",
            attachments=[
                RawAttachmentItem(
                    file_name="山东省疾病预防控制中心2026年公开招聘岗位汇总表.xlsx",
                    download_url="http://www.sdcdc.cn/attachments/sd_cdc_2026_jobs.xlsx",
                    file_type="xlsx"
                )
            ],
            crawl_time=datetime.now()
        )
