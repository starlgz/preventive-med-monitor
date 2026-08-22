import asyncio
import os
import re
import httpx
from bs4 import BeautifulSoup
from datetime import datetime
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models.entities import Announcement, Job, Attachment, Source, CrawlLog
from app.parsers.attachment_downloader import AttachmentDownloader
from app.parsers.dispatcher import ParserDispatcher
from app.extractors.service import JobExtractionService
from app.rules.matcher_service import MajorMatcherService
from app.rules.bianzhi_service import BianzhiService
from app.rules.priority_service import PriorityService
from app.core.logger import logger

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

CHANNELS = [
    ("全国医疗卫生", "https://www.shiyebian.com/yiliaoweisheng/"),
    ("全国最新招聘", "https://www.shiyebian.com/xinxi/"),
    ("北京", "https://www.shiyebian.com/beijing/"),
    ("山东", "https://www.shiyebian.com/shandong/"),
    ("广东", "https://www.shiyebian.com/guangdong/"),
    ("江苏", "https://www.shiyebian.com/jiangsu/"),
    ("浙江", "https://www.shiyebian.com/zhejiang/"),
    ("河南", "https://www.shiyebian.com/henan/"),
    ("四川", "https://www.shiyebian.com/sichuan/"),
    ("湖北", "https://www.shiyebian.com/hubei/"),
    ("湖南", "https://www.shiyebian.com/hunan/"),
    ("河北", "https://www.shiyebian.com/hebei/"),
    ("陕西", "https://www.shiyebian.com/shanxi/"),
    ("安徽", "https://www.shiyebian.com/anhui/"),
    ("福建", "https://www.shiyebian.com/fujian/"),
    ("辽宁", "https://www.shiyebian.com/liaoning/"),
    ("黑龙江", "https://www.shiyebian.com/heilongjiang/"),
    ("吉林", "https://www.shiyebian.com/jilin/"),
    ("江西", "https://www.shiyebian.com/jiangxi/"),
    ("广西", "https://www.shiyebian.com/guangxi/"),
    ("云南", "https://www.shiyebian.com/yunnan/"),
    ("贵州", "https://www.shiyebian.com/guizhou/"),
    ("重庆", "https://www.shiyebian.com/chongqing/"),
    ("天津", "https://www.shiyebian.com/tianjin/"),
    ("上海", "https://www.shiyebian.com/shanghai/"),
    ("山西", "https://www.shiyebian.com/sx/"),
    ("内蒙古", "https://www.shiyebian.com/neimenggu/"),
    ("甘肃", "https://www.shiyebian.com/gansu/"),
    ("青海", "https://www.shiyebian.com/qinghai/"),
    ("宁夏", "https://www.shiyebian.com/ningxia/"),
    ("新疆", "https://www.shiyebian.com/xinjiang/"),
    ("海南", "https://www.shiyebian.com/hainan/")
]

def infer_province(title: str, ch_name: str) -> str:
    provinces = ["北京", "天津", "上海", "重庆", "河北", "山西", "辽宁", "吉林", "黑龙江", "江苏", "浙江", "安徽", "福建", "江西", "山东", "河南", "湖北", "湖南", "广东", "海南", "四川", "贵州", "云南", "陕西", "甘肃", "青海", "台湾", "内蒙古", "广西", "西藏", "宁夏", "新疆"]
    for p in provinces:
        if p in title:
            return p
    if ch_name in provinces:
        return ch_name
    return "全国"

async def fetch_channel_links(client: httpx.AsyncClient, ch_name: str, ch_url: str):
    items = []
    try:
        r = await client.get(ch_url, timeout=10.0)
        if r.status_code != 200:
            return items
        soup = BeautifulSoup(r.text, "html.parser")
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            title = a.get_text(strip=True)
            if not href or not title or len(title) < 5:
                continue
            if "/xinxi/" in href and href.endswith(".html") and not href.endswith("zhinan.html") and not href.endswith("index.html"):
                if href.startswith("/"):
                    full_url = "https://www.shiyebian.com" + href
                elif href.startswith("http"):
                    full_url = href
                else:
                    full_url = "https://www.shiyebian.com/xinxi/" + href
                
                province = infer_province(title, ch_name)
                items.append({
                    "title": title,
                    "url": full_url,
                    "province": province
                })
    except Exception as e:
        logger.warning(f"Error fetching channel {ch_name} ({ch_url}): {e}")
    return items

