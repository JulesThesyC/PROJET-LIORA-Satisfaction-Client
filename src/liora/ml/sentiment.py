"""Modèle d'analyse de sentiment (français) — baseline TF-IDF + régression logistique."""

from __future__ import annotations

import re
from typing import Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, f1_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

LABEL_MAP = {1: "negatif", 2: "negatif", 3: "neutre", 4: "positif", 5: "positif"}


def rating_to_sentiment(rating: int) -> str:
    return LABEL_MAP.get(int(rating), "neutre")


def clean_text(text: str) -> str:
    if not isinstance(text, str):
        return ""
    text = text.lower()
    text = re.sub(r"http\S+", "", text)
    text = re.sub(r"[^a-zàâäéèêëïîôùûüç0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def build_training_frame(df: pd.DataFrame) -> pd.DataFrame:
    frame = df.copy()
    frame["text_clean"] = frame["text"].apply(clean_text)
    frame = frame[frame["text_clean"].str.len() > 10]
    frame["sentiment"] = frame["rating"].apply(rating_to_sentiment)
    return frame


def train_sentiment_model(
    df: pd.DataFrame,
) -> Tuple[Pipeline, dict, pd.DataFrame]:
    frame = build_training_frame(df)
    X = frame["text_clean"]
    y = frame["sentiment"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    pipeline = Pipeline(
        [
            ("tfidf", TfidfVectorizer(max_features=8000, ngram_range=(1, 2))),
            (
                "clf",
                LogisticRegression(max_iter=500, class_weight="balanced"),
            ),
        ]
    )
    pipeline.fit(X_train, y_train)
    y_pred = pipeline.predict(X_test)
    metrics = {
        "f1_macro": float(f1_score(y_test, y_pred, average="macro")),
        "report": classification_report(y_test, y_pred),
        "n_train": len(X_train),
        "n_test": len(X_test),
    }
    return pipeline, metrics, frame


def predict_sentiment(model: Pipeline, texts: list[str]) -> list[dict]:
    cleaned = [clean_text(t) for t in texts]
    labels = model.predict(cleaned)
    probas = model.predict_proba(cleaned)
    classes = list(model.named_steps["clf"].classes_)
    results = []
    for i, label in enumerate(labels):
        proba_dict = {c: float(probas[i][j]) for j, c in enumerate(classes)}
        results.append({"sentiment": label, "probabilities": proba_dict})
    return results


def save_model(model: Pipeline, path: str) -> None:
    joblib.dump(model, path)


def load_model(path: str) -> Pipeline:
    return joblib.load(path)
