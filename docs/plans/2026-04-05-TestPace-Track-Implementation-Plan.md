# TestPace-Track Implementation Plan

> **For agentic workers:** 执行前请读取 `task_plan.md` 查看当前阶段状态

**Goal:** 构建测试进度跟踪 Web 工具
**Architecture:** Flask REST API + 原生 HTML/CSS/JS + SQLite + openpyxl
**Tech Stack:** Flask, openpyxl, SQLite, 原生 HTML/CSS/JS

---

## 项目结构

```
TestPace-Track/
├── app.py                      # Flask 主应用
├── config/
│   └── documents.json          # 文档配置
├── data/
│   ├── cache/                 # Excel 缓存（永久）
│   └── pace_track.db          # SQLite 数据库
├── modules/
│   ├── __init__.py
│   ├── db_manager.py           # 数据库管理
│   ├── config_manager.py      # 配置管理
│   ├── version_manager.py     # 版本计划 CRUD
│   ├── data_fetcher.py        # API 下载模块
│   ├── data_parser.py         # Excel 解析
│   ├── risk_analyzer.py        # 风险分析
│   └── stats_calculator.py     # 统计计算
├── templates/
│   └── index.html             # 前端页面
├── static/
│   ├── style.css              # 样式
│   └── app.js                 # 前端逻辑
└── tests/
    └── test_data_parser.py    # 测试
```

---

## Phase 1: 项目初始化

### Task 1: 创建目录结构和配置

```bash
mkdir -p modules static templates tests data/cache config
touch modules/__init__.py
```

创建 `config/documents.json`:
```json
{
  "documents": [
    {
      "version_id": "0330",
      "name": "0330需求列表",
      "bucket_path": "/7223826/479248",
      "doc_id": "31b5087ed7a95f70afe4b5bfbbe215c2"
    }
  ]
}
```

创建 `.gitignore`:
```
config/documents.json
data/cache/*.xlsx
data/*.db
__pycache__/
*.pyc
```

---

### Task 2: SQLite 数据库初始化

创建 `modules/db_manager.py`:

```python
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'pace_track.db')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS version_plan (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            version_id TEXT NOT NULL,
            version_name TEXT NOT NULL,
            stage_name TEXT NOT NULL,
            target_date TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
```

验证: `python -c "from modules.db_manager import init_db; init_db()"`

---

## Phase 2: 数据解析模块

### Task 3: Excel 读取

创建 `modules/data_parser.py`:

```python
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
    
    def load_sheet(self, sheet_name: str):
        self.current_sheet = sheet_name
    
    def get_merged_ranges(self) -> list:
        ws = self.workbook[self.current_sheet]
        return list(ws.merged_cells.ranges)
```

---

### Task 4: 合并单元格分组

```python
def get_requirement_groups(self) -> list:
    """基于 Column A 合并单元格检测需求组"""
    ws = self.workbook[self.current_sheet]
    groups = []
    merged_ranges = list(ws.merged_cells.ranges)
    
    col_a_merges = []
    for mr in merged_ranges:
        if mr.min_col == 1 and mr.max_col == 1:
            col_a_merges.append({
                'min_row': mr.min_row,
                'max_row': mr.max_row
            })
    
    for mr in sorted(col_a_merges, key=lambda x: x['min_row']):
        groups.append({
            'rows': list(range(mr['min_row'], mr['max_row'] + 1)),
            'is_merged': True
        })
    
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
```

---

### Task 5: 字段合并逻辑

```python
YES_NO_FIELDS = {'是否变更接口', '是否涉及资料', '是否涉及性能、过载', '是否涉及可靠性'}
PERSONNEL_FIELDS = {'测试人员', '开发人员', 'TSE', '业务团队'}

def merge_yes_no_field(values: list) -> str:
    for v in values:
        if v == '是':
            return '是'
    return '否'

def merge_personnel_field(values: list) -> str:
    non_null = [v for v in values if v and str(v).strip() and str(v) != '/']
    unique = list(dict.fromkeys(non_null))
    return ', '.join(unique) if unique else ''

def merge_value_field(values: list):
    for v in values:
        if v is not None and str(v).strip():
            return v
    return ''
```

---

### Task 6: 日期和进度标准化

```python
import re
from datetime import datetime

def parse_date(value) -> str:
    if value is None or str(value).strip() == '':
        return ''
    val = str(value).strip()
    
    if re.match(r'\d{4}/\d{1,2}/\d{1,2}', val):
        parts = val.split('/')
        return f"{int(parts[0]):04d}/{int(parts[1]):02d}/{int(parts[2]):02d}"
    
    if re.match(r'\d{4}\.\d{1,2}\.\d{1,2}', val):
        parts = val.split('.')
        return f"{int(parts[0]):04d}/{int(parts[1]):02d}/{int(parts[2]):02d}"
    
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
```

---

## Phase 3: 数据获取模块

### Task 7: API 下载

创建 `modules/data_fetcher.py`:

```python
import requests
import os
from datetime import datetime

class DataFetcher:
    def construct_download_url(self, bucket_path: str, doc_id: str) -> str:
        bucket_path = bucket_path.lstrip('/')
        return f"https://onebox.huawei.com/perfect/share/getDocOnlineDownloadUrl/{bucket_path}/{doc_id}"
    
    def get_download_link(self, bucket_path: str, doc_id: str) -> str:
        url = self.construct_download_url(bucket_path, doc_id)
        try:
            response = requests.get(url)
            data = response.json()
            return data.get('data')
        except Exception as e:
            print(f"Error: {e}")
            return None
    
    def download_excel(self, bucket_path: str, doc_id: str, save_path: str) -> bool:
        download_url = self.get_download_link(bucket_path, doc_id)
        if not download_url:
            return False
        try:
            response = requests.get(download_url, stream=True)
            if response.status_code == 200:
                with open(save_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                return True
            return False
        except Exception as e:
            print(f"Download error: {e}")
            return False
    
    def save_to_cache(self, bucket_path: str, doc_id: str, version_name: str, cache_dir: str) -> str:
        os.makedirs(cache_dir, exist_ok=True)
        date_str = datetime.now().strftime('%Y%m%d')
        filename = f"{version_name}_{date_str}.xlsx"
        save_path = os.path.join(cache_dir, filename)
        
        if self.download_excel(bucket_path, doc_id, save_path):
            return save_path
        return None
```

---

## Phase 4-6: 业务模块

### Task 8: 版本计划 (modules/version_manager.py)
- CRUD operations for version plans

### Task 9: 风险分析 (modules/risk_analyzer.py)
- Risk detection based on stage dates

### Task 10: 统计计算 (modules/stats_calculator.py)
- Statistics aggregation

---

## Phase 7: Flask 后端

### Task 11: API 路由 (app.py)

核心路由:
- `GET /api/versions` - 获取版本列表
- `POST /api/documents` - 创建文档配置
- `GET /api/sheets` - 获取 Sheet 页
- `POST /api/download` - 下载 Excel
- `POST /api/load_sheet` - 加载数据
- `GET/POST/PUT/DELETE /api/version_plans` - 版本计划 CRUD

---

## Phase 8: 前端

### Task 12: HTML/CSS/JS

- `templates/index.html` - 页面结构
- `static/style.css` - Organic Modern 风格
- `static/app.js` - 数据加载和渲染

---

## Phase 9: 测试

使用 `test_read_copy.xlsx` 验证:
- Excel 读取和解析
- 合并单元格处理
- 风险判断逻辑
