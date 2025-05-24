import os
import shutil
import sqlite3
import unittest

from mcp_sqlite_server.server import SQLiteMcpServer


class TestSQLiteMcpServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # 使用固定数据库路径
        cls.db_path = os.path.abspath("data/complaints.db")
        cls.backup_path = cls.db_path + ".backup"

        # 备份原有数据库(如果存在)
        if os.path.exists(cls.db_path):
            shutil.copy2(cls.db_path, cls.backup_path)

        # 初始化测试数据
        os.makedirs(os.path.dirname(cls.db_path), exist_ok=True)
        conn = sqlite3.connect(cls.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE test_table (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                value REAL,
                is_active INTEGER DEFAULT 1
            )
        """
        )
        cursor.execute("INSERT INTO test_table (name, value) VALUES ('test1', 10.5)")
        cursor.execute("INSERT INTO test_table (name, value) VALUES ('test2', 20.0)")
        cursor.execute(
            "INSERT INTO test_table (name, value, is_active) VALUES ('test3', 30.5, 0)"
        )
        conn.commit()
        conn.close()

    @classmethod
    def tearDownClass(cls):
        # 恢复原有数据库
        if os.path.exists(cls.backup_path):
            shutil.move(cls.backup_path, cls.db_path)
        elif os.path.exists(cls.db_path):
            os.remove(cls.db_path)

    def setUp(self):
        self.server = SQLiteMcpServer(db_path=self.db_path)

    def tearDown(self):
        self.server.close()

    def test_connect(self):
        self.assertTrue(self.server.connect())
        self.assertIsNotNone(self.server.conn)

    def test_get_tables(self):
        tables = self.server.get_tables()
        self.assertIn("test_table", tables)

    def test_get_schema(self):
        schema = self.server.get_schema("test_table")
        self.assertEqual(schema["table"], "test_table")
        self.assertIn("CREATE TABLE test_table", schema["create_statement"])

        columns = {col["name"]: col for col in schema["columns"]}
        self.assertEqual(columns["id"]["type"], "INTEGER")
        self.assertTrue(columns["id"]["primary_key"])
        self.assertEqual(columns["name"]["type"], "TEXT")
        self.assertTrue(columns["name"]["not_null"])
        self.assertEqual(columns["value"]["type"], "REAL")
        self.assertEqual(columns["is_active"]["type"], "INTEGER")
        self.assertEqual(columns["is_active"]["default_value"], "1")

    def test_query(self):
        # 测试简单查询
        result = self.server.query("SELECT * FROM test_table")
        self.assertEqual(result["row_count"], 3)
        self.assertEqual(len(result["columns"]), 4)
        self.assertEqual(len(result["data"]), 3)

        # 测试带参数的查询
        result = self.server.query("SELECT * FROM test_table WHERE name = ?", ["test1"])
        self.assertEqual(result["row_count"], 1)
        self.assertEqual(result["data"][0]["name"], "test1")

        # 测试错误查询
        result = self.server.query("SELECT * FROM non_existent_table")
        self.assertIn("error", result)

    def test_update_data(self):
        # 测试插入数据
        result = self.server.update_data(
            "INSERT INTO test_table (name, value) VALUES (?, ?)", ["test4", 40.0]
        )
        self.assertEqual(result["rows_affected"], 1)
        self.assertGreater(result["last_rowid"], 0)

        # 测试更新数据
        result = self.server.update_data(
            "UPDATE test_table SET value = ? WHERE name = ?", [15.0, "test1"]
        )
        self.assertEqual(result["rows_affected"], 1)

        # 测试错误更新
        result = self.server.update_data("UPDATE non_existent_table SET value = 1")
        self.assertIn("error", result)

    def test_analyze_table(self):
        # 测试基础分析
        result = self.server.analyze_table("test_table")
        self.assertEqual(result["table"], "test_table")
        self.assertEqual(result["row_count"], 3)
        self.assertEqual(result["column_count"], 4)
        self.assertIn("value", result["null_counts"])

        # 测试详细分析
        result = self.server.analyze_table("test_table", "detailed")
        self.assertIn("value", result)
        self.assertAlmostEqual(result["value"]["mean"], 20.333, places=1)

        # 测试错误表名
        result = self.server.analyze_table("non_existent_table")
        self.assertIn("error", result)

    def test_get_resources(self):
        resources = self.server.get_resources()
        self.assertIn("schema://tables", resources)
        self.assertIn("schema://{table}", resources)

    def test_get_tools(self):
        tools = self.server.get_tools()
        self.assertIn("query", tools)
        self.assertIn("update_data", tools)
        self.assertIn("analyze_table", tools)


if __name__ == "__main__":
    unittest.main()
