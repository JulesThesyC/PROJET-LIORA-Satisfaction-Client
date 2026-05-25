#!/usr/bin/env python
"""Point d'entrée — collecte Trustpilot → CSV."""

from __future__ import annotations

import argparse
import logging
import sys
from dataclasses import asdict
from pathlib import Path

import pandas as pd

# Permettre l'exécution depuis la racine du projet
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from liora.config import (
    MAX_REVIEWS_PER_COMPANY,
    MAX_REVIEW_PAGES,
    PROCESSED_DIR,
    RAW_DIR,
    SCRAPER_HEADLESS,
    load_companies_config,
)
from liora.scraper.trustpilot import TrustpilotScraper

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def run(
    max_reviews: int | None = None,
    max_pages: int | None = None,
    include_categories: bool = False,
) -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    cfg = load_companies_config()
    scraper = TrustpilotScraper(headless=SCRAPER_HEADLESS)
    limit = max_reviews or MAX_REVIEWS_PER_COMPANY
    pages = max_pages or MAX_REVIEW_PAGES

    companies_rows: list[dict] = []
    reviews_rows: list[dict] = []

    for company in cfg["companies"]:
        key = company["key"]
        logger.info("=== Entreprise : %s ===", company["name"])
        info = scraper.scrape_company_profile(
            company_key=key,
            name=company["name"],
            domain=company["domain"],
            theme=company["theme"],
            slug=company["trustpilot_slug"],
        )
        companies_rows.append(asdict(info))

        reviews = scraper.scrape_reviews(
            company_key=key,
            company_name=company["name"],
            domain=company["domain"],
            slug=company["trustpilot_slug"],
            max_reviews=limit,
            max_pages=pages,
        )
        reviews_rows.extend(asdict(r) for r in reviews)
        logger.info("  → %s avis collectés", len(reviews))

    df_companies = pd.DataFrame(companies_rows)
    df_reviews = pd.DataFrame(reviews_rows)

    companies_path = RAW_DIR / "entreprises_trustpilot.csv"
    reviews_path = RAW_DIR / "avis_trustpilot.csv"
    df_companies.to_csv(companies_path, index=False, encoding="utf-8-sig")
    df_reviews.to_csv(reviews_path, index=False, encoding="utf-8-sig")

    if include_categories:
        cat_rows: list[dict] = []
        for cat in cfg.get("category_urls", []):
            logger.info("Catégorie : %s", cat["name"])
            cat_rows.extend(
                scraper.scrape_category_companies(cat["url"], max_companies=25)
            )
        if cat_rows:
            pd.DataFrame(cat_rows).to_csv(
                RAW_DIR / "categories_trustpilot.csv",
                index=False,
                encoding="utf-8-sig",
            )

    logger.info("Export : %s (%s lignes)", companies_path, len(df_companies))
    logger.info("Export : %s (%s lignes)", reviews_path, len(df_reviews))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scraper Trustpilot LIORA")
    parser.add_argument("--max-reviews", type=int, default=None)
    parser.add_argument("--max-pages", type=int, default=None)
    parser.add_argument("--categories", action="store_true")
    args = parser.parse_args()
    run(
        max_reviews=args.max_reviews,
        max_pages=args.max_pages,
        include_categories=args.categories,
    )
