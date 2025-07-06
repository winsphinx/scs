import logging
import os
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, Generator, Optional

from dotenv import load_dotenv
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import Runnable, RunnablePassthrough
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field, SecretStr
from pydantic.functional_validators import AfterValidator
from typing_extensions import Annotated

from utils.logging import configure_logging

# 配置日志
configure_logging()
logger = logging.getLogger(__name__)

try:
    from utils.config import (
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


# Pydantic 模型定义
class ComplaintAnalysisResult(BaseModel):
    category: str = Field(..., description="投诉分类结果")
    reply: str = Field(..., description="生成的回复文本")
    complaint_id: Optional[int] = Field(None, description="投诉记录ID")


class ComplaintRecord(BaseModel):
    id: int
    content: str
    complaint_category: str
    reply: str
    complaint_time: datetime


def validate_non_empty_text(v: str) -> str:
    if not v or not isinstance(v, str):
        raise ValueError("文本内容不能为空")
    return v


NonEmptyString = Annotated[str, AfterValidator(validate_non_empty_text)]


class ComplaintAnalyzer:
    def __init__(self, db_path: Optional[str] = None):
        """初始化投诉分析器

        Args:
            db_path: 数据库文件路径，默认为./data/complaints.db
        """
        load_dotenv()
        self.mode = os.getenv("LLM_MODE", "online")
        logger.info(f"初始化 ComplaintAnalyzer, 模式: {self.mode}")

        self.api_key = os.getenv("API_KEY")
        self.base_url = os.getenv("BASE_URL")
        self.model_name = os.getenv("MODEL_NAME")
        self.db_path = db_path or "./data/complaints.db"
        self.product_patterns: Dict[str, re.Pattern] = PRODUCT_PATTERNS
        self.templates: Dict[str, str] = REPLY_TEMPLATES

        # 初始化LLM链
        self._init_chains()
        self._init_db()

    def __enter__(self):
        """支持上下文管理器协议"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出上下文时清理资源"""
        pass

    def _init_chains(self):
        """初始化LangChain处理链"""
        if self.mode != "mock" and self.api_key and self.model_name:
            self.llm = ChatOpenAI(
                model=self.model_name,
                api_key=SecretStr(self.api_key),
                base_url=self.base_url,
            )

            # 分类链
            self.classification_chain = (
                {"text": RunnablePassthrough()}
                | PromptTemplate.from_template(CLASSIFICATION_PROMPT)
                | self.llm
                | StrOutputParser()
            )

            # 回复生成链
            self.reply_chain = (
                {"text": RunnablePassthrough(), "category": RunnablePassthrough()}
                | PromptTemplate.from_template(REPLY_PROMPT)
                | self.llm
                | StrOutputParser()
            )

            # 查询解析链
            self.query_parser_chain = (
                {"query": RunnablePassthrough()}
                | PromptTemplate.from_template(QUERY_PARSER_PROMPT)
                | self.llm
                | StrOutputParser()
            )
        else:
            # Mock处理链
            self.classification_chain = self._mock_chain("未知")
            self.reply_chain = self._mock_chain(self.templates["未知"])
            self.query_parser_chain = self._mock_chain("")

    def _mock_chain(self, default_value: Any) -> Runnable:
        """创建模拟处理链"""
        from langchain_core.runnables import RunnableLambda

        def mock_invoke(input_data: Any) -> str:
            logger.debug(f"模拟处理输入: {input_data}")
            return default_value

        return RunnableLambda(mock_invoke)

    @contextmanager
    def db_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """数据库连接上下文管理器"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            yield conn
        except sqlite3.Error as e:
            logger.error(f"数据库连接错误: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def _init_db(self):
        """初始化数据库表结构"""
        with self.db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS complaints (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    complaint_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    content TEXT NOT NULL,
                    user_id TEXT NOT NULL DEFAULT 'anonymous',
                    complaint_category TEXT NOT NULL,
                    reply TEXT
                )
                """
            )
            conn.commit()
            logger.info("数据库初始化完成")

    def classify_complaint(self, text: NonEmptyString) -> str:
        """分类客户投诉文本，返回产品类别"""
        logger.debug(f"开始分类投诉文本: {text[:50]}...")

        if self.mode == "mock" or not self.classification_chain:
            return self._classify_with_regex(text)

        try:
            result = self.classification_chain.invoke(text)
            return result.strip()
        except Exception as e:
            logger.error(f"分类投诉时出错: {e}")
            return self._classify_with_regex(text)

    def _classify_with_regex(self, text: str) -> str:
        """使用正则表达式进行分类"""
        for category, pattern in self.product_patterns.items():
            if pattern.search(text):
                return category
        return "未知"

    def generate_reply(
        self, text: NonEmptyString, category: Optional[str] = None
    ) -> str:
        """根据投诉文本和分类生成回复"""
        if not category:
            category = self.classify_complaint(text)

        logger.debug(f"为类别'{category}'生成回复")

        if self.mode == "mock" or not self.reply_chain:
            return self.templates.get(category, self.templates["未知"])

        try:
            result = self.reply_chain.invoke({"text": text, "category": category})
            return result.strip()
        except Exception as e:
            logger.error(f"生成回复时出错: {e}")
            return self.templates.get(category, self.templates["未知"])

    def analyze(self, text: NonEmptyString) -> ComplaintAnalysisResult:
        """分析投诉文本，返回分类和回复"""
        logger.info(f"开始分析投诉: {text[:50]}...")
        category = self.classify_complaint(text)
        reply = self.generate_reply(text, category)
        return ComplaintAnalysisResult(
            category=category, reply=reply, complaint_id=None
        )

    def create_complaint(self, text: str, category: str, reply: str) -> int:
        """创建新的投诉记录并返回ID"""
        with self.db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO complaints (content, complaint_category, reply)
                VALUES (?, ?, ?)
                """,
                (text, category, reply),
            )
            conn.commit()
            last_id = cursor.lastrowid
            if last_id is None:
                raise ValueError("未能获取新创建的投诉ID")
            return last_id

    def get_complaint(self, complaint_id: int) -> Optional[ComplaintRecord]:
        """获取单个投诉记录"""
        with self.db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, content, complaint_category, reply, complaint_time
                FROM complaints WHERE id = ?
                """,
                (complaint_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None

            return ComplaintRecord(
                id=row[0],
                content=row[1],
                complaint_category=row[2],
                reply=row[3],
                complaint_time=datetime.strptime(row[4], "%Y-%m-%d %H:%M:%S"),
            )

    def update_complaint(
        self,
        complaint_id: int,
        content: Optional[str] = None,
        complaint_category: Optional[str] = None,
        reply: Optional[str] = None,
    ) -> bool:
        """更新投诉记录"""
        if not any([content, complaint_category, reply]):
            raise ValueError("至少需要提供一个更新字段")

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

        with self.db_connection() as conn:
            cursor = conn.cursor()
            set_clause = ", ".join(updates)
            query = f"""
                UPDATE complaints
                SET {set_clause}
                WHERE id = ?
            """
            cursor.execute(query, params)
            conn.commit()
            return cursor.rowcount > 0

    def delete_complaint(self, complaint_id: int) -> bool:
        """删除投诉记录"""
        with self.db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM complaints WHERE id = ?", (complaint_id,))
            conn.commit()
            return cursor.rowcount > 0
