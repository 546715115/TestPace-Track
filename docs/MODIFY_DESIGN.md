# 修改设计方案

## 问题分析

### 根本原因

`normalize_progress(None)` 返回 `0` 而不是 `None`。

在 `data_parser.py` 第 123 行：

```python
if value is None or str(value).strip() == '':
    return None
```

当 `value is None` 时：
1. `value is None` 计算结果为 Python 布尔值 `True`
2. 由于 `or` 的短路求值特性，`True or <anything>` 直接返回 `True`
3. **结果**：函数返回布尔值 `True`，而不是 `None`！

接着代码继续执行：
- `str(None).strip()` 返回字符串 `'None'`
- `float('None')` 抛出 `ValueError`
- `except` 块返回 `0`

**最终效果**：`normalize_progress(None)` 返回 `0`，导致：
- 风险分析器错误地添加 `'test_progress_delayed'` 标记（因为 `0 < 100` 为真）
- 统计计算时将空进度当作 0% 处理

### 影响分析

| 场景 | 期望行为 | 实际行为 |
|------|----------|----------|
| `normalize_progress(None)` | 返回 `None` | 返回 `0` |
| 风险分析器遇到空进度 | 不添加 `test_progress_delayed`（数据不足无法判断） | 添加 `test_progress_delayed`（错误地认为进度滞后） |
| 统计计算遇到空进度 | 计为"未开始" | 计为"未开始"（但由于上述 bug，risk 不一致） |

### 前端不一致问题

在 `showRiskDetailModal` 的 `matchesType` 函数中：
```javascript
const progress = r['测试进度'] || 0;
if (type === 'not-started') {
    return progress === 0;
}
```

当进度为 `None` 时，前端用 `|| 0` 将其当作 0，显示为"未开始"。

但后端添加了 `test_progress_delayed` 标记，导致：
- 麻将块统计：该需求出现在"进度滞后"
- 弹窗筛选：显示为"未开始"

**麻将块统计与弹窗表格逻辑不一致**。

---

## 修改点清单

| 序号 | 文件 | 修改点 | 风险等级 |
|------|------|--------|----------|
| 1 | `modules/data_parser.py` | 修复 `normalize_progress` 函数 | 中 |
| 2 | `modules/stats_calculator.py` | 明确处理 `progress is None` 的情况 | 低 |
| 3 | `modules/risk_analyzer.py` | 确保空进度不添加 `test_progress_delayed` | 中 |

---

## 修改详情

### 修改点 1：`data_parser.py` - 修复 `normalize_progress` 函数

**位置**：`modules/data_parser.py` 第 121-144 行

**问题**：`value is None or str(value).strip() == ''` 由于 Python 短路求值，当 value 为 None 时返回布尔值 `True` 而不是 `None`

**修改方案**：将 `is None` 检查独立出来，避免 `or` 短路问题

```python
def normalize_progress(value):
    """标准化进度为整数百分比，空值返回None"""
    # 独立检查 None，避免 Python 短路求值问题
    # value is None 时返回 True，但我们的逻辑期望返回 None
    if value is None:
        return None
    if str(value).strip() == '':
        return None

    val = str(value).strip()

    if val == '已完成':
        return 100

    val = val.replace('%', '')

    try:
        num = float(val)
        if num < 1 and num > 0:
            return int(num * 100)
        if num == int(num):
            return int(num)
        else:
            return int(num)
    except:
        return 0
```

**影响分析**：
- **风险**：`normalize_progress` 是公共方法，被多处调用
- **正面影响**：
  - `risk_analyzer.py`：空进度不会错误添加 `test_progress_delayed`
  - `stats_calculator.py`：空进度返回 `None`，可以正确分类
- **需验证**：检查其他调用方是否期望空进度返回 0

**其他调用方检查**：

1. `stats_calculator.py` 第 59 行：
   ```python
   progress = normalize_progress(get_progress(req))
   if progress is None:
       bucket = self._get_progress_bucket(progress)
       # skip counting
   ```
   **结论**：期望 `None` 为空，兼容

2. `risk_analyzer.py` 第 42 行：
   ```python
   progress = normalize_progress(req.get('反串讲进度（%）', 0))
   if progress < 100:
       risks.append('reverse_serial_incomplete')
   ```
   **结论**：若 `normalize_progress` 返回 `None`，`None < 100` 会报错！但根据修改后，空进度返回 `None` 而不添加 risk，正确

3. `risk_analyzer.py` 第 50 行：
   ```python
   progress = normalize_progress(get_progress(req))
   if progress < 100:
       risks.append('test_progress_delayed')
   ```
   **结论**：同上，空进度不应添加 risk

### 修改点 2：`stats_calculator.py` - 明确处理空进度

**位置**：`modules/stats_calculator.py` 第 58-73 行

