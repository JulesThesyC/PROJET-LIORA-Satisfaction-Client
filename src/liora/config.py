"""Configuration centralisée du projet."""

from __future__ import annotations

import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

load_dotenv()

ROOT_DIR = Path(__file__).resolve().parents[2]
CONFIG_DIR = ROOT_DIR / "config"
DATA_DIR = Path(os.getenv("DATA_DIR", ROOT_DIR / "data"))
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"

MAX_REVIEWS_PER_COMPANY = int(os.getenv("MAX_REVIEWS_PER_COMPANY", "200"))
MAX_REVIEW_PAGES = int(os.getenv("MAX_REVIEW_PAGES", "20"))
SCRAPER_HEADLESS = os.getenv("SCRAPER_HEADLESS", "true").lower() == "true"

POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_DB = os.getenv("POSTGRES_DB", "liora_satisfaction")
POSTGRES_USER = os.getenv("POSTGRES_USER", "liora")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "liora_secret")

MONGO_URI = os.getenv("MONGO_URI", "mongodb://liora:liora_secret@localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "liora_reviews")

ELASTICSEARCH_URL = os.getenv("ELASTICSEARCH_URL", "http://localhost:9200")
MLFLOW_TRACKING_URI = os.getenv(
    "MLFLOW_TRACKING_URI", f"file:///{(ROOT_DIR / 'mlruns').as_posix()}"
)


def load_companies_config() -> dict:
    with open(CONFIG_DIR / "companies.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def postgres_dsn() -> str:
    return (
        f"host={POSTGRES_HOST} port={POSTGRES_PORT} dbname={POSTGRES_DB} "
        f"user={POSTGRES_USER} password={POSTGRES_PASSWORD}"
    )
