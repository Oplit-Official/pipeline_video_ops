#!/usr/bin/env python3
"""Monte en lot toutes les vidéos d'une catégorie + journal + notif macOS.

Usage: python3 build_batch.py "<DST categorie>"
Construit chaque <DST>/**/spec.json -> mp4 (chemin "out" du spec).
Journal: video helpdesk/progress.log (suivi via `tail -f`).
Notif macOS à chaque vidéo + à la fin.
"""
import os, sys, glob, subprocess, datetime

DST = sys.argv[1]
ROOT = "/Users/mehdi/Desktop/tutorials_automation"
LOG = os.path.join(ROOT, "video helpdesk", "progress.log")
os.makedirs(os.path.dirname(LOG), exist_ok=True)

specs = sorted(glob.glob(os.path.join(DST, "**", "spec.json"), recursive=True))
cat = os.path.basename(DST.rstrip("/"))

def ts():
    return datetime.datetime.now().strftime("%H:%M:%S")

def notify(msg):
    subprocess.run(["osascript", "-e",
                    f'display notification "{msg}" with title "Oplit vidéos — {cat}"'],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def log(line):
    with open(LOG, "a") as f:
        f.write(line + "\n")
    print(line, flush=True)

total = len(specs)
log(f"[{ts()}] ▶ START {cat} — {total} vidéo(s)")
notify(f"Démarrage : {total} vidéos")
ok = 0
for i, s in enumerate(specs, 1):
    name = os.path.basename(os.path.dirname(s))
    log(f"[{ts()}] [{i}/{total}] … {name}")
    r = subprocess.run([sys.executable, os.path.join(ROOT, "scripts/make_helpdesk_video.py"), s],
                       stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    if r.returncode == 0:
        ok += 1
        log(f"[{ts()}] [{i}/{total}] ✅ {name}")
        notify(f"{i}/{total} ✓ {name}")
    else:
        err = (r.stderr.decode(errors="ignore").strip().splitlines() or ["?"])[-1]
        log(f"[{ts()}] [{i}/{total}] ❌ {name} — {err[:160]}")
        notify(f"{i}/{total} ÉCHEC {name}")
log(f"[{ts()}] ■ TERMINÉ {cat} — {ok}/{total} OK")
notify(f"Terminé : {ok}/{total} OK")
