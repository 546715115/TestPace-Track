# TestPace-Track 任务计划

**项目**: TestPace-Track 测试进度跟踪工具
**方案**: 直接 API 下载 + Excel 分析（简化版，无 Playwright）
**更新日期**: 2026-04-05

---

## 阶段

### 阶段 1: 项目初始化
- [x] 创建目录结构
- [x] 创建 .gitignore
- [x] 创建 config/documents.json
- [x] 初始化 SQLite 数据库

**负责人**: Agent
**状态**: complete

---

### 阶段 2: 数据解析模块 (data_parser.py)
- [x] ExcelReader 类 - 读取 Sheet
- [x] get_requirement_groups() - 合并单元格分组
- [x] merge_group() - 字段合并逻辑
- [x] parse_date() - 日期格式标准化
- [x] normalize_progress() - 进度格式标准化

**负责人**: Agent
**状态**: complete

---

### 阶段 3: 数据获取模块 (data_fetcher.py)
- [x] construct_download_url() - 构建下载 URL
- [x] get_download_link() - 调用 API 获取下载链接
- [x] download_excel() - 下载 Excel 文件
- [x] save_to_cache() - 保存到本地缓存

**负责人**: Agent
**状态**: complete

---

### 阶段 4: 风险分析模块 (risk_analyzer.py)
- [x] RiskAnalyzer 类
- [x] analyze_requirement() - 单条需求风险分析
- [x] 判断逻辑:
  - 串讲/设计未完成
  - 反串讲未完成
  - 测试进度滞后
  - 空白字段

**负责人**: Agent
**状态**: complete

---

### 阶段 5: 统计计算模块 (stats_calculator.py)
- [x] StatsCalculator 类
- [x] calculate() - 基础统计
- [x] calculate_with_groups() - 含分组的统计
- [x] 进度分布统计

**负责人**: Agent
**状态**: complete

---

### 阶段 6: 版本计划模块 (version_manager.py)
- [x] VersionManager 类
- [x] create_version_plan()
- [x] get_version_plans()
- [x] update_version_plan()
- [x] delete_version_plan()

**负责人**: Agent
**状态**: complete

---

### 阶段 7: Flask 后端 (app.py)
- [x] API 路由:
  - [x] GET /api/versions
  - [x] GET/POST/PUT/DELETE /api/documents
  - [x] GET /api/sheets
  - [x] POST /api/load_sheet
  - [x] POST /api/download
  - [x] GET/POST/PUT/DELETE /api/version_plans

**负责人**: Agent
**状态**: complete

---

### 阶段 8: 前端页面
- [x] templates/index.html - 主页面结构
- [x] static/style.css - 样式
- [x] static/app.js - 前端逻辑
- [x] 功能:
  - [x] 版本选择下拉
  - [x] 版本计划时间轴可视化
  - [x] 统计仪表盘
  - [x] 风险卡片
  - [x] 需求列表表格
  - [x] Sheet 选择
  - [x] 测试人员过滤
  - [x] 搜索框
  - [x] 下载更新按钮

**负责人**: Agent
**状态**: complete

---

### 阶段 9: 测试与验证
- [x] 使用 test_read_copy.xlsx 测试数据解析
- [x] 验证合并单元格处理 (23个需求组)
- [x] 验证风险判断逻辑
- [x] 验证前端页面功能

**负责人**: Agent
**状态**: complete

**测试结果**:
- API版本加载: 通过
- Sheet列表获取: 通过
- 数据解析: 23个需求，5个合并组
- 统计计算: 通过 (21未开始，2进行中，0已完成)
- 前端页面: 可访问

---

## 目标

构建一个 Flask Web 工具，能够:
1. 从 OneBox API 下载 Excel 表格
2. 解析合并单元格，提取需求数据
3. 按版本展示统计和风险
4. 支持过滤和搜索

---

## 技术栈

- Flask (Python 3.10+)
- openpyxl (Excel 解析)
- SQLite (配置存储)
- 原生 HTML/CSS/JS

---

## 测试数据

- `test_read_copy.xlsx` - 用于测试的 Excel 文件
