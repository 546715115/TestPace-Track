# TestPace-Track 任务计划

**项目**: TestPace-Track 测试进度跟踪工具
**方案**: 直接 API 下载 + Excel 分析（简化版，无 Playwright）
**更新日期**: 2026-04-06

---

## 阶段

### 阶段 1-6: 核心模块 ✅
- [x] 项目初始化
- [x] 数据解析模块 (data_parser.py)
- [x] 数据获取模块 (data_fetcher.py)
- [x] 风险分析模块 (risk_analyzer.py)
- [x] 统计计算模块 (stats_calculator.py)
- [x] 版本计划模块 (version_manager.py)

---

### 阶段 7: Flask 后端 ✅
- [x] GET /api/versions
- [x] GET/POST/PUT/DELETE /api/documents
- [x] GET /api/sheets
- [x] POST /api/load_sheet
- [x] POST /api/download
- [x] GET/POST/PUT/DELETE /api/version_plans
- [x] GET/POST /api/cookie
- [x] GET /api/empty_fields

---

### 阶段 8: 前端页面 ✅
- [x] 版本选择下拉
- [x] 版本计划时间轴可视化
- [x] 统计仪表盘
- [x] 风险卡片（重构：需求串讲/设计未完成、反串讲进度滞后、需求测试完成进度滞后）
- [x] 需求列表表格（特性分类、业务团队、需求编号、需求描述、测试人员等）
- [x] Sheet 选择
- [x] 测试人员过滤
- [x] 搜索框
- [x] 下载更新按钮
- [x] Cookie 配置弹窗
- [x] 空白字段统计弹窗

---

### 阶段 10: 遗留功能 🔄

#### 10.1 特性分类列合并
- [ ] 表格特性分类列使用 rowspan 合并
- [ ] 业务团队、需求编号、需求描述、操作列不合并
- [ ] 测试人员、进度、风险列显示合并后值

#### 10.2 跳转页面交互
- [ ] 风险卡片点击后的跳转/过滤交互逻辑

#### 10.3 版本计划时间轴重新设计
- [ ] 重新设计 UI 和交互

---

## 技术栈

- Flask (Python 3.10+)
- openpyxl (Excel 解析)
- SQLite (配置存储)
- 原生 HTML/CSS/JS

---

## 测试数据

- `test_read_copy.xlsx` - 用于测试的 Excel 文件
- `data/cache/0330需求列表_test.xlsx` - 缓存的测试数据
