"""
Train a page classifier to detect balance_sheet / income_statement / cash_flow / other pages.

Uses TF-IDF + LogisticRegression (scikit-learn).
Saves trained model to backend/ml/models/page_classifier.joblib

Usage:
    python -m ml.train_classifier
"""
import os
import json
import logging
from pathlib import Path

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import classification_report, confusion_matrix
import numpy as np

logger = logging.getLogger("finscope.ml")

LABELS_FILE = Path(__file__).parent / "training_data.json"
MODEL_DIR = Path(__file__).parent / "models"
MODEL_PATH = MODEL_DIR / "page_classifier.joblib"
VECTORIZER_PATH = MODEL_DIR / "tfidf_vectorizer.joblib"


def load_training_data() -> tuple[list[str], list[str]]:
    """Load labeled training data.
    
    Expected format: [{"text": "page text...", "label": "balance_sheet"}, ...]
    """
    if not LABELS_FILE.exists():
        logger.warning("No training data found at %s", LABELS_FILE)
        # Generate synthetic training data from keyword patterns
        return _generate_synthetic_data()
    
    with open(LABELS_FILE) as f:
        data = json.load(f)
    
    texts = [d["text"] for d in data]
    labels = [d["label"] for d in data]
    return texts, labels


def _generate_synthetic_data() -> tuple[list[str], list[str]]:
    """Generate synthetic training data from known keyword patterns."""
    from statement_classifier import STATEMENT_KEYWORDS
    
    texts = []
    labels = []
    
    # Balance sheet variants
    bs_templates = [
        "CONSOLIDATED BALANCE SHEETS\n(In millions)\nAssets\nCurrent assets:\nCash and cash equivalents\nTotal current assets {}\nTotal assets {}\nLiabilities\nTotal current liabilities {}\nTotal liabilities {}\nStockholders' equity\nTotal stockholders' equity {}",
        "BALANCE SHEET\nStatement of Financial Position\nTotal Assets {}\nTotal Liabilities {}\nTotal Equity {}",
        "CONSOLIDATED STATEMENTS OF FINANCIAL POSITION\nAssets\nCurrent Assets\nTotal current assets\nTotal assets\nLiabilities and Stockholders Equity\nCurrent liabilities\nTotal current liabilities\nTotal liabilities\nTotal stockholders equity",
    ]
    
    # Income statement variants
    is_templates = [
        "CONSOLIDATED INCOME STATEMENTS\n(In millions)\nRevenue:\nTotal revenue {}\nCost of revenue {}\nGross margin\nOperating income {}\nNet income {}",
        "CONSOLIDATED STATEMENTS OF INCOME\nNet sales\nCost of sales\nGross profit\nOperating income\nIncome before taxes\nNet income",
        "STATEMENT OF PROFIT AND LOSS\nTotal Revenue\nCost of Goods Sold\nOperating Profit\nNet Profit",
    ]
    
    # Cash flow variants
    cf_templates = [
        "CONSOLIDATED STATEMENTS OF CASH FLOWS\nCash flows from operating activities:\nNet income\nDepreciation\nNet cash from operating activities\nCash flows from investing activities:\nNet cash from investing activities\nCash flows from financing activities:\nNet cash from financing activities",
        "CASH FLOW STATEMENT\nOperating Activities\nInvesting Activities\nFinancing Activities\nNet change in cash",
    ]
    
    # Other page variants
    other_templates = [
        "NOTES TO CONSOLIDATED FINANCIAL STATEMENTS\nNote 1: Summary of Significant Accounting Policies\nThe Company uses the accrual method of accounting...",
        "MANAGEMENT'S DISCUSSION AND ANALYSIS OF FINANCIAL CONDITION AND RESULTS OF OPERATIONS\nOverview\nThe following discussion should be read...",
        "RISK FACTORS\nThe following risk factors could materially affect our business...",
        "PROPERTIES\nOur corporate headquarters is located at...",
        "Table of Contents\nPart I\nItem 1. Business\nItem 1A. Risk Factors",
    ]
    
    import random
    random.seed(42)
    
    for template in bs_templates:
        for _ in range(20):
            nums = [random.randint(10000, 999999) for _ in range(5)]
            text = template.format(*nums) if "{}" in template else template
            texts.append(text)
            labels.append("balance_sheet")
    
    for template in is_templates:
        for _ in range(20):
            nums = [random.randint(10000, 999999) for _ in range(4)]
            text = template.format(*nums) if "{}" in template else template
            texts.append(text)
            labels.append("income_statement")
    
    for template in cf_templates:
        for _ in range(20):
            texts.append(template)
            labels.append("cash_flow")
    
    for template in other_templates:
        for _ in range(15):
            texts.append(template)
            labels.append("other")
    
    logger.info("Generated %d synthetic training samples", len(texts))
    return texts, labels


def train():
    """Train the page classifier and save it."""
    texts, labels = load_training_data()
    
    if len(texts) < 10:
        logger.error("Not enough training data (%d samples)", len(texts))
        return
    
    logger.info("Training on %d samples across %d classes", len(texts), len(set(labels)))
    
    # TF-IDF vectorization
    vectorizer = TfidfVectorizer(
        max_features=5000,
        ngram_range=(1, 2),
        stop_words="english",
        sublinear_tf=True,
    )
    
    X = vectorizer.fit_transform(texts)
    y = np.array(labels)
    
    # Train LogisticRegression
    clf = LogisticRegression(
        max_iter=1000,
        multi_class="multinomial",
        class_weight="balanced",
        C=1.0,
    )
    
    # Cross-validation
    scores = cross_val_score(clf, X, y, cv=min(5, len(set(labels))), scoring="accuracy")
    logger.info("Cross-validation accuracy: %.3f ± %.3f", scores.mean(), scores.std())
    
    # Train on full data
    clf.fit(X, y)
    
    # Save model and vectorizer
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(clf, MODEL_PATH)
    joblib.dump(vectorizer, VECTORIZER_PATH)
    
    logger.info("Model saved to %s", MODEL_PATH)
    
    # Print classification report on training data
    y_pred = clf.predict(X)
    print("\n=== Classification Report (training set) ===")
    print(classification_report(y, y_pred))
    print("\n=== Confusion Matrix ===")
    print(confusion_matrix(y, y_pred))
    
    return {
        "cv_accuracy": float(scores.mean()),
        "cv_std": float(scores.std()),
        "n_samples": len(texts),
        "n_classes": len(set(labels)),
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    train()
