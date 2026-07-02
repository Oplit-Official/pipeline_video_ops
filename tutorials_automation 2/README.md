# Tutorial Automation — pipeline vidéos & parcours (FAQ Oplit)

But : transformer les **articles PDF du centre d'aide Oplit** en **vidéos tutoriels** (1080p, voix FR, sous-titres karaoké, curseur animé), et assembler des **parcours PDF** (plusieurs articles combinés). Ce README explique comment tout fonctionne pour qu'on puisse reprendre la pipeline.

---

## 1. Vue d'ensemble du flux

```
PDF article  ──(extract_shots)──>  captures (shot-01.png …)
     │                                    │
     │  (live: Playwright sur l'app)      │  (fallback: images du PDF, déjà annotées rose)
     ▼                                    ▼
        spec.json  (intro + 1 scène/étape + conclusion)
                          │
                  make_helpdesk_video.py   ──>  <article>.mp4
```

- **1 vidéo par article** (jamais combinées).
- **Parcours = 1 PDF combiné** (pas de vidéo) : `make_parcours_pdf.py`.

### Arborescence
- **Source** : `Articles Helpdesk pour alimentation IA/<Catégorie>/<sous-dossier>/<article> _ FAQ Oplit.pdf`
  (Catégories : Stock, Ordonnancement, Planification, Paramètres, Nouveauté produit, Autre, Client-fournisseur)
- **Sortie** : `video helpdesk/<Catégorie>/<sous-dossier>/<article>.mp4` (miroir de la source)
- **Scripts** : `scripts/`

---

## 2. Le moteur : `scripts/make_helpdesk_video.py`

Prend **un `spec.json`** en argument et produit une vidéo.

```bash
TTS=eleven MUTE=0 python3 scripts/make_helpdesk_video.py /chemin/spec.json
```

### Format du spec
```json
{
  "out":  "/abs/.../video.mp4",
  "work": "/abs/.../_work",          // dossier scratch (slides, clips, audio, states)
  "scenes": [
    {"badge":"", "title":"Tutoriel — X", "shot":null,
     "subtitle":"…", "narration":"Bienvenue… À la fin vous serez capable de…"},   // CARTON titre
    {"badge":"Étape 1", "title":"…", "shot":"/abs/shot-01.png",
     "narration":"…",                                  // narration = sous-titre karaoké + voix
     "highlight":{"fx":0.88,"fy":0.11,"fw":0.10,"fh":0.04}},   // encadré rose + curseur (optionnel)
    {"badge":"", "title":"Tutoriel terminé", "shot":null, "subtitle":"…", "narration":"…"}
  ]
}
```
Règles par scène :
- `shot:null` → **carton de titre** (intro/outro), avec `subtitle`. Sinon → **scène d'étape** avec capture.
- **Curseur / encadré rose** sur une étape, par ordre de priorité :
  1. `highlight {fx,fy,fw,fh}` (fractions de la capture) → dessine un **rectangle rose** + place le curseur au centre. (Utilisé pour les captures **live**, coordonnées issues du **rect DOM** du bouton.)
  2. `target {fx,fy}` → curseur seul.
  3. rien → **détection auto** du magenta : sur les captures **PDF** (déjà annotées rose par la FAQ), le curseur se place sur la plus grosse tache magenta.

### Ce que le moteur fabrique
- Slides 1920×1080 : header navy + logo Oplit + badge violet + capture cadrée + bandeau bas.
- **Sous-titres karaoké jaune** : remplissage **continu** mot par mot (rendu **image par image en PIL**, pas de libass — voir §5), **synchronisé** sur la voix.
- **Curseur animé + onde de clic** (overlay ffmpeg).
- **Voix off** (voir §3), **normalisée** (`loudnorm`) et **paddée** (`apad`) pour rester synchro au concat.

### Variables d'env
| Var | Défaut | Rôle |
|---|---|---|
| `TTS` | `say` | `eleven` (ElevenLabs) ou `say` (macOS) |
| `MUTE` | `1` | `1` = vidéo muette (timing quand même calé) ; `0` = avec voix |
| `ELEVEN_VOICE_ID` | `0igQGE0lbNpTaWsexf1r` (**Paul K**, FR natif) | voix ElevenLabs |
| `ELEVEN_MODEL` | `eleven_multilingual_v2` | modèle |
| `ELEVEN_LANG` | `""` | si non vide (`fr`), force la langue (modèles turbo/flash uniquement) |
| `VOICE` | `Thomas` | voix macOS `say` (fallback) |

**Clé ElevenLabs** : lue depuis `$ELEVENLABS_API_KEY` ou le fichier `~/.config/elevenlabs/key`.

---

## 3. Voix

- **ElevenLabs** (préféré) : voix **Paul K** (FR natif, e-learning). L'endpoint `/with-timestamps` renvoie l'audio **+ les timestamps par caractère** → regroupés en mots → **synchro karaoké exacte**.
- **Cache** : `~/.cache/oplit_eleven/<md5(voix|modèle|lang|texte)>.{mp3,json}` → re-générer un texte identique **ne reconsomme pas de crédits**. Changer de voix/modèle = nouvelle dépense.
- **Fallback `say`** (macOS, gratuit, FR « Thomas ») si pas de clé : pas de timestamps → karaoké **proportionnel** (un peu moins précis).
- Crédits = **caractères** (≈ 1000 car. ≈ 1 min). La clé fournie n'a pas la permission `user_read` (impossible de lire le solde par API → voir le dashboard).

