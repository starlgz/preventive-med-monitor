import re

class UnitTypeClassifier:
    """用人单位类型智能分类器"""

    CATEGORIES = [
        ("疾控中心", [r"疾病预防控制", r"疾控中心", r"CDC", r"防疫站", r"预防控制"]),
        ("卫健局/委", [r"卫生健康委员会", r"卫生健康局", r"卫健委", r"卫健局", r"卫生局"]),
        ("卫生监督", [r"卫生监督", r"卫监所", r"卫生健康行政执法"]),
        ("妇幼保健院", [r"妇幼保健", r"妇幼保健院", r"妇保院", r"妇女儿童医院"]),
        ("公立医院", [r"医院", r"医疗中心", r"诊所", r"卫生院", r"社区卫生服务中心"]),
        ("科研院所", [r"医学科学院", r"研究所", r"研究院", r"医学院", r"大学", r"科研所"]),
        ("急救中心", [r"急救中心", r"紧急救援", r"120"]),
    ]

    @classmethod
    def classify(cls, unit_name: str) -> str:
        if not unit_name:
            return "其他事业单位"

        for category, patterns in cls.CATEGORIES:
            for pat in patterns:
                if re.search(pat, unit_name, re.IGNORECASE):
                    return category

        return "其他事业单位"
