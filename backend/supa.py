#!/usr/bin/env python3
"""Supabase : Storage (fichiers vidéo/PDF) + table `imports` (métadonnées).
Tout via l'API REST (urllib), avec la clé service_role côté serveur uniquement.
Activé si SUPABASE_URL + SUPABASE_SERVICE_KEY sont définis (sinon repli fichier).
"""
import os, json, urllib.request, urllib.parse, mimetypes

URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
BUCKET = os.environ.get("SUPABASE_BUCKET", "videos")
TABLE = os.environ.get("SUPABASE_TABLE", "imports")

# colonnes autorisées dans la table (évite les erreurs PostgREST)
COLS = ("id", "title", "section", "category", "icon", "dur", "min", "video", "pdf", "active")


def enabled():
    return bool(URL and KEY)


def _headers(extra=None):
    h = {"apikey": KEY, "Authorization": f"Bearer {KEY}"}
    if extra:
        h.update(extra)
    return h


def _req(url, data=None, method="GET", extra=None, timeout=120):
    req = urllib.request.Request(url, data=data, method=method, headers=_headers(extra))
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
    return raw


# ---------- Storage ----------
def upload(local_path, dest, content_type=None):
    """Upload un fichier dans le bucket, renvoie l'URL publique."""
    content_type = content_type or mimetypes.guess_type(local_path)[0] or "application/octet-stream"
    data = open(local_path, "rb").read()
    enc = urllib.parse.quote(dest)
    _req(f"{URL}/storage/v1/object/{BUCKET}/{enc}", data=data, method="POST",
         extra={"Content-Type": content_type, "x-upsert": "true"})
    return f"{URL}/storage/v1/object/public/{BUCKET}/{enc}"


def remove(dest):
    try:
        _req(f"{URL}/storage/v1/object/{BUCKET}/{urllib.parse.quote(dest)}", method="DELETE", timeout=30)
    except Exception:
        pass


# ---------- Table ----------
def db_list():
    # n'affiche que les actifs (les supprimés ont active=false)
    raw = _req(f"{URL}/rest/v1/{TABLE}?select=*&active=eq.true&order=created_at.desc", timeout=30)
    return json.loads(raw or "[]")


def db_insert(row):
    row = {k: row[k] for k in COLS if k in row}
    _req(f"{URL}/rest/v1/{TABLE}", data=json.dumps(row).encode(), method="POST",
         extra={"Content-Type": "application/json", "Prefer": "return=minimal"}, timeout=30)


def db_update(item_id, fields):
    fields = {k: v for k, v in fields.items() if k in COLS}
    _req(f"{URL}/rest/v1/{TABLE}?id=eq.{urllib.parse.quote(item_id)}",
         data=json.dumps(fields).encode(), method="PATCH",
         extra={"Content-Type": "application/json", "Prefer": "return=minimal"}, timeout=30)


def db_delete(item_id):
    # soft delete : passe active=false (le fichier reste dans le bucket, undo possible)
    db_update(item_id, {"active": False})


def db_restore(item_id):
    db_update(item_id, {"active": True})


def db_rename_category(old, new, icon=None):
    fields = {"category": new}
    if icon:
        fields["icon"] = icon
    _req(f"{URL}/rest/v1/{TABLE}?category=eq.{urllib.parse.quote(old)}",
         data=json.dumps(fields).encode(), method="PATCH",
         extra={"Content-Type": "application/json", "Prefer": "return=minimal"}, timeout=30)
