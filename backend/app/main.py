from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from .ml.classifier import classify_email as ml_classify
from .ml.deadline_extractor import extract_deadline

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class EmailData(BaseModel):
    subject: str
    snippet: str

@app.get("/test")
def test_main():
    return {"message": "works!"}

@app.post("/classify")
def classify_email(data: EmailData):
    category, confidence = ml_classify(data.subject, data.snippet)
    deadline = extract_deadline(f"{data.subject} {data.snippet}")

    return {
        "category": category,
        "confidence": confidence,
        "deadline": deadline
    }