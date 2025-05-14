import os
from litellm import completion
import uvicorn

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from database import DatabaseManager

load_dotenv()

# Load LLM configuration
LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME")

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

llm_chain = None
if LLM_API_KEY:
    try:
        os.environ["OPENROUTER_API_KEY"] = LLM_API_KEY

        def llm_chain_func(question):
            response = completion(
                model=LLM_MODEL_NAME,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {
                        "role": "user",
                        "content": f"Answer the following question: {question}",
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
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM查询失败: {str(e)}")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
