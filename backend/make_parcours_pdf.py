#!/usr/bin/env python3
"""Assemble un PARCOURS en PDF : page d'intro (rédigée, avec liens vidéo
cliquables) + PDF des articles dans l'ordre + page de conclusion. Les vidéos
restent à l'unité (liens Drive) ; ceci ne produit QU'UN fichier PDF combiné.

Utilisable :
  - en CLI :   python3 make_parcours_pdf.py /chemin/parcours_pdf.json [base_dir]
  - en module : from make_parcours_pdf import build_parcours ; build_parcours(cfg, base_dir)

cfg :
{
  "out": "/abs/Parcours.pdf",
  "title": "Parcours — …",
  "subtitle": "…",
  "intro_text": "Bienvenue… (optionnel)",
  "objectives": ["créer …", "définir …"],
  "video_links": [{"titre": "Créer …", "url": "https://drive.google.com/file/d/…/view"}],
  "conclusion_title": "Conclusion",
  "conclusion_text": "Félicitations… À très bientôt !",
  "articles": ["article1.pdf", "article2.pdf", ...]   # dans l'ordre (abs ou relatif à base_dir)
}
"""
import sys, os, json, subprocess, tempfile, unicodedata, shutil, re
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Intègre Arial sous les noms Helvetica* -> texte embarqué, rendu garanti partout
for _name, _file in [("Helvetica", "Arial.ttf"), ("Helvetica-Bold", "Arial Bold.ttf"),
                     ("Helvetica-Oblique", "Arial Italic.ttf")]:
    _p = "/System/Library/Fonts/Supplemental/" + _file
    if os.path.exists(_p):
        try:
            pdfmetrics.registerFont(TTFont(_name, _p))
        except Exception:
            pass

PAGE_W, PAGE_H = A4                       # 595.27 x 841.89 pts
NAVY   = (27/255, 42/255, 74/255)
ACCENT = (124/255, 92/255, 255/255)
DARK   = (33/255, 43/255, 64/255)
GREY   = (96/255, 104/255, 124/255)
LINK   = (0.16, 0.32, 0.86)
MX = 50                                   # marge gauche
MAXW = PAGE_W - 2 * MX


def nfc(s):
    # Recompose les accents (les noms macOS sont en NFD : 'e' + accent combinant,
    # qu'Helvetica dessine comme un carré). NFC -> 'é' précomposé, rendu correctement.
    return unicodedata.normalize("NFC", s or "")


def _wrap(c, text, font, size, maxw):
    text = nfc(text)
    lines, cur = [], ""
    for w in (text or "").split():
        t = (cur + " " + w).strip()
        if c.stringWidth(t, font, size) <= maxw:
            cur = t
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def _chrome(c):
    """Bandeau navy + logo + pied, sur la page courante."""
    c.setFillColorRGB(*NAVY)
    c.rect(0, PAGE_H - 92, PAGE_W, 92, fill=1, stroke=0)
    c.setStrokeColorRGB(1, 1, 1)
    c.setLineWidth(2.4)
    c.circle(MX + 2, PAGE_H - 46, 15, stroke=1, fill=0)
    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica-Bold", 24)
    c.drawString(MX + 28, PAGE_H - 54, "Oplit")
    c.setFillColorRGB(*NAVY)
    c.rect(0, 0, PAGE_W, 26, fill=1, stroke=0)


class Doc:
    def __init__(self, c):
        self.c = c
        self.y = 0
        self._start_page(accent=True)

    def _start_page(self, accent=False):
        _chrome(self.c)
        self.y = PAGE_H - 150
        if accent:
            self.c.setFillColorRGB(*ACCENT)
            self.c.rect(MX, self.y + 30, 92, 5, fill=1, stroke=0)

    def _need(self, h):
        if self.y - h < 48:
            self.c.showPage()
            self._start_page()

    def para(self, text, font, size, color, lead, gap=0, maxw=MAXW, x=MX):
        for ln in _wrap(self.c, text, font, size, maxw):
            self._need(lead)
            self.c.setFont(font, size)
            self.c.setFillColorRGB(*color)
            self.c.drawString(x, self.y, ln)
            self.y -= lead
        self.y -= gap

    def heading(self, text):
        self.y -= 6
        self.para(text, "Helvetica-Bold", 14, NAVY, 20, gap=4)

    def bullet(self, text):
        # puce accent + texte (multi-lignes alignées)
        lines = _wrap(self.c, text, "Helvetica", 12, MAXW - 26)
        for i, ln in enumerate(lines):
            self._need(19)
            if i == 0:
                self.c.setFillColorRGB(*ACCENT)
                self.c.circle(MX + 5, self.y + 4, 3, fill=1, stroke=0)
            self.c.setFont("Helvetica", 12)
            self.c.setFillColorRGB(*DARK)
            self.c.drawString(MX + 20, self.y, ln)
            self.y -= 19
        self.y -= 8

    def link(self, label, url):
        # petit triangle "play" + label cliquable (souligné, couleur lien)
        label = nfc(label)
        self._need(18)
        self.c.setFillColorRGB(*ACCENT)
        p = self.c.beginPath()
        p.moveTo(MX + 2, self.y + 9)
        p.lineTo(MX + 2, self.y)
        p.lineTo(MX + 11, self.y + 4.5)
        p.close()
        self.c.drawPath(p, fill=1, stroke=0)
        self.c.setFont("Helvetica", 11.5)
        tw = self.c.stringWidth(label, "Helvetica", 11.5)
        avail = MAXW - 24
        # tronque visuellement si trop long
        disp = label
        if tw > avail:
            while disp and self.c.stringWidth(disp + "…", "Helvetica", 11.5) > avail:
                disp = disp[:-1]
            disp += "…"
            tw = self.c.stringWidth(disp, "Helvetica", 11.5)
        self.c.setFillColorRGB(*LINK)
        self.c.drawString(MX + 20, self.y, disp)
        self.c.setStrokeColorRGB(*LINK)
        self.c.setLineWidth(0.6)
        self.c.line(MX + 20, self.y - 1.5, MX + 20 + tw, self.y - 1.5)
        self.c.linkURL(url, (MX + 20, self.y - 3, MX + 20 + tw, self.y + 11), relative=0)
        self.y -= 23

    def space(self, d):
        self.y -= d


