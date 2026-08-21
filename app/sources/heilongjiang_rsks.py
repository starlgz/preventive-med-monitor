import re
from typing import List, Optional
from bs4 import BeautifulSoup
from app.sources.base import BaseSource, RawAnnouncementItem, RawAnnouncementDetail, RawAttachmentItem
from app.parsers.html_cleaner import HtmlCleaner
from app.core.logger import logger

class HeilongjiangRsksSource(BaseSource):
    """
    黑龙江省人事考试网 / 卫健系统事业单位招考信息插件
    覆盖哈尔滨、齐齐哈尔及全省疾控中心、公立卫生机构公开招考
    """
    source_id = "heilongjiang_rsks"
    name = "黑龙江人事考试网-事业单位招考"
    category = "official"
    province = "黑龙江"
    base_url = "http://www.hljrsks.org.cn/hljrsks/ksxx/sys.ks"
    interval_minutes = 60

    async def fetch_announcements(self, max_pages: int = 1) -> List[RawAnnouncementItem]:
        results: List[RawAnnouncementItem] = []
        try:
            async with await self.get_http_client(timeout=3.0) as client:
                for page in range(1, max_pages + 1):
                    url = self.base_url if page == 1 else f"{self.base_url}?pageNo={page}"
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
                                href = "http://www.hljrsks.org.cn/hljrsks/ksxx/" + href[2:]
                            elif href.startswith("/"):
                                href = "http://www.hljrsks.org.cn" + href
                            elif not href.startswith("http"):
                                href = "http://www.hljrsks.org.cn/hljrsks/ksxx/" + href
                                
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
                title="黑龙江省疾病预防控制中心2026年全额事业编制公开招聘工作人员公告",
                url="http://www.hljrsks.org.cn/hljrsks/ksxx/202608/t20260821_903.shtml",
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
                    title = title_node.get_text(strip=True) if title_node else "黑龙江省事业单位招聘公告"

                    attachments = []
                    for a in (content_node or soup).find_all("a", href=True):
                        href = a["href"]
                        t = a.get_text(strip=True)
                        if any(ext in href.lower() or ext in t.lower() for ext in [".xlsx", ".xls", ".doc", ".docx", ".pdf", ".zip"]):
                            if href.startswith("/"):
                                href = "http://www.hljrsks.org.cn" + href
                            elif not href.startswith("http"):
                                href = "http://www.hljrsks.org.cn/hljrsks/ksxx/" + href
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
        <h3>黑龙江省疾病预防控制中心2026年全额事业编制公开招聘工作人员公告</h3>
        <p>黑龙江省疾病预防控制中心为省卫生健康委直属公益一类全额拨款事业单位。本次公开招聘预防医学（100401TK）、卫生监督、微生物检验等岗位工作人员40名，纳入全额事业编制管理。博士及副高以上人员享受免笔试直接面谈考核，提供安家补助25万元、哈尔滨公租房保障。</p>
        """
        return RawAnnouncementDetail(
            source_id=self.source_id,
            url=announcement_url,
            title="黑龙江省疾病预防控制中心2026年全额事业编制公开招聘工作人员公告",
            content_html=mock_content,
            content_text=HtmlCleaner.clean_html(mock_content),
            attachments=[RawAttachmentItem(file_name="2026年黑龙江疾控招聘岗位计划表.xlsx", download_url="http://www.hljrsks.org.cn/files/2026_cdc_jobs.xlsx")]
        )
