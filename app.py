"""
TestPace-Track Flask 后端
测试进度跟踪工具 API
"""
import os
import json
from datetime import datetime
from flask import Flask, jsonify, request, render_template

from modules.db_manager import init_db
from modules.version_manager import VersionManager
from modules.data_parser import ExcelReader, get_progress, PROGRESS_FIELD
from modules.risk_analyzer import RiskAnalyzer
from modules.stats_calculator import StatsCalculator, EMPTY_FIELD_COLUMNS
from modules.data_fetcher import DataFetcher

app = Flask(__name__)

# 初始化数据库
init_db()


def now_str():
    """返回当前时间字符串用于日志"""
    return datetime.now().strftime('%H:%M:%S')


def get_cache_file(version_id: str) -> str:
    """查找版本对应的缓存文件"""
    cache_dir = os.path.join(os.path.dirname(__file__), 'data', 'cache')
    if not os.path.exists(cache_dir):
        return None

    for filename in os.listdir(cache_dir):
        if version_id in filename and filename.endswith('.xlsx'):
            return os.path.join(cache_dir, filename)
    return None


def get_config_documents():
    """加载文档配置"""
    config_path = os.path.join(os.path.dirname(__file__), 'config', 'documents.json')
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"documents": []}


def save_config_documents(config):
    """保存文档配置"""
    config_path = os.path.join(os.path.dirname(__file__), 'config', 'documents.json')
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


@app.route('/')
def index():
    return render_template('index.html')


# ============ 版本和文档 API ============

@app.route('/api/versions', methods=['GET'])
def get_versions():
    """获取所有版本配置"""
    config = get_config_documents()
    return jsonify({'success': True, 'data': {'versions': config.get('documents', [])}})


@app.route('/api/documents', methods=['GET'])
def get_documents():
    """获取文档配置列表"""
    config = get_config_documents()
    return jsonify({'success': True, 'data': {'documents': config.get('documents', [])}})


@app.route('/api/documents', methods=['POST'])
def create_document():
    """创建/更新文档配置"""
    data = request.json
    config = get_config_documents()

    new_doc = {
        'version_id': data.get('version_id'),
        'name': data.get('name'),
        'download_url': data.get('download_url')
    }

    # 检查是否已存在
    for i, doc in enumerate(config.get('documents', [])):
        if doc.get('version_id') == new_doc['version_id']:
            config['documents'][i] = new_doc
            save_config_documents(config)
            return jsonify({'success': True, 'data': {'document': new_doc}})

    config.setdefault('documents', []).append(new_doc)
    save_config_documents(config)
    return jsonify({'success': True, 'data': {'document': new_doc}})


@app.route('/api/documents/<version_id>', methods=['PUT'])
def update_document(version_id):
    """更新文档配置"""
    data = request.json
    config = get_config_documents()

    for i, doc in enumerate(config.get('documents', [])):
        if doc.get('version_id') == version_id:
            config['documents'][i] = {
                'version_id': version_id,
                'name': data.get('name', doc.get('name')),
                'download_url': data.get('download_url', doc.get('download_url'))
            }
            save_config_documents(config)
            return jsonify({'success': True, 'data': {'document': config['documents'][i]}})

    return jsonify({'success': False, 'error': 'Document not found'})


@app.route('/api/documents/<version_id>', methods=['DELETE'])
def delete_document(version_id):
    """删除文档配置"""
    config = get_config_documents()

    for i, doc in enumerate(config.get('documents', [])):
        if doc.get('version_id') == version_id:
            del config['documents'][i]
            save_config_documents(config)
            return jsonify({'success': True})

    return jsonify({'success': False, 'error': 'Document not found'})


# ============ 缓存管理 API ============

@app.route('/api/caches', methods=['GET'])
def get_caches():
    """获取所有缓存文件列表"""
    cache_dir = os.path.join(os.path.dirname(__file__), 'data', 'cache')
    if not os.path.exists(cache_dir):
        return jsonify({'success': True, 'data': {'caches': []}})

    caches = []
    for filename in os.listdir(cache_dir):
        if filename.endswith('.xlsx'):
            file_path = os.path.join(cache_dir, filename)
            # 解析文件名：名称_YYYYMMDD.xlsx 或 名称_YYYYMMDD (1).xlsx
            import re
            match = re.match(r'^(.+?)_(\d{8})(?:\s*\(\d+\))?\.xlsx$', filename)
            if match:
                name = match.group(1)
                date_str = match.group(2)
                # 格式化日期
                formatted_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
            else:
                name = filename.replace('.xlsx', '')
                formatted_date = '未知'

            caches.append({
                'filename': filename,
                'name': name,
                'date': formatted_date,
                'size': os.path.getsize(file_path),
                'path': file_path
            })

    # 按日期倒序排列
    caches.sort(key=lambda x: x['date'], reverse=True)

    return jsonify({'success': True, 'data': {'caches': caches}})


