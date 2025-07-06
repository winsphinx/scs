const API_BASE = 'http://localhost:8000';

async function loadComplaints() {
    try {
        const response = await fetch(`${API_BASE}/complaints/`);
        const data = await response.json();

        const tbody = document.getElementById('complaintList');
        tbody.innerHTML = data.map(complaint => `
            <tr ondblclick="showComplaintDetails('${complaint.complaint_category}', '${complaint.user_id}', '${new Date(complaint.complaint_time).toLocaleString()}', '${complaint.content.replace(/'/g, "\\'").replace(/\n/g, "\\n")}', '${complaint.reply ? complaint.reply.replace(/'/g, "\\'").replace(/\n/g, "\\n") : ''}')">
                <td>${complaint.complaint_category}</td>
                <td>${complaint.user_id}</td>
                <td>${new Date(complaint.complaint_time).toLocaleString()}</td>
                <td>${complaint.content}</td>
                <td>${complaint.reply || '未回复'}</td>
                <td><button onclick="showComplaintDetails('${complaint.complaint_category}', '${complaint.user_id}', '${new Date(complaint.complaint_time).toLocaleString()}', '${complaint.content.replace(/'/g, "\\'").replace(/\n/g, "\\n")}', '${complaint.reply ? complaint.reply.replace(/'/g, "\\'").replace(/\n/g, "\\n") : ''}')">查看</button></td>
            </tr>
        `).join('');
    } catch (error) {
        console.error('加载投诉列表失败:', error);
    }
}

async function loadStatistics() {
    try {
        const response = await fetch(`${API_BASE}/statistics/`);
        const data = await response.json();

        const totalCount = Object.values(data).reduce((sum, count) => sum + count, 0);
        document.getElementById('totalComplaints').textContent = ` (共${totalCount}条)`;

        const chartContainer = document.getElementById('categoryChart');
        chartContainer.innerHTML = '';

        const categories = Object.entries(data).sort((a, b) => b[1] - a[1]);
        const maxCount = Math.max(...categories.map(([_, count]) => count), 0);

        const chartInner = document.createElement('div');
        chartInner.classList.add('chart-inner');

        const maxLabelValue = maxCount <= 0 ? 1 : maxCount;

        const barsContainer = document.createElement('div');
        barsContainer.classList.add('chart-bars-container');

        categories.forEach(([category, count]) => {
            const barWrapper = document.createElement('div');
            barWrapper.classList.add('chart-bar-wrapper');

            const bar = document.createElement('div');
            bar.classList.add('chart-bar');
            const barHeight = (count / maxLabelValue) * (chartContainer.clientHeight - 50);
            bar.style.height = `${barHeight}px`;
            bar.setAttribute('data-count', count);

            const label = document.createElement('div');
            label.classList.add('chart-label');
            label.textContent = category;

            barWrapper.appendChild(bar);
            barWrapper.appendChild(label);
            barsContainer.appendChild(barWrapper);
        });

        chartInner.appendChild(barsContainer);
        chartContainer.appendChild(chartInner);

    } catch (error) {
        console.error('加载统计信息失败:', error);
    }
}

async function simulateData() {
    try {
        const response = await fetch(`${API_BASE}/simulate/`, {
            method: 'POST'
        });
        if (!response.ok) throw new Error('模拟数据生成失败');
        alert('成功生成10条模拟数据！');
        await loadComplaints();
        await loadStatistics();
    } catch (error) {
        alert(`错误：${error.message}`);
    }
}

