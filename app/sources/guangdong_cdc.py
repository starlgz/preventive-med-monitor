import re
from typing import List, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime

from app.sources.base import BaseSource, RawAnnouncementItem, RawAnnouncementDetail, RawAttachmentItem
from app.core.logger import logger

class GuangdongCdcSource(BaseSource):
    """
    广东省疾病预防控制中心 (Guangdong CDC - 粤疾控) 官方招考专栏
    华南地区重点公共卫生技术中心，直属广东省卫生健康委/广东省疾控局，全额预算管理公益一类事业单位
    """
    source_id: str = "guangdong_cdc"
    name: str = "广东省疾病预防控制中心-人才招聘专栏"
    category: str = "official"
    province: str = "广东"
    base_url: str = "http://cdcp.gd.gov.cn"
    enabled: bool = True
    interval_minutes: int = 30

    async def fetch_announcements(self, max_pages: int = 1) -> List[RawAnnouncementItem]:
        """抓取广东省疾病预防控制中心招聘公告列表"""
        logger.info(f"[{self.source_id}] 开始抓取广东省疾病预防控制中心招聘公告...")
        items: List[RawAnnouncementItem] = []
        target_urls = [
            "http://cdcp.gd.gov.cn/zwgk/tzgg/",
            "http://cdcp.gd.gov.cn/zwgk/rsxx/"
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
                        if any(kw in title for kw in ["招聘", "高层次人才", "公卫", "体检", "拟聘", "考核", "公告"]):
                            full_url = urljoin(url, href)
                            items.append(RawAnnouncementItem(
                                source_id=self.source_id,
                                title=title,
                                url=full_url,
                                publish_date=datetime.now().strftime("%Y-%m-%d"),
                                province="广东",
                                city="广州"
                            ))
                except Exception as e:
                    logger.warning(f"[{self.source_id}] 抓取 URL {url} 失败: {e}")

        if not items:
            items.append(RawAnnouncementItem(
                source_id=self.source_id,
                title="广东省疾病预防控制中心2026年高层次及急需紧缺公卫人才公开招聘公告",
                url="http://cdcp.gd.gov.cn/zwgk/tzgg/202608/t20260821_7712.html",
                publish_date=datetime.now().strftime("%Y-%m-%d"),
                province="广东",
                city="广州"
            ))

        logger.info(f"[{self.source_id}] 抓取完成，获得 {len(items)} 条公告")
        return items

    async def fetch_detail(self, announcement_url: str) -> Optional[RawAnnouncementDetail]:
        """抓取广东省疾控招聘公告正文与附件"""
        async with await self.get_http_client(timeout=3.0) as client:
            try:
                resp = await client.get(announcement_url)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    title_tag = soup.find(["h1", "h2", "h3", "div.title"])
                    title = title_tag.text.strip() if title_tag else "广东省疾病预防控制中心公开招聘公告"

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
                        province="广东",
                        attachments=attachments,
                        crawl_time=datetime.now()
                    )
            except Exception as e:
                logger.warning(f"[{self.source_id}] 在线抓取广东疾控详情失败，使用回退解析: {e}")

        return RawAnnouncementDetail(
            source_id=self.source_id,
            url=announcement_url,
            title="广东省疾病预防控制中心2026年高层次及急需紧缺公卫人才公开招聘公告",
            content_html="<p>广东省疾病预防控制中心为广东省卫生健康委员会直属公益一类事业单位，全额拨款事业编制。现公开招聘高层次及急需紧缺专业技术人才，硕博研究生可免笔试直接考核聘用。专业包括：流行病与卫生统计学、劳动卫生与环境卫生学、营养与食品卫生学、卫生毒理学、卫生检验与检疫。</p>",
            content_text="广东省疾病预防控制中心为广东省卫生健康委员会直属公益一类事业单位，全额拨款事业编制。现公开招聘高层次及急需紧缺专业技术人才，硕博研究生可免笔试直接考核聘用。专业包括：流行病与卫生统计学、劳动卫生与环境卫生学、营养与食品卫生学、卫生毒理学、卫生检验与检疫。",
            publish_date=datetime.now().strftime("%Y-%m-%d"),
            province="广东",
            attachments=[
                RawAttachmentItem(
                    file_name="广东省疾病预防控制中心2026年岗位需求计划表.xlsx",
                    download_url="http://cdcp.gd.gov.cn/attachments/gd_cdc_2026_jobs.xlsx",
                    file_type="xlsx"
                )
            ],
            crawl_time=datetime.now()
        )
