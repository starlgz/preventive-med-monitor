import re
from datetime import datetime, date
from typing import Optional, Dict, Any, Tuple
from app.core.logger import logger

class DeadlineDetector:
    """
    招考公告与岗位报名时效/截止日期检测器
    用于从公告标题、正文及附件中提取发布时间、报名起止时间，并研判是否已过期
    """

    DATE_PATTERN_RANGE = [
        # 2026年8月20日 09:00 至 2026年8月30日 17:00 或 2026-08-20 至 2026-08-30
        r'([0-9]{4}[-/年][0-9]{1,2}[-/月][0-9]{1,2}日?)(?:\s*[0-9]{1,2}:[0-9]{1,2})?\s*(?:至|到|-|—|~)\s*([0-9]{4}[-/年][0-9]{1,2}[-/月][0-9]{1,2}日?|[0-9]{1,2}月[0-9]{1,2}日?)',
    ]

    DEADLINE_PATTERNS = [
        r'(?:报名截止时间|截止报名时间|报名截至|报名截止|截止时间为|截止至|截至)[:：\s]*([0-9]{4}年[0-9]{1,2}月[0-9]{1,2}日?|[0-9]{4}-[0-9]{1,2}-[0-9]{1,2})',
        r'([0-9]{4}年[0-9]{1,2}月[0-9]{1,2}日?|[0-9]{4}-[0-9]{1,2}-[0-9]{1,2})\s*(?:前报名|截止|报名结束)'
    ]

    PUB_PATTERNS = [
        r'(?:发布时间|发布日期|发文日期)[:：\s]*([0-9]{4}年[0-9]{1,2}月[0-9]{1,2}日?|[0-9]{4}-[0-9]{1,2}-[0-9]{1,2})',
        r'([0-9]{4}年[0-9]{1,2}月[0-9]{1,2}日)'
    ]

    @classmethod
    def normalize_date(cls, date_str: Optional[str], default_year: int = 2026) -> Optional[date]:
        """将各类日期字符串统一转为 date 对象"""
        if not date_str:
            return None
        date_str = date_str.strip()
        date_str = date_str.split()[0]

        if re.match(r'^[0-9]{1,2}月[0-9]{1,2}日?$', date_str):
            date_str = f"{default_year}年{date_str}"
        
        clean = date_str.replace("年", "-").replace("月", "-").replace("日", "").replace("/", "-").replace(".", "-")
        parts = clean.split("-")
        if len(parts) == 3:
            try:
                y = int(parts[0])
                m = int(parts[1])
                d = int(parts[2])
                return date(y, m, d)
            except Exception:
                return None
        return None

    @classmethod
    def extract_time_meta(cls, title: str, content: str) -> Dict[str, Any]:
        """
        从标题和正文提取发布日期与报名起止时间
        """
        text = (content or "")[:3000]
        pub_date: Optional[date] = None
        start_date: Optional[date] = None
        end_date: Optional[date] = None

        # 1. 提取发布日期
        for p in cls.PUB_PATTERNS:
            m = re.search(p, text)
            if m:
                pub_date = cls.normalize_date(m.group(1))
                if pub_date:
                    break

        # 2. 提取起止报名时间
        for p in cls.DATE_PATTERN_RANGE:
            m = re.search(p, text)
            if m:
                s_str = m.group(1)
                e_str = m.group(2)
                start_date = cls.normalize_date(s_str)
                # 处理如果结束时间只有月日
                if not re.match(r'^[0-9]{4}', e_str) and start_date:
                    end_date = cls.normalize_date(f"{start_date.year}年{e_str}")
                else:
                    end_date = cls.normalize_date(e_str)
                if start_date or end_date:
                    break

        # 3. 如果未匹配到起止范围，尝试匹配单一截止时间
        if not end_date:
            for p in cls.DEADLINE_PATTERNS:
                m = re.search(p, text)
                if m:
                    end_date = cls.normalize_date(m.group(1))
                    if end_date:
                        break

        # 4. 从标题兜底研判年份/月份 (如 2025年公告)
        if not pub_date:
            title_m = re.search(r'(202[0-9])年', title)
            if title_m:
                y = int(title_m.group(1))
                pub_date = date(y, 1, 1)

        return {
            "publish_date": pub_date,
            "apply_start_date": start_date,
            "apply_end_date": end_date
        }

    @classmethod
    def is_expired(cls, pub_date: Optional[date], end_date: Optional[date], current_date: Optional[date] = None) -> bool:
        """
        研判是否已过期:
        1. 如果有明确报名截止日 end_date，且 end_date < 当前日期 -> 过期
        2. 如果无截止日但有发布日期 pub_date：
           - 若发布日期早于当前日期 60 天以上 -> 默认已过报名期
        3. 若发布年份早于当前年份 (如 2025 年及以前) -> 过期
        """
        today = current_date or date.today()

        if end_date:
            return end_date < today

        if pub_date:
            # 年份过期
            if pub_date.year < today.year:
                return True
            # 发布已超过 60 天
            delta_days = (today - pub_date).days
            if delta_days > 60:
                return True

        return False

    @classmethod
    def check_announcement_deadline(cls, title: str, pub_date_val: Any, content: str) -> Tuple[str, Optional[str]]:
        """
        综合判断公告状态 ('ACTIVE' 或 'EXPIRED')
        """
        today = date.today()
        # 统一处理 pub_date
        pub_d: Optional[date] = None
        if isinstance(pub_date_val, str) and pub_date_val:
            pub_d = cls.normalize_date(pub_date_val)
        elif isinstance(pub_date_val, datetime):
            pub_d = pub_date_val.date()
        elif isinstance(pub_date_val, date):
            pub_d = pub_date_val

        meta = cls.extract_time_meta(title, content or "")
        final_pub = pub_d or meta["publish_date"]
        final_end = meta["apply_end_date"]

        expired = cls.is_expired(final_pub, final_end, today)
        return ("EXPIRED" if expired else "ACTIVE", final_end.strftime("%Y-%m-%d") if final_end else (final_pub.strftime("%Y-%m-%d") if final_pub else None))
