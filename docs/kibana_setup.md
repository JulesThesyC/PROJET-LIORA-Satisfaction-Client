# Dashboard Kibana — suivi des avis

## Prérequis

```bash
docker compose up -d elasticsearch kibana
```

- Kibana : http://localhost:5601
- Elasticsearch : http://localhost:9200

## Indexation

Après le scraping :

```powershell
$env:PYTHONPATH = ".\src"
python -m liora.etl.load_mongodb
```

Index créé : **`liora_reviews`**

## Configuration dans Kibana

1. **Stack Management → Index Patterns**
   - Créer le pattern `liora_reviews*`
   - Time field : `published_date`

2. **Discover**
   - Filtrer par `company_name.keyword` : Amazon FR, Chronopost FR, etc.
   - Visualiser les champs `rating`, `has_company_reply`, `text`

3. **Dashboard suggéré — « Suivi satisfaction »**

   | Visualisation | Type | Champ |
   |---------------|------|-------|
   | Avis par entreprise | Lens / bar | `company_name.keyword` |
   | Distribution notes | pie | `rating` |
   | Taux de réponse | metric | `has_company_reply` |
   | Nuage de mots | tag cloud | `text` |
   | Timeline avis | histogram | `published_date` |

4. **Filtres utiles**
   - `rating: 1` → avis négatifs
   - `has_company_reply: true` → suivi réponse entreprise

## Requête exemple (Dev Tools)

```json
GET liora_reviews/_search
{
  "size": 0,
  "aggs": {
    "par_entreprise": {
      "terms": { "field": "company_key" },
      "aggs": {
        "note_moyenne": { "avg": { "field": "rating" } }
      }
    }
  }
}
```
