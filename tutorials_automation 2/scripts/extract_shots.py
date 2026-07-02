#!/usr/bin/env python3
"""Extrait les vraies captures d'écran d'un PDF FAQ Oplit (ignore logos/icônes).

Usage: python3 extract_shots.py "/abs/article.pdf" "/abs/out_dir"
Sort: shot-01.png, shot-02.png, … (ordre des pages) + imprime le nombre.
Heuristique : on garde les images larges (>=700 px) et hautes (>=400 px),
ce qui élimine barre de recherche, logo et pictos.
"""
import os, sys, subprocess, glob, shutil
from PIL import Image

pdf, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
tmp = os.path.join(out, "_raw")
if os.path.isdir(tmp):
    shutil.rmtree(tmp)
os.makedirs(tmp)

subprocess.run(["pdfimages", "-png", pdf, os.path.join(tmp, "img")],
               check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

raws = sorted(glob.glob(os.path.join(tmp, "img-*.png")))
n = 0
for r in raws:
    w, h = Image.open(r).size
    if w >= 700 and h >= 400:
        n += 1
        shutil.copy(r, os.path.join(out, f"shot-{n:02d}.png"))
shutil.rmtree(tmp)
print(n)
