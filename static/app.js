// TestPace-Track 前端逻辑

let currentVersion = null;
let currentSheet = null;
let currentSheets = [];
let allRequirements = [];      // 原始所有行
let mergedRequirements = [];   // 合并后的实际需求
let allGroups = [];
let allStats = {};
let versionPlans = [];
let currentRiskDetailFiltered = [];  // 当前风险详情弹窗的筛选数据
let currentRiskDetailType = '';      // 当前风险详情类型

// ============ 初始化 ============

async function init() {
    await loadVersions();
    setupEventListeners();
}

function setupEventListeners() {
    document.getElementById('version-select').addEventListener('change', onVersionChange);
    document.getElementById('download-btn').addEventListener('click', downloadData);
    document.getElementById('add-plan-btn').addEventListener('click', showAddPlanModal);
    document.getElementById('cancel-plan-btn').addEventListener('click', hidePlanModal);
    document.getElementById('plan-form').addEventListener('submit', saveVersionPlan);
    document.getElementById('tester-filter').addEventListener('change', filterRequirements);
    document.getElementById('search-box').addEventListener('input', filterRequirements);
    document.getElementById('sheet-select').addEventListener('change', onSheetChange);
    document.getElementById('config-btn').addEventListener('click', showConfigModal);
    document.getElementById('config-close-btn').addEventListener('click', hideConfigModal);
    document.getElementById('config-cancel-btn').addEventListener('click', resetConfigForm);
    document.getElementById('config-form').addEventListener('submit', saveDocumentConfig);
    document.getElementById('cache-btn').addEventListener('click', showCacheModal);
    document.getElementById('cache-close-btn').addEventListener('click', hideCacheModal);
    document.getElementById('empty-fields-close-btn').addEventListener('click', hideEmptyFieldsModal);
    document.getElementById('risk-detail-close-btn').addEventListener('click', hideRiskDetailModal);
    document.getElementById('risk-detail-tester-filter').addEventListener('change', filterRiskDetailByTester);

    document.querySelectorAll('.risk-cards .card').forEach(card => {
        card.addEventListener('click', (e) => {
            const type = e.target.closest('[data-type]')?.dataset.type;
            if (type) filterByRiskType(type, e.target);
        });
    });

    // 统计卡片点击事件
    document.querySelectorAll('.stat-card').forEach(card => {
        card.addEventListener('click', (e) => {
            const h3 = e.target.closest('.stat-card')?.querySelector('h3');
            if (!h3) return;
            const text = h3.textContent;
            if (text.includes('未开始')) {
                showRiskDetailModal('not-started', '未开始');
            } else if (text.includes('进行中')) {
                showRiskDetailModal('in-progress', '进行中');
            } else if (text.includes('已完成')) {
                showRiskDetailModal('completed', '已完成');
            }
        });
    });
}

// ============ 版本加载 ============

async function loadVersions() {
    try {
        const response = await fetch('/api/versions');
        const data = await response.json();
        if (data.success) {
            const select = document.getElementById('version-select');
            data.data.versions.forEach(v => {
                const option = document.createElement('option');
                option.value = v.version_id;
                option.textContent = v.name || v.version_id;
                select.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Failed to load versions:', error);
    }
}

// ============ 版本变更 ============

async function onVersionChange(e) {
    currentVersion = e.target.value;
    if (!currentVersion) {
        clearDisplay();
        return;
    }

    await Promise.all([loadVersionPlans(), loadSheets()]);
}

async function loadSheets() {
    try {
        const response = await fetch(`/api/sheets?version_id=${currentVersion}`);
        const data = await response.json();

        if (data.success) {
            currentSheets = data.data.sheets;
            populateSheetSelect();

            if (currentSheets.length > 0) {
                currentSheet = currentSheets[0];
                await loadData();
            }
        } else {
            currentSheets = [];
            currentSheet = null;
            populateSheetSelect();
            clearDisplay();
        }
    } catch (error) {
        console.error('Failed to load sheets:', error);
        currentSheets = [];
        currentSheet = null;
    }
}

function populateSheetSelect() {
    const select = document.getElementById('sheet-select');
    select.innerHTML = '<option value="">选择Sheet</option>';
    currentSheets.forEach(sheet => {
        const option = document.createElement('option');
        option.value = sheet;
        option.textContent = sheet;
        select.appendChild(option);
    });
}

async function onSheetChange(e) {
    currentSheet = e.target.value;
    if (currentSheet) {
        await loadData();
    }
}

// ============ 数据加载 ============

async function loadData() {
    if (!currentVersion || !currentSheet) return;

    try {
        const response = await fetch('/api/load_sheet', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                version_id: currentVersion,
                sheet_name: currentSheet
            })
        });

        const data = await response.json();
        console.log('[DEBUG loadData] 收到响应:', data);
        if (data.success) {
            allRequirements = data.data.requirements;
            allGroups = data.data.groups;
            allStats = data.data.stats || {};

            console.log('[DEBUG loadData] allRequirements 数量:', allRequirements.length);
            console.log('[DEBUG loadData] allGroups 数量:', allGroups.length);
            console.log('[DEBUG loadData] allStats:', allStats);

            // 构建合并后的实际需求（用于统计）
            mergedRequirements = allRequirements.filter(r => r._is_first_in_group);
            console.log('[DEBUG loadData] mergedRequirements 数量:', mergedRequirements.length);

            renderStats();
            renderRiskCards();
            populateTesterFilter();
            renderTable(allRequirements);
        } else {
            console.error('[DEBUG loadData] 请求失败:', data.error);
        }
    } catch (error) {
        console.error('Failed to load data:', error);
    }
}

