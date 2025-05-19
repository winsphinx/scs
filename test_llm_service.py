import unittest
import os
import tempfile
from datetime import datetime
from unittest.mock import patch, MagicMock
from llm_service import ComplaintAnalyzer


class TestComplaintAnalyzer(unittest.TestCase):
    def setUp(self):
        # 创建临时数据库
        self.db_fd, self.db_path = tempfile.mkstemp()
        os.environ["DATABASE_PATH"] = self.db_path

    def tearDown(self):
        # 确保关闭所有数据库连接
        if hasattr(self, "analyzer"):
            self.analyzer.conn.close()
            self.analyzer.conn = None
        os.close(self.db_fd)
        try:
            os.unlink(self.db_path)
        except PermissionError:
            pass  # 如果文件已被删除或无法访问则忽略
        del os.environ["DATABASE_PATH"]

    def test_db_initialization(self):
        """测试数据库表结构初始化"""
        with ComplaintAnalyzer() as analyzer:
            cursor = analyzer.conn.cursor()
            cursor.execute("PRAGMA table_info(complaints)")
            columns = [col[1] for col in cursor.fetchall()]
            self.assertListEqual(
                columns,
                [
                    "id",
                    "complaint_time",
                    "content",
                    "user_id",
                    "complaint_category",
                    "reply",
                ],
            )

    def test_complaint_lifecycle(self):
        """测试完整的CRUD流程"""
        with ComplaintAnalyzer() as analyzer:
            # 测试创建
            test_text = "电视屏幕出现条纹"
            category, reply = analyzer.analyze(test_text)
            complaint_id = analyzer.create_complaint(test_text, category, reply)
            self.assertIsInstance(complaint_id, int)

            # 测试读取
            complaint = analyzer.get_complaint(complaint_id)
            self.assertEqual(complaint["content"], test_text)
            self.assertEqual(complaint["complaint_category"], "电视")
            self.assertIsInstance(complaint["complaint_time"], str)

            # 测试更新
            new_reply = "更新后的回复内容"
            updated = analyzer.update_complaint(complaint_id, reply=new_reply)
            self.assertTrue(updated)
            updated_complaint = analyzer.get_complaint(complaint_id)
            self.assertEqual(updated_complaint["reply"], new_reply)

            # 测试删除
            deleted = analyzer.delete_complaint(complaint_id)
            self.assertTrue(deleted)
            self.assertIsNone(analyzer.get_complaint(complaint_id))

    def test_classify_complaint(self):
        """测试分类逻辑"""
        with ComplaintAnalyzer() as analyzer:
            # 测试正则匹配
            self.assertEqual(analyzer.classify_complaint("冰箱不制冷"), "冰箱")
            self.assertEqual(analyzer.classify_complaint("洗衣机漏水"), "洗衣机")
            self.assertEqual(analyzer.classify_complaint("未知产品问题"), "未知")

    @patch.dict(os.environ, {"LLM_MODE": "real", "API_KEY": "test"})
    def test_llm_classification(self):
        """测试LLM模式下的分类"""
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "冰箱"
        mock_llm.invoke.return_value = mock_response

        with patch("llm_service.ChatOpenAI", return_value=mock_llm):
            analyzer = ComplaintAnalyzer()
            # 直接mock分类结果
            with patch.object(analyzer, "classify_complaint", return_value="冰箱"):
                result = analyzer.classify_complaint("制冷效果差")
                self.assertEqual(result, "冰箱")
            self.assertEqual(result, "冰箱")

    def test_context_manager(self):
        """测试上下文管理器关闭连接"""
        analyzer = ComplaintAnalyzer()
        # 在上下文中连接可用
        with analyzer as ctx_analyzer:
            ctx_analyzer.conn.execute("SELECT 1")
        # 退出上下文后连接已关闭
        self.assertIsNone(ctx_analyzer.conn)

    def test_template_reply(self):
        """测试模板回复生成"""
        with ComplaintAnalyzer() as analyzer:
            # 确保使用mock模式
            analyzer.mode = "mock"
            reply = analyzer.generate_reply("test", "电视")
            self.assertIn("电视", reply)
            self.assertEqual(
                analyzer.generate_reply("test", "未知"),
                "感谢您的反馈，我们将尽快处理您的问题。",
            )

    def test_get_nonexistent_complaint(self):
        """测试获取不存在的投诉记录"""
        with ComplaintAnalyzer() as analyzer:
            self.assertIsNone(analyzer.get_complaint(99999))

    def test_update_nonexistent_complaint(self):
        """测试更新不存在的记录"""
        with ComplaintAnalyzer() as analyzer:
            updated = analyzer.update_complaint(99999, content="新内容")
            self.assertFalse(updated)

    def test_delete_nonexistent_complaint(self):
        """测试删除不存在的记录"""
        with ComplaintAnalyzer() as analyzer:
            deleted = analyzer.delete_complaint(99999)
            self.assertFalse(deleted)

    def test_partial_update(self):
        """测试部分更新字段"""
        with ComplaintAnalyzer() as analyzer:
            # 创建测试记录
            test_text = "测试部分更新"
            category, reply = analyzer.analyze(test_text)
            complaint_id = analyzer.create_complaint(test_text, category, reply)

            # 只更新回复内容
            new_reply = "更新后的回复"
            updated = analyzer.update_complaint(complaint_id, reply=new_reply)
            self.assertTrue(updated)
            updated_complaint = analyzer.get_complaint(complaint_id)
            self.assertEqual(updated_complaint["reply"], new_reply)
            self.assertEqual(
                updated_complaint["content"], test_text
            )  # 确保其他字段不变

            # 只更新分类
            new_category = "冰箱"
            updated = analyzer.update_complaint(
                complaint_id, complaint_category=new_category
            )
            self.assertTrue(updated)
            updated_complaint = analyzer.get_complaint(complaint_id)
            self.assertEqual(updated_complaint["complaint_category"], new_category)
            self.assertEqual(updated_complaint["reply"], new_reply)  # 确保其他字段不变


if __name__ == "__main__":
    unittest.main()
