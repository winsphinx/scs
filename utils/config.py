import re
from typing import Dict

# 数据库配置
SQLALCHEMY_DATABASE_URL = "sqlite:///./data/complaints.db"

# 产品匹配模式配置
PRODUCT_PATTERNS: Dict[str, re.Pattern] = {
    "手机": re.compile(r"手机|mobile|phone|cellphone|smartphone", re.IGNORECASE),
    "宽带": re.compile(r"宽带|broadband|wifi|网络|internet", re.IGNORECASE),
    "固话": re.compile(r"固话|座机|landline|telephone", re.IGNORECASE),
}

# 回复模板配置
REPLY_TEMPLATES: Dict[str, str] = {
    "分类": "建议：安排技术人员检查该通信设备问题，预计1-3个工作日内完成。",
    "其它": "建议：客服人员将联系您了解详细情况。",
}

# 分类提示模板
CLASSIFICATION_PROMPT = """你是一个通信服务分类专家，请严格从[手机、宽带、固话]中选择最匹配的类别，如果没有匹配项则返回'其它'。特别注意：账单、发票、服务态度等问题都属于'其它'类别。投诉内容：{text}"""

# 回复生成提示模板
REPLY_PROMPT = """根据客户投诉文本和分类结果，直接提供核心解决方案和建议，不要包含任何问候语或道歉：
投诉文本：{text}
分类：{category}
建议："""

# 模拟数据配置
SIMULATION_CONFIG = {
    "categories": ["手机", "宽带", "固话", "其它"],
    "problems": {
        "手机": ["信号差", "无法上网", "电池耗电快", "屏幕失灵"],
        "宽带": ["网速慢", "频繁掉线", "无法连接", "延迟高"],
        "固话": ["无声音", "杂音大", "无法拨出", "来电不响"],
        "其它": ["服务问题", "费用争议", "网络覆盖问题"],
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
示例输入：'查找用户 USER001 最近3天关于手机的投诉'
示例输出：and_(Complaint.user_id == '123', Complaint.complaint_time >= datetime.now() - timedelta(days=3), Complaint.complaint_category == '手机')
查询内容：{query}
输出："""
