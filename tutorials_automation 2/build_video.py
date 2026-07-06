#!/usr/bin/env python3
"""Build a narrated 1080p tutorial video from the Oplit exercise screenshots."""
import os, subprocess, json, textwrap
from PIL import Image, ImageDraw, ImageFont

# coordonnées des items de menu actifs (extraites du DOM par oplit_capture.py)
try:
    with open("/Users/mehdi/Desktop/tutorials_automation/build/menu_coords.json") as fh:
        MENU_COORDS = json.load(fh)
except FileNotFoundError:
    MENU_COORDS = {}
# rectangles à encadrer (onglet, menu, boutons) extraits du DOM
try:
    with open("/Users/mehdi/Desktop/tutorials_automation/build/highlights.json") as fh:
        HIGHLIGHTS_AUTO = json.load(fh)
except FileNotFoundError:
    HIGHLIGHTS_AUTO = {}
# mapping scène -> clé de capture live (correspond au mapping de make_tutorial.py)
SCENE_TO_LIVE = {
    1: "01_factory_structure",  2: "01_factory_structure",
    3: "03_sector_information", 4: "04_calendar",
    5: "05_sectors_groups",     6: "06_parameters_list",
    7: "07_add_parameter",      8: "08_calc_rule_general",
    9: "09_calc_rule_sector",  10: "10_duplicate",
    11: "08_calc_rule_general",12: "12_import_parsing",
    13: "13_import_data",
}

ROOT = "/Users/mehdi/Desktop/tutorials_automation"
SHOTS = os.environ.get("SHOTS_DIR", os.path.join(ROOT, "build/shots"))
OUT_NAME = os.environ.get("OUT_NAME", "Tutoriel_Oplit_chap1_Settings.mp4")
SLIDES = os.path.join(ROOT, "build/slides")
AUDIO = os.path.join(ROOT, "build/audio")
CLIPS = os.path.join(ROOT, "build/clips")
for d in (SLIDES, AUDIO, CLIPS):
    os.makedirs(d, exist_ok=True)

W, H = 1920, 1080
NAVY = (27, 42, 74)
NAVY_D = (14, 26, 43)
ACCENT = (124, 92, 255)   # violet, proche de l'UI Oplit
WHITE = (255, 255, 255)
GREY_BG = (244, 246, 250)
TEXT_DARK = (33, 43, 64)
FOOT_BG = (27, 42, 74)

AR = "/System/Library/Fonts/Supplemental/Arial.ttf"
ARB = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"

def font(path, size):
    return ImageFont.truetype(path, size)

# ------ curseur animé ------
CURSOR_PATH = os.path.join(ROOT, "build/cursor.png")
def make_cursor(path, size=64):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # pointeur classique, pointe au coin haut-gauche (0,0)
    pts = [(3, 3), (3, 46), (14, 35), (24, 56), (32, 53), (22, 32), (40, 32)]
    d.polygon(pts, fill=(255, 255, 255, 255))
    d.line(pts + [pts[0]], fill=(0, 0, 0, 255), width=3, joint="curve")
    img.save(path)
make_cursor(CURSOR_PATH)

# cible (fraction x, y du screenshot embarqué) pour chaque scène d'étape (1..13)
# 0,0 = coin haut-gauche du screenshot ; 1,1 = coin bas-droit
TARGETS = {
    1:  (0.30, 0.55),  # arbre de structure
    2:  (0.85, 0.32),  # niveau le plus à droite (création poste)
    3:  (0.45, 0.34),  # champ "Nom du secteur"
    4:  (0.45, 0.55),  # un jour du calendrier
    5:  (0.93, 0.13),  # bouton "Créer un groupe"
    6:  (0.93, 0.18),  # bouton "Ajouter un paramètre"
    7:  (0.45, 0.55),  # options du dropdown "Type de champ"
    8:  (0.92, 0.15),  # bouton "Créer une nouvelle règle"
    9:  (0.40, 0.40),  # formule de capacité
    10: (0.55, 0.55),  # cases à cocher de la modale "Dupliquer"
    11: (0.40, 0.27),  # dropdown "Choisissez une règle"
    12: (0.50, 0.50),  # ligne du tableau parsing
    13: (0.93, 0.16),  # bouton "Importer un fichier"
}
MOVE_DUR = 1.8  # secondes pour atteindre la cible

