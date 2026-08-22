import re
from typing import Dict, Any, List, Optional, Tuple, Set
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.entities import MajorCatalog

class MajorMatcher:
    """教育部专业代码穿透匹配、AST 逻辑消歧与五星量化打分模型 2.0"""

    # 1. 教育部学科代码穿透映射 (本硕博双向穿透)
    # 本科 (2012/2020目录): 1004 公共卫生与预防医学类
    # 硕博 (2018/2026目录): 1004 公共卫生与预防医学, 1053 公共卫生(MPH)
    MAJOR_CODES_LEVEL_5 = {
        "100401K": "预防医学(本科国控)",
        "100401": "预防医学/流行病与卫生统计学",
        "100402": "劳动卫生与环境卫生学",
        "100403": "营养与食品卫生学",
        "100404": "儿少卫生与妇幼保健学",
        "100405": "卫生毒理学",
        "1004": "公共卫生与预防医学类/一级学科",
        "1053": "公共卫生硕士(MPH)",
        "105300": "公共卫生(专业硕士)",
        "100402TK": "食品卫生与营养学(本科)",
        "100403TK": "妇幼保健医学(本科)",
        "100404TK": "卫生监督(本科)",
        "100405TK": "全球健康学(本科)",
        "101007": "卫生检验与检疫(本科医学技术类)"
    }

    # 细分专业子学科关键词库定义 (用于证据链溯源与细分标签展示)
    SUB_DISCIPLINE_KEYWORDS = {
        "预防医学核心": ["预防医学", "公共卫生与预防医学", "公共卫生", "公卫医师", "MPH", "公共卫生硕士", "现场流行病学", "FETP"],
        "流行病与卫生统计学": ["流行病与卫生统计", "流行病学", "卫生统计学", "现场流调", "传染病流行病", "慢性病流行病", "分子流行病", "空间流行病", "临床流行病", "数字公卫", "动力学建模"],
        "劳动卫生与环境卫生学": ["劳动卫生与环境卫生", "劳动卫生", "环境卫生", "职业卫生", "职业病防治", "放射卫生", "环境健康", "职业健康监护", "辐射防护"],
        "营养与食品卫生学": ["营养与食品卫生", "食品营养", "食品卫生", "食品安全风险监测", "营养学", "膳食暴露评估", "公共营养"],
        "儿少卫生与妇幼保健学": ["儿少卫生", "妇幼保健", "母婴保健", "儿童保健", "学校卫生", "妇女保健", "生殖健康"],
        "卫生毒理学": ["卫生毒理", "毒理学", "毒物分析", "化学毒物检测", "毒理检验", "遗传毒理", "分子毒理", "环境毒理"],
        "卫生检验与检疫": ["卫生检验与检疫", "卫生检验", "理化检验", "微生物检验", "病原检验", "检验检疫", "水质理化", "空气理化", "食品理化检验"],
        "卫生监督与行政执法": ["卫生监督", "公共卫生监督", "医疗卫生监督", "卫生行政执法", "卫生法学"],
        "社会医学与卫生事业管理": ["社会医学", "卫生事业管理", "卫生政策", "医院管理", "卫生经济学", "健康政策与管理", "公卫事业管理"],
        "生物统计与健康大数据": ["生物统计学", "生物统计", "医学统计", "健康医疗大数据", "卫生信息学", "医学信息学", "空间流行病学"],
        "疾病控制与应急处置": ["疾病预防控制", "传染病防制", "慢病防制", "免疫规划", "计划免疫", "艾滋病防治", "结核病防治", "地方病防治", "突发公共卫生事件应急", "消毒与病媒生物防制", "院感控制"]
    }

    # 排除性/否定词上下文正则（用于消除歧义）
    EXCLUSION_CONTEXT_PATTERNS = [
        r"(?:除|不含|不包括|排除)[^，,；;。]*?(?:预防医学|公共卫生|公卫|卫生检验)",
        r"(?:仅限|只要|招收)[^，,；;。]*?(?:临床医学|口腔医学|中医学|护理学|非医学)[^，,；;。]*?(?:除外|不含公卫)",
        r"(?:临床医学|口腔医学|中西医结合|中医学|药学|护理学)[^，,；;。]*?\((?:不含预防|排除公卫)\)"
    ]

    # 一星明确排除专业（非医学或纯无关专业）
    NON_MEDICAL_EXCLUDES = [
        "会计", "财务管理", "审计", "汉语言文学", "文秘", "法学", "思想政治", "马克思主义",
        "计算机", "软件工程", "网络工程", "电气工程", "机械工程", "土木工程", "建筑学",
        "市场营销", "工商管理", "电子商务", "英语", "日语", "艺术设计", "音乐学", "体育学"
    ]

    # 单位类型权重加成 (CDC 与卫监所等核心单位权重更高)
    UNIT_TYPE_SCORES = {
        "疾控中心": 20,
        "卫生监督": 18,
        "妇幼保健院": 15,
        "急救中心": 15,
        "血站": 14,
        "综合医院": 12,
        "专科医院": 12,
        "社区卫生服务中心": 14,
        "乡镇卫生院": 12,
        "科研院所": 16,
        "其他事业单位": 10
    }

    @classmethod
    def parse_logic_and_clean(cls, text: str) -> Tuple[str, bool]:
        """
        AST 逻辑消歧：检测是否存在对公卫/预防医学的显式否定
        返回: (清洗后的文本, 是否被显式否定排除)
        """
        if not text:
            return "", False

        # 检查否定排除模式
        for pat in cls.EXCLUSION_CONTEXT_PATTERNS:
            if re.search(pat, text):
                return text, True

        return text, False

    @classmethod
    def match_major_codes(cls, text: str) -> List[Tuple[str, str]]:
        """提取文本中出现的教育部学科专业代码"""
        hits = []
        for code, name in cls.MAJOR_CODES_LEVEL_5.items():
            # 匹配独立代码（边界匹配避免误伤纯数字）
            if re.search(rf"(?<!\d){re.escape(code)}(?!\d)", text, re.IGNORECASE):
                hits.append((code, name))
        return hits

    @classmethod
    def calculate_match_score(
        cls, 
        major_raw: str, 
        unit_type: str = "其他事业单位", 
        job_name: str = "",
        unit_name: str = ""
    ) -> Dict[str, Any]:
        """
        五星智能打分量化模型 2.0:
        Score = S_专业(50%) + S_岗位(30%) + S_单位(20%)
        """
        text = (major_raw or "").strip()
        job_name = (job_name or "").strip()
        unit_name = (unit_name or "").strip()
        full_text = f"{text} {job_name} {unit_name}"

        evidence_chain = []
        matched_codes = []
        matched_keywords = []

        # 1. 逻辑消歧检测
        cleaned_text, is_negated = cls.parse_logic_and_clean(full_text)
        if is_negated:
            return {
                "match_level": 1,
                "match_score": 10,
                "matched_codes": [],
                "matched_keywords": ["检测到显式排除公卫/预防医学限制"],
                "match_reason": "专业要求中包含排除性条件（如明确注明不含预防医学/公卫类），判定为不相关",
                "evidence_chain": ["AST消歧引擎识别到否定排除句式"],
                "sub_disciplines": {}
            }

        # 2. 专业代码穿透匹配
        code_hits = cls.match_major_codes(cleaned_text)
        if code_hits:
            matched_codes = [c[0] for c in code_hits]
            for c, name in code_hits:
                evidence_chain.append(f"教育部学科代码精准穿透: {c} ({name})")

        # 3. 细分学科关键词扫描与证据提取
        sub_disciplines = {}
        for category, kws in cls.SUB_DISCIPLINE_KEYWORDS.items():
            hits = [kw for kw in kws if kw in full_text]
            if hits:
                sub_disciplines[category] = hits
                matched_keywords.extend(hits)

        matched_keywords = list(set(matched_keywords))

        # 4. 专业得分 S_专业 (满分 50)
        s_major = 0
        if matched_codes or any(kw in text for kw in ["预防医学", "公共卫生与预防医学", "公共卫生硕士", "MPH", "1004", "1053"]):
            s_major = 50
            evidence_chain.append("专业要求明确锁定预防医学/公卫核心学科 (满分50)")
        elif any(kw in text for kw in ["流行病", "卫生统计", "卫生检验", "食品卫生", "环境卫生", "劳动卫生", "妇幼保健", "妇幼保健医学", "儿少卫生", "卫生毒理", "卫生监督"]):
            s_major = 42
            evidence_chain.append("专业要求命中公卫二级学科/检验/毒理/流统 (得分42)")
        elif any(kw in text for kw in ["公共卫生类", "公卫类", "预防医学类", "医学检验", "卫生事业管理", "健康服务与管理", "社会医学"]):
            s_major = 32
            evidence_chain.append("专业要求为公卫大类/卫管/医学检验等相关学科 (得分32)")
        elif any(kw in text for kw in ["基础医学", "临床医学", "中西医结合", "医学类", "医药卫生类"]):
            s_major = 20
            evidence_chain.append("专业要求为大医学类不限 (得分20)")
        elif any(kw in text for kw in ["不限", "不限专业", "专业不限", "综合类"]):
            s_major = 12
            evidence_chain.append("专业要求不限专业 (得分12)")
        elif not text:
            # 专业未填写的兜底
            s_major = 15
            evidence_chain.append("专业要求未明确填写 (得分15)")
        else:
            # 检查是否命中纯无关专业
            if any(kw in text for kw in cls.NON_MEDICAL_EXCLUDES):
                s_major = 0
                evidence_chain.append("专业要求为完全非医学无关专业 (得分0)")
            else:
                s_major = 5
                evidence_chain.append("专业要求为其他未列明专业 (得分5)")

        # 5. 岗位得分 S_岗位 (满分 30)
        s_job = 0
        if any(kw in job_name for kw in ["公卫医师", "公共卫生医师", "流调", "现场流调", "慢病", "疾控", "应急处置", "传染病", "艾防", "结防", "地防", "理化检验", "微生物检验"]):
            s_job = 30
            evidence_chain.append(f"岗位名称 [{job_name}] 为疾控公卫核心专业业务岗 (满分30)")
        elif any(kw in job_name for kw in ["卫生监督", "公卫", "预防", "检验", "感控", "院感", "防保", "保健", "监测", "采样", "消杀"]):
            s_job = 22
            evidence_chain.append(f"岗位名称 [{job_name}] 为公卫防保/检验/院感相关岗 (得分22)")
        elif any(kw in job_name for kw in ["医师", "技师", "医生", "科研", "业务"]):
            s_job = 15
            evidence_chain.append(f"岗位名称 [{job_name}] 为通用医药卫生业务岗 (得分15)")
        else:
            s_job = 8
            evidence_chain.append(f"岗位名称 [{job_name}] 为通用综合岗 (得分8)")

        # 6. 单位得分 S_单位 (满分 20)
        s_unit = cls.UNIT_TYPE_SCORES.get(unit_type, 10)
        if any(kw in unit_name for kw in ["疾病预防控制", "疾控", "CDC", "卫生监督", "卫生健康监督"]):
            s_unit = 20
            evidence_chain.append(f"单位 [{unit_name}] 为各级疾病预防控制中心/卫监所 (满分20)")
        else:
            evidence_chain.append(f"单位类型为 [{unit_type}] (得分{s_unit})")

        # 7. 计算总分与星级映射
        total_score = s_major + s_job + s_unit

        if total_score >= 85 or s_major >= 50 or (matched_codes and s_major >= 40):
            match_level = 5
            match_reason = f"【五星精选】明确招录预防医学/公卫核心专业（总评分: {total_score}分）"
        elif total_score >= 68 or s_major >= 40:
            match_level = 4
            match_reason = f"【四星优选】公卫二级学科/流统/卫检/MPH高相关岗位（总评分: {total_score}分）"
        elif total_score >= 50 or s_major >= 30:
            match_level = 3
            match_reason = f"【三星备选】医学检验/公卫大类/卫管等相近医学岗（总评分: {total_score}分）"
        elif total_score >= 35 or s_major >= 15:
            match_level = 2
            match_reason = f"【二星关注】大医学类通用岗/专业不限招考（总评分: {total_score}分）"
        else:
            match_level = 1
            match_reason = f"【一星参考】非公卫专业或通用综合管理岗（总评分: {total_score}分）"

        return {
            "match_level": match_level,
            "match_score": total_score,
            "matched_codes": matched_codes,
            "matched_keywords": matched_keywords,
            "match_reason": match_reason,
            "evidence_chain": evidence_chain,
            "sub_disciplines": sub_disciplines
        }

    @classmethod
    def match(cls, major_raw: str, unit_type: str = "其他事业单位", job_name: str = "") -> Dict[str, Any]:
        """兼容老接口调用"""
        res = cls.calculate_match_score(major_raw=major_raw, unit_type=unit_type, job_name=job_name)
        # 兼容旧字段
        res["degree_req"] = {"matched_degrees": [], "min_degree": "不限"}
        return res
