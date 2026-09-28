#!/usr/bin/env python3
"""Attach and preview per-platform captions on a task.

Claude writes the actual copy; this script stores it on the task and enforces
each platform's limits so nothing gets truncated at post time.

Commands:
  set   --task <id> --platform x --caption "..."   (reads --caption or stdin)
  show  --task <id>                                 preview all drafts + checks

Python 3 stdlib only.
"""
import argparse
import json
import os
import sys

import config
from common import emit

PATH = config.TASKS_PATH

# platform -> (max caption chars or None, link_clickable, note)
LIMITS = {
    "x":         (280,  True,  "≤280 chars incl. link; 1–2 hashtags."),
    "tiktok":    (2200, False, "Link NOT clickable in caption — put it in bio/pinned comment."),
    "instagram": (2200, False, "Link NOT clickable — use 'link in bio'. Up to ~30 hashtags."),
    "meta":      (2200, True,  "Routed to IG (not clickable) + FB (clickable). Keep link in text for FB."),
    "facebook":  (2200, True,  "Link is clickable — include it."),
    "telegram":  (4096, True,  "Link clickable; markdown supported."),
    "whatsapp":  (4096, True,  "Link clickable in text."),
}


def _load():
    if not os.path.exists(PATH):
        emit(False, error="no tasks file yet — create a task with tasks.py add")
    with open(PATH, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _save(db):
    with open(PATH, "w", encoding="utf-8") as fh:
        json.dump(db, fh, indent=2, ensure_ascii=False)


def _find(db, task_id):
    for t in db["tasks"]:
        if t["id"] == task_id:
            return t
    return None


def cmd_set(args):
    caption = args.caption if args.caption is not None else sys.stdin.read()
    caption = caption.strip()
    if not caption:
        emit(False, error="empty caption")
    platform = args.platform.lower()
    if platform not in LIMITS:
        emit(False, error=f"unknown platform '{platform}'", valid=sorted(LIMITS))
    db = _load()
    task = _find(db, args.task)
    if not task:
        emit(False, error=f"no task #{args.task}")
    limit = LIMITS[platform][0]
    over = limit is not None and len(caption) > limit
    task["captions"][platform] = caption
    # promote draft -> ready once every target platform has a caption
    if all(p in task["captions"] for p in task["platforms"]) and task["status"] == "draft":
        task["status"] = "ready"
    _save(db)
    emit(not over,
         task=args.task, platform=platform, length=len(caption), limit=limit,
         over_limit=over,
         warning=(f"caption is {len(caption)}/{limit} chars — trim it" if over else None),
         status=task["status"])


def cmd_show(args):
    db = _load()
    task = _find(db, args.task)
    if not task:
        emit(False, error=f"no task #{args.task}")
    preview = {}
    for platform in task["platforms"]:
        cap = task["captions"].get(platform)
        limit, clickable, note = LIMITS.get(platform, (None, True, ""))
        preview[platform] = {
            "caption": cap,
            "length": len(cap) if cap else 0,
            "limit": limit,
            "over_limit": bool(cap and limit and len(cap) > limit),
            "link_clickable_in_caption": clickable,
            "note": note,
            "missing": cap is None,
        }
    emit(True, product=task["product"], link=task["link"],
         status=task["status"], platforms=preview)


def main():
    p = argparse.ArgumentParser(description="Attach/preview per-platform captions")
    sub = p.add_subparsers(dest="cmd", required=True)

    ps = sub.add_parser("set")
    ps.add_argument("--task", type=int, required=True)
    ps.add_argument("--platform", required=True)
    ps.add_argument("--caption", help="caption text; if omitted, read from stdin")
    ps.set_defaults(func=cmd_set)

    psh = sub.add_parser("show")
    psh.add_argument("--task", type=int, required=True)
    psh.set_defaults(func=cmd_show)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