# Mini-scènes de navigation désactivées (base v5)
NAV_LABELS = {}
def nav_target_fraction(scene_idx):
    """(fx, fy) de l'item de menu actif pour la scène, depuis MENU_COORDS."""
    key = SCENE_TO_LIVE.get(scene_idx)
    c = MENU_COORDS.get(key) if key else None
    return (c["fx"], c["fy"]) if c else None
NAV_DUR = 2.6
CLICK_OFFSET = 4  # déplacement en px lors du "clic"
CLICK_HOLD = 0.15  # durée du clic enfoncé

# Encadrés magenta (façon PDF). Format de chaque rect : (fx0, fy0, fx1, fy1)
# fractions du screenshot. Pour les écrans à modale (extraits par oplit_capture_modals)
# les highlights auto ne sont pas dispos -> définis ici manuellement.
HIGHLIGHT_COLOR = (227, 30, 152, 255)
HIGHLIGHT_PAD = 10        # padding autour de l'élément (px image full-res)
HIGHLIGHT_WIDTH = 6
HIGHLIGHT_RADIUS = 14
MANUAL_HIGHLIGHTS = {}   # tout vient du DOM (capture) ; ajouter ici pour overrider

def _to_corners(r):
    if r is None:
        return None
    if isinstance(r, dict):
        return (r["fx"], r["fy"], r["fx"] + r["fw"], r["fy"] + r["fh"])
    return tuple(r)

def draw_highlights(image, rects):
    """Dessine des rectangles arrondis magenta autour des éléments listés."""
    if not rects:
        return
    d = ImageDraw.Draw(image, "RGBA")
    W, H = image.size
    for r in rects:
        c = _to_corners(r)
        if not c:
            continue
        fx0, fy0, fx1, fy1 = c
        x0 = int(fx0 * W) - HIGHLIGHT_PAD
        y0 = int(fy0 * H) - HIGHLIGHT_PAD
        x1 = int(fx1 * W) + HIGHLIGHT_PAD
        y1 = int(fy1 * H) + HIGHLIGHT_PAD
        d.rounded_rectangle([x0, y0, x1, y1], radius=HIGHLIGHT_RADIUS,
                            outline=HIGHLIGHT_COLOR, width=HIGHLIGHT_WIDTH)

def highlights_for_scene(scene_idx):
    """Compose la liste des rectangles à encadrer pour cette scène."""
    rects = []
    key = SCENE_TO_LIVE.get(scene_idx)
    auto = HIGHLIGHTS_AUTO.get(key) if key else None
    if auto:
        if auto.get("tab"):  rects.append(auto["tab"])
        if auto.get("menu"): rects.append(auto["menu"])
        for b in auto.get("buttons") or []:
            rects.append(b)
    rects.extend(MANUAL_HIGHLIGHTS.get(scene_idx, []))
    return rects

f_logo = font(ARB, 46)
f_step = font(ARB, 30)
f_title = font(ARB, 44)
f_foot = font(ARB, 34)
f_title_big = font(ARB, 84)
f_sub_big = font(AR, 44)

