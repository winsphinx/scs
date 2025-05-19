import os
import re
import sqlite3
from typing import Tuple

from dotenv import load_dotenv
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI


class ComplaintAnalyzer:
    def __init__(self):
        load_dotenv()
        self.mode = os.getenv("LLM_MODE", "mock")
        self.api_key = os.getenv("API_KEY")
        self.base_url = os.getenv("BASE_URL")
        self.model_name = os.getenv("MODEL_NAME")
        self.db_path = os.getenv("DATABASE_PATH", "complaints.db")
        self.conn = sqlite3.connect(self.db_path)
        self._init_db()
        self.product_patterns = {
            "电视": re.compile(r"电视|TV|television", re.IGNORECASE),
            "冰箱": re.compile(r"冰箱|refrigerator|fridge", re.IGNORECASE),
            "洗衣机": re.compile(r"洗衣机|washer|washing machine", re.IGNORECASE),
        }
        self.templates = {
            "电视": "感谢您的反馈，我们对您的电视问题表示歉意，将尽快安排维修人员与您联系。",
            "冰箱": "感谢您的反馈，我们对您的冰箱问题表示歉意，将尽快安排维修人员与您联系。",
            "洗衣机": "感谢您的反馈，我们对您的洗衣机问题表示歉意，将尽快安排维修人员与您联系。",
            "未知": "感谢您的反馈，我们将尽快处理您的问题。",
        }
        if self.mode == "real" and self.api_key:
            self.llm = ChatOpenAI(
                model=self.model_name,
                api_key=self.api_key,
                base_url=self.base_url,
            )
            self.classification_prompt = PromptTemplate(
                input_variables=["text"],
                template="你是一个客户服务分类专家，请严格从[电视、冰箱、洗衣机]中选择最匹配的类别，如果没有匹配项则返回'未知'。投诉内容：{text}",
            )
            self.classification_chain = self.classification_prompt | self.llm
            self.reply_prompt = PromptTemplate(
                input_variables=["text", "category"],
                template="根据以下客户投诉文本和分类结果，生成合适的回复：\n投诉文本：{text}\n分类：{category}",
            )
            self.reply_chain = self.reply_prompt | self.llm

            self.query_parser_prompt = PromptTemplate(
                input_variables=["query"],
                template="将用户自然语言查询转换为SQL WHERE条件（使用SQLAlchemy语法）：\n"
                "可用字段：complaint_time（datetime）, content（str）, user_id（str）, product_category（str）\n"
                "示例输入：'查找用户123最近3天关于电视的投诉'\n"
                "示例输出：and_(Complaint.user_id == '123', Complaint.complaint_time >= datetime.now() - timedelta(days=3), Complaint.product_category == '电视')\n"
                "查询内容：{query}\n"
                "输出：",
            )
            self.query_parser_chain = self.query_parser_prompt | self.llm
        else:
            self.llm = None
            self.classification_chain = None
            self.reply_chain = None

    def classify_complaint(self, text: str) -> str:
        """
        分类客户投诉文本，判断涉及的产品类别。
        """
        if self.mode == "real" and self.llm:
            # Use the classification chain
            result = self.classification_chain.invoke(text)
            return result.content.strip()
        else:
            for category, pattern in self.product_patterns.items():
                if pattern.search(text):
                    return category
            return "未知"

    def generate_reply(self, text: str, category: str = None) -> str:
        """
        根据投诉文本和分类结果生成回复。
        """
        if not category:
            category = self.classify_complaint(text)
        if self.mode == "real" and self.llm:
            result = self.reply_chain.invoke({"text": text, "category": category})
            return result["text"].strip()
        else:
            return self.templates.get(category, self.templates["未知"])

    def analyze(self, text: str) -> Tuple[str, str]:
        """
        分析投诉文本，返回分类和回复。
        """
        category = self.classify_complaint(text)
        reply = self.generate_reply(text, category)
        self.create_complaint(text, category, reply)
        return category, reply

    def _init_db(self):
        """初始化数据库表结构"""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS complaints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT NOT NULL,
                category TEXT NOT NULL,
                reply TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """
        )
        self.conn.commit()

    def create_complaint(self, text: str, category: str, reply: str) -> int:
        """创建新的投诉记录"""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO complaints (text, category, reply)
            VALUES (?, ?, ?)
        """,
            (text, category, reply),
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_complaint(self, complaint_id: int) -> dict:
        """获取单个投诉记录"""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT id, text, category, reply, timestamp
            FROM complaints WHERE id = ?
        """,
            (complaint_id,),
        )
        row = cursor.fetchone()
        return (
            {
                "id": row[0],
                "text": row[1],
                "category": row[2],
                "reply": row[3],
                "timestamp": row[4],
            }
            if row
            else None
        )

    def update_complaint(
        self,
        complaint_id: int,
        text: str = None,
        category: str = None,
        reply: str = None,
    ) -> bool:
        """更新投诉记录"""
        updates = []
        params = []
        if text:
            updates.append("text = ?")
            params.append(text)
        if category:
            updates.append("category = ?")
            params.append(category)
        if reply:
            updates.append("reply = ?")
            params.append(reply)

        if not updates:
            return False

        params.append(complaint_id)
        query = f"""
            UPDATE complaints
            SET {', '.join(updates)}
            WHERE id = ?
        """
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        self.conn.commit()
        return cursor.rowcount > 0

    def delete_complaint(self, complaint_id: int) -> bool:
        """删除投诉记录"""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM complaints WHERE id = ?", (complaint_id,))
        self.conn.commit()
        return cursor.rowcount > 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            self.conn.close()
            self.conn = None


if __name__ == "__main__":
    complaint_analyzer = ComplaintAnalyzer()
    print(complaint_analyzer.classify_complaint("我的冰箱坏了"))
    print(complaint_analyzer.classify_complaint("我的脑袋坏了"))
