#!/usr/bin/env python3
"""Orchestrateur tout-en-un : (re)capture les écrans Oplit puis monte la vidéo.
Usage:  python3 scripts/make_tutorial.py [version]
        version par défaut = horodatage. Ex: python3 scripts/make_tutorial.py v4
Pré-requis : s'être connecté une fois via scripts/oplit_login.py (session persistée).
"""
import os, sys, shutil, subprocess, datetime

ROOT = "/Users/mehdi/Desktop/tutorials_automation"
LIVE = os.path.join(ROOT, "build/live")
SHOTS = os.path.join(ROOT, "build/shots_auto")
SCRIPTS = os.path.join(ROOT, "scripts")

ver = sys.argv[1] if len(sys.argv) > 1 else datetime.datetime.now().strftime("%Y%m%d_%H%M")
out_name = f"Tutoriel_Oplit_chap1_{ver}.mp4"

# mapping scène (1..13) -> fichier capturé dans build/live
MAP = {
    1:  "01_factory_structure",
    2:  "01_factory_structure",   # création poste : même écran (arbre en canvas, non survolable headless)
    3:  "03_sector_information",
    4:  "04_calendar",
    5:  "05_sectors_groups",
    6:  "06_parameters_list",
    7:  "07_add_parameter",       # modale + dropdown "type de champ"
    8:  "08_calc_rule_general",
    9:  "09_calc_rule_sector",
    10: "10_duplicate",           # modale duplication
    11: "08_calc_rule_general",   # niveau parent : page règle générale
    12: "12_import_parsing",
    13: "13_import_data",
}

def run(script):
    print(f"\n=== {script} ===", flush=True)
    subprocess.run([sys.executable, os.path.join(SCRIPTS, script)], check=True)

# 1) Captures (headless, session réutilisée)
run("oplit_capture.py")
run("oplit_capture_modals.py")

# 2) Mapping -> dossier shots
os.makedirs(SHOTS, exist_ok=True)
for n, key in MAP.items():
    src = os.path.join(LIVE, f"{key}.png")
    dst = os.path.join(SHOTS, f"shot-{n:02d}.png")
    if not os.path.exists(src):
        raise SystemExit(f"Capture manquante : {src} (la session a-t-elle expiré ? relance oplit_login.py)")
    shutil.copy(src, dst)
print(f"\n{len(MAP)} captures mappées dans {SHOTS}", flush=True)

# 3) Montage
env = dict(os.environ, SHOTS_DIR=SHOTS, OUT_NAME=out_name)
subprocess.run([sys.executable, os.path.join(ROOT, "build_video.py")], check=True, env=env)
print(f"\n✅ Vidéo : {os.path.join(ROOT, out_name)}", flush=True)
