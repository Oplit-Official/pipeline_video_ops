#!/usr/bin/env python3
"""One-time visible login to demo.oplit.fr. Detects when you're logged in,
saves the session in build/pw-profile, then closes. All later runs are headless."""
import os, time
from playwright.sync_api import sync_playwright

PROFILE = "/Users/mehdi/Desktop/tutorials_automation/build/pw-profile"
OUT = "/Users/mehdi/Desktop/tutorials_automation/build/live"
os.makedirs(PROFILE, exist_ok=True)
os.makedirs(OUT, exist_ok=True)

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        user_data_dir=PROFILE,
        channel="chrome",
        headless=False,
        args=["--no-first-run", "--no-default-browser-check"],
        viewport={"width": 1600, "height": 900},
    )
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.goto("https://staging.oplit.fr", wait_until="domcontentloaded")
    print(">> Connecte-toi dans la fenêtre. Je détecte automatiquement quand c'est bon.", flush=True)

    stable = 0
    logged_in = False
    deadline = time.time() + 300  # 5 min max
    while time.time() < deadline:
        try:
            has_pw = page.query_selector("input[type=password]") is not None
            url = page.url
            # connecté = plus de champ mot de passe, et toujours sur le domaine app
            if (not has_pw) and ("staging.oplit.fr" in url) and ("login" not in url.lower()):
                stable += 1
            else:
                stable = 0
            if stable >= 3:  # ~9s stable
                logged_in = True
                break
        except Exception:
            stable = 0
        time.sleep(3)

    time.sleep(3)  # laisser la session se persister sur le disque
    print("Connecté:", logged_in, "| URL:", page.url, flush=True)
    page.screenshot(path=os.path.join(OUT, "after_login.png"))
    ctx.close()
    print("DONE", flush=True)
