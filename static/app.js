// TestPace-Track 前端逻辑

let currentVersion = null;
let currentSheet = null;
let currentSheets = [];
let allRequirements = [];
let allGroups = [];
let allStats = {};
let versionPlans = [];

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
    document.getElementById('cookie-btn').addEventListener('click', showCookieModal);
    document.getElementById('cookie-cancel-btn').addEventListener('click', hideCookieModal);
    document.getElementById('cookie-form').addEventListener('submit', saveCookie);
    document.getElementById('empty-fields-close-btn').addEventListener('click', hideEmptyFieldsModal);

    document.querySelectorAll('.risk-cards .card').forEach(card => {
        card.addEventListener('click', (e) => {
            const type = e.target.closest('[data-type]')?.dataset.type;
            if (type) filterByRiskType(type, e.target);
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
        if (data.success) {
            allRequirements = data.data.requirements;
            allGroups = data.data.groups;
            allStats = data.data.stats || {};

            renderStats();
            renderRiskCards();
            populateTesterFilter();
            renderTable(allRequirements);
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

    const byVersion = {};
    versionPlans.forEach(p => {
        if (!byVersion[p.version_name]) {
            byVersion[p.version_name] = [];
        }
        byVersion[p.version_name].push(p);
    });

    let html = '';
    for (const [versionName, plans] of Object.entries(byVersion)) {
        html += `<div class="timeline-version">`;
        html += `<h4 style="margin:0 0 8px;color:var(--color-primary)">${versionName}</h4>`;
        html += `<div class="timeline-stages">`;

        plans.sort((a, b) => a.id - b.id).forEach(plan => {
            const isOverdue = plan.target_date && new Date(plan.target_date) < new Date();
            html += `
                <div class="timeline-stage ${isOverdue ? 'overdue' : ''}">
                    <span class="stage-name">${plan.stage_name}</span>
                    <span class="stage-date">${plan.target_date || '未设置'}</span>
                    <div class="stage-actions">
                        <button class="edit-btn" onclick="editPlan(${plan.id}, '${plan.stage_name}', '${plan.target_date || ''}')">编辑</button>
                        <button class="delete-btn" onclick="deletePlan(${plan.id})">删除</button>
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
    const formData = {
        version_id: document.getElementById('plan-version-id').value,
        version_name: 'Beta_T1',
        stage_name: document.getElementById('plan-stage-name').value,
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
    const risks = {
        not_started: allRequirements.filter(r =>
            r.risks && (r.risks.includes('serial_review_incomplete') || r.risks.includes('reverse_serial_incomplete'))
        ),
        reverse_delayed: allRequirements.filter(r =>
            r.risks && r.risks.includes('reverse_serial_incomplete')
        ),
        test_delayed: allRequirements.filter(r =>
            r.risks && r.risks.includes('test_progress_delayed')
        ),
        empty_fields: allRequirements.filter(r =>
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

    let filtered = allRequirements;

    if (type === 'not-started') {
        filtered = filtered.filter(r =>
            r.risks && (r.risks.includes('serial_review_incomplete') || r.risks.includes('reverse_serial_incomplete'))
        );
    } else if (type === 'reverse-delayed') {
        filtered = filtered.filter(r => r.risks && r.risks.includes('reverse_serial_incomplete'));
    } else if (type === 'test-delayed') {
        filtered = filtered.filter(r => r.risks && r.risks.includes('test_progress_delayed'));
    }

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

    tbody.innerHTML = requirements.map(req => {
        const riskTags = (req.risks || []).map(risk =>
            `<span class="risk-tag ${risk}">${getRiskLabel(risk)}</span>`
        ).join('');

        const detailLink = req['需求编号']
            ? `<a href="https://clouddevops.huawei.com/workitem/+${req['需求编号']}" target="_blank">详情</a>`
            : '';

        const progress = req['测试进度'] || 0;
        const progressClass = progress >= 100 ? 'progress-complete' : progress > 0 ? 'progress-active' : 'progress-zero';

        return `
            <tr>
                <td>${req['特性分类'] || ''}</td>
                <td>${req['业务团队'] || ''}</td>
                <td>${req['需求编号'] || ''}</td>
                <td class="desc-cell" title="${req['需求描述'] || ''}">${req['需求描述'] || ''}</td>
                <td>${req['测试人员'] || ''}</td>
                <td class="${progressClass}">${progress}%</td>
                <td>${riskTags}</td>
                <td>${detailLink}</td>
            </tr>
        `;
    }).join('');
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
                document.getElementById('config-bucket-path').value = doc.bucket_path || '';
                document.getElementById('config-doc-id').value = doc.doc_id || '';
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
        bucket_path: document.getElementById('config-bucket-path').value,
        doc_id: document.getElementById('config-doc-id').value
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

// ============ Cookie 配置 ============

async function showCookieModal() {
    await checkCookieStatus();
    document.getElementById('cookie-modal').classList.add('show');
}

function hideCookieModal() {
    document.getElementById('cookie-modal').classList.remove('show');
    document.getElementById('cookie-form').reset();
}

async function checkCookieStatus() {
    try {
        const response = await fetch('/api/cookie');
        const data = await response.json();
        if (data.success) {
            const statusEl = document.getElementById('cookie-status-value');
            if (data.data.configured) {
                statusEl.textContent = '✅ 已配置';
                statusEl.style.color = 'var(--color-success)';
            } else {
                statusEl.textContent = '⚠️ 未配置';
                statusEl.style.color = 'var(--color-warning)';
            }
        }
    } catch (error) {
        console.error('Failed to check cookie status:', error);
    }
}

async function saveCookie(e) {
    e.preventDefault();
    const cookie = document.getElementById('cookie-input').value;

    try {
        const response = await fetch('/api/cookie', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ cookie })
        });
        const data = await response.json();
        if (data.success) {
            hideCookieModal();
            alert('Cookie 保存成功');
        } else {
            alert('保存失败');
        }
    } catch (error) {
        console.error('Failed to save cookie:', error);
        alert('保存失败');
    }
}

// ============ 启动 ============

document.addEventListener('DOMContentLoaded', init);
