import re
from typing import Dict, Any, List, Optional

class TalentPolicyExtractor:
    """
    人才引进、免笔试、高层次人才待遇、安家补贴提取器
    支持识别博士免笔试、紧缺人才绿色通道、科研启动经费、购房安家补贴等优惠政策
    """

    # 免笔试判定特征词
    NO_WRITTEN_EXAM_KEYWORDS = [
        "免笔试", "直接面试", "免考笔试", "考核招聘", "直接考核", 
        "面谈考核", "考核录用", "免除笔试", "不设笔试", "简化程序",
        "绿色通道", "高层次人才引进", "急需紧缺人才", "直接考察",
        "免统一笔试", "免统考", "考核招考", "面试考核入围", "考核直聘",
        "人才直通车", "硕博引才", "紧缺急需人才", "综合考核录取",
        "免笔试直接面试", "直接面试考核", "面试直通车", "简化考试程序",
        "博士免笔试", "硕士研究生直接面试", "紧缺岗位免笔试", "免试入围"
    ]

    # 人才引进模式匹配
    TALENT_INTRO_PATTERNS = [
        r"人才引进", r"高层次.*人才", r"急需紧缺", r"紧缺.*人才", r"专项引才", 
        r"绿色通道", r"高精尖人才", r"领军人才", r"博士引进", r"学科带头人",
        r"优才引进", r"选聘高层次", r"优秀人才", r"博创人才", r"硕博引才",
        r"雏鹰计划", r"英才计划", r"紧缺专业引才", r"博士直通车", r"名校优生",
        r"大湾区青年人才", r"蓉漂计划", r"钱塘英才", r"金陵名家", r"黄鹤英才", r"鹏城孔雀",
        r"泉城学者", r"盛京英才", r"冰城之星", r"姑苏卫生人才", r"三湘公卫英才", r"庐州英才", r"榕城公卫学者",
        r"太湖人才计划", r"瓯越英才计划", r"三江英才计划", r"东莞特色人才", r"佛山领军人才", r"通城英才",
        r"龙城英才计划", r"名士之乡英才", r"星耀南湖", r"珠海英才计划", r"中山特聘人才"
    ]

    # 安家费与购房补贴正则匹配
    SETTLEMENT_ALLOWANCE_PATTERNS = [
        r"一次性安家费(?:最高)?(?:达)?([0-9]+(?:\.[0-9]+)?(?:万元|万|w))",
        r"安家费(?:最高)?(?:达)?([0-9]+(?:\.[0-9]+)?(?:万元|万|w))",
        r"安家(?:补贴|补助|费)(?:最高)?(?:达)?([0-9]+(?:\.[0-9]+)?(?:万元|万|w))",
        r"购房(?:补贴|安置|资助)(?:最高)?(?:达)?([0-9]+(?:\.[0-9]+)?(?:万元|万|w))",
        r"引进人才(?:补贴|奖励)(?:最高)?(?:达)?([0-9]+(?:\.[0-9]+)?(?:万元|万|w))",
        r"生活补贴(?:每月)?([0-9]+(?:\.[0-9]+)?(?:万元|万|w|元))",
        r"提供安家费([0-9]+(?:-[0-9]+)?万元)",
        r"安家费及购房补贴([0-9]+(?:\.[0-9]+)?(?:万元|万))",
        r"住房补贴(?:最高)?([0-9]+(?:\.[0-9]+)?(?:万元|万))",
        r"一次性(?:人才)?补贴([0-9]+(?:\.[0-9]+)?(?:万元|万))",
        r"安家落户补贴([0-9]+(?:\.[0-9]+)?(?:万元|万))"
    ]

    # 科研启动经费正则
    RESEARCH_FUND_PATTERNS = [
        r"科研启动(?:经费|费|金|资助)(?:最高)?(?:达)?([0-9]+(?:\.[0-9]+)?(?:万元|万|w))",
        r"科研经费(?:最高)?(?:达)?([0-9]+(?:\.[0-9]+)?(?:万元|万|w))",
        r"提供科研启动(?:经费|费)([0-9]+(?:-[0-9]+)?万元)",
        r"科研项目启动资助([0-9]+(?:\.[0-9]+)?(?:万元|万))"
    ]

    # 户口解决与配偶安置
    BENEFITS_KEYWORDS = {
        "解决编制": ["落实事业编制", "纳入实名制编制", "全额事业编制", "入编", "直聘事业编制", "正式编制"],
        "户口解决": ["解决北京户口", "解决上海户口", "落户", "解决户口", "协助落户", "配偶随迁", "落户安置"],
        "住房保障": ["提供人才公寓", "提供过渡住房", "免租金", "周转房", "人才周转房", "人才周转公寓", "周转公寓", "免租人才公寓", "人才公寓", "住房保障", "配租", "租房补贴"],
        "子女入学": ["协助解决子女入学", "解决子女就读", "子女优质学位", "子女入学优待", "解决配偶工作及子女优质入学", "协调解决配偶工作", "子女入学", "保障子女就读"]
    }

    @classmethod
    def _parse_amount_to_number(cls, amount_str: Optional[str]) -> Optional[int]:
        """将包含万元、万、元等的补贴金额解析为整型数字（单位：元）"""
        if not amount_str:
            return None
        m = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*(万|w|元)?", str(amount_str), re.IGNORECASE)
        if not m:
            return None
        num = float(m.group(1))
        unit = m.group(2)
        if unit in ["万", "w", "W"]:
            return int(num * 10000)
        return int(num)

    @classmethod
    def extract_talent_policies(cls, text: str, job_title: str = "", requirements: str = "") -> Dict[str, Any]:
        """
        全面抽取文本及岗位要求中的人才引进政策
        """
        full_text = f"{text}\n{job_title}\n{requirements}"
        
        # 1. 判断是否免笔试/考核招聘
        is_no_exam = any(kw in full_text for kw in cls.NO_WRITTEN_EXAM_KEYWORDS)
        exam_form = "免笔试/直接考核" if is_no_exam else "笔试+面试"
        matched_no_exam_kw = [kw for kw in cls.NO_WRITTEN_EXAM_KEYWORDS if kw in full_text]

        # 2. 是否为人才引进项目
        is_talent_intro = any(re.search(pat, full_text) for pat in cls.TALENT_INTRO_PATTERNS)

        # 3. 提取安家费/购房补贴
        settlement_allowance = None
        settling_allowance_val = None
        for pattern in cls.SETTLEMENT_ALLOWANCE_PATTERNS:
            match = re.search(pattern, full_text)
            if match:
                settlement_allowance = match.group(0)
                settling_allowance_val = match.group(1) if match.groups() else match.group(0)
                break

        # 4. 提取科研启动经费
        research_fund = None
        research_fund_val = None
        for pattern in cls.RESEARCH_FUND_PATTERNS:
            match = re.search(pattern, full_text)
            if match:
                research_fund = match.group(0)
                research_fund_val = match.group(1) if match.groups() else match.group(0)
                break

        # 5. 提取特殊福利与待遇亮点
        special_benefits = []
        for benefit_name, kws in cls.BENEFITS_KEYWORDS.items():
            if any(k in full_text for k in kws):
                special_benefits.append(benefit_name)

        # 6. 生成政策综合置信度与评级 (S / A / B / C)
        tier = "C"
        reasons = []
        if is_talent_intro or is_no_exam:
            tier = "B"
            reasons.append("符合免笔试或人才引进专项通道")
        if settlement_allowance or research_fund:
            tier = "A"
            reasons.append("提供专项安家补贴或科研启动金")
        if (is_talent_intro or is_no_exam) and (settlement_allowance or research_fund) and special_benefits:
            tier = "S"
            reasons.append("顶格人才引进政策（免笔试+安家补助+落户/编制/住房保障）")

        # 构造补贴与待遇描述
        benefit_details = []
        if settlement_allowance:
            benefit_details.append(f"安家费/购房补贴: {settlement_allowance}")
        if research_fund:
            benefit_details.append(f"科研启动费: {research_fund}")
        if special_benefits:
            benefit_details.append(f"福利支持: {','.join(special_benefits)}")

        allowance_summary = "，".join(benefit_details) if benefit_details else None

        # 提取目标学历要求
        target_degrees = []
        if "博士" in full_text:
            target_degrees.append("博士")
        if "硕士" in full_text or "研究生" in full_text:
            target_degrees.append("硕士研究生")
        if "本科" in full_text:
            target_degrees.append("本科")

        benefits_list = []
        if "提供人才公寓" in full_text or "人才公寓" in full_text:
            benefits_list.append("提供人才公寓")
        if "配偶" in full_text or "子女" in full_text:
            benefits_list.append("解决配偶工作及子女优质入学")

        # 构造亮点列表
        highlights = list(matched_no_exam_kw)
        if settlement_allowance:
            highlights.append("安家补贴")
        if research_fund:
            highlights.append("科研经费")
        if "住房保障" in special_benefits:
            highlights.append("住房保障")
        if "子女入学" in special_benefits:
            highlights.append("子女入学")

        # 识别人才层次
        talent_level = "常规人才"
        if "顶尖" in full_text or "领军" in full_text or "学科带头人" in full_text:
            talent_level = "领军人才"
        elif "高层次" in full_text:
            talent_level = "高层次人才"
        elif "紧缺" in full_text:
            talent_level = "紧缺人才"
        elif "博士" in full_text:
            talent_level = "博士研究生"

        settlement_num = cls._parse_amount_to_number(settling_allowance_val or settlement_allowance)
        research_num = cls._parse_amount_to_number(research_fund_val or research_fund)

        return {
            # 扩展字段
            "is_talent_intro": is_talent_intro,
            "is_no_written_exam": is_no_exam,
            "is_no_exam": is_no_exam,
            "exam_form": exam_form,
            "matched_policy_keywords": matched_no_exam_kw,
            "settlement_allowance": settlement_allowance,
            "settling_allowance": settling_allowance_val or settlement_allowance,
            "housing_subsidy_amt": settlement_num,
            "research_fund_amt": research_num,
            "research_fund": research_fund_val or research_fund,
            "special_benefits": special_benefits,
            "has_housing_or_subsidy": bool(settlement_allowance or "住房保障" in special_benefits),
            "highlights": highlights,
            "tags": highlights,
            "talent_level": talent_level,
            "policy_tier": tier,
            "tier": tier,
            "tier_level": tier,
            "policy_summary": " | ".join(reasons) if reasons else "常规招聘渠道",
            
            # 兼容历史接口与字段
            "is_talent_introduction": is_talent_intro,
            "is_exam_exempt": is_no_exam,
            "allowance_summary": allowance_summary,
            "target_degree": "、".join(target_degrees) if target_degrees else "不限",
            "benefits": benefits_list if benefits_list else special_benefits,
            "benefit_details": "；".join(benefit_details) if benefit_details else "无专项补贴说明"
        }

    @classmethod
    def extract_talent_policy(cls, title: str = "", content: str = "", requirements: str = "") -> Dict[str, Any]:
        """兼容历史方法 extract_talent_policy"""
        text = f"{title}\n{content}"
        return cls.extract_talent_policies(text=text, requirements=requirements)

    @classmethod
    def extract(cls, announcement_text: str = "", job_name: str = "", requirements: str = "", **kwargs) -> Dict[str, Any]:
        """统一兼容通用 extract 入口"""
        text = kwargs.get("text", announcement_text)
        job_title = kwargs.get("job_title", job_name)
        req = kwargs.get("requirements", requirements)
        return cls.extract_talent_policies(text=text, job_title=job_title, requirements=req)
