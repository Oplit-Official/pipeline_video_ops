#!/usr/bin/env python3
"""Moteur générique de tutoriels vidéo Oplit (1080p), piloté par un spec JSON.

Réutilise le style validé : slides navy/violet, sous-titres karaoké jaune
(balayage continu) calés sur une voix off macOS (mutée par défaut, mais
synthétisée pour le timing), curseur animé + onde de clic positionnés
automatiquement sur l'encadré magenta déjà présent dans la capture FAQ.

Usage:  python3 make_helpdesk_video.py /chemin/spec.json
Spec JSON:
{
  "out":   "/abs/video.mp4",
  "work":  "/abs/_work",
  "scenes": [
    {"badge":"", "title":"Tutoriel — X", "shot":null,
     "subtitle":"…", "narration":"Bienvenue …"},
    {"badge":"Étape 1","title":"…","shot":"/abs/shot-01.png","narration":"…"},
    {"badge":"", "title":"Tutoriel terminé","shot":null,
     "subtitle":"…","narration":"Voilà …"}
  ]
}
"""
import os, sys, json, subprocess, base64, urllib.request, hashlib
import numpy as np
from scipy import ndimage
from PIL import Image, ImageDraw, ImageFont

SPEC = json.load(open(sys.argv[1]))
OUT = SPEC["out"]
WORK = SPEC["work"]
SCENES = SPEC["scenes"]
SLIDES = os.path.join(WORK, "slides")
CLIPS = os.path.join(WORK, "clips")
STATES = os.path.join(WORK, "states")
AUDIO = os.path.join(WORK, "audio")
for d in (SLIDES, CLIPS, STATES, AUDIO):
    os.makedirs(d, exist_ok=True)

W, H, FPS = 1920, 1080, 30
NAVY, NAVY_D = (27, 42, 74), (14, 26, 43)
ACCENT, WHITE, GREY_BG = (124, 92, 255), (255, 255, 255), (244, 246, 250)
AR = "/System/Library/Fonts/Supplemental/Arial.ttf"
ARB = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
def font(p, s): return ImageFont.truetype(p, s)
f_logo, f_step, f_title = font(ARB, 46), font(ARB, 30), font(ARB, 44)
f_foot, f_title_big, f_sub_big = font(ARB, 34), font(ARB, 84), font(AR, 44)

VOICE = os.environ.get("VOICE", "Thomas")
VOICE_RATE = 178
END_PAD = 1.0
MUTE = os.environ.get("MUTE", "1") != "0"

# Backend voix : "say" (macOS, par défaut) ou "eleven" (ElevenLabs + timestamps mot).
TTS = os.environ.get("TTS", "say")
def _eleven_key():
    k = os.environ.get("ELEVENLABS_API_KEY")
    if not k:
        kf = os.path.expanduser("~/.config/elevenlabs/key")
        if os.path.exists(kf):
            k = open(kf).read().strip()
    return k
ELEVEN_KEY = _eleven_key()
# Paul K — voix masculine FRANÇAISE NATIVE, spéciale e-learning/formation + multilingual_v2.
# Voix native -> pas besoin de forcer language_code (et multilingual_v2 l'ignore).
ELEVEN_VOICE_ID = os.environ.get("ELEVEN_VOICE_ID", "0igQGE0lbNpTaWsexf1r")
ELEVEN_MODEL = os.environ.get("ELEVEN_MODEL", "eleven_multilingual_v2")
ELEVEN_LANG = os.environ.get("ELEVEN_LANG", "")     # vide = pas de forçage

# karaoké
FOOT_LH = 50
KARA_DIM, KARA_LIT = (150, 140, 70), (255, 210, 30)
KARA_LEAD = 0.15
_scratch = ImageDraw.Draw(Image.new("RGB", (8, 8)))

# curseur + anneaux de clic
MOVE_DUR, CLICK_T, CLICK_DIP = 1.8, 1.8, 3
RING_N, RING_STEP, RING_HOLD = 3, 0.10, 0.18
RING_SIZES = [44, 76, 112]
CX, CY = W // 2, H // 2