async function downloadData() {
    if (!currentVersion) {
        alert('请先选择版本');
        return;
    }

    const btn = document.getElementById('download-btn');
    btn.disabled = true;
    btn.textContent = '下载中...';

    try {
        const response = await fetch('/api/download', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ version_id: currentVersion })
        });

        const data = await response.json();
        if (data.success) {
            await loadSheets();
            alert('下载成功');
        } else {
            alert(data.error || '下载失败');
        }
    } catch (error) {
        console.error('Download failed:', error);
        alert('下载失败');
    } finally {
        btn.disabled = false;
        btn.textContent = '📥 下载更新';
    }
}

// ============ 版本计划 ============

async function loadVersionPlans() {
    try {
        const response = await fetch(`/api/version_plans?version_id=${currentVersion}`);
        const data = await response.json();
        if (data.success) {
            versionPlans = data.data.plans || [];
            renderTimeline();
        }
    } catch (error) {
        console.error('Failed to load version plans:', error);
    }
}

function renderTimeline() {
    const container = document.getElementById('timeline-content');

    if (!versionPlans || versionPlans.length === 0) {
        container.innerHTML = '<p class="no-data">暂无版本计划，点击"添加阶段"创建</p>';
        return;
    }

    // 按version_id分组
    const byVersionId = {};
    versionPlans.forEach(p => {
        if (!byVersionId[p.version_id]) {
            byVersionId[p.version_id] = [];
        }
        byVersionId[p.version_id].push(p);
    });

    let html = '';
    for (const [versionId, plans] of Object.entries(byVersionId)) {
        // 过滤有日期的计划，用于计算时间范围
        const datedPlans = plans.filter(p => p.target_date && p.target_date.trim());

        // 计算时间范围
        let minDate = null, maxDate = null;
        if (datedPlans.length > 0) {
            const dates = datedPlans.map(p => new Date(p.target_date));
            minDate = new Date(Math.min(...dates));
            maxDate = new Date(Math.max(...dates));

            // 扩展范围，让第一个和最后一个点不要贴在边缘
            const range = maxDate - minDate;
            if (range > 0) {
                minDate = new Date(minDate.getTime() - range * 0.1);
                maxDate = new Date(maxDate.getTime() + range * 0.1);
            } else {
                // 如果所有日期相同，扩展前后各一天
                minDate = new Date(minDate.getTime() - 24 * 60 * 60 * 1000);
                maxDate = new Date(maxDate.getTime() + 24 * 60 * 60 * 1000);
            }
        }

        // 版本标题
        html += `<div class="timeline-version">`;
        html += `<h4 style="margin:0 0 8px;color:var(--color-primary)">版本 ${versionId}</h4>`;

        // 时间轴容器
        html += `<div class="timeline-arrow-container">`;
        html += `<div class="timeline-arrow"></div>`;

        // 计算每个计划的位置并存储
        const planPositions = [];
        plans.sort((a, b) => a.id - b.id).forEach(plan => {
            const isOverdue = plan.target_date && new Date(plan.target_date) < new Date();

            // 计算位置百分比
            let leftPercent = 50; // 默认居中
            if (plan.target_date && minDate && maxDate) {
                const planDate = new Date(plan.target_date);
                const totalRange = maxDate - minDate;
                if (totalRange > 0) {
                    const position = (planDate - minDate) / totalRange;
                    leftPercent = Math.max(0, Math.min(100, position * 100));
                }
            }

            planPositions.push({
                plan: plan,
                leftPercent: leftPercent,
                isOverdue: isOverdue
            });
        });

        // 按位置排序，用于重叠检测
        const sortedPositions = [...planPositions].sort((a, b) => a.leftPercent - b.leftPercent);

        // 重叠检测：如果两个标记的位置相差小于5%，认为重叠
        const OVERLAP_THRESHOLD = 5; // 百分比
        const positionGroups = [];

        for (let i = 0; i < sortedPositions.length; i++) {
            const current = sortedPositions[i];

            // 查找与当前标记重叠的组
            let foundGroup = false;
            for (let j = 0; j < positionGroups.length; j++) {
                const group = positionGroups[j];
                // 检查当前标记是否与组内任一标记重叠
                if (group.some(item => Math.abs(item.leftPercent - current.leftPercent) < OVERLAP_THRESHOLD)) {
                    group.push(current);
                    foundGroup = true;
                    break;
                }
            }

            // 如果没有找到重叠组，创建新组
            if (!foundGroup) {
                positionGroups.push([current]);
            }
        }

        // 为每个重叠组内的标记分配文字和日期垂直位置
        positionGroups.forEach(group => {
            if (group.length === 1) {
                // 单个标记：文字在上，日期在下
                group[0].textPosition = 'text-top';
                group[0].datePosition = 'text-bottom';
            } else if (group.length === 2) {
                // 两个标记：交替分配相反位置
                group[0].textPosition = 'text-top';
                group[0].datePosition = 'text-bottom';
                group[1].textPosition = 'text-bottom';
                group[1].datePosition = 'text-top';
            } else {
                // 三个或更多标记：循环分配组合
                const combinations = [
                    { text: 'text-top', date: 'text-bottom' },
                    { text: 'text-middle', date: 'text-middle' },
                    { text: 'text-bottom', date: 'text-top' }
                ];
                group.forEach((item, index) => {
                    const combo = combinations[index % combinations.length];
                    item.textPosition = combo.text;
                    item.datePosition = combo.date;
                });
            }
        });

        // 渲染所有标记
        planPositions.forEach(item => {
            const { plan, leftPercent, isOverdue, textPosition = 'text-top', datePosition = 'text-bottom' } = item;
            const overdueClass = isOverdue ? 'overdue' : '';

            html += `
                <div class="timeline-marker ${overdueClass}" style="left: ${leftPercent}%;">
                    <div class="version-stage ${textPosition}" title="${plan.version_name}">${plan.version_name}</div>
                    <div class="marker-dot" onclick="editPlan(${plan.id}, '${plan.stage_name}', '${plan.target_date || ''}')"></div>
                    <div class="test-stage ${textPosition}" title="${plan.stage_name}">${plan.stage_name}</div>
                    <div class="marker-line"></div>
                    <div class="timeline-date ${datePosition}">${plan.target_date || '未设置'}</div>
                    <div class="timeline-actions">
                        <button class="timeline-edit-btn" onclick="editPlan(${plan.id}, '${plan.stage_name}', '${plan.target_date || ''}'); event.stopPropagation();">编辑</button>
                        <button class="timeline-delete-btn" onclick="deletePlan(${plan.id}); event.stopPropagation();">删除</button>
                    </div>
                </div>
            `;
        });

        html += `</div></div>`;
    }

    container.innerHTML = html;
}

