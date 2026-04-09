# -*- coding: utf-8 -*-
"""
TestPace-Track 统计功能测试
测试未开始、进行中、已完成统计，以及风险卡片与弹窗的一致性
"""
import sys
import os

# 添加项目根目录到sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding='utf-8')

import unittest
from modules.data_parser import normalize_progress, get_progress
from modules.stats_calculator import StatsCalculator, EMPTY_FIELD_COLUMNS
from modules.risk_analyzer import RiskAnalyzer, get_risk_label


class TestNormalizeProgress(unittest.TestCase):
    """测试进度标准化函数"""

    def test_normalize_completed(self):
        """测试'已完成'转换为100"""
        self.assertEqual(normalize_progress('已完成'), 100)

    def test_normalize_percentage(self):
        """测试百分比字符串"""
        self.assertEqual(normalize_progress('80%'), 80)
        self.assertEqual(normalize_progress('100%'), 100)
        self.assertEqual(normalize_progress('0%'), 0)

    def test_normalize_number(self):
        """测试数字字符串"""
        self.assertEqual(normalize_progress('80'), 80)
        self.assertEqual(normalize_progress('0'), 0)
        self.assertEqual(normalize_progress('100'), 100)

    def test_normalize_decimal(self):
        """测试小数（0.8表示80%）"""
        self.assertEqual(normalize_progress('0.8'), 80)
        self.assertEqual(normalize_progress('0.5'), 50)

    def test_normalize_none(self):
        """测试空值"""
        self.assertIsNone(normalize_progress(None))
        self.assertIsNone(normalize_progress(''))
        self.assertIsNone(normalize_progress('  '))


class TestStatsCalculator(unittest.TestCase):
    """测试StatsCalculator统计计算"""

    def setUp(self):
        """设置测试数据"""
        self.version_plans = [
            {'stage_name': '需求串讲/设计完成', 'target_date': '2026/03/01'},
            {'stage_name': '需求反串讲完成', 'target_date': '2026/03/15'},
            {'stage_name': '需求测试完成', 'target_date': '2026/04/01'},
        ]

    def _create_requirements(self, reqs_data):
        """创建测试需求数据"""
        return reqs_data

    def test_not_started_count(self):
        """测试未开始统计：进度=0且不为空"""
        requirements = [
            {'测试进度': 0, '串讲和测试设计进度': '未开始', '测试人员': '张三'},
            {'测试进度': 0, '串讲和测试设计进度': '未开始', '测试人员': '张三'},
            {'测试进度': 50, '串讲和测试设计进度': '进行中', '测试人员': '张三'},
        ]
        calc = StatsCalculator(requirements)
        stats = calc.calculate()
        self.assertEqual(stats['not_started_count'], 2, "进度=0应该计入未开始")

    def test_in_progress_count(self):
        """测试进行中统计：0<进度<100"""
        requirements = [
            {'测试进度': 50, '串讲和测试设计进度': '进行中', '测试人员': '张三'},
            {'测试进度': 99, '串讲和测试设计进度': '进行中', '测试人员': '张三'},
            {'测试进度': 100, '串讲和测试设计进度': '已完成', '测试人员': '张三'},
        ]
        calc = StatsCalculator(requirements)
        stats = calc.calculate()
        self.assertEqual(stats['in_progress_count'], 2, "0<进度<100应该计入进行中")

    def test_completed_count(self):
        """测试已完成统计：进度>=100"""
        requirements = [
            {'测试进度': 100, '串讲和测试设计进度': '已完成', '测试人员': '张三'},
            {'测试进度': 200, '串讲和测试设计进度': '已完成', '测试人员': '张三'},
            {'测试进度': '已完成', '串讲和测试设计进度': '已完成', '测试人员': '张三'},
        ]
        calc = StatsCalculator(requirements)
        stats = calc.calculate()
        self.assertEqual(stats['completed_count'], 3, "进度>=100或'已完成'应该计入已完成")

    def test_empty_progress_counted_as_not_started(self):
        """测试空进度计入未开始统计（新需求：空白的测试进度 = 未开始）"""
        requirements = [
            {'测试进度': None, '串讲和测试设计进度': '未开始', '测试人员': '张三'},
            {'测试进度': '', '串讲和测试设计进度': '未开始', '测试人员': '张三'},
            {'测试进度': 0, '串讲和测试设计进度': '未开始', '测试人员': '张三'},
        ]
        calc = StatsCalculator(requirements)
        stats = calc.calculate()
        # 空进度（None和''）应该计入not_started_count
        self.assertEqual(stats['not_started_count'], 3, "空进度和0都应该计入未开始")
        self.assertEqual(stats['test_progress_distribution'].get('未填写', 0), 2, "空进度应该计入'未填写'桶")