async function handleSearch() {
    const query = document.getElementById('naturalQuery').value;
    const outputDiv = document.getElementById('llmOutput');
    outputDiv.innerHTML = '<div class="loading">查询中...</div>';

    try {
        const [complaintsData, analysisData] = await Promise.all([
            fetch(`${API_BASE}/complaints/?q=${encodeURIComponent(query)}`)
                .then(res => res.ok ? res.json() : []),
            fetch(`${API_BASE}/analyze/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text: query })
            }).then(res => res.ok ? res.json() : { suggestion: "分析服务不可用" })
        ]);

        const complaints = Array.isArray(complaintsData) ? complaintsData : [];
        const analysis = analysisData;

        // 显示分析结果弹窗
        showAnalysisResult(analysis);

        // 清空查询结果区域
        outputDiv.innerHTML = '';

        // 更新投诉列表
        const tbody = document.getElementById('complaintList');
        tbody.innerHTML = complaints.map(complaint => `
            <tr ondblclick="showComplaintDetails('${complaint.complaint_category}', '${complaint.user_id}', '${new Date(complaint.complaint_time).toLocaleString()}', '${complaint.content.replace(/'/g, "\\'").replace(/\n/g, "\\n")}', '${complaint.reply ? complaint.reply.replace(/'/g, "\\'").replace(/\n/g, "\\n") : ''}')">
                <td>${complaint.complaint_category}</td>
                <td>${complaint.user_id}</td>
                <td>${new Date(complaint.complaint_time).toLocaleString()}</td>
                <td>${complaint.content}</td>
                <td>${complaint.reply || '未回复'}</td>
                <td><button onclick="showComplaintDetails('${complaint.complaint_category}', '${complaint.user_id}', '${new Date(complaint.complaint_time).toLocaleString()}', '${complaint.content.replace(/'/g, "\\'").replace(/\n/g, "\\n")}', '${complaint.reply ? complaint.reply.replace(/'/g, "\\'").replace(/\n/g, "\\n") : ''}')">查看</button></td>
            </tr>
        `).join('');
    } catch (error) {
        outputDiv.innerHTML = `<div class="error">查询失败: ${error.message}</div>`;
        console.error("查询失败:", error);
    }
}

function showComplaintDetails(category, userId, time, content, reply) {
    document.getElementById('modalCategory').textContent = category;
    document.getElementById('modalUserId').textContent = userId;
    document.getElementById('modalTime').textContent = time;
    document.getElementById('modalContent').textContent = content;
    document.getElementById('modalReply').textContent = reply || '未回复';
    document.getElementById('complaintModal').style.display = 'flex';
}

function showAnalysisResult(analysis) {
    document.getElementById('analysisCategory').textContent = analysis.category || '未知';
    document.getElementById('analysisReason').textContent = analysis.reason || '无原因分析';

    // 将Markdown格式的处理建议转换为HTML
    const suggestion = analysis.suggestion || '无处理建议';
    let processedSuggestion = suggestion.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>'); // 加粗

    const lines = processedSuggestion.split('\n');
    let htmlParts = [];
    let inList = false;

    lines.forEach(line => {
        const trimmedLine = line.trim();
        if (trimmedLine.match(/^\d+\.\s+/) || trimmedLine.match(/^[\*\-\+]\s+/)) { // 匹配数字或无序列表项
            if (!inList) {
                htmlParts.push('<ul>');
                inList = true;
            }
            htmlParts.push(`<li>${trimmedLine.replace(/^\d+\.\s+/, '').replace(/^[\*\-\+]\s+/, '')}</li>`);
        } else {
            if (inList) {
                htmlParts.push('</ul>');
                inList = false;
            }
            if (trimmedLine) { // 避免空行生成<p>
                htmlParts.push(`<p>${trimmedLine}</p>`);
            }
        }
    });

    if (inList) {
        htmlParts.push('</ul>');
    }

    document.getElementById('analysisSuggestion').innerHTML = htmlParts.join('');
    document.getElementById('analysisModal').style.display = 'flex';
}

document.addEventListener('DOMContentLoaded', () => {
    // Initial data load
    loadComplaints();
    loadStatistics();

    // Button listeners
    document.querySelector('.simulate-btn').addEventListener('click', simulateData);
    document.querySelector('.refresh-btn').addEventListener('click', loadComplaints);
    document.querySelector('.search-btn').addEventListener('click', handleSearch);

    // Modal listeners
    const complaintModal = document.getElementById('complaintModal');
    const closeButton = document.querySelector('.close-button');

    closeButton.addEventListener('click', () => {
        complaintModal.style.display = 'none';
    });

    window.addEventListener('click', (event) => {
        if (event.target === complaintModal) {
            complaintModal.style.display = 'none';
        }
        if (event.target === document.getElementById('analysisModal')) {
            document.getElementById('analysisModal').style.display = 'none';
        }
    });

    // 添加分析结果弹窗关闭按钮事件
    document.querySelector('#analysisModal .close-button').addEventListener('click', () => {
        document.getElementById('analysisModal').style.display = 'none';
    });
});