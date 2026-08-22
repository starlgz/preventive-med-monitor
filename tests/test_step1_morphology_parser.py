import pytest
import os
from app.parsers.column_mapper import ColumnMapper
from app.parsers.excel_parser import ExcelJobParser

def test_column_mapper_single_header():
    headers = ["序号", "招聘单位", "岗位代码", "招聘岗位", "招聘人数", "学历要求", "专业要求", "其他条件"]
    mapping = ColumnMapper.map_columns(headers)
    assert mapping["unit_name"] == 1
    assert mapping["job_code"] == 2
    assert mapping["job_name"] == 3
    assert mapping["headcount"] == 4
    assert mapping["education"] == 5
    assert mapping["major"] == 6
    assert mapping["other_requirements"] == 7
    # 确保序号没有被误识别为岗位
    assert "序号" not in mapping

def test_column_mapper_exclude_patterns():
    headers = ["序号", "岗位类别", "专业技术等级", "招聘总表", "备注说明"]
    mapping = ColumnMapper.map_columns(headers)
    assert "job_name" not in mapping  # 不应把岗位类别或总表当成 job_name
    assert "major" not in mapping     # 不应把专业技术等级当成 major

def test_multi_header_synthesis():
    row1 = ["单位名称", "岗位信息", "", "资格条件", "", ""]
    row2 = ["", "岗位名称", "人数", "学历", "专业及代码", "其他要求"]
    synthesized = ColumnMapper.synthesize_multi_headers([row1, row2])
    mapping = ColumnMapper.map_columns(synthesized)
    assert mapping["unit_name"] == 0
    assert mapping["job_name"] == 1
    assert mapping["headcount"] == 2
    assert mapping["education"] == 3
    assert mapping["major"] == 4
    assert mapping["other_requirements"] == 5

def test_excel_job_parser_real_files():
    # 测试真实已下载的附件
    test_file_xls = "data/attachments/871b786ece749bf1_2026年度日照市人民医院公开招聘急需紧缺人才岗位汇总表.xls"
    if os.path.exists(test_file_xls):
        jobs = ExcelJobParser.parse_file(test_file_xls, default_unit_name="日照市人民医院")
        assert len(jobs) > 0
        # 确保没有序号行
        for j in jobs:
            assert j["job_name"] not in ["1", "2", "3", "序号", "1.0", "2.0"]
            assert j["unit_name"] != ""
            assert j["headcount"] >= 1

    test_file_xlsx = "data/attachments/93089a5d10a8abfc_南京市卫生健康委员会所属部分事业单位2026年公开招聘高层次人才岗位信息表第一批.xlsx"
    if os.path.exists(test_file_xlsx):
        jobs2 = ExcelJobParser.parse_file(test_file_xlsx, default_unit_name="南京市卫健委")
        assert len(jobs2) > 0
        for j in jobs2:
            assert j["job_name"] != ""
            assert j["headcount"] >= 1
