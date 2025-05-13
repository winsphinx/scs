from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional
from database import DatabaseManager
import os
from dotenv import load_dotenv

load_dotenv()

# Load LLM configuration
LLM_API_URL = os.getenv("LLM_API_URL")
LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.7"))
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "1024"))

app = FastAPI()
templates = Jinja2Templates(directory="templates")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
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

# Initialize LLM if API key is available
llm_chain = None
if LLM_API_KEY:
    try:
        from langchain_core.prompts import PromptTemplate
        from langchain_core.runnables import RunnablePassthrough

        llm = OpenAI(
            temperature=LLM_TEMPERATURE,
            openai_api_key=LLM_API_KEY,
            model_name=LLM_MODEL_NAME,
            max_tokens=LLM_MAX_TOKENS,
        )
        prompt = PromptTemplate.from_template(
            "Answer the following question: {question}"
        )
        llm_chain = {"question": RunnablePassthrough()} | prompt | llm
    except ImportError as e:
        print(f"Warning: LLM dependencies not installed - {str(e)}")


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
        raise HTTPException(
            status_code=501, detail="LLM服务不可用。请在.env文件中设置LLM_API_KEY"
        )
    try:
        response = llm_chain.invoke(query.question)
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM查询失败: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