function showAddPlanModal() {
    if (!currentVersion) {
        alert('请先选择版本');
        return;
    }
    document.getElementById('plan-version-id').value = currentVersion;
    document.getElementById('plan-modal').classList.add('show');
}

function hidePlanModal() {
    document.getElementById('plan-modal').classList.remove('show');
    document.getElementById('plan-form').reset();
}

async function saveVersionPlan(e) {
    e.preventDefault();
    const versionStageName = document.getElementById('plan-version-stage-name').value;
    const testStageName = document.getElementById('plan-stage-name').value;

    if (!versionStageName) {
        alert('请选择版本阶段名称');
        return;
    }
    if (!testStageName) {
        alert('请选择测试阶段名称');
        return;
    }

    const formData = {
        version_id: document.getElementById('plan-version-id').value,
        version_name: versionStageName,
        stage_name: testStageName,
        target_date: document.getElementById('plan-target-date').value
    };

    try {
        const response = await fetch('/api/version_plans', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(formData)
        });
        const data = await response.json();
        if (data.success) {
            hidePlanModal();
            await loadVersionPlans();
            await loadData();
        } else {
            alert('保存失败');
        }
    } catch (error) {
        console.error('Failed to save plan:', error);
        alert('保存失败');
    }
}

async function editPlan(planId, stageName, targetDate) {
    const newDate = prompt(`编辑阶段 "${stageName}" 的目标日期:`, targetDate);
    if (newDate === null) return;

    try {
        const response = await fetch(`/api/version_plans/${planId}`, {
            method: 'PUT',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ target_date: newDate })
        });
        const data = await response.json();
        if (data.success) {
            await loadVersionPlans();
            await loadData();
        } else {
            alert('更新失败');
        }
    } catch (error) {
        console.error('Failed to update plan:', error);
        alert('更新失败');
    }
}

async function deletePlan(planId) {
    if (!confirm('确定要删除这个阶段吗？')) return;

    try {
        const response = await fetch(`/api/version_plans/${planId}`, { method: 'DELETE' });
        const data = await response.json();
        if (data.success) {
            await loadVersionPlans();
            await loadData();
        } else {
            alert('删除失败');
        }
    } catch (error) {
        console.error('Failed to delete plan:', error);
        alert('删除失败');
    }
}

// ============ 渲染 ============

function renderStats() {
    document.getElementById('stat-actual-count').textContent = allStats.actual_requirement_count || 0;
    document.getElementById('stat-total-count').textContent = allStats.total_row_count || 0;
    document.getElementById('stat-completed').textContent = allStats.completed_count || 0;
    document.getElementById('stat-in-progress').textContent = allStats.in_progress_count || 0;
    document.getElementById('stat-not-started').textContent = allStats.not_started_count || 0;
}

