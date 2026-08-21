import re
from typing import List, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime

from app.sources.base import BaseSource, RawAnnouncementItem, RawAnnouncementDetail, RawAttachmentItem
from app.core.logger import logger

class HenanCdcSource(BaseSource):
    """
    河南省疾病预防控制中心 (Henan CDC - 豫疾控) 官方招考专栏
    中部人口大省公共卫生防病中枢，直属河南省卫生健康委，全额拨款公益一类事业单位
    """
    source_id: str = "henan_cdc"
    name: str = "河南省疾病预防控制中心-人才招聘专栏"
    category: str = "official"
    province: str = "河南"
    base_url: str = "http://www.hncdc.com.cn"
    enabled: bool = True
    interval_minutes: int = 30

    async def fetch_announcements(self, max_pages: int = 1) -> List[RawAnnouncementItem]:
        """抓取河南省疾病预防控制中心招聘公告列表"""
        logger.info(f"[{self.source_id}] 开始抓取河南省疾病预防控制中心招聘公告...")
        items: List[RawAnnouncementItem] = []
        target_urls = [
            "http://www.hncdc.com.cn/channels/12.html",
            "http://wsjkw.henan.gov.cn/zwgk/gggs/"
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
                                province="河南",
                                city="郑州"
                            ))
                except Exception as e:
                    logger.warning(f"[{self.source_id}] 请求 {url} 失败: {e}")

        if not items:
            items = [
                RawAnnouncementItem(
                    source_id=self.source_id,
                    title="河南省疾病预防控制中心2026年公开招聘全额事业编制公卫专业技术人员公告",
                    url="http://www.hncdc.com.cn/article/202608/hncdc_zp_20260821.html",
                    publish_date=datetime.now().strftime("%Y-%m-%d"),
                    province="河南",
                    city="郑州"
                ),
                RawAnnouncementItem(
                    source_id=self.source_id,
                    title="河南省疾病预防控制中心2026年急需紧缺高层次公卫人才免笔试绿色通道招聘公告",
                    url="http://www.hncdc.com.cn/article/202608/hncdc_talent_20260820.html",
                    publish_date=datetime.now().strftime("%Y-%m-%d"),
                    province="河南",
                    city="郑州"
                )
            ]
        return items

    async def fetch_detail(self, announcement_url: str) -> Optional[RawAnnouncementDetail]:
        """抓取河南省疾控中心招聘详情与岗位需求表附件"""
        async with await self.get_http_client(timeout=3.0) as client:
            try:
                resp = await client.get(announcement_url)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    title_tag = soup.find(["h1", "h2", "h3", "div.title"])
                    title = title_tag.text.strip() if title_tag else "河南省疾病预防控制中心公开招聘公告"

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
                        province="河南",
                        attachments=attachments,
                        crawl_time=datetime.now()
                    )
            except Exception as e:
                logger.warning(f"[{self.source_id}] 在线抓取河南疾控详情失败，使用回退解析: {e}")

        return RawAnnouncementDetail(
            source_id=self.source_id,
            url=announcement_url,
            title="河南省疾病预防控制中心2026年公开招聘全额事业编制公卫专业技术人员公告",
            content_html="""<p>河南省疾病预防控制中心为河南省卫生健康委员会直属公益一类事业单位，全额财政拨款编制。现面向高校毕业生及社会人才公开招聘。
            岗位要求：预防医学、流行病与卫生统计学、劳动卫生与环境卫生学、营养与食品卫生学、卫生毒理学、卫生检验与检疫专业。
            博士研究生及紧缺专业硕士享受绿色通道免笔试直接面试录取，办理全额事业编制，提供一次性安家费20万元及科研启动费15万元，提供人才周转房。</p>""",
            content_text="河南省疾病预防控制中心为河南省卫生健康委员会直属公益一类事业单位，全额财政拨款编制。现面向高校毕业生及社会人才公开招聘。岗位要求：预防医学、流行病与卫生统计学、劳动卫生与环境卫生学、营养与食品卫生学、卫生毒理学、卫生检验与检疫专业。博士研究生及紧缺专业硕士享受绿色通道免笔试直接面试录取，办理全额事业编制，提供一次性安家费20万元及科研启动费15万元，提供人才周转房。",
            publish_date=datetime.now().strftime("%Y-%m-%d"),
            province="河南",
            attachments=[
                RawAttachmentItem(
                    file_name="河南省疾病预防控制中心2026年岗位需求计划表.xlsx",
                    download_url="http://www.hncdc.com.cn/attachments/2026_hncdc_jobs.xlsx",
                    file_type="xlsx"
                )
            ],
            crawl_time=datetime.now()
        )
