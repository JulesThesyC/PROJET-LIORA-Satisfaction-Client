"""
API FastAPI — analyse de sentiment & synthèse entreprises.
"""

from __future__ import annotations

import json
import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from pydantic import BaseModel, Field

from liora.config import PROCESSED_DIR, RAW_DIR
from liora.ml.drift import run_drift_report
from liora.ml.sentiment import load_model, predict_sentiment

logger = logging.getLogger(__name__)

REQUEST_COUNT = Counter("liora_api_requests_total", "Total API requests", ["endpoint", "method"])
REQUEST_LATENCY = Histogram("liora_api_request_duration_seconds", "Request latency", ["endpoint"])

MODEL_PATH = PROCESSED_DIR / "models" / "sentiment_model.joblib"
_model = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _model
    if MODEL_PATH.exists():
        _model = load_model(str(MODEL_PATH))
        logger.info("Modèle sentiment chargé.")
    else:
        logger.warning("Modèle absent — entraîner via ml/train.py")
    yield


app = FastAPI(
    title="LIORA — API Satisfaction Client",
    description="API de scoring sentiment et métriques Trustpilot",
    version="1.0.0",
    lifespan=lifespan,
)


class SentimentRequest(BaseModel):
    texts: list[str] = Field(..., min_length=1, max_length=50)


class SentimentResponse(BaseModel):
    results: list[dict[str, Any]]


class CompanySummary(BaseModel):
    company_key: str
    display_name: str
    trust_score: float | None
    total_reviews: int | None
    theme: str | None


@app.middleware("http")
async def metrics_middleware(request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    endpoint = request.url.path
    REQUEST_COUNT.labels(endpoint=endpoint, method=request.method).inc()
    REQUEST_LATENCY.labels(endpoint=endpoint).observe(time.perf_counter() - start)
    return response


@app.get("/health")
def health():
    return {
        "status": "ok",
        "model_loaded": _model is not None,
    }


@app.get("/metrics")
def metrics():
    return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/companies", response_model=list[CompanySummary])
def list_companies():
    path = RAW_DIR / "entreprises_trustpilot.csv"
    if not path.exists():
        raise HTTPException(404, "Données entreprises non disponibles. Lancer le scraper.")
    df = pd.read_csv(path)
    return [
        CompanySummary(
            company_key=row["company_key"],
            display_name=row["display_name"],
            trust_score=row.get("trust_score"),
            total_reviews=int(row.get("total_reviews") or 0),
            theme=row.get("theme"),
        )
        for _, row in df.iterrows()
    ]


@app.post("/predict/sentiment", response_model=SentimentResponse)
def predict_sentiment_endpoint(body: SentimentRequest):
    if _model is None:
        raise HTTPException(503, "Modèle non chargé. Exécuter src/liora/ml/train.py")
    results = predict_sentiment(_model, body.texts)
    return SentimentResponse(results=results)


@app.get("/reviews/stats/{company_key}")
def review_stats(company_key: str):
    path = RAW_DIR / "avis_trustpilot.csv"
    if not path.exists():
        raise HTTPException(404, "Fichier avis introuvable")
    df = pd.read_csv(path)
    subset = df[df["company_key"] == company_key]
    if subset.empty:
        raise HTTPException(404, f"Aucun avis pour {company_key}")
    return {
        "company_key": company_key,
        "count": len(subset),
        "avg_rating": round(subset["rating"].mean(), 2),
        "reply_rate_pct": round(subset["has_company_reply"].mean() * 100, 2),
        "rating_distribution": subset["rating"].value_counts().to_dict(),
    }


@app.post("/monitoring/drift")
def drift_check():
    try:
        report = run_drift_report()
        return report
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