function renderRiskCards() {
    // 使用mergedRequirements（实际需求数）来统计
    const merged = mergedRequirements.length > 0 ? mergedRequirements : allRequirements.filter(r => r._is_first_in_group);

    const risks = {
        not_started: merged.filter(r =>
            r.risks && (r.risks.includes('serial_review_incomplete') || r.risks.includes('serial review incomplete'))
        ),
        reverse_delayed: merged.filter(r =>
            r.risks && (r.risks.includes('reverse_serial_incomplete') || r.risks.includes('reverse serial incomplete'))
        ),
        test_delayed: merged.filter(r =>
            r.risks && (r.risks.includes('test_progress_delayed') || r.risks.includes('test progress delayed'))
        ),
        empty_fields: merged.filter(r =>
            r.risks && r.risks.some(risk => risk.startsWith('empty_field_'))
        )
    };

    document.querySelector('.risk-cards .card[data-type="not-started"] .count').textContent = risks.not_started.length;
    document.getElementById('risk-reverse-delayed').textContent = risks.reverse_delayed.length;
    document.getElementById('risk-test-delayed').textContent = risks.test_delayed.length;
    document.querySelector('.risk-cards .card[data-type="empty-fields"] .count').textContent = risks.empty_fields.length;
}

function populateTesterFilter() {
    const testers = [...new Set(allRequirements.map(r => r['测试人员']).filter(Boolean))];
    const select = document.getElementById('tester-filter');
    select.innerHTML = '<option value="">全部测试人员</option>';
    testers.forEach(tester => {
        const option = document.createElement('option');
        option.value = tester;
        option.textContent = tester;
        select.appendChild(option);
    });
}

function filterRequirements() {
    const tester = document.getElementById('tester-filter').value;
    const search = document.getElementById('search-box').value.toLowerCase();

    let filtered = allRequirements;
    if (tester) filtered = filtered.filter(r => r['测试人员'] === tester);
    if (search) {
        filtered = filtered.filter(r => {
            const id = (r['需求编号'] || '').toLowerCase();
            const desc = (r['需求描述'] || '').toLowerCase();
            return id.includes(search) || desc.includes(search);
        });
    }
    renderTable(filtered);
}

function filterByRiskType(type, target) {
    // 空白字段特殊处理，弹出弹窗
    if (type === 'empty-fields') {
        showEmptyFieldsModal();
        return;
    }

    if (type === 'not-started') {
        showRiskDetailModal('serial-review-incomplete', '需求串讲/设计未完成');
        return;
    } else if (type === 'reverse-delayed') {
        showRiskDetailModal('reverse-delayed', '反串讲完成进度滞后');
        return;
    } else if (type === 'test-delayed') {
        showRiskDetailModal('test-delayed', '需求测试完成进度滞后');
        return;
    }

    let filtered = allRequirements;
    const tester = document.getElementById('tester-filter').value;
    if (tester) filtered = filtered.filter(r => r['测试人员'] === tester);

    renderTable(filtered);
}

async function showEmptyFieldsModal() {
    if (!currentVersion) {
        alert('请先选择版本');
        return;
    }

    try {
        const response = await fetch(`/api/empty_fields?version_id=${currentVersion}`);
        const data = await response.json();

        if (data.success) {
            renderEmptyFieldsTable(data.data);
            document.getElementById('empty-fields-modal').classList.add('show');
        } else {
            alert(data.error || '获取数据失败');
        }
    } catch (error) {
        console.error('Failed to load empty fields:', error);
        alert('获取数据失败');
    }
}

function hideEmptyFieldsModal() {
    document.getElementById('empty-fields-modal').classList.remove('show');
}

function showRiskDetailModal(type, title) {
    if (!currentVersion) {
        alert('请先选择版本');
        return;
    }

    currentRiskDetailType = type;

    // 如果mergedRequirements为空，尝试用allRequirements
    if (!mergedRequirements || mergedRequirements.length === 0) {
        mergedRequirements = allRequirements.filter(r => r._is_first_in_group);
    }

    // 判断条件函数
    function matchesType(r) {
        const progress = r['测试进度'] || 0;
        if (type === 'not-started') {
            return progress === 0;
        } else if (type === 'in-progress') {
            return progress > 0 && progress < 100;
        } else if (type === 'completed') {
            return progress >= 100;
        } else if (type === 'serial-review-incomplete') {
            return r.risks && (r.risks.includes('serial_review_incomplete') || r.risks.includes('serial review incomplete') || r.risks.includes('reverse_serial_incomplete') || r.risks.includes('reverse serial incomplete'));
        } else if (type === 'reverse-delayed') {
            return r.risks && (r.risks.includes('reverse_serial_incomplete') || r.risks.includes('reverse serial incomplete'));
        } else if (type === 'test-delayed') {
            return r.risks && (r.risks.includes('test_progress_delayed') || r.risks.includes('test progress delayed'));
        }
        return false;
    }

    // 1. 先找出满足条件的组索引（基于每组第一行）
    const matchedGroupIdxs = new Set();
    allRequirements.forEach(r => {
        if (r._is_first_in_group && matchesType(r)) {
            matchedGroupIdxs.add(r._group_idx);
        }
    });

    // 2. 保留满足条件的组的所有行，保持allRequirements原始顺序
    // 这样能确保同组数据连续且顺序正确
    const allRowsWithIndex = allRequirements.map((r, index) => ({...r, originalIndex: index}));
    let filtered = allRowsWithIndex.filter(r => matchedGroupIdxs.has(r._group_idx));

    // 按原始索引排序，确保顺序与主表格一致
    filtered.sort((a, b) => a.originalIndex - b.originalIndex);

    // 显示最终结果数量（基于合并后的需求数）
    document.getElementById('risk-detail-title').textContent = title + ' (结果数=' + matchedGroupIdxs.size + ')';

    // 保存筛选后的数据
    currentRiskDetailFiltered = filtered;
    renderRiskDetailModal(filtered, title);
    document.getElementById('risk-detail-modal').classList.add('show');
}