CURSOR_PATH = os.path.join(WORK, "cursor.png")
def make_cursor(path, size=64):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    pts = [(3, 3), (3, 46), (14, 35), (24, 56), (32, 53), (22, 32), (40, 32)]
    d.polygon(pts, fill=(255, 255, 255, 255))
    d.line(pts + [pts[0]], fill=(0, 0, 0, 255), width=3, joint="curve")
    img.save(path)
make_cursor(CURSOR_PATH)

RING_PATHS = []
for i, sz in enumerate(RING_SIZES):
    p = os.path.join(WORK, f"ring{i}.png")
    im = Image.new("RGBA", (sz, sz), (0, 0, 0, 0))
    ImageDraw.Draw(im).ellipse([4, 4, sz-4, sz-4], outline=(124, 92, 255, max(60, 240-i*70)), width=5)
    im.save(p); RING_PATHS.append(p)

# ---------- détection auto de la cible (encadré magenta de la FAQ) ----------
def detect_target(shot_path):
    """Centre (fx, fy) de l'encadré magenta le PLUS marquant, ou None si absent.

    La FAQ numérote parfois plusieurs éléments (1, 2, 3) : viser la médiane de
    tous les pixels placerait le curseur « entre » les marques. On isole donc
    les taches magenta (composantes connexes), et on vise le centre de la plus
    grosse (cercle/encadré principal) — un seul élément, jamais l'entre-deux.
    """
    a = np.asarray(Image.open(shot_path).convert("RGB")).astype(int)
    R, G, B = a[:, :, 0], a[:, :, 1], a[:, :, 2]
    m = (R > 200) & (B > 200) & (G < 150) & (R - G > 90)
    if m.sum() < 300:
        return None
    h, w = m.shape
    md = ndimage.binary_dilation(m, iterations=6)   # relie un encadré à son n°
    lbl, n = ndimage.label(md)
    if n == 0:
        return None
    sizes = ndimage.sum(m, lbl, range(1, n + 1))    # aire magenta réelle / tache
    k = int(np.argmax(sizes)) + 1
    ys, xs = np.where(lbl == k)
    return ((xs.min() + xs.max()) / 2 / w, (ys.min() + ys.max()) / 2 / h)

