import openpyxl
import xlrd
from typing import List, Dict, Any, Optional
from app.core.logger import logger
from app.parsers.column_mapper import ColumnMapper

class ExcelJobParser:
    """Excel 岗位表专用解析器 (支持 .xlsx, .xls，支持合并单元格自动向下/向右继承填充)"""

    @classmethod
    def parse_file(cls, file_path: str, default_unit_name: Optional[str] = None) -> List[Dict[str, Any]]:
        if file_path.endswith(".xlsx"):
            return cls._parse_xlsx(file_path, default_unit_name)
        elif file_path.endswith(".xls"):
            return cls._parse_xls(file_path, default_unit_name)
        else:
            logger.warning(f"Unsupported excel format: {file_path}")
            return []

    @classmethod
    def _parse_xlsx(cls, file_path: str, default_unit_name: Optional[str]) -> List[Dict[str, Any]]:
        jobs = []
        try:
            wb = openpyxl.load_workbook(file_path, data_only=True)
            for sheet_name in wb.sheetnames:
                ws = wb[sheet_name]
                sheet_jobs = cls._parse_worksheet(ws, default_unit_name)
                jobs.extend(sheet_jobs)
            wb.close()
        except Exception as e:
            logger.error(f"Error parsing xlsx file {file_path}: {e}")
        return jobs

    @classmethod
    def _parse_worksheet(cls, ws, default_unit_name: Optional[str]) -> List[Dict[str, Any]]:
        rows_data = []
        for row in ws.iter_rows(values_only=False):
            row_vals = [cell.value for cell in row]
            rows_data.append(row_vals)

        if not rows_data:
            return []

        # 1. 查找表头行
        header_row_idx = -1
        col_map = {}
        for idx, row in enumerate(rows_data):
            str_row = [str(c or "").strip() for c in row]
            mapped = ColumnMapper.map_columns(str_row)
            if "job_name" in mapped or "major" in mapped:
                header_row_idx = idx
                col_map = mapped
                break

        if header_row_idx == -1:
            return []

        # 2. 合并单元格自动向下填充处理
        merged_ranges = list(ws.merged_cells.ranges)
        
        jobs = []
        last_unit = default_unit_name or ""

        for r_idx in range(header_row_idx + 1, len(rows_data)):
            row = rows_data[r_idx]
            # 还原合并单元格的值 (如果是合并区域中的从属单元格，取左上角单元格值)
            clean_row = []
            for c_idx, cell_val in enumerate(row):
                actual_val = cell_val
                # 检查是否落在合并区域
                for m_range in merged_ranges:
                    if (r_idx + 1 >= m_range.min_row and r_idx + 1 <= m_range.max_row and
                        c_idx + 1 >= m_range.min_col and c_idx + 1 <= m_range.max_col):
                        top_left_cell = ws.cell(row=m_range.min_row, column=m_range.min_col)
                        actual_val = top_left_cell.value
                        break
                clean_row.append(str(actual_val or "").strip())

            # 如果整行为空或包含表头重复字样，跳过
            if not any(clean_row):
                continue
            if clean_row[col_map.get("job_name", 0)] in ["岗位名称", "招考职位", "招聘岗位"]:
                continue

            unit = clean_row[col_map["unit_name"]] if "unit_name" in col_map and col_map["unit_name"] < len(clean_row) else ""
            if unit:
                last_unit = unit
            else:
                unit = last_unit

            job_name = clean_row[col_map["job_name"]] if "job_name" in col_map and col_map["job_name"] < len(clean_row) else ""
            major_raw = clean_row[col_map["major"]] if "major" in col_map and col_map["major"] < len(clean_row) else ""
            job_code = clean_row[col_map["job_code"]] if "job_code" in col_map and col_map["job_code"] < len(clean_row) else ""
            headcount_raw = clean_row[col_map["headcount"]] if "headcount" in col_map and col_map["headcount"] < len(clean_row) else "1"
            education = clean_row[col_map["education"]] if "education" in col_map and col_map["education"] < len(clean_row) else ""
            other_req = clean_row[col_map["other_requirements"]] if "other_requirements" in col_map and col_map["other_requirements"] < len(clean_row) else ""

            if not job_name and not major_raw:
                continue

            # 人数提取
            try:
                headcount = int(float(headcount_raw)) if headcount_raw else 1
            except:
                headcount = 1

            jobs.append({
                "unit_name": unit or default_unit_name or "未指定招聘单位",
                "job_name": job_name or "未命名岗位",
                "job_code": job_code,
                "headcount": headcount,
                "education": education,
                "major_raw": major_raw,
                "other_requirements": other_req
            })

        return jobs

    @classmethod
    def _parse_xls(cls, file_path: str, default_unit_name: Optional[str]) -> List[Dict[str, Any]]:
        jobs = []
        try:
            book = xlrd.open_workbook(file_path, formatting_info=True)
            for sheet in book.sheets():
                if sheet.nrows == 0:
                    continue
                header_row_idx = -1
                col_map = {}
                for r in range(min(10, sheet.nrows)):
                    row_vals = [str(sheet.cell_value(r, c)).strip() for c in range(sheet.ncols)]
                    mapped = ColumnMapper.map_columns(row_vals)
                    if len(mapped) >= 2 and ("job_name" in mapped or "major" in mapped):
                        header_row_idx = r
                        col_map = mapped
                        break
                if header_row_idx == -1:
                    continue

                last_unit = default_unit_name or ""
                for r in range(header_row_idx + 1, sheet.nrows):
                    row_vals = [str(sheet.cell_value(r, c)).strip() for c in range(sheet.ncols)]
                    if not any(row_vals):
                        continue
                    if "job_name" in col_map and row_vals[col_map["job_name"]] in ["岗位名称", "招考职位", "招聘岗位", "岗位\n名称", "岗位"]:
                        continue

                    unit = row_vals[col_map["unit_name"]] if "unit_name" in col_map and col_map["unit_name"] < len(row_vals) else ""
                    if unit:
                        last_unit = unit
                    else:
                        unit = last_unit

                    job_name = row_vals[col_map["job_name"]] if "job_name" in col_map and col_map["job_name"] < len(row_vals) else ""
                    major_raw = row_vals[col_map["major"]] if "major" in col_map and col_map["major"] < len(row_vals) else ""
                    if not job_name and not major_raw:
                        continue

                    headcount_raw = row_vals[col_map["headcount"]] if "headcount" in col_map and col_map["headcount"] < len(row_vals) else "1"
                    try:
                        headcount = int(float(headcount_raw)) if headcount_raw else 1
                    except:
                        headcount = 1

                    education = row_vals[col_map["education"]] if "education" in col_map and col_map["education"] < len(row_vals) else ""
                    other_req = row_vals[col_map["other_requirements"]] if "other_requirements" in col_map and col_map["other_requirements"] < len(row_vals) else ""

                    jobs.append({
                        "unit_name": unit or default_unit_name or "未指定招聘单位",
                        "job_name": job_name or "未命名岗位",
                        "job_code": row_vals[col_map["job_code"]] if "job_code" in col_map and col_map["job_code"] < len(row_vals) else "",
                        "headcount": headcount,
                        "education": education,
                        "major_raw": major_raw,
                        "other_requirements": other_req
                    })
        except Exception as e:
            logger.error(f"Error parsing xls file {file_path}: {e}")
        return jobs
