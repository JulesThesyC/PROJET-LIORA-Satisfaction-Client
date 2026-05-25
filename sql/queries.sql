-- Requêtes de démonstration — base LIORA

-- 1. Vue synthétique des 4 entreprises avec dernières métriques
SELECT
    e.nom,
    e.domaine,
    t.label AS theme,
    m.trust_score,
    m.nombre_avis,
    m.pct_excellent,
    m.pct_mauvais,
    m.taux_reponse_pct,
    m.scraped_at
FROM entreprises e
JOIN themes t ON t.theme_id = e.theme_id
JOIN LATERAL (
    SELECT *
    FROM metriques_entreprise me
    WHERE me.entreprise_id = e.entreprise_id
    ORDER BY me.scraped_at DESC
    LIMIT 1
) m ON TRUE
ORDER BY m.trust_score DESC NULLS LAST;

-- 2. Entreprise la plus critique (plus fort % d'avis 1 étoile)
SELECT e.nom, m.pct_mauvais, m.trust_score
FROM entreprises e
JOIN metriques_entreprise m ON m.entreprise_id = e.entreprise_id
WHERE m.scraped_at = (
    SELECT MAX(scraped_at) FROM metriques_entreprise m2 WHERE m2.entreprise_id = e.entreprise_id
)
ORDER BY m.pct_mauvais DESC NULLS LAST
LIMIT 1;

-- 3. Comparaison distribution des notes par thème
SELECT
    t.label AS theme,
    ROUND(AVG(m.pct_excellent), 2) AS avg_pct_5,
    ROUND(AVG(m.pct_mauvais), 2) AS avg_pct_1,
    SUM(m.nombre_avis) AS total_avis_plateforme
FROM metriques_entreprise m
JOIN entreprises e ON e.entreprise_id = m.entreprise_id
JOIN themes t ON t.theme_id = e.theme_id
GROUP BY t.label;

-- 4. Entreprises avec profil revendiqué
SELECT nom, domaine, est_revendique
FROM entreprises
WHERE est_revendique = TRUE;
