import pandas as pd
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score, classification_report
import joblib

print("Loading dataset...")
df = pd.read_csv('data/email_training_data.csv')

print(f"Total samples: {len(df)}")
print(f"Categories: {df['label'].unique()}")
print(f"\nLabel distribution:")
print(df['label'].value_counts())

# split data
X = df['text']
y = df['label']

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

print(f"\nTraining samples: {len(X_train)}")
print(f"Testing samples: {len(X_test)}")


def make_vectorizer():
    return TfidfVectorizer(
        ngram_range=(1, 1),
        stop_words=None,
        min_df=1,
        max_features=None,
    )

def make_model():
    return LogisticRegression(C=10, max_iter=2000, random_state=42)


# vectorizer + model in ONE pipeline: whenever the pipeline is fit (including
# inside each cross-validation fold) the vectorizer only ever sees training text
pipeline = Pipeline([
    ("tfidf", make_vectorizer()),
    ("clf", make_model()),
])

print("\nFitting pipeline (TF-IDF + Logistic Regression) on the training split...")
pipeline.fit(X_train, y_train)
print(f"Training accuracy: {pipeline.score(X_train, y_train):.2%}")

# evaluate on test split
y_pred = pipeline.predict(X_test)
accuracy = accuracy_score(y_test, y_pred)

print(f"\n{'='*50}")
print(f"MODEL PERFORMANCE (single test split)")
print(f"{'='*50}")
print(f"Accuracy: {accuracy:.2%}")
print(f"\nDetailed Report:")
print(classification_report(y_test, y_pred, zero_division=0))

# cross validation: the pipeline is re-fit from scratch inside every fold,
# so the held-out fold never influences the vocabulary or IDF weights (no leakage)
print(f"\n{'='*50}")
print(f"CROSS-VALIDATION (5-fold, leak-free: vectorizer fit inside each fold)")
print(f"{'='*50}")
cv_scores = cross_val_score(pipeline, X_train, y_train, cv=5)
print(f"CV Accuracy: {cv_scores.mean():.2%} (+/- {cv_scores.std():.2%})")

# for comparison only: the OLD way (vectorizer fit on all training text first),
# so you can see how much the leak inflated the score
leaky_vectorizer = make_vectorizer()
X_train_tfidf_leaky = leaky_vectorizer.fit_transform(X_train)
leaky_scores = cross_val_score(make_model(), X_train_tfidf_leaky, y_train, cv=5)
print(f"\nFor comparison, old (leaky) CV accuracy: {leaky_scores.mean():.2%} "
      f"(+/- {leaky_scores.std():.2%})")
print(f"Difference caused by the leak: {(leaky_scores.mean() - cv_scores.mean()) * 100:+.2f} points")

# save model and vectorizer separately (same files as before, so classifier.py
# and evaluate.py keep working without any changes)
print("\nSaving model and vectorizer...")
joblib.dump(pipeline.named_steps["clf"], 'models/email_classifier_model.pkl')
joblib.dump(pipeline.named_steps["tfidf"], 'models/tfidf_vectorizer.pkl')

print("Model saved successfully!")
print("   - email_classifier_model.pkl")
print("   - tfidf_vectorizer.pkl")