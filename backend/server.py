#!/usr/bin/env python3
"""Serveur de l'interface Studio Ops.
- sert les fichiers statiques (index.html, player.html, PDF, vidéos…)
- POST /api/parcours-pdf : génère et renvoie le PDF combiné d'un parcours.

Lancement :  python3 server.py [port]   (défaut 8765)
"""
import os, sys, json, tempfile, urllib.parse, urllib.request, urllib.error, base64, threading, time, uuid, re, shutil, subprocess, hashlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from functools import partial

from make_parcours_pdf import build_parcours
import import_pipeline
import supa

# Racine du projet = parent de backend/ (front, médias, imports, .env y vivent)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load_env(path):
    """Charge un fichier .env (KEY=VALUE) dans l'environnement (sans écraser l'existant)."""
    if not os.path.exists(path):
        return
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_env(os.path.join(BASE_DIR, ".env"))

# --- Accès protégé par mot de passe (optionnel) : APP_PASSWORD dans .env ---
APP_PASSWORD = os.environ.get("APP_PASSWORD", "").strip()
AUTH_TOKEN = hashlib.sha256(APP_PASSWORD.encode()).hexdigest() if APP_PASSWORD else None

LOGIN_HTML = """<!doctype html><html lang=fr><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>Oplit · Studio Ops — Connexion</title>
<link rel="icon" type="image/svg+xml" href="__FAVICON__">
<style>
  *{box-sizing:border-box;margin:0;font-family:-apple-system,Inter,system-ui,sans-serif}
  body{min-height:100vh;display:grid;place-items:center;background:#0f1020;color:#eef0ff}
  .box{background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.1);border-radius:18px;
       padding:34px 30px;width:340px;text-align:center;box-shadow:0 30px 70px -30px #000}
  .logo{width:46px;height:46px;border-radius:13px;margin:0 auto 16px;display:grid;place-items:center;
        font-weight:800;font-size:24px;color:#fff;background:linear-gradient(135deg,#5b4bff,#8b5cf6)}
  h1{font-size:19px;margin-bottom:6px}p{color:#9498bd;font-size:13px;margin-bottom:20px}
  input{width:100%;padding:12px 14px;border-radius:11px;border:1px solid rgba(255,255,255,.15);
        background:#15172b;color:#fff;font-size:15px;outline:none}
  input:focus{border-color:#8b5cf6}
  button{width:100%;margin-top:12px;padding:12px;border:none;border-radius:11px;cursor:pointer;
         font-size:15px;font-weight:700;color:#fff;background:linear-gradient(135deg,#5b4bff,#8b5cf6)}
  .err{color:#f25f8a;font-size:12.5px;margin-top:10px;min-height:16px}
</style></head><body>
  <form class=box onsubmit="return go(event)">
    <div class=logo>O</div><h1>Studio Ops</h1><p>Accès protégé — entrez le mot de passe.</p>
    <input id=pw type=password placeholder="Mot de passe" autofocus autocomplete=current-password>
    <button>Entrer</button><div class=err id=err></div>
  </form>
  <script>
  async function go(e){e.preventDefault();
    const r=await fetch('/api/login',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({password:document.getElementById('pw').value})});
    if(r.ok){location.reload();}else{document.getElementById('err').textContent='Mot de passe incorrect.';}
    return false;}
  </script>
</body></html>"""

FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
IMPORTS_DIR = os.environ.get("IMPORTS_DIR") or os.path.join(BASE_DIR, "imports")
IMPORTS_JSON = os.path.join(IMPORTS_DIR, "imports.json")
os.makedirs(IMPORTS_DIR, exist_ok=True)

JOBS = {}            # job_id -> {phase,label,pct,error,article,...}
JOBS_LOCK = threading.Lock()
CHARS_PER_MIN = 1000   # ~1000 caractères ≈ 1 min de voix (cf. README)


def _eleven_key():
    k = os.environ.get("ELEVENLABS_API_KEY")
    if not k:
        kf = os.path.expanduser("~/.config/elevenlabs/key")
        if os.path.exists(kf):
            k = open(kf).read().strip()
    return k


def eleven_credits():
    """Solde ElevenLabs (live). Nécessite la permission `user_read` sur la clé."""
    key = _eleven_key()
    if not key:
        return {"ok": False, "reason": "no_key"}
    try:
        req = urllib.request.Request("https://api.elevenlabs.io/v1/user/subscription",
                                     headers={"xi-api-key": key})
        with urllib.request.urlopen(req, timeout=10) as r:
            d = json.load(r)
        limit = d.get("character_limit")
        used = d.get("character_count")
        rem = (limit - used) if (limit is not None and used is not None) else None
        return {"ok": True, "remaining": rem, "limit": limit, "used": used,
                "minutes": (round(rem / CHARS_PER_MIN, 1) if rem is not None else None)}
    except urllib.error.HTTPError as e:
        return {"ok": False, "reason": "missing_permission" if e.code == 401 else f"http_{e.code}"}
    except Exception as e:
        return {"ok": False, "reason": str(e)[:120]}


