"""Tests unitaires — sentiment."""

import pandas as pd

from liora.ml.sentiment import build_training_frame, clean_text, rating_to_sentiment, train_sentiment_model


def test_clean_text():
    assert "bonjour" in clean_text("Bonjour!!! https://x.com")


def test_rating_mapping():
    assert rating_to_sentiment(1) == "negatif"
    assert rating_to_sentiment(5) == "positif"


def test_train_minimal():
    df = pd.DataFrame(
        {
            "text": ["super produit rapide"] * 5 + ["horrible retard colis"] * 5,
            "rating": [5, 5, 4, 5, 4, 1, 1, 2, 1, 2],
        }
    )
    frame = build_training_frame(df)
    assert len(frame) >= 8
    model, metrics, _ = train_sentiment_model(df)
    assert metrics["f1_macro"] >= 0
    assert model is not None