@app.route('/api/caches/<filename>', methods=['DELETE'])
def delete_cache(filename):
    """删除指定缓存文件"""
    cache_dir = os.path.join(os.path.dirname(__file__), 'data', 'cache')
    file_path = os.path.join(cache_dir, filename)

    # 安全检查：只允许删除 .xlsx 文件
    if not filename.endswith('.xlsx') or '..' in filename or '/' in filename or '\\' in filename:
        return jsonify({'success': False, 'error': 'Invalid filename'})

    if os.path.exists(file_path):
        os.remove(file_path)
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': 'File not found'})


@app.route('/api/caches/<filename>/sheets', methods=['GET'])
def get_cache_sheets(filename):
    """获取指定缓存文件的所有 Sheet 页"""
    cache_dir = os.path.join(os.path.dirname(__file__), 'data', 'cache')
    file_path = os.path.join(cache_dir, filename)

    # 安全检查
    if not filename.endswith('.xlsx') or '..' in filename or '/' in filename or '\\' in filename:
        return jsonify({'success': False, 'error': 'Invalid filename'})

    if not os.path.exists(file_path):
        return jsonify({'success': False, 'error': 'Cache file not found'})

    reader = ExcelReader(file_path)
    sheets = reader.get_sheet_names()
    return jsonify({'success': True, 'data': {'sheets': sheets, 'filename': filename}})


@app.route('/api/load_sheet_from_cache', methods=['POST'])
def load_sheet_from_cache():
    """从指定缓存文件加载 Sheet 数据"""
    data = request.json
    filename = data.get('filename')
    sheet_name = data.get('sheet_name')

    print(f'[{now_str()}] [模块:缓存加载] 请求: filename={filename}, sheet={sheet_name}')

    if not filename or not sheet_name:
        return jsonify({'success': False, 'error': 'filename and sheet_name required'})

    cache_dir = os.path.join(os.path.dirname(__file__), 'data', 'cache')
    file_path = os.path.join(cache_dir, filename)

    if not os.path.exists(file_path):
        print(f'[{now_str()}] [模块:缓存加载] 失败: 文件不存在 - {file_path}')
        return jsonify({'success': False, 'error': 'Cache file not found'})

    print(f'[{now_str()}] [模块:Excel解析] 开始解析: {file_path}')
    reader = ExcelReader(file_path)
    reader.load_sheet(sheet_name)

    raw_rows, groups = reader.get_raw_rows()
    print(f'[{now_str()}] [模块:Excel解析] 完成: Excel行数={len(raw_rows)}, 合并组数={len(groups)}')

    # 计算风险
    print(f'[{now_str()}] [模块:风险分析] 开始分析 {len(raw_rows)} 条需求...')
    merged_reqs = [reader.merge_group(g) for g in groups]

    # 从文件名解析 version_id
    import re
    match = re.match(r'^(.+?)_(\d{8})', filename)
    version_id = match.group(1) if match else filename
    version_plans = VersionManager().get_version_plans(version_id)
    analyzer = RiskAnalyzer(version_plans)

    for raw_row in raw_rows:
        raw_row['risks'] = analyzer.analyze_requirement(raw_row)

    for idx, merged_req in enumerate(merged_reqs):
        group_rows = [r for r in raw_rows if r['_group_idx'] == idx]
        all_risks = set()
        for r in group_rows:
            risks = r.get('risks', []) or []
            for risk in risks:
                if risk is not None:
                    all_risks.add(risk)
        min_progress = get_progress(merged_req)
        for r in group_rows:
            r['risks'] = sorted([x for x in all_risks if x is not None])
            r[PROGRESS_FIELD] = min_progress
            r['测试进度'] = min_progress  # 兼容前端

    print(f'[{now_str()}] [模块:风险分析] 完成')

    print(f'[{now_str()}] [模块:统计计算] 开始计算...')
    stats_calc = StatsCalculator(merged_reqs)
    stats = stats_calc.calculate_with_groups(groups)
    print(f'[{now_str()}] [模块:统计计算] 完成: 实际需求={stats.get("actual_requirement_count")}, 全部需求={stats.get("total_row_count")}')

    print(f'[{now_str()}] [模块:缓存加载] 成功返回: {len(raw_rows)} 行')
    return jsonify({
        'success': True,
        'data': {
            'requirements': raw_rows,
            'groups': groups,
            'stats': stats,
            'filename': filename
        }
    })


