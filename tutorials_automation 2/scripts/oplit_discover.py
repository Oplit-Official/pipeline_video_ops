#!/usr/bin/env python3
"""Discover selectors for the interactive screens (field-type dropdown, duplicate menu, factory node actions)."""
import os
from playwright.sync_api import sync_playwright

PROFILE = "/Users/mehdi/Desktop/tutorials_automation/build/pw-profile"
BASE = "https://staging.oplit.fr"

def trim(s, n=2000):
    return (s[:n] + " …") if s and len(s) > n else s

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        user_data_dir=PROFILE, channel="chrome", headless=True,
        args=["--no-first-run", "--no-default-browser-check"],
        viewport={"width": 1680, "height": 1000}, device_scale_factor=1,
    )
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.goto(f"{BASE}/home", wait_until="domcontentloaded"); page.wait_for_timeout(3000)
    cid = page.url.split("cid=")[1].split("&")[0] if "cid=" in page.url else ""
    sfx = f"?cid={cid}" if cid else ""

    print("\n========== ADD-PARAMETER MODAL ==========", flush=True)
    page.goto(f"{BASE}/parameters/general/parameters-list{sfx}", wait_until="domcontentloaded")
    page.wait_for_timeout(4000)
    page.get_by_text("Ajouter un paramètre", exact=False).first.click()
    page.wait_for_timeout(1500)
    # éléments interactifs dans la modale
    modal = page.locator(".create-field-modal, .f-modal-wrapper").first
    info = page.evaluate(
        """() => {
            const m = document.querySelector('.create-field-modal') || document.querySelector('.f-modal-wrapper');
            if(!m) return 'NO MODAL';
            const out=[];
            m.querySelectorAll('input,select,[role=combobox],[role=button],button,.f-select,.v-select,[class*=select]').forEach(e=>{
                out.push(`<${e.tagName.toLowerCase()}> role=${e.getAttribute('role')} cls="${e.className}" ph="${e.getAttribute('placeholder')||''}" txt="${(e.innerText||'').slice(0,40).replace(/\\n/g,' ')}"`);
            });
            return out.join('\\n');
        }"""
    )
    print(info, flush=True)

    print("\n========== CALC RULE SECTOR — header buttons ==========", flush=True)
    page.goto(f"{BASE}/parameters/sector/calculation-rules{sfx}", wait_until="domcontentloaded")
    page.wait_for_timeout(4500)
    info2 = page.evaluate(
        """() => {
            const out=[];
            document.querySelectorAll('button,[role=button],.f-icon,[class*=icon],[aria-haspopup]').forEach(e=>{
                const r=e.getBoundingClientRect();
                if(r.top<260 && r.right>1200){ // zone haut-droite (en-tête carte)
                    out.push(`<${e.tagName.toLowerCase()}> cls="${e.className}" aria=${e.getAttribute('aria-haspopup')} x=${Math.round(r.x)} y=${Math.round(r.y)} txt="${(e.innerText||'').slice(0,30).replace(/\\n/g,' ')}"`);
                }
            });
            return out.join('\\n');
        }"""
    )
    print(info2, flush=True)
    ctx.close()
    print("\nDONE", flush=True)
