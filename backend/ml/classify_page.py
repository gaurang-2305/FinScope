"""
Page classifier — loads the trained model and classifies PDF pages.
"""
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger("finscope.ml")

MODEL_DIR = Path(__file__).parent / "models"
MODEL_PATH = MODEL_DIR / "page_classifier.joblib"
VECTORIZER_PATH = MODEL_DIR / "tfidf_vectorizer.joblib"

_clf = None
_vectorizer = None


def _load_model():
    """Lazy-load the trained model and vectorizer."""
    global _clf, _vectorizer
    
    if _clf is not None:
        return True
    
    if not MODEL_PATH.exists() or not VECTORIZER_PATH.exists():
        logger.warning("ML classifier model not found — run `python -m ml.train_classifier` first")
        return False
    
    import joblib
    _clf = joblib.load(MODEL_PATH)
    _vectorizer = joblib.load(VECTORIZER_PATH)
    logger.info("ML page classifier loaded")
    return True


def classify_page(text: str) -> tuple[Optional[str], float]:
    """Classify a single page of text.
    
    Returns (label, confidence) where label is one of:
    'balance_sheet', 'income_statement', 'cash_flow', 'other'
    
    Returns (None, 0.0) if the model isn't available.
    """
    if not _load_model():
        return None, 0.0
    
    X = _vectorizer.transform([text])
    proba = _clf.predict_proba(X)[0]
    label_idx = proba.argmax()
    label = _clf.classes_[label_idx]
    confidence = float(proba[label_idx])
    
    return label, confidence


def classify_pages(pages_text: list[str]) -> list[tuple[str, float]]:
    """Classify all pages in a document.
    
    Returns list of (label, confidence) tuples, one per page.
    """
    if not _load_model():
        return [(None, 0.0)] * len(pages_text)
    
    X = _vectorizer.transform(pages_text)
    probas = _clf.predict_proba(X)
    labels = _clf.classes_
    
    results = []
    for proba in probas:
        label_idx = proba.argmax()
        results.append((labels[label_idx], float(proba[label_idx])))
    
    return results
