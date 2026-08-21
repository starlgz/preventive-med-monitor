import re
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.entities import MajorCatalog

class MajorMatcher:
    """预防医学及公卫相关专业五星匹配与冷门专业、细分二级学科、国标代码全量召回规则引擎"""

    # 细分专业子学科关键词库定义
    SUB_DISCIPLINE_KEYWORDS = {
        "卫生毒理学": ["卫生毒理", "毒理学", "毒物分析", "化学毒物", "毒理检验", "遗传毒理", "环境毒理", "食品毒理", "分子毒理", "计算毒理", "生化与分子毒理"],
        "营养与食品卫生学": ["营养与食品卫生", "食品营养", "营养学", "食品安全", "临床营养", "公共营养", "食品卫生检验", "分子营养学", "精准营养", "食品毒理与安全", "营养流行病学"],
        "儿少卫生与妇幼保健学": ["儿少卫生", "妇幼保健", "母婴保健", "儿童保健", "少儿卫生与妇幼保健学", "少儿卫生", "学校卫生与儿少卫生", "妇女保健", "优生优育", "生殖健康", "青少年健康监测"],
        "劳动卫生与环境卫生学": ["劳动卫生与环境卫生", "劳动卫生", "环境卫生", "职业卫生", "职业病防治", "环境流行病学", "辐射卫生", "职业健康", "职业卫生评价", "环境与健康", "环境暴露学", "劳动生理", "放射卫生", "卫生应急与辐射防护"],
        "流行病与卫生统计学": ["流行病与卫生统计", "流行病学", "卫生统计学", "现场流行病学", "传染病流行病学", "慢性病流行病学", "空间流行病学", "分子流行病学", "临床流行病学", "健康大数据统计", "生物统计与流行病", "基因流行病学", "数字公共卫生", "传染病动力学建模"],
        "卫生检验与检疫": ["卫生检验与检疫", "卫生检验", "检验检疫", "病原检验", "微生物检验", "卫生理化检验", "理化检验", "分子生物学检验", "病毒检验", "细菌检验", "水质理化检验", "食品理化检验", "空气理化检验", "公共卫生检验技术"],
        "卫生监督": ["卫生监督", "公共卫生监督", "医疗监督", "卫生执法", "卫生行政执法", "卫生监督与行政执法", "卫生法制监督"],
        "生物统计学": ["生物统计学", "生物统计", "生物信息学", "医学统计", "统计与生物信息", "应用统计学(生物统计方向)", "生物信息与统计", "健康医疗大数据"],
        "全球健康学": ["全球健康学", "全球健康", "全球卫生", "国际卫生", "国际健康", "Global Health", "国际卫生与全球健康", "全球公共卫生"],
        "医院感染控制": ["医院感染控制", "医院感染管理", "院感", "感控", "感染控制", "消毒与病媒生物防制", "病媒生物防制", "医院感染监控", "消毒与媒介生物学"],
        "社会医学与卫生事业管理": ["卫生事业管理", "社会医学", "医院管理", "卫生政策", "卫生管理", "公共卫生事业管理", "卫生经济学", "卫生法学与监督", "卫生应急管理", "医疗保障管理", "健康政策与管理"],
        "健康教育与健康促进": ["健康教育", "健康促进", "社区卫生", "健康大数据与生物信息", "健康传播学", "健康管理", "公共卫生健康促进"],
        "卫生应急与生物安全": ["卫生应急", "生物安全", "公共卫生应急", "突发公共卫生事件应急", "生物安全防护", "卫生防化", "重大疫情应急处置", "实验室生物安全"],
        "全科医学": ["全科医学", "全科医生", "全科方向", "全科医学科"],
        "医学信息学与健康大数据": ["医学信息学", "卫生信息学", "健康大数据", "时空流行病学分析", "数字健康", "公卫智能", "卫生信息统计", "医疗大数据分析", "医学人工智能与公卫", "健康医疗大数据挖掘"],
        "全球健康与国境卫生检疫": ["全球健康学", "海关口岸卫生检疫", "国际卫生检疫", "全球公共卫生", "出入境检验检疫", "口岸传染病监测", "国境卫生检疫", "海关卫生检疫", "国境口岸传染病防控"],
        "放射卫生与辐射防护": ["放射医学", "放射卫生", "辐射防护", "核辐射卫生应急", "辐射危害评价", "职业放射病防治", "放射损伤防治", "核化生防护", "放射性核素监测"],
        "循证医学与临床流行病学": ["循证医学", "临床流行病学", "循证公共卫生", "临床试验统计设计", "卫生技术评估", "HTA", "真实世界研究", "Meta分析与系统评价", "循证决策"],
        "医学与公卫人工智能": ["医学人工智能", "智慧公卫", "公卫大模型", "医疗人工智能", "生物医学计算", "公卫智能预警", "智能流行病学", "计算医学", "健康人工智能"],
        "公卫应急与卫生化验": ["卫生化验", "卫生理化分析", "公卫检验", "环境介质检测", "职业卫生检测", "食品理化快检", "水质理化分析", "突发公卫应急检测"],
        "现场流行病学与应急调查": ["现场流行病学", "FETP", "现场流调", "疫情现场处置", "突发疫情流调溯源", "现场流行病学培训项目", "现场流行病学调查", "突发事件卫生应急处置"],
        "病原微生物与生物安全三级实验室": ["生物安全三级实验室", "P3实验室", "BSL-3", "高级别生物安全实验室", "高致病性病原微生物", "生物安全二级实验室", "P2+实验室", "病原微生物基因组学", "高通量病原测序"],
        "病媒生物防制与寄生虫病防治": ["病媒生物防制", "媒介生物学", "媒介伊蚊防制", "鼠害控制与监测", "热带病与寄生虫病", "寄生虫病防治", "血吸虫病防治", "媒介生物抗药性监测", "消毒与媒介生物学"],
        "食品安全风险监测与营养评估": ["食品安全风险监测", "食品安全风险评估", "营养与健康状况监测", "膳食暴露评估", "食品污染与有害因素监测", "人群营养干预", "慢性病营养防控"],
        "公卫医师规培与全科公卫": ["公共卫生医师规范化培训", "公卫医师规培", "公共卫生医师规培", "疾控岗位培训", "公共卫生住院医师", "公共卫生医师专项培养", "公卫执业医师"],
        "免疫规划与疫苗管理": ["免疫规划", "疫苗接种管理", "疫苗临床评价", "免疫效果评价", "计划免疫", "预防接种异常反应", "AEFI监测", "疫苗研发与评价", "免疫监测"],
        "重大传染病与结核艾滋病防治": ["结核病防治", "结核病预防控制", "艾滋病防治", "性病防治", "结核病实验室", "耐药结核", "艾滋病高危人群干预", "抗病毒治疗管理", "性病艾滋病检测"],
        "地方病与慢性病综合防控": ["地方病防治", "慢性病综合防控", "慢性病管理", "碘缺乏病防治", "地方性氟中毒", "大骨节病", "慢性病危险因素监测", "死因监测"],
        "健康危害因素监测与化学毒物检测": ["健康危害因素监测", "化学毒物检测", "职业病危害监测", "职业健康监护", "工作场所职业病危害因素", "环境健康风险评估", "现场快速检测", "职业卫生技术支撑"],
        "健康中国行动与营养健康": ["健康中国行动", "全民健康生活方式", "健康素养促进", "健康城市评估", "三减三健", "国民体质监测", "健康教育与健康传播"],
        "流行病学调查与疾病监测": ["疾病监测", "症状监测", "传染病报告管理", "突发公共卫生事件监测预警", "哨点监测", "病媒传染病监测", "不明原因肺炎监测", "聚集性疫情调查"],
        "放射卫生与核化应急监测": ["放射卫生检测", "核化生防护与检测", "放射工作场所检测", "医用辐射防护监测", "环境天然放射性水平监测", "核与辐射事故医学应急"],
        "环境与职业健康监护": ["工作场所职业病危害因素监测", "环境健康影响评价", "职业健康监护与管理", "公卫理化检验分析", "职业病诊断与鉴定", "环境污染物人群暴露评估"],
        "智慧化多点触发预警": ["多点触发预警", "智慧化疾控监测", "公卫监测预警平台", "症候群监测", "传染病多渠道监测", "智能化疫情研判", "传染病预测预警模型"],
        "跨境与海关口岸传染病检疫": ["国境卫生检疫", "口岸传染病排查", "出入境检疫查验", "口岸病媒生物控制", "国际旅行卫生保健", "海关生物安全监测"],
        "毒物代谢与环境靶向毒理": ["毒物代谢动力学", "靶器官毒理", "环境内分泌干扰物", "代谢组学毒理", "生化与分子毒理学", "计算毒理学"],
        "智慧化现场流调与接触者追踪": ["数字化流调", "时空接触者追踪", "流调排查智能终端", "突发疫情数字化响应", "数字传染病学"],
        "新污染物健康风险与暴露组学": ["新污染物", "环境暴露组学", "微塑料暴露", "全氟化合物健康风险", "高通量环境暴露筛查", "新型持久性有机污染物"],
        "高通量病原宏基因组学与分子溯源": ["宏基因组测序", "mNGS", "病原高通量测序", "病原全基因组测序", "分子溯源分析", "基因组流行病学"]
    }

    # 学历层次层级定义
    DEGREE_HIERARCHY = {
        "博士": ["博士", "博士研究生", "博士学位", "PhD", "博士后"],
        "硕士": ["硕士", "硕士研究生", "硕士学位", "公卫硕士", "MPH", "学术硕士", "专业硕士"],
        "本科": ["本科", "学士", "大学本科", "本科及以上", "学士学位"],
        "大专": ["大专", "专科", "高职高专", "专科及以上"]
    }

    # 1. 五星 (★★★★★): 明确直接命中预防医学本科/核心国控专业/代码
    LEVEL_5_PATTERNS = [
        r"预防医学",
        r"100401[A-Za-z]?",       # 预防医学专业代码
        r"100402[A-Za-z]?",       # 卫生检验与检疫
        r"100403[A-Za-z]?",       # 妇幼保健医学
        r"100404[A-Za-z]?",       # 卫生监督
        r"100405[A-Za-z]?",       # 全球健康学
        r"全球健康学",
        r"全球健康",
        r"跨境卫生检疫",
        r"国际卫生检疫",
        r"现场流行病学",
        r"病原微生物基因组学",
        r"分子流行病学",
        r"病媒生物防制",
        r"媒介生物学",
        r"消毒与病媒生物防制",
        r"食品安全风险监测",
        r"膳食暴露评估",
        r"卫生检验与检疫",
        r"卫生检验",
        r"检验检疫",
        r"病原检验",
        r"微生物检验",
        r"卫生理化检验",
        r"理化检验",
        r"妇幼保健医学",
        r"妇幼保健",
        r"儿少卫生与妇幼保健学",
        r"少儿卫生与妇幼保健学",
        r"儿少卫生",
        r"母婴保健",
        r"儿童保健",
        r"卫生监督",
        r"公共卫生医师",
        r"公卫医师",
        r"公共卫生医师规范化培训",
        r"公卫医师规培",
        r"公共卫生医师规培",
        r"免疫规划",
        r"计划免疫",
        r"疫苗临床评价",
        r"结核病防治",
        r"艾滋病防治",
        r"地方病防治",
        r"慢性病综合防控",
        r"健康危害因素监测",
        r"放射卫生检测",
        r"核化生防护与检测",
        r"多点触发预警",
        r"智慧化疾控监测",
        r"口岸传染病排查",
        r"出入境检疫查验",
        r"环境健康影响评价",
        r"职业病危害因素监测",
        r"职业健康监护",
        r"健康中国行动",
        r"疾病监测",
        r"症状监测"
    ]

    # 2. 四星 (★★★★☆): 公卫一级学科、二级学科研究生、专硕 (MPH)、交叉前沿学科
    LEVEL_4_PATTERNS = [
        r"全球健康学",
        r"全球健康",
        r"全球卫生",
        r"公共卫生与预防医学",
        r"公共卫生硕士",
        r"公共卫生硕士\(MPH\)",
        r"MPH\b",
        r"流行病与卫生统计学",
        r"流行病学与卫生统计学",
        r"劳动卫生与环境卫生学",
        r"环境卫生与劳动卫生学",
        r"营养与食品卫生学",
        r"卫生毒理学",
        r"现场流行病学",
        r"传染病流行病学",
        r"慢性病流行病学",
        r"环境流行病学",
        r"分子流行病学",
        r"空间流行病学",
        r"基因流行病学",
        r"传染病动力学建模",
        r"数字公共卫生",
        r"流行病学",
        r"卫生统计学",
        r"劳动卫生",
        r"环境卫生学?",
        r"职业卫生",
        r"职业病防治",
        r"放射卫生",
        r"营养与食品卫生",
        r"食品营养",
        r"营养学",
        r"食品安全",
        r"临床营养",
        r"公共营养",
        r"卫生毒理",
        r"毒理学",
        r"毒物分析",
        r"化学毒物",
        r"毒理检验",
        r"遗传毒理",
        r"环境毒理",
        r"食品毒理",
        r"分子毒理",
        r"军事预防医学",
        r"放射医学",
        r"卫生应急与管理",
        r"卫生应急与生物安全",
        r"公共卫生应急",
        r"生物安全防护",
        r"突发公共卫生事件应急",
        r"实验室生物安全",
        r"卫生统计与信息学",
        r"应用统计学\(生物统计方向\)",
        r"生物统计学",
        r"生物统计",
        r"健康大数据与生物信息",
        r"职业卫生与职业病",
        r"全科医学",
        r"全科医生",
        r"全科方向",
        r"传染病预防控制",
        r"慢性病防控",
        r"消毒与病媒生物防制",
        r"病媒生物防制",
        r"消毒与媒介生物学",
        r"医院感染控制",
        r"医院感染管理",
        r"院感",
        r"感控",
        r"感染控制",
        r"食品安全与卫生",
        r"卫生化验",
        r"医学人工智能",
        r"公卫大数据",
        r"智慧公卫",
        r"智慧公共卫生",
        r"公卫应急",
        r"突发公共卫生事件",
        r"1004\b",               # 一级学科代码
        r"1053\b",               # 公卫专硕代码
        r"100401", r"100402", r"100403", r"100404", r"100405",
        r"100401TK", r"100402TK",
        r"公共卫生学",
        r"医学信息学",
        r"卫生信息学",
        r"健康大数据",
        r"海关口岸卫生检疫",
        r"国境卫生检疫",
        r"国境口岸传染病",
        r"放射卫生与辐射防护",
        r"核辐射卫生应急",
        r"循证医学",
        r"循证公共卫生",
        r"真实世界研究",
        r"卫生技术评估",
        r"现场流行病学调查",
        r"突发疫情流调溯源",
        r"现场流行病学培训项目",
        r"FETP\b",
        r"生物安全三级实验室",
        r"P3实验室",
        r"BSL-3\b",
        r"病原微生物基因组学",
        r"高通量病原测序",
        r"病媒生物防制",
        r"媒介生物学",
        r"媒介伊蚊防制",
        r"食品安全风险监测",
        r"食品安全风险评估",
        r"放射卫生检测",
        r"环境健康影响评价",
        r"多点触发预警",
        r"多渠道监测预警",
        r"口岸传染病排查",
        r"膳食暴露评估"
    ]

    # 3. 三星 (★★★☆☆): 疾控/卫监/妇幼单位业务岗中的大类宽泛专业 / 医学检验 / 卫生管理
    LEVEL_3_PATTERNS = [
        r"公共卫生类",
        r"公卫类",
        r"预防医学类",
        r"医学检验技术",
        r"医学检验",
        r"临床检验诊断学",
        r"社会医学与卫生事业管理",
        r"社会医学",
        r"卫生事业管理",
        r"医院管理",
        r"卫生政策",
        r"卫生管理学",
        r"卫生管理",
        r"公共卫生事业管理",
        r"健康教育与健康促进",
        r"医学类",
        r"医药卫生类",
        r"基础医学类",
        r"健康服务与管理",
        r"生物医学工程",
        r"病理学与病理生理学",
        r"免疫学",
        r"病原生物学"
    ]

    # 4. 二星 (★★☆☆☆): 模糊医学大类 / 待核实
    LEVEL_2_PATTERNS = [
        r"临床医学及相关专业",
        r"相关专业",
        r"不限专业",
        r"医药类",
        r"生物医药类",
        r"生物学类",
        r"生命科学类"
    ]

    # 5. 一星排除 (★☆☆☆☆): 明确仅限非公卫/无关专业
    EXCLUDE_PATTERNS = [
        r"中医学",
        r"中药学",
        r"中西医结合",
        r"针灸推拿",
        r"护理学",
        r"助产",
        r"计算机",
        r"软件工程",
        r"网络工程",
        r"会计",
        r"财务管理",
        r"审计",
        r"汉语言文学",
        r"法学",
        r"行政管理",
        r"马克思主义"
    ]

    @classmethod
    async def load_catalogs_from_db(cls, db: AsyncSession) -> List[MajorCatalog]:
        """从 SQLite 数据库动态加载专业目录"""
        res = await db.execute(select(MajorCatalog).where(MajorCatalog.is_active == 1))
        return res.scalars().all()

    @classmethod
    def find_sub_disciplines(cls, text: str) -> Dict[str, List[str]]:
        """识别文本中命中的细分专业及关键词"""
        matched = {}
        for category, keywords in cls.SUB_DISCIPLINE_KEYWORDS.items():
            hits = [kw for kw in keywords if kw in text]
            if hits:
                matched[category] = hits
        return matched

    @classmethod
    def extract_degree_requirement(cls, text: str) -> Dict[str, Any]:
        """提取岗位学历层级要求（博士/硕士/本科/大专）"""
        matched_degrees = []
        for level, kw_list in cls.DEGREE_HIERARCHY.items():
            if any(kw in text for kw in kw_list):
                matched_degrees.append(level)
        
        min_degree = "不限"
        if "博士" in matched_degrees:
            min_degree = "博士"
        elif "硕士" in matched_degrees:
            min_degree = "硕士"
        elif "本科" in matched_degrees:
            min_degree = "本科"
        elif "大专" in matched_degrees:
            min_degree = "大专"

        return {
            "matched_degrees": matched_degrees,
            "min_degree": min_degree
        }

    @classmethod
    def match(cls, major_raw: str, unit_type: str = "其他事业单位", job_name: str = "") -> Dict[str, Any]:
        """
        对岗位专业要求进行五星级精准匹配研判与全维度解析
        返回: {
            "match_level": 5/4/3/2/1,
            "matched_codes": [...],
            "matched_keywords": [...],
            "match_reason": "...",
            "sub_disciplines": {...},
            "degree_req": {...}
        }
        """
        if not major_raw or not major_raw.strip():
            # 专业未填写的，如果在疾控中心业务岗，给 3 星待确认，否则 2 星
            if unit_type in ["疾控中心", "卫生监督", "急救中心", "妇幼保健院"]:
                return {
                    "match_level": 3,
                    "matched_codes": [],
                    "matched_keywords": [],
                    "match_reason": "未注明具体专业，单位为疾控/卫监/妇幼等公卫业务核心单位，需人工确认",
                    "sub_disciplines": {},
                    "degree_req": {"matched_degrees": [], "min_degree": "不限"}
                }
            return {
                "match_level": 2,
                "matched_codes": [],
                "matched_keywords": [],
                "match_reason": "专业要求空白，需核实具体公告",
                "sub_disciplines": {},
                "degree_req": {"matched_degrees": [], "min_degree": "不限"}
            }

        text = major_raw.strip()
        sub_disciplines = cls.find_sub_disciplines(text + " " + job_name)
        degree_req = cls.extract_degree_requirement(text + " " + job_name)

        # 检查 5 星核心词
        matched_l5 = []
        for pat in cls.LEVEL_5_PATTERNS:
            found = re.findall(pat, text, re.IGNORECASE)
            if found:
                matched_l5.extend(found)

        # 处理 "公共卫生与预防医学" 导致 matched_l5 捕获了 "预防医学" 的情况
        if "公共卫生与预防医学" in text and "预防医学" in matched_l5:
            replaced = text.replace("公共卫生与预防医学", "")
            if not any(re.search(pat, replaced, re.IGNORECASE) for pat in cls.LEVEL_5_PATTERNS):
                matched_l5 = []

        if matched_l5:
            res_codes = list(set(matched_l5))
            return {
                "match_level": 5,
                "matched_codes": res_codes,
                "matched_keywords": res_codes,
                "match_reason": f"明确命中预防医学核心专业要求：[{', '.join(res_codes)}]",
                "sub_disciplines": sub_disciplines,
                "degree_req": degree_req
            }

        # Step 1: 检查具体的 4 星一级/二级学科及冷门专硕
        matched_l4 = []
        for pat in cls.LEVEL_4_PATTERNS:
            found = re.findall(pat, text, re.IGNORECASE)
            if found:
                matched_l4.extend(found)

        if matched_l4:
            res_codes = list(set(matched_l4))
            return {
                "match_level": 4,
                "matched_codes": res_codes,
                "matched_keywords": res_codes,
                "match_reason": f"命中公卫与预防医学高度相关学科/MPH专硕：[{', '.join(res_codes)}]",
                "sub_disciplines": sub_disciplines,
                "degree_req": degree_req
            }

        # Step 2: 检查 3 星 (疾控/公卫大类、医学检验、卫管等)
        matched_l3 = []
        for pat in cls.LEVEL_3_PATTERNS:
            found = re.findall(pat, text, re.IGNORECASE)
            if found:
                matched_l3.extend(found)

        if matched_l3:
            res_codes = list(set(matched_l3))
            return {
                "match_level": 3,
                "matched_codes": res_codes,
                "matched_keywords": res_codes,
                "match_reason": f"命中公卫大类/检验/卫管相关专业：[{', '.join(res_codes)}]",
                "sub_disciplines": sub_disciplines,
                "degree_req": degree_req
            }

        # Step 3: 检查 1 星明确排除
        matched_ex = []
        for pat in cls.EXCLUDE_PATTERNS:
            found = re.findall(pat, text, re.IGNORECASE)
            if found:
                matched_ex.extend(found)

        if matched_ex and not matched_l3:
            res_codes = list(set(matched_ex))
            return {
                "match_level": 1,
                "matched_codes": res_codes,
                "matched_keywords": res_codes,
                "match_reason": f"明确要求非预防医学专业：[{', '.join(res_codes)}]",
                "sub_disciplines": sub_disciplines,
                "degree_req": degree_req
            }

        # Step 4: 兜底 2 星
        return {
            "match_level": 2,
            "matched_codes": [],
            "matched_keywords": [],
            "match_reason": f"专业要求模糊或未明确包含公卫代码，需人工核对：{text[:30]}",
            "sub_disciplines": sub_disciplines,
            "degree_req": degree_req
        }

    def match_major(self, major_raw: str, job_name: str = "") -> dict:
        """alias for backward compat / tests; adds matched_keywords field"""
        result = self.__class__.match(major_raw, job_name=job_name)
        result.setdefault("matched_keywords", result.get("matched_codes", []))
        return result
