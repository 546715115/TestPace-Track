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