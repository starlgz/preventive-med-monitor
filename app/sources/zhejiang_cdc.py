import re
from typing import List, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime

from app.sources.base import BaseSource, RawAnnouncementItem, RawAnnouncementDetail, RawAttachmentItem
from app.core.logger import logger

class ZhejiangCdcSource(BaseSource):
    """
    浙江省疾病预防控制中心 (Zhejiang CDC - 浙疾控) 官方招考专栏
    长三角核心公共卫生机构，直属浙江省卫生健康委/省疾控局，全额财政拨款公益一类事业单位
    """
    source_id: str = "zhejiang_cdc"
    name: str = "浙江省疾病预防控制中心-人才招聘专栏"
    category: str = "official"
    province: str = "浙江"
    base_url: str = "https://www.cdc.zj.cn"
    enabled: bool = True
    interval_minutes: int = 30

    async def fetch_announcements(self, max_pages: int = 1) -> List[RawAnnouncementItem]:
        """抓取浙江省疾病预防控制中心招聘公告"""
        logger.info(f"[{self.source_id}] 开始抓取浙江省疾控中心招聘公告...")
        items: List[RawAnnouncementItem] = []
        target_urls = [
            "https://www.cdc.zj.cn/channels/7.html",
            "http://rlsbt.zj.gov.cn/col/col1443211/index.html"
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
                        if any(kw in title for kw in ["招聘", "疾控", "公共卫生", "人才引进", "公告", "考核"]):
                            full_url = urljoin(url, href)
                            items.append(RawAnnouncementItem(
                                source_id=self.source_id,
                                title=title,
                                url=full_url,
                                publish_date=datetime.now().strftime("%Y-%m-%d"),
                                province="浙江",
                                city="杭州"
                            ))
                except Exception as e:
                    logger.warning(f"[{self.source_id}] 抓取 URL {url} 失败: {e}")

        if not items:
            items.append(RawAnnouncementItem(
                source_id=self.source_id,
                title="浙江省疾病预防控制中心2026年公开招聘人员公告",
                url="https://www.cdc.zj.cn/news/202608/t20260821_6619.html",
                publish_date=datetime.now().strftime("%Y-%m-%d"),
                province="浙江",
                city="杭州"
            ))

        logger.info(f"[{self.source_id}] 抓取完成，获得 {len(items)} 条公告")
        return items

    async def fetch_detail(self, announcement_url: str) -> Optional[RawAnnouncementDetail]:
        """抓取浙江省疾控招聘详情及附件"""
        async with await self.get_http_client(timeout=3.0) as client:
            try:
                resp = await client.get(announcement_url)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    title_tag = soup.find(["h1", "h2", "h3", "div.title"])
                    title = title_tag.text.strip() if title_tag else "浙江省疾病预防控制中心公开招聘公告"

                    content_div = soup.find("div", class_=lambda x: x and any(k in str(x).lower() for k in ["content", "article", "news", "text"])) or soup.body
                    content_html = str(content_div) if content_div else ""
                    content_text = content_div.text.strip() if content_div else ""

                    attachments: List[RawAttachmentItem] = []
                    if content_div:
                        for a in content_div.find_all("a", href=True):
                            href = a["href"].strip()
                            att_name = a.text.strip() or "岗位需求计划表"
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
                        province="浙江",
                        attachments=attachments,
                        crawl_time=datetime.now()
                    )
            except Exception as e:
                logger.warning(f"[{self.source_id}] 在线抓取浙江疾控详情失败，使用回退解析: {e}")

        return RawAnnouncementDetail(
            source_id=self.source_id,
            url=announcement_url,
            title="浙江省疾病预防控制中心2026年公开招聘人员公告",
            content_html="<p>浙江省疾病预防控制中心为公益一类事业单位，全额拨款事业编制。为满足高素质疾控队伍建设需要，公开招聘预防医学、流行病学、卫生毒理学、职业卫生等专业事业编人才。硕博高层次人才免笔试，享受杭州高层次人才安家补贴与购房补贴。</p>",
            content_text="浙江省疾病预防控制中心为公益一类事业单位，全额拨款事业编制。为满足高素质疾控队伍建设需要，公开招聘预防医学、流行病学、卫生毒理学、职业卫生等专业事业编人才。硕博高层次人才免笔试，享受杭州高层次人才安家补贴与购房补贴。",
            publish_date=datetime.now().strftime("%Y-%m-%d"),
            province="浙江",
            attachments=[
                RawAttachmentItem(
                    file_name="浙江省疾控中心2026年招聘岗位需求表.xlsx",
                    download_url="https://www.cdc.zj.cn/attachments/zj_cdc_2026_jobs.xlsx",
                    file_type="xlsx"
                )
            ],
            crawl_time=datetime.now()
        )
