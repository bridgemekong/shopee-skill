#!/usr/bin/env python3
"""Shared helpers: HTTP (stdlib urllib) and structured output."""
import json
import sys
import urllib.error
import urllib.parse
import urllib.request


def http(method, url, headers=None, body=None, form=None, timeout=30):
    """Make an HTTP request and return (status_code, parsed_or_text).

    body: dict -> sent as JSON. form: dict -> sent as x-www-form-urlencoded.
    """
    headers = dict(headers or {})
    data = None
    if form is not None:
        data = urllib.parse.urlencode(form).encode("utf-8")
        headers.setdefault("Content-Type", "application/x-www-form-urlencoded")
    elif body is not None:
        data = body.encode("utf-8") if isinstance(body, str) else json.dumps(body).encode("utf-8")
        headers.setdefault("Content-Type", "application/json")

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", "replace")
            return resp.status, _maybe_json(raw)
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", "replace")
        return exc.code, _maybe_json(raw)
    except urllib.error.URLError as exc:
        return 0, {"error": f"network error: {exc.reason}"}


def _maybe_json(text):
    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return text


def emit(ok, **fields):
    """Print a structured JSON result and exit non-zero on failure."""
    payload = {"ok": ok}
    payload.update(fields)
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    sys.exit(0 if ok else 1)
