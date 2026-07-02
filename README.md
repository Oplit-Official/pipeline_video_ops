# Pipeline Video Ops — Studio Ops Oplit

Interface web pour la team Ops permettant de **composer des parcours de formation Oplit**
(catalogue d'articles vidéo classés par catégorie / sous-catégorie), de **générer un PDF
combiné** d'un parcours, d'**envoyer** aux clients, et d'**importer un PDF pour en générer
automatiquement une vidéo** (voix off ElevenLabs + captures).

## Contenu du dépôt (code uniquement)

| Fichier | Rôle |
|---|---|
| `index.html` / `styles.css` / `app.js` | Interface (catalogue, sélection, gestion des vidéos, import) |
| `player.html` / `player.js` | Lecteur de parcours vidéo + visionneuse PDF |
| `data.js` | Catalogue (catégories → sections → articles, liens vidéo/PDF/Drive) |
| `server.py` | Backend stdlib : sert le statique + endpoints (PDF parcours, import, crédits ElevenLabs, gestion) |
| `make_parcours_pdf.py` | Génère le PDF combiné (intro rédigée + articles caviardés + conclusion) |
| `import_pipeline.py` | PDF → vidéo (réécriture de la narration via l'API Claude, moteur `make_helpdesk_video.py`) |
| `tutorials_automation 2/scripts/` + `README.md` | Pipeline de fabrication des vidéos (moteur, captures, batch) |

> Les **médias** (vidéos `.mp4`, PDF FAQ, dossiers `video helpdesk`, `imports/`, artefacts de
> build) ne sont **pas versionnés** (voir `.gitignore`) : ils restent locaux.

## Installation & lancement

```bash
pip install -r requirements.txt          # Pillow, reportlab, pypdf, numpy, scipy
brew install ffmpeg poppler              # binaires système (macOS)
cp .env.example .env                      # puis renseigner les clés dans .env
python3 server.py                         # http://localhost:8765
```

Il faut aussi récupérer les **médias** (dossiers `Articles Helpdesk…`, `video helpdesk…`),
non versionnés, pour que le catalogue pointe vers du contenu réel.

## Clés (dans `.env`, jamais committé)

- `ELEVENLABS_API_KEY` — voix off des vidéos importées (requis pour l'import)
- `ANTHROPIC_API_KEY` — réécriture des scripts de narration (optionnel, repli sinon)

Le serveur charge automatiquement le `.env` au démarrage ; à défaut il lit aussi
`~/.config/elevenlabs/key` et `~/.config/anthropic/key`, ou les variables d'environnement.
