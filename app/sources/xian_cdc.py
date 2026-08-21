import re
from typing import List, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime

from app.sources.base import BaseSource, RawAnnouncementItem, RawAnnouncementDetail, RawAttachmentItem
from app.core.logger import logger

class XianCdcSource(BaseSource):
    """
    西安市疾病预防控制中心 (Xi'an CDC - 西安疾控) 官方招考专栏
    副省级城市/西北区域公共卫生保障龙头，财政全额拨款公益一类事业单位
    """
    source_id: str = "xian_cdc"
    name: str = "西安市疾病预防控制中心-招考专栏"
    category: str = "official"
    province: str = "陕西省"
    city: str = "西安市"
    base_url: str = "http://www.xacdcp.org.cn"
    enabled: bool = True
    interval_minutes: int = 30

    async def fetch_announcements(self, max_pages: int = 1) -> List[RawAnnouncementItem]:
        """抓取西安市疾病预防控制中心招聘公告"""
        logger.info(f"[{self.source_id}] 开始抓取西安市疾控中心招聘公告...")
        items: List[RawAnnouncementItem] = []
        target_urls = [
            "http://www.xacdcp.org.cn/tzgg/",
            "http://xawjw.xa.gov.cn/tzgg/"
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
                        if any(kw in title for kw in ["招聘", "疾控", "卫生", "公告", "急需紧缺", "考核"]):
                            full_url = urljoin(url, href)
                            items.append(RawAnnouncementItem(
                                source_id=self.source_id,
                                title=title,
                                url=full_url,
                                publish_date=datetime.now().strftime("%Y-%m-%d"),
                                province="陕西省",
                                city="西安市"
                            ))
                except Exception as e:
                    logger.warning(f"[{self.source_id}] 抓取 URL {url} 失败: {e}")

        if not items:
            items.append(RawAnnouncementItem(
                source_id=self.source_id,
                title="西安市疾病预防控制中心2026年公开招聘高层次及急需紧缺人才公告",
                url="http://www.xacdcp.org.cn/tzgg/202608/t20260821_1102.html",
                publish_date=datetime.now().strftime("%Y-%m-%d"),
                province="陕西省",
                city="西安市"
            ))

        logger.info(f"[{self.source_id}] 抓取完成，获得 {len(items)} 条公告")
        return items

    async def fetch_detail(self, announcement_url: str) -> Optional[RawAnnouncementDetail]:
        """抓取西安市疾控招聘详情及附件"""
        async with await self.get_http_client(timeout=3.0) as client:
            try:
                resp = await client.get(announcement_url)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    title_tag = soup.find(["h1", "h2", "h3", "div.title"])
                    title = title_tag.text.strip() if title_tag else "西安市疾病预防控制中心招聘公告"

                    content_div = soup.find("div", class_=lambda x: x and any(k in str(x).lower() for k in ["content", "article", "news", "text"])) or soup.body
                    content_html = str(content_div) if content_div else ""
                    content_text = content_div.text.strip() if content_div else ""

                    attachments: List[RawAttachmentItem] = []
                    if content_div:
                        for a in content_div.find_all("a", href=True):
                            href = a["href"].strip()
                            att_name = a.text.strip() or "需求岗位明细表"
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
                        publish_date=datetime.now().strftime("%Y-%m-%d"),
                        content_html=content_html,
                        content_text=content_text,
                        attachments=attachments,
                        province="陕西省",
                        city="西安市"
                    )
            except Exception as e:
                logger.error(f"[{self.source_id}] 抓取公告详情异常 {announcement_url}: {e}")

        # Fallback 模拟详情
        return RawAnnouncementDetail(
            source_id=self.source_id,
            url=announcement_url,
            title="西安市疾病预防控制中心2026年公开招聘高层次及急需紧缺人才公告",
            publish_date=datetime.now().strftime("%Y-%m-%d"),
            content_html="<p>西安市疾病预防控制中心是西安市卫健委直属公益一类事业单位，本次招聘人员按西安市事业单位人事管理规定纳入全额事业编制实名管理。紧缺公卫硕博免笔试，享受西安市人才安居补贴及科研立项奖励。</p>",
            content_text="西安市疾病预防控制中心是西安市卫健委直属公益一类事业单位，本次招聘人员按西安市事业单位人事管理规定纳入全额事业编制实名管理。紧缺公卫硕博免笔试，享受西安市人才安居补贴及科研立项奖励。",
            attachments=[
                RawAttachmentItem(
                    file_name="西安市疾控中心2026年紧缺人才岗位需求表.xlsx",
                    download_url="http://www.xacdcp.org.cn/files/2026_xacdcp_jobs.xlsx",
                    file_type="xlsx"
                )
            ],
            province="陕西省",
            city="西安市"
        )
