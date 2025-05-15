import configparser
import re
import sqlite3

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from litellm import completion
from pydantic import BaseModel

from database import DatabaseManager

# ## for debug
from litellm import litellm

# litellm._turn_on_debug()
# ##

config = configparser.ConfigParser()
config.read("settings.ini")

configs = {}
for section in config.sections():
    configs[section] = {}
    for key, value in config.items(section):
        configs[section][key] = value


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


# 全局变量存储对话历史
conversation_history = [
    {
        "role": "system",
        "content": "You are an expert in SQLite. Convert the following natural language description into a valid SQLite query. Return only the SQLite query, nothing else.",
    }
]


def create_llm_chain(model_name, api_base=None, api_key=None, stream=False):
    def llm_chain_func(question):
        global conversation_history

        # 添加用户新问题到对话历史
        conversation_history.append({"role": "user", "content": question})

        response = completion(
            model=model_name,
            api_base=api_base,
            api_key=api_key,
            stream=stream,
            messages=conversation_history,
        )

        if stream:
            # 处理流式响应
            full_response = ""
            for chunk in response:
                if chunk.choices[0].delta.content:
                    full_response += chunk.choices[0].delta.content

            # 添加AI响应到对话历史
            conversation_history.append({"role": "assistant", "content": full_response})
            return full_response
        else:
            # 处理普通响应
            ai_response = response.choices[0].message.content

            # 添加AI响应到对话历史
            conversation_history.append({"role": "assistant", "content": ai_response})
            return ai_response

    return llm_chain_func


if configs["openrouter"]["enabled"].upper() == "TRUE":
    llm_chain = create_llm_chain(
        model_name=f"openrouter/{configs['openrouter']['model_name']}",
        api_key=configs["openrouter"]["api_key"],
        # stream=True,
    )

if configs["ollama"]["enabled"].upper() == "TRUE":
    llm_chain = create_llm_chain(
        model_name=f"ollama/{configs['ollama']['model_name']}",
        api_base=configs["ollama"]["base_url"],
    )

if configs["openai"]["enabled"].upper() == "TRUE":
    llm_chain = create_llm_chain(
        model_name=f"openai/{configs['openai']['model_name']}",
        api_base=configs["openai"]["base_url"],
        api_key=configs["openai"]["api_key"],
    )


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


@app.post("/reset/")
async def reset_conversation():
    global conversation_history
    conversation_history = [
        {
            "role": "system",
            "content": "You are an expert in SQLite. Convert the following natural language description into a valid SQLite query. Return only the SQLite query, nothing else.",
        }
    ]
    return {"status": "success"}


@app.post("/query/")
async def query_llm(query: Query):
    if not llm_chain:
        raise HTTPException(status_code=501)
    try:
        response = llm_chain(query.question)
        print(response)

        # 首选方案，尝试提取返回结果中的SQL
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
        conn = get_db_connection()
        result = conn.execute(sql_query).fetchall()
        conn.close()

        # 转换为字典列表
        complaints = []
        for row in result:
            complaints.append(
                {
                    "id": row[0],
                    "title": row[1],
                    "content": row[2],
                    "date": row[3],
                    "category": row[4],
                    "source": row[5],
                }
            )

        return {"response": response, "complaints": complaints}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


def get_db_connection():
    conn = sqlite3.connect("complaint.db")
    conn.row_factory = sqlite3.Row
    return conn


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
