# 智能客户服务系统

## 项目概述
本项目是一个智能客户服务系统，包含爬虫、数据库和LLM平台三部分功能，用于收集、存储和处理客户投诉数据。

## 功能说明
1. 爬虫模块：从目标网站抓取投诉数据并保存为JSON格式
2. 数据库模块：使用SQLite存储结构化投诉数据
3. API服务：提供投诉数据的CRUD操作
4. LLM集成：在设置API_KEY后提供智能问答功能

## 安装指南
1. 安装Python 3.8+
2. 安装依赖库：
```bash
pip install -r requirements.txt
```

## API使用说明
1. 启动服务：
```bash
python main.py
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
1. 复制.env.example为.env
2. 在.env中设置LLM_API_KEY
3. 其他可选配置：
   - LLM_MODEL_NAME: 模型名称(默认gpt-3.5-turbo)
   - LLM_TEMPERATURE: 温度参数(默认0.7)
   - LLM_MAX_TOKENS: 最大token数(默认1000)