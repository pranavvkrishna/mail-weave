import joblib
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
model_path = os.path.join(current_dir, 'models', 'email_classifier_model.pkl')
vectorizer_path = os.path.join(current_dir, 'models', 'tfidf_vectorizer.pkl')

model = joblib.load(model_path)
vectorizer = joblib.load(vectorizer_path)


def classify_email(subject: str, snippet: str):
    text = f"{subject} {snippet}"

    text_tfidf = vectorizer.transform([text])
    category = model.predict(text_tfidf)[0]
    probabilities = model.predict_proba(text_tfidf)[0]
    confidence = float(max(probabilities))

    return category, confidence
