from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

@app.get("/health")
def health():
    return {"status": "ok"}


class EchoRequest(BaseModel):
    name: str
    message: str


@app.post("/echo")
def echo(payload: EchoRequest):
    return payload