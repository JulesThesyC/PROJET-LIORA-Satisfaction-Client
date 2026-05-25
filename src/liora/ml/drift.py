"""Détection de dérive des données (distribution notes & longueur textes)."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from liora.config import PROCESSED_DIR, RAW_DIR

logger = logging.getLogger(__name__)
REFERENCE_PATH = PROCESSED_DIR / "reference_snapshot.json"
DRIFT_REPORT_PATH = PROCESSED_DIR / "drift_report.json"


def _distribution(series: pd.Series) -> dict[str, float]:
    counts = series.value_counts(normalize=True).sort_index()
    return {str(k): float(v) for k, v in counts.items()}


def save_reference_snapshot(df: pd.DataFrame) -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    snapshot = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "rating_distribution": _distribution(df["rating"]),
        "avg_text_length": float(df["text"].str.len().mean()),
        "reply_rate": float(df["has_company_reply"].mean()),
        "n_samples": len(df),
    }
    REFERENCE_PATH.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
    logger.info("Référence sauvegardée : %s", REFERENCE_PATH)


def compute_drift(current_df: pd.DataFrame) -> dict:
    if not REFERENCE_PATH.exists():
        save_reference_snapshot(current_df)
        return {"status": "reference_created", "message": "Premier snapshot de référence créé."}

    ref = json.loads(REFERENCE_PATH.read_text(encoding="utf-8"))
    cur_dist = _distribution(current_df["rating"])
    ref_dist = ref["rating_distribution"]

    all_keys = set(ref_dist) | set(cur_dist)
    psi = 0.0
    for k in all_keys:
        expected = ref_dist.get(k, 1e-6)
        actual = cur_dist.get(k, 1e-6)
        psi += (actual - expected) * np.log(actual / expected)

    avg_len_cur = float(current_df["text"].str.len().mean())
    avg_len_ref = ref["avg_text_length"]
    len_drift_pct = abs(avg_len_cur - avg_len_ref) / max(avg_len_ref, 1) * 100

    reply_cur = float(current_df["has_company_reply"].mean())
    reply_drift = abs(reply_cur - ref["reply_rate"]) * 100

    alert = psi > 0.2 or len_drift_pct > 15 or reply_drift > 10
    report = {
        "computed_at": datetime.now(timezone.utc).isoformat(),
        "population_stability_index": round(float(psi), 4),
        "avg_text_length_drift_pct": round(len_drift_pct, 2),
        "reply_rate_drift_pct": round(reply_drift, 2),
        "reference_distribution": ref_dist,
        "current_distribution": cur_dist,
        "drift_detected": alert,
        "thresholds": {"psi": 0.2, "text_length_pct": 15, "reply_rate_pct": 10},
    }
    DRIFT_REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def run_drift_report() -> dict:
    path = RAW_DIR / "avis_trustpilot.csv"
    df = pd.read_csv(path)
    return compute_drift(df)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(json.dumps(run_drift_report(), indent=2))