async def fetch_detail_page(client: httpx.AsyncClient, url: str):
    try:
        r = await client.get(url, timeout=10.0)
        if r.status_code != 200:
            return None
        soup = BeautifulSoup(r.text, "html.parser")
        
        # 找正文
        content_div = soup.find("div", class_="ws-content-text") or soup.find("div", class_="ws-content") or soup.find("div", class_="content")
        text = content_div.get_text(separator="\n", strip=True) if content_div else ""
        
        # 找附件
        attachments = []
        if content_div:
            for a in content_div.find_all("a", href=True):
                href = a["href"].strip()
                name = a.get_text(strip=True)
                # 过滤题库等宣传链接
                if "ziliao" in href or "tiku" in href or "app" in href or not name:
                    continue
                
                is_att = any(ext in href.lower() or ext in name.lower() for ext in [".xls", ".xlsx", ".doc", ".docx", ".pdf", ".zip", ".rar", "download.php"])
                if is_att:
                    if href.startswith("/"):
                        full_att_url = "https://www.shiyebian.com" + href
                    elif href.startswith("http"):
                        full_att_url = href
                    else:
                        full_att_url = "https://www.shiyebian.com/" + href
                    
                    # 确定后缀
                    ext = ".xls"
                    for candidate in [".xlsx", ".xls", ".docx", ".doc", ".pdf", ".zip", ".rar"]:
                        if candidate in href.lower() or candidate in name.lower():
                            ext = candidate
                            break
                    
                    attachments.append({
                        "file_name": name,
                        "download_url": full_att_url,
                        "file_type": ext
                    })
        return {
            "content_text": text,
            "attachments": attachments
        }
    except Exception as e:
        logger.warning(f"Error fetching detail {url}: {e}")
        return None

async def run():
    logger.info("🚀 开始执行仅限 https://www.shiyebian.com/ 的深度采集与岗位提取...")
    
    async with AsyncSessionLocal() as session:
        # 1. 禁用所有其他数据源，仅激活 shiyebian_national
        await session.execute(update(Source).values(is_active=0))
        await session.execute(update(Source).where(Source.source_id == "shiyebian_national").values(is_active=1))
        await session.commit()
    
    limits = httpx.Limits(max_keepalive_connections=20, max_connections=30)
    async with httpx.AsyncClient(headers=HEADERS, limits=limits, follow_redirects=True) as client:
        # 2. 收集所有频道公告链接
        all_items_dict = {}
        for ch_name, ch_url in CHANNELS:
            items = await fetch_channel_links(client, ch_name, ch_url)
            for it in items:
                all_items_dict[it["url"]] = it
            logger.info(f"[{ch_name}] 发现 {len(items)} 条公告链接，去重总计: {len(all_items_dict)} 条")

        logger.info(f"📊 共汇总 {len(all_items_dict)} 篇公告，开始并发拉取详情与附件...")

        # 3. 逐篇存入公告表并下载附件
        saved_annos = 0
        new_jobs_count = 0
        
        async with AsyncSessionLocal() as session:
            for idx, (url, it) in enumerate(all_items_dict.items(), start=1):
                existing = (await session.execute(select(Announcement).where(Announcement.url == url))).scalars().first()
                if existing:
                    anno_id = existing.id
                else:
                    detail = await fetch_detail_page(client, url)
                    content_raw = detail["content_text"] if detail else ""
                    anno = Announcement(
                        source_id="shiyebian_national",
                        title=it["title"],
                        url=url,
                        province=it["province"],
                        content_raw=content_raw,
                        is_processed=0
                    )
                    session.add(anno)
                    await session.flush()
                    anno_id = anno.id
                    saved_annos += 1
                    
                    if detail and detail["attachments"]:
                        for att_info in detail["attachments"]:
                            # 下载附件
                            dl_res = await AttachmentDownloader.download_file(att_info["download_url"], att_info["file_name"])
                            att_obj = Attachment(
                                announcement_id=anno_id,
                                file_name=att_info["file_name"],
                                file_type=att_info["file_type"],
                                file_url=att_info["download_url"],
                                local_path=dl_res["local_path"] if dl_res else None,
                                parse_status="PARSED" if dl_res else "DOWNLOAD_FAILED"
                            )
                            session.add(att_obj)
                        await session.flush()

                # 4. 解析岗位
                try:
                    res = await JobExtractionService.extract_and_save_jobs(session, anno_id)
                    new_jobs_count += res.get("new_saved", 0)
                except Exception as e:
                    logger.warning(f"解析岗位失败 (anno_id={anno_id}): {e}")

                if idx % 50 == 0:
                    await session.commit()
                    logger.info(f"⏳ 进度 [{idx}/{len(all_items_dict)}] - 已存公告: {saved_annos}, 提取岗位: {new_jobs_count}")
            
            await session.commit()
            logger.info(f"✅ 抓取与岗位抽取完成！新增公告: {saved_annos}, 新增岗位: {new_jobs_count}")

            # 5. 执行预防医学五星评级与编制三色研判流水线
            logger.info("⭐ 正在进行预防医学专业匹配与星级打分...")
            m_res = await MajorMatcherService.run_batch_match(session)
            logger.info(f"专业匹配完成: {m_res}")

            logger.info("🟢🟡🔴 正在进行编制三色研判与置信度评估...")
            b_res = await BianzhiService.run_batch_evaluation(session)
            logger.info(f"编制研判完成: {b_res}")

            logger.info("🎯 正在进行优先级划分...")
            p_res = await PriorityService.run_batch_priority_evaluation(session)
            logger.info(f"优先级划分完成: {p_res}")

            await session.commit()

        logger.info("🎉 事业单位招聘考试网 (shiyebian.com) 全量抓取与结构化入库流程圆满完成！")

if __name__ == "__main__":
    asyncio.run(run())
