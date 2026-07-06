#!/usr/bin/env python3
"""Prépare une catégorie : miroir des dossiers + extraction des captures + manifeste.

Usage: python3 prepare_category.py "<SRC categorie>" "<DST categorie>"
  SRC = .../Articles Helpdesk pour alimentation IA/Stock
  DST = .../video helpdesk/Stock
Pour chaque PDF : extrait les vraies captures dans <DST>/<sous-dossier>/_work/<nom>/shots,
puis écrit <DST>/_manifest.json (liste des articles à scénariser/monter).
"""
import os, sys, subprocess, glob, shutil, json
from PIL import Image

SRC, DST = sys.argv[1], sys.argv[2]

def extract_shots(pdf, out):
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
    for r in sorted(glob.glob(os.path.join(tmp, "img-*.png"))):
        w, h = Image.open(r).size
        if w >= 700 and h >= 400:
            n += 1
            shutil.copy(r, os.path.join(out, f"shot-{n:02d}.png"))
    shutil.rmtree(tmp)
    return n

manifest = []
for pdf in sorted(glob.glob(os.path.join(SRC, "**", "*.pdf"), recursive=True)):
    rel = os.path.relpath(pdf, SRC)
    sub = os.path.dirname(rel)
    stem = os.path.splitext(os.path.basename(pdf))[0]
    name = stem.replace(" _ FAQ Oplit", "").strip()
    work = os.path.join(DST, sub, "_work", name)
    shots = os.path.join(work, "shots")
    out = os.path.join(DST, sub, name + ".mp4")
    n = extract_shots(pdf, shots)
    manifest.append({"pdf": pdf, "sub": sub, "name": name,
                     "work": work, "shots": shots, "out": out, "nshots": n})

os.makedirs(DST, exist_ok=True)
json.dump(manifest, open(os.path.join(DST, "_manifest.json"), "w"),
          ensure_ascii=False, indent=2)
print(f"{len(manifest)} articles")
for m in manifest:
    print(f"  {m['nshots']:>2} shots   {m['sub']} / {m['name']}")
