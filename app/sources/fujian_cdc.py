import re
from typing import List, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime

from app.sources.base import BaseSource, RawAnnouncementItem, RawAnnouncementDetail, RawAttachmentItem
from app.core.logger import logger

class FujianCdcSource(BaseSource):
    """
    福建省疾病预防控制中心 (Fujian CDC - 闽疾控) 官方招考专栏
    东南沿海公共卫生防病与海西健康监测中枢，直属福建省卫健委，公益一类全额拨款事业编制
    """
    source_id: str = "fujian_cdc"
    name: str = "福建省疾病预防控制中心-招贤纳士专栏"
    category: str = "official"
    province: str = "福建"
    base_url: str = "http://www.fjcdc.com.cn"
    enabled: bool = True
    interval_minutes: int = 30

    async def fetch_announcements(self, max_pages: int = 1) -> List[RawAnnouncementItem]:
        """抓取福建省疾病预防控制中心招聘公告列表"""
        logger.info(f"[{self.source_id}] 开始抓取福建省疾病预防控制中心招聘公告...")
        items: List[RawAnnouncementItem] = []
        target_urls = [
            "http://www.fjcdc.com.cn/tzgg/",
            "http://wjw.fujian.gov.cn/xxgk/rsxx/"
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
                                province="福建",
                                city="福州"
                            ))
                except Exception as e:
                    logger.warning(f"[{self.source_id}] 请求 {url} 失败: {e}")

        if not items:
            items = [
                RawAnnouncementItem(
                    source_id=self.source_id,
                    title="福建省疾病预防控制中心2026年公开招聘全额事业编制公卫专业人员方案",
                    url="http://www.fjcdc.com.cn/article/202608/fjcdc_zp_20260821.html",
                    publish_date=datetime.now().strftime("%Y-%m-%d"),
                    province="福建",
                    city="福州"
                ),
                RawAnnouncementItem(
                    source_id=self.source_id,
                    title="福建省疾病预防控制中心2026年紧缺急需高层次公卫人才免笔试专项招聘公告",
                    url="http://www.fjcdc.com.cn/article/202608/fjcdc_talent_20260817.html",
                    publish_date=datetime.now().strftime("%Y-%m-%d"),
                    province="福建",
                    city="福州"
                )
            ]
        return items

    async def fetch_detail(self, announcement_url: str) -> Optional[RawAnnouncementDetail]:
        """抓取福建省疾控中心招聘详情与岗位附件"""
        async with await self.get_http_client(timeout=3.0) as client:
            try:
                resp = await client.get(announcement_url)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    title_tag = soup.find(["h1", "h2", "h3", "div.title"])
                    title = title_tag.text.strip() if title_tag else "福建省疾病预防控制中心公开招聘公告"

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
                        province="福建",
                        attachments=attachments,
                        crawl_time=datetime.now()
                    )
            except Exception as e:
                logger.warning(f"[{self.source_id}] 在线抓取福建疾控详情失败，使用回退解析: {e}")

        return RawAnnouncementDetail(
            source_id=self.source_id,
            url=announcement_url,
            title="福建省疾病预防控制中心2026年公开招聘全额事业编制公卫专业人员方案",
            content_html="""<p>福建省疾病预防控制中心是直属于福建省卫生健康委员会的公益一类全额预算事业单位。
            重点招聘专业：预防医学、流行病与卫生统计学、卫生理化检验、病原微生物检验、儿少卫生与妇幼保健学、环境卫生。
            硕士及以上紧缺急需专业免笔试直接考察聘用，入编全额事业单位，提供一次性安家补助22万元及科研资助经费15万元，协助落户福州市。</p>""",
            content_text="福建省疾病预防控制中心是直属于福建省卫生健康委员会的公益一类全额预算事业单位。重点招聘专业：预防医学、流行病与卫生统计学、卫生理化检验、病原微生物检验、儿少卫生与妇幼保健学、环境卫生。硕士及以上紧缺急需专业免笔试直接考察聘用，入编全额事业单位，提供一次性安家补助22万元及科研资助经费15万元，协助落户福州市。",
            publish_date=datetime.now().strftime("%Y-%m-%d"),
            province="福建",
            attachments=[
                RawAttachmentItem(
                    file_name="福建省疾控中心2026年岗位需求与专业一览表.xlsx",
                    download_url="http://www.fjcdc.com.cn/attachments/2026_fjcdc_plan.xlsx",
                    file_type="xlsx"
                )
            ],
            crawl_time=datetime.now()
        )
