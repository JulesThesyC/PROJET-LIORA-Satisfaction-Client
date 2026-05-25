"""Entraînement du modèle de sentiment avec versioning MLflow."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from liora.config import MLFLOW_TRACKING_URI, PROCESSED_DIR, RAW_DIR
from liora.ml.sentiment import save_model, train_sentiment_model

logger = logging.getLogger(__name__)
MODEL_DIR = PROCESSED_DIR / "models"
MODEL_PATH = MODEL_DIR / "sentiment_model.joblib"


def _log_mlflow(model, metrics: dict, df: pd.DataFrame, experiment_name: str) -> str:
    try:
        import mlflow
        import mlflow.sklearn
    except ImportError as exc:
        raise RuntimeError(f"MLflow non installé: {exc}") from exc

    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow.set_experiment(experiment_name)
    with mlflow.start_run(run_name="tfidf_logreg_v1") as run:
        mlflow.log_param("model_type", "TfidfVectorizer+LogisticRegression")
        mlflow.log_param("n_samples", len(df))
        mlflow.log_metric("f1_macro", metrics["f1_macro"])
        mlflow.log_text(metrics["report"], "classification_report.txt")
        mlflow.sklearn.log_model(model, "sentiment_model")
        mlflow.log_artifact(str(MODEL_PATH))
        return run.info.run_id


def train_and_log(experiment_name: str = "liora_sentiment") -> str:
    csv_path = RAW_DIR / "avis_trustpilot.csv"
    if not csv_path.exists():
        raise FileNotFoundError(
            f"Lancer d'abord le scraper : {csv_path} introuvable."
        )

    df = pd.read_csv(csv_path)
    model, metrics, _ = train_sentiment_model(df)
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    save_model(model, str(MODEL_PATH))
    logger.info("Modèle sauvegardé : %s (f1=%.3f)", MODEL_PATH, metrics["f1_macro"])

    try:
        run_id = _log_mlflow(model, metrics, df, experiment_name)
        logger.info("MLflow run_id=%s", run_id)
        return run_id
    except Exception as exc:
        logger.warning("MLflow indisponible (%s) — modèle local uniquement.", exc)
        return "local-only"


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    train_and_log()
