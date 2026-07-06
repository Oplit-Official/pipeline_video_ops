#!/usr/bin/env python3
"""Capture LIVE sur staging.oplit.fr pour les imports.

- deduce_script(title, text) : Claude déduit, depuis le texte du PDF, un script
  d'étapes { route (parmi une liste connue), button (à encadrer), narration }.
- capture_live(steps, out_dir) : Playwright (session persistée) navigue chaque
  route, screenshote, et calcule le rect DOM du bouton visé (curseur au pixel).

Nécessite : playwright + Chrome + une session staging loguée (profil persistant).
"""
import os, re, json, urllib.request

import import_pipeline as ip   # réutilise clé Claude + modèle + _clean

OPLIT_BASE = os.environ.get("OPLIT_BASE", "https://staging.oplit.fr")
OPLIT_PROFILE = os.environ.get("OPLIT_PROFILE",
                               "/Users/mehdi/Desktop/tutorials_automation/build/pw-profile")

# Routes Oplit connues (paramétrage) — Claude choisit parmi celles-ci
KNOWN_ROUTES = [
    ["/parameters/general/factory-structure", "Structure de l'usine (postes, ateliers)"],
    ["/parameters/general/parameters-list", "Liste des paramètres"],
    ["/parameters/general/calculation-rules", "Règles de calcul de la capacité (général)"],
    ["/parameters/general/sectors-groups", "Groupes de secteurs"],
    ["/parameters/sector/information", "Informations d'un secteur"],
    ["/parameters/sector/calendar", "Calendrier d'un secteur"],
    ["/parameters/sector/calculation-rules", "Règles de calcul par secteur"],
    ["/parameters/import/import-parsing-rules", "Règles de parsing des imports"],
    ["/parameters/import/import-data", "Import des données"],
    ["/home", "Page d'accueil / sélection client"],
]


def deduce_script(title, full_text, max_steps=6):
    """Renvoie {"intro","outro","steps":[{"route","button","narration"}]} ou None."""
    key = ip._anthropic_key()
    if not key:
        return None
    routes_desc = "\n".join(f"- {r}  → {d}" for r, d in KNOWN_ROUTES)
    valid = {r for r, _ in KNOWN_ROUTES}
    prompt = (
        f"Tu prépares un tutoriel vidéo Oplit à partir d'un article : « {title} ».\n"
        f"Voix-off au vouvoiement, français, claire. Le texte ci-dessous est l'extrait "
        f"brut du PDF (peut contenir du bruit).\n\n"
        f"Pour chaque étape, choisis la ROUTE de l'application Oplit la plus pertinente "
        f"STRICTEMENT dans cette liste :\n{routes_desc}\n\n"
        f"Réponds UNIQUEMENT en JSON :\n"
        f'{{"intro":"...","outro":"...","steps":[{{"route":"/parameters/...","button":"Texte exact du bouton à cliquer ou \\"\\"","narration":"..."}}]}}\n'
        f"Contraintes : 3 à {max_steps} étapes, `route` OBLIGATOIREMENT dans la liste, "
        f"`button` = libellé exact d'un bouton visible (ex. « Ajouter un paramètre ») ou vide, "
        f"`narration` = 1 à 2 phrases.\n\nTEXTE :\n{full_text[:6000]}"
    )
    body = json.dumps({"model": ip.ANTHROPIC_MODEL, "max_tokens": 1600,
                       "messages": [{"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=body,
                                 headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                                          "content-type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.load(r)
        txt = "".join(b.get("text", "") for b in data.get("content", []))
        txt = re.sub(r"^```(?:json)?|```$", "", txt.strip(), flags=re.M).strip()
        obj = json.loads(txt)
        steps = []
        for s in (obj.get("steps") or []):
            route = s.get("route", "")
            if route in valid:
                steps.append({"route": route, "button": (s.get("button") or "").strip(),
                              "narration": ip._clean(s.get("narration", ""))})
        if not steps:
            return None
        return {"intro": ip._clean(obj.get("intro", "")),
                "outro": ip._clean(obj.get("outro", "")), "steps": steps}
    except Exception:
        return None


# JS : rect (fractions du viewport) d'un bouton par son texte exact
_JS_BTN = """([label, VW, VH]) => {
    if (!label) return null;
    const els = Array.from(document.querySelectorAll('a,button,div,span,li'))
        .filter(e => (e.textContent||'').trim() === label);
    els.sort((a,b) => { const ra=a.getBoundingClientRect(), rb=b.getBoundingClientRect();
        return (ra.width*ra.height)-(rb.width*rb.height); });
    for (const e of els) {
        const r = e.getBoundingClientRect();
        if (r.width>20 && r.width<500 && r.height>10 && r.height<80)
            return {fx:r.left/VW, fy:r.top/VH, fw:r.width/VW, fh:r.height/VH};
    }
    return null;
}"""


def capture_live(steps, out_dir, on_log=lambda m: None):
    """Screenshote chaque route + calcule le rect du bouton. Enrichit steps avec
    'shot' et 'highlight'. Retourne (steps, n_captures)."""
    from playwright.sync_api import sync_playwright
    os.makedirs(out_dir, exist_ok=True)
    VW, VH = 1680, 1000
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            OPLIT_PROFILE, channel="chrome", headless=True,
            args=["--no-first-run", "--no-default-browser-check"],
            viewport={"width": VW, "height": VH}, device_scale_factor=2)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(f"{OPLIT_BASE}/home", wait_until="domcontentloaded")
        page.wait_for_timeout(3500)
        cid = page.url.split("cid=")[1].split("&")[0] if "cid=" in page.url else ""
        if "input[type=password]" and page.query_selector("input[type=password]"):
            ctx.close()
            raise RuntimeError("Session Oplit expirée : reconnectez-vous.")
        suffix = f"?cid={cid}" if cid else ""
        for i, st in enumerate(steps, 1):
            page.goto(f"{OPLIT_BASE}{st['route']}{suffix}", wait_until="domcontentloaded")
            page.wait_for_timeout(4000)
            shot = os.path.join(out_dir, f"shot-{i:02d}.png")
            page.screenshot(path=shot)
            st["shot"] = shot
            hl = None
            if st.get("button"):
                try:
                    hl = page.evaluate(_JS_BTN, [st["button"], VW, VH])
                except Exception:
                    hl = None
            st["highlight"] = hl
            on_log(f"route {st['route']} — {'cible ✓' if hl else 'pas de bouton'}")
        ctx.close()
    return steps, len(steps)