# ---------- texte ----------
def wrap_lines(draw, text, fnt, max_w):
    words, lines, cur = text.split(), [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if draw.textlength(test, font=fnt) <= max_w:
            cur = test
        else:
            lines.append(cur); cur = w
    if cur:
        lines.append(cur)
    return lines

def draw_wrapped(draw, text, fnt, fill, cx, top, max_w, line_h):
    y = top
    for ln in wrap_lines(draw, text, fnt, max_w):
        tw = draw.textlength(ln, font=fnt)
        draw.text((cx - tw/2, y), ln, font=fnt, fill=fill)
        y += line_h
    return y

def foot_layout_lines(caption):
    lines = wrap_lines(_scratch, caption, f_foot, 1740)
    foot_h = max(140, len(lines) * FOOT_LH + 56)
    return lines, foot_h

def footer_layout(lines, foot_h):
    space = _scratch.textlength(" ", font=f_foot)
    fy0 = H - foot_h
    y = fy0 + (foot_h - len(lines) * FOOT_LH) // 2
    boxes = []
    for ln in lines:
        words = ln.split()
        widths = [_scratch.textlength(w, font=f_foot) for w in words]
        total = sum(widths) + space * (len(words) - 1)
        x = W/2 - total/2
        for w, wd in zip(words, widths):
            boxes.append((x, y, w, wd)); x += wd + space
        y += FOOT_LH
    return boxes

# ---------- slides ----------
def render_title_base(title, subtitle, foot_h):
    """Carton de titre + bandeau karaoké réservé en bas (texte ajouté frame/frame)."""
    img = Image.new("RGB", (W, H), NAVY_D); d = ImageDraw.Draw(img); cx = W//2
    ah = H - foot_h                       # zone titre (au-dessus du bandeau)
    cyl = int(ah * 0.30)                  # centre du logo
    d.ellipse([cx-44, cyl-44, cx+44, cyl+44], outline=WHITE, width=8)
    tw = d.textlength("Oplit", font=f_title_big)
    d.text((cx - tw/2, cyl + 56), "Oplit", font=f_title_big, fill=WHITE)
    by = int(ah * 0.60)
    d.rectangle([cx-260, by, cx+260, by+4], fill=ACCENT)
    draw_wrapped(d, title, f_title_big, WHITE, cx, by + 28, 1500, 96)
    if subtitle:
        draw_wrapped(d, subtitle, f_sub_big, (180, 195, 220), cx, int(ah*0.84), 1400, 56)
    fy0 = H - foot_h                      # bandeau bas (même style que les étapes)
    d.rectangle([0, fy0, W, H], fill=NAVY)
    d.rectangle([0, fy0, W, fy0+5], fill=ACCENT)
    return img

# encadré rose (style FAQ) dessiné par nous sur les captures live (propres)
HL_COLOR, HL_PAD, HL_WIDTH, HL_RADIUS = (236, 0, 180, 255), 10, 6, 16
def draw_box(img, box):
    """Trace un rectangle arrondi magenta autour de box=(fx,fy,fw,fh) (fractions)."""
    d = ImageDraw.Draw(img, "RGBA"); iw, ih = img.size
    fx, fy, fw, fh = box
    x0, y0 = int(fx*iw) - HL_PAD, int(fy*ih) - HL_PAD
    x1, y1 = int((fx+fw)*iw) + HL_PAD, int((fy+fh)*ih) + HL_PAD
    d.rounded_rectangle([x0, y0, x1, y1], radius=HL_RADIUS, outline=HL_COLOR, width=HL_WIDTH)

def render_base_slide(badge, title, shot, foot_h, highlight=None):
    img = Image.new("RGB", (W, H), GREY_BG); d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 150], fill=NAVY)
    d.ellipse([40, 49, 92, 101], outline=WHITE, width=5)
    d.text((110, 50), "Oplit", font=f_logo, fill=WHITE)
    bx0 = 360
    if badge:
        bw = d.textlength(badge, font=f_step) + 50
        d.rounded_rectangle([bx0, 52, bx0+bw, 100], radius=24, fill=ACCENT)
        d.text((bx0+25, 58), badge, font=f_step, fill=WHITE)
        tx = bx0 + bw + 30
    else:
        tx = bx0
    d.text((tx, 53), title, font=f_title, fill=WHITE)
    fy0 = H - foot_h
    d.rectangle([0, fy0, W, H], fill=NAVY)
    d.rectangle([0, fy0, W, fy0+5], fill=ACCENT)
    s = Image.open(shot).convert("RGB")
    if highlight:
        draw_box(s, highlight)             # encadré rose en pleine résolution
    top, bottom = 150, fy0
    avail_w, avail_h = 1740, (bottom - top) - 40
    ratio = min(avail_w/s.width, avail_h/s.height)
    nw, nh = int(s.width*ratio), int(s.height*ratio)
    s = s.resize((nw, nh), Image.LANCZOS)
    ox, oy = (W-nw)//2, top + ((bottom - top) - nh)//2
    d.rectangle([ox-3, oy-3, ox+nw+3, oy+nh+3], outline=(210, 216, 228), width=3)
    img.paste(s, (ox, oy))
    return img, (ox, oy, nw, nh)

def make_dim_footer(base, boxes):
    img = base.copy(); d = ImageDraw.Draw(img)
    for x, y, w, _ in boxes:
        d.text((x, y), w, font=f_foot, fill=KARA_DIM)
    return img

