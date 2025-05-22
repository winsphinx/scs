const API_BASE = 'http://localhost:8000';

document.addEventListener('DOMContentLoaded', () => {
    loadComplaints();
    loadStatistics();

    document.querySelector('.simulate-btn').addEventListener('click', simulateData);
    document.querySelector('.refresh-btn').addEventListener('click', loadComplaints);
});

async function submitComplaint(event) {
    event.preventDefault();

    const complaintData = {
        user_id: document.getElementById('userId').value,
        complaint_category: document.getElementById('productCategory').value,
        content: document.getElementById('content').value,
        complaint_time: new Date().toISOString()
    };

    try {
        const response = await fetch(`${API_BASE}/complaints/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(complaintData)
        });

        if (!response.ok) throw new Error('提交失败');

        alert('投诉提交成功！');
        event.target.reset();
        await loadComplaints();
        await loadStatistics();
    } catch (error) {
        alert(`错误：${error.message}`);
    }
}

async function loadComplaints() {
    try {
        const response = await fetch(`${API_BASE}/complaints/`);
        const data = await response.json();

        const listContainer = document.getElementById('complaintList');
        let tableHtml = `
            <table>
                <thead>
                    <tr>
                        <th>产品类别</th>
                        <th>用户ID</th>
                        <th>投诉时间</th>
                        <th>投诉内容</th>
                        <th>回复状态</th>
                    </tr>
                </thead>
                <tbody>
                    ${data.map(complaint => `
                        <tr ondblclick="showComplaintDetails('${complaint.complaint_category}', '${complaint.user_id}', '${new Date(complaint.complaint_time).toLocaleString()}', '${complaint.content.replace(/'/g, "\\'").replace(/\n/g, "\\n")}', '${complaint.reply ? complaint.reply.replace(/'/g, "\\'").replace(/\n/g, "\\n") : ''}')">
                            <td>${complaint.complaint_category}</td>
                            <td>${complaint.user_id}</td>
                            <td>${new Date(complaint.complaint_time).toLocaleString()}</td>
                            <td>${complaint.content}</td>
                            <td>${complaint.reply || '未回复'}</td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;
        listContainer.innerHTML = tableHtml;
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

        const yAxis = document.createElement('div');
        yAxis.classList.add('chart-y-axis');
        const yAxisLabels = [];
        let step = 1;
        if (maxCount <= 0) maxCount = 1;
        if (maxCount > 20) {
            step = Math.ceil(maxCount / 10) * 2;
        } else if (maxCount > 10) {
            step = 5;
        } else if (maxCount > 5) {
            step = 2;
        }

        let minMaxLabel = Math.ceil(maxCount / step) * step;
        const maxLabelValue = Math.max(minMaxLabel + step, step);

        yAxisLabels.push(0);
        for (let i = step; i <= maxLabelValue; i += step) {
            yAxisLabels.push(i);
        }
        yAxisLabels.sort((a, b) => b - a);

        yAxisLabels.forEach(labelText => {
            const label = document.createElement('div');
            label.classList.add('y-axis-label');
            label.textContent = labelText;
            yAxis.appendChild(label);
        });

        chartInner.appendChild(yAxis);

        const barsContainer = document.createElement('div');
        barsContainer.classList.add('chart-bars-container');

        categories.forEach(([category, count]) => {
            const barWrapper = document.createElement('div');
            barWrapper.classList.add('chart-bar-wrapper');

            const bar = document.createElement('div');
            bar.classList.add('chart-bar');
            const barHeight = (count / maxLabelValue) * 300;
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
const complaintModal = document.getElementById('complaintModal');
const modalCategory = document.getElementById('modalCategory');
const modalUserId = document.getElementById('modalUserId');
const modalTime = document.getElementById('modalTime');
const modalContent = document.getElementById('modalContent');
const closeButton = document.querySelector('.close-button');

function showComplaintDetails(category, userId, time, content, reply) {
    modalCategory.textContent = category;
    modalUserId.textContent = userId;
    modalTime.textContent = time;
    modalContent.textContent = content;
    modalReply.textContent = reply || '未回复';
    complaintModal.style.display = 'flex';
}

closeButton.addEventListener('click', () => {
    complaintModal.style.display = 'none';
});

window.addEventListener('click', (event) => {
    if (event.target === complaintModal) {
        complaintModal.style.display = 'none';
    }
});

async function handleSearch() {
    const query = document.getElementById('naturalQuery').value;
    const outputDiv = document.getElementById('llmOutput');

    try {
        const response = await fetch(`${API_BASE}/complaints/?q=${encodeURIComponent(query)}`);

        if (!response.ok) throw new Error('查询失败');

        const complaints = await response.json();
        outputDiv.innerHTML = `
            <div class="query-result">
                <h3>查询解析：</h3>
                <p>匹配记录：${complaints.length} 条</p>
            </div>
        `;

        // 更新投诉列表显示查询结果
        const listContainer = document.getElementById('complaintList');
        let tableHtml = `
            <table>
                <thead>
                    <tr>
                        <th>产品类别</th>
                        <th>用户ID</th>
                        <th>投诉时间</th>
                        <th>投诉内容</th>
                        <th>回复状态</th>
                    </tr>
                </thead>
                <tbody>
                    ${complaints.map(complaint => `
                        <tr ondblclick="showComplaintDetails('${complaint.complaint_category}', '${complaint.user_id}', '${new Date(complaint.complaint_time).toLocaleString()}', '${complaint.content.replace(/'/g, "\\'").replace(/\n/g, "\\n")}', '${complaint.reply ? complaint.reply.replace(/'/g, "\\'").replace(/\n/g, "\\n") : ''}')">
                            <td>${complaint.complaint_category}</td>
                            <td>${complaint.user_id}</td>
                            <td>${new Date(complaint.complaint_time).toLocaleString()}</td>
                            <td>${complaint.content}</td>
                            <td>${complaint.reply || '未回复'}</td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;
        listContainer.innerHTML = tableHtml;
    } catch (error) {
        outputDiv.innerHTML = `<div class="error">错误：${error.message}</div>`;
    }
}