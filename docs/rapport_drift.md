# Rapport — mesure de la dérive des données

## Objectif

Détecter si les nouvelles collectes Trustpilot s’écartent de la **référence** (premier snapshot ou baseline validée), ce qui peut invalider le modèle de sentiment.

## Indicateurs

| Indicateur | Description | Seuil d’alerte |
|------------|-------------|----------------|
| **PSI** | Population Stability Index sur la distribution des notes 1–5 | > 0,2 |
| **Longueur texte** | Écart % sur la longueur moyenne des avis | > 15 % |
| **Taux de réponse** | Écart sur `has_company_reply` | > 10 pts |

## Fichiers

- Référence : `data/processed/reference_snapshot.json`
- Rapport : `data/processed/drift_report.json`

## Exécution

```powershell
$env:PYTHONPATH = ".\src"
python -m liora.ml.drift
```

Via API :

```http
POST http://localhost:8000/monitoring/drift
```

## Interprétation

- **PSI élevé** : changement de profil clients (ex. vague d’avis 1★ après incident livraison).
- **Longueur** : avis plus courts/longs → adapter le TF-IDF.
- **Réponse** : entreprise plus/moins réactive → indicateur supply chain aval.

Action recommandée si `drift_detected: true` : ré-entraîner le modèle et mettre à jour la référence après validation métier.
