#!/usr/bin/env python3
"""Capture the interactive screens (work-center action, field-type dropdown, duplicate modal)
on staging.oplit.fr, fully automatically, reusing the saved session.
Also extracts highlight rectangles for the modal elements and merges into highlights.json."""
import os, json
from playwright.sync_api import sync_playwright

PROFILE = "/Users/mehdi/Desktop/tutorials_automation/build/pw-profile"
OUT = "/Users/mehdi/Desktop/tutorials_automation/build/live"
BASE = "https://staging.oplit.fr"
os.makedirs(OUT, exist_ok=True)

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        user_data_dir=PROFILE, channel="chrome", headless=True,
        args=["--no-first-run", "--no-default-browser-check"],
        viewport={"width": 1680, "height": 1000}, device_scale_factor=2,
    )
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.goto(f"{BASE}/home", wait_until="domcontentloaded"); page.wait_for_timeout(3000)
    cid = page.url.split("cid=")[1].split("&")[0] if "cid=" in page.url else ""
    sfx = f"?cid={cid}" if cid else ""

    def shot(name):
        page.screenshot(path=os.path.join(OUT, f"{name}.png"))
        print("saved", name, flush=True)

    VW, VH = 1680, 1000
    # liste flottante du dropdown ouvert : panneau v-overlay / v-list visible contenant les options
    JS_DROPDOWN_RECT = """(VW_VH) => {
        const [VW, VH] = VW_VH;
        const toFrac = r => ({fx: r.left/VW, fy: r.top/VH, fw: r.width/VW, fh: r.height/VH});
        const opts = ['Nombre','Pourcentage','Liste déroulante'];
        const cands = Array.from(document.querySelectorAll(
            '.v-overlay__content, .v-list, [role=listbox], [class*=menu__content], [class*=dropdown]'
        ))
        .filter(e => {
            const r = e.getBoundingClientRect();
            const t = e.textContent || '';
            return r.width > 0 && r.height > 0
                && opts.every(o => t.includes(o));
        })
        .map(e => ({el: e, r: e.getBoundingClientRect()}));
        cands.sort((a,b) => (a.r.width*a.r.height) - (b.r.width*b.r.height));
        return cands[0] ? toFrac(cands[0].r) : null;
    }"""
    # boîte intérieure de la modale "Dupliquer" : on part du titre puis on remonte
    # jusqu'à un parent borné (et non le wrapper plein écran)
    JS_DUP_MODAL_RECT = """(VW_VH) => {
        const [VW, VH] = VW_VH;
        const toFrac = r => ({fx: r.left/VW, fy: r.top/VH, fw: r.width/VW, fh: r.height/VH});
        const titles = Array.from(document.querySelectorAll('h1,h2,h3,h4,h5,div,span'))
            .filter(e => {
                const t = (e.textContent || '').trim();
                return /^Dupliquer/i.test(t) && t.length < 80;
            })
            .map(e => ({el: e, r: e.getBoundingClientRect()}))
            .filter(o => o.r.width > 30 && o.r.height > 12 && o.r.height < 60);
        titles.sort((a,b) => (a.r.width*a.r.height) - (b.r.width*b.r.height));
        let el = titles[0]?.el;
        if (!el) return null;
        // remonter au parent dont la taille est < 80% de la fenêtre (= la boîte modale)
        while (el && el.parentElement) {
            const r = el.parentElement.getBoundingClientRect();
            if (r.width > 200 && r.width < VW*0.85 && r.height > 100 && r.height < VH*0.95) {
                return toFrac(r);
            }
            el = el.parentElement;
        }
        return null;
    }"""

    HL_PATH = "/Users/mehdi/Desktop/tutorials_automation/build/highlights.json"
    try:
        with open(HL_PATH) as fh:
            highlights = json.load(fh)
    except FileNotFoundError:
        highlights = {}

    # ---------- Scene 2 : créer un poste de charge (survol d'un nœud feuille) ----------
    try:
        page.goto(f"{BASE}/parameters/general/factory-structure{sfx}", wait_until="domcontentloaded")
        page.wait_for_timeout(4500)
        # repérer le nœud feuille le plus à droite/bas et le survoler pour révéler les actions (+ / éditer / supprimer)
        box = page.evaluate(
            """() => {
                let best=null, bx=-1;
                document.querySelectorAll('*').forEach(e=>{
                    const t=(e.childElementCount===0 ? (e.textContent||'') : '').trim();
                    const r=e.getBoundingClientRect();
                    // feuilles = petits libellés alignés à droite (derniers niveaux), dans la zone de l'arbre
                    if(t && t.length>=2 && t.length<=10 && r.width>0 && r.height>0 && r.height<28 && r.left>900 && r.top>140 && r.top<900){
                        if(r.left>bx){bx=r.left; best=r;}
                    }
                });
                return best ? {x:best.left+best.width/2, y:best.top+best.height/2} : null;
            }"""
        )
        if box:
            page.mouse.move(box["x"], box["y"])
            page.wait_for_timeout(1200)
            page.mouse.move(box["x"], box["y"])  # re-trigger hover
            page.wait_for_timeout(800)
            print("hover node @", box, flush=True)
        shot("02_work_center")
    except Exception as e:
        print("ECHEC scene2:", e, flush=True)

    # ---------- Scene 7 : modale ajout paramètre + dropdown "Type de champ" ouvert ----------
    try:
        page.goto(f"{BASE}/parameters/general/parameters-list{sfx}", wait_until="domcontentloaded")
        page.wait_for_timeout(4000)
        page.get_by_text("Ajouter un paramètre", exact=False).first.click()
        page.wait_for_timeout(1500)
        # le déclencheur du select "Type de champ" est le bouton .input-button de la modale
        page.locator(".create-field-modal button.input-button, .f-modal-wrapper button.input-button").first.click()
        page.wait_for_timeout(1000)
        shot("07_add_parameter")
        # rectangle de la liste déroulante ouverte
        opts = page.evaluate(JS_DROPDOWN_RECT, [VW, VH])
        if opts:
            highlights["07_add_parameter"] = {"buttons": [opts]}
            print("  highlight dropdown:", opts, flush=True)
    except Exception as e:
        print("ECHEC scene7:", e, flush=True)

    # ---------- Scene 10 : modale de duplication de règle ----------
    try:
        page.goto(f"{BASE}/parameters/sector/calculation-rules{sfx}", wait_until="domcontentloaded")
        page.wait_for_timeout(4500)
        page.locator("button:has(.vue-feather--more-vertical)").first.click()
        page.wait_for_timeout(900)
        page.get_by_text("Dupliquer", exact=False).first.click()
        page.wait_for_timeout(1800)
        shot("10_duplicate")
        # rectangle de la modale de duplication
        modal = page.evaluate(JS_DUP_MODAL_RECT, [VW, VH])
        if modal:
            highlights["10_duplicate"] = {"buttons": [modal]}
            print("  highlight modale duplication:", modal, flush=True)
    except Exception as e:
        print("ECHEC scene10:", e, flush=True)

    with open(HL_PATH, "w") as fh:
        json.dump(highlights, fh, indent=2)
    ctx.close()
    print("DONE", flush=True)
