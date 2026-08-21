import re
from typing import List, Optional
from bs4 import BeautifulSoup
from app.sources.base import BaseSource, RawAnnouncementItem, RawAnnouncementDetail, RawAttachmentItem
from app.parsers.html_cleaner import HtmlCleaner
from app.core.logger import logger

class JiangxiWsjkwSource(BaseSource):
    """
    江西省卫生健康委员会 / 江西省疾控及公卫事业单位招考插件
    覆盖江西省疾控中心、南昌市及各设区市疾控机构招考
    """
    source_id = "jiangxi_wsjkw"
    name = "江西省卫生健康委员会-人事人才"
    category = "official"
    province = "江西"
    base_url = "http://hc.jiangxi.gov.cn/col/col38139/index.html"
    interval_minutes = 60

    async def fetch_announcements(self, max_pages: int = 1) -> List[RawAnnouncementItem]:
        results: List[RawAnnouncementItem] = []
        async with await self.get_http_client() as client:
            for page in range(1, max_pages + 1):
                url = self.base_url if page == 1 else f"http://hc.jiangxi.gov.cn/col/col38139/index.html?uid=123&pageNum={page}"
                try:
                    resp = await client.get(url)
                    if resp.status_code != 200:
                        logger.warning(f"[{self.source_id}] 请求失败: {resp.status_code}")
                        continue
                    
                    soup = BeautifulSoup(resp.text, "html.parser")
                    items = soup.select(".default_pgContainer li, .news_list li, .list-box li, ul li")
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
                        
                        if not any(k in title for k in ["招聘", "招考", "选聘", "引进", "招录", "拟聘", "聘用", "遴选"]):
                            continue
                        
                        if href.startswith("./"):
                            href = "http://hc.jiangxi.gov.cn/col/col38139/" + href[2:]
                        elif href.startswith("/"):
                            href = "http://hc.jiangxi.gov.cn" + href
                        elif not href.startswith("http"):
                            href = "http://hc.jiangxi.gov.cn/col/col38139/" + href
                            
                        date_str = ""
                        time_tag = item.select_one("span, .time, em, i, .date")
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
                    logger.error(f"[{self.source_id}] 抓取第 {page} 页异常: {e}")
                    
        return results

    async def fetch_detail(self, announcement_url: str) -> Optional[RawAnnouncementDetail]:
        try:
            async with await self.get_http_client() as client:
                resp = await client.get(announcement_url)
                if resp.status_code != 200:
                    return None
                soup = BeautifulSoup(resp.text, "html.parser")
                content_node = soup.select_one(".view-content, .article-content, #zoom, .con_txt, .news_content") or soup.body
                content_html = str(content_node) if content_node else resp.text
                content_text = HtmlCleaner.clean_html(content_html)
                
                title_node = soup.select_one("h1, .article-title, .title")
                title = title_node.get_text(strip=True) if title_node else "江西省卫健委招聘公告"

                attachments = []
                for a in (content_node or soup).find_all("a", href=True):
                    href = a["href"]
                    t = a.get_text(strip=True)
                    if any(ext in href.lower() or ext in t.lower() for ext in [".xlsx", ".xls", ".doc", ".docx", ".pdf", ".zip"]):
                        if href.startswith("/"):
                            href = "http://hc.jiangxi.gov.cn" + href
                        elif not href.startswith("http"):
                            href = "http://hc.jiangxi.gov.cn/col/col38139/" + href
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
            logger.error(f"[{self.source_id}] 抓取详情异常: {e}")
            return None
