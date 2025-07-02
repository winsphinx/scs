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
│   ├── static/         # 静态资源
│   └── index.html      # 前端页面
├── tests/              # 测试代码
├── utils/              # 工具模块
│   ├── config.py       # 配置管理
│   ├── db.py           # 数据库操作
│   └── logging.py      # 日志配置
├── .env.example        # 环境变量示例
├── main.py             # 主程序入口
├── pyproject.toml      # 项目库配置
└── uv.lock             # 依赖锁定文件
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
python -m unittest discover -s ./test/
```

## API使用说明

1. 启动服务：
```bash
uv run main.py
```

2. 创建投诉(POST):
```
POST /complaint/
Content-Type: application/json

{
    "title": "投诉标题",
    "content": "投诉内容",
    "category": "投诉类别"
}
```

3. 查询投诉(GET):
```
GET /complaint/
```

4. 智能问答(POST):
```
POST /query/
Content-Type: application/json

{
    "question": "你的问题"
}
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