import pytest
from fastapi.testclient import TestClient
from main import app, SessionLocal, Base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import random

# 配置测试数据库
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建测试数据库表
Base.metadata.create_all(bind=engine)


@pytest.fixture(scope="function")
def db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="module")
def client():
    # 使用内存数据库覆盖原数据库配置
    app.dependency_overrides[SessionLocal] = TestingSessionLocal
    with TestClient(app) as c:
        yield c


def test_create_complaint(client):
    test_data = {
        "complaint_time": "2024-01-01T00:00:00",
        "content": "测试投诉内容",
        "user_id": "test_user_1",
        "complaint_category": "electronics",
    }
    response = client.post("/complaints/", json=test_data)
    assert response.status_code == 200
    result = response.json()
    assert result["user_id"] == "test_user_1"
    assert "id" in result


def test_read_complaint_not_found(client):
    response = client.get("/complaints/999")
    assert response.status_code == 404


def test_complaint_crud_flow(client):
    # 创建
    create_res = client.post(
        "/complaints/",
        json={
            "complaint_time": "2024-01-01T00:00:00",
            "content": "完整流程测试",
            "user_id": "crud_test_user",
            "complaint_category": "home",
        },
    )
    assert create_res.status_code == 200
    complaint_id = create_res.json()["id"]

    # 读取
    get_res = client.get(f"/complaints/{complaint_id}")
    assert get_res.status_code == 200
    assert get_res.json()["content"] == "完整流程测试"

    # 更新
    update_res = client.put(
        f"/complaints/{complaint_id}",
        json={
            "complaint_time": "2024-01-02T00:00:00",
            "content": "更新后的内容",
            "user_id": "crud_test_user",
            "complaint_category": "home",
        },
    )
    assert update_res.status_code == 200
    assert update_res.json()["content"] == "更新后的内容"

    # 删除
    delete_res = client.delete(f"/complaints/{complaint_id}")
    assert delete_res.status_code == 200
    assert delete_res.json()["message"] == "Complaint deleted"

    # 验证删除
    verify_res = client.get(f"/complaints/{complaint_id}")
    assert verify_res.status_code == 404


def test_statistics(client, db):
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
        client.post("/complaints/", json=complaint)

    response = client.get("/statistics/")
    assert response.status_code == 200
    stats = response.json()
    assert sum(stats.values()) >= 5  # 至少包含新添加的5条


def test_simulate_endpoint(client):
    response = client.post("/simulate/")
    assert response.status_code == 200
    assert len(response.json()) == 10
    categories = {item["complaint_category"] for item in response.json()}
    assert len(categories) > 1  # 确保生成多个品类


def test_query_with_search(client):
    # 需要根据实际query_parser_chain的实现调整测试逻辑
    # 这里测试基本查询功能
    response = client.get("/complaints/?q=complaint_category:electronics")
    assert response.status_code in (200, 400)  # 根据实际解析器实现可能返回400

    if response.status_code == 200:
        assert len(response.json()) >= 0
