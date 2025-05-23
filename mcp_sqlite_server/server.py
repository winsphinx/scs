import os
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

import sqlite3
import pandas as pd
from mcp.server.session import ServerSession
from typing import Dict, Any, List, Optional
from pathlib import Path


class SQLiteMcpServer(ServerSession):
    def __init__(
        self,
        read_stream=None,
        write_stream=None,
        init_options=None,
        db_path: Optional[str] = None,
    ):
        super().__init__(read_stream, write_stream, init_options)
        if db_path:
            self.db_path = os.path.abspath(db_path)
        else:
            self.db_path = os.path.abspath(os.environ.get("DB_PATH"))
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        logger.info(f"Database path: {self.db_path}")
        self.conn = None

    def connect(self):
        """Connect to SQLite database"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            return True
        except sqlite3.Error as e:
            self.log_error(f"Database connection error: {str(e)}")
            return False

    def get_tables(self) -> List[str]:
        """Get list of all tables in database"""
        if not self.conn:
            if not self.connect():
                return []

        cursor = self.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        return [row[0] for row in cursor.fetchall()]

    def get_schema(self, table: str) -> Dict[str, Any]:
        """Get schema information for a table"""
        if not self.conn:
            if not self.connect():
                return {}

        cursor = self.conn.cursor()
        cursor.execute(f"PRAGMA table_info({table})")
        columns = []
        for row in cursor.fetchall():
            columns.append(
                {
                    "name": row[1],
                    "type": row[2],
                    "not_null": bool(row[3]),
                    "default_value": row[4],
                    "primary_key": bool(row[5]),
                }
            )

        cursor.execute(f"SELECT sql FROM sqlite_master WHERE name='{table}'")
        row = cursor.fetchone()
        create_stmt = row[0] if row else ""

        return {"table": table, "create_statement": create_stmt, "columns": columns}

    def query(self, sql: str, params=None) -> Dict[str, Any]:
        """Execute a read-only SQL query"""
        if not self.conn:
            if not self.connect():
                return {"error": "Database connection failed"}

        try:
            df = pd.read_sql_query(sql, self.conn, params=params)
            return {
                "data": df.to_dict(orient="records"),
                "columns": list(df.columns),
                "row_count": len(df),
            }
        except Exception as e:
            return {"error": str(e)}

    def update_data(self, sql: str, params=None) -> Dict[str, Any]:
        """Execute data modification query"""
        if not self.conn:
            if not self.connect():
                return {"error": "Database connection failed"}

        try:
            cursor = self.conn.cursor()
            cursor.execute(sql, params or ())
            self.conn.commit()
            return {"rows_affected": cursor.rowcount, "last_rowid": cursor.lastrowid}
        except Exception as e:
            self.conn.rollback()
            return {"error": str(e)}

    def analyze_table(self, table: str, analysis_type: str = "basic") -> Dict[str, Any]:
        """Analyze table data"""
        if not self.conn:
            if not self.connect():
                return {"error": "Database connection failed"}

        try:
            df = pd.read_sql_query(f"SELECT * FROM {table}", self.conn)

            result = {
                "table": table,
                "row_count": len(df),
                "column_count": len(df.columns),
                "null_counts": df.isnull().sum().to_dict(),
            }

            if analysis_type == "detailed":
                numeric_cols = df.select_dtypes(include=["number"]).columns
                for col in numeric_cols:
                    result[col] = {
                        "mean": df[col].mean(),
                        "std": df[col].std(),
                        "min": df[col].min(),
                        "max": df[col].max(),
                    }

            return result
        except Exception as e:
            return {"error": str(e)}

    def get_resources(self) -> Dict[str, str]:
        """Get available MCP resources"""
        tables = self.get_tables()
        resources = {
            "schema://tables": "List of all tables in database",
            "schema://{table}": "Schema information for specific table",
        }
        return resources

    def get_tools(self) -> Dict[str, str]:
        """Get available MCP tools"""
        return {
            "query": "Execute read-only SQL queries",
            "update_data": "Perform data modifications",
            "analyze_table": "Perform statistical analysis on table data",
        }

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            self.conn = None


if __name__ == "__main__":
    import sys
    import json

    server = SQLiteMcpServer()
    logger.info("MCP Server started (stdio mode)")

    # 简单的stdio服务器实现
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break

            try:
                request = json.loads(line)
                method = request.get("method")
                params = request.get("params", {})

                if method == "call_tool":
                    tool_name = params.get("name")
                    args = params.get("arguments", {})

                    # 显式处理每种工具调用
                    if tool_name == "query":
                        result = server.query(args.get("sql"), args.get("params"))
                        response = {
                            "jsonrpc": "2.0",
                            "result": {
                                "content": [
                                    {
                                        "text": result.get("data", []),
                                        "columns": result.get("columns", []),
                                    }
                                ]
                            },
                            "id": request.get("id"),
                        }
                    elif tool_name == "update_data":
                        result = server.update_data(args.get("sql"), args.get("params"))
                        response = {
                            "jsonrpc": "2.0",
                            "result": {
                                "content": [
                                    {
                                        "text": {
                                            "rows_affected": result.get(
                                                "rows_affected", 0
                                            ),
                                            "last_rowid": result.get("last_rowid", 0),
                                        }
                                    }
                                ]
                            },
                            "id": request.get("id"),
                        }
                    else:
                        response = {
                            "jsonrpc": "2.0",
                            "error": {
                                "code": -32601,
                                "message": f"Unknown tool: {tool_name}",
                            },
                            "id": request.get("id"),
                        }
                else:
                    response = {
                        "jsonrpc": "2.0",
                        "error": {"code": -32601, "message": "Method not found"},
                        "id": request.get("id"),
                    }

                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()

            except Exception as e:
                logger.error(f"Error handling request: {str(e)}")
                response = {
                    "jsonrpc": "2.0",
                    "error": {"code": -32603, "message": str(e)},
                    "id": request.get("id") if "request" in locals() else None,
                }
                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()

        except KeyboardInterrupt:
            break
        except Exception as e:
            logger.error(f"Server error: {str(e)}")
            continue

    server.close()
    logger.info("MCP Server stopped")
