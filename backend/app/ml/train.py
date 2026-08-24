import pandas as pd
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
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

# improved TF-IDF: n-grams + stopwords + min_df
print("\nCreating TF-IDF features (with n-grams + stopwords)...")
vectorizer = TfidfVectorizer(
    max_features=300,
    ngram_range=(1, 2),
    stop_words='english',
    min_df=2
)
X_train_tfidf = vectorizer.fit_transform(X_train)
X_test_tfidf = vectorizer.transform(X_test)

# train model (still Logistic Regression)
print("Training Logistic Regression model...")
model = LogisticRegression(max_iter=1000, random_state=42)
model.fit(X_train_tfidf, y_train)

# evaluate on test split
y_pred = model.predict(X_test_tfidf)
accuracy = accuracy_score(y_test, y_pred)

print(f"\n{'='*50}")
print(f"MODEL PERFORMANCE (single test split)")
print(f"{'='*50}")
print(f"Accuracy: {accuracy:.2%}")
print(f"\nDetailed Report:")
print(classification_report(y_test, y_pred, zero_division=0))

# cross validation for a more reliable accuracy estimate
print(f"\n{'='*50}")
print(f"CROSS-VALIDATION (5-fold, more reliable estimate)")
print(f"{'='*50}")
cv_scores = cross_val_score(model, X_train_tfidf, y_train, cv=5)
print(f"CV Accuracy: {cv_scores.mean():.2%} (+/- {cv_scores.std():.2%})")

# save model and vectorizer
print("\nSaving model and vectorizer...")
joblib.dump(model, 'models/email_classifier_model.pkl')
joblib.dump(vectorizer, 'models/tfidf_vectorizer.pkl')

print("Model saved successfully!")
print("   - email_classifier_model.pkl")
print("   - tfidf_vectorizer.pkl")