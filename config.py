import re
from typing import Dict

# 产品匹配模式配置
PRODUCT_PATTERNS: Dict[str, re.Pattern] = {
    "电视": re.compile(r"电视|TV|television", re.IGNORECASE),
    "冰箱": re.compile(r"冰箱|refrigerator|fridge", re.IGNORECASE),
    "洗衣机": re.compile(r"洗衣机|washer|washing machine", re.IGNORECASE),
}

# 回复模板配置
REPLY_TEMPLATES: Dict[str, str] = {
    "电视": "感谢您的反馈，我们对您的电视问题表示歉意，将尽快安排维修人员与您联系。",
    "冰箱": "感谢您的反馈，我们对您的冰箱问题表示歉意，将尽快安排维修人员与您联系。",
    "洗衣机": "感谢您的反馈，我们对您的洗衣机问题表示歉意，将尽快安排维修人员与您联系。",
    "未知": "感谢您的反馈，我们将尽快处理您的问题。",
}

# 分类提示模板
CLASSIFICATION_PROMPT = """你是一个客户服务分类专家，请严格从[电视、冰箱、洗衣机]中选择最匹配的类别，如果没有匹配项则返回'未知'。投诉内容：{text}"""

# 回复生成提示模板
REPLY_PROMPT = """根据以下客户投诉文本和分类结果，生成合适的回复：\n投诉文本：{text}\n分类：{category}"""

# 模拟数据配置
SIMULATION_CONFIG = {
    "categories": ["电视", "冰箱", "洗衣机", "未知"],
    "problems": {
        "电视": ["屏幕有坏点", "无法开机", "遥控器失灵", "画面模糊"],
        "冰箱": ["不制冷", "噪音大", "门封不严", "结霜严重"],
        "洗衣机": ["不脱水", "漏水", "噪音大", "无法启动"],
        "未知": ["产品使用问题", "售后服务问题", "质量投诉"],
    },
    "replies": [
        "已处理，请检查是否解决",
        "正在处理中，预计3个工作日内完成",
        "已转交相关部门处理",
        "需要更多信息，客服将联系您",
        None,
    ],
}

# 查询解析提示模板
QUERY_PARSER_PROMPT = """将用户自然语言查询转换为SQL WHERE条件（使用SQLAlchemy语法）：
可用字段：complaint_time（datetime）, content（str）, user_id（str）, complaint_category（str）
示例输入：'查找用户123最近3天关于电视的投诉'
示例输出：and_(Complaint.user_id == '123', Complaint.complaint_time >= datetime.now() - timedelta(days=3), Complaint.complaint_category == '电视')
查询内容：{query}
输出："""
