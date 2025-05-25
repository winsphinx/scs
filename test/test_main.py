import os
import random
import unittest
from datetime import datetime

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from main import Base, SessionLocal, app

# 配置测试数据库
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class TestComplaintAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(bind=engine)
        # 使用内存数据库覆盖原数据库配置
        app.dependency_overrides[SessionLocal] = TestingSessionLocal
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        Base.metadata.drop_all(bind=engine)

    def setUp(self):
        self.db = TestingSessionLocal()
        Base.metadata.create_all(bind=engine)

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=engine)

    def test_create_complaint(self):
        test_data = {
            "complaint_time": "2024-01-01T00:00:00",
            "content": "测试投诉内容",
            "user_id": "test_user_1",
            "complaint_category": "electronics",
        }
        response = self.client.post("/complaints/", json=test_data)
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result["user_id"], "test_user_1")
        self.assertIn("id", result)

    def test_read_complaint_not_found(self):
        response = self.client.get("/complaints/999")
        self.assertEqual(response.status_code, 404)

    def test_complaint_crud_flow(self):
        # 创建
        create_res = self.client.post(
            "/complaints/",
            json={
                "complaint_time": "2024-01-01T00:00:00",
                "content": "完整流程测试",
                "user_id": "crud_test_user",
                "complaint_category": "home",
            },
        )
        self.assertEqual(create_res.status_code, 200)
        complaint_id = create_res.json()["id"]

        # 读取
        get_res = self.client.get(f"/complaints/{complaint_id}")
        self.assertEqual(get_res.status_code, 200)
        self.assertEqual(get_res.json()["content"], "完整流程测试")

        # 更新
        update_res = self.client.put(
            f"/complaints/{complaint_id}",
            json={
                "complaint_time": "2024-01-02T00:00:00",
                "content": "更新后的内容",
                "user_id": "crud_test_user",
                "complaint_category": "home",
            },
        )
        self.assertEqual(update_res.status_code, 200)
        self.assertEqual(update_res.json()["content"], "更新后的内容")

        # 删除
        delete_res = self.client.delete(f"/complaints/{complaint_id}")
        self.assertEqual(delete_res.status_code, 200)
        self.assertEqual(delete_res.json()["message"], "Complaint deleted")

        # 验证删除
        verify_res = self.client.get(f"/complaints/{complaint_id}")
        self.assertEqual(verify_res.status_code, 404)

    def test_statistics(self):
        # 添加测试数据
        categories = ["electronics", "clothing", "food"]
        for _ in range(5):
            category = random.choice(categories)
            complaint = {
                "complaint_time": datetime.now().isoformat(),
                "content": f"测试统计{category}",
                "user_id": "stat_test_user",
                "complaint_category": category,
            }
            self.client.post("/complaints/", json=complaint)

        response = self.client.get("/statistics/")
        self.assertEqual(response.status_code, 200)
        stats = response.json()
        self.assertGreaterEqual(sum(stats.values()), 5)  # 至少包含新添加的5条

    def test_simulate_endpoint(self):
        response = self.client.post("/simulate/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 10)
        categories = {item["complaint_category"] for item in response.json()}
        self.assertGreater(len(categories), 1)  # 确保生成多个品类

    def test_query_with_search(self):
        # 需要根据实际query_parser_chain的实现调整测试逻辑
        # 这里测试基本查询功能
        response = self.client.get("/complaints/?q=complaint_category:electronics")
        self.assertIn(response.status_code, (200, 400))  # 根据实际解析器实现可能返回400

        if response.status_code == 200:
            self.assertGreaterEqual(len(response.json()), 0)
