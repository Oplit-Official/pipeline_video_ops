# Pipeline Video Ops — Studio Ops Oplit

Interface web pour la team Ops permettant de **composer des parcours de formation Oplit**
(catalogue d'articles vidéo classés par catégorie / sous-catégorie), de **générer un PDF
combiné** d'un parcours, d'**envoyer** aux clients, et d'**importer un PDF pour en générer
automatiquement une vidéo** (voix off ElevenLabs + captures).

## Structure du dépôt (code uniquement)

```
frontend/       Interface web (index.html, app.js, styles.css, player.html, player.js, data.js)
backend/        server.py · import_pipeline.py · make_parcours_pdf.py
video_engine/   Moteur de fabrication des vidéos (scripts/, build_video.py, README)
Dockerfile · render.yaml · requirements.txt · .env.example
```

| Élément | Rôle |
|---|---|
| `frontend/` | Catalogue, sélection, gestion des vidéos, import, lecteur + visionneuse PDF |
| `frontend/data.js` | Catalogue (catégories → sections → articles, liens vidéo/PDF/Drive) |
| `backend/server.py` | Serveur stdlib : sert `frontend/` + médias racine + endpoints (PDF parcours, import, crédits, gestion) |
| `backend/make_parcours_pdf.py` | PDF combiné (intro rédigée + articles caviardés + conclusion) |
| `backend/import_pipeline.py` | PDF → vidéo (narration réécrite via l'API Claude, appelle le moteur) |
| `video_engine/scripts/` | Moteur vidéo (`make_helpdesk_video.py`, captures, batch) |

> Les **médias** (vidéos `.mp4`, PDF FAQ, dossiers `video helpdesk…`, `Articles Helpdesk…`,
> `imports/`, artefacts de build) ne sont **pas versionnés** (voir `.gitignore`) : ils restent locaux.

## Installation & lancement

```bash
pip install -r requirements.txt          # Pillow, reportlab, pypdf, numpy, scipy
brew install ffmpeg poppler              # binaires système (macOS)
cp .env.example .env                      # puis renseigner les clés dans .env
python3 backend/server.py                 # http://localhost:8765
```

Il faut aussi récupérer les **médias** (dossiers `Articles Helpdesk…`, `video helpdesk…`),
non versionnés, pour que le catalogue pointe vers du contenu réel.

## Déploiement (Render, Docker)

Le repo contient un `Dockerfile` (Python + ffmpeg + poppler + polices) et un `render.yaml`.

1. Sur [Render](https://render.com) : **New → Blueprint** et pointer sur ce repo (lit `render.yaml`).
2. Renseigner `ELEVENLABS_API_KEY` et `ANTHROPIC_API_KEY` dans les **Secrets** du service.
3. Un **disque persistant** est monté sur `/app/imports` (vidéos importées + `imports.json`).

> ⚠️ Le plan **free** de Render est éphémère et sans disque → utiliser **starter** pour la persistance.
> ⚠️ Les **médias existants** (`Articles Helpdesk…`, `video helpdesk…`) ne sont pas dans l'image :
> pour un catalogue fonctionnel en ligne, il faut les téléverser sur le disque ou les héberger
> ailleurs (Drive / R2 / S3). Les vidéos **importées** via l'appli, elles, sont bien persistées.

Build/test en local :
```bash
docker build -t pipeline-video-ops . && docker run -p 8765:8765 --env-file .env pipeline-video-ops
```

## Clés (dans `.env`, jamais committé)

- `ELEVENLABS_API_KEY` — voix off des vidéos importées (requis pour l'import)
- `ANTHROPIC_API_KEY` — réécriture des scripts de narration (optionnel, repli sinon)

Le serveur charge automatiquement le `.env` au démarrage ; à défaut il lit aussi
`~/.config/elevenlabs/key` et `~/.config/anthropic/key`, ou les variables d'environnement.
