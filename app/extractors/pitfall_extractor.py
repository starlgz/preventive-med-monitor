import re
from typing import Dict, Any, List, Optional

class PitfallExtractor:
    """
    招考公告与岗位隐形门槛、避坑特征深度研判提取器
    识别内容：
    1. 最低服务年限 (如服务期5年内不得调动/辞职)
    2. 规培证/执业医师证硬性门槛
    3. 应届生/政治面貌/党员限制
    4. 年龄上限与博士/高级职称放宽政策
    5. 违约金/违约责任预警
    6. 综合避坑建议指数
    """

    @classmethod
    def extract(cls, text: Optional[str] = None, job_desc: Optional[str] = None, announcement_text: Optional[str] = None) -> List[Dict[str, Any]]:
        """便捷提取排坑风险条目列表"""
        res = cls.analyze(text=text, job_desc=job_desc, announcement_text=announcement_text)
        return res.get("pitfall_items", []) or res.get("pitfalls", [])

    @classmethod
    def analyze(cls, text: Optional[str] = None, job_desc: Optional[str] = None, announcement_text: Optional[str] = None) -> Dict[str, Any]:
        combined_parts = []
        if text:
            combined_parts.append(text)
        if job_desc:
            combined_parts.append(job_desc)
        if announcement_text:
            combined_parts.append(announcement_text)
        
        full_text = " ".join(combined_parts)
        if not full_text:
            return {
                "service_years": None,
                "service_years_evidence": None,
                "is_party_required": 0,
                "party_evidence": None,
                "training_requirement": "不限/无明确要求",
                "cert_requirement": "不限/无明确要求",
                "age_rules": "常规要求",
                "penalty_warning": 0,
                "pitfalls": [],
                "pitfall_items": [],
                "risk_level": "LOW",
                "summary": "无特殊限制门槛"
            }

        pitfalls = []
        risk_score = 0

        # 1. 最低服务年限
        service_years = None
        service_years_evidence = None
        service_match = re.search(r"(最低服务(年限|期)|服务期|工作年限|最低服务)?\s*([一二三四五六七八九十\d]+)\s*(个?年)(.*?)(不得(流动|辞职|调离|调动|报考)|须在|内不得)", full_text)
        if not service_match:
            service_match = re.search(r"(服务期|最低服务年限|服务年限)\s*(不少于|至少|为)?\s*([一二三四五六七八九十\d]+)\s*年", full_text)
        
        if service_match:
            raw_num = service_match.group(3) if len(service_match.groups()) >= 3 else service_match.group(0)
            # 汉字转数字
            num_map = {"一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "十": 10}
            if str(raw_num) in num_map:
                service_years = num_map[str(raw_num)]
            elif re.search(r"\d+", str(raw_num)):
                service_years = int(re.search(r"\d+", str(raw_num)).group(0))
            
            service_years_evidence = service_match.group(0).strip()
            if service_years and service_years >= 5:
                pitfalls.append(f"⚠️ 最低服务年限长达 {service_years} 年（期间通常锁定档案不得调离）")
                risk_score += 3
            elif service_years and service_years >= 3:
                pitfalls.append(f"📌 要求最低服务期 {service_years} 年")
                risk_score += 1

        # 2. 违约金/赔偿限制
        penalty_warning = 0
        if re.search(r"违约责任|违约金|赔偿.*金|退还.*补贴|未满服务期.*退回", full_text):
            penalty_warning = 1
            pitfalls.append("⚠️ 明确提及提前离职违约赔偿或退回安家费/补贴条款")
            risk_score += 2

        # 3. 政治面貌门槛
        is_party_required = 0
        party_evidence = None
        party_match = re.search(r"(必须为|限|要求|需是)?(中共党员|中共预备党员|党员)(才可报考|优先)?", full_text)
        if party_match and "党员" in party_match.group(0):
            if re.search(r"(限|必须|须为|要求).*?党员", full_text):
                is_party_required = 1
                party_evidence = party_match.group(0).strip()
                pitfalls.append("🔒 硬性限制：限中共党员（含预备党员）")
                risk_score += 1
            elif "优先" in full_text:
                is_party_required = 2
                party_evidence = "中共党员优先"

        # 4. 规培证要求
        training_req = "不限/无明确要求"
        if re.search(r"(具有|取得|需|须).*?(住院医师规范化培训合格证书|规培证|规培合格)", full_text):
            training_req = "硬性要求规培合格"
            pitfalls.append("📋 门槛要求：须持有住院医师规范化培训合格证书")
        elif re.search(r"完成规培|2026年.*完成规培", full_text):
            training_req = "应届需当年完成规培"

        # 5. 执业医师/专业技术资格
        cert_req = "不限/无明确要求"
        if re.search(r"(具有|取得|持有).*?(公共卫生|公卫).*?(执业医师|执业资格)", full_text):
            cert_req = "公共卫生执业医师资格"
        elif re.search(r"(具有|取得|持有).*?执业医师资格", full_text):
            cert_req = "执业医师资格证"
        elif re.search(r"中级及以上职称|主管医师|副主任医师", full_text):
            cert_req = "要求中级及以上专业技术职称"
            risk_score += 1

        # 6. 年龄放宽条款
        age_rules = "常规要求"
        age_match = re.search(r"(\d{2})周岁以下.*?(博士|高级职称|研究生|急需紧缺).*?放宽至\s*(\d{2})\s*周岁", full_text)
        if age_match:
            age_rules = f"基准 {age_match.group(1)} 岁，{age_match.group(2)} 可放宽至 {age_match.group(3)} 岁"
        elif re.search(r"博士.*?放宽|高级职称.*?放宽", full_text):
            age_rules = "高层次人才/博士年龄可适当放宽"

        # 评定综合风险等级
        if risk_score >= 3:
            risk_level = "HIGH"
        elif risk_score >= 1:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        summary = "；".join(pitfalls) if pitfalls else "经研判无苛刻锁定限制或特殊违约条款"

        return {
            "service_years": service_years,
            "service_years_evidence": service_years_evidence,
            "is_party_required": is_party_required,
            "party_evidence": party_evidence,
            "training_requirement": training_req,
            "cert_requirement": cert_req,
            "age_rules": age_rules,
            "penalty_warning": penalty_warning,
            "pitfalls": pitfalls,
            "pitfall_items": pitfalls,
            "risk_level": risk_level,
            "summary": summary
        }
