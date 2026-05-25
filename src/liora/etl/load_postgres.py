"""Charge les CSV entreprises vers PostgreSQL."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from liora.config import RAW_DIR, ROOT_DIR, postgres_dsn

logger = logging.getLogger(__name__)


def _connect():
    return psycopg2.connect(postgres_dsn())


def init_schema() -> None:
    schema_path = ROOT_DIR / "sql" / "schema.sql"
    with _connect() as conn, conn.cursor() as cur:
        cur.execute(schema_path.read_text(encoding="utf-8"))
        conn.commit()
    logger.info("Schéma PostgreSQL initialisé.")


def load_companies_csv(csv_path: Path | None = None) -> None:
    path = csv_path or RAW_DIR / "entreprises_trustpilot.csv"
    if not path.exists():
        raise FileNotFoundError(f"Fichier introuvable : {path}")

    df = pd.read_csv(path)
    with _connect() as conn, conn.cursor() as cur:
        for _, row in df.iterrows():
            cur.execute(
                "SELECT theme_id FROM themes WHERE code = %s",
                (row["theme"],),
            )
            theme_row = cur.fetchone()
            theme_id = theme_row[0] if theme_row else None

            cur.execute(
                """
                INSERT INTO entreprises (
                    company_key, nom, domaine, theme_id, trustpilot_id,
                    profile_url, site_web, pays, est_revendique, description, scraped_at
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (company_key) DO UPDATE SET
                    nom = EXCLUDED.nom,
                    trustpilot_id = EXCLUDED.trustpilot_id,
                    scraped_at = EXCLUDED.scraped_at
                RETURNING entreprise_id
                """,
                (
                    row["company_key"],
                    row["display_name"],
                    row["domain"],
                    theme_id,
                    row["trustpilot_id"],
                    row["profile_url"],
                    row.get("website_url"),
                    row.get("country"),
                    bool(row.get("is_claimed")),
                    row.get("description"),
                    row.get("scraped_at"),
                ),
            )
            entreprise_id = cur.fetchone()[0]

            cur.execute(
                """
                INSERT INTO metriques_entreprise (
                    entreprise_id, trust_score, note_moyenne_etoiles, nombre_avis,
                    pct_excellent, pct_bien, pct_moyen, pct_mediocre, pct_mauvais,
                    taux_reponse_pct, categories, scraped_at
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                (
                    entreprise_id,
                    row.get("trust_score"),
                    row.get("stars"),
                    int(row.get("total_reviews") or 0),
                    row.get("pct_5_stars"),
                    row.get("pct_4_stars"),
                    row.get("pct_3_stars"),
                    row.get("pct_2_stars"),
                    row.get("pct_1_stars"),
                    row.get("reply_percentage"),
                    row.get("categories"),
                    row.get("scraped_at"),
                ),
            )
        conn.commit()
    logger.info("Chargement PostgreSQL terminé (%s lignes).", len(df))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    init_schema()
    load_companies_csv()
