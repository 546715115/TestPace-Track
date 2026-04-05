"""
Excel 数据解析模块
处理合并单元格、字段合并、日期和进度标准化
"""
import openpyxl
import re
from datetime import datetime
from typing import List, Dict, Any, Tuple

# 字段类型定义
YES_NO_FIELDS = {'是否变更接口', '是否涉及资料', '是否涉及性能、过载', '是否涉及可靠性'}
PERSONNEL_FIELDS = {'测试人员', '开发人员', 'TSE', '业务团队'}
DATE_FIELDS = {'计划转测时间', '资料转测时间', '需求串讲/设计完成日期'}


def parse_date(value) -> str:
    """解析多种日期格式，统一为 YYYY/MM/DD"""
    if value is None or str(value).strip() == '':
        return ''

    val = str(value).strip()

    # 已是目标格式
    if re.match(r'\d{4}/\d{1,2}/\d{1,2}', val):
        parts = val.split('/')
        return f"{int(parts[0]):04d}/{int(parts[1]):02d}/{int(parts[2]):02d}"

    # 点分隔符
    if re.match(r'\d{4}\.\d{1,2}\.\d{1,2}', val):
        parts = val.split('.')
        return f"{int(parts[0]):04d}/{int(parts[1]):02d}/{int(parts[2]):02d}"

    # 短格式（假设当前年份）
    if re.match(r'\d{1,2}/\d{1,2}', val):
        parts = val.split('/')
        year = datetime.now().year
        return f"{year}/{int(parts[0]):02d}/{int(parts[1]):02d}"

    if re.match(r'\d{1,2}\.\d{1,2}', val):
        parts = val.split('.')
        year = datetime.now().year
        return f"{year}/{int(parts[0]):02d}/{int(parts[1]):02d}"

    return str(value)


def normalize_progress(value) -> int:
    """标准化进度为整数百分比"""
    if value is None or str(value).strip() == '':
        return 0

    val = str(value).strip()

    if val == '已完成':
        return 100

    val = val.replace('%', '')

    try:
        return int(float(val))
    except:
        return 0


def merge_yes_no_field(values: list) -> str:
    """合并是否类字段：任意'是'则为'是'"""
    for v in values:
        if v == '是':
            return '是'
    return '否'


def merge_personnel_field(values: list) -> str:
    """合并人员类字段：去重拼接"""
    non_null = [v for v in values if v and str(v).strip() and str(v) != '/']
    unique = list(dict.fromkeys(non_null))  # 保持顺序，去重
    return ', '.join(unique) if unique else ''


def merge_value_field(values: list):
    """合并数值类字段：取第一个非空值"""
    for v in values:
        if v is not None and str(v).strip():
            return v
    return ''


class ExcelReader:
    """Excel 读取器，解析合并单元格"""

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.workbook = None
        self.current_sheet = None
        self._load()

    def _load(self):
        self.workbook = openpyxl.load_workbook(self.file_path, data_only=True)

    def get_sheet_names(self) -> List[str]:
        return self.workbook.sheetnames

    def get_headers(self, sheet_name: str) -> List[str]:
        ws = self.workbook[sheet_name]
        return [cell.value for cell in ws[1]]

    def load_sheet(self, sheet_name: str):
        self.current_sheet = sheet_name

    def get_merged_ranges(self) -> list:
        """获取所有合并单元格区域"""
        ws = self.workbook[self.current_sheet]
        return list(ws.merged_cells.ranges)

    def get_requirement_groups(self) -> list:
        """
        基于 Column A（特性分类）合并单元格检测需求组
        返回: [{'rows': [2,3,4,5], 'is_merged': True}, ...]
        """
        ws = self.workbook[self.current_sheet]
        groups = []
        merged_ranges = list(ws.merged_cells.ranges)

        # 找出 Column A 的合并区域
        col_a_merges = []
        for mr in merged_ranges:
            if mr.min_col == 1 and mr.max_col == 1:
                col_a_merges.append({
                    'min_row': mr.min_row,
                    'max_row': mr.max_row
                })

        # 添加合并组
        for mr in sorted(col_a_merges, key=lambda x: x['min_row']):
            groups.append({
                'rows': list(range(mr['min_row'], mr['max_row'] + 1)),
                'is_merged': True
            })

        # 找出被合并的行
        merged_rows = set()
        for mr in col_a_merges:
            for r in range(mr['min_row'], mr['max_row'] + 1):
                merged_rows.add(r)

        # 添加非合并的单行
        for row_idx in range(2, ws.max_row + 1):
            if row_idx not in merged_rows:
                groups.append({
                    'rows': [row_idx],
                    'is_merged': False
                })

        return groups

    def merge_group(self, group: dict) -> dict:
        """
        合并需求组为单行数据
        根据字段类型应用不同的合并逻辑
        """
        ws = self.workbook[self.current_sheet]
        headers = self.get_headers(self.current_sheet)
        result = {}

        for col_idx, header in enumerate(headers, start=1):
            values = []

            for row_idx in group['rows']:
                cell = ws.cell(row=row_idx, column=col_idx)
                values.append(cell.value)

            # 根据字段类型应用合并逻辑
            if header in YES_NO_FIELDS:
                result[header] = merge_yes_no_field(values)
            elif header in PERSONNEL_FIELDS:
                result[header] = merge_personnel_field(values)
            elif any(kw in str(header) for kw in ['进度', '进度（%）']):
                result[header] = normalize_progress(merge_value_field(values))
            elif any(kw in str(header) for kw in ['时间', '日期']):
                result[header] = parse_date(merge_value_field(values))
            else:
                result[header] = merge_value_field(values)

        # 保留元数据
        result['_rows'] = group['rows']
        result['_is_merged'] = group['is_merged']
        return result

    def get_all_requirements(self) -> Tuple[List[Dict], List[Dict]]:
        """
        获取所有解析后的需求和分组信息
        返回: (merged_requirements, groups)
        """
        groups = self.get_requirement_groups()
        merged = [self.merge_group(g) for g in groups]
        return merged, groups


if __name__ == '__main__':
    # 测试代码
    import os
    test_file = os.path.join(os.path.dirname(__file__), '..', 'test_read_copy.xlsx')
    if os.path.exists(test_file):
        reader = ExcelReader(test_file)
        print("Sheets:", reader.get_sheet_names())

        reader.load_sheet('0330需求列表')
        groups = reader.get_requirement_groups()
        print(f"Found {len(groups)} groups")

        if groups:
            merged = reader.merge_group(groups[0])
            print("First merged row keys:", list(merged.keys())[:5])
