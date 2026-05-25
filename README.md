# PROJET LIORA — Satisfaction Client (Data Engineering)

[![GitHub](https://img.shields.io/badge/GitHub-JulesThesyC-181717?logo=github)](https://github.com/JulesThesyC/PROJET-LIORA-Satisfaction-Client)

**Auteur :** [JulesThesyC](https://github.com/JulesThesyC) — Data Engineering & Science des données

Pipeline complet de collecte et d’analyse des avis **Trustpilot France** pour :

- **Amazon FR** (`www.amazon.fr`)
- **Chronopost FR** (`www.chronopost.fr`)
- **Tesla FR** (`tesla.com`)
- **Temu FR** (`temu.com`)

Données : infos société, notes, avis utilisateurs, réponses entreprise.

## Structure

```
PROJET_LIORA/
├── config/companies.yaml      # Configuration entreprises
├── src/liora/
│   ├── scraper/               # Web scraping Playwright
│   ├── etl/                   # PostgreSQL, MongoDB, ES
│   ├── ml/                    # Sentiment + MLflow + drift
│   └── api/                   # FastAPI
├── sql/                       # Schéma & requêtes PostgreSQL
├── notebooks/                 # Analyse sentiment
├── airflow/dags/              # Pipeline journalier
├── docs/                      # Documentation & rapports
├── data/raw/                  # CSV exportés
└── docker-compose.yml
```

## Installation

```powershell
cd PROJET_LIORA
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m playwright install chromium
copy .env.example .env
```

## Pipeline local (sans Docker)

```powershell
$env:PYTHONPATH = ".\src"
.\scripts\run_pipeline.ps1 -MaxReviews 80
```

Étapes : scrape → PostgreSQL → Mongo/ES → train ML → drift.

## Docker (production-like)

```powershell
docker compose up -d postgres mongodb elasticsearch kibana mlflow api
# Scraping one-shot :
docker compose --profile scrape run scraper
```

| Service        | URL                    |
|----------------|------------------------|
| API Swagger    | http://localhost:8000/docs |
| Kibana         | http://localhost:5601  |
| MLflow         | http://localhost:5000  |
| PostgreSQL     | localhost:5432         |

## Documentation

- [Traitement des données](docs/traitement_donnees.md)
- [**Rapport global détaillé (soutenance)**](docs/rapport_global.md)
- [Kibana](docs/kibana_setup.md)
- [Dérive des données](docs/rapport_drift.md)

## API — exemples

```http
GET  /health
GET  /companies
GET  /reviews/stats/amazon_fr
POST /predict/sentiment  {"texts": ["Livraison rapide, très satisfait"]}
POST /monitoring/drift
```

## Licence & usage

Projet académique. Respecter les conditions d’utilisation de Trustpilot pour tout déploiement réel.
