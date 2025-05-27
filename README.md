# 智能客户服务系统 (SCS)

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
├── mcp/                # SQLite服务模块
├── static/             # 静态资源
├── templates/          # HTML模板
├── test/               # 测试代码
├── utils/              # 工具模块
├── config.py           # 配置文件
├── data_processing.py  # 数据处理
├── llm_service.py      # LLM服务
├── main.py             # 主程序入口
└── pyproject.toml      # 项目配置
```

## 开发环境
- Python
- uv (推荐) 或 pip
- SQLite 3

## 安装指南
1. 克隆仓库
```bash
git clone https://github.com/winsphinx/scs
```
2. 安装依赖：
```bash
uv sync
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

## 配置说明
1. 复制`.env.example`为`.env`
2. 在`.env`中设置 API_KEY、API_BASE（模型地址）、MODEL_NAME（模型名称）

## 贡献指南
1. Fork本项目
2. 创建特性分支 (`git checkout -b feature/your-feature`)
3. 提交变更 (`git commit -am 'Add some feature'`)
4. 推送分支 (`git push origin feature/your-feature`)
5. 创建Pull Request

## 许可证
MIT License

Copyright (c) 2025-present