def _set_job(jid, **kw):
    with JOBS_LOCK:
        JOBS.setdefault(jid, {}).update(kw)


def _load_imports():
    if supa.enabled():
        try:
            return supa.db_list()
        except Exception:
            return []
    if os.path.exists(IMPORTS_JSON):
        try:
            return json.load(open(IMPORTS_JSON, encoding="utf-8"))
        except Exception:
            return []
    return []


def _save_import(article):
    if supa.enabled():
        supa.db_insert(article)
        return
    items = _load_imports()
    items.append(article)
    json.dump(items, open(IMPORTS_JSON, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


_OPLIT_LOGIN = {"running": False, "done_at": None}


def _oplit_profile():
    return os.environ.get("OPLIT_PROFILE",
                          "/Users/mehdi/Desktop/tutorials_automation/build/pw-profile")


def _oplit_status():
    """Statut léger : profil de session présent & non vide (login déjà fait une fois)."""
    prof = _oplit_profile()
    connected = os.path.isdir(prof) and bool(os.listdir(prof))
    return {"connected": connected, "logging_in": _OPLIT_LOGIN["running"]}


def _run_oplit_login():
    _OPLIT_LOGIN["running"] = True
    try:
        script = os.path.join(BASE_DIR, "backend", "video_engine", "scripts", "oplit_login.py")
        subprocess.run([sys.executable, script], timeout=360)
    except Exception:
        pass
    finally:
        _OPLIT_LOGIN["running"] = False


def _run_import(jid, pdf_path, title, section, category, category_icon, live=False):
    try:
        slug = import_pipeline.slugify(title) + "-" + jid[:6]
        work = os.path.join(IMPORTS_DIR, "_work", slug)
        os.makedirs(work, exist_ok=True)
        out_mp4 = os.path.join(IMPORTS_DIR, slug + ".mp4")
        pdf_dst = os.path.join(IMPORTS_DIR, slug + ".pdf")
        import shutil
        shutil.copy(pdf_path, pdf_dst)

        def cb(phase, label, pct, extra):
            _set_job(jid, phase=phase, label=label, pct=pct, **(extra or {}))

        cred = eleven_credits()
        remaining = cred.get("remaining") if cred.get("ok") else None
        import_pipeline.build_video(pdf_path, title, section, work, out_mp4, cb,
                                    remaining_chars=remaining, live=live)

        # durée réelle de la vidéo
        dur = None
        try:
            out = subprocess.run(["ffprobe", "-v", "quiet", "-show_entries",
                                  "format=duration", "-of", "csv=p=0", out_mp4],
                                 capture_output=True, text=True).stdout.strip()
            dur = round(float(out))
        except Exception:
            pass

        video_ref = os.path.relpath(out_mp4, BASE_DIR)
        pdf_ref = os.path.relpath(pdf_dst, BASE_DIR)
        # Supabase Storage : upload -> URLs publiques (sinon on garde les chemins locaux)
        if supa.enabled():
            try:
                _set_job(jid, phase="render", label="Envoi vers Supabase…", pct=92)
                video_ref = supa.upload(out_mp4, slug + ".mp4", "video/mp4")
                pdf_ref = supa.upload(pdf_dst, slug + ".pdf", "application/pdf")
            except Exception as e:
                _set_job(jid, phase="render", label=f"Supabase indisponible ({str(e)[:40]}) — stockage local", pct=95)

        article = {
            "id": "imp-" + jid[:8], "title": title, "section": section or "Importé",
            "category": category or "Mes imports", "icon": category_icon or "📥",
            "dur": dur, "min": max(1, round(dur / 60)) if dur else 3,
            "video": video_ref,
            "pdf": pdf_ref,
        }
        _save_import(article)
        _set_job(jid, phase="done", label="Vidéo prête", pct=100, article=article)
    except Exception as e:
        _set_job(jid, phase="error", label=str(e), error=str(e), pct=0)


class Handler(SimpleHTTPRequestHandler):
    def _json(self, code, obj):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _authed(self):
        if not AUTH_TOKEN:
            return True
        m = re.search(r"ops_auth=([a-f0-9]+)", self.headers.get("Cookie", ""))
        return bool(m and m.group(1) == AUTH_TOKEN)

    def _favicon_data_uri(self):
        try:
            with open(os.path.join(FRONTEND_DIR, "favicon.svg"), "rb") as f:
                return "data:image/svg+xml;base64," + base64.b64encode(f.read()).decode()
        except Exception:
            return ""

    def _send_favicon(self):
        try:
            with open(os.path.join(FRONTEND_DIR, "favicon.svg"), "rb") as f:
                body = f.read()
        except Exception:
            return self.send_error(404)
        self.send_response(200)
        self.send_header("Content-Type", "image/svg+xml")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_login(self):
        body = LOGIN_HTML.replace("__FAVICON__", self._favicon_data_uri()).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _login(self):
        b = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or "{}")
        ok = AUTH_TOKEN and hashlib.sha256((b.get("password") or "").encode()).hexdigest() == AUTH_TOKEN
        if not ok:
            return self._json(401, {"error": "Mot de passe incorrect."})
        body = b'{"ok":true}'
        self.send_response(200)
        self.send_header("Set-Cookie", f"ops_auth={AUTH_TOKEN}; Path=/; HttpOnly; SameSite=Lax")
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def translate_path(self, path):
        # sert d'abord depuis frontend/ (index, app.js…), sinon depuis la racine (médias)
        default = super().translate_path(path)
        rel = os.path.relpath(default, BASE_DIR)
        cand = os.path.join(FRONTEND_DIR, rel)
        if os.path.exists(cand):
            return cand
        return default

    def do_GET(self):
        if self.path.split("?")[0] in ("/favicon.svg", "/favicon.ico"):
            return self._send_favicon()         # favicon accessible même sans login
        if AUTH_TOKEN and not self._authed():
            return self._send_login()          # non authentifié -> page de login
        if self.path in ("/", ""):
            self.path = "/index.html"
        path = self.path.split("?")[0]
        if path == "/api/imports":
            return self._json(200, _load_imports())
        if path == "/api/eleven-credits":
            return self._json(200, eleven_credits())
        if path == "/api/oplit-status":
            return self._json(200, _oplit_status())
        if path == "/api/import-status":
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            jid = (qs.get("job") or [""])[0]
            with JOBS_LOCK:
                st = dict(JOBS.get(jid, {"phase": "unknown"}))
            return self._json(200, st)
        return super().do_GET()

    def do_POST(self):
        path = self.path.split("?")[0]
        if path == "/api/login":
            return self._login()
        if AUTH_TOKEN and not self._authed():
            return self._json(401, {"error": "non autorisé"})
        if path == "/api/import-exercise":
            return self._import_exercise()
        if path == "/api/oplit-login":
            return self._oplit_login()
        if path == "/api/rename-category":
            return self._rename_category()
        if path == "/api/update-import":
            return self._update_import()
        if path == "/api/delete-import":
            return self._delete_import()
        if path == "/api/restore-import":
            return self._restore_import()
        if path != "/api/parcours-pdf":
            return self._json(404, {"error": "not found"})
        try:
            length = int(self.headers.get("Content-Length", 0))
            cfg = json.loads(self.rfile.read(length) or "{}")
            if not cfg.get("articles"):
                return self._json(400, {"error": "Aucun article sélectionné."})

            out = os.path.join(tempfile.mkdtemp(), "Parcours.pdf")
            cfg["out"] = out
            build_parcours(cfg, BASE_DIR)
            with open(out, "rb") as fh:
                data = fh.read()
            os.unlink(out)

            # Nom de fichier : ASCII pur dans `filename` (en-têtes HTTP = latin-1),
            # + variante UTF-8 percent-encodée (RFC 5987) pour conserver les accents.
            raw = (cfg.get("title") or "Parcours").strip().replace('"', "") + ".pdf"
            ascii_name = raw.encode("ascii", "ignore").decode("ascii").strip() or "Parcours.pdf"
            utf8_name = urllib.parse.quote(raw)
            self.send_response(200)
            self.send_header("Content-Type", "application/pdf")
            self.send_header("Content-Disposition",
                             f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{utf8_name}")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except FileNotFoundError as e:
            self._json(400, {"error": str(e)})
        except Exception as e:
            self._json(500, {"error": f"{type(e).__name__}: {e}"})

    def _import_exercise(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length) or "{}")
            title = (body.get("title") or "").strip()
            section = (body.get("section") or "").strip()
            category = (body.get("category") or "Mes imports").strip()
            category_icon = (body.get("category_icon") or "📥").strip()
            live = bool(body.get("live"))
            b64 = body.get("pdf_base64") or ""
            if not title or not b64:
                return self._json(400, {"error": "Titre et PDF requis."})
            pdf_bytes = base64.b64decode(b64.split(",")[-1])
            if pdf_bytes[:5] != b"%PDF-":
                return self._json(400, {"error": "Le fichier n'est pas un PDF valide."})
            jid = uuid.uuid4().hex
            tmp_pdf = os.path.join(tempfile.mkdtemp(), "src.pdf")
            with open(tmp_pdf, "wb") as f:
                f.write(pdf_bytes)
            _set_job(jid, phase="queued", label="En file d'attente…", pct=4)
            threading.Thread(target=_run_import,
                             args=(jid, tmp_pdf, title, section, category, category_icon, live),
                             daemon=True).start()
            return self._json(200, {"job": jid})
        except Exception as e:
            return self._json(500, {"error": f"{type(e).__name__}: {e}"})

    def _update_import(self):
        try:
            b = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or "{}")
            fields = {k: str(b[k]).strip() for k in ("title", "section", "category", "icon")
                      if b.get(k) is not None and str(b[k]).strip()}
            if supa.enabled():
                supa.db_update(b.get("id"), fields)
                return self._json(200, {"ok": True})
            items = _load_imports()
            art = next((it for it in items if it.get("id") == b.get("id")), None)
            if not art:
                return self._json(404, {"error": "import introuvable"})
            art.update(fields)
            json.dump(items, open(IMPORTS_JSON, "w", encoding="utf-8"),
                      ensure_ascii=False, indent=2)
            return self._json(200, {"ok": True, "article": art})
        except Exception as e:
            return self._json(500, {"error": str(e)})

    def _delete_import(self):
        try:
            b = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or "{}")
            if supa.enabled():
                supa.db_delete(b.get("id"))   # (les fichiers restent dans le bucket)
                return self._json(200, {"ok": True})
            items = _load_imports()
            art = next((it for it in items if it.get("id") == b.get("id")), None)
            if not art:
                return self._json(404, {"error": "import introuvable"})
            # corbeille (déplace, ne supprime pas) -> permet l'undo
            trash = os.path.join(IMPORTS_DIR, "_trash")
            os.makedirs(trash, exist_ok=True)
            for key in ("video", "pdf"):
                rel = art.get(key)
                if rel and not rel.startswith("http"):
                    p = os.path.realpath(os.path.join(BASE_DIR, rel))
                    if p.startswith(os.path.realpath(IMPORTS_DIR)) and os.path.isfile(p):
                        shutil.move(p, os.path.join(trash, os.path.basename(p)))
            items = [it for it in items if it.get("id") != b.get("id")]
            json.dump(items, open(IMPORTS_JSON, "w", encoding="utf-8"),
                      ensure_ascii=False, indent=2)
            return self._json(200, {"ok": True})
        except Exception as e:
            return self._json(500, {"error": str(e)})

    def _restore_import(self):
        try:
            b = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or "{}")
            art = b.get("article")
            if not art:
                return self._json(400, {"error": "article requis"})
            if supa.enabled():
                supa.db_insert(art)   # ré-insère la ligne (fichiers toujours dans le bucket)
                return self._json(200, {"ok": True})
            trash = os.path.join(IMPORTS_DIR, "_trash")
            for key in ("video", "pdf"):
                rel = art.get(key)
                if rel:
                    dst = os.path.realpath(os.path.join(BASE_DIR, rel))
                    src = os.path.join(trash, os.path.basename(dst))
                    if os.path.isfile(src) and dst.startswith(os.path.realpath(IMPORTS_DIR)):
                        shutil.move(src, dst)
            items = _load_imports()
            if not any(it.get("id") == art.get("id") for it in items):
                items.append(art)
            json.dump(items, open(IMPORTS_JSON, "w", encoding="utf-8"),
                      ensure_ascii=False, indent=2)
            return self._json(200, {"ok": True})
        except Exception as e:
            return self._json(500, {"error": str(e)})

    def _oplit_login(self):
        if _OPLIT_LOGIN["running"]:
            return self._json(200, {"ok": True, "already": True})
        threading.Thread(target=_run_oplit_login, daemon=True).start()
        return self._json(200, {"ok": True})

    def _rename_category(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            b = json.loads(self.rfile.read(length) or "{}")
            old, new = b.get("old"), b.get("new")
            icon = b.get("icon")
            if not old or not new:
                return self._json(400, {"error": "old/new requis"})
            if supa.enabled():
                supa.db_rename_category(old, new, icon)
                return self._json(200, {"ok": True})
            items = _load_imports()
            for it in items:
                if it.get("category") == old:
                    it["category"] = new
                    if icon:
                        it["icon"] = icon
            json.dump(items, open(IMPORTS_JSON, "w", encoding="utf-8"),
                      ensure_ascii=False, indent=2)
            return self._json(200, {"ok": True})
        except Exception as e:
            return self._json(500, {"error": str(e)})

    def log_message(self, fmt, *args):
        pass  # silencieux


if __name__ == "__main__":
    port = int(os.environ.get("PORT") or (sys.argv[1] if len(sys.argv) > 1 else 8765))
    httpd = ThreadingHTTPServer(("", port), partial(Handler, directory=BASE_DIR))
    print(f"Studio Ops sur http://localhost:{port}  (Ctrl+C pour arrêter)")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nArrêt.")
