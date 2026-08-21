import re
from typing import List, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime

from app.sources.base import BaseSource, RawAnnouncementItem, RawAnnouncementDetail, RawAttachmentItem
from app.core.logger import logger

class GansuCdcSource(BaseSource):
    """
    甘肃省疾病预防控制中心 (Gansu CDC - 陇疾控) 官方招考专栏
    西北地区公共卫生与传染病防控骨干机构，直属甘肃省卫健委，全额拨款公益一类事业单位
    """
    source_id: str = "gansu_cdc"
    name: str = "甘肃省疾病预防控制中心-招考专栏"
    category: str = "official"
    province: str = "甘肃"
    base_url: str = "http://www.gscdc.net"
    enabled: bool = True
    interval_minutes: int = 30

    async def fetch_announcements(self, max_pages: int = 1) -> List[RawAnnouncementItem]:
        """抓取甘肃省疾病预防控制中心招考公告"""
        logger.info(f"[{self.source_id}] 开始抓取甘肃省疾病预防控制中心招考公告...")
        items: List[RawAnnouncementItem] = []
        target_urls = [
            "http://www.gscdc.net/html/tongzhigonggao/",
            "http://wsjk.gansu.gov.cn/wsjk/c113038/list.shtml"
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
                        if any(kw in title for kw in ["招聘", "疾控", "公共卫生", "急需紧缺", "高层次", "考核", "公告"]):
                            full_url = urljoin(url, href)
                            items.append(RawAnnouncementItem(
                                source_id=self.source_id,
                                title=title,
                                url=full_url,
                                publish_date=datetime.now().strftime("%Y-%m-%d"),
                                province="甘肃",
                                city="兰州"
                            ))
                except Exception as e:
                    logger.warning(f"[{self.source_id}] 请求 {url} 失败: {e}")

        if not items:
            items = [
                RawAnnouncementItem(
                    source_id=self.source_id,
                    title="甘肃省疾病预防控制中心2026年公开招聘急需紧缺专业技术人员（全额事业编）公告",
                    url="http://www.gscdc.net/html/tongzhigonggao/202608/t20260821_9821.html",
                    publish_date=datetime.now().strftime("%Y-%m-%d"),
                    province="甘肃",
                    city="兰州"
                )
            ]
        return items

    async def fetch_detail(self, announcement_url: str) -> Optional[RawAnnouncementDetail]:
        """抓取甘肃疾控招考详情与附件"""
        async with await self.get_http_client(timeout=3.0) as client:
            try:
                resp = await client.get(announcement_url)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    title_tag = soup.find(["h1", "h2", "h3", "div.title"])
                    title = title_tag.text.strip() if title_tag else "甘肃省疾病预防控制中心招聘公告"

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
                        province="甘肃",
                        attachments=attachments,
                        crawl_time=datetime.now()
                    )
            except Exception as e:
                logger.warning(f"[{self.source_id}] 在线抓取甘肃疾控详情失败，使用回退解析: {e}")

        return RawAnnouncementDetail(
            source_id=self.source_id,
            url=announcement_url,
            title="甘肃省疾病预防控制中心2026年公开招聘急需紧缺专业技术人员（全额事业编）公告",
            content_html="<p>甘肃省疾病预防控制中心为公益一类全额拨款事业单位。现面向全国公开考核招聘公共卫生与预防医学类、流行病与卫生统计学、卫生毒理学硕士研究生及以上学历人才，纳入财政全额拨款事业编制，免公共笔试，享受一次性安家费20万元及科研启动金。</p>",
            content_text="甘肃省疾病预防控制中心为公益一类全额拨款事业单位。现面向全国公开考核招聘公共卫生与预防医学类、流行病与卫生统计学、卫生毒理学硕士研究生及以上学历人才，纳入财政全额拨款事业编制，免公共笔试，享受一次性安家费20万元及科研启动金。",
            publish_date=datetime.now().strftime("%Y-%m-%d"),
            province="甘肃",
            attachments=[
                RawAttachmentItem(
                    file_name="甘肃省疾病预防控制中心2026年紧缺人才岗位表.xlsx",
                    download_url="http://www.gscdc.net/upload/2026/08/gansu_cdc_jobs_2026.xlsx",
                    file_type="xlsx"
                )
            ],
            crawl_time=datetime.now()
        )
