"""Web state reader for the OSWorld 2.0 mocked web apps (step 4, 6 Nov 2026).

Every OSWorld-web app keeps its whole per-user state as JSON behind /api/state (GET reads it, PUT replaces it; the
user is the user_id cookie, passed to the page as ?cookie=<id>).  So the web part of the symbolic state is that JSON,
a change is a JSON diff, and a reset is one PUT of the saved state.  Bookkeeping fields (meta.updated_at,
meta.version, note) are not state.
"""
import glob
import json
import os

import requests
import urllib3

urllib3.disable_warnings()
SUFFIX = os.environ.get("WEBSITE_HOST_SUFFIX", "site.hku.icu")   # team-hosted 2026.08.08 sites; v2.1 needs self-hosting
IGNORE = {("meta", "updated_at"), ("meta", "version"), ("note",)}


def base(app):
    return f"https://{app}.{SUFFIX}"


def new_user(app):
    s = requests.Session()
    s.get(base(app) + "/api/state", verify=False, timeout=30).raise_for_status()
    return s.cookies["user_id"]


def read(app, uid):
    r = requests.get(base(app) + "/api/state", cookies={"user_id": uid}, verify=False, timeout=30)
    r.raise_for_status()
    return r.json()["state"]


def write(app, uid, state):
    r = requests.put(base(app) + "/api/state", json=state, cookies={"user_id": uid}, verify=False, timeout=30)
    r.raise_for_status()


def diff(a, b, path=()):
    """-> list of (path, old, new) leaf differences; lists of dicts with an 'id' are matched by id."""
    if path in IGNORE:
        return []
    if isinstance(a, dict) and isinstance(b, dict):
        out = []
        for k in sorted(set(a) | set(b), key=str):
            out += diff(a.get(k, "<absent>"), b.get(k, "<absent>"), path + (k,))
        return out
    if isinstance(a, list) and isinstance(b, list):
        if all(isinstance(x, dict) and "id" in x for x in a + b) and (a or b):
            da, db = {x["id"]: x for x in a}, {x["id"]: x for x in b}
            return diff(da, db, path)
        if len(a) == len(b):
            out = []
            for i, (x, y) in enumerate(zip(a, b)):
                out += diff(x, y, path + (i,))
            return out
    return [] if a == b else [(path, a, b)]


def chromium():
    return glob.glob(os.path.expanduser("~/Library/Caches/ms-playwright/chromium_headless_shell-*/*/chrome-headless-shell"))[0]
