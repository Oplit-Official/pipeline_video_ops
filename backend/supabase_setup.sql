-- Table des vidéos importées (métadonnées). À exécuter dans Supabase → SQL Editor.
create table if not exists public.imports (
  id         text primary key,
  title      text not null,
  section    text,
  category   text,
  icon       text,
  dur        integer,          -- durée en secondes
  min        integer,          -- durée arrondie en minutes
  video      text,             -- URL publique du .mp4 (Storage)
  pdf        text,             -- URL publique du .pdf (Storage)
  created_at timestamptz default now()
);

-- Le serveur accède avec la clé service_role (bypass RLS). Pas de policy requise.
-- Si tu veux exposer la table en lecture publique (anon), active plutôt une policy select.

-- Storage : crée un bucket « videos » (Dashboard → Storage → New bucket), coché PUBLIC
-- pour que les URLs /object/public/... soient lisibles directement par le navigateur.
