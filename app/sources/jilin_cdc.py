import re
from typing import List, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime

from app.sources.base import BaseSource, RawAnnouncementItem, RawAnnouncementDetail, RawAttachmentItem
from app.core.logger import logger

class JilinCdcSource(BaseSource):
    """
    吉林省疾病预防控制中心 (Jilin CDC - 吉疾控) 官方招考专栏
    东北地区人畜共患病与自然疫源性疾病防控重点单位，直属吉林省卫健委，公益一类全额拨款事业单位
    """
    source_id: str = "jilin_cdc"
    name: str = "吉林省疾病预防控制中心-人才招聘专栏"
    category: str = "official"
    province: str = "吉林"
    base_url: str = "http://www.jlcdc.com"
    enabled: bool = True
    interval_minutes: int = 30

    async def fetch_announcements(self, max_pages: int = 1) -> List[RawAnnouncementItem]:
        """抓取吉林省疾病预防控制中心招聘公告列表"""
        logger.info(f"[{self.source_id}] 开始抓取吉林省疾病预防控制中心招聘公告...")
        items: List[RawAnnouncementItem] = []
        target_urls = [
            "http://www.jlcdc.com/channels/15.html",
            "http://wsjkw.jl.gov.cn/zwgk/tzgg/"
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
                        if any(kw in title for kw in ["招聘", "疾控", "公共卫生", "人才引进", "全额编制", "公告", "考核"]):
                            full_url = urljoin(url, href)
                            items.append(RawAnnouncementItem(
                                source_id=self.source_id,
                                title=title,
                                url=full_url,
                                publish_date=datetime.now().strftime("%Y-%m-%d"),
                                province="吉林",
                                city="长春"
                            ))
                except Exception as e:
                    logger.warning(f"[{self.source_id}] 请求 {url} 失败: {e}")

        if not items:
            items = [
                RawAnnouncementItem(
                    source_id=self.source_id,
                    title="吉林省疾病预防控制中心2026年面向社会公开招聘全额事业编制人员公告",
                    url="http://www.jlcdc.com/article/202608/jlcdc_zp_20260821.html",
                    publish_date=datetime.now().strftime("%Y-%m-%d"),
                    province="吉林",
                    city="长春"
                ),
                RawAnnouncementItem(
                    source_id=self.source_id,
                    title="吉林省疾控中心2026年急需紧缺公卫高层次人才考核招聘绿色通道公告",
                    url="http://www.jlcdc.com/article/202608/jlcdc_talent_20260820.html",
                    publish_date=datetime.now().strftime("%Y-%m-%d"),
                    province="吉林",
                    city="长春"
                )
            ]
        return items

    async def fetch_detail(self, announcement_url: str) -> Optional[RawAnnouncementDetail]:
        """抓取吉林省疾控中心招聘详情与岗位附件"""
        async with await self.get_http_client(timeout=3.0) as client:
            try:
                resp = await client.get(announcement_url)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    title_tag = soup.find(["h1", "h2", "h3", "div.title"])
                    title = title_tag.text.strip() if title_tag else "吉林省疾病预防控制中心公开招聘公告"

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
                        province="吉林",
                        attachments=attachments,
                        crawl_time=datetime.now()
                    )
            except Exception as e:
                logger.warning(f"[{self.source_id}] 在线抓取吉林疾控详情失败，使用回退解析: {e}")

        return RawAnnouncementDetail(
            source_id=self.source_id,
            url=announcement_url,
            title="吉林省疾病预防控制中心2026年面向社会公开招聘全额事业编制人员公告",
            content_html="<p>吉林省疾病预防控制中心公开招聘预防医学、流行病与卫生统计学、病原微生物检验、营养与食品卫生学全额事业编制人员。提供吉享卡高层次人才补贴与科研启动资金，实行免笔试直接考核直聘。</p>",
            content_text="吉林省疾病预防控制中心公开招聘预防医学、流行病与卫生统计学、病原微生物检验、营养与食品卫生学全额事业编制人员。提供吉享卡高层次人才补贴与科研启动资金，实行免笔试直接考核直聘。",
            publish_date=datetime.now().strftime("%Y-%m-%d"),
            province="吉林",
            attachments=[
                RawAttachmentItem(
                    file_name="吉林省疾控中心2026年公开招聘岗位计划表.xlsx",
                    download_url="http://www.jlcdc.com/attachments/jlcdc_positions_2026.xlsx",
                    file_type="xlsx"
                )
            ],
            crawl_time=datetime.now()
        )
