"""
风险分析模块
基于版本计划时间节点判断需求风险
"""
from datetime import datetime
from typing import List, Dict, Any

from modules.data_parser import normalize_progress, get_progress


class RiskAnalyzer:
    """风险分析器"""

    def __init__(self, version_plans: List[Dict]):
        """
        初始化风险分析器
        version_plans: 版本计划列表
        """
        self.version_plans = {vp['stage_name']: vp for vp in version_plans}

    @staticmethod
    def _is_serial_review_complete(value: Any) -> bool:
        """
        判断串讲/设计是否完成
        支持多种填写方式：
        - '已完成'、'已完成(4.1)'、'测试设计已完成' 等 → 认为是完成
        - '未开始'、'进行中'、'未完成' → 认为未完成
        - None、空字符串 → 认为未完成
        """
        if value is None:
            return False
        if isinstance(value, (int, float)):
            # 数字类型，默认完成（如填写了100%）
            return True
        val = str(value).strip()
        if val == '':
            return False
        # 明确未完成的状态
        incomplete_status = ['未开始', '进行中', '未完成']
        if val in incomplete_status:
            return False
        # 包含"未"字且不是"已完成"的（如"未完成"、"未开始"）→ 未完成
        if '未' in val and val != '已完成':
            return False
        # 其他情况（包含"完成"关键词的各种填写）→ 认为完成
        return True

    def analyze_requirement(self, req: Dict, current_date: str = None) -> List[str]:
        """
        分析单条需求的风险
        返回风险列表
        """
        if current_date is None:
            current_date = datetime.now().strftime('%Y/%m/%d')

        risks = []

        # 1. 串讲/设计未完成
        if '需求串讲/设计完成' in self.version_plans:
            plan = self.version_plans['需求串讲/设计完成']
            if self._is_overdue(plan['target_date'], current_date):
                if not self._is_serial_review_complete(req.get('串讲和测试设计进度')):
                    risks.append('serial_review_incomplete')

        # 2. 反串讲未完成
        if '需求反串讲完成' in self.version_plans:
            plan = self.version_plans['需求反串讲完成']
            if self._is_overdue(plan['target_date'], current_date):
                progress = normalize_progress(req.get('反串讲进度（%）', 0))
                if progress is not None and progress < 100:
                    risks.append('reverse_serial_incomplete')

        # 3. 测试进度滞后
        if '需求测试完成' in self.version_plans:
            plan = self.version_plans['需求测试完成']
            if self._is_overdue(plan['target_date'], current_date):
                progress = normalize_progress(get_progress(req))
                if progress is not None and progress < 100:
                    risks.append('test_progress_delayed')

        # 4. 空白字段检查
        empty_fields = self._check_empty_fields(req)
        for field in empty_fields:
            risks.append(f'empty_field_{field}')

        return risks

    def _is_overdue(self, target_date: str, current_date: str) -> bool:
        """判断是否已逾期"""
        if not target_date or not current_date:
            return False
        return target_date < current_date

    def _check_empty_fields(self, req: Dict, required_fields: List[str] = None) -> List[str]:
        """检查必填字段是否为空"""
        if required_fields is None:
            required_fields = ['测试人员', '计划转测时间', '测试进度（%）']

        empty = []
        for field in required_fields:
            value = req.get(field)
            if not value or str(value).strip() == '':
                # 进度字段特殊处理：兼容新旧列名
                if field == '测试进度（%）':
                    if req.get('测试进度') or str(req.get('测试进度', '')).strip():
                        continue  # 旧列名有值，不算空
                empty.append(field)
        return empty

    def analyze_all(self, requirements: List[Dict], current_date: str = None) -> List[Dict]:
        """
        分析所有需求的风险
        返回带风险标记的需求列表
        """
        for req in requirements:
            req['risks'] = self.analyze_requirement(req, current_date)
        return requirements


def get_risk_label(risk: str) -> str:
    """获取风险标签中文"""
    labels = {
        'serial_review_incomplete': '串讲未完成',
        'reverse_serial_incomplete': '反串讲未完成',
        'test_progress_delayed': '进度滞后',
        'empty_field_测试人员': '测试人员空白',
        'empty_field_计划转测时间': '计划转测时间空白',
        'empty_field_测试进度': '测试进度空白',
    }
    return labels.get(risk, risk)


if __name__ == '__main__':
    # 测试代码
    plans = [
        {'stage_name': '需求串讲/设计完成', 'target_date': '2026/03/01'},
        {'stage_name': '需求反串讲完成', 'target_date': '2026/03/15'},
        {'stage_name': '需求测试完成', 'target_date': '2026/04/01'},
    ]

    analyzer = RiskAnalyzer(plans)

    req = {
        '串讲和测试设计进度': '进行中',
        '反串讲进度（%）': 50,
        '测试进度': 30,
        '测试人员': '张三',
    }

    risks = analyzer.analyze_requirement(req, '2026/04/05')
    print(f"Risks: {risks}")
