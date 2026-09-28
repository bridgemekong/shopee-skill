#!/usr/bin/env python3
"""Unified social poster for Shopee promotion tasks.

  post.py --task <id> --platform telegram          # DRY RUN (default): preview only
  post.py --task <id> --platform telegram --live    # actually publishes
  post.py --task <id> --platform all --live         # every platform on the task

SAFETY: dry-run is the default. A live post is public and irreversible, so the
SKILL.md workflow requires the user to see the preview and confirm before you
pass --live. Each backend reads its own credentials via config.section().

Backends: telegram (full), x (full), meta = facebook + instagram (Graph API),
tiktok (Content Posting API, video via PULL_FROM_URL), whatsapp (stub).
Python 3 stdlib only. See references/social-apis.md.
"""
import argparse
import json
import os

import config
from common import http, emit

PATH = config.TASKS_PATH


def _load_task(task_id):
    if not os.path.exists(PATH):
        emit(False, error="no tasks file yet")
    with open(PATH, "r", encoding="utf-8") as fh:
        db = json.load(fh)
    for t in db["tasks"]:
        if t["id"] == task_id:
            return db, t
    emit(False, error=f"no task #{task_id}")


def _save(db):
    with open(PATH, "w", encoding="utf-8") as fh:
        json.dump(db, fh, indent=2, ensure_ascii=False)


def _text(task, platform):
    """Caption for a platform, falling back to a link-only message."""
    cap = task["captions"].get(platform)
    if cap:
        return cap
    return f"{task['product']} {task['link']}".strip()


# ---- backends: each returns (ok, detail_dict) -----------------------------

def post_telegram(task, dry):
    cfg = config.section("telegram")
    text = _text(task, "telegram")
    url = f"https://api.telegram.org/bot{cfg['bot_token']}/sendMessage"
    form = {"chat_id": cfg["chat_id"], "text": text, "disable_web_page_preview": "false"}
    if dry:
        return True, {"would_POST": url.replace(cfg["bot_token"], "***"), "text": text}
    status, data = http("POST", url, form=form)
    ok = status == 200 and isinstance(data, dict) and data.get("ok")
    return ok, {"status": status, "response": data}


def post_x(task, dry):
    cfg = config.section("x")
    text = _text(task, "x")
    url = "https://api.twitter.com/2/tweets"
    headers = {"Authorization": f"Bearer {cfg['access_token']}"}
    if dry:
        return True, {"would_POST": url, "text": text, "length": len(text)}
    status, data = http("POST", url, headers=headers, body={"text": text})
    ok = status in (200, 201)
    return ok, {"status": status, "response": data}


def post_facebook(task, dry):
    cfg = config.section("meta")
    if not cfg.get("fb_page_id"):
        return False, {"error": "meta.fb_page_id not set"}
    text = _text(task, "meta")
    url = f"https://graph.facebook.com/v20.0/{cfg['fb_page_id']}/feed"
    form = {"message": text, "link": task["link"], "access_token": cfg["access_token"]}
    if dry:
        return True, {"would_POST": url, "message": text, "link": task["link"]}
    status, data = http("POST", url, form=form)
    ok = status == 200 and isinstance(data, dict) and "id" in data
    return ok, {"status": status, "response": data}


def post_instagram(task, dry):
    """IG needs an image/video URL. Requires task['media_url']."""
    cfg = config.section("meta")
    media = task.get("media_url")
    text = _text(task, "meta")
    if not media:
        return False, {"error": "Instagram requires task['media_url'] (image/video URL). "
                                "Add one to the task in tasks.json, or post to FB/others."}
    base = f"https://graph.facebook.com/v20.0/{cfg['ig_user_id']}"
    if dry:
        return True, {"would_create_container": base + "/media",
                      "image_url": media, "caption": text,
                      "then_publish": base + "/media_publish"}
    s1, d1 = http("POST", base + "/media",
                  form={"image_url": media, "caption": text, "access_token": cfg["access_token"]})
    if s1 != 200 or not isinstance(d1, dict) or "id" not in d1:
        return False, {"stage": "create_container", "status": s1, "response": d1}
    s2, d2 = http("POST", base + "/media_publish",
                  form={"creation_id": d1["id"], "access_token": cfg["access_token"]})
    ok = s2 == 200 and isinstance(d2, dict) and "id" in d2
    return ok, {"stage": "publish", "status": s2, "response": d2}


