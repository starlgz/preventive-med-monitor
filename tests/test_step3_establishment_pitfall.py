import pytest
from app.extractors.pitfall_extractor import PitfallExtractor

def test_bianzhi_formal():
    text = "本次公开招聘人员纳入事业单位编制管理，为财政全额拨款事业编制。"
    res = PitfallExtractor.evaluate_bianzhi("疾控专员", text)
    assert res["type"] == PitfallExtractor.TYPE_FORMAL
    assert res["confidence"] == "HIGH"
    assert "全额拨款" in " ".join(res["evidence_chain"])

def test_bianzhi_beian():
    text = "本次公立医院公开招聘实行人员总量控制，备案制管理，待遇同编同酬。"
    res = PitfallExtractor.evaluate_bianzhi("临床医师", text)
    assert res["type"] == PitfallExtractor.TYPE_BEIAN
    assert "备案制" in " ".join(res["evidence_chain"])

def test_bianzhi_labor_dispatch():
    text = "录用后与劳务派遣公司签订劳动合同，缴纳五险一金。"
    res = PitfallExtractor.evaluate_bianzhi("办公室文员", text)
    assert res["type"] == PitfallExtractor.TYPE_DISPATCH
    assert res["confidence"] == "HIGH"

def test_pitfall_analysis():
    job_desc = "公卫医师 具有公卫执业医师资格 限本地户籍"
    ann_text = "聘用后需在本单位最低服务满5年，服务期内不得调离或报考其他单位。"
    res = PitfallExtractor.analyze(job_desc, ann_text)
    assert res["risk_level"] in ["medium", "high"]
    tags = [p["tag"] for p in res["pitfall_items"]]
    assert any("服务期" in t for t in tags)
    assert any("户籍" in t for t in tags)
    assert any("执业医师" in t for t in tags)
