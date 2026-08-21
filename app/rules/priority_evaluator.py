from datetime import datetime, timedelta
from typing import Dict, Any, Optional

class PriorityEvaluator:
    """
    岗位通知优先级判定器
    等级定义 (V1.1 规范):
      - S 级 (紧急高价值/即时强提醒): 5星专业 + 绿标在编 + 距报名截止 <= 3天 (或今日首发疾控核心岗)
      - A 级 (高价值核心推送): 5星专业 + 绿标在编 (实名制事业编制)
      - B 级 (重要公卫推送): 4星专业 + 绿标在编，或 5星专业 + 黄标备案制/员额制
      - C 级 (常规监测记录): 3星对口岗位，或 4星+黄标/存疑，或 5星+红标非编(可选通知)
      - D 级 (待复核/低价值忽略): 2星模糊待查、1星排除专业、或普通非编合同工
    """

    @classmethod
    def evaluate(
        cls,
        match_level: int,
        is_bianzhi: int,
        apply_end_date: Optional[datetime] = None,
        unit_type: Optional[str] = "",
        now: Optional[datetime] = None
    ) -> Dict[str, Any]:
        now = now or datetime.now()
        
        # 1. 检查是否临期 (截止时间 <= 3天且未过期)
        is_expiring_soon = False
        if apply_end_date:
            days_left = (apply_end_date - now).total_seconds() / 86400.0
            if 0 <= days_left <= 3.0:
                is_expiring_soon = True

        priority = "C"
        reason = ""

        # 2. S 级判定：5星直接对口 + 绿标实名在编 + 临期 <= 3天
        if match_level == 5 and is_bianzhi == 1 and is_expiring_soon:
            priority = "S"
            reason = "5星核心预防医学 + 实名事业编制 + 报名即将截止(<=3天)，紧急置顶提醒"
        
        # 3. A 级判定：5星直接对口 + 绿标实名在编
        elif match_level == 5 and is_bianzhi == 1:
            priority = "A"
            reason = "5星核心预防医学 + 实名事业编制，核心重点推荐"

        # 4. B 级判定：
        #    - 4星公卫硕博 + 绿标实名在编
        #    - 5星预防医学 + 黄标报备员额制
        elif (match_level == 4 and is_bianzhi == 1) or (match_level == 5 and is_bianzhi == 2):
            priority = "B"
            if match_level == 4 and is_bianzhi == 1:
                reason = "4星公卫硕士/相关学科 + 实名事业编制，优质对口推荐"
            else:
                reason = "5星核心预防医学 + 报备员额制/存疑编制，高相关度推荐"

        # 5. C 级判定：
        #    - 3星业务对口 + 绿标/黄标
        #    - 4星公卫学科 + 黄标/存疑
        elif (match_level == 3 and is_bianzhi in (1, 2)) or (match_level == 4 and is_bianzhi == 2):
            priority = "C"
            reason = "业务对口大类或公卫相关岗位，纳入常规监控池"

        # 6. D 级判定：
        #    - 2星模糊
        #    - 1星排除
        #    - 0 红标非编合同工/劳务派遣
        else:
            priority = "D"
            if match_level <= 1:
                reason = "专业非预防医学/已排除专业，归为低优先级"
            elif is_bianzhi == 0:
                reason = "编外/劳务派遣合同工，归为低优先级"
            elif match_level == 2:
                reason = "专业要求模糊待人工核实，归为待复核队列"
            else:
                reason = "常规监测归档"

        return {
            "priority_level": priority,
            "priority_reason": reason,
            "is_expiring_soon": is_expiring_soon
        }
