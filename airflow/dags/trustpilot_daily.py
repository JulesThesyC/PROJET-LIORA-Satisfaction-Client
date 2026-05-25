"""
DAG Airflow — pipeline journalier LIORA
Scraping → PostgreSQL → MongoDB/ES → entraînement ML → rapport dérive
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator

# Chemins dans le conteneur Airflow
PROJECT_SRC = "/opt/airflow/src"
DATA_DIR = "/opt/airflow/data"

default_args = {
    "owner": "liora",
    "depends_on_past": False,
    "email_on_failure": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=10),
}


def _run_etl_postgres():
    sys.path.insert(0, PROJECT_SRC)
    os.environ["DATA_DIR"] = DATA_DIR
    from liora.etl.load_postgres import init_schema, load_companies_csv

    init_schema()
    load_companies_csv()


def _run_etl_mongo():
    sys.path.insert(0, PROJECT_SRC)
    os.environ["DATA_DIR"] = DATA_DIR
    os.environ["MONGO_URI"] = os.getenv(
        "MONGO_URI", "mongodb://liora:liora_secret@mongodb:27017"
    )
    from liora.etl.load_mongodb import index_reviews_elasticsearch, load_reviews_to_mongo

    load_reviews_to_mongo()
    try:
        index_reviews_elasticsearch()
    except Exception:
        pass


def _run_train():
    sys.path.insert(0, PROJECT_SRC)
    os.environ["DATA_DIR"] = DATA_DIR
    from liora.ml.train import train_and_log

    train_and_log()


def _run_drift():
    sys.path.insert(0, PROJECT_SRC)
    os.environ["DATA_DIR"] = DATA_DIR
    from liora.ml.drift import run_drift_report

    return run_drift_report()


with DAG(
    dag_id="liora_trustpilot_daily",
    default_args=default_args,
    description="Collecte quotidienne Trustpilot et chaîne analytique",
    schedule_interval="@daily",
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["liora", "trustpilot", "satisfaction"],
) as dag:

    scrape = BashOperator(
        task_id="scrape_trustpilot",
        bash_command=(
            f"export PYTHONPATH={PROJECT_SRC} DATA_DIR={DATA_DIR} && "
            f"python -m liora.scraper.run_scraper --max-reviews 150"
        ),
    )

    load_pg = PythonOperator(
        task_id="load_postgresql",
        python_callable=_run_etl_postgres,
    )

    load_doc = PythonOperator(
        task_id="load_mongodb_elasticsearch",
        python_callable=_run_etl_mongo,
    )

    train_ml = PythonOperator(
        task_id="train_sentiment_mlflow",
        python_callable=_run_train,
    )

    drift = PythonOperator(
        task_id="compute_data_drift",
        python_callable=_run_drift,
    )

    scrape >> load_pg >> load_doc >> train_ml >> drift