function hideRiskDetailModal() {
    document.getElementById('risk-detail-modal').classList.remove('show');
}

function filterRiskDetailByTester() {
    const tester = document.getElementById('risk-detail-tester-filter').value;
    let filtered = currentRiskDetailFiltered;

    if (tester) {
        // 找出有该测试人员的组（基于原始筛选数据）
        const keepGroupIdxs = new Set();
        filtered.forEach(r => {
            if (r['测试人员'] && r['测试人员'].includes(tester)) {
                keepGroupIdxs.add(r._group_idx);
            }
        });

        // 保留这些组的所有行
        filtered = filtered.filter(r => keepGroupIdxs.has(r._group_idx));
    }

    renderRiskDetailTable(filtered);
}

function renderRiskDetailModal(data, title) {
    document.getElementById('risk-detail-title').textContent = title + ' 详情';

    // 只取每组第一行（合并后的实际需求）
    const mergedData = data.filter(r => r._is_first_in_group);

    // 按测试人员汇总
    const testerStats = {};
    mergedData.forEach(r => {
        const testers = (r['测试人员'] || '').split(',').map(t => t.trim()).filter(t => t);
        testers.forEach(tester => {
            if (!testerStats[tester]) {
                testerStats[tester] = 0;
            }
            testerStats[tester]++;
        });
    });

    // 渲染汇总行
    const summaryDiv = document.getElementById('risk-detail-summary');
    let summaryHtml = '';
    Object.keys(testerStats).sort().forEach(tester => {
        summaryHtml += `<div class="risk-detail-summary-item"><span class="tester-name">${tester}</span>: <span class="count">${testerStats[tester]}</span>个</div>`;
    });
    summaryDiv.innerHTML = summaryHtml || '<div class="no-data">暂无数据</div>';

    // 渲染测试人员筛选下拉
    const testerSelect = document.getElementById('risk-detail-tester-filter');
    const testers = Object.keys(testerStats).sort();
    testerSelect.innerHTML = '<option value="">全部测试人员</option>';
    testers.forEach(tester => {
        testerSelect.innerHTML += `<option value="${tester}">${tester}</option>`;
    });

    // 渲染表格（传入所有原始行数据，用rowspan合并特性分类和测试进度）
    renderRiskDetailTable(data);
}

function renderRiskDetailTable(data) {
    const tbody = document.getElementById('risk-detail-tbody');
    const escapeHtml = (str) => {
        if (!str) return '';
        return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    };

    if (data.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" class="no-data">暂无数据</td></tr>';
        return;
    }

    // 调试：检查所有数据的分组完整性
    console.log('弹窗表格数据完整性检查:');
    const groups = {};
    data.forEach((r, i) => {
        const groupIdx = r._group_idx;
        if (!groups[groupIdx]) {
            groups[groupIdx] = {
                firstRowIndex: r._is_first_in_group ? i : -1,
                rows: [],
                rowSpan: r._row_span,
                count: 0,
                progressValues: []
            };
        }
        groups[groupIdx].rows.push({
            index: i,
            reqNo: r['需求编号'],
            isFirst: r._is_first_in_group,
            rowSpan: r._row_span,
            progress: r['测试进度'] || 0
        });
        groups[groupIdx].progressValues.push(r['测试进度'] || 0);
        groups[groupIdx].count++;
    });

    // 验证每个组的测试进度是否一致（应该都是最小值）
    Object.entries(groups).forEach(([gid, g]) => {
        const uniqueProgress = [...new Set(g.progressValues)];
        if (uniqueProgress.length > 1) {
            console.warn(`⚠️ 组 ${gid} 的测试进度不一致:`, g.progressValues, '最小值应为:', Math.min(...g.progressValues));
        }
    });

    console.log('分组统计:', Object.entries(groups).map(([gid, g]) => ({
        groupIdx: gid,
        rowSpan: g.rowSpan,
        actualRows: g.count,
        firstRowIndex: g.firstRowIndex,
        progressValues: [...new Set(g.progressValues)], // 去重显示
        rows: g.rows
    })));

    let html = '';

    for (const r of data) {
        const progress = r['测试进度'] || 0;
        const progressClass = progress >= 100 ? 'progress-complete' : progress > 0 ? 'progress-active' : 'progress-zero';

        // 非第一行：只输出per-row列（需求编号、需求描述），其他列已被rowspan合并
        if (!r._is_first_in_group) {
            console.log('非首行数据:', {
                '需求编号': r['需求编号'],
                '需求描述': r['需求描述']?.substring(0, 20) + '...',
                'group_idx': r._group_idx
            });
            html += `<tr data-group-idx="${r._group_idx}" data-is-first="false">
                <td class="req-no-cell">${escapeHtml(r['需求编号'])}</td>
                <td class="desc-cell" title="${escapeHtml(r['需求描述'])}">${escapeHtml(r['需求描述'])}</td>
            </tr>`;
            continue;
        }

        // 第一行：带rowspan的合并列
        html += `<tr data-group-idx="${r._group_idx}" data-is-first="true">`;
        const rowSpanAttr = r._row_span > 1 ? ` rowspan="${r._row_span}"` : '';

        // 特性分类列
        html += `<td${rowSpanAttr} class="merged-cell">${escapeHtml(r['特性分类'])}</td>`;

        // per-row列
        html += `<td>${escapeHtml(r['需求编号'])}</td>`;
        html += `<td class="desc-cell" title="${escapeHtml(r['需求描述'])}">${escapeHtml(r['需求描述'])}</td>`;

        // 测试进度列
        html += `<td${rowSpanAttr} class="${progressClass}">${progress}%</td>`;
        html += '</tr>';
    }
    tbody.innerHTML = html;
}

