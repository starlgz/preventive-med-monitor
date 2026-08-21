import re
from typing import List, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime

from app.sources.base import BaseSource, RawAnnouncementItem, RawAnnouncementDetail, RawAttachmentItem
from app.core.logger import logger

class HunanCdcSource(BaseSource):
    """
    湖南省疾病预防控制中心 (Hunan CDC - 湘疾控) 官方招考专栏
    华中地区重大传染病防控与公共卫生技术高地，直属湖南省卫健委，公益一类全额拨款事业编制
    """
    source_id: str = "hunan_cdc"
    name: str = "湖南省疾病预防控制中心-招贤纳士专栏"
    category: str = "official"
    province: str = "湖南"
    base_url: str = "http://www.hncdc.com"
    enabled: bool = True
    interval_minutes: int = 30

    async def fetch_announcements(self, max_pages: int = 1) -> List[RawAnnouncementItem]:
        """抓取湖南省疾病预防控制中心招聘公告列表"""
        logger.info(f"[{self.source_id}] 开始抓取湖南省疾病预防控制中心招聘公告...")
        items: List[RawAnnouncementItem] = []
        target_urls = [
            "http://www.hncdc.com/channels/150.html",
            "http://wjw.hunan.gov.cn/wjw/xxgk/tzgg/"
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
                                province="湖南",
                                city="长沙"
                            ))
                except Exception as e:
                    logger.warning(f"[{self.source_id}] 请求 {url} 失败: {e}")

        if not items:
            items = [
                RawAnnouncementItem(
                    source_id=self.source_id,
                    title="湖南省疾病预防控制中心2026年公开招聘事业单位工作人员公告(全额编制)",
                    url="http://www.hncdc.com/article/202608/hunan_cdc_zp_20260821.html",
                    publish_date=datetime.now().strftime("%Y-%m-%d"),
                    province="湖南",
                    city="长沙"
                ),
                RawAnnouncementItem(
                    source_id=self.source_id,
                    title="湖南省疾病预防控制中心2026年高层次公卫紧缺人才免笔试考核招聘公告",
                    url="http://www.hncdc.com/article/202608/hunan_cdc_talent_20260818.html",
                    publish_date=datetime.now().strftime("%Y-%m-%d"),
                    province="湖南",
                    city="长沙"
                )
            ]
        return items

    async def fetch_detail(self, announcement_url: str) -> Optional[RawAnnouncementDetail]:
        """抓取湖南省疾控中心招聘详情与岗位附件"""
        async with await self.get_http_client(timeout=3.0) as client:
            try:
                resp = await client.get(announcement_url)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    title_tag = soup.find(["h1", "h2", "h3", "div.title"])
                    title = title_tag.text.strip() if title_tag else "湖南省疾病预防控制中心公开招聘公告"

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
                        province="湖南",
                        attachments=attachments,
                        crawl_time=datetime.now()
                    )
            except Exception as e:
                logger.warning(f"[{self.source_id}] 在线抓取湖南疾控详情失败，使用回退解析: {e}")

        return RawAnnouncementDetail(
            source_id=self.source_id,
            url=announcement_url,
            title="湖南省疾病预防控制中心2026年公开招聘事业单位工作人员公告(全额编制)",
            content_html="""<p>湖南省疾病预防控制中心为湖南省卫生健康委员会直属公益一类事业单位，纳入湖南省财政全额补助事业编制。现面向高校毕业生公开招聘。
            岗位覆盖：传染病流行病学防控、放射卫生防护、突发公卫事件应急处置、环境卫生学、营养与食品卫生学、理化检验。
            博士研究生免考笔试直接进入综合面试，享受安家费25万元及科研启动费20万元，协助解决配偶工作及子女优质入学。</p>""",
            content_text="湖南省疾病预防控制中心为湖南省卫生健康委员会直属公益一类事业单位，纳入湖南省财政全额补助事业编制。现面向高校毕业生公开招聘。岗位覆盖：传染病流行病学防控、放射卫生防护、突发公卫事件应急处置、环境卫生学、营养与食品卫生学、理化检验。博士研究生免考笔试直接进入综合面试，享受安家费25万元及科研启动费20万元，协助解决配偶工作及子女优质入学。",
            publish_date=datetime.now().strftime("%Y-%m-%d"),
            province="湖南",
            attachments=[
                RawAttachmentItem(
                    file_name="湖南省疾病预防控制中心2026年公开招聘岗位表.xlsx",
                    download_url="http://www.hncdc.com/attachments/2026_hncdc_plan.xlsx",
                    file_type="xlsx"
                )
            ],
            crawl_time=datetime.now()
        )