class TestRiskAnalyzer(unittest.TestCase):
    """测试RiskAnalyzer风险分析"""

    def setUp(self):
        """设置测试数据"""
        self.version_plans = [
            {'stage_name': '需求串讲/设计完成', 'target_date': '2026/03/01'},
            {'stage_name': '需求反串讲完成', 'target_date': '2026/03/15'},
            {'stage_name': '需求测试完成', 'target_date': '2026/04/01'},
        ]

    def test_serial_review_incomplete(self):
        """测试串讲/设计未完成风险"""
        analyzer = RiskAnalyzer(self.version_plans)
        # 当前日期2026/04/05，已超过计划日期2026/03/01，且串讲未完成
        req = {
            '串讲和测试设计进度': '进行中',
            '反串讲进度（%）': 100,
            '测试进度': 100,
            '测试人员': '张三',
        }
        risks = analyzer.analyze_requirement(req, '2026/04/05')
        self.assertIn('serial_review_incomplete', risks, "串讲未完成应该触发风险")

    def test_serial_review_complete_no_risk(self):
        """测试串讲已完成无风险"""
        analyzer = RiskAnalyzer(self.version_plans)
        req = {
            '串讲和测试设计进度': '已完成',
            '反串讲进度（%）': 100,
            '测试进度': 100,
            '测试人员': '张三',
        }
        risks = analyzer.analyze_requirement(req, '2026/04/05')
        self.assertNotIn('serial_review_incomplete', risks, "串讲已完成不应该触发串讲未完成风险")

    def test_reverse_serial_incomplete(self):
        """测试反串讲未完成风险"""
        analyzer = RiskAnalyzer(self.version_plans)
        # 当前日期2026/04/05，已超过计划日期2026/03/15，反串讲进度<100%
        req = {
            '串讲和测试设计进度': '已完成',
            '反串讲进度（%）': 50,
            '测试进度': 80,
            '测试人员': '张三',
        }
        risks = analyzer.analyze_requirement(req, '2026/04/05')
        self.assertIn('reverse_serial_incomplete', risks, "反串讲未完成应该触发风险")

    def test_reverse_serial_complete_no_risk(self):
        """测试反串讲完成无风险"""
        analyzer = RiskAnalyzer(self.version_plans)
        req = {
            '串讲和测试设计进度': '已完成',
            '反串讲进度（%）': 100,
            '测试进度': 80,
            '测试人员': '张三',
        }
        risks = analyzer.analyze_requirement(req, '2026/04/05')
        self.assertNotIn('reverse_serial_incomplete', risks, "反串讲完成不应该触发反串讲未完成风险")

    def test_test_progress_delayed(self):
        """测试测试进度滞后风险"""
        analyzer = RiskAnalyzer(self.version_plans)
        # 当前日期2026/04/05，已超过计划日期2026/04/01，进度<100%
        req = {
            '串讲和测试设计进度': '已完成',
            '反串讲进度（%）': 100,
            '测试进度': 80,
            '测试人员': '张三',
        }
        risks = analyzer.analyze_requirement(req, '2026/04/05')
        self.assertIn('test_progress_delayed', risks, "测试进度滞后应该触发风险")

    def test_test_complete_no_risk(self):
        """测试测试完成无风险"""
        analyzer = RiskAnalyzer(self.version_plans)
        req = {
            '串讲和测试设计进度': '已完成',
            '反串讲进度（%）': 100,
            '测试进度': 100,
            '测试人员': '张三',
        }
        risks = analyzer.analyze_requirement(req, '2026/04/05')
        self.assertNotIn('test_progress_delayed', risks, "测试完成不应该触发进度滞后风险")

    def test_before_plan_date_no_risk(self):
        """测试在计划日期前无风险"""
        analyzer = RiskAnalyzer(self.version_plans)
        # 当前日期2026/02/15，还在计划日期2026/03/01之前
        req = {
            '串讲和测试设计进度': '进行中',
            '反串讲进度（%）': 0,
            '测试进度': 0,
            '测试人员': '张三',
        }
        risks = analyzer.analyze_requirement(req, '2026/02/15')
        self.assertNotIn('serial_review_incomplete', risks, "在计划日期前不应该触发风险")


