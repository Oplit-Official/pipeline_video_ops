#!/usr/bin/env python3
"""Assemble un PARCOURS : juxtaposition des contenus de plusieurs articles, dans
l'ordre, encadrée d'UNE intro globale (« à la fin vous serez capable de… ») et
d'UNE mini-conclusion. Aucun carton intro/outro par article n'est conservé.

Usage: python3 make_parcours.py /chemin/parcours.json
parcours.json:
{
  "out": "/abs/Parcours.mp4",
  "work": "/abs/_work_parcours",
  "title": "Parcours — …",
  "subtitle": "…",
  "intro_narration": "Bienvenue… À la fin de ce parcours, vous serez capable de : …",
  "conclusion_title": "Parcours terminé",
  "conclusion_subtitle": "…",
  "conclusion_narration": "Félicitations… À très bientôt !",
  "articles": ["/abs/spec_article1.json", "/abs/spec_article2.json", ...]  # dans l'ordre
}
"""
import sys, os, json, subprocess

cfg = json.load(open(sys.argv[1]))
scenes = []
# 1) intro globale (carton titre + objectifs en voix/karaoké)
scenes.append({"badge": "", "title": cfg["title"], "shot": None,
               "subtitle": cfg.get("subtitle", ""),
               "narration": cfg["intro_narration"]})
# 2) contenu des articles dans l'ordre — uniquement les scènes d'ÉTAPE (avec capture)
for sp in cfg["articles"]:
    art = json.load(open(sp))
    for s in art["scenes"]:
        if s.get("shot"):              # on saute les cartons intro/outro de chaque article
            scenes.append(s)
# 3) mini-conclusion
scenes.append({"badge": "", "title": cfg.get("conclusion_title", "Parcours terminé"),
               "shot": None, "subtitle": cfg.get("conclusion_subtitle", ""),
               "narration": cfg["conclusion_narration"]})

combined = {"out": cfg["out"], "work": cfg["work"], "scenes": scenes}
spec_path = os.path.join(cfg["work"] + "_spec.json")
os.makedirs(os.path.dirname(spec_path) or ".", exist_ok=True)
json.dump(combined, open(spec_path, "w"), ensure_ascii=False, indent=2)
print(f"parcours: {len(scenes)} scènes ({len(cfg['articles'])} articles juxtaposés)")

engine = os.path.join(os.path.dirname(os.path.abspath(__file__)), "make_helpdesk_video.py")
subprocess.run([sys.executable, engine, spec_path], env=os.environ, check=True)
print("PARCOURS ->", cfg["out"])