def post_meta(task, dry):
    """meta = Facebook feed + Instagram (best-effort each)."""
    fb_ok, fb = post_facebook(task, dry)
    ig_ok, ig = post_instagram(task, dry)
    return (fb_ok or ig_ok), {"facebook": fb, "instagram": ig}


def post_tiktok(task, dry):
    """TikTok direct video post via PULL_FROM_URL. Requires task['media_url']."""
    cfg = config.section("tiktok")
    media = task.get("media_url")
    text = _text(task, "tiktok")
    if not media:
        return False, {"error": "TikTok requires task['media_url'] (a public video URL). "
                                "TikTok posts are videos, not link cards."}
    url = "https://open.tiktokapis.com/v2/post/publish/video/init/"
    headers = {"Authorization": f"Bearer {cfg['access_token']}",
               "Content-Type": "application/json; charset=UTF-8"}
    body = {
        "post_info": {"title": text[:150], "privacy_level": "SELF_ONLY"},
        "source_info": {"source": "PULL_FROM_URL", "video_url": media},
    }
    if dry:
        return True, {"would_POST": url, "title": text[:150], "video_url": media,
                      "note": "privacy_level SELF_ONLY until your app passes TikTok review"}
    status, data = http("POST", url, headers=headers, body=body)
    ok = status == 200 and isinstance(data, dict) and (data.get("data") or {}).get("publish_id")
    return ok, {"status": status, "response": data}


def post_whatsapp(task, dry):
    """Stub: WhatsApp Cloud API needs a Business number + message templates."""
    return False, {"error": "WhatsApp backend is a documented stub — see references/social-apis.md. "
                            "Cloud API requires a verified Business phone number and approved template."}


BACKENDS = {
    "telegram": post_telegram,
    "x": post_x,
    "facebook": post_facebook,
    "instagram": post_instagram,
    "meta": post_meta,
    "tiktok": post_tiktok,
    "whatsapp": post_whatsapp,
}


def main():
    p = argparse.ArgumentParser(description="Post a task's captions to socials")
    p.add_argument("--task", type=int, required=True)
    p.add_argument("--platform", required=True,
                   help="one of: " + ", ".join(sorted(BACKENDS)) + ", or 'all'")
    p.add_argument("--live", action="store_true",
                   help="actually publish (default is a dry-run preview)")
    args = p.parse_args()

    db, task = _load_task(args.task)
    dry = not args.live

    targets = task["platforms"] if args.platform == "all" else [args.platform.lower()]
    unknown = [t for t in targets if t not in BACKENDS]
    if unknown:
        emit(False, error=f"unknown platform(s): {', '.join(unknown)}", valid=sorted(BACKENDS))

    results = {}
    all_ok = True
    if not dry:
        task["status"] = "posting"
        _save(db)
    for plat in targets:
        ok, detail = BACKENDS[plat](task, dry)
        results[plat] = {"ok": ok, **detail}
        all_ok = all_ok and ok
        if ok and not dry:
            task.setdefault("posted", {})[plat] = detail

    if not dry:
        # done only when every target platform has been posted
        if all(p in task.get("posted", {}) for p in task["platforms"]):
            task["status"] = "done"
        else:
            task["status"] = "ready"
        _save(db)

    emit(all_ok, mode="dry-run" if dry else "live",
         task=args.task, status=task["status"], results=results,
         reminder=None if not dry else "Preview only. Re-run with --live after the user confirms.")


if __name__ == "__main__":
    main()