def draw_footer_continuous(dim_base, boxes, cur, frac):
    img = dim_base.copy(); d = ImageDraw.Draw(img)
    for j, (x, y, w, wd) in enumerate(boxes):
        if j < cur:
            d.text((x, y), w, font=f_foot, fill=KARA_LIT)
        elif j == cur and frac > 0:
            cutw = max(1, int(round(frac * wd)))
            tile = Image.new("RGBA", (int(wd) + 2, FOOT_LH), (0, 0, 0, 0))
            ImageDraw.Draw(tile).text((0, 0), w, font=f_foot, fill=KARA_LIT)
            crop = tile.crop((0, 0, cutw, FOOT_LH))
            img.paste(crop, (int(round(x)), y), crop)
    return img

# ---------- audio / durées ----------
def dur(path):
    out = subprocess.check_output(["ffprobe", "-v", "quiet", "-print_format",
                                   "json", "-show_format", path])
    return float(json.loads(out)["format"]["duration"])

def say_synth(idx, text):
    aiff = os.path.join(AUDIO, f"sc-{idx:02d}.aiff")
    subprocess.run(["say", "-v", VOICE, "-r", str(VOICE_RATE), "-o", aiff, text],
                   check=True)
    return aiff, dur(aiff), None   # pas de timing mot -> proportionnel

ELEVEN_CACHE = os.path.expanduser("~/.cache/oplit_eleven")

def _spans_from_alignment(al):
    chars = al.get("characters", [])
    st = al.get("character_start_times_seconds", [])
    en = al.get("character_end_times_seconds", [])
    spans, cur = [], None
    for ch, a, b in zip(chars, st, en):
        if ch.isspace():
            if cur: spans.append(tuple(cur)); cur = None
        else:
            cur = [a, b] if cur is None else [cur[0], b]
    if cur:
        spans.append(tuple(cur))
    return spans