@app.route('/api/caches/cleanup', methods=['POST'])
def cleanup_caches():
    """清理旧缓存，保留最多100条"""
    cache_dir = os.path.join(os.path.dirname(__file__), 'data', 'cache')
    if not os.path.exists(cache_dir):
        return jsonify({'success': True, 'deleted': 0})

    files = []
    for filename in os.listdir(cache_dir):
        if filename.endswith('.xlsx'):
            file_path = os.path.join(cache_dir, filename)
            files.append((filename, os.path.getsize(file_path)))

    # 按名称和日期排序（保留最新的）
    files.sort(key=lambda x: x[0], reverse=True)

    # 删除超过100条的旧文件
    deleted = 0
    if len(files) > 100:
        files_to_delete = files[100:]
        for filename, _ in files_to_delete:
            file_path = os.path.join(cache_dir, filename)
            os.remove(file_path)
            deleted += 1

    return jsonify({'success': True, 'deleted': deleted})


# ============ Sheet 和数据 API ============

@app.route('/api/sheets', methods=['GET'])
def get_sheets():
    """获取版本对应的所有 Sheet 页"""
    version_id = request.args.get('version_id')
    if not version_id:
        return jsonify({'success': False, 'error': 'version_id required'})

    cache_file = get_cache_file(version_id)
    if not cache_file or not os.path.exists(cache_file):
        return jsonify({'success': False, 'error': 'No cache found. Please download first.'})

    reader = ExcelReader(cache_file)
    sheets = reader.get_sheet_names()
    return jsonify({'success': True, 'data': {'sheets': sheets}})


@app.route('/api/download', methods=['POST'])
def download_document():
    """从 OneBox 下载文档"""
    data = request.json
    version_id = data.get('version_id')

    if not version_id:
        return jsonify({'success': False, 'error': 'version_id required'})

    # 获取文档配置
    config = get_config_documents()
    doc = None
    for d in config.get('documents', []):
        if d.get('version_id') == version_id:
            doc = d
            break

    if not doc:
        return jsonify({'success': False, 'error': '文档配置不存在'})

    download_url = doc.get('download_url')
    if not download_url:
        return jsonify({'success': False, 'error': '下载链接不存在'})

    try:
        fetcher = DataFetcher()
        cache_dir = os.path.join(os.path.dirname(__file__), 'data', 'cache')
        os.makedirs(cache_dir, exist_ok=True)

        save_path = fetcher.download_from_url(
            download_url=download_url,
            version_name=doc.get('name', version_id),
            cache_dir=cache_dir
        )

        if save_path:
            return jsonify({'success': True, 'data': {'cache_path': save_path}})
        else:
            return jsonify({'success': False, 'error': '下载失败，请检查配置'})
    except Exception as e:
        return jsonify({'success': False, 'error': f'下载异常: {str(e)}'})


