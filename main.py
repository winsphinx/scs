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

litellm._turn_on_debug()
# ##


class Complaint(BaseModel):
    title: str
    content: str
    category: str


class Query(BaseModel):
    question: str


DEFAULT_SYSTEM_PROMPT = "You are an expert in SQLite. Convert the following natural language description into a valid SQLite query. Return only the SQLite query, nothing else."

config = configparser.ConfigParser()
config.read("settings.ini")

templates = Jinja2Templates(directory="templates")

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

db = DatabaseManager()

llm_chain = None

# 全局变量存储对话历史
conversation = [
    {
        "role": "system",
        "content": DEFAULT_SYSTEM_PROMPT,
    }
]


def create_llm_chain(model_name, api_base=None, api_key=None, stream=False):
    def llm_chain_func(question):
        global conversation

        # 添加用户新问题到对话历史
        conversation.append({"role": "user", "content": question})

        response = completion(
            model=model_name,
            api_base=api_base,
            api_key=api_key,
            stream=stream,
            messages=conversation,
        )

        ai_response_content = ""
        if stream:
            # 处理流式响应
            for chunk in response:
                if chunk.choices[0].delta.content:
                    ai_response_content += chunk.choices[0].delta.content
        else:
            # 处理普通响应
            ai_response_content = response.choices[0].message.content

        # 添加AI响应到对话历史
        conversation.append({"role": "assistant", "content": ai_response_content})
        return ai_response_content

    return llm_chain_func


def initialize_llm_chain(config: configparser.ConfigParser):
    # 自动从配置文件中获取所有provider
    for provider_name in config.sections():

        if config.get(provider_name, "enabled", fallback="FALSE").upper() == "TRUE":
            model_name = f"{provider_name}/{config[provider_name]['model_name']}"
            chain_params = {"model_name": model_name}

            # 自动收集provider的所有参数
            for param_key in config[provider_name]:
                if param_key.lower() not in ["enabled", "model_name"]:
                    # 处理参数名标准化
                    normalized_key = param_key.lower()
                    chain_params[normalized_key] = config[provider_name][param_key]

            return create_llm_chain(**chain_params)

    return None


llm_chain = initialize_llm_chain(config)


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
    global conversation
    conversation = [
        {
            "role": "system",
            "content": DEFAULT_SYSTEM_PROMPT,
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
        complaints = [dict(row) for row in result]

        return {"response": response, "complaints": complaints}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


def get_db_connection():
    conn = sqlite3.connect("complaint.db")
    conn.row_factory = sqlite3.Row
    return conn


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
