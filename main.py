import logging
import random
import os
import subprocess
import json
from datetime import datetime
from typing import Dict, List, Any

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from llm_service import ComplaintAnalyzer
from config import SIMULATION_CONFIG

app = FastAPI()

# 配置中间件和静态文件
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# MCP数据库服务配置
MCP_SERVER_PATH = "mcp_sqlite_server/server.py"
DB_PATH = os.path.abspath("data/complaints.db")

# 确保数据库目录存在
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)


class MCPClient:
    def __init__(self):
        env = os.environ.copy()
        env["DB_PATH"] = DB_PATH
        self.process = subprocess.Popen(
            ["python", MCP_SERVER_PATH],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            text=True,
            bufsize=1,
        )

    def call_tool(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        request = {
            "jsonrpc": "2.0",
            "method": "call_tool",
            "params": {"name": tool_name, "arguments": params},
            "id": 1,
        }
        try:
            request_str = json.dumps(request) + "\n"
            self.process.stdin.write(request_str)
            self.process.stdin.flush()

            # Read response line by line until we get a complete JSON
            response_lines = []
            while True:
                line = self.process.stdout.readline()
                if not line:
                    break
                response_lines.append(line)
                try:
                    return json.loads("".join(response_lines))
                except json.JSONDecodeError:
                    continue

            return {"error": "No valid JSON response received"}
        except Exception as e:
            return {"error": str(e)}


# 初始化MCP客户端
mcp_client = MCPClient()


def execute_mcp_query(sql: str, params=None):
    """通过MCP服务器执行查询"""
    result = mcp_client.call_tool("query", {"sql": sql, "params": params or []})
    if "error" in result:
        logger.error(f"MCP query error: {result['error']}")
        return {"error": result["error"]}

    # 解析MCP服务器返回的数据格式
    data = []
    if "content" in result and isinstance(result["content"], list):
        for item in result["content"]:
            if "text" in item and isinstance(item["text"], list):
                data.extend(item["text"])

    return {"data": data, "columns": list(data[0].keys()) if data else []}


def execute_mcp_update(sql: str, params=None):
    """通过MCP服务器执行更新"""
    # 序列化datetime参数
    processed_params = []
    if params:
        for param in params:
            if isinstance(param, datetime):
                processed_params.append(param.isoformat())
            else:
                processed_params.append(param)

    result = mcp_client.call_tool(
        "update_data", {"sql": sql, "params": processed_params or []}
    )

    if "error" in result:
        logger.error(f"MCP update error: {result['error']}")
        return {"error": result["error"]}

    # 解析MCP服务器返回的数据格式
    rows_affected = 0
    last_rowid = 0
    if "content" in result and isinstance(result["content"], list):
        for item in result["content"]:
            if "text" in item and isinstance(item["text"], dict):
                rows_affected = item["text"].get("rows_affected", 0)
                last_rowid = item["text"].get("last_rowid", 0)
                break

    return {"rows_affected": rows_affected, "last_rowid": last_rowid}


# 初始化数据库表
init_sql = """
CREATE TABLE IF NOT EXISTS complaints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    complaint_time DATETIME NOT NULL,
    content TEXT NOT NULL,
    user_id TEXT NOT NULL,
    complaint_category TEXT NOT NULL,
    reply TEXT
);
"""
result = execute_mcp_update(init_sql)
if "error" in result:
    logger.error(f"Failed to initialize database: {result['error']}")


@app.get("/")
async def read_index():
    return FileResponse("templates/index.html")


class ComplaintCreate(BaseModel):
    complaint_time: datetime
    content: str
    user_id: str
    complaint_category: str
    reply: str | None = None


class ComplaintResponse(ComplaintCreate):
    id: int
    complaint_time: datetime

    class Config:
        from_attributes = True


@app.post("/complaints/", response_model=ComplaintResponse)
def create_complaint(complaint: ComplaintCreate):
    columns = ["complaint_time", "content", "user_id", "complaint_category", "reply"]
    values = [getattr(complaint, col) for col in columns]
    sql = f"""
    INSERT INTO complaints ({','.join(columns)})
    VALUES ({','.join(['?']*len(values))})
    """
    result = execute_mcp_update(sql, values)
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
    return {**complaint.model_dump(), "id": result["last_rowid"]}


@app.get("/complaints/", response_model=List[ComplaintResponse])
def read_complaints(
    q: str = None,
    skip: int = 0,
    limit: int = 100,
    analyzer: ComplaintAnalyzer = Depends(lambda: ComplaintAnalyzer()),
):
    sql = "SELECT * FROM complaints"
    params = []

    if q:
        try:
            filter_condition = analyzer.query_parser_chain.invoke({"query": q}).content
            if filter_condition:
                logger.info(f"Parsed query condition: {filter_condition}")
                sql += f" WHERE {filter_condition}"
        except Exception as e:
            logger.error(f"Query parsing failed: {str(e)}")
            raise HTTPException(status_code=400, detail=f"查询解析失败: {str(e)}")

    sql += f" LIMIT {limit} OFFSET {skip}"
    result = execute_mcp_query(sql, params)
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
    return result["data"]


@app.get("/complaints/{complaint_id}", response_model=ComplaintCreate)
def read_complaint(complaint_id: int):
    sql = "SELECT * FROM complaints WHERE id = ?"
    result = execute_mcp_query(sql, [complaint_id])
    if not result["data"]:
        raise HTTPException(status_code=404, detail="Complaint not found")
    return result["data"][0]


@app.put("/complaints/{complaint_id}", response_model=ComplaintCreate)
def update_complaint(complaint_id: int, complaint: ComplaintCreate):
    updates = []
    params = []
    for key, value in complaint.model_dump().items():
        updates.append(f"{key} = ?")
        params.append(value)
    params.append(complaint_id)

    sql = f"UPDATE complaints SET {','.join(updates)} WHERE id = ?"
    result = execute_mcp_update(sql, params)
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
    if result["rows_affected"] == 0:
        raise HTTPException(status_code=404, detail="Complaint not found")
    return {**complaint.model_dump(), "id": complaint_id}


@app.delete("/complaints/{complaint_id}")
def delete_complaint(complaint_id: int):
    sql = "DELETE FROM complaints WHERE id = ?"
    result = execute_mcp_update(sql, [complaint_id])
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
    if result["rows_affected"] == 0:
        raise HTTPException(status_code=404, detail="Complaint not found")
    return {"message": "Complaint deleted"}


@app.get("/statistics/", response_model=Dict[str, int])
def get_statistics():
    sql = """
    SELECT complaint_category, COUNT(id) as count
    FROM complaints
    GROUP BY complaint_category
    ORDER BY count DESC
    """
    result = execute_mcp_query(sql)
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
    return {row["complaint_category"]: row["count"] for row in result["data"]}


@app.post("/simulate/", response_model=List[ComplaintCreate])
def simulate_data():
    config = SIMULATION_CONFIG
    complaints = []
    for _ in range(10):
        category = random.choice(config["categories"])
        problem = random.choice(config["problems"][category])
        content = f"我的{category}{problem}" if category != "未知" else problem
        user_id = f"user_{random.randint(1, 1000):04d}"
        reply = random.choice(config["replies"]) if random.random() > 0.7 else None

        sql = """
        INSERT INTO complaints
        (complaint_time, content, user_id, complaint_category, reply)
        VALUES (?, ?, ?, ?, ?)
        """
        params = [datetime.now(), content, user_id, category, reply]
        result = execute_mcp_update(sql, params)
        if "error" in result:
            logger.error(f"Failed to insert simulated complaint: {result['error']}")
        else:
            complaints.append(
                {
                    "complaint_time": params[0],
                    "content": params[1],
                    "user_id": params[2],
                    "complaint_category": params[3],
                    "reply": params[4],
                    "id": result["last_rowid"],
                }
            )
            logger.info(f"Generated simulated complaint: {content}")
    return complaints


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