class TestRiskLabelMapping(unittest.TestCase):
    """测试风险标签映射"""

    def test_get_risk_label(self):
        """测试风险标签中英文映射"""
        self.assertEqual(get_risk_label('serial_review_incomplete'), '串讲未完成')
        self.assertEqual(get_risk_label('reverse_serial_incomplete'), '反串讲未完成')
        self.assertEqual(get_risk_label('test_progress_delayed'), '进度滞后')


class TestFrontendLogicConsistency(unittest.TestCase):
    """
    测试前端逻辑一致性
    比较renderRiskCards和showRiskDetailModal的逻辑是否一致
    """

    def setUp(self):
        """设置测试数据"""
        self.version_plans = [
            {'stage_name': '需求串讲/设计完成', 'target_date': '2026/03/01'},
            {'stage_name': '需求反串讲完成', 'target_date': '2026/03/15'},
            {'stage_name': '需求测试完成', 'target_date': '2026/04/01'},
        ]

    def test_risk_card_vs_modal_not_started(self):
        """
        测试风险卡片'未开始'与弹窗'not-started'逻辑一致性

        renderRiskCards:
          not_started: r.risks.includes('serial_review_incomplete')

        showRiskDetailModal (not-started):
          progress === 0

        问题：这两个逻辑不一致！
        - 风险卡片统计的是'串讲未完成'的需求
        - 弹窗过滤的是'进度=0'的需求
        """
        analyzer = RiskAnalyzer(self.version_plans)

        # 场景1：进度=0，但串讲已完成 - 应该出现在哪个统计中？
        req1 = {
            '串讲和测试设计进度': '已完成',  # 串讲已完成
            '反串讲进度（%）': 0,
            '测试进度': 0,  # 进度=0
            '测试人员': '张三',
        }
        risks1 = analyzer.analyze_requirement(req1, '2026/04/05')

        # renderRiskCards会显示：不显示（因为无serial_review_incomplete风险）
        # showRiskDetailModal会显示：是（因为progress === 0）
        has_serial_review_risk = 'serial_review_incomplete' in risks1
        is_progress_zero = req1['测试进度'] == 0

        print(f"\n场景1 - 进度=0但串讲已完成:")
        print(f"  风险卡片计数（serial_review_incomplete）: {has_serial_review_risk}")
        print(f"  弹窗显示（progress === 0）: {is_progress_zero}")
        print(f"  逻辑是否一致: {has_serial_review_risk == is_progress_zero}")

        # 场景2：进度>0，但串讲未完成
        req2 = {
            '串讲和测试设计进度': '进行中',  # 串讲未完成
            '反串讲进度（%）': 50,
            '测试进度': 30,  # 进度>0
            '测试人员': '张三',
        }
        risks2 = analyzer.analyze_requirement(req2, '2026/04/05')

        has_serial_review_risk2 = 'serial_review_incomplete' in risks2
        is_progress_zero2 = req2['测试进度'] == 0

        print(f"\n场景2 - 进度>0但串讲未完成:")
        print(f"  风险卡片计数（serial_review_incomplete）: {has_serial_review_risk2}")
        print(f"  弹窗显示（progress === 0）: {is_progress_zero2}")
        print(f"  逻辑是否一致: {has_serial_review_risk2 == is_progress_zero2}")

        # 断言：这两个场景都表明逻辑不一致
        # 如果代码正确，两者应该一致
        self.assertEqual(has_serial_review_risk, is_progress_zero,
                         "风险卡片和弹窗的'未开始'逻辑应该一致")

    def test_risk_card_vs_modal_serial_review(self):
        """
        测试风险卡片'需求串讲/设计未完成'与弹窗'serial-review-incomplete'逻辑一致性

        renderRiskCards:
          not_started: r.risks.includes('serial_review_incomplete')

        showRiskDetailModal (serial-review-incomplete):
          r.risks.includes('serial_review_incomplete') ||
          r.risks.includes('serial review incomplete') ||
          r.risks.includes('reverse_serial_incomplete') ||  <-- 错误！包含了反串讲
          r.risks.includes('reverse serial incomplete')

        问题：弹窗逻辑错误地包含了反串讲！
        """
        analyzer = RiskAnalyzer(self.version_plans)

        # 只有串讲未完成，不包含反串讲问题
        req = {
            '串讲和测试设计进度': '进行中',  # 串讲未完成
            '反串讲进度（%）': 100,  # 反串讲已完成
            '测试进度': 80,
            '测试人员': '张三',
        }
        risks = analyzer.analyze_requirement(req, '2026/04/05')

        print(f"\n场景 - 只有串讲未完成:")
        print(f"  实际风险: {risks}")
        print(f"  包含serial_review_incomplete: {'serial_review_incomplete' in risks}")
        print(f"  包含reverse_serial_incomplete: {'reverse_serial_incomplete' in risks}")

        # showRiskDetailModal的serial-review-incomplete会错误地匹配这个需求
        # 因为它的条件包含了reverse_serial_incomplete
        modal_would_match = (
            'serial_review_incomplete' in risks or
            'reverse_serial_incomplete' in risks
        )
        card_would_match = 'serial_review_incomplete' in risks

        print(f"  风险卡片会显示: {card_would_match}")
        print(f"  弹窗会显示: {modal_would_match}")
        print(f"  逻辑是否一致: {card_would_match == modal_would_match}")

        # 这个测试预期会失败，因为弹窗逻辑确实有问题
        self.assertEqual(card_would_match, modal_would_match,
                         "风险卡片和弹窗的'串讲未完成'逻辑应该一致")


