import pandas as pd
from sklearn.model_selection import train_test_split, GridSearchCV, StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report

df = pd.read_csv("data/email_training_data.csv")
X_train, X_test, y_train, y_test = train_test_split(
    df["text"], df["label"], test_size=0.2, stratify=df["label"], random_state=42
)

pipe = Pipeline([
    ("tfidf", TfidfVectorizer()),
    ("clf", LogisticRegression(max_iter=2000, random_state=42)),
])

grid = {
    "tfidf__max_features": [300, 600, 1000, None],
    "tfidf__ngram_range": [(1, 1), (1, 2)],
    "tfidf__stop_words": ["english", None],   # None keeps "due", "by", "before"
    "tfidf__min_df": [1, 2],
    "clf__C": [1, 3, 10, 30],
    "clf__class_weight": [None, "balanced"],
}

cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
search = GridSearchCV(pipe, grid, cv=cv, scoring="accuracy", n_jobs=-1, verbose=1)
search.fit(X_train, y_train)          # only the train split is used here

print("\nBest CV accuracy:", f"{search.best_score_:.2%}")
print("Best settings:")
for k, v in search.best_params_.items():
    print(f"  {k}: {v}")

print("\nTop 5 settings:")
res = pd.DataFrame(search.cv_results_).sort_values("rank_test_score").head(5)
print(res[["mean_test_score", "std_test_score", "params"]].to_string(index=False))

print("\nTest split (look at this ONCE):")
print(classification_report(y_test, search.predict(X_test)))