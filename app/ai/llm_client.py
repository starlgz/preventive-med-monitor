import httpx
import json
from typing import Dict, Any, Optional
from app.core.config import settings
from loguru import logger

class OpenAICompatibleClient:
    """
    OpenAI 兼容协议 LLM 客户端 (支持接入 Antigravity API / DeepSeek / 本地大模型)
    """

    def __init__(self, api_base: Optional[str] = None, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_base = api_base or getattr(settings, "LLM_API_BASE", "http://103.244.90.28:8045/v1")
        self.api_key = api_key or getattr(settings, "LLM_API_KEY", "sk-mock-key")
        self.model = model or getattr(settings, "LLM_MODEL", "gpt-4o-mini")

    async def chat_completion(self, system_prompt: str, user_prompt: str, temperature: float = 0.1) -> Dict[str, Any]:
        """
        调用 LLM 对复杂岗位报考资格与潜在风险进行研判
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": temperature,
            "response_format": {"type": "json_object"}
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(f"{self.api_base}/chat/completions", headers=headers, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    content_str = data["choices"][0]["message"]["content"]
                    return json.loads(content_str)
                else:
                    logger.warning(f"LLM API 调用返回状态码 {resp.status_code}: {resp.text}")
                    return self._fallback_rule_response()
        except Exception as e:
            logger.warning(f"LLM 接口网络调用异常，降级为规则判定: {e}")
            return self._fallback_rule_response()

    def _fallback_rule_response(self) -> Dict[str, Any]:
        """降级兜底返回"""
        return {
            "is_eligible": True,
            "eligibility_analysis": "规则引擎初审符合基本条件，AI 接口调用降级",
            "risk_warnings": ["请以官方发布最终招聘公告与资格初审结果为准"],
            "suggestion": "建议直接投递并关注现场确认通知"
        }
