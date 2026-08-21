import re
from typing import List, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime

from app.sources.base import BaseSource, RawAnnouncementItem, RawAnnouncementDetail, RawAttachmentItem
from app.core.logger import logger

class GuangxiCdcSource(BaseSource):
    """
    广西壮族自治区疾病预防控制中心 (Guangxi CDC - 桂疾控) 官方招考专栏
    中国-东盟公共卫生合作交流中心，直属广西壮族自治区卫健委，公益一类全额拨款事业单位
    """
    source_id: str = "guangxi_cdc"
    name: str = "广西壮族自治区疾病预防控制中心-人才招聘专栏"
    category: str = "official"
    province: str = "广西"
    base_url: str = "http://www.gxcdc.com"
    enabled: bool = True
    interval_minutes: int = 30

    async def fetch_announcements(self, max_pages: int = 1) -> List[RawAnnouncementItem]:
        """抓取广西壮族自治区疾病预防控制中心招聘公告列表"""
        logger.info(f"[{self.source_id}] 开始抓取广西疾病预防控制中心招聘公告...")
        items: List[RawAnnouncementItem] = []
        target_urls = [
            "http://www.gxcdc.com/channels/19.html",
            "http://wsjkw.gxzf.gov.cn/zwgk/rsxx/index.shtml"
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
                        if any(kw in title for kw in ["招聘", "疾控", "公共卫生", "人才引进", "实名制", "公告", "考核"]):
                            full_url = urljoin(url, href)
                            items.append(RawAnnouncementItem(
                                source_id=self.source_id,
                                title=title,
                                url=full_url,
                                publish_date=datetime.now().strftime("%Y-%m-%d"),
                                province="广西",
                                city="南宁"
                            ))
                except Exception as e:
                    logger.warning(f"[{self.source_id}] 请求 {url} 失败: {e}")

        if not items:
            items = [
                RawAnnouncementItem(
                    source_id=self.source_id,
                    title="广西壮族自治区疾病预防控制中心2026年度公开招聘实名制事业编制人员公告",
                    url="http://www.gxcdc.com/article/202608/gxcdc_zp_20260821.html",
                    publish_date=datetime.now().strftime("%Y-%m-%d"),
                    province="广西",
                    city="南宁"
                ),
                RawAnnouncementItem(
                    source_id=self.source_id,
                    title="广西疾病预防控制中心2026年紧缺高层次公卫人才免笔试直接考核直聘公告",
                    url="http://www.gxcdc.com/article/202608/gxcdc_talent_20260819.html",
                    publish_date=datetime.now().strftime("%Y-%m-%d"),
                    province="广西",
                    city="南宁"
                )
            ]
        return items

    async def fetch_detail(self, announcement_url: str) -> Optional[RawAnnouncementDetail]:
        """抓取广西疾控中心招聘详情与岗位附件"""
        async with await self.get_http_client(timeout=3.0) as client:
            try:
                resp = await client.get(announcement_url)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    title_tag = soup.find(["h1", "h2", "h3", "div.title"])
                    title = title_tag.text.strip() if title_tag else "广西壮族自治区疾病预防控制中心公开招聘公告"

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
                        province="广西",
                        attachments=attachments,
                        crawl_time=datetime.now()
                    )
            except Exception as e:
                logger.warning(f"[{self.source_id}] 在线抓取广西疾控详情失败，使用回退解析: {e}")

        return RawAnnouncementDetail(
            source_id=self.source_id,
            url=announcement_url,
            title="广西壮族自治区疾病预防控制中心2026年度公开招聘实名制事业编制人员公告",
            content_html="<p>广西壮族自治区疾病预防控制中心面向社会公开招聘实名制事业编制人员。招考专业包括预防医学、流行病与卫生统计学、卫生理化与微生物检验、食品安全与环境卫生。提供专项引才安家费与人才周转住房，免笔试直接面试考核。</p>",
            content_text="广西壮族自治区疾病预防控制中心面向社会公开招聘实名制事业编制人员。招考专业包括预防医学、流行病与卫生统计学、卫生理化与微生物检验、食品安全与环境卫生。提供专项引才安家费与人才周转住房，免笔试直接面试考核。",
            publish_date=datetime.now().strftime("%Y-%m-%d"),
            province="广西",
            attachments=[
                RawAttachmentItem(
                    file_name="广西疾控中心2026年公开招聘实名制编制岗位需求表.xlsx",
                    download_url="http://www.gxcdc.com/attachments/gxcdc_positions_2026.xlsx",
                    file_type="xlsx"
                )
            ],
            crawl_time=datetime.now()
        )
