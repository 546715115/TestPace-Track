"""
统计计算模块
计算需求的各种统计指标
"""
from typing import List, Dict

from modules.data_parser import normalize_progress, get_progress


# 需要检查空白字段的列（排除业务团队、需求编号、需求描述、开发人员、测试人员）
# 注意：有些列名在不同Excel文件中可能有细微差异，使用模糊匹配
EMPTY_FIELD_COLUMNS = [
    '串讲和测试设计进度',
    '反串讲进度（%）',
    '用例数',
    '计划转测时间',          # 可能有后缀如"（格式:2024/01/01）"
    '测试进度',              # 可能有"（%）"后缀
    '自验质量（自验pass，测试fail）',
    '问题单数量',
    '是否变更接口',
    '是否涉及资料',
    '资料转测时间',
    '是否涉及性能、过载',
    '是否涉及可靠性',
    '涉及数据底座（MySQL/Cassandra/influxDB）',
]


def _get_field_value(req: Dict, field_name: str):
    """从req中获取字段值，支持模糊匹配"""
    # 先精确匹配
    if field_name in req:
        return req[field_name]
    # 模糊匹配：req中的key包含field_name
    for key in req.keys():
        if field_name in key:
            return req[key]
    return None


class StatsCalculator:
    """统计计算器"""

    def __init__(self, requirements: List[Dict]):
        self.requirements = requirements

    def calculate(self) -> Dict:
        """计算基础统计"""
        stats = {
            'total_requirements': len(self.requirements),
            'completed_count': 0,
            'in_progress_count': 0,
            'not_started_count': 0,
            'test_progress_distribution': {},
            'serial_review_status': {}
        }

        for req in self.requirements:
            progress = normalize_progress(get_progress(req))

            if progress >= 100:
                stats['completed_count'] += 1
            elif progress > 0:
                stats['in_progress_count'] += 1
            else:
                stats['not_started_count'] += 1

            # 进度分布桶
            bucket = self._get_progress_bucket(progress)
            stats['test_progress_distribution'][bucket] = \
                stats['test_progress_distribution'].get(bucket, 0) + 1

            # 串讲状态分布
            serial = req.get('串讲和测试设计进度', '未知')
            stats['serial_review_status'][serial] = \
                stats['serial_review_status'].get(serial, 0) + 1

        return stats

    def calculate_with_groups(self, groups: List[Dict]) -> Dict:
        """计算包含分组信息的统计"""
        stats = self.calculate()

        merged_groups = [g for g in groups if g.get('is_merged', False)]
        single_rows = [g for g in groups if not g.get('is_merged', True)]

        stats['actual_requirement_count'] = len(groups)
        stats['total_row_count'] = sum(len(g.get('rows', [])) for g in groups)
        stats['merged_group_count'] = len(merged_groups)
        stats['single_row_count'] = len(single_rows)

        return stats

    def calculate_empty_fields_by_tester(self) -> List[Dict]:
        """按测试人员统计空白字段情况"""
        from datetime import datetime

        # 按测试人员聚合
        tester_data = {}

        # 调试日志：显示需要检查的列名和req中实际的列名
        print(f'[{datetime.now().strftime("%H:%M:%S")}] [模块:空白字段统计] 需要检查的列: {EMPTY_FIELD_COLUMNS}')

        # 打印第一个需求的实际列名（用于调试）
        if self.requirements:
            print(f'[{datetime.now().strftime("%H:%M:%S")}] [模块:空白字段统计] 第一个需求的实际列名: {list(self.requirements[0].keys())}')

        for idx, req in enumerate(self.requirements):
            # 获取测试人员（取第一个）
            tester = req.get('测试人员', '')
            if not tester:
                continue

            # 处理多个测试人员的情况，只取第一个
            if ',' in tester:
                tester = tester.split(',')[0].strip()

            if tester not in tester_data:
                tester_data[tester] = {
                    'tester': tester,
                    'columns': {col: 0 for col in EMPTY_FIELD_COLUMNS},
                    'total_empty_requirements': 0,
                    'requirement_count': 0
                }

            tester_data[tester]['requirement_count'] += 1

            # 调试日志：显示每个需求在各列的值
            debug_info = []
            for col in EMPTY_FIELD_COLUMNS:
                value = _get_field_value(req, col)
                is_empty = not value or str(value).strip() == ''
                debug_info.append(f'{col}:{repr(value)[:20]}={is_empty}')

            print(f'[{datetime.now().strftime("%H:%M:%S")}] [模块:空白字段统计] 需求{idx} 测试员={tester}: {debug_info}')

            # 检查每个需要统计的列是否为空
            for col in EMPTY_FIELD_COLUMNS:
                value = _get_field_value(req, col)
                if not value or str(value).strip() == '':
                    tester_data[tester]['columns'][col] += 1

        # 计算合计列（只要有一个空字段的需求数）
        for req in self.requirements:
            tester = req.get('测试人员', '')
            if not tester:
                continue
            if ',' in tester:
                tester = tester.split(',')[0].strip()

            if tester not in tester_data:
                continue

            # 检查该需求是否有任何空白字段
            has_empty = False
            for col in EMPTY_FIELD_COLUMNS:
                value = _get_field_value(req, col)
                if not value or str(value).strip() == '':
                    has_empty = True
                    break

            if has_empty:
                tester_data[tester]['total_empty_requirements'] += 1

        # 转换为列表并按合计降序排列
        result = list(tester_data.values())
        result.sort(key=lambda x: x['total_empty_requirements'], reverse=True)

        return result

    def _get_progress_bucket(self, progress: int) -> str:
        """获取进度桶"""
        if progress >= 100:
            return '100%'
        elif progress >= 75:
            return '75-99%'
        elif progress >= 50:
            return '50-74%'
        elif progress >= 25:
            return '25-49%'
        elif progress > 0:
            return '1-24%'
        else:
            return '0%'


if __name__ == '__main__':
    # 测试代码
    requirements = [
        {'测试进度': 100, '串讲和测试设计进度': '已完成'},
        {'测试进度': 50, '串讲和测试设计进度': '进行中'},
        {'测试进度': 0, '串讲和测试设计进度': '未开始'},
    ]

    calc = StatsCalculator(requirements)
    stats = calc.calculate()
    print(f"Stats: {stats}")
