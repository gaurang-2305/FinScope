import tempfile
import os

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from pipeline import run_extraction_pipeline
from ratio_engine import calculate_ratios

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


class EchoRequest(BaseModel):
    name: str
    message: str


@app.post("/echo")
def echo(payload: EchoRequest):
    return payload


@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    return {"filename": file.filename, "content_type": file.content_type, "size": file.size}


@app.post("/api/analyze")
async def analyze(file: UploadFile = File(...)):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files allowed")

    contents = await file.read()
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(contents)
        tmp_path = tmp.name

    try:
        statement = run_extraction_pipeline(tmp_path)
        ratios = calculate_ratios(statement)
    finally:
        os.remove(tmp_path)

    return {"statement": statement.dict(), "ratios": ratios}