// 简化的弹窗表格渲染（只显示合并后的需求，每组一行）
function renderRiskDetailTableSimple(data) {
    const tbody = document.getElementById('risk-detail-tbody');
    const escapeHtml = (str) => {
        if (!str) return '';
        return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    };

    if (!data || data.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" class="no-data">暂无数据</td></tr>';
        return;
    }

    let html = '';
    for (const r of data) {
        const progress = r['测试进度'] || 0;
        const progressClass = progress >= 100 ? 'progress-complete' : progress > 0 ? 'progress-active' : 'progress-zero';

        html += '<tr>';
        html += `<td>${escapeHtml(r['特性分类'])}</td>`;
        html += `<td>${escapeHtml(r['需求编号'])}</td>`;
        html += `<td class="desc-cell" title="${escapeHtml(r['需求描述'])}">${escapeHtml(r['需求描述'])}</td>`;
        html += `<td class="${progressClass}">${progress}%</td>`;
        html += '</tr>';
    }
    tbody.innerHTML = html;
}

function renderEmptyFieldsTable(data) {
    const { empty_stats, columns } = data;
    const thead = document.getElementById('empty-fields-thead');
    const tbody = document.getElementById('empty-fields-tbody');

    // 构建表头
    let theadHtml = '<tr><th>测试人员</th>';
    columns.forEach(col => {
        theadHtml += `<th>${col}</th>`;
    });
    theadHtml += '<th class="total-col">合计</th></tr>';
    thead.innerHTML = theadHtml;

    // 构建表体
    if (empty_stats.length === 0) {
        tbody.innerHTML = '<tr><td colspan="' + (columns.length + 2) + '" class="no-data">暂无数据</td></tr>';
        return;
    }

    tbody.innerHTML = empty_stats.map(item => {
        let row = `<td>${item.tester}</td>`;
        columns.forEach(col => {
            const count = item.columns[col] || 0;
            row += `<td>${count === 0 ? '已填写' : count}</td>`;
        });
        row += `<td class="total-col">${item.total_empty_requirements}</td>`;
        return `<tr>${row}</tr>`;
    }).join('');
}

function renderTable(requirements) {
    const tbody = document.getElementById('requirements-body');

    if (!requirements || requirements.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" class="no-data">暂无数据</td></tr>';
        return;
    }

    let html = '';

    for (const req of requirements) {
        const riskTags = (req.risks || []).map(risk =>
            `<span class="risk-tag ${risk}">${getRiskLabel(risk)}</span>`
        ).join('');

        const detailLink = req['需求编号']
            ? `<a href="https://clouddevops.huawei.com/workitem/+${req['需求编号']}" target="_blank">详情</a>`
            : '';

        const progress = req['测试进度'] || 0;
        const progressClass = progress >= 100 ? 'progress-complete' : progress > 0 ? 'progress-active' : 'progress-zero';

        // HTML转义函数
        const escapeHtml = (str) => {
            if (!str) return '';
            return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
        };

        // 非第一行：rowspan已覆盖的列（特性分类、测试人员、测试进度、风险）留空，只输出per-row列
        if (!req._is_first_in_group) {
            html += `<tr>
                <td></td>
                <td>${escapeHtml(req['业务团队'])}</td>
                <td>${escapeHtml(req['需求编号'])}</td>
                <td class="desc-cell" title="${escapeHtml(req['需求描述'])}">${escapeHtml(req['需求描述'])}</td>
                <td></td>
                <td></td>
                <td></td>
                <td>${detailLink}</td>
            </tr>`;
            continue;
        }

        // 第一行：带rowspan的合并列
        html += '<tr>';
        const rowSpanAttr = req._row_span > 1 ? ` rowspan="${req._row_span}"` : '';

        // 特性分类列
        html += `<td${rowSpanAttr} class="merged-cell">${req['特性分类'] || ''}</td>`;

        // per-row列
        html += `<td>${escapeHtml(req['业务团队'])}</td>`;
        html += `<td>${escapeHtml(req['需求编号'])}</td>`;
        html += `<td class="desc-cell" title="${escapeHtml(req['需求描述'])}">${escapeHtml(req['需求描述'])}</td>`;

        // 测试人员列
        html += `<td${rowSpanAttr} class="merged-cell">${req['测试人员'] || ''}</td>`;

        // 测试进度列
        html += `<td${rowSpanAttr} class="${progressClass}">${progress}%</td>`;

        // 风险列
        html += `<td${rowSpanAttr}>${riskTags}</td>`;

        // 详情列：per-row，不合并
        html += `<td>${detailLink}</td>`;
        html += '</tr>';
    }

    tbody.innerHTML = html;
}

