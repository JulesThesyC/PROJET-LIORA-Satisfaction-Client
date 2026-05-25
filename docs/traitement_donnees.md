# Traitement des données — Projet LIORA

## Contexte

Projet **Satisfaction Client** : évaluation de la supply chain en aval via les avis Trustpilot (France).

**Entreprises ciblées :**

| Entreprise     | Domaine Trustpilot   | Thème        |
|----------------|----------------------|--------------|
| Amazon FR      | www.amazon.fr        | E-commerce   |
| Chronopost FR  | www.chronopost.fr    | Logistique   |
| Tesla FR       | tesla.com            | Automobile   |
| Temu FR        | temu.com             | E-commerce   |

## Étape 1 — Collecte (web scraping)

### Source

- Site : [Trustpilot France](https://fr.trustpilot.com)
- Pages entreprise : `https://fr.trustpilot.com/review/{domaine}`

### Données extraites

**a) Informations société**

- Nom affiché, domaine, URL profil, site web
- TrustScore, note étoiles, nombre total d’avis
- Pays, catégories, description
- Profil revendiqué (`is_claimed`)
- Taux de réponse aux avis négatifs

**b) Notes**

- TrustScore (1–5)
- Distribution par classe (5 à 1 étoiles, en % — barres HTML)

**c) Avis utilisateurs**

- Identifiant, titre, texte, note (1–5)
- Date de publication, langue
- Nom et pays du reviewer
- Badge vérifié, nombre de « utile »

**d) Réponses entreprise**

- Présence d’une réponse (`reply` dans le JSON)
- Texte et date de la réponse

### Technique

1. **Playwright** (Chromium headless) : contourne le blocage HTTP 403.
2. Extraction du JSON embarqué `__NEXT_DATA__` (20 avis par page).
3. Pagination via paramètre `?page=N`.
4. Distribution des étoiles via attributs `data-star-rating` et largeur CSS des barres.

### Fichiers produits

| Fichier | Contenu |
|---------|---------|
| `data/raw/entreprises_trustpilot.csv` | Métriques agrégées par entreprise |
| `data/raw/avis_trustpilot.csv` | Avis détaillés + réponses |
| `data/raw/categories_trustpilot.csv` | (optionnel) listes catégories Trustpilot |

### Commande

```powershell
$env:PYTHONPATH = ".\src"
python -m liora.scraper.run_scraper --max-reviews 200
```

Paramètres : `MAX_REVIEWS_PER_COMPANY`, `MAX_REVIEW_PAGES` dans `.env`.

### Limites & éthique

- Respect des délais entre pages (`delay_seconds`).
- Volume limité par défaut (échantillon pour analyse, pas miroir complet).
- Usage pédagogique ; vérifier les CGU Trustpilot en production.

## Étape 2 — Organisation

- **PostgreSQL** : modèle relationnel (`themes`, `entreprises`, `metriques_entreprise`)
- **MongoDB** : collection `reviews` (documents = avis complets)
- **Elasticsearch** : index `liora_reviews` pour **Kibana**

Voir `sql/schema.sql`, `sql/queries.sql` et `docs/kibana_setup.md`.

## Étapes 3 à 5

- ML : `src/liora/ml/` + notebook `notebooks/sentiment_analysis.ipynb`
- API : `src/liora/api/main.py`
- Orchestration : `airflow/dags/trustpilot_daily.py`
