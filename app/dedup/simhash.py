import re
import hashlib
from typing import List, Dict, Any, Tuple

class SimHashDedup:
    """
    SimHash 文本指纹计算与公告延期/变更检测引擎
    """
    
    @classmethod
    def _tokenize(cls, text: str) -> List[str]:
        """中文分词与 N-gram 特征提取"""
        # 清除标点与空白
        clean = re.sub(r'[^\w\u4e00-\u9fa5]', '', text)
        if not clean:
            return []
        # 2-gram 窗口特征
        tokens = [clean[i:i+2] for i in range(len(clean) - 1)]
        return tokens or [clean]

    @classmethod
    def compute_simhash(cls, text: str, bit_size: int = 64) -> int:
        """计算文本的 64 位 SimHash 指纹"""
        tokens = cls._tokenize(text)
        if not tokens:
            return 0

        v = [0] * bit_size
        for token in tokens:
            # MD5 哈希作为特征基底
            h = int(hashlib.md5(token.encode('utf-8')).hexdigest(), 16)
            for i in range(bit_size):
                bit = (h >> i) & 1
                if bit:
                    v[i] += 1
                else:
                    v[i] -= 1

        fingerprint = 0
        for i in range(bit_size):
            if v[i] > 0:
                fingerprint |= (1 << i)
        return fingerprint

    @classmethod
    def hamming_distance(cls, hash1: int, hash2: int, bit_size: int = 64) -> int:
        """计算两个 SimHash 指纹的海明距离"""
        x = (hash1 ^ hash2) & ((1 << bit_size) - 1)
        return bin(x).count('1')

    @classmethod
    def similarity(cls, text1: str, text2: str) -> float:
        """计算两段文本的归一化相似度 (0.0 ~ 1.0)"""
        h1 = cls.compute_simhash(text1)
        h2 = cls.compute_simhash(text2)
        dist = cls.hamming_distance(h1, h2)
        return round(1.0 - (dist / 64.0), 3)

    @classmethod
    def detect_announcement_change(
        cls,
        old_title: str,
        old_text: str,
        new_title: str,
        new_text: str
    ) -> Dict[str, Any]:
        """
        检测新公告是否为既有公告的变更/延期/补充公告
        """
        change_keywords = ["延期", "变更", "补充", "更正", "修改", "调整", "核减", "取消"]
        has_change_kw = any(kw in new_title for kw in change_keywords)
        
        sim = cls.similarity(old_text, new_text)
        
        # 命中变更词且相似度较高，确认为追踪延期变更
        if has_change_kw and sim >= 0.70:
            return {
                "is_update": True,
                "update_type": "延期/变更/补充公告",
                "similarity": sim,
                "reason": f"命中变更关键词且正文 SimHash 相似度高达 {sim}，确认为招考变更/延期追踪"
            }
        elif sim >= 0.90:
            return {
                "is_update": True,
                "update_type": "重复发布/微调公告",
                "similarity": sim,
                "reason": f"正文 SimHash 相似度为 {sim}，属于多源重复抓取或内容微调"
            }
        
        return {
            "is_update": False,
            "update_type": "独立新公告",
            "similarity": sim,
            "reason": "未命中强相似或变更特征，属于独立公告"
        }
