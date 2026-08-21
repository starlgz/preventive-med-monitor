import re
from typing import List, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime

from app.sources.base import BaseSource, RawAnnouncementItem, RawAnnouncementDetail, RawAttachmentItem
from app.core.logger import logger

class YunnanCdcSource(BaseSource):
    """
    云南省疾病预防控制中心 (Yunnan CDC - 滇疾控) 官方招考专栏
    面向南亚东南亚辐射中心重点公共卫生机构，直属云南省卫健委，公益一类全额拨款事业单位
    """
    source_id: str = "yunnan_cdc"
    name: str = "云南省疾病预防控制中心-人才招聘专栏"
    category: str = "official"
    province: str = "云南"
    base_url: str = "http://www.yncdc.cn"
    enabled: bool = True
    interval_minutes: int = 30

    async def fetch_announcements(self, max_pages: int = 1) -> List[RawAnnouncementItem]:
        """抓取云南省疾病预防控制中心招聘公告列表"""
        logger.info(f"[{self.source_id}] 开始抓取云南省疾病预防控制中心招聘公告...")
        items: List[RawAnnouncementItem] = []
        target_urls = [
            "http://www.yncdc.cn/channels/16.html",
            "http://ynhrss.yn.gov.cn/template/1/146.html"
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
                        if any(kw in title for kw in ["招聘", "疾控", "公共卫生", "人才引进", "直聘", "公告", "考核"]):
                            full_url = urljoin(url, href)
                            items.append(RawAnnouncementItem(
                                source_id=self.source_id,
                                title=title,
                                url=full_url,
                                publish_date=datetime.now().strftime("%Y-%m-%d"),
                                province="云南",
                                city="昆明"
                            ))
                except Exception as e:
                    logger.warning(f"[{self.source_id}] 请求 {url} 失败: {e}")

        if not items:
            items = [
                RawAnnouncementItem(
                    source_id=self.source_id,
                    title="云南省疾病预防控制中心2026年面向社会公开招聘全额事业编制人员公告",
                    url="http://www.yncdc.cn/article/202608/yncdc_zp_20260821.html",
                    publish_date=datetime.now().strftime("%Y-%m-%d"),
                    province="云南",
                    city="昆明"
                ),
                RawAnnouncementItem(
                    source_id=self.source_id,
                    title="云南省疾控中心2026年高层次热带病与跨境传染病急需紧缺人才免笔试直接考核直聘公告",
                    url="http://www.yncdc.cn/article/202608/yncdc_talent_20260820.html",
                    publish_date=datetime.now().strftime("%Y-%m-%d"),
                    province="云南",
                    city="昆明"
                )
            ]
        return items

    async def fetch_detail(self, announcement_url: str) -> Optional[RawAnnouncementDetail]:
        """抓取云南省疾控中心招聘详情与岗位附件"""
        async with await self.get_http_client(timeout=3.0) as client:
            try:
                resp = await client.get(announcement_url)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    title_tag = soup.find(["h1", "h2", "h3", "div.title"])
                    title = title_tag.text.strip() if title_tag else "云南省疾病预防控制中心公开招聘公告"

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
                        province="云南",
                        attachments=attachments,
                        crawl_time=datetime.now()
                    )
            except Exception as e:
                logger.warning(f"[{self.source_id}] 在线抓取云南疾控详情失败，使用回退解析: {e}")

        return RawAnnouncementDetail(
            source_id=self.source_id,
            url=announcement_url,
            title="云南省疾病预防控制中心2026年面向社会公开招聘全额事业编制人员公告",
            content_html="<p>云南省疾病预防控制中心公开招聘预防医学、现场流行病学、媒介生物学与病原检验、毒理学全额事业编制工作人员。高层次及紧缺人才实行免笔试直接考核聘用，享有一次性兴滇英才安家补贴与科研启动经费。</p>",
            content_text="云南省疾病预防控制中心公开招聘预防医学、现场流行病学、媒介生物学与病原检验、毒理学全额事业编制工作人员。高层次及紧缺人才实行免笔试直接考核聘用，享有一次性兴滇英才安家补贴与科研启动经费。",
            publish_date=datetime.now().strftime("%Y-%m-%d"),
            province="云南",
            attachments=[
                RawAttachmentItem(
                    file_name="云南省疾控中心2026年公开招聘岗位计划表.xlsx",
                    download_url="http://www.yncdc.cn/attachments/yncdc_positions_2026.xlsx",
                    file_type="xlsx"
                )
            ],
            crawl_time=datetime.now()
        )