@app.route('/api/load_sheet', methods=['POST'])
def load_sheet():
    """加载指定 Sheet 的数据"""
    data = request.json
    version_id = data.get('version_id')
    sheet_name = data.get('sheet_name')

    print(f'[{now_str()}] [模块:数据加载] 请求: version_id={version_id}, sheet={sheet_name}')

    if not version_id or not sheet_name:
        return jsonify({'success': False, 'error': 'version_id and sheet_name required'})

    cache_file = get_cache_file(version_id)
    if not cache_file or not os.path.exists(cache_file):
        print(f'[{now_str()}] [模块:数据加载] 失败: 缓存文件不存在 - {cache_file}')
        return jsonify({'success': False, 'error': 'No cache found'})

    print(f'[{now_str()}] [模块:Excel解析] 开始解析: {cache_file}')
    reader = ExcelReader(cache_file)
    reader.load_sheet(sheet_name)

    # 获取原始所有行（用于前端rowspan合并显示）
    raw_rows, groups = reader.get_raw_rows()
    print(f'[{now_str()}] [模块:Excel解析] 完成: Excel行数={len(raw_rows)}, 合并组数={len(groups)}')

    # 计算风险：先对每个原始行分别分析，再去重合并
    print(f'[{now_str()}] [模块:风险分析] 开始分析 {len(raw_rows)} 条需求...')
    merged_reqs = [reader.merge_group(g) for g in groups]
    version_plans = VersionManager().get_version_plans(version_id)
    analyzer = RiskAnalyzer(version_plans)

    # 对每个原始行单独分析风险
    for raw_row in raw_rows:
        raw_row['risks'] = analyzer.analyze_requirement(raw_row)

    # 对每个组内的风险去重合并，并同步最小进度
    for idx, merged_req in enumerate(merged_reqs):
        group_rows = [r for r in raw_rows if r['_group_idx'] == idx]
        all_risks = set()
        for r in group_rows:
            risks = r.get('risks', []) or []
            for risk in risks:
                if risk is not None:
                    all_risks.add(risk)
        min_progress = get_progress(merged_req)
        for r in group_rows:
            r['risks'] = sorted([x for x in all_risks if x is not None])
            r[PROGRESS_FIELD] = min_progress
            r['测试进度'] = min_progress  # 兼容前端

    print(f'[{now_str()}] [模块:风险分析] 完成')

    # 计算统计
    print(f'[{now_str()}] [模块:统计计算] 开始计算...')
    stats_calc = StatsCalculator(merged_reqs)
    stats = stats_calc.calculate_with_groups(groups)
    print(f'[{now_str()}] [模块:统计计算] 完成: 实际需求={stats.get("actual_requirement_count")}, 全部需求={stats.get("total_row_count")}')

    print(f'[{now_str()}] [模块:数据加载] 成功返回: {len(raw_rows)} 行')
    return jsonify({
        'success': True,
        'data': {
            'requirements': raw_rows,  # 原始所有行
            'groups': groups,          # 合并组信息
            'stats': stats
        }
    })


@app.route('/api/empty_fields', methods=['GET'])
def get_empty_fields():
    """获取空白字段统计"""
    version_id = request.args.get('version_id')
    if not version_id:
        return jsonify({'success': False, 'error': 'version_id required'})

    cache_file = get_cache_file(version_id)
    if not cache_file or not os.path.exists(cache_file):
        return jsonify({'success': False, 'error': 'No cache found'})

    reader = ExcelReader(cache_file)
    # 获取第一个sheet
    sheets = reader.get_sheet_names()
    if not sheets:
        return jsonify({'success': False, 'error': 'No sheets found'})

    reader.load_sheet(sheets[0])
    groups = reader.get_requirement_groups()
    merged_reqs = [reader.merge_group(g) for g in groups]

    # 计算空白字段统计
    stats_calc = StatsCalculator(merged_reqs)
    empty_stats = stats_calc.calculate_empty_fields_by_tester()

    return jsonify({
        'success': True,
        'data': {
            'empty_stats': empty_stats,
            'columns': EMPTY_FIELD_COLUMNS
        }
    })


# ============ 版本计划 API ============

@app.route('/api/version_plans', methods=['GET'])
def get_version_plans():
    """获取版本计划列表"""
    version_id = request.args.get('version_id')
    vm = VersionManager()
    plans = vm.get_version_plans(version_id)
    return jsonify({'success': True, 'data': {'plans': plans}})


@app.route('/api/version_plans', methods=['POST'])
def create_version_plan():
    """创建版本计划"""
    data = request.json
    vm = VersionManager()
    plan_id = vm.create_version_plan(
        version_id=data.get('version_id'),
        version_name=data.get('version_name'),
        stage_name=data.get('stage_name'),
        target_date=data.get('target_date')
    )
    return jsonify({'success': True, 'data': {'plan_id': plan_id}})


@app.route('/api/version_plans/<int:plan_id>', methods=['PUT'])
def update_version_plan(plan_id):
    """更新版本计划"""
    data = request.json
    vm = VersionManager()
    success = vm.update_version_plan(plan_id, data.get('target_date'))
    return jsonify({'success': success})


@app.route('/api/version_plans/<int:plan_id>', methods=['DELETE'])
def delete_version_plan(plan_id):
    """删除版本计划"""
    vm = VersionManager()
    success = vm.delete_version_plan(plan_id)
    return jsonify({'success': success})


if __name__ == '__main__':
    app.run(debug=False, port=5001)