# (badge, titre, screenshot or None, narration, légende)
SCENES = [
    ("", "INTRO", None,
     "Bienvenue dans Oplit. Dans ce tutoriel, nous allons parcourir le chapitre 1 : la configuration, c'est-à-dire les Settings. "
     "Vous allez explorer la structure d'une usine, créer vos premiers éléments, et poser les bases d'une configuration propre et évolutive.",
     ""),
    ("Étape 1", "Structure de l'usine", "shot-01.png",
     "Rendez-vous dans Paramètres, Paramètres généraux, puis Structure de l'usine. Vérifiez la cohérence de l'architecture, niveau par niveau.",
     "Paramètres > Paramètres généraux > Structure de l'usine — vérifier l'architecture niveau par niveau"),
    ("Étape 1", "Créer un poste de charge", "shot-02.png",
     "Pour créer un poste de charge au niveau le plus bas, cliquez sur l'emplacement souhaité, puis sur le bouton plus. Une fois le poste créé, vous pouvez le supprimer.",
     "Cliquer sur l'emplacement, puis « + » pour créer un poste de charge (puis le supprimer)"),
    ("Étape 2", "Informations du secteur", "shot-03.png",
     "Dans Paramètres par secteur, ouvrez Informations du secteur. Vérifiez la cohérence des données de chaque secteur : l'identifiant ERP, le nom, et l'unité.",
     "Paramètres par secteur > Informations du secteur — vérifier erp_id, nom, unité"),
    ("Étape 3", "Calendrier d'ouverture", "shot-04.png",
     "Toujours dans Paramètres par secteur, ouvrez le Calendrier et définissez le calendrier d'ouverture de votre usine. Au niveau le plus haut, fermer ou ouvrir des jours impacte toute l'usine. Pour un secteur précis, rendez-vous directement dessus.",
     "Paramètres par secteur > Calendrier — définir l'ouverture (niveau haut = toute l'usine)"),
    ("Étape 4", "Groupes de secteurs", "shot-05.png",
     "Dans Paramètres généraux, créez un groupe de secteurs. Cela permet de sélectionner en un seul clic les secteurs dont vous avez besoin. Cette fonction est surtout utile pour le module d'ordonnancement.",
     "Paramètres généraux > Groupes de secteurs — sélectionner plusieurs secteurs en un clic"),
    ("Étape 5", "Liste de paramètres", "shot-06.png",
     "Ouvrez la Liste de paramètres. Vous y définissez les paramètres qui serviront de base à vos règles de calcul de capacité : nombre d'équipes, nombre de machines, durée de shift, et d'autres si nécessaire.",
     "Paramètres généraux > Liste de paramètres — nb équipes, nb machines, durée de shift…"),
    ("Étape 5", "Type de champ", "shot-07.png",
     "Pour chaque paramètre, choisissez le type de champ adapté : nombre, pourcentage, ou liste déroulante. Par exemple pour la durée de shift : un nombre si elle est constante, une liste déroulante si vous avez plusieurs équipes, comme du 1x8, 2x8 ou 3x8.",
     "Type de champ : nombre, pourcentage ou liste déroulante (ex. shift 1x8 / 2x8 / 3x8)"),
    ("Étape 6", "Règle de calcul de capacité", "shot-08.png",
     "Dans Paramètres généraux, ouvrez Règle de calcul et créez votre règle de capacité. Utilisez la formule : heures d'ouverture égale nombre d'équipes, multiplié par nombre de machines, multiplié par durée standard d'un shift.",
     "Heures d'ouverture = Nb équipes × Nb machines × Durée standard d'un shift"),
    ("Étape 7", "Affecter la règle aux postes", "shot-09.png",
     "Dans Paramètres par secteur, ouvrez Règle de calcul, et affectez la règle adaptée à chaque poste de charge, uniquement au niveau le plus bas. Vous pouvez ajuster les paramètres pour coller au plus près de chaque poste.",
     "Paramètres par secteur > Règle de calcul — affecter au niveau le plus bas uniquement"),
    ("Étape 8", "Dupliquer la règle", "shot-10.png",
     "Dupliquez la règle sur plusieurs postes, via les trois points à droite. Sélectionnez les paramètres communs, comme la durée de shift, puis les postes concernés. Attention : appliquez la règle uniquement aux postes du niveau le plus bas.",
     "Dupliquer via les « ⋮ » — choisir les paramètres communs, puis les postes (niveaux bas)"),
    ("Étape 9", "Niveau parent", "shot-11.png",
     "Affectez maintenant une règle au niveau parent, juste au-dessus de vos postes les plus bas. Le calcul correspond généralement à : somme égale niveaux inférieurs.",
     "Niveau parent — règle d'agrégation : somme = niveaux inférieurs"),
    ("Étape 10", "Mapping des imports", "shot-12.png",
     "Dans Imports, ouvrez Paramétrage des imports. Cette page gère le mapping de vos fichiers de charge et de production. Vérifiez les éléments du tableau, ajoutez un identifiant avec le bouton dédié, puis supprimez-le.",
     "Imports > Paramétrage des imports — mapping charge/production ; ajouter un identifiant puis le supprimer"),
    ("Étape 11", "Import des données", "shot-13.png",
     "Enfin, dans Imports, ouvrez Import de données. Importez un fichier de charge et un fichier de production. Si des lignes sont ignorées, cliquez sur le i de la colonne dédiée pour les analyser. L'erreur la plus fréquente : un identifiant ERP ignoré.",
     "Imports > Import de données — importer charge + production ; vérifier les lignes ignorées (erp_id)"),
    ("", "OUTRO", None,
     "Voilà, vous avez terminé le chapitre 1 : Settings. Votre environnement est prêt pour la visite sur site. À très bientôt avec Oplit !",
     ""),
]

