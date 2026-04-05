import openpyxl
from typing import List, Dict, Any

class ExcelReader:
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

    def get_all_data(self, sheet_name: str) -> List[Dict[str, Any]]:
        ws = self.workbook[sheet_name]
        headers = self.get_headers(sheet_name)
        data = []
        for row in ws.iter_rows(min_row=2, values_only=True):
            if any(cell is not None for cell in row):
                data.append(dict(zip(headers, row)))
        return data

    def load_sheet(self, sheet_name: str):
        self.current_sheet = sheet_name

    def get_merged_ranges(self) -> list:
        ws = self.workbook[self.current_sheet]
        return list(ws.merged_cells.ranges)

    def get_requirement_groups(self) -> list:
        """Detect requirement groups based on merged cells in column A (特性分类)"""
        ws = self.workbook[self.current_sheet]
        groups = []
        merged_ranges = list(ws.merged_cells.ranges)

        # Find merged ranges in column A (特性分类)
        col_a_merges = []
        for mr in merged_ranges:
            if mr.min_col == 1 and mr.max_col == 1:
                col_a_merges.append({
                    'min_row': mr.min_row,
                    'max_row': mr.max_row
                })

        # Add merged groups
        for mr in sorted(col_a_merges, key=lambda x: x['min_row']):
            groups.append({
                'rows': list(range(mr['min_row'], mr['max_row'] + 1)),
                'is_merged': True
            })

        # Add non-merged rows
        merged_rows = set()
        for mr in col_a_merges:
            for r in range(mr['min_row'], mr['max_row'] + 1):
                merged_rows.add(r)

        for row_idx in range(2, ws.max_row + 1):
            if row_idx not in merged_rows:
                groups.append({
                    'rows': [row_idx],
                    'is_merged': False
                })

        return groups