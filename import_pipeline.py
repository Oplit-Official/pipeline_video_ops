#!/usr/bin/env python3
"""Pipeline d'import d'un exercice : PDF -> vidéo (qualité « fallback PDF »).
Réutilise le moteur officiel `make_helpdesk_video.py` (mêmes slides, voix Paul K,
karaoké, curseur auto sur le magenta). Reporte l'avancement via un callback.

build_video(pdf_path, title, section, work_dir, out_mp4, on_progress) -> out_mp4
"""
import os, re, glob, shutil, subprocess, json, unicodedata, urllib.request, urllib.error
from PIL import Image

ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")


def _anthropic_key():
    k = os.environ.get("ANTHROPIC_API_KEY")
    if k:
        return k.strip()
    for p in ("~/.config/anthropic/key", "~/.config/elevenlabs/key", "~/.config/claude/key"):
        fp = os.path.expanduser(p)
        if os.path.exists(fp):
            for line in open(fp):
                line = line.strip()
                if line.startswith("sk-ant-"):
                    return line
    return None


def generate_narration(title, full_text, n_steps):
    """Réécrit une voix-off propre et cohérente via l'API Claude.
    Retourne {"intro":..., "steps":[... n_steps ...], "outro":...} ou None si indispo."""
    key = _anthropic_key()
    if not key or not full_text.strip():
        return None
    prompt = (
        f"Tu rédiges la VOIX-OFF d'un tutoriel vidéo Oplit (logiciel de planification industrielle).\n"
        f"Titre du tutoriel : « {title} ».\n"
        f"Le texte ci-dessous est extrait brut d'un article PDF (il peut contenir du bruit : "
        f"fils d'ariane, menus, fragments). Rédige un script clair, naturel et fluide en français, "
        f"au vouvoiement, sans dates ni éléments de navigation.\n"
        f"Réponds UNIQUEMENT en JSON valide, sans texte autour, au format :\n"
        f'{{"intro": "...", "steps": ["...", "..."], "outro": "..."}}\n'
        f"Contraintes : exactement {n_steps} éléments dans \"steps\" (un par étape/capture d'écran), "
        f"chaque étape = 1 à 2 phrases concises ; \"intro\" accueille et annonce l'objectif ; "
        f'"outro" conclut brièvement.\n\n'
        f"TEXTE DE L'ARTICLE :\n{full_text[:6000]}"
    )
    body = json.dumps({
        "model": ANTHROPIC_MODEL,
        "max_tokens": 1500,
        "messages": [{"role": "user", "content": prompt}],
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages", data=body,
        headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                 "content-type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.load(r)
        txt = "".join(b.get("text", "") for b in data.get("content", []))
        txt = re.sub(r"^```(?:json)?|```$", "", txt.strip(), flags=re.M).strip()
        obj = json.loads(txt)
        steps = [str(s).strip() for s in (obj.get("steps") or [])]
        # ajuste à n_steps
        while len(steps) < n_steps:
            steps.append("")
        steps = steps[:n_steps]
        return {"intro": str(obj.get("intro", "")).strip(),
                "steps": steps,
                "outro": str(obj.get("outro", "")).strip()}
    except Exception:
        return None

BASE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.join(BASE, "tutorials_automation 2", "scripts", "make_helpdesk_video.py")


def _extract_shots(pdf, out):
    os.makedirs(out, exist_ok=True)
    for old in glob.glob(os.path.join(out, "shot-*.png")):
        os.remove(old)
    tmp = os.path.join(out, "_raw")
    if os.path.isdir(tmp):
        shutil.rmtree(tmp)
    os.makedirs(tmp)
    subprocess.run(["pdfimages", "-png", pdf, os.path.join(tmp, "img")],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    n = 0
    shots = []
    for r in sorted(glob.glob(os.path.join(tmp, "img-*.png"))):
        w, h = Image.open(r).size
        if w >= 700 and h >= 400:
            n += 1
            dst = os.path.join(out, f"shot-{n:02d}.png")
            shutil.copy(r, dst)
            shots.append(dst)
    shutil.rmtree(tmp)
    return shots


def _pdf_text(pdf):
    try:
        return subprocess.run(["pdftotext", "-layout", pdf, "-"],
                              capture_output=True, text=True).stdout
    except Exception:
        return ""


# Boilerplate FAQ / navigation à retirer de la narration
_BOILER = [
    r"https?://\S+",
    r"\d{1,2}/\d{1,2}/\d{2,4}",                 # dates
    r"\b\d{1,2}\s*[:hH]\s*\d{2}\b",             # heures
    r"\|?\s*FAQ Oplit",
    r"Aller au site",
    r"Rechercher sur le centre d['’]aide\s*\.*",
    r"Articles?\s+sur\s*:",
    r"Articles?\s+en\s+rapport",
    r"__+\s*Objectifs?\s*:?\s*__+",
    r"__+",                                      # marqueurs ___
    r"\bFAQ\b",
]


def _nfc(t):
    # recompose les accents (macOS = NFD : 'e' + accent combinant -> PIL casse l'affichage)
    return unicodedata.normalize("NFC", t or "")


def _clean(t):
    t = _nfc(t)
    for p in _BOILER:
        t = re.sub(p, " ", t, flags=re.I)
    t = re.sub(r"\.{2,}", ". ", t)              # "…" -> point
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _split_narration(text, n):
    """Découpe le texte du PDF en n segments ~équilibrés (frontières de phrases)."""
    text = _clean(text)
    if not text:
        return ["" for _ in range(n)]
    sents = re.split(r"(?<=[.!?])\s+", text)
    sents = [s for s in sents if len(s) > 2]
    if not sents:
        return ["" for _ in range(n)]
    per = max(1, len(sents) // n)
    chunks, i = [], 0
    for k in range(n):
        part = sents[i:i + per] if k < n - 1 else sents[i:]
        i += per
        seg = " ".join(part).strip()
        if len(seg) > 220:               # narration courte par étape (durée + coût TTS)
            seg = seg[:220].rsplit(" ", 1)[0] + "."
        chunks.append(seg)
    return chunks


def build_video(pdf_path, title, section, work_dir, out_mp4, on_progress=lambda *a: None,
                remaining_chars=None):
    title = _nfc(title)
    section = _nfc(section)
    on_progress("extract", "Extraction des captures du PDF", 12, {})
    shots = _extract_shots(pdf_path, os.path.join(work_dir, "shots"))
    if not shots:
        raise RuntimeError("Aucune capture exploitable trouvée dans le PDF "
                           "(images trop petites ou PDF sans capture).")
    on_progress("extract", f"{len(shots)} capture(s) extraite(s)", 22, {"shots": len(shots)})

    on_progress("spec", "Préparation du script et de la narration", 30, {"shots": len(shots)})
    raw = _clean(_pdf_text(pdf_path))
    intro = (f"Bienvenue dans ce tutoriel Oplit : {title}. "
             f"Suivez les étapes pour prendre en main cette fonctionnalité pas à pas.")
    outro = (f"Voilà, vous savez maintenant {title.lower()}. "
             f"Merci d'avoir suivi ce tutoriel Oplit, à très bientôt !")
    llm = generate_narration(title, raw, len(shots))   # réécriture cohérente via Claude
    if llm:
        narr = [_clean(s) for s in llm["steps"]]
        if llm.get("intro"):
            intro = _clean(llm["intro"])
        if llm.get("outro"):
            outro = _clean(llm["outro"])
    else:
        narr = _split_narration(raw, len(shots))         # repli : découpage brut
    scenes = [{"badge": "", "title": f"Tutoriel — {title}", "shot": None,
               "subtitle": section or "", "narration": intro}]
    for i, sh in enumerate(shots):
        scenes.append({"badge": f"Étape {i + 1}", "title": title, "shot": sh,
                       "narration": narr[i] or f"Étape {i + 1}."})
    scenes.append({"badge": "", "title": "Tutoriel terminé", "shot": None,
                   "subtitle": "Merci d'avoir suivi ce tutoriel", "narration": outro})

    # Garde-fou crédits ElevenLabs (si le solde est connu)
    needed = sum(len(s.get("narration") or "") for s in scenes)
    if remaining_chars is not None and needed > remaining_chars:
        raise RuntimeError(
            f"Crédits ElevenLabs insuffisants : ~{needed} caractères nécessaires "
            f"(~{needed // 1000 + 1} min de voix), {remaining_chars} restants. "
            f"Rechargez votre quota ElevenLabs.")

    spec = {"out": out_mp4, "work": work_dir, "scenes": scenes}
    spec_path = os.path.join(work_dir, "spec.json")
    json.dump(spec, open(spec_path, "w"), ensure_ascii=False, indent=2)

    on_progress("render", "Voix (ElevenLabs) + montage vidéo", 45,
                {"shots": len(shots), "scenes": len(scenes)})
    env = dict(os.environ, TTS="eleven", MUTE="0")
    r = subprocess.run(["python3", ENGINE, spec_path],
                       env=env, capture_output=True, text=True)
    if r.returncode != 0:
        last = (r.stderr.strip().splitlines() or ["échec inconnu"])[-1]
        raise RuntimeError(f"Montage échoué : {last[:200]}")
    if not os.path.exists(out_mp4):
        raise RuntimeError("La vidéo n'a pas été produite.")
    on_progress("done", "Vidéo prête", 100, {"shots": len(shots)})
    return out_mp4


def slugify(s):
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^A-Za-z0-9]+", "-", s).strip("-").lower()
    return s or "exercice"