**当前代码**：
```python
progress = normalize_progress(get_progress(req))

# 空值（未填写）不计入完成/进行中/未开始统计
if progress is None:
    bucket = self._get_progress_bucket(progress)
    stats['test_progress_distribution'][bucket] = \
        stats['test_progress_distribution'].get(bucket, 0) + 1
    continue

if progress >= 100:
    stats['completed_count'] += 1
elif progress > 0:
    stats['in_progress_count'] += 1
else:
    stats['not_started_count'] += 1
```

**问题**：空进度（`None`）被跳过，不计入任何统计类别

**修改方案**：将空进度明确计为"未开始"

```python
progress = normalize_progress(get_progress(req))

# 空值（未填写）计入未开始统计
if progress is None:
    bucket = self._get_progress_bucket(progress)
    stats['test_progress_distribution'][bucket] = \
        stats['test_progress_distribution'].get(bucket, 0) + 1
    stats['not_started_count'] += 1
    continue

if progress >= 100:
    stats['completed_count'] += 1
elif progress > 0:
    stats['in_progress_count'] += 1
else:
    stats['not_started_count'] += 1
```

**影响分析**：
- 空进度现在会被计入 `not_started_count`
- `test_progress_distribution` 中的 '未填写' 桶仍然保持（用于显示分布）
- 不影响空白字段检测逻辑（`empty_field_*` 统计使用 `_check_empty_fields`，不经过 `normalize_progress`）

### 修改点 3：`risk_analyzer.py` - 确保空进度不添加 risk

**位置**：`modules/risk_analyzer.py` 第 47-52 行

**当前代码**：
```python
if '需求测试完成' in self.version_plans:
    plan = self.version_plans['需求测试完成']
    if self._is_overdue(plan['target_date'], current_date):
        progress = normalize_progress(get_progress(req))
        if progress < 100:
            risks.append('test_progress_delayed')
```

**问题**：若 `normalize_progress` 返回 `None`（修复后），`None < 100` 会抛出 `TypeError`

**修改方案**：添加 `None` 检查

```python
if '需求测试完成' in self.version_plans:
    plan = self.version_plans['需求测试完成']
    if self._is_overdue(plan['target_date'], current_date):
        progress = normalize_progress(get_progress(req))
        if progress is not None and progress < 100:
            risks.append('test_progress_delayed')
```

**同样修改反串讲进度检查**（第 42 行）：
```python
progress = normalize_progress(req.get('反串讲进度（%）', 0))
if progress is not None and progress < 100:
    risks.append('reverse_serial_incomplete')
```

**影响分析**：
- 空进度不会添加 `test_progress_delayed` 或 `reverse_serial_incomplete`
- 与前端 `matchesType` 逻辑一致（空进度显示为"未开始"）
- 不影响空白字段检测（`_check_empty_fields` 不调用 `normalize_progress`）

---

## 影响分析

### 调用方影响矩阵

| 调用方 | 文件:行号 | 调用方式 | 修改后行为 | 是否影响 |
|--------|-----------|----------|------------|----------|
| `risk_analyzer` | `risk_analyzer.py:42` | `normalize_progress(value)` | 返回 `None` 时不添加 risk | **已修改** |
| `risk_analyzer` | `risk_analyzer.py:50` | `normalize_progress(get_progress(req))` | 返回 `None` 时不添加 risk | **已修改** |
| `stats_calculator` | `stats_calculator.py:59` | `normalize_progress(get_progress(req))` | 空进度明确计为未开始 | **已修改** |
| `stats_calculator` | 空白字段统计 | 不调用 `normalize_progress` | 无变化 | 无 |

### 空白字段检测不受影响

`RiskAnalyzer._check_empty_fields` 方法：
```python
def _check_empty_fields(self, req: Dict, required_fields: List[str] = None) -> List[str]:
    for field in required_fields:
        value = req.get(field)
        if not value or str(value).strip() == '':
            # 进度字段特殊处理
            if field == '测试进度（%）':
                if req.get('测试进度') or str(req.get('测试进度', '')).strip():
                    continue
            empty.append(field)
```

- **不调用** `normalize_progress`
- 直接检查原始字段值
- 不受本次修改影响

---

## 回退方案

### 回退步骤

1. **回退 `data_parser.py`**：
   ```python
   def normalize_progress(value):
       if value is None or str(value).strip() == '':  # 恢复原代码
           return None
   ```

2. **回退 `stats_calculator.py`**：删除新增的 `stats['not_started_count'] += 1`

3. **回退 `risk_analyzer.py`**：删除 `progress is not None and` 条件检查

### 回退后状态

- `normalize_progress(None)` 再次返回 `0`
- 空进度不会添加到 `not_started_count`
- 风险分析器对空进度的处理恢复原状

### 验证点

回退后执行以下验证：
1. 空进度需求的风险标记应包含 `test_progress_delayed`
2. 空进度需求的 `not_started_count` 不增加
3. 空白字段检测功能正常