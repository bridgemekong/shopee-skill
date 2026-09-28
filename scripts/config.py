#!/usr/bin/env python3
"""Load and validate the Shopee-skill credentials file.

Credentials live in ~/.shopee-skill/credentials.json (override with
$SHOPEE_SKILL_HOME). This module is imported by every other script; run it
directly with --check to see what's configured.

No third-party dependencies — Python 3 standard library only.
"""
import json
import os
import sys

HOME = os.environ.get("SHOPEE_SKILL_HOME", os.path.expanduser("~/.shopee-skill"))
CRED_PATH = os.path.join(HOME, "credentials.json")
TASKS_PATH = os.path.join(HOME, "tasks.json")

# section -> list of required keys for that section to count as "configured"
REQUIRED = {
    "shopee_affiliate": ["app_id", "secret"],
    "shopee_shop": ["partner_id", "partner_key", "shop_id", "access_token"],
    "tiktok": ["access_token"],
    "meta": ["access_token", "ig_user_id"],   # fb_page_id optional; ig_user_id needed for IG
    "x": ["access_token"],
    "telegram": ["bot_token", "chat_id"],
    "whatsapp": ["access_token", "phone_number_id"],
}


def load():
    """Return the parsed credentials dict, or {} if the file is absent."""
    if not os.path.exists(CRED_PATH):
        return {}
    try:
        with open(CRED_PATH, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (json.JSONDecodeError, OSError) as exc:
        print(json.dumps({"ok": False, "error": f"could not read {CRED_PATH}: {exc}"}))
        sys.exit(1)


def section(name):
    """Return a credentials section, exiting with a clear message if missing.

    Use this in the API scripts: cfg = config.section('telegram').
    """
    creds = load()
    data = creds.get(name, {})
    missing = [k for k in REQUIRED.get(name, []) if not str(data.get(k, "")).strip()]
    if missing:
        print(json.dumps({
            "ok": False,
            "error": f"'{name}' is not configured (missing: {', '.join(missing)})",
            "fix": f"Add them to {CRED_PATH} — see references/credentials-setup.md",
        }))
        sys.exit(2)
    return data


def status():
    """Return {section: {'configured': bool, 'missing': [...]}} for all sections."""
    creds = load()
    out = {}
    for name, keys in REQUIRED.items():
        data = creds.get(name, {})
        missing = [k for k in keys if not str(data.get(k, "")).strip()]
        out[name] = {"configured": not missing, "missing": missing}
    return out


def _check(as_json=False):
    exists = os.path.exists(CRED_PATH)
    st = status()
    if as_json:
        print(json.dumps({"ok": True, "path": CRED_PATH, "exists": exists, "sections": st}))
        return
    print(f"Credentials file: {CRED_PATH}")
    print(f"  exists: {exists}")
    if not exists:
        print("  → Copy assets/credentials.example.json to that path and fill in what you need.")
    for name, info in st.items():
        mark = "✓" if info["configured"] else "·"
        detail = "" if info["configured"] else f"  (missing: {', '.join(info['missing'])})"
        print(f"  {mark} {name}{detail}")


if __name__ == "__main__":
    _check(as_json="--json" in sys.argv)