---

## 4. Captures : LIVE vs FALLBACK PDF

Politique : **1 scène par étape du PDF, jamais de saut.** Live si reproductible, **sinon image du PDF**.

### a) Live (Playwright sur l'app)
- Session persistée : `build/pw-profile` (login fait une fois via `scripts/oplit_login.py`, fenêtre visible). Ensuite **headless**.
- Cible : `https://staging.oplit.fr`. **Client démo « Oplit »** (le `cid` persiste dans le profil) → **aucune donnée client réelle** (confidentialité).
- **Lecture seule** : on navigue, on ouvre des modales puis on les ferme (Annuler/Escape). **Aucune écriture** (pas de création/suppression d'enregistrements).
- On capture la capture d'écran **+ le rect DOM** du bouton visé (`element.bounding_box()` → fractions du viewport) → injecté comme `highlight` dans le spec (encadré rose dessiné par nous, au pixel).
- Viewport 1680×1000, `device_scale_factor=2` (les PNG font donc 3360×2000 → **réduire avant de les afficher** dans le chat).

### b) Fallback PDF
- `extract_shots.py` sort les **vraies captures** intégrées au PDF (filtre : largeur ≥ 700 et hauteur ≥ 400 px → élimine logos/icônes).
- Ces images **contiennent déjà les encadrés roses** de la FAQ → la **détection magenta** place le curseur dessus (pas de `highlight` à fournir).
- Données = client démo de la FAQ (« Tesla »), donc non confidentielles. Convient aux vues riches en données / pages non reproductibles en lecture seule (login, graphes, etc.).

---

## 5. Pièges / décisions importantes

- **ffmpeg sans libass** sur cette machine → impossible de brûler des sous-titres ASS. Le **karaoké est rendu en PIL** (frames RGB envoyées en pipe à ffmpeg). Gère les **silences entre mots** (sinon la surbrillance « saute »).
- **Sync audio au concat** : chaque clip a son audio **paddé à la durée de la scène** (`apad`) sinon la voix prend de l'avance clip après clip. Niveau **normalisé** à -16 LUFS (`loudnorm`).
- **Accents macOS (NFC/NFD)** : les noms de dossiers/fichiers contiennent des accents stockés **décomposés**. Un chemin écrit « à la main » (NFC) **ne matche pas** (`cd`/`glob`/`os.path.exists` échouent). **Solution** : résoudre les fichiers par `glob` avec jokers sur les accents (`Param*tres`, `G*rer`) ou `os.walk`/`os.listdir`, jamais en dur.
- **Captures live** : la session garde le **dernier client sélectionné** ; ne pas re-cliquer « Aubert & Duval » à l'aveugle — lire le `cid` courant ou re-sélectionner « Oplit » proprement.
- **Couverture intégrale** : ne **jamais** sauter une capture/étape du PDF (on a déjà eu ce reproche). Ne fusionner que des écrans strictement identiques.

---

## 6. Scripts utilitaires

| Script | Rôle |
|---|---|
| `make_helpdesk_video.py` | **Moteur** : `spec.json` → `.mp4` |
| `extract_shots.py` | `PDF out_dir` → `shot-01.png…` (vraies captures) |
| `prepare_category.py` | `SRC DST` → extrait les captures de **toute une catégorie** + `_manifest.json` |
| `build_batch.py` | `DST` → monte **tous** les `spec.json` trouvés + `video helpdesk/progress.log` + **notif macOS** |
| `make_parcours_pdf.py` | **Parcours = PDF combiné** : page intro (« à la fin vous serez capable de… ») + PDF des articles dans l'ordre + page conclusion (via `pdfunite`) |
| `oplit_login.py` | login visible (une fois) → persiste la session Playwright |
| `make_parcours.py` | (obsolète : faisait une *vidéo* combinée — on ne veut **que** le PDF combiné) |

### Suivi d'un lot
```bash
tail -f "video helpdesk/progress.log"
```

---

## 7. Recettes

**Une vidéo (voix FR) :**
```bash
TTS=eleven MUTE=0 python3 scripts/make_helpdesk_video.py /tmp/spec.json
```

**Toute une catégorie :**
```bash
python3 scripts/prepare_category.py "Articles Helpdesk pour alimentation IA/Stock" "video helpdesk/Stock"
# … rédiger un spec.json par article (intro + 1 scène/capture + conclusion) …
TTS=eleven MUTE=0 python3 scripts/build_batch.py "video helpdesk/Stock"
```

**Un parcours PDF :**
```bash
python3 scripts/make_parcours_pdf.py /tmp/parcours.json
# parcours.json: {out, title, subtitle, objectives[], conclusion_text, articles[](ordre)}
```

---

## 8. État actuel
- **Stock** : 15 vidéos (1er lot via fallback PDF) ; 3 refaites en **live + voix Paul K** (Machines, Règles de calcul, Import des données — couverture intégrale).
- **Hors Stock** : 6 vidéos (Paramètres, Ordonnancement ×2, Planification ×2, Client-fournisseur) en fallback PDF intégral.
- **Parcours PDF** : exemple `PARCOURS_Stock_Parametrage.pdf` (intro + 3 articles + conclusion).
- Reste à industrialiser les autres catégories. Décisions calées : **client démo Oplit**, **voix Paul K**, **couverture intégrale**, **fallback PDF** pour les états non reproductibles en lecture seule.