function getRiskLabel(risk) {
    const labels = {
        'serial_review_incomplete': '串讲未完成',
        'reverse_serial_incomplete': '反串讲未完成',
        'test_progress_delayed': '进度滞后',
        'empty_field_测试人员': '测试人员空白',
        'empty_field_计划转测时间': '计划转测时间空白',
        'empty_field_测试进度': '测试进度空白'
    };
    return labels[risk] || risk;
}

function clearDisplay() {
    allRequirements = [];
    allGroups = [];
    allStats = {};
    versionPlans = [];
    currentSheets = [];

    document.getElementById('stat-actual-count').textContent = '-';
    document.getElementById('stat-total-count').textContent = '-';
    document.getElementById('stat-completed').textContent = '-';
    document.getElementById('stat-in-progress').textContent = '-';
    document.getElementById('stat-not-started').textContent = '-';

    document.querySelector('.risk-cards .card[data-type="not-started"] .count').textContent = '0';
    document.getElementById('risk-reverse-delayed').textContent = '0';
    document.getElementById('risk-test-delayed').textContent = '0';
    document.querySelector('.risk-cards .card[data-type="empty-fields"] .count').textContent = '0';

    document.getElementById('timeline-content').innerHTML = '<p class="no-data">暂无版本计划</p>';
    document.getElementById('requirements-body').innerHTML = '';
    document.getElementById('tester-filter').innerHTML = '<option value="">全部测试人员</option>';
    document.getElementById('sheet-select').innerHTML = '<option value="">选择Sheet</option>';
}

// ============ 文档配置 ============

async function showConfigModal() {
    await loadConfigList();
    document.getElementById('config-modal').classList.add('show');
}

function hideConfigModal() {
    document.getElementById('config-modal').classList.remove('show');
    resetConfigForm();
}

function resetConfigForm() {
    document.getElementById('config-form').reset();
    document.getElementById('config-id').value = '';
    document.getElementById('config-form-title').textContent = '添加新文档';
    document.getElementById('config-version-id').disabled = false;
}

async function loadConfigList() {
    try {
        const response = await fetch('/api/documents');
        const data = await response.json();
        const listEl = document.getElementById('config-list');

        if (data.success && data.data.documents.length > 0) {
            listEl.innerHTML = data.data.documents.map(doc => `
                <div class="config-item">
                    <div class="config-item-info">
                        <div class="name">${doc.name || doc.version_id}</div>
                        <div class="details">
                            版本ID: ${doc.version_id} | Bucket: ${doc.bucket_path} | Doc: ${doc.doc_id}
                        </div>
                    </div>
                    <div class="config-item-actions">
                        <button class="edit-btn" onclick="editDocument('${doc.version_id}')">编辑</button>
                        <button class="delete-btn" onclick="deleteDocument('${doc.version_id}')">删除</button>
                    </div>
                </div>
            `).join('');
        } else {
            listEl.innerHTML = '<p class="no-data">暂无配置，点击下方表单添加</p>';
        }
    } catch (error) {
        console.error('Failed to load config list:', error);
    }
}

async function editDocument(versionId) {
    try {
        const response = await fetch('/api/documents');
        const data = await response.json();
        if (data.success) {
            const doc = data.data.documents.find(d => d.version_id === versionId);
            if (doc) {
                document.getElementById('config-id').value = doc.version_id;
                document.getElementById('config-version-id').value = doc.version_id;
                document.getElementById('config-version-id').disabled = true;
                document.getElementById('config-name').value = doc.name || '';
                document.getElementById('config-download-url').value = doc.download_url || '';
                document.getElementById('config-form-title').textContent = '编辑文档';
            }
        }
    } catch (error) {
        console.error('Failed to edit document:', error);
    }
}

async function deleteDocument(versionId) {
    if (!confirm(`确定要删除版本 "${versionId}" 吗？`)) return;

    try {
        const response = await fetch(`/api/documents/${versionId}`, { method: 'DELETE' });
        const data = await response.json();
        if (data.success) {
            await loadConfigList();
            const select = document.getElementById('version-select');
            select.innerHTML = '<option value="">选择版本</option>';
            await loadVersions();
        } else {
            alert('删除失败');
        }
    } catch (error) {
        console.error('Failed to delete document:', error);
        alert('删除失败');
    }
}