def _intro(c, cfg):
    d = Doc(c)
    d.para(cfg.get("title", "Parcours Oplit"), "Helvetica-Bold", 26, NAVY, 34, gap=10)
    if cfg.get("subtitle"):
        d.para(cfg["subtitle"], "Helvetica", 14.5, ACCENT, 21, gap=22)
    if cfg.get("intro_text"):
        d.para(cfg["intro_text"], "Helvetica", 12, DARK, 20, gap=14)
    # explique que le PDF lui-même déroule le tuto
    d.para("Les pages suivantes reprennent chaque article du parcours, avec les "
           "explications détaillées, étape par étape, et les captures d'écran. "
           "Vous pouvez donc suivre toute la formation directement dans ce document.",
           "Helvetica-Oblique", 11.5, GREY, 19, gap=18)
    objs = cfg.get("objectives") or []
    if objs:
        d.heading("À la fin de ce parcours, vous serez capable de :")
        for o in objs:
            d.bullet(o)
        d.space(10)
    links = cfg.get("video_links") or []
    if links:
        d.space(4)
        d.heading("Vidéos du parcours (consultables sur le Drive) :")
        for it in links:
            if it.get("url"):
                d.link(it.get("titre", it["url"]), it["url"])
    # repère bas de page : « Tutoriel ci-dessous » + flèche
    cx = PAGE_W / 2
    c.setFillColorRGB(*ACCENT)
    c.setFont("Helvetica-Bold", 13)
    c.drawCentredString(cx, 84, "Tutoriel ci-dessous")
    p = c.beginPath()
    p.moveTo(cx - 10, 70); p.lineTo(cx + 10, 70); p.lineTo(cx, 52); p.close()
    c.drawPath(p, fill=1, stroke=0)
    c.showPage()


def _conclusion(c, cfg):
    d = Doc(c)
    d.para(cfg.get("conclusion_title", "Conclusion"), "Helvetica-Bold", 26, NAVY, 34, gap=20)
    if cfg.get("conclusion_text"):
        d.para(cfg["conclusion_text"], "Helvetica", 12.5, DARK, 21)
    c.showPage()


_DATE_RE = re.compile(r"\d{1,2}/\d{1,2}/\d{2,4}")


