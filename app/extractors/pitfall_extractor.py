import re
from typing import Dict, Any, List

class PitfallExtractor:
    """
    编制四维确权与避坑风险标签提取引擎 2.0
    """
    TYPE_FORMAL = "正式事业编"
    TYPE_BEIAN = "报备员额制"
    TYPE_CONTRACT = "编外/合同制"
    TYPE_DISPATCH = "劳务派遣"
    TYPE_UNKNOWN = "未注明"

    @classmethod
    def evaluate_bianzhi(cls, job_name: str, text: str) -> Dict[str, Any]:
        """
        四维投票评估编制属性并输出置信度与证据链
        """
        if not text:
            return {
                "type": cls.TYPE_UNKNOWN,
                "confidence": "LOW",
                "evidence_chain": ["缺少正文及岗位编制说明"]
            }

        scores = {
            cls.TYPE_FORMAL: 0,
            cls.TYPE_BEIAN: 0,
            cls.TYPE_CONTRACT: 0,
            cls.TYPE_DISPATCH: 0
        }
        evidence = {
            cls.TYPE_FORMAL: [],
            cls.TYPE_BEIAN: [],
            cls.TYPE_CONTRACT: [],
            cls.TYPE_DISPATCH: []
        }

        # 1. 劳务派遣判定 (高优先级排除)
        dispatch_patterns = [
            (r"劳务派遣", 50, "明确注明劳务派遣用工"),
            (r"派遣制", 40, "标注派遣制"),
            (r"与.*?劳务.*?公司签订", 50, "与第三方劳务公司签订合同")
        ]
        for p, score, desc in dispatch_patterns:
            if re.search(p, text):
                scores[cls.TYPE_DISPATCH] += score
                evidence[cls.TYPE_DISPATCH].append(desc)

        # 2. 编外/合同制判定
        contract_patterns = [
            (r"编外", 40, "明确为编外聘用"),
            (r"非事业编|非在编", 40, "明确非事业编制"),
            (r"自收自支", 25, "自收自支性质"),
            (r"院聘|聘用制合同", 30, "院聘/合同制管理")
        ]
        for p, score, desc in contract_patterns:
            if re.search(p, text):
                scores[cls.TYPE_CONTRACT] += score
                evidence[cls.TYPE_CONTRACT].append(desc)

        # 3. 报备员额制判定
        beian_patterns = [
            (r"备案制|报备员额", 40, "公立医院/高校人员控制总量备案制"),
            (r"人员控制总量", 40, "纳入人员控制总量管理"),
            (r"员额制", 35, "实行员额制管理"),
            (r"同工同酬|待遇同编", 20, "待遇同编同酬")
        ]
        for p, score, desc in beian_patterns:
            if re.search(p, text):
                scores[cls.TYPE_BEIAN] += score
                evidence[cls.TYPE_BEIAN].append(desc)

        # 4. 正式事业编判定
        formal_patterns = [
            (r"全额拨款|全额事业", 40, "财政全额拨款事业编制"),
            (r"纳入.*?事业编制|列入.*?编制", 40, "明确列入正式事业编制管理"),
            (r"事业编制|在编人员", 30, "属于正式事业编制"),
            (r"事业用编计划|办理用编手续", 35, "办理正式用编手续")
        ]
        for p, score, desc in formal_patterns:
            if re.search(p, text):
                scores[cls.TYPE_FORMAL] += score
                evidence[cls.TYPE_FORMAL].append(desc)

        # 综合打分裁决
        max_type = max(scores, key=scores.get)
        max_score = scores[max_type]

        if max_score >= 30:
            final_type = max_type
            confidence = "HIGH" if max_score >= 50 else "MEDIUM"
            evidence_chain = evidence[max_type]
        else:
            final_type = cls.TYPE_UNKNOWN
            confidence = "LOW"
            evidence_chain = ["未检索到明确编制确权条款，建议查看官方原文"]

        return {
            "type": final_type,
            "confidence": confidence,
            "score": max_score,
            "evidence_chain": evidence_chain
        }

    @classmethod
    def analyze(cls, job_desc: str, announcement_text: str = "") -> Dict[str, Any]:
        """
        提取避坑标签及风险等级
        """
        combined = f"{job_desc} {announcement_text}"
        pitfalls = []
        risk_score = 0

        # 服务期限制
        service_m = re.findall(r"(?:服务期|最低服务|服务年限|工作年限).*?([1-9一二三四五六七八九十])\s*年", combined)
        if service_m:
            yr = service_m[0]
            pitfalls.append({
                "tag": f"最低服务期{yr}年",
                "risk": "medium",
                "detail": f"岗位明确约定最低服务年限 {yr} 年，期间一般不得调动或报考其他单位。"
            })
            risk_score += 30

        if re.search(r"不得调离|不得报考|违约金", combined):
            pitfalls.append({
                "tag": "调动受限/违约条款",
                "risk": "high",
                "detail": "公告含有服务期内限制调离、解约赔偿等刚性约束条款。"
            })
            risk_score += 30

        # 户籍限制
        if re.search(r"限.*?户籍|限.*?生源|本市户籍|本县户籍|本地户籍", combined):
            pitfalls.append({
                "tag": "限本地户籍/生源",
                "risk": "medium",
                "detail": "限制特定区域户籍或生源地考生报考。"
            })
            risk_score += 20

        # 资格证书与门槛
        if re.search(r"公卫执业医师|公共卫生执业医师|执业医师资格", combined):
            pitfalls.append({
                "tag": "需公卫执业医师证",
                "risk": "low",
                "detail": "要求具备公卫执业医师资格证。"
            })
        if re.search(r"规培|住院医师规范化培训", combined):
            pitfalls.append({
                "tag": "需住院医师规培证",
                "risk": "low",
                "detail": "要求具备规培合格证书。"
            })
        if re.search(r"英语六级|CET-6|CET6", combined):
            pitfalls.append({
                "tag": "需英语六级(CET-6)",
                "risk": "low",
                "detail": "要求大学英语六级成绩 425 分及以上。"
            })

        # 确定整体风险级别
        if risk_score >= 50:
            overall_risk = "high"
        elif risk_score >= 20:
            overall_risk = "medium"
        else:
            overall_risk = "low"

        summary = "；".join([p["detail"] for p in pitfalls]) if pitfalls else "岗位条件常规，无明显隐形门槛与避坑风险。"

        return {
            "risk_level": overall_risk,
            "pitfall_items": pitfalls,
            "summary": summary
        }
