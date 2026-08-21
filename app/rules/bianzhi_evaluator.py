import re
from typing import Dict, Any, List, Tuple, Optional

class BianzhiEvaluator:
    """
    升级版编制判定与置信度引擎
    支持：
    1. 全额事业编 (公益一类/实名制编制)
    2. 差额事业编 / 自收自支
    3. 报备员额 / 人员总量备案制 (公立医院改革)
    4. 合同制 (编外聘用)
    5. 劳务派遣
    输出置信度评分 (0.0 ~ 1.0) 及可解释自然语言证据链
    """

    # 1. 劳务派遣排除词
    DISPATCH_KEYWORDS = [
        (r"劳务派遣", "劳务派遣", "岗位明确采用劳务派遣用工形式"),
        (r"第三方劳务公司|劳务外包", "第三方外包", "用工主体为第三方人力资源或劳务外包公司"),
        (r"派遣合同|派遣员工", "派遣合同", "聘用合同签订主体为派遣机构"),
    ]

    # 2. 合同制/编外排除词
    CONTRACT_KEYWORDS = [
        (r"编外人员|编外聘用|编外聘用人员|编制外聘用", "明确编外", "公告明确招聘性质为编外聘用人员"),
        (r"合同制人员|合同聘用|聘用制人员|合同制管理", "合同制用工", "公告载明为合同制/聘用制"),
        (r"不占编制|不占用编制|不纳入编制|不列入编制|不占事业编制", "不占编制", "明确说明招聘人员不占国家事业单位编制"),
        (r"购买服务|政府购买服务", "政府购买服务", "用人方式为政府购买服务岗位"),
        (r"项目聘用|临时用工|短期雇佣", "项目/临时聘用", "岗位为阶段性项目或临时聘用用工"),
        (r"自主招聘.*编外|自主用工", "单位自主编外用工", "招聘性质为医院/单位自主组织编外用工"),
    ]

    # 3. 报备员额 / 备案制
    BEIAN_KEYWORDS = [
        (r"人员总量|人员总量管理", "人员总量管理", "采用公立医院人员总量管理"),
        (r"备案制人员|备案制编制|公立医院备案制|员额备案制", "备案制管理", "属于公立医院人员备案制管理"),
        (r"公立医院公卫科.*员额|公立三甲.*报备员额|院感科.*员额", "三甲公立医院公卫员额", "公立医院公共卫生/院感岗位实行报备员额制管理"),
        (r"报备员额|员额制", "报备员额", "实行事业单位报备员额制管理"),
        (r"控制总量", "控制总量", "纳入事业单位人员控制总量管理"),
        (r"同工同酬员额|员额管理人员", "员额管理", "明确实行公立机构员额管理"),
    ]

    # 4. 全额事业编强证据
    QUAN_E_KEYWORDS = [
        (r"公益一类事业(单位|编制)", "公益一类事业单位", "单位性质为公益一类全额拨款事业单位", "全额事业编"),
        (r"财政全额拨款|全额拨款事业(单位|编制)|财政全额核拨|全额补助", "全额拨款事业单位", "财政全额拨款事业单位编制", "全额事业编"),
        (r"财政补助事业(单位|编制)", "财政补助事业单位", "财政补助事业单位正式编制", "全额事业编"),
        (r"实名制事业编制|实名制编制|事业编制实名制|机构编制实名制|实名制入编", "实名制编制", "办理实名制事业单位录用入编手续", "全额事业编"),
        (r"进站即入编|出站留编|博后带编|联合培养带编|卓越公卫学者入编", "博士后/卓越公卫学者带编引才", "高校/疾控博士后或卓越公卫学者入站即落实全额事业编制", "全额事业编"),
        (r"行政编制|公务员招录|口岸关务员|海关公务员|参公编制", "行政/参公编制", "岗位明确属于国家行政编制或参公管理", "行政编制"),
        (r"事业编制人员|正式编制人员|在编人员|核定事业编制", "明确在编人员", "招考公告明确声明招录事业单位正式在编人员", "全额事业编"),
        (r"事业单位公开招聘工作人员|事业单位统一公开招聘|直聘事业单位编制", "事业单位公开招聘", "属于人社部门/卫健委统一组织的标准事业单位公开招聘/直聘", "全额事业编"),
        (r"统一公开招聘考试", "事业编统考", "属于各省市事业单位统一公开招聘考试", "全额事业编"),
        (r"事业编制", "事业编制", "岗位明确标注事业编制", "全额事业编"),
    ]

    # 5. 差额/自收自支事业编
    CHA_E_KEYWORDS = [
        (r"差额拨款事业(单位|编制)", "差额拨款事业单位", "财政差额拨款事业单位编制"),
        (r"差额补助事业(单位|编制)", "差额补助事业单位", "财政差额补助事业单位编制"),
        (r"自收自支事业(单位|编制)", "自收自支事业编", "自收自支事业单位编制"),
        (r"经费自理事业单位", "经费自理", "经费自理事业单位编制"),
    ]

    # 6. 单位类型基准偏置
    UNIT_TYPE_BIAS = {
        "疾控中心": {"score": 0.45, "reason": "疾病预防控制中心（CDC）普遍为政府全额拨款公益一类事业单位"},
        "卫生监督": {"score": 0.45, "reason": "卫生监督机构普遍为行政执法/参公/全额拨款事业单位"},
        "综合医院/专科医院": {"score": -0.2, "reason": "公立综合/专科医院普遍推行人员总量备案制或自主合同用工，需细致甄别"},
        "妇幼保健": {"score": 0.1, "reason": "妇幼保健院多数为公益二类差额拨款事业单位或备案制"},
        "基层医疗卫生机构": {"score": 0.25, "reason": "社区卫生服务中心及乡镇卫生院多为全额或差额拨款事业单位"},
        "医学科研/院校": {"score": 0.15, "reason": "医学院校及医学科研机构多数为财政差额/全额事业单位"},
        "其他事业单位": {"score": 0.0, "reason": "其他事业单位常规评估"}
    }

    # 7. 定向培养/公费公卫医师/订单式入编强确编证据
    ORIENTED_BINDING_KEYWORDS = [
        (r"定向培养.*(?:入编|编制|事业编)|订单定向.*(?:编制|事业编)|公费公卫医师.*(?:编制|入编)", "定向/公费入编", "订单定向培养或公费公卫医师项目明确入编安排"),
        (r"全科医生定向培养.*(?:在编|入编|编制)|农村订单定向医学生.*(?:编制|入编)", "基层全科定向入编", "基层全科/农村订单定向医学生毕业入编安置"),
        (r"专项编制保障|单列编制|周转编制|编制专项", "专项编制保障", "人社/编制部门核定的专项或周转编制保障"),
        (r"人才池编制|人才周转池事业编制|编制周转池", "人才周转池编制", "属于政府/卫健委核定的人才周转池全额事业编制"),
        (r"高校附属公卫中心编制|国家区域公共卫生中心带编", "区域公卫中心带编", "依托国家/省区域公共卫生中心设立的专项事业编制"),
    ]

    @classmethod
    def evaluate(
        cls,
        job_name: str = "",
        unit_name: str = "",
        unit_type: str = "其他事业单位",
        other_requirements: str = "",
        announcement_title: str = "",
        announcement_text: str = "",
        text: Optional[str] = None,
        source_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        升级版编制研判评分与自然语言证据链生成
        兼容 text 与 source_name 等直接入参
        """
        if text:
            announcement_text = f"{text} {announcement_text}"
        if source_name:
            announcement_title = f"{source_name} {announcement_title}"

        full_text = f"{announcement_title} {job_name} {unit_name} {other_requirements} {announcement_text[:1500]}"
        evidence_chain: List[str] = []
        evidence_list: List[str] = []

        # 自动推导单位类型（若为默认其他且名称含有特征词）
        derived_unit_type = unit_type
        if derived_unit_type == "其他事业单位":
            if "疾病预防控制" in full_text or "疾控" in full_text or "CDC" in full_text:
                derived_unit_type = "疾控中心"
            elif "卫生监督" in full_text:
                derived_unit_type = "卫生监督"
            elif "妇幼保健" in full_text:
                derived_unit_type = "妇幼保健"
            elif "医院" in full_text:
                derived_unit_type = "综合医院/专科医院"
            elif "卫生院" in full_text or "社区卫生" in full_text:
                derived_unit_type = "基层医疗卫生机构"

        # ----------------------------------------------------
        # 阶段 1: 检查合同制 / 编外聘用 / 劳务派遣 (红标判定)
        # ----------------------------------------------------
        has_dispatch = False
        for pat, term, reason in cls.DISPATCH_KEYWORDS:
            if re.search(pat, full_text):
                if term not in evidence_chain:
                    evidence_chain.append(term)
                evidence_list.append(f"【派遣证据】{reason}")
                has_dispatch = True

        for pat, term, reason in cls.CONTRACT_KEYWORDS:
            if re.search(pat, full_text):
                if term not in evidence_chain:
                    evidence_chain.append(term)
                evidence_list.append(f"【排除证据】{reason}")

        if evidence_chain:
            evidence_str = "; ".join(evidence_list)
            b_type = "合同制"
            return {
                "is_bianzhi": 0,
                "bianzhi_type": b_type,
                "confidence": 0.98 if has_dispatch else 0.95,
                "evidence_chain": evidence_chain,
                "evidence_details": evidence_str,
                "bianzhi_confidence": 0.98 if has_dispatch else 0.95,
                "bianzhi_evidence": evidence_str,
                "risk_notes": "非编警告：此岗位为编外合同制/劳务派遣聘用，不占国家事业单位编制。",
                "action_advice": "若追求事业编制稳定性，建议慎重或直接放弃该岗位。"
            }

        # ----------------------------------------------------
        # 阶段 3: 检查报备员额 / 备案制 / 人员总量
        # ----------------------------------------------------
        for pat, term, reason in cls.BEIAN_KEYWORDS:
            if re.search(pat, full_text):
                if term not in evidence_chain:
                    evidence_chain.append(term)
                evidence_list.append(f"【员额/备案证据】{reason}")

        if evidence_chain:
            evidence_str = "; ".join(evidence_list)
            return {
                "is_bianzhi": 2,
                "bianzhi_type": "报备员额",
                "confidence": 0.75,
                "evidence_chain": evidence_chain,
                "evidence_details": evidence_str,
                "bianzhi_confidence": 0.75,
                "bianzhi_evidence": evidence_str,
                "risk_notes": "存疑提示：该岗位属于公立医院改革推广的报备员额/总量备案制，薪酬福利对标在编但无实名制编制卡。",
                "action_advice": "经济发达地区公立三甲医院员额制待遇优厚，具备较高报考价值，可与用人单位进一步核实晋升调动通道。"
            }

        # ----------------------------------------------------
        # 阶段 4: 检查强确编 (全额 / 差额事业编)
        # ----------------------------------------------------
        score = 0.0
        strong_found = False
        determined_type = None

        # 差额/自收自支检查
        for pat, term, reason in cls.CHA_E_KEYWORDS:
            if re.search(pat, full_text):
                score += 0.45
                if term not in evidence_chain:
                    evidence_chain.append(term)
                evidence_list.append(f"【差额确编】{reason}")
                strong_found = True
                determined_type = "差额事业编"

        # 全额拨款检查
        for pat, term, reason, b_type in cls.QUAN_E_KEYWORDS:
            if re.search(pat, full_text):
                score += 0.55
                if term not in evidence_chain:
                    evidence_chain.append(term)
                evidence_list.append(f"【确编证据】{reason}")
                strong_found = True
                if not determined_type:
                    determined_type = b_type

        # 定向/公费公卫医师强确编检查（额外加分，用于基层定向与公费项目）
        for pat, term, reason in cls.ORIENTED_BINDING_KEYWORDS:
            if re.search(pat, full_text):
                score += 0.5
                if term not in evidence_chain:
                    evidence_chain.append(term)
                evidence_list.append(f"【定向确编】{reason}")
                strong_found = True
                if not determined_type:
                    determined_type = "全额事业编"

        # 结合用人单位类型偏置
        bias = cls.UNIT_TYPE_BIAS.get(derived_unit_type, {"score": 0.0, "reason": ""})
        if bias["score"] != 0:
            score += bias["score"]
            if bias["reason"]:
                evidence_list.append(f"【单位性质】{bias['reason']}")

        if not determined_type:
            determined_type = "全额事业编"

        # ----------------------------------------------------
        # 阶段 5: 综合决策阈值判定
        # ----------------------------------------------------
        if strong_found and score >= 0.5:
            confidence = min(round(0.85 + score * 0.15, 2), 0.99)
            evidence_str = "; ".join(evidence_list)
            return {
                "is_bianzhi": 1,
                "bianzhi_type": determined_type,
                "confidence": confidence,
                "evidence_chain": evidence_chain,
                "evidence_details": evidence_str,
                "bianzhi_confidence": confidence,
                "bianzhi_evidence": evidence_str,
                "risk_notes": "正式在编：确认为国家事业单位正式实名制编制，享有完备的体制内保障。",
                "action_advice": "建议重点关注并按时完成报名与资格审查。"
            }
        elif strong_found or score >= 0.35:
            confidence = min(round(0.70 + score * 0.2, 2), 0.92)
            evidence_str = "; ".join(evidence_list)
            return {
                "is_bianzhi": 1,
                "bianzhi_type": determined_type,
                "confidence": confidence,
                "evidence_chain": evidence_chain,
                "evidence_details": evidence_str,
                "bianzhi_confidence": confidence,
                "bianzhi_evidence": evidence_str,
                "risk_notes": "高概率在编：命中多项事业单位公开招考特征。",
                "action_advice": "大概率为正式事业单位编制，建议积极关注并进一步核对拟聘公示及简章细则。"
            }
        else:
            # 医院等若无明确编制说明，归入报备员额/存疑
            b_type = "报备员额" if derived_unit_type == "综合医院/专科医院" else "未知"
            evidence_str = "; ".join(evidence_list) if evidence_list else "未明确说明编制属性"
            return {
                "is_bianzhi": 2,
                "bianzhi_type": b_type,
                "confidence": 0.45,
                "evidence_chain": evidence_chain,
                "evidence_details": evidence_str,
                "bianzhi_confidence": 0.45,
                "bianzhi_evidence": evidence_str,
                "risk_notes": "编制存疑：简章中未明确标注事业单位正式编制、员额制或编外用工属性。",
                "action_advice": "建议致电招考单位人社或卫健委政工人事科电话核实具体用工属性及是否实名制入编。"
            }
