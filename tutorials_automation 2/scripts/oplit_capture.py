#!/usr/bin/env python3
"""Headless capture of the Settings screens on staging.oplit.fr, reusing the saved session.
Also extracts, per page, the bounding rect of the active left-sidebar menu item,
saved to build/menu_coords.json (used by build_video.py to position the navigation cursor)."""
import os, time, json
from playwright.sync_api import sync_playwright

PROFILE = "/Users/mehdi/Desktop/tutorials_automation/build/pw-profile"
OUT = "/Users/mehdi/Desktop/tutorials_automation/build/live"
os.makedirs(OUT, exist_ok=True)

BASE = "https://staging.oplit.fr"
# (clé fichier, chemin route)
TARGETS = [
    ("01_factory_structure", "/parameters/general/factory-structure"),
    ("03_sector_information", "/parameters/sector/information"),
    ("04_calendar",           "/parameters/sector/calendar"),
    ("05_sectors_groups",     "/parameters/general/sectors-groups"),
    ("06_parameters_list",    "/parameters/general/parameters-list"),
    ("08_calc_rule_general",  "/parameters/general/calculation-rules"),
    ("09_calc_rule_sector",   "/parameters/sector/calculation-rules"),
    ("12_import_parsing",     "/parameters/import/import-parsing-rules"),
    ("13_import_data",        "/parameters/import/import-data"),
]

# Onglet du haut actif d'après l'URL
def tab_label(path):
    if "/general/" in path: return "Paramètres généraux"
    if "/sector/" in path:  return "Paramètres par secteur"
    if "/import/" in path:  return "Imports"
    return None

# Boutons à encadrer (par texte) pour chaque page
EXTRA_BUTTONS = {
    "05_sectors_groups":    ["Créer un groupe"],
    "06_parameters_list":   ["Ajouter un paramètre"],
    "08_calc_rule_general": ["Créer une nouvelle règle"],
    "13_import_data":       ["Importer un fichier"],
}

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        user_data_dir=PROFILE,
        channel="chrome",
        headless=True,
        args=["--no-first-run", "--no-default-browser-check"],
        viewport={"width": 1680, "height": 1000},
        device_scale_factor=2,
    )
    page = ctx.pages[0] if ctx.pages else ctx.new_page()

    # récupérer le cid depuis /home
    page.goto(f"{BASE}/home", wait_until="domcontentloaded")
    page.wait_for_timeout(4000)
    cid = ""
    if "cid=" in page.url:
        cid = page.url.split("cid=")[1].split("&")[0]
    print("URL home:", page.url, "| cid:", cid, flush=True)

    suffix = f"?cid={cid}" if cid else ""

    JS_HIGHLIGHTS = """([tabLabel, buttonLabels, VW, VH]) => {
        const toFrac = r => ({fx: r.left/VW, fy: r.top/VH, fw: r.width/VW, fh: r.height/VH});
        function findActiveMenu() {
            const cands = Array.from(document.querySelectorAll('a, button, div, li, span'))
                .filter(e => {
                    const cls = (e.className || '').toString();
                    return /active|--selected/i.test(cls)
                        || e.getAttribute('aria-current') === 'page'
                        || e.getAttribute('aria-selected') === 'true';
                })
                .map(e => ({el: e, r: e.getBoundingClientRect()}))
                .filter(o => o.r.width > 30 && o.r.height > 12 && o.r.height < 60
                              && o.r.left < 260 && o.r.left > 50 && o.r.top > 80);
            cands.sort((a,b) => (a.r.width*a.r.height) - (b.r.width*b.r.height));
            return cands[0] ? toFrac(cands[0].r) : null;
        }
        function findByText(label, topMax) {
            const els = Array.from(document.querySelectorAll('a, button, div, span, li'))
                .filter(e => {
                    if ((e.textContent || '').trim() !== label) return false;
                    const r = e.getBoundingClientRect();
                    return r.width > 30 && r.width < 400 && r.height > 12 && r.height < 60
                           && (topMax === undefined || r.top < topMax);
                });
            els.sort((a,b) => {
                const ra = a.getBoundingClientRect(), rb = b.getBoundingClientRect();
                return (ra.width*ra.height) - (rb.width*rb.height);
            });
            return els[0] ? toFrac(els[0].getBoundingClientRect()) : null;
        }
        const out = {menu: findActiveMenu(), tab: null, buttons: []};
        if (tabLabel) out.tab = findByText(tabLabel, 100);
        (buttonLabels || []).forEach(lbl => {
            const r = findByText(lbl);
            if (r) out.buttons.push(r);
        });
        return out;
    }"""

    coords = {}        # rétro-compat (centre du menu actif)
    highlights = {}    # rectangles à encadrer (tab, menu, boutons)
    VW, VH = 1680, 1000
    for key, path in TARGETS:
        url = f"{BASE}{path}{suffix}"
        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_timeout(4500)
        out = os.path.join(OUT, f"{key}.png")
        page.screenshot(path=out)
        hl = page.evaluate(JS_HIGHLIGHTS, [tab_label(path), EXTRA_BUTTONS.get(key, []), VW, VH])
        highlights[key] = hl
        if hl and hl.get("menu"):
            m = hl["menu"]
            coords[key] = {"fx": m["fx"] + m["fw"]/2, "fy": m["fy"] + m["fh"]/2}
        print(f"{key}: tab={'OK' if hl.get('tab') else '-'} "
              f"menu={'OK' if hl.get('menu') else '-'} "
              f"boutons={len(hl.get('buttons', []))}", flush=True)

    with open("/Users/mehdi/Desktop/tutorials_automation/build/menu_coords.json", "w") as fh:
        json.dump(coords, fh, indent=2)
    with open("/Users/mehdi/Desktop/tutorials_automation/build/highlights.json", "w") as fh:
        json.dump(highlights, fh, indent=2)
    ctx.close()
    print("DONE", flush=True)
