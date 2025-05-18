const API_BASE = 'http://localhost:8000';

document.addEventListener('DOMContentLoaded', () => {
    loadComplaints();
    loadStatistics();

    // 为按钮绑定事件监听
    document.querySelector('.simulate-btn').addEventListener('click', simulateData);
    document.querySelector('.refresh-btn').addEventListener('click', loadComplaints);
});

async function submitComplaint(event) {
    event.preventDefault();

    const complaintData = {
        user_id: document.getElementById('userId').value,
        product_category: document.getElementById('productCategory').value,
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
                    </tr>
                </thead>
                <tbody>
                    ${data.map(complaint => `
                        <tr ondblclick="showComplaintDetails('${complaint.product_category}', '${complaint.user_id}', '${new Date(complaint.complaint_time).toLocaleString()}', '${complaint.content.replace(/'/g, "\\'").replace(/\n/g, "\\n")}')">
                            <td>${complaint.product_category}</td>
                            <td>${complaint.user_id}</td>
                            <td>${new Date(complaint.complaint_time).toLocaleString()}</td>
                            <td>${complaint.content}</td>
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

        const chartContainer = document.getElementById('categoryChart');
        // Clear previous chart content
        chartContainer.innerHTML = '';

        const categories = Object.entries(data).sort((a, b) => b[1] - a[1]);
        const maxCount = Math.max(...categories.map(([_, count]) => count), 0);

        // Create chart container
        const chartInner = document.createElement('div');
        chartInner.classList.add('chart-inner');

        // Create Y-axis labels (simplified based on image)
        const yAxis = document.createElement('div');
        yAxis.classList.add('chart-y-axis');
        // Add Y-axis labels based on the max count, adjust as needed
        // Add labels every 2 units, up to maxCount + a small buffer
        // Add Y-axis labels including 0 and 4
        const yAxisLabels = [];
        // Enhanced Y-axis scaling algorithm
        let step = 1;
        if (maxCount <= 0) maxCount = 1; // Handle zero case
        if (maxCount > 20) {
            step = Math.ceil(maxCount / 10) * 2;
        } else if (maxCount > 10) {
            step = 5;
        } else if (maxCount > 5) {
            step = 2;
        }

        // Calculate max label value as the smallest multiple of step >= maxCount, plus one step for headroom
        let minMaxLabel = Math.ceil(maxCount / step) * step;
        const maxLabelValue = Math.max(minMaxLabel + step, step); // 使用实际计算值

        // Generate labels with dynamic step, ensuring 0 is included
        yAxisLabels.push(0);
        for (let i = step; i <= maxLabelValue; i += step) {
            yAxisLabels.push(i);
        }
        yAxisLabels.sort((a, b) => b - a); // Sort labels in descending order

        yAxisLabels.forEach(labelText => {
            const label = document.createElement('div');
            label.classList.add('y-axis-label');
            label.textContent = labelText;
            yAxis.appendChild(label); // Add labels
        });

        chartInner.appendChild(yAxis);


        // Create bars container
        const barsContainer = document.createElement('div');
        barsContainer.classList.add('chart-bars-container');

        categories.forEach(([category, count]) => {
            const barWrapper = document.createElement('div');
            barWrapper.classList.add('chart-bar-wrapper');

            const bar = document.createElement('div');
            bar.classList.add('chart-bar');
            // Calculate height based on count and maxCount for scaling
            // Assuming a max chart height, e.g., 200px, adjust multiplier as needed
            // Calculate height based on count and maxCount for scaling, add more padding for top labels
            // Calculate height based on count and maxLabelValue for scaling
            const barHeight = (count / maxLabelValue) * 300; // 基于调整后的最大值计算高度
            bar.style.height = `${barHeight}px`;
            bar.setAttribute('data-count', count); // Add count as data attribute

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
// Get the modal and the elements to display complaint details
const complaintModal = document.getElementById('complaintModal');
const modalCategory = document.getElementById('modalCategory');
const modalUserId = document.getElementById('modalUserId');
const modalTime = document.getElementById('modalTime');
const modalContent = document.getElementById('modalContent');
const closeButton = document.querySelector('.close-button');

function showComplaintDetails(category, userId, time, content) {
    modalCategory.textContent = category;
    modalUserId.textContent = userId;
    modalTime.textContent = time;
    modalContent.textContent = content;
    complaintModal.style.display = 'flex'; // Show the modal
}

// Close the modal when the close button is clicked
closeButton.addEventListener('click', () => {
    complaintModal.style.display = 'none';
});

// Close the modal when the user clicks anywhere outside of the modal content
window.addEventListener('click', (event) => {
    if (event.target === complaintModal) {
        complaintModal.style.display = 'none';
    }
});

// 新增智能搜索处理函数
async function handleSearch() {
    const query = document.getElementById('naturalQuery').value;
    const outputDiv = document.getElementById('llmOutput');

    try {
        const response = await fetch(`${API_BASE}/query`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ query })
        });

        if (!response.ok) throw new Error('查询失败');

        const result = await response.json();
        outputDiv.innerHTML = `
            <div class="query-result">
                <h3>查询结果：</h3>
                <p>解析条件：${result.condition}</p>
                <p>匹配记录：${result.count} 条</p>
                <pre>${JSON.stringify(result.results, null, 2)}</pre>
            </div>
        `;
    } catch (error) {
        outputDiv.innerHTML = `<div class="error">错误：${error.message}</div>`;
    }
}