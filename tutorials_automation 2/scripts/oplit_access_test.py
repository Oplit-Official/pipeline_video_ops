#!/usr/bin/env python3
"""Test access to demo.oplit.fr reusing the existing Chrome profile (logged-in session)."""
import os, sys
from playwright.sync_api import sync_playwright

CHROME_DIR = os.path.expanduser("~/Library/Application Support/Google/Chrome")
OUT = "/Users/mehdi/Desktop/tutorials_automation/build/live"
os.makedirs(OUT, exist_ok=True)

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        user_data_dir=CHROME_DIR,
        channel="chrome",
        headless=False,
        args=["--profile-directory=Default", "--no-first-run", "--no-default-browser-check"],
        viewport={"width": 1600, "height": 900},
    )
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.goto("https://demo.oplit.fr", wait_until="domcontentloaded")
    page.wait_for_timeout(6000)  # laisser l'app charger / rediriger
    print("URL finale:", page.url)
    print("Titre:", page.title())
    shot = os.path.join(OUT, "access_test.png")
    page.screenshot(path=shot, full_page=False)
    print("Capture:", shot)
    ctx.close()
