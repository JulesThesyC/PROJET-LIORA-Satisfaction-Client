-- Projet LIORA — Schéma relationnel PostgreSQL
-- Satisfaction client Trustpilot

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Thèmes / secteurs (supply chain, ecommerce, etc.)
CREATE TABLE IF NOT EXISTS themes (
    theme_id SERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,
    label VARCHAR(100) NOT NULL,
    description TEXT
);

-- Entreprises suivies
CREATE TABLE IF NOT EXISTS entreprises (
    entreprise_id SERIAL PRIMARY KEY,
    company_key VARCHAR(50) UNIQUE NOT NULL,
    nom VARCHAR(200) NOT NULL,
    domaine VARCHAR(255) NOT NULL,
    theme_id INTEGER REFERENCES themes(theme_id),
    trustpilot_id VARCHAR(64),
    profile_url TEXT,
    site_web TEXT,
    pays VARCHAR(10),
    est_revendique BOOLEAN DEFAULT FALSE,
    description TEXT,
    scraped_at TIMESTAMPTZ
);

-- Snapshot des métriques agrégées (historisable)
CREATE TABLE IF NOT EXISTS metriques_entreprise (
    metrique_id SERIAL PRIMARY KEY,
    entreprise_id INTEGER NOT NULL REFERENCES entreprises(entreprise_id) ON DELETE CASCADE,
    trust_score NUMERIC(4, 2),
    note_moyenne_etoiles NUMERIC(3, 1),
    nombre_avis INTEGER,
    pct_excellent NUMERIC(6, 3),  -- 5 étoiles
    pct_bien NUMERIC(6, 3),       -- 4 étoiles
    pct_moyen NUMERIC(6, 3),      -- 3 étoiles
    pct_mediocre NUMERIC(6, 3),   -- 2 étoiles
    pct_mauvais NUMERIC(6, 3),    -- 1 étoile
    taux_reponse_pct NUMERIC(6, 2),
    categories TEXT,
    scraped_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (entreprise_id, scraped_at)
);

-- Catégories Trustpilot (liste entreprises par thème — type données 1)
CREATE TABLE IF NOT EXISTS entreprises_categorie (
    id SERIAL PRIMARY KEY,
    categorie_nom VARCHAR(100),
    categorie_url TEXT,
    nom_entreprise VARCHAR(200),
    domaine VARCHAR(255),
    profile_url TEXT,
    scraped_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_metriques_entreprise ON metriques_entreprise(entreprise_id);
CREATE INDEX IF NOT EXISTS idx_entreprises_theme ON entreprises(theme_id);

-- Données initiales thèmes
INSERT INTO themes (code, label, description) VALUES
    ('ecommerce', 'E-commerce', 'Marketplaces et vente en ligne'),
    ('logistique', 'Logistique', 'Transport, livraison, supply chain aval'),
    ('automobile', 'Automobile', 'Constructeurs et mobilité')
ON CONFLICT (code) DO NOTHING;
