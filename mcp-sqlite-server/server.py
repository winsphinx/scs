import os
import sqlite3
import pandas as pd
from mcp.server.session import ServerSession
from typing import Dict, Any, List, Optional
from pathlib import Path


class SQLiteMcpServer(ServerSession):
    def __init__(self, read_stream=None, write_stream=None, init_options=None):
        super().__init__(read_stream, write_stream, init_options)
        self.db_path = os.getenv("DB_PATH", "database.sqlite")
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
        create_stmt = cursor.fetchone()[0]

        return {"table": table, "create_statement": create_stmt, "columns": columns}

    def query(self, sql: str) -> Dict[str, Any]:
        """Execute a read-only SQL query"""
        if not self.conn:
            if not self.connect():
                return {"error": "Database connection failed"}

        try:
            df = pd.read_sql_query(sql, self.conn)
            return {
                "data": df.to_dict(orient="records"),
                "columns": list(df.columns),
                "row_count": len(df),
            }
        except Exception as e:
            return {"error": str(e)}

    def update_data(self, sql: str) -> Dict[str, Any]:
        """Execute data modification query"""
        if not self.conn:
            if not self.connect():
                return {"error": "Database connection failed"}

        try:
            cursor = self.conn.cursor()
            cursor.execute(sql)
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


if __name__ == "__main__":
    server = SQLiteMcpServer()
    from mcp.server.stdio import stdio_server

    print("MCP Server started (stdio mode)")
    stdio_server(server)