async function saveDocumentConfig(e) {
    e.preventDefault();

    const versionId = document.getElementById('config-id').value;
    const configData = {
        version_id: document.getElementById('config-version-id').value,
        name: document.getElementById('config-name').value,
        download_url: document.getElementById('config-download-url').value
    };

    try {
        let response;
        if (versionId) {
            response = await fetch(`/api/documents/${versionId}`, {
                method: 'PUT',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(configData)
            });
        } else {
            response = await fetch('/api/documents', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(configData)
            });
        }

        const data = await response.json();
        if (data.success) {
            hideConfigModal();
            const select = document.getElementById('version-select');
            select.innerHTML = '<option value="">选择版本</option>';
            await loadVersions();
            await loadConfigList();
        } else {
            alert('保存失败');
        }
    } catch (error) {
        console.error('Failed to save document:', error);
        alert('保存失败');
    }
}

// ============ 缓存管理 ============

async function showCacheModal() {
    await loadCacheList();
    document.getElementById('cache-modal').classList.add('show');
}

function hideCacheModal() {
    document.getElementById('cache-modal').classList.remove('show');
}

async function loadCacheList() {
    try {
        const response = await fetch('/api/caches');
        const data = await response.json();
        const listEl = document.getElementById('cache-list');

        if (data.success && data.data.caches.length > 0) {
            let html = '<table class="cache-table"><thead><tr><th>文档名称</th><th>下载日期</th><th>大小</th><th>操作</th></tr></thead><tbody>';
            data.data.caches.forEach(cache => {
                const sizeStr = formatFileSize(cache.size);
                html += `<tr>
                    <td>${escapeHtml(cache.name)}</td>
                    <td>${cache.date}</td>
                    <td>${sizeStr}</td>
                    <td>
                        <button class="btn-small btn-primary" onclick="loadCache('${escapeHtml(cache.filename)}')">加载</button>
                        <button class="btn-small btn-danger" onclick="deleteCache('${escapeHtml(cache.filename)}')">删除</button>
                    </td>
                </tr>`;
            });
            html += '</tbody></table>';
            listEl.innerHTML = html;
        } else {
            listEl.innerHTML = '<p class="no-data">暂无缓存文件</p>';
        }
    } catch (error) {
        console.error('Failed to load caches:', error);
        document.getElementById('cache-list').innerHTML = '<p class="error">加载失败</p>';
    }
}

async function deleteCache(filename) {
    if (!confirm(`确定要删除缓存 "${filename}" 吗？`)) return;

    try {
        const response = await fetch(`/api/caches/${encodeURIComponent(filename)}`, {
            method: 'DELETE'
        });
        const data = await response.json();
        if (data.success) {
            await loadCacheList();
        } else {
            alert(data.error || '删除失败');
        }
    } catch (error) {
        console.error('Failed to delete cache:', error);
        alert('删除失败');
    }
}

let currentCacheFile = null;  // 当前选中的缓存文件

async function loadCache(filename) {
    try {
        // 保存当前选中的缓存文件
        currentCacheFile = filename;

        // 获取该缓存文件的 sheets
        const response = await fetch(`/api/caches/${encodeURIComponent(filename)}/sheets`);
        const data = await response.json();

        if (data.success) {
            currentSheets = data.data.sheets;
            populateSheetSelect();

            // 默认选择第一个 sheet
            if (currentSheets.length > 0) {
                currentSheet = currentSheets[0];
                await loadDataFromCache(filename, currentSheet);
            }

            hideCacheModal();
        } else {
            alert(data.error || '加载失败');
        }
    } catch (error) {
        console.error('Failed to load cache:', error);
        alert('加载失败');
    }
}

async function loadDataFromCache(filename, sheetName) {
    try {
        const response = await fetch('/api/load_sheet_from_cache', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                filename: filename,
                sheet_name: sheetName
            })
        });

        const data = await response.json();
        console.log('[DEBUG loadDataFromCache] 收到响应:', data);
        if (data.success) {
            allRequirements = data.data.requirements;
            allGroups = data.data.groups;
            allStats = data.data.stats || {};

            console.log('[DEBUG loadDataFromCache] allRequirements 数量:', allRequirements.length);
            console.log('[DEBUG loadDataFromCache] allGroups 数量:', allGroups.length);
            console.log('[DEBUG loadDataFromCache] allStats:', allStats);

            mergedRequirements = allRequirements.filter(r => r._is_first_in_group);
            groups = allGroups;

            console.log('[DEBUG loadDataFromCache] mergedRequirements 数量:', mergedRequirements.length);

            renderStats();
            renderRiskCards();
            renderRequirements();
            updateTesterFilter();
        } else {
            alert(data.error || '加载数据失败');
        }
    } catch (error) {
        console.error('Failed to load data from cache:', error);
        alert('加载数据失败');
    }
}

function populateSheetSelect() {
    const select = document.getElementById('sheet-select');
    select.innerHTML = '<option value="">选择Sheet</option>';
    currentSheets.forEach(sheet => {
        const option = document.createElement('option');
        option.value = sheet;
        option.textContent = sheet;
        select.appendChild(option);
    });
}

function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ============ 启动 ============

document.addEventListener('DOMContentLoaded', init);
