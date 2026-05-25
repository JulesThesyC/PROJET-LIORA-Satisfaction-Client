"""Charge les avis CSV vers MongoDB + index Elasticsearch."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import pandas as pd
from elasticsearch import Elasticsearch, helpers
from pymongo import MongoClient, UpdateOne

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from liora.config import ELASTICSEARCH_URL, MONGO_DB, MONGO_URI, RAW_DIR

logger = logging.getLogger(__name__)
INDEX_NAME = "liora_reviews"


def load_reviews_to_mongo(csv_path: Path | None = None) -> int:
    path = csv_path or RAW_DIR / "avis_trustpilot.csv"
    if not path.exists():
        raise FileNotFoundError(path)

    df = pd.read_csv(path)
    client = MongoClient(MONGO_URI)
    db = client[MONGO_DB]
    collection = db["reviews"]

    operations = []
    for doc in df.to_dict(orient="records"):
        doc["_id"] = doc["review_id"]
        operations.append(
            UpdateOne({"_id": doc["review_id"]}, {"$set": doc}, upsert=True)
        )

    if operations:
        result = collection.bulk_write(operations, ordered=False)
        logger.info(
            "MongoDB : %s upserts, %s modifiés",
            result.upserted_count,
            result.modified_count,
        )

    collection.create_index([("company_key", 1), ("rating", 1)])
    collection.create_index([("published_date", -1)])
    return len(df)


def index_reviews_elasticsearch(csv_path: Path | None = None) -> int:
    path = csv_path or RAW_DIR / "avis_trustpilot.csv"
    df = pd.read_csv(path)
    es = Elasticsearch(ELASTICSEARCH_URL, request_timeout=60)

    if not es.indices.exists(index=INDEX_NAME):
        es.indices.create(
            index=INDEX_NAME,
            body={
                "mappings": {
                    "properties": {
                        "company_key": {"type": "keyword"},
                        "company_name": {"type": "keyword"},
                        "rating": {"type": "integer"},
                        "text": {"type": "text", "analyzer": "french"},
                        "title": {"type": "text"},
                        "published_date": {"type": "date"},
                        "has_company_reply": {"type": "boolean"},
                        "company_reply_text": {"type": "text"},
                        "reviewer_name": {"type": "keyword"},
                    }
                }
            },
        )

    actions = [
        {
            "_index": INDEX_NAME,
            "_id": row["review_id"],
            "_source": row.to_dict(),
        }
        for _, row in df.iterrows()
    ]
    if actions:
        helpers.bulk(es, actions, raise_on_error=False)
    logger.info("Elasticsearch : %s documents indexés.", len(actions))
    return len(actions)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    n = load_reviews_to_mongo()
    logger.info("%s avis en MongoDB", n)
    try:
        index_reviews_elasticsearch()
    except Exception as exc:
        logger.warning("Elasticsearch indisponible : %s", exc)
