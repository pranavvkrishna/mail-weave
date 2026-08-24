import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import confusion_matrix, ConfusionMatrixDisplay
import matplotlib.pyplot as plt
import joblib

# load data (same split as train.py)
print("Loading dataset...")
df = pd.read_csv('data/email_training_data.csv')

X = df['text']
y = df['label']

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

# load trained model + vectorizer
print("Loading trained model and vectorizer...")
model = joblib.load('models/email_classifier_model.pkl')
vectorizer = joblib.load('models/tfidf_vectorizer.pkl')

X_test_tfidf = vectorizer.transform(X_test)
y_pred = model.predict(X_test_tfidf)

# confusion matrix
print("\nGenerating confusion matrix...")
cm = confusion_matrix(y_test, y_pred, labels=model.classes_)
disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=model.classes_)

fig, ax = plt.subplots(figsize=(10, 8))
disp.plot(xticks_rotation=45, cmap='Blues', ax=ax)
plt.title("Email Classifier — Confusion Matrix")
plt.tight_layout()
plt.savefig('outputs/confusion_matrix.png')
print("Saved outputs/confusion_matrix.png")

# error analysis
print(f"\n{'='*60}")
print("MISCLASSIFIED EXAMPLES")
print(f"{'='*60}")

X_test_reset = X_test.reset_index(drop=True)
y_test_reset = y_test.reset_index(drop=True)

misclassified_count = 0
for i in range(len(y_test_reset)):
    actual = y_test_reset[i]
    predicted = y_pred[i]
    if actual != predicted:
        misclassified_count += 1
        print(f"\nText: \"{X_test_reset[i]}\"")
        print(f"  Actual:    {actual}")
        print(f"  Predicted: {predicted}")

print(f"\nTotal misclassified: {misclassified_count} out of {len(y_test_reset)}")

# top predictive words per category
print(f"\n{'='*60}")
print("TOP 10 PREDICTIVE WORDS/PHRASES PER CATEGORY")
print(f"{'='*60}")

feature_names = vectorizer.get_feature_names_out()

for i, category in enumerate(model.classes_):
    top_indices = model.coef_[i].argsort()[-10:][::-1]
    top_words = [feature_names[j] for j in top_indices]
    print(f"\n{category}:")
    print(f"  {', '.join(top_words)}")

print("\nEvaluation complete!")