class TestEmptyFieldsDetection(unittest.TestCase):
    """测试空白字段检测是否正常"""

    def test_empty_field_detection(self):
        """测试空白字段检测"""
        # 必须包含 EMPTY_FIELD_COLUMNS 中的所有列，否则缺失的列会被当作空白
        requirements = [
            {
                '测试人员': '张三',
                '串讲和测试设计进度': '',  # 空
                '反串讲进度（%）': None,  # 空
                '测试进度': '',  # 空
                '计划转测时间': '',  # 空
                '用例数': None,  # 空
                '自验质量（自验pass，测试fail）': '',
                '问题单数量': None,
                '是否变更接口': '',
                '是否涉及资料': '',
                '资料转测时间': None,
                '是否涉及性能、过载': '',
                '是否涉及可靠性': '',
                '涉及数据底座（MySQL/Cassandra/influxDB）': '',
            },
            {
                '测试人员': '张三',
                '串讲和测试设计进度': '已完成',
                '反串讲进度（%）': 100,
                '测试进度': 80,
                '计划转测时间': '2026/04/01',
                '用例数': 50,
                '自验质量（自验pass，测试fail）': 'pass',
                '问题单数量': 3,
                '是否变更接口': '否',
                '是否涉及资料': '是',
                '资料转测时间': '2026/04/01',
                '是否涉及性能、过载': '否',
                '是否涉及可靠性': '是',
                '涉及数据底座（MySQL/Cassandra/influxDB）': 'MySQL',
            }
        ]

        calc = StatsCalculator(requirements)
        empty_stats = calc.calculate_empty_fields_by_tester()

        # 张三有1个需求有空白字段
        zhangsan_stats = next((s for s in empty_stats if s['tester'] == '张三'), None)
        self.assertIsNotNone(zhangsan_stats)
        self.assertEqual(zhangsan_stats['total_empty_requirements'], 1,
                         "张三应该有1个需求有空白字段")


if __name__ == '__main__':
    unittest.main(verbosity=2)