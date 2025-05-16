import configparser
import re
import sqlite3
import logging

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from litellm import completion
from pydantic import BaseModel

from database import DatabaseManager

db = DatabaseManager()

## Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from litellm import litellm

litellm._turn_on_debug()
##

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


class Complaint(BaseModel):
    title: str
    content: str
    category: str


class Query(BaseModel):
    question: str


class LLMChain:
    def __init__(self, config: configparser.ConfigParser):
        self.reset()
        self.llm_chain = self.initialize_llm_chain(config)

    def reset(self):
        self.conversation = [
            {
                "role": "system",
                "content": DEFAULT_SYSTEM_PROMPT,
            }
        ]

    def initialize_llm_chain(self, config: configparser.ConfigParser):
        for provider_name in config.sections():
            if config.get(provider_name, "enabled", fallback="FALSE").upper() == "TRUE":
                model_name = f"{provider_name}/{config[provider_name]['model_name']}"
                chain_params = {"model_name": model_name}

                for param_key in config[provider_name]:
                    if param_key.lower() not in ["enabled", "model_name"]:
                        normalized_key = param_key.lower()
                        chain_params[normalized_key] = config[provider_name][param_key]

                return self.create_llm_chain(**chain_params)
        return None

    def create_llm_chain(self, model_name, api_base=None, api_key=None, stream=False):
        def llm_chain_func(question):
            self.conversation.append({"role": "user", "content": question})

            response = completion(
                model=model_name,
                api_base=api_base,
                api_key=api_key,
                stream=stream,
                messages=self.conversation,
            )

            response_content = ""
            if stream:
                for chunk in response:
                    if chunk.choices[0].delta.content:
                        response_content += chunk.choices[0].delta.content
            else:
                response_content = response.choices[0].message.content

            self.conversation.append({"role": "user", "content": response_content})

            return response_content

        return llm_chain_func


llm_chain_instance = LLMChain(config)


@app.get("/")
async def serve_home(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "llm_available": bool(llm_chain_instance.llm_chain)},
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
    llm_chain_instance.reset()
    return {"status": "success"}


@app.post("/query/")
async def query_llm(query: Query):
    if not llm_chain_instance.llm_chain:
        raise HTTPException(status_code=501)
    try:
        response = llm_chain_instance.llm_chain(query.question)
        logger.info(response)

        # 首选方案，尝试提取返回结果中的SQL
        sql_match = re.search(r"```sql\n(.*?)\n```", response, re.DOTALL)
        if sql_match:
            sql_query = sql_match.group(1).strip()
        else:
            # 后备方案：提取以select开头，分号结束的SQL
            sql_match = re.search(r"(select.*?;)", response, re.IGNORECASE | re.DOTALL)
            if sql_match:
                sql_query = sql_match.group(1).strip()
            else:
                raise HTTPException(
                    status_code=400, detail="无法从返回结果中提取有效的SQL查询语句"
                )
        logger.info(sql_query)

        # 安全检查：只允许SELECT查询
        if not sql_query.lower().startswith("select"):
            raise HTTPException(status_code=400, detail="只允许执行SELECT查询")

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
