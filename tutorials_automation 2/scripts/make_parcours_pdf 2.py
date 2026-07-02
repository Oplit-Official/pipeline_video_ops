#!/usr/bin/env python3
"""Assemble un PARCOURS en PDF : page d'intro (rédigée) + PDF des articles dans
l'ordre + page de conclusion. Les vidéos restent à l'unité ; ceci ne produit
QU'UN fichier PDF combiné.

Usage: python3 make_parcours_pdf.py /chemin/parcours_pdf.json
parcours_pdf.json:
{
  "out": "/abs/Parcours.pdf",
  "title": "Parcours — …",
  "subtitle": "…",
  "objectives": ["créer …", "définir …", "importer …"],
  "intro_text": "Bienvenue… (paragraphe libre, optionnel)",
  "conclusion_title": "Conclusion",
  "conclusion_text": "Félicitations… À très bientôt !",
  "articles": ["/abs/article1.pdf", "/abs/article2.pdf", ...]   # dans l'ordre
}
"""
import sys, os, json, subprocess, tempfile
from PIL import Image, ImageDraw, ImageFont

cfg = json.load(open(sys.argv[1]))
W, H = 1240, 1754                      # A4 portrait ~150 dpi
NAVY, ACCENT, WHITE = (27, 42, 74), (124, 92, 255), (255, 255, 255)
DARK, GREY = (33, 43, 64), (90, 100, 120)
AR = "/System/Library/Fonts/Supplemental/Arial.ttf"
ARB = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
def F(p, s): return ImageFont.truetype(p, s)

def wrap(d, text, fnt, maxw):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if d.textlength(t, font=fnt) <= maxw: cur = t
        else: lines.append(cur); cur = w
    if cur: lines.append(cur)
    return lines

def page(title, subtitle, body_lines, objectives=None):
    img = Image.new("RGB", (W, H), WHITE); d = ImageDraw.Draw(img)
    # bandeau navy + logo
    d.rectangle([0, 0, W, 230], fill=NAVY)
    d.ellipse([70, 95-34, 138, 95+34], outline=WHITE, width=6)
    d.text((160, 70), "Oplit", font=F(ARB, 60), fill=WHITE)
    d.rectangle([70, 300, 70+200, 308], fill=ACCENT)
    y = 340
    for ln in wrap(d, title, F(ARB, 54), W-140):
        d.text((70, y), ln, font=F(ARB, 54), fill=NAVY); y += 70
    if subtitle:
        y += 6
        for ln in wrap(d, subtitle, F(AR, 32), W-140):
            d.text((70, y), ln, font=F(AR, 32), fill=ACCENT); y += 44
    y += 30
    for ln in body_lines:
        for w in wrap(d, ln, F(AR, 34), W-140):
            d.text((70, y), w, font=F(AR, 34), fill=DARK); y += 50
        y += 10
    if objectives:
        y += 10
        d.text((70, y), "À la fin de ce parcours, vous serez capable de :",
                font=F(ARB, 36), fill=NAVY); y += 64
        for obj in objectives:
            d.ellipse([86, y+14, 100, y+28], fill=ACCENT)
            for i, w in enumerate(wrap(d, obj, F(AR, 34), W-200)):
                d.text((120, y), w, font=F(AR, 34), fill=DARK); y += 48
            y += 12
    # pied
    d.rectangle([0, H-70, W, H], fill=NAVY)
    return img

tmp = tempfile.mkdtemp()
intro = page(cfg["title"], cfg.get("subtitle", ""),
             wrap(ImageDraw.Draw(Image.new("RGB",(1,1))), cfg.get("intro_text",""), F(AR,34), W-140) if cfg.get("intro_text") else [],
             objectives=cfg.get("objectives"))
intro_pdf = os.path.join(tmp, "00_intro.pdf"); intro.save(intro_pdf, "PDF", resolution=150)
concl = page(cfg.get("conclusion_title", "Conclusion"), "",
             [cfg.get("conclusion_text", "")])
concl_pdf = os.path.join(tmp, "zz_concl.pdf"); concl.save(concl_pdf, "PDF", resolution=150)

parts = [intro_pdf] + cfg["articles"] + [concl_pdf]
missing = [p for p in cfg["articles"] if not os.path.exists(p)]
if missing:
    raise SystemExit("PDF article introuvable: " + "; ".join(missing))
os.makedirs(os.path.dirname(cfg["out"]) or ".", exist_ok=True)
subprocess.run(["pdfunite", *parts, cfg["out"]], check=True)
print(f"PARCOURS PDF -> {cfg['out']}  ({len(cfg['articles'])} articles + intro + conclusion)")
