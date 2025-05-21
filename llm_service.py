import logging
import os
import re
import sqlite3
from typing import Dict, Optional, Tuple

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

from dotenv import load_dotenv
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

try:
    from config import (
        CLASSIFICATION_PROMPT,
        PRODUCT_PATTERNS,
        QUERY_PARSER_PROMPT,
        REPLY_PROMPT,
        REPLY_TEMPLATES,
    )

    logger.info("成功加载配置文件")
except ImportError as e:
    logger.error(f"加载配置文件失败: {e}")
    raise


class ComplaintAnalyzer:
    def __init__(self):
        """初始化投诉分析器

        Raises:
            ValueError: 当必需的环境变量缺失时抛出
        """
        load_dotenv()
        self.mode = os.getenv("LLM_MODE", "mock")
        logger.info(f"初始化ComplaintAnalyzer，模式: {self.mode}")
        self.api_key = os.getenv("API_KEY")
        self.base_url = os.getenv("BASE_URL")
        self.model_name = os.getenv("MODEL_NAME")
        self.db_path = os.getenv("DATABASE_PATH", "complaints.db")
        self.conn = sqlite3.connect(self.db_path)
        self._init_db()
        self.product_patterns: Dict[str, re.Pattern] = PRODUCT_PATTERNS
        self.templates: Dict[str, str] = REPLY_TEMPLATES
        if self.mode == "enabled" and self.api_key:
            self.llm = ChatOpenAI(
                model=self.model_name,
                api_key=self.api_key,
                base_url=self.base_url,
            )
            self.classification_prompt = PromptTemplate(
                input_variables=["text"],
                template=CLASSIFICATION_PROMPT,
            )
            self.classification_chain = self.classification_prompt | self.llm
            self.reply_prompt = PromptTemplate(
                input_variables=["text", "category"],
                template=REPLY_PROMPT,
            )
            self.reply_chain = self.reply_prompt | self.llm

            self.query_parser_prompt = PromptTemplate(
                input_variables=["query"],
                template=QUERY_PARSER_PROMPT,
            )
            self.query_parser_chain = self.query_parser_prompt | self.llm
        else:
            self.llm = None
            self.classification_chain = None
            self.reply_chain = None

    def classify_complaint(self, text: str) -> str:
        """分类客户投诉文本，判断涉及的产品类别。

        Args:
            text: 要分类的投诉文本

        Returns:
            产品类别字符串

        Raises:
            ValueError: 当输入文本为空时抛出
        """
        if not text or not isinstance(text, str):
            logger.error("分类投诉时收到无效文本")
            raise ValueError("投诉文本不能为空")

        logger.debug(f"开始分类投诉文本: {text[:50]}...")
        if self.mode == "enabled" and self.llm:
            # Use the classification chain
            result = self.classification_chain.invoke(text)
            return result.content.strip()
        else:
            for category, pattern in self.product_patterns.items():
                if pattern.search(text):
                    return category
            return "未知"

    def generate_reply(self, text: str, category: Optional[str] = None) -> str:
        """根据投诉文本和分类结果生成回复。

        Args:
            text: 投诉文本
            category: 可选的产品类别，如果未提供将自动分类

        Returns:
            生成的回复文本

        Raises:
            ValueError: 当输入文本为空时抛出
        """
        if not text or not isinstance(text, str):
            logger.error("生成回复时收到无效文本")
            raise ValueError("投诉文本不能为空")

        logger.debug(f"开始为类别'{category}'生成回复")
        if not category:
            category = self.classify_complaint(text)
        if self.mode == "enabled" and self.llm:
            result = self.reply_chain.invoke({"text": text, "category": category})
            return result.content.strip()
        else:
            return self.templates.get(category, self.templates["未知"])

    def analyze(self, text: str) -> Tuple[str, str]:
        """分析投诉文本，返回分类和回复。

        Args:
            text: 要分析的投诉文本

        Returns:
            元组(分类结果, 回复文本)

        Raises:
            ValueError: 当输入文本为空时抛出
            sqlite3.Error: 数据库操作失败时抛出
        """
        logger.info(f"开始分析投诉: {text[:50]}...")
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
                complaint_time DATETIME NOT NULL,
                content TEXT NOT NULL,
                user_id TEXT NOT NULL,
                complaint_category TEXT NOT NULL,
                reply TEXT
            )
        """
        )
        self.conn.commit()

    def create_complaint(self, text: str, category: str, reply: str) -> int:
        """创建新的投诉记录

        Args:
            text: 投诉内容文本
            category: 投诉分类
            reply: 自动生成的回复

        Returns:
            新创建的投诉记录ID

        Raises:
            sqlite3.Error: 数据库操作失败时抛出
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                INSERT INTO complaints (content, complaint_category, reply, complaint_time, user_id)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP, 'anonymous')
            """,
                (text, category, reply),
            )
            self.conn.commit()
            return cursor.lastrowid
        except sqlite3.Error as e:
            self.conn.rollback()
            raise sqlite3.Error(f"创建投诉记录失败: {e}")

    def get_complaint(self, complaint_id: int) -> dict | None:
        """获取单个投诉记录

        Args:
            complaint_id: 要查询的投诉ID

        Returns:
            包含投诉信息的字典，如果不存在则返回None

        Raises:
            sqlite3.Error: 数据库操作失败时抛出
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                SELECT id, content, complaint_category, reply, complaint_time
                FROM complaints WHERE id = ?
            """,
                (complaint_id,),
            )
            row = cursor.fetchone()
            return (
                {
                    "id": row[0],
                    "content": row[1],
                    "complaint_category": row[2],
                    "reply": row[3],
                    "complaint_time": row[4],
                }
                if row
                else None
            )
        except sqlite3.Error as e:
            raise sqlite3.Error(f"查询投诉记录失败: {e}")

    def update_complaint(
        self,
        complaint_id: int,
        content: str | None = None,
        complaint_category: str | None = None,
        reply: str | None = None,
    ) -> bool:
        """更新投诉记录

        Args:
            complaint_id: 要更新的投诉ID
            content: 新的投诉内容(可选)
            complaint_category: 新的投诉分类(可选)
            reply: 新的回复内容(可选)

        Returns:
            是否成功更新记录

        Raises:
            sqlite3.Error: 数据库操作失败时抛出
            ValueError: 当没有提供任何更新字段时抛出
        """
        if not any([content, complaint_category, reply]):
            raise ValueError("至少需要提供一个更新字段")

        try:
            updates = []
            params = []
            if content is not None:
                updates.append("content = ?")
                params.append(content)
            if complaint_category is not None:
                updates.append("complaint_category = ?")
                params.append(complaint_category)
            if reply is not None:
                updates.append("reply = ?")
                params.append(reply)

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
        except sqlite3.Error as e:
            self.conn.rollback()
            raise sqlite3.Error(f"更新投诉记录失败: {e}")

    def delete_complaint(self, complaint_id: int) -> bool:
        """删除投诉记录

        Args:
            complaint_id: 要删除的投诉ID

        Returns:
            是否成功删除记录

        Raises:
            sqlite3.Error: 数据库操作失败时抛出
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM complaints WHERE id = ?", (complaint_id,))
            self.conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error as e:
            self.conn.rollback()
            raise sqlite3.Error(f"删除投诉记录失败: {e}")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            self.conn.close()
            self.conn = None
