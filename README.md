# 智能客户服务系统 (Smart Customer Service)

## 项目概述

本项目是一个智能客户服务系统，包含爬虫、数据库和LLM平台三部分功能，用于收集、存储和处理客户投诉数据。

## 功能说明

1. 爬虫模块：从目标网站抓取投诉数据并保存为JSON格式
2. 数据库模块：使用SQLite存储结构化投诉数据
3. API服务：提供投诉数据的CRUD操作
4. LLM集成：在设置API_KEY后提供智能问答功能

## 项目结构

```
.
├── data/               # 数据存储目录
|   └── schema.sql      # 数据库表结构
├── logs/               # 日志文件
├── services/           # 服务模块
│   ├── fetch.py        # 数据抓取服务
│   └── llm.py          # LLM服务实现
├── templates/          # 前端资源
│   ├── static/         # 静态资源目录
│   └── index.html      # 前端页面
├── tests/              # 测试代码目录
├── utils/              # 工具模块
│   ├── config.py       # 配置管理
│   ├── db.py           # 数据库操作
│   └── logging.py      # 日志配置
├── .env.example        # 环境变量示例
└── main.py             # 主程序入口
```

## 开发环境

- Python 3.12+
- uv (推荐) 或 pip
- SQLite 3

## 配置说明

1. 复制`.env.example`为`.env`
2. 在`.env`中设置 API_KEY、API_BASE（模型地址）、MODEL_NAME（模型名称）

## 安装指南

1. 克隆仓库
```bash
git clone https://github.com/winsphinx/scs
```
2. 安装依赖
```bash
uv sync
```
3. 运行项目
```bash
uv run main.py
```

## 测试方法

```bash
source .venv/Scripts/activate
python -m unittest discover -s ./test/
```

## API使用说明

### 基础信息
- 基础URL: `http://localhost:8000`
- 默认端口: 8000
- 响应格式: JSON

### 投诉管理API

#### 1. 创建投诉 (POST)
```
POST /complaints/
Content-Type: application/json

请求示例:
{
    "complaint_time": "2025-02-02T13:00:00",
    "content": "网络信号覆盖存在缺陷，通话经常中断",
    "user_id": "user_12345",
    "complaint_category": "网络质量",
    "reply": null
}

成功响应 (201 Created):
{
    "id": 123,
    "complaint_time": "2025-02-02T13:00:00",
    "content": "网络信号覆盖存在缺陷，通话经常中断",
    "user_id": "user_12345",
    "complaint_category": "网络质量",
    "reply": null
}

错误响应:
- 422 Unprocessable Entity: 请求参数格式错误或缺失必填字段
```

#### 2. 查询投诉列表 (GET)
```
GET /complaints/
GET /complaints/?q=网络质量
GET /complaints/?skip=0&limit=10

成功响应 (200 OK):
[
    {
        "id": 123,
        "complaint_time": "2025-02-02T13:00:00",
        "content": "网络信号覆盖存在缺陷，通话经常中断",
        "user_id": "user_12345",
        "complaint_category": "网络质量",
        "reply": null
    }
]

查询参数说明：
- `q`: 搜索关键词，支持在内容和分类中搜索
- `skip`: 跳过的记录数，用于分页（默认：0）
- `limit`: 返回的最大记录数（默认：100）
```

#### 3. 获取单个投诉详情 (GET)
```
GET /complaints/{complaint_id}

成功响应 (200 OK):
{
    "complaint_time": "2025-02-02T13:00:00",
    "content": "网络信号覆盖存在缺陷，通话经常中断",
    "user_id": "user_12345",
    "complaint_category": "网络质量",
    "reply": null
}

错误响应:
- 404 Not Found: 投诉记录不存在
```

#### 4. 更新投诉 (PUT)
```
PUT /complaints/{complaint_id}
Content-Type: application/json

请求示例:
{
    "complaint_time": "2025-02-02T13:00:00",
    "content": "网络信号覆盖存在缺陷，通话经常中断",
    "user_id": "user_12345",
    "complaint_category": "网络质量",
    "reply": "已安排技术人员现场处理"
}

成功响应 (200 OK):
{
    "complaint_time": "2025-02-02T13:00:00",
    "content": "网络信号覆盖存在缺陷，通话经常中断",
    "user_id": "user_12345",
    "complaint_category": "网络质量",
    "reply": "已安排技术人员现场处理"
}

错误响应:
- 404 Not Found: 投诉记录不存在
- 422 Unprocessable Entity: 请求参数格式错误
```

#### 5. 删除投诉 (DELETE)
```
DELETE /complaints/{complaint_id}

成功响应 (200 OK):
{
    "message": "Complaint deleted"
}

错误响应:
- 404 Not Found: 投诉记录不存在
```

### 统计分析API

#### 6. 获取投诉统计 (GET)
```
GET /statistics/

成功响应 (200 OK):
{
    "网络质量": 45,
    "服务态度": 32,
    "费用争议": 28,
    "业务办理": 15,
    "其它": 10
}

返回各分类的投诉数量统计，按数量降序排列
```

### 数据模拟API

#### 7. 生成模拟数据 (POST)
```
POST /simulate/

成功响应 (200 OK):
[
    {
        "id": 124,
        "complaint_time": "2024-01-15T14:20:00",
        "content": "我的网络质量信号覆盖差",
        "user_id": "user_0842",
        "complaint_category": "网络质量",
        "reply": null
    }
]

生成10条模拟投诉数据用于测试
```

### 智能分析API

#### 8. 投诉内容分析 (POST)
```
POST /analyze/
Content-Type: application/json

请求示例:
{
    "text": "网络信号覆盖存在缺陷，通话经常中断"
}

成功响应 (200 OK):
{
    "category": "网络质量",
    "reply": "尊敬的用户，关于您反映的网络信号问题，我们深表歉意。建议您：1. 检查手机网络设置是否正确；2. 尝试重启手机；3. 如问题持续，请联系客服安排技术人员上门检测。感谢您的反馈！",
    "suggestion": "尊敬的用户，关于您反映的网络信号问题，我们深表歉意。建议您：1. 检查手机网络设置是否正确；2. 尝试重启手机；3. 如问题持续，请联系客服安排技术人员上门检测。感谢您的反馈！"
}

错误响应:
- 400 Bad Request: 投诉内容为空
- 500 Internal Server Error: 分析服务异常
```

## 贡献指南

1. Fork本项目
2. 创建特性分支 (`git checkout -b feature/your-feature`)
3. 提交变更 (`git commit -am 'Add some feature'`)
4. 推送分支 (`git push origin feature/your-feature`)
5. 创建Pull Request

## 许可证

MIT License

Copyright (c) 2025-present