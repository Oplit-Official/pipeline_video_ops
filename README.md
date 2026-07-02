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

## Lancer l'interface

```bash
python3 server.py        # http://localhost:8765
```

## Dépendances

- Python : `Pillow`, `reportlab`, `pypdf`, `numpy`, `scipy`
- Binaires système : `ffmpeg`, `poppler` (`pdfunite`, `pdfimages`, `pdftotext`)
- Clés (hors dépôt, lues depuis `~/.config` ou l'environnement) :
  - `ELEVENLABS_API_KEY` (ou `~/.config/elevenlabs/key`) — voix off
  - `ANTHROPIC_API_KEY` (ou `~/.config/anthropic/key`) — réécriture des scripts