def wrap_lines(draw, text, fnt, max_w):
    words = text.split()
    lines, cur = [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if draw.textlength(test, font=fnt) <= max_w:
            cur = test
        else:
            lines.append(cur); cur = w
    if cur:
        lines.append(cur)
    return lines

def draw_wrapped(draw, text, fnt, fill, cx, top, max_w, line_h, anchor_center=True):
    lines = wrap_lines(draw, text, fnt, max_w)
    y = top
    for ln in lines:
        if anchor_center:
            tw = draw.textlength(ln, font=fnt)
            draw.text((cx - tw/2, y), ln, font=fnt, fill=fill)
        else:
            draw.text((cx, y), ln, font=fnt, fill=fill)
        y += line_h
    return y

def make_title_slide(path, title, subtitle):
    img = Image.new("RGB", (W, H), NAVY_D)
    d = ImageDraw.Draw(img)
    cx = W//2
    # logo circle
    d.ellipse([cx-44, 300-44, cx+44, 300+44], outline=WHITE, width=8)
    tw = d.textlength("Oplit", font=f_title_big)
    d.text((cx - tw/2, 360), "Oplit", font=f_title_big, fill=WHITE)
    # accent bar above the title
    d.rectangle([cx-260, 520, cx+260, 524], fill=ACCENT)
    draw_wrapped(d, title, f_title_big, WHITE, cx, 560, 1500, 96)
    draw_wrapped(d, subtitle, f_sub_big, (180, 195, 220), cx, 740, 1400, 56)
    img.save(path)

def make_step_slide(path, badge, title, shot, caption, highlights=None):
    img = Image.new("RGB", (W, H), GREY_BG)
    d = ImageDraw.Draw(img)
    # header
    d.rectangle([0, 0, W, 150], fill=NAVY)
    d.ellipse([40, 75-26, 92, 75+26], outline=WHITE, width=5)
    d.text((110, 50), "Oplit", font=f_logo, fill=WHITE)
    # badge
    bx0 = 360
    bw = d.textlength(badge, font=f_step) + 50
    d.rounded_rectangle([bx0, 52, bx0+bw, 100], radius=24, fill=ACCENT)
    d.text((bx0+25, 58), badge, font=f_step, fill=WHITE)
    # title
    d.text((bx0+bw+30, 53), title, font=f_title, fill=WHITE)
    # subtitle band (no voiceover — the narration text is shown here),
    # height auto-fits the number of wrapped lines
    LH = 50
    lines = wrap_lines(d, caption, f_foot, 1740)
    FOOT_H = max(140, len(lines) * LH + 56)
    fy0 = H - FOOT_H
    d.rectangle([0, fy0, W, H], fill=NAVY)
    d.rectangle([0, fy0, W, fy0+5], fill=ACCENT)
    text_block_h = len(lines) * LH
    draw_wrapped(d, caption, f_foot, WHITE, W//2,
                 fy0 + (FOOT_H - text_block_h)//2, 1740, LH)
    # screenshot area (between header and footer)
    s = Image.open(os.path.join(SHOTS, shot)).convert("RGB")
    if highlights:
        draw_highlights(s, highlights)   # dessiné en pleine résolution avant resize
    top, bottom = 150, fy0
    avail_w, avail_h = 1740, (bottom - top) - 40
    ratio = min(avail_w/s.width, avail_h/s.height)
    nw, nh = int(s.width*ratio), int(s.height*ratio)
    s = s.resize((nw, nh), Image.LANCZOS)
    ox, oy = (W-nw)//2, top + ((bottom - top) - nh)//2
    d.rectangle([ox-3, oy-3, ox+nw+3, oy+nh+3], outline=(210, 216, 228), width=3)
    img.paste(s, (ox, oy))
    img.save(path)
    return ox, oy, nw, nh

# duration of a media file via ffprobe
def dur(path):
    out = subprocess.check_output([
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_format", path])
    return float(json.loads(out)["format"]["duration"])

# reading-time based duration (no voiceover): ~2.6 words/sec, with margins
def read_time(text):
    n = len(text.split())
    return round(min(16.0, max(4.5, 1.8 + n / 2.6)), 1)

CX, CY = W // 2, H // 2  # point de départ du curseur (centre)

def build_clip(slide_path, duration, target_xy=None, click=False, out=None):
    """Encode un clip d'une slide ; si target_xy, le curseur va du centre à la cible."""
    if target_xy is None:
        subprocess.run([
            "ffmpeg", "-y", "-loop", "1", "-i", slide_path, "-t", str(duration),
            "-c:v", "libx264", "-tune", "stillimage", "-pix_fmt", "yuv420p",
            "-r", "25", "-vf", f"scale={W}:{H}", out
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return
    tx, ty = target_xy
    # ease-out cubique pendant MOVE_DUR, puis "clic" (léger déplacement) si demandé
    if click:
        ex = (f"if(lt(t,{MOVE_DUR}),{CX}+({tx}-{CX})*(1-pow(1-t/{MOVE_DUR},3)),"
              f"if(lt(t,{MOVE_DUR}+{CLICK_HOLD}),{tx}+{CLICK_OFFSET},{tx}))")
        ey = (f"if(lt(t,{MOVE_DUR}),{CY}+({ty}-{CY})*(1-pow(1-t/{MOVE_DUR},3)),"
              f"if(lt(t,{MOVE_DUR}+{CLICK_HOLD}),{ty}+{CLICK_OFFSET},{ty}))")
    else:
        ex = f"if(lt(t,{MOVE_DUR}),{CX}+({tx}-{CX})*(1-pow(1-t/{MOVE_DUR},3)),{tx})"
        ey = f"if(lt(t,{MOVE_DUR}),{CY}+({ty}-{CY})*(1-pow(1-t/{MOVE_DUR},3)),{ty})"
    subprocess.run([
        "ffmpeg", "-y",
        "-loop", "1", "-i", slide_path,
        "-loop", "1", "-i", CURSOR_PATH,
        "-filter_complex", f"[0:v][1:v]overlay=x='{ex}':y='{ey}':eval=frame[v]",
        "-map", "[v]", "-t", str(duration),
        "-c:v", "libx264", "-tune", "stillimage", "-pix_fmt", "yuv420p", "-r", "25",
        out
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

clip_list = []
for i, (badge, title, shot, narration, caption) in enumerate(SCENES):
    slide = os.path.join(SLIDES, f"slide-{i:02d}.png")
    rect = None
    if shot is None:
        sub = ("Chapitre 1 : Settings  ·  Exercice avant la visite sur site"
               if title == "INTRO" else "Configuration terminée  ·  Merci !")
        tt = ("Tutoriel — Paramétrage" if title == "INTRO" else "Chapitre 1 terminé")
        make_title_slide(slide, tt, sub)
    else:
        rect = make_step_slide(slide, badge, title, shot, narration,
                               highlights=highlights_for_scene(i))

    # --- Mini-scène de navigation avant cette étape (si concernée) ---
    if rect and i in NAV_LABELS:
        nav_frac = nav_target_fraction(i)
        nav_cap = NAV_LABELS[i]
        nav_slide = os.path.join(SLIDES, f"slide-{i:02d}_nav.png")
        nav_rect = make_step_slide(nav_slide, "Naviguer", nav_cap, shot,
                                   f"→ {nav_cap}")
        nox, noy, nnw, nnh = nav_rect
        if nav_frac is None:
            print(f"  nav -> {i}: pas de coord DOM, scène ignorée")
        else:
            nav_target = (nox + nav_frac[0] * nnw, noy + nav_frac[1] * nnh)
            nav_clip = os.path.join(CLIPS, f"clip-{i:02d}_nav.mp4")
            build_clip(nav_slide, NAV_DUR, target_xy=nav_target, click=True, out=nav_clip)
            clip_list.append(nav_clip)
            print(f"  nav -> {i}: '{nav_cap}' ({NAV_DUR}s, clic) @ ({nav_frac[0]:.3f},{nav_frac[1]:.3f})")

    d_scene = read_time(narration)
    clip = os.path.join(CLIPS, f"clip-{i:02d}.mp4")
    target = TARGETS.get(i) if rect else None
    target_xy = None
    if target and rect:
        ox, oy, nw, nh = rect
        target_xy = (ox + target[0] * nw, oy + target[1] * nh)
    build_clip(slide, d_scene, target_xy=target_xy, click=False, out=clip)
    clip_list.append(clip)
    print(f"scene {i}: '{title}' -> {d_scene}s {'+ souris' if target_xy else ''}")

# concat
listfile = os.path.join(ROOT, "build/clips.txt")
with open(listfile, "w") as fh:
    for c in clip_list:
        fh.write(f"file '{c}'\n")

out = os.path.join(ROOT, OUT_NAME)
subprocess.run([
    "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", listfile,
    "-c", "copy", out
], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
print("DONE ->", out)
print("Total duration:", round(dur(out), 1), "s")
