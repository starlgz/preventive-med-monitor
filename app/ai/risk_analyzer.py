from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.entities import Job
from app.ai.llm_client import OpenAICompatibleClient
from loguru import logger

class JobRiskAnalyzer:
    """
    AI 报考资格与风险研判模块:
    低成本漏斗策略: 规则初筛 -> 复杂/存疑/高星级岗位触发 AI 深度资格与避坑风险研判
    """

    SYSTEM_PROMPT = """你是一名资深的中国医药卫生与公共卫生事业单位招考报考规划专家。
你的任务是对招考岗位的报考资格、限制条件、隐形门槛及考编风险进行深度研判。

请严格输出 JSON 格式，包含以下字段：
{
  "is_eligible_summary": "一句话资格概括",
  "major_compliance": "专业契合度分析（预防医学/公卫各专业报考难度与注意事项）",
  "experience_cert_risks": ["执业资格/规培/工作年限等核心风险点1", "风险点2"],
  "bianzhi_security_level": "编制安全性评级 (极高/高/中等/存疑/非编) 及理由",
  "hidden_pitfalls": ["潜在避坑提示（如基层最低服务年限、违约金、差额考察淘汰率等）"],
  "expert_advice": "给预防医学考生的报考策略与复习建议"
}
"""

    @classmethod
    async def analyze_job_risk(
        cls, 
        job_data: Dict[str, Any], 
        client: Optional[OpenAICompatibleClient] = None
    ) -> Dict[str, Any]:
        """
        对单个岗位进行 AI 资格与风险研判
        """
        llm = client or OpenAICompatibleClient()
        
        user_prompt = f"""请研判以下事业单位招考岗位的报考条件与风险：
招考单位：{job_data.get('unit_name')}（单位类型：{job_data.get('unit_type', '未知')}）
招聘岗位：{job_data.get('job_name')}（招聘人数：{job_data.get('headcount', 1)}人）
专业要求：{job_data.get('major_raw')}
学历学位：{job_data.get('education')}
应届要求：{'限应届生' if job_data.get('is_fresh_grad') == 1 else ('限往届/经验' if job_data.get('is_fresh_grad') == 2 else '不限')}
证书要求：{job_data.get('cert_requirements', '无明确证书限制')}
年龄上限：{job_data.get('age_limit_num', '无明确限制')}周岁
编制类型：{job_data.get('bianzhi_type', '未知')} (置信度: {job_data.get('bianzhi_confidence', 0.5)})
编制证据：{job_data.get('bianzhi_evidence', '无')}
其他条件与备注：{job_data.get('other_requirements', '无')}
"""
        logger.info(f"触发 AI 岗位资格与风险研判: {job_data.get('unit_name')} - {job_data.get('job_name')}")
        result = await llm.chat_completion(cls.SYSTEM_PROMPT, user_prompt)
        return result
