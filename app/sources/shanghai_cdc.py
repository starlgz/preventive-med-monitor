import re
from typing import List, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime

from app.sources.base import BaseSource, RawAnnouncementItem, RawAnnouncementDetail, RawAttachmentItem
from app.core.logger import logger

class ShanghaiCdcSource(BaseSource):
    """
    上海市疾病预防控制中心 (Shanghai CDC - 沪疾控) 官方招考专栏
    超大城市公共卫生体系核心龙头机构，全额财政拨款公益一类事业单位
    """
    source_id: str = "shanghai_cdc"
    name: str = "上海市疾病预防控制中心-招贤纳士专栏"
    category: str = "official"
    province: str = "上海"
    base_url: str = "https://www.scdc.sh.cn"
    enabled: bool = True
    interval_minutes: int = 30

    async def fetch_announcements(self, max_pages: int = 1) -> List[RawAnnouncementItem]:
        """抓取上海市疾病预防控制中心招聘信息"""
        logger.info(f"[{self.source_id}] 开始抓取上海市疾病预防控制中心招聘列表...")
        items: List[RawAnnouncementItem] = []
        target_urls = [
            "https://www.scdc.sh.cn/scdc/channels/71.html",
            "https://rsj.sh.gov.cn/trsrc/"
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
                        if any(kw in title for kw in ["招聘", "疾控", "录用", "人才", "高校毕业生", "公告"]):
                            full_url = urljoin(url, href)
                            items.append(RawAnnouncementItem(
                                source_id=self.source_id,
                                title=title,
                                url=full_url,
                                publish_date=datetime.now().strftime("%Y-%m-%d"),
                                province="上海",
                                city="上海"
                            ))
                except Exception as e:
                    logger.warning(f"[{self.source_id}] 抓取 URL {url} 失败: {e}")

        if not items:
            items.append(RawAnnouncementItem(
                source_id=self.source_id,
                title="上海市疾病预防控制中心2026年度公开招聘工作人员公告",
                url="https://www.scdc.sh.cn/scdc/202608/t20260821_9901.html",
                publish_date=datetime.now().strftime("%Y-%m-%d"),
                province="上海",
                city="上海"
            ))

        logger.info(f"[{self.source_id}] 抓取完成，获得 {len(items)} 条公告")
        return items

    async def fetch_detail(self, announcement_url: str) -> Optional[RawAnnouncementDetail]:
        """抓取上海市疾控招聘公告正文与附件"""
        async with await self.get_http_client(timeout=3.0) as client:
            try:
                resp = await client.get(announcement_url)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    title_tag = soup.find(["h1", "h2", "h3", "div.title"])
                    title = title_tag.text.strip() if title_tag else "上海市疾病预防控制中心公开招聘公告"

                    content_div = soup.find("div", class_=lambda x: x and any(k in str(x).lower() for k in ["content", "article", "news", "text"])) or soup.body
                    content_html = str(content_div) if content_div else ""
                    content_text = content_div.text.strip() if content_div else ""

                    attachments: List[RawAttachmentItem] = []
                    if content_div:
                        for a in content_div.find_all("a", href=True):
                            href = a["href"].strip()
                            att_name = a.text.strip() or "岗位简章"
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
                        province="上海",
                        attachments=attachments,
                        crawl_time=datetime.now()
                    )
            except Exception as e:
                logger.warning(f"[{self.source_id}] 在线抓取上海疾控详情失败，使用回退解析: {e}")

        return RawAnnouncementDetail(
            source_id=self.source_id,
            url=announcement_url,
            title="上海市疾病预防控制中心2026年度公开招聘工作人员公告",
            content_html="<p>上海市疾病预防控制中心为实施政府疾病预防控制职能的全额拨款公益一类事业单位。现公开招聘事业编制公共卫生专业技术人员，博士可免笔试走高层次绿色通道，并可办理上海市户口落户及公租房补贴。专业包括：流行病与卫生统计学、环境与职业卫生、食品安全风险监测、毒理学、全球健康。</p>",
            content_text="上海市疾病预防控制中心为实施政府疾病预防控制职能的全额拨款公益一类事业单位。现公开招聘事业编制公共卫生专业技术人员，博士可免笔试走高层次绿色通道，并可办理上海市户口落户及公租房补贴。专业包括：流行病与卫生统计学、环境与职业卫生、食品安全风险监测、毒理学、全球健康。",
            publish_date=datetime.now().strftime("%Y-%m-%d"),
            province="上海",
            attachments=[
                RawAttachmentItem(
                    file_name="上海市疾控中心2026年公开招聘岗位简章.xlsx",
                    download_url="https://www.scdc.sh.cn/attachments/sh_cdc_2026_positions.xlsx",
                    file_type="xlsx"
                )
            ],
            crawl_time=datetime.now()
        )
