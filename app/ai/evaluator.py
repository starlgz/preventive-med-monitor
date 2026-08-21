import json
import httpx
from typing import Dict, Any, Optional
from loguru import logger

class AIEligibilityEvaluator:
    """
    AI 报考资格与风险研判模块
    采用“低成本规则漏斗 + 大模型深度研判”双层架构：
    1. 规则漏斗：明确对口/明确排除岗位直接由规则判定 (0 Token 消耗)
    2. AI 研判：针对边界模糊岗位 (2星/3星/存疑编制)，调用 OpenAI 兼容 API 生成研判理由与风险提示
    """

    PROMPT_TEMPLATE = """你是一名中国预防医学与卫生事业编招考专家。请分析以下岗位与考生的匹配度、编制真实性及报考风险。

【招考单位】：{unit_name} ({unit_type})
【岗位名称】：{job_name}
【学历要求】：{education}
【专业要求】：{major_raw}
【证书及其他条件】：{cert_requirements}
【公告标题】：{announcement_title}

【考生画像】：
- 毕业专业：{user_major}
- 最高学历：{user_education}
- 考生身份：{user_fresh}
- 执业证书：{user_cert}
- 所在年龄：{user_age}岁

请以 JSON 格式输出分析结果，必须包含以下字段：
1. eligibility: true/false (是否具备报名资格)
2. match_score: 1-100 的整数评分
3. is_bianzhi_safe: true/false (编制是否确切为实名事业编/安全)
4. reason: 简明扼要的资格匹配分析
5. risk_warnings: 潜在风险提示列表 (如：可能属于院内自聘/需规培证/户籍限制/现场审核严格等)
"""

    @classmethod
    async def evaluate_eligibility(
        cls,
        job_data: Dict[str, Any],
        user_profile: Dict[str, Any],
        api_base: Optional[str] = "http://103.244.90.28:8045/v1",
        api_key: Optional[str] = "sk-antigravity",
        model: Optional[str] = "gpt-4o-mini"
    ) -> Dict[str, Any]:
        """
        双层漏斗研判：
        1. 快速规则过滤 (0 Token)
        2. LLM 深度研判 (模糊岗位/存疑编制)
        """
        major_raw = job_data.get("major_raw", "")
        match_level = job_data.get("match_level", 2)
        is_bianzhi = job_data.get("is_bianzhi", 2)

        # 规则快速直通车：5星且绿标编制且无复杂证书限制 -> 0 Token 判定
        if match_level == 5 and is_bianzhi == 1 and not job_data.get("cert_requirements"):
            return {
                "eligibility": True,
                "match_score": 98,
                "is_bianzhi_safe": True,
                "reason": "【规则快速通道】专业完全对口(5星)，且属于实名制事业编制，无附加门槛证书限制。",
                "risk_warnings": ["注意关注现场资格复审时间", "留意报名表照片及政审证明材料规范"],
                "engine": "RULE_FAST_TRACK"
            }

        # 规则快速否决车：1星排除专业或明确非编劳务派遣 -> 0 Token 判定
        if match_level == 1 or is_bianzhi == 0:
            return {
                "eligibility": False,
                "match_score": 20,
                "is_bianzhi_safe": False,
                "reason": "【规则快速通道】岗位为编外派遣性质或专业明确不符，不建议报考。",
                "risk_warnings": ["属于第三方劳动合同/劳务派遣", "无体制内事业编制保障"],
                "engine": "RULE_FAST_TRACK"
            }

        # 进入 AI 深度研判 (兼容 OpenAI 协议)
        prompt = cls.PROMPT_TEMPLATE.format(
            unit_name=job_data.get("unit_name", "未知单位"),
            unit_type=job_data.get("unit_type", "事业单位"),
            job_name=job_data.get("job_name", "公卫岗"),
            education=job_data.get("education", "本科"),
            major_raw=major_raw,
            cert_requirements=job_data.get("cert_requirements", "无"),
            announcement_title=job_data.get("announcement_title", "招考公告"),
            user_major=user_profile.get("major", "预防医学"),
            user_education=user_profile.get("education", "本科"),
            user_fresh="应届毕业生" if user_profile.get("is_fresh_grad", True) else "往届生",
            user_cert="具有公卫执业医师证" if user_profile.get("has_cert", False) else "暂无执业医师证",
            user_age=user_profile.get("age", 25)
        )

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "model": model,
                    "messages": [
                        {"role": "system", "content": "You are a professional recruitment analyst. Return valid JSON only."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.2
                }
                resp = await client.post(f"{api_base.rstrip('/')}/chat/completions", headers=headers, json=payload)
                if resp.status_code == 200:
                    content = resp.json()["choices"][0]["message"]["content"]
                    # 解析 JSON
                    content = content.replace("```json", "").replace("```", "").strip()
                    res_json = json.loads(content)
                    res_json["engine"] = "AI_LLM_DEEP_EVAL"
                    return res_json
        except Exception as e:
            logger.warning(f"AI 研判接口调用异常 (降级为智能规则判定): {e}")

        # 降级兜底研判
        return {
            "eligibility": True if match_level >= 3 else False,
            "match_score": 75 if match_level >= 3 else 45,
            "is_bianzhi_safe": True if is_bianzhi == 1 else False,
            "reason": f"【降级研判】专业匹配评定为 {match_level} 星，编制标识为 {is_bianzhi}，建议结合现场报名确认条件。",
            "risk_warnings": [
                "建议电话咨询用人单位确认公卫专业代码是否在认可目录内",
                "关注是否要求毕业2年内算应届身份"
            ],
            "engine": "FALLBACK_RULE_ENGINE"
        }
