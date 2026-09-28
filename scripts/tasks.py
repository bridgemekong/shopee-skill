#!/usr/bin/env python3
"""Local task/campaign queue for Shopee promotions.

Stored at ~/.shopee-skill/tasks.json (override with $SHOPEE_SKILL_HOME).
A task = a product + link + target platforms + drafted captions + status.

Commands:
  add     --product --link --platforms a,b --schedule <iso>
  list    [--due] [--json]
  next               show the next actionable task (due or ready)
  show    --task <id>
  done    --task <id>
  remove  --task <id>

Statuses: draft -> ready -> posting -> done.  Python 3 stdlib only.
"""
import argparse
import datetime as dt
import json
import os

import config
from common import emit

PATH = config.TASKS_PATH
VALID_PLATFORMS = {"tiktok", "meta", "instagram", "facebook", "x", "telegram", "whatsapp"}


def _load():
    if not os.path.exists(PATH):
        return {"tasks": [], "next_id": 1}
    with open(PATH, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _save(db):
    os.makedirs(os.path.dirname(PATH), exist_ok=True)
    with open(PATH, "w", encoding="utf-8") as fh:
        json.dump(db, fh, indent=2, ensure_ascii=False)


def _find(db, task_id):
    for t in db["tasks"]:
        if t["id"] == task_id:
            return t
    return None


def _is_due(task, now):
    when = task.get("scheduled_for")
    if not when:
        return True  # unscheduled tasks are always actionable
    try:
        return dt.datetime.fromisoformat(when) <= now
    except ValueError:
        return True


def cmd_add(args):
    platforms = [p.strip().lower() for p in args.platforms.split(",") if p.strip()]
    bad = [p for p in platforms if p not in VALID_PLATFORMS]
    if bad:
        emit(False, error=f"unknown platform(s): {', '.join(bad)}",
             valid=sorted(VALID_PLATFORMS))
    if args.schedule:
        try:
            dt.datetime.fromisoformat(args.schedule)
        except ValueError:
            emit(False, error="--schedule must be ISO 8601, e.g. 2026-10-01T09:00")
    db = _load()
    task = {
        "id": db["next_id"],
        "product": args.product,
        "link": args.link,
        "platforms": platforms,
        "captions": {},
        "status": "draft",
        "scheduled_for": args.schedule,
        "posted": {},
        "created_at": dt.datetime.now().replace(microsecond=0).isoformat(),
    }
    db["tasks"].append(task)
    db["next_id"] += 1
    _save(db)
    emit(True, created=task)


def cmd_list(args):
    db = _load()
    now = dt.datetime.now()
    tasks = db["tasks"]
    if args.due:
        tasks = [t for t in tasks if t["status"] != "done" and _is_due(t, now)]
    if args.json:
        emit(True, count=len(tasks), tasks=tasks)
    if not tasks:
        emit(True, count=0, message="no tasks")
    lines = []
    for t in tasks:
        sched = f" @ {t['scheduled_for']}" if t.get("scheduled_for") else ""
        drafted = ",".join(sorted(t["captions"])) or "—"
        lines.append(f"#{t['id']} [{t['status']}] {t['product']} → "
                     f"{','.join(t['platforms'])}{sched}  captions: {drafted}")
    emit(True, count=len(tasks), summary="\n".join(lines))


def cmd_next(args):
    db = _load()
    now = dt.datetime.now()
    actionable = [t for t in db["tasks"] if t["status"] != "done" and _is_due(t, now)]
    actionable.sort(key=lambda t: (t.get("scheduled_for") or "", t["id"]))
    emit(True, task=actionable[0] if actionable else None,
         message=None if actionable else "nothing due")


def cmd_due(args):
    """Cron-friendly: print all due tasks as JSON. Exit 0 if any are due, 3 if
    none — so a scheduler can chain `tasks.py due && <post step>`."""
    import sys
    db = _load()
    now = dt.datetime.now()
    due = [t for t in db["tasks"] if t["status"] != "done" and _is_due(t, now)]
    due.sort(key=lambda t: (t.get("scheduled_for") or "", t["id"]))
    print(json.dumps({"ok": True, "count": len(due), "tasks": due}, ensure_ascii=False))
    sys.exit(0 if due else 3)


def cmd_show(args):
    db = _load()
    task = _find(db, args.task)
    if not task:
        emit(False, error=f"no task #{args.task}")
    emit(True, task=task)


def cmd_done(args):
    db = _load()
    task = _find(db, args.task)
    if not task:
        emit(False, error=f"no task #{args.task}")
    task["status"] = "done"
    _save(db)
    emit(True, task=task)


def cmd_remove(args):
    db = _load()
    before = len(db["tasks"])
    db["tasks"] = [t for t in db["tasks"] if t["id"] != args.task]
    if len(db["tasks"]) == before:
        emit(False, error=f"no task #{args.task}")
    _save(db)
    emit(True, removed=args.task)


def cmd_report(args):
    db = _load()
    by_status = {}
    for t in db["tasks"]:
        by_status[t["status"]] = by_status.get(t["status"], 0) + 1
    emit(True, total=len(db["tasks"]), by_status=by_status)


def main():
    p = argparse.ArgumentParser(description="Shopee promotion task queue")
    sub = p.add_subparsers(dest="cmd", required=True)

    pa = sub.add_parser("add")
    pa.add_argument("--product", required=True)
    pa.add_argument("--link", required=True)
    pa.add_argument("--platforms", required=True, help="comma list: tiktok,meta,x,telegram")
    pa.add_argument("--schedule", help="ISO 8601 datetime, optional")
    pa.set_defaults(func=cmd_add)

    pl = sub.add_parser("list")
    pl.add_argument("--due", action="store_true", help="only actionable/due, not done")
    pl.add_argument("--json", action="store_true")
    pl.set_defaults(func=cmd_list)

    pn = sub.add_parser("next")
    pn.set_defaults(func=cmd_next)

    pdue = sub.add_parser("due", help="cron mode: JSON of due tasks; exit 3 if none")
    pdue.set_defaults(func=cmd_due)

    ps = sub.add_parser("show")
    ps.add_argument("--task", type=int, required=True)
    ps.set_defaults(func=cmd_show)

    pd = sub.add_parser("done")
    pd.add_argument("--task", type=int, required=True)
    pd.set_defaults(func=cmd_done)

    prm = sub.add_parser("remove")
    prm.add_argument("--task", type=int, required=True)
    prm.set_defaults(func=cmd_remove)

    prep = sub.add_parser("report")
    prep.set_defaults(func=cmd_report)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
