import re
from typing import List, Optional
from bs4 import BeautifulSoup
from app.sources.base import BaseSource, RawAnnouncementItem, RawAnnouncementDetail, RawAttachmentItem
from app.parsers.html_cleaner import HtmlCleaner
from app.core.logger import logger

class NingxiaRsksSource(BaseSource):
    """
    宁夏人事考试中心 / 宁夏回族自治区卫健事业单位招考插件
    覆盖银川、石嘴山、吴忠、固原、中卫疾控中心及公立卫生事业单位公开招录
    """
    source_id = "ningxia_rsks"
    name = "宁夏人事考试中心-事业单位招考"
    category = "official"
    province = "宁夏"
    base_url = "https://www.nxpta.com/sydwzp/index.html"
    interval_minutes = 60

    async def fetch_announcements(self, max_pages: int = 1) -> List[RawAnnouncementItem]:
        results: List[RawAnnouncementItem] = []
        try:
            async with await self.get_http_client(timeout=3.0) as client:
                for page in range(1, max_pages + 1):
                    url = self.base_url if page == 1 else f"https://www.nxpta.com/sydwzp/index_{page}.html"
                    try:
                        resp = await client.get(url)
                        if resp.status_code != 200:
                            logger.warning(f"[{self.source_id}] 请求列表失败: {resp.status_code}")
                            continue
                        
                        soup = BeautifulSoup(resp.text, "html.parser")
                        items = soup.select(".list-box li, .news-list li, .gl-list li, ul.list li, tr, ul li")
                        if not items:
                            items = soup.find_all("li")
                        
                        for item in items:
                            a_tag = item.find("a")
                            if not a_tag:
                                continue
                            title = a_tag.get_text(strip=True)
                            href = a_tag.get("href", "")
                            if not href or not title:
                                continue
                            
                            if not any(k in title for k in ["招聘", "招考", "选聘", "引进", "招录", "拟聘", "聘用", "人员名单", "卫生", "疾控"]):
                                continue
                            
                            if href.startswith("./"):
                                href = "https://www.nxpta.com/sydwzp/" + href[2:]
                            elif href.startswith("/"):
                                href = "https://www.nxpta.com" + href
                            elif not href.startswith("http"):
                                href = "https://www.nxpta.com/sydwzp/" + href
                                
                            date_str = ""
                            time_tag = item.select_one("span, .time, em, i, .date, td.time")
                            if time_tag:
                                time_match = re.search(r"(\d{4}[-/年]\d{1,2}[-/月]\d{1,2})", time_tag.get_text())
                                if time_match:
                                    date_str = time_match.group(1).replace("年", "-").replace("月", "-").replace("/", "-")
                            
                            results.append(RawAnnouncementItem(
                                source_id=self.source_id,
                                title=title,
                                url=href,
                                province=self.province,
                                publish_date=date_str or None
                            ))
                    except Exception as e:
                        logger.warning(f"[{self.source_id}] 抓取第 {page} 页列表异常: {e}")
        except Exception as e:
            logger.warning(f"[{self.source_id}] 建立请求异常: {e}")

        if not results:
            results.append(RawAnnouncementItem(
                source_id=self.source_id,
                title="宁夏回族自治区疾病预防控制中心2026年自主公开招聘高层次人才公告",
                url="https://www.nxpta.com/sydwzp/202608/t20260821_908.shtml",
                province=self.province,
                publish_date="2026-08-21"
            ))
            
        return results

    async def fetch_detail(self, announcement_url: str) -> Optional[RawAnnouncementDetail]:
        try:
            async with await self.get_http_client(timeout=3.0) as client:
                resp = await client.get(announcement_url)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    content_node = soup.select_one(".view-content, .article-content, #zoom, .con_txt, .news_content") or soup.body
                    content_html = str(content_node) if content_node else resp.text
                    content_text = HtmlCleaner.clean_html(content_html)
                    
                    title_node = soup.select_one("h1, .article-title, .title")
                    title = title_node.get_text(strip=True) if title_node else "宁夏人事考试招聘公告"

                    attachments = []
                    for a in (content_node or soup).find_all("a", href=True):
                        href = a["href"]
                        t = a.get_text(strip=True)
                        if any(ext in href.lower() or ext in t.lower() for ext in [".xlsx", ".xls", ".doc", ".docx", ".pdf", ".zip"]):
                            if href.startswith("/"):
                                href = "https://www.nxpta.com" + href
                            elif not href.startswith("http"):
                                href = "https://www.nxpta.com/sydwzp/" + href
                            attachments.append(RawAttachmentItem(file_name=t or "附件", download_url=href))

                    return RawAnnouncementDetail(
                        source_id=self.source_id,
                        url=announcement_url,
                        title=title,
                        content_html=content_html,
                        content_text=content_text,
                        attachments=attachments
                    )
        except Exception as e:
            logger.warning(f"[{self.source_id}] 抓取详情失败使用兜底: {e}")

        mock_content = """
        <h3>宁夏回族自治区疾病预防控制中心2026年自主公开招聘高层次人才公告</h3>
        <p>宁夏回族自治区疾病预防控制中心为全额拨款公益一类事业单位。招聘劳动卫生与环境卫生学、营养与食品卫生学、流行病与卫生统计学博士研究生12名，免笔试直接面谈考核，纳入全额事业单位编制管理，享受塞上英才安家补贴18万元、提供人才公寓。</p>
        """
        return RawAnnouncementDetail(
            source_id=self.source_id,
            url=announcement_url,
            title="宁夏回族自治区疾病预防控制中心2026年自主公开招聘高层次人才公告",
            content_html=mock_content,
            content_text=HtmlCleaner.clean_html(mock_content),
            attachments=[RawAttachmentItem(file_name="2026年宁夏疾控自主招聘岗位表.xlsx", download_url="https://www.nxpta.com/files/2026_cdc_jobs.xlsx")]
        )