def _bbox_pages(pdf):
    """[(W, H, [(xMin,yMin,xMax,yMax,texte), …]), …] — coords poppler, origine haut-gauche."""
    xml = subprocess.run(["pdftotext", "-bbox", pdf, "-"], capture_output=True, text=True).stdout
    pages = []
    for w, h, body in re.findall(r'<page width="([\d.]+)" height="([\d.]+)">(.*?)</page>', xml, re.S):
        words = [(float(a), float(b), float(c), float(d), t) for a, b, c, d, t in
                 re.findall(r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">([^<]*)</word>', body)]
        pages.append((float(w), float(h), words))
    return pages


def redact_pdf(src, dst):
    """Caviarde (bandes blanches) les éléments parasites des PDF FAQ :
    en-tête date/heure, titres « Explication vidéo/écrite », bloc de fin
    (« Mis à jour », feedback, « Vous ne trouvez pas », ©) et footer (URL + n° page)."""
    import io
    from pypdf import PdfReader, PdfWriter
    pages = _bbox_pages(src)
    r = PdfReader(src)
    w = PdfWriter()
    for idx, page in enumerate(r.pages):
        mb = page.mediabox
        x0, ytop = float(mb.left), float(mb.top)
        W, H = float(mb.width), float(mb.height)
        bands = []  # (a, b) en coords haut-gauche (a au-dessus de b)
        if idx < len(pages):
            pw, ph, words = pages[idx]
            sy = H / ph if ph else 1.0
            top = [(b * sy, d * sy, t.strip()) for (a, b, c, d, t) in words if b * sy < H * 0.20]
            rech = [d for (b, d, t) in top if t == "Rechercher"]
            if rech:                                              # masthead + barre de recherche
                bands.append((0, max(rech) + 22))
            elif any(_DATE_RE.search(t) or t in ("Aller", "FAQ") for (b, d, t) in top):
                bands.append((0, H * 0.085))                      # masthead (date) seul
            for a, b, c, d, t in words:
                if t.strip() == "Explication":                    # titres de section
                    bands.append((b * sy - 5, d * sy + 5))
                if "loom" in t.lower():                           # liens Loom (vidéo embarquée)
                    bands.append((b * sy - 5, d * sy + 5))
            mis = [b * sy for a, b, c, d, t in words if t.strip() == "Mis"]
            if mis:
                bands.append((min(mis) - 8, H))                   # bloc de fin -> bas
            bands.append((H - 30, H))                             # footer (URL + n° page)
        else:
            bands = [(0, H * 0.085), (H - 30, H)]
        buf = io.BytesIO()
        cv = canvas.Canvas(buf, pagesize=(W, H))
        cv.setFillColorRGB(1, 1, 1)
        for a, b in bands:
            a, b = max(0, a), min(H, b)
            if b > a:
                cv.rect(0, H - b, W, b - a, fill=1, stroke=0)
        cv.save(); buf.seek(0)
        ov = PdfReader(buf).pages[0]
        page.merge_transformed_page(ov, (1, 0, 0, 1, x0, ytop - H))
        w.add_page(page)
    with open(dst, "wb") as f:
        w.write(f)
    return dst


def resolve_path(rel, base):
    """Résout un chemin (relatif à `base`, séparateur '/') vers le fichier réel,
    en tolérant les différences d'encodage Unicode (NFC/NFD) sur les accents.
    Télécharge d'abord si c'est une URL http (ex. Supabase Storage)."""
    if isinstance(rel, str) and rel.startswith("http"):
        import urllib.request
        dst = os.path.join(tempfile.mkdtemp(), "article.pdf")
        urllib.request.urlretrieve(rel, dst)
        return dst
    if os.path.isabs(rel) and os.path.isfile(rel):
        return rel
    parts = [p for p in rel.replace("\\", "/").split("/") if p not in ("", ".")]
    cur = base
    for part in parts:
        if not os.path.isdir(cur):
            raise FileNotFoundError(cur)
        target = unicodedata.normalize("NFC", part)
        match = next((e for e in os.listdir(cur)
                      if unicodedata.normalize("NFC", e) == target), None)
        if match is None:
            raise FileNotFoundError(os.path.join(cur, part))
        cur = os.path.join(cur, match)
    if not os.path.isfile(cur):
        raise FileNotFoundError(cur)
    return cur


def build_parcours(cfg, base_dir="."):
    """Génère le PDF combiné. `articles` peut être absolu ou relatif à base_dir.
    Retourne le chemin de sortie (cfg['out'])."""
    resolved, missing = [], []
    for a in cfg["articles"]:
        try:
            resolved.append(resolve_path(a, base_dir))
        except FileNotFoundError:
            missing.append(a)
    if missing:
        raise FileNotFoundError("PDF article introuvable : " + " ; ".join(missing))
    if not resolved:
        raise ValueError("Aucun article à fusionner.")

    tmp = tempfile.mkdtemp()
    intro_pdf = os.path.join(tmp, "00_intro.pdf")
    c = canvas.Canvas(intro_pdf, pagesize=A4); _intro(c, cfg); c.save()
    concl_pdf = os.path.join(tmp, "zz_concl.pdf")
    c = canvas.Canvas(concl_pdf, pagesize=A4); _conclusion(c, cfg); c.save()

    if not shutil.which("pdfunite"):
        raise RuntimeError("pdfunite (poppler) introuvable : `brew install poppler`.")
    # caviarde l'en-tête (date/heure) de chaque article
    redacted = []
    for i, a in enumerate(resolved):
        try:
            rp = os.path.join(tmp, f"art_{i:02d}.pdf")
            redacted.append(redact_pdf(a, rp))
        except Exception:
            redacted.append(a)   # en cas d'échec, on garde l'original
    parts = [intro_pdf] + redacted + [concl_pdf]
    os.makedirs(os.path.dirname(cfg["out"]) or ".", exist_ok=True)
    subprocess.run(["pdfunite", *parts, cfg["out"]], check=True)
    return cfg["out"]


if __name__ == "__main__":
    cfg = json.load(open(sys.argv[1]))
    base = sys.argv[2] if len(sys.argv) > 2 else os.path.dirname(os.path.abspath(sys.argv[1]))
    out = build_parcours(cfg, base)
    print(f"PARCOURS PDF -> {out}  ({len(cfg['articles'])} articles + intro + conclusion)")