def eleven_synth(idx, text):
    """ElevenLabs avec timestamps : renvoie (mp3, durée, spans mot exacts).
    Mis en cache par (voix, modèle, texte) -> pas de re-conso de crédits en itérant."""
    os.makedirs(ELEVEN_CACHE, exist_ok=True)
    key = hashlib.md5(f"{ELEVEN_VOICE_ID}|{ELEVEN_MODEL}|{ELEVEN_LANG}|{text}".encode()).hexdigest()
    cmp3 = os.path.join(ELEVEN_CACHE, key + ".mp3")
    cjson = os.path.join(ELEVEN_CACHE, key + ".json")
    if os.path.exists(cmp3) and os.path.exists(cjson):
        spans = json.load(open(cjson))
        return cmp3, dur(cmp3), [tuple(s) for s in spans]
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVEN_VOICE_ID}/with-timestamps"
    payload = {"text": text, "model_id": ELEVEN_MODEL,
               "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}}
    if ELEVEN_LANG:
        payload["language_code"] = ELEVEN_LANG   # honoré par turbo_v2_5 / flash_v2_5
    body = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=body, method="POST", headers={
        "xi-api-key": ELEVEN_KEY, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        data = json.load(r)
    with open(cmp3, "wb") as f:
        f.write(base64.b64decode(data["audio_base64"]))
    spans = _spans_from_alignment(data.get("alignment") or {})
    json.dump(spans, open(cjson, "w"))
    return cmp3, dur(cmp3), spans

def synth(idx, text):
    if TTS == "eleven" and ELEVEN_KEY:
        return eleven_synth(idx, text)
    return say_synth(idx, text)

def _word_times(toks, speak_dur, word_spans=None):
    # timing exact (ElevenLabs) si dispo et cohérent, sinon proportionnel
    if word_spans and len(word_spans) == len(toks):
        return list(word_spans)
    weights = [len(w) + 1 for w in toks]
    span = max(0.1, speak_dur - KARA_LEAD)
    t, spans = KARA_LEAD, []
    for wt in weights:
        d = span * wt / sum(weights)
        spans.append((t, t + d)); t += d
    return spans

# ---------- clips ----------
_base_input = lambda p, v: (["-i", p] if v else ["-loop", "1", "-i", p])
# normalise le niveau (voix ElevenLabs sort bas) PUIS comble de silence jusqu'à
# la fin de la scène (apad) : sans ça l'audio (plus court que la vidéo à cause
# d'END_PAD) prend de l'avance à chaque scène lors du concat -c copy.
AUDIO_ARGS = ["-af", "loudnorm=I=-16:TP=-1.5:LRA=11,apad",
              "-c:a", "aac", "-b:a", "160k", "-ar", "44100", "-ac", "2"]

def render_karaoke_video(idx, base, boxes, spans, duration):
    """Encode la vidéo de fond : balayage karaoké continu calé sur `spans`."""
    dim_base = make_dim_footer(base, boxes)
    sdir = os.path.join(STATES, f"scene-{idx:02d}"); os.makedirs(sdir, exist_ok=True)
    base_mp4 = os.path.join(sdir, "base.mp4")
    nframes = max(1, int(round(duration * FPS)))
    proc = subprocess.Popen(
        ["ffmpeg", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
         "-r", str(FPS), "-i", "-", "-an", "-vframes", str(nframes),
         "-c:v", "libx264", "-pix_fmt", "yuv420p", base_mp4],
        stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    last = len(spans)
    for f in range(nframes):
        t = f / FPS
        if not spans or t >= spans[-1][1]:
            cur, frac = last, 0.0          # tout lu
        elif t < spans[0][0]:
            cur, frac = 0, 0.0             # rien encore
        else:
            # gère les SILENCES entre mots (ElevenLabs) : si t tombe dans un trou
            # après le mot j-1, on garde j-1 mots allumés (pas de saut « tout allumé »)
            cur, frac = last, 0.0
            for j, (t0, t1) in enumerate(spans):
                if t < t0:                 # trou avant le mot j : j mots déjà lus
                    cur, frac = j, 0.0; break
                if t0 <= t < t1:           # en cours de remplissage du mot j
                    cur, frac = j, (t - t0) / (t1 - t0); break
                cur = j + 1                # mot j terminé
        proc.stdin.write(draw_footer_continuous(dim_base, boxes, cur, frac).tobytes())
    proc.stdin.close(); proc.wait()
    return base_mp4

def build_karaoke_base(idx, badge, title, shot, caption, duration, speak_dur,
                       word_spans=None, highlight=None):
    lines, foot_h = foot_layout_lines(caption)
    base, rect = render_base_slide(badge, title, shot, foot_h, highlight=highlight)
    boxes = footer_layout(lines, foot_h)
    toks = [w for _, _, w, _ in boxes]
    spans = _word_times(toks, speak_dur, word_spans)
    return render_karaoke_video(idx, base, boxes, spans, duration), rect

def build_title_karaoke(idx, title, subtitle, narration, duration, speak_dur, word_spans=None):
    """Carton de titre AVEC sous-titres karaoké (intro / outro)."""
    lines, foot_h = foot_layout_lines(narration)
    base = render_title_base(title, subtitle, foot_h)
    boxes = footer_layout(lines, foot_h)
    toks = [w for _, _, w, _ in boxes]
    spans = _word_times(toks, speak_dur, word_spans)
    return render_karaoke_video(idx, base, boxes, spans, duration)

def build_clip(base_path, duration, target_xy=None, out=None,
               base_is_video=False, audio_path=None):
    if target_xy is None:
        cmd = ["ffmpeg", "-y", *_base_input(base_path, base_is_video)]
        if audio_path: cmd += ["-i", audio_path]
        cmd += ["-map", "0:v"]
        if audio_path: cmd += ["-map", "1:a", *AUDIO_ARGS]
        cmd += ["-t", str(duration), "-c:v", "libx264", "-tune", "stillimage",
                "-pix_fmt", "yuv420p", "-r", str(FPS), "-vf", f"scale={W}:{H}", out]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return
    tx, ty = target_xy
    dip = f"if(between(t,{CLICK_T},{CLICK_T}+0.12),{CLICK_DIP},0)"
    ex = f"if(lt(t,{MOVE_DUR}),{CX}+({tx}-{CX})*(1-pow(1-t/{MOVE_DUR},3)),{tx}+{dip})"
    ey = f"if(lt(t,{MOVE_DUR}),{CY}+({ty}-{CY})*(1-pow(1-t/{MOVE_DUR},3)),{ty}+{dip})"
    parts = [f"[0:v][1:v]overlay=x='{ex}':y='{ey}':eval=frame[v0]"]
    for k in range(RING_N):
        x, y = int(tx - RING_SIZES[k]/2), int(ty - RING_SIZES[k]/2)
        start = CLICK_T + k * RING_STEP
        parts.append(f"[v{k}][{2+k}:v]overlay=x={x}:y={y}:"
                     f"enable='between(t,{start:.3f},{start+RING_HOLD:.3f})'[v{k+1}]")
    cmd = ["ffmpeg", "-y", *_base_input(base_path, base_is_video),
           "-loop", "1", "-i", CURSOR_PATH]
    for p in RING_PATHS:
        cmd += ["-loop", "1", "-i", p]
    audio_idx = 2 + RING_N
    if audio_path: cmd += ["-i", audio_path]
    cmd += ["-filter_complex", ";".join(parts), "-map", f"[v{RING_N}]"]
    if audio_path: cmd += ["-map", f"{audio_idx}:a", *AUDIO_ARGS]
    cmd += ["-t", str(duration), "-c:v", "libx264", "-tune", "stillimage",
            "-pix_fmt", "yuv420p", "-r", str(FPS), out]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

# ---------- montage ----------
clip_list = []
for i, sc in enumerate(SCENES):
    badge = sc.get("badge", "")
    title = sc["title"]
    shot = sc.get("shot")
    narration = sc["narration"]
    audio, adur, spans = synth(i, narration)
    if MUTE:
        audio = None
    d_scene = round(adur + END_PAD, 2)
    clip = os.path.join(CLIPS, f"clip-{i:02d}.mp4")
    if not shot:
        base_mp4 = build_title_karaoke(i, title, sc.get("subtitle", ""),
                                       narration, d_scene, adur, word_spans=spans)
        build_clip(base_mp4, d_scene, target_xy=None, out=clip,
                   base_is_video=True, audio_path=audio)
        print(f"scene {i}: '{title}' -> {d_scene}s (titre + karaoké)")
    else:
        hl = sc.get("highlight")           # {fx,fy,fw,fh} rect DOM (captures live)
        hl_box = (hl["fx"], hl["fy"], hl["fw"], hl["fh"]) if hl else None
        base_mp4, (ox, oy, nw, nh) = build_karaoke_base(
            i, badge, title, shot, narration, d_scene, adur,
            word_spans=spans, highlight=hl_box)
        # cible curseur : centre de l'encadré -> sinon "target" -> sinon magenta
        if hl_box:
            tgt = (hl_box[0] + hl_box[2]/2, hl_box[1] + hl_box[3]/2)
        elif sc.get("target"):
            tgt = (sc["target"]["fx"], sc["target"]["fy"])
        else:
            tgt = detect_target(shot)
        target_xy = (ox + tgt[0] * nw, oy + tgt[1] * nh) if tgt else None
        build_clip(base_mp4, d_scene, target_xy=target_xy, out=clip,
                   base_is_video=True, audio_path=audio)
        print(f"scene {i}: '{title}' -> {d_scene}s "
              f"{'+ curseur' if target_xy else '(sans curseur)'} + karaoké")
    clip_list.append(clip)

listfile = os.path.join(WORK, "clips.txt")
with open(listfile, "w") as fh:
    for c in clip_list:
        fh.write(f"file '{c}'\n")
os.makedirs(os.path.dirname(OUT), exist_ok=True)
subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", listfile,
                "-c", "copy", OUT], check=True,
               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
print("DONE ->", OUT)
print("Total:", round(dur(OUT), 1), "s")
