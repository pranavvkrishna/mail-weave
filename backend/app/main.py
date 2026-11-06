from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from .ml.classifier import classify_email as ml_classify
from .ml.deadline_extractor import extract_deadline, resolve_deadline

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
    snippet: str          # first ~250 chars: used by the classifier
    body: str = ""        # longer body (up to ~5000 chars): used only for deadlines
    date: str = ""        # when the email was sent: used to turn "Friday" into a real date

@app.get("/test")
def test_main():
    return {"message": "works!"}

@app.post("/classify")
def classify_email(data: EmailData):
    category, confidence = ml_classify(data.subject, data.snippet)

    # deadline search uses the longer body when we have it, else the short snippet
    text_for_deadline = data.body or data.snippet
    deadline = extract_deadline(f"{data.subject}. {text_for_deadline}")
    resolved = resolve_deadline(deadline, data.date)

    return {
        "category": category,
        "confidence": confidence,
        "deadline": resolved["display"] if resolved else deadline,
        "deadline_iso": resolved["iso"] if resolved else None,
        "deadline_text": deadline,
    }