import configparser
import os
import re
import sqlite3

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from litellm import completion
from pydantic import BaseModel

from database import DatabaseManager

config = configparser.ConfigParser()
config.read("settings.ini")

LLM_API_KEY = config.get("openrouter", "LLM_API_KEY")
LLM_MODEL_NAME = f"openrouter/{config.get('openrouter', 'LLM_MODEL_NAME')}"

app = FastAPI()
templates = Jinja2Templates(directory="templates")

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class Complaint(BaseModel):
    title: str
    content: str
    category: str


class Query(BaseModel):
    question: str


db = DatabaseManager()

llm_chain = None
if LLM_API_KEY:
    try:
        os.environ["OPENROUTER_API_KEY"] = LLM_API_KEY

        def llm_chain_func(question):
            response = completion(
                model=LLM_MODEL_NAME,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert in SQLite. Convert the following natural language description into a valid SQLite query.",
                    },
                    {
                        "role": "user",
                        "content": f"Description: {question}",
                    },
                ],
            )
            return response.choices[0].message.content

        llm_chain = llm_chain_func
    except Exception as e:
        llm_chain = None


@app.get("/")
async def serve_home(request: Request):
    return templates.TemplateResponse(
        "index.html", {"request": request, "llm_available": bool(llm_chain)}
    )


@app.post("/complaint/")
async def create_complaint(complaint: Complaint):
    complaint_id = db.add_complaint(
        complaint.title, complaint.content, complaint.category
    )
    return {"id": complaint_id}


@app.get("/complaint/")
async def get_complaint():
    complaints = db.get_all_complaints()
    return {"complaints": complaints}


@app.post("/query/")
async def query_llm(query: Query):
    if not llm_chain:
        raise HTTPException(status_code=501)
    try:
        response = llm_chain(query.question)

        # 先尝试提取代码块中的SQL
        sql_match = re.search(r"```sql\n(.*?)\n```", response, re.DOTALL)
        if sql_match:
            sql_query = sql_match.group(1).strip()
        else:
            # 后备方案：提取以select开头，分号结束的SQL
            sql_match = re.search(r"(select.*?;)", response, re.IGNORECASE | re.DOTALL)
            if sql_match:
                sql_query = sql_match.group(1).strip()

        # 安全检查：只允许SELECT查询
        # if not sql_query.lower().startswith("select"):
        #     raise HTTPException(status_code=400, detail="只允许执行SELECT查询")

        # 执行SQL查询
        # conn = get_db_connection()
        # result = conn.execute(sql_query).fetchall()
        # conn.close()

        # 转换为字典列表
        # complaints = []
        # for row in result:
        #     complaints.append(
        #         {
        #             "id": row[0],
        #             "title": row[1],
        #             "content": row[2],
        #             "date": row[3].isoformat() if row[3] else None,
        #             "category": row[4],
        #             "source": row[5],
        #         }
        #     )

        # return {"response": response, "complaints": complaints}

        return {"response": sql_query}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


def get_db_connection():
    conn = sqlite3.connect("complaint.db")
    conn.row_factory = sqlite3.Row
    return conn


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
