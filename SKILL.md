---
name: shopee
description: Connect a Shopee Affiliate or Shopee Shop (Seller) account and manage the full promote-a-product workflow — generate tracked product links, compose per-platform social captions, run a task/campaign queue, and auto-post to TikTok, Instagram/Facebook, X, or Telegram. Trigger when the user mentions Shopee affiliate links, promoting Shopee products, their Shopee shop, or posting Shopee links to socials.
---

# Shopee → Socials

Help a user promote Shopee products end to end: **connect** their Shopee
account, **generate** tracked links, **compose** social posts, queue them as
**tasks/campaigns**, and **post** them to their social channels.

Everything runs locally through the helper scripts in `scripts/`. Credentials
live in a file the **user** creates — never type the user's passwords or API
keys into any website login field.

> **Model-agnostic.** The scripts are plain Python 3 CLIs that print JSON, so
> any AI agent (Claude, GPT, Gemini, Llama, Cursor, Cline, …) or a human can
> drive the same workflow — this `SKILL.md` is the Claude-facing entry point;
> `AGENTS.md` and `README.md` cover other agents and manual use.

## Golden rules

1. **Never enter the user's Shopee or social passwords/keys into a web login
   form.** The user obtains API keys from each developer console themselves and
   puts them in `~/.shopee-skill/credentials.json`. You only ever *read* that
   file (via `config.py`). If a step seems to need a password typed into a site,
   stop and point the user to `references/credentials-setup.md`.
2. **Posting is public and irreversible — confirm before every live post.**
   All posting defaults to `--dry-run`. Only pass `--live` after the user has
   seen the exact caption + link + target and said yes, in this session.
3. **Run scripts with the skill's own path.** Use
   `python3 "$SKILL_DIR/scripts/<script>.py" ...` where `$SKILL_DIR` is this
   skill's directory.
4. **Read the matching reference before calling an API** you haven't used yet
   this session (`references/`). The scripts encode the auth signing; the
   references explain fields, scopes, and approvals.

## First-run setup (do this before anything else)

1. Run `python3 scripts/config.py --check`. It reports which credentials are
   present and which are missing.
2. For anything missing, open `references/credentials-setup.md` and walk the
   user through obtaining it. Have **them** paste values into
   `~/.shopee-skill/credentials.json` (copy `assets/credentials.example.json`
   as a starting template). Do not fabricate keys or fill placeholders.
3. Re-run `--check` until the parts the user needs are green. A user promoting
   only affiliate links to Telegram doesn't need Shopee Shop or TikTok keys —
   only require what the current task uses.

## The core workflow

```
connect → generate link → create task → compose captions → confirm → post → done
```

### 1. Generate / collect a link
- **Affiliate:** `python3 scripts/shopee_affiliate.py link --url "<shopee product url>" --sub-id "<campaign tag>"`
  → tracked short link. `offers --keyword "<kw>"` lists promotable products;
  `report` pulls conversions. See `references/shopee-affiliate-api.md`.
- **Seller shop:** `python3 scripts/shopee_shop.py items` lists your listings;
  `item --id <item_id>` returns its info + link. See
  `references/shopee-open-platform-api.md`.
- The user can also just paste a Shopee product URL — feed it straight into a
  task (step 2) and, if affiliate creds exist, wrap it as a tracked link first.

### 2. Create a task
`python3 scripts/tasks.py add --product "<name>" --link "<url>" --platforms tiktok,meta,x,telegram [--schedule "2026-10-01T09:00"]`
→ prints the new task id. Tasks persist in `~/.shopee-skill/tasks.json`.
See the full queue anytime with `tasks.py list` and the next due one with
`tasks.py next`.

### 3. Compose captions (you do this part)
You write the copy — that's your strength, not an API call.

**Language: write captions in Thai and English (bilingual).** Shopee's core
audience here is Thai, so lead with a natural Thai caption, then a short English
line beneath it. Keep hashtags in both where it helps reach (e.g. `#ShopeeFinds
# shopeehaul` plus Thai tags like `#ของมันต้องมี #รีวิวสินค้า`). Match each
platform's tone in Thai, don't just translate word-for-word. If the user asks
for one language only, honor that.

For each target platform, draft a caption that fits its norms and limits (see
`references/social-apis.md` for the per-platform limits `compose.py` enforces):
- **TikTok**: hook-first, casual, hashtags; links aren't clickable in caption —
  tell the user to put the link in bio/pinned comment.
- **Instagram**: visual-first caption, up to ~30 hashtags; link not clickable —
  use "link in bio".
- **Facebook**: link *is* clickable — include it in the message.
- **X**: ≤280 chars including the link; 1–2 hashtags.
- **Telegram**: link is clickable; can be longer, markdown supported.

Store them onto the task:
`python3 scripts/compose.py set --task <id> --platform x --caption "<text>"`
(repeat per platform). `compose.py show --task <id>` previews all drafts with a
character-count check.

### 4. Confirm, then post
- Always preview first (dry-run is the default):
  `python3 scripts/post.py --task <id> --platform telegram`
  → shows exactly what would be sent.
- Show that preview to the user and get an explicit **yes**.
- Then post for real: `python3 scripts/post.py --task <id> --platform telegram --live`
- `--platform all` iterates every platform on the task. Each success prints the
  live post URL/id; `post.py` then advances the task status.

### 5. Close out
`python3 scripts/tasks.py done --task <id>` marks it complete (posting all
platforms live does this automatically). `tasks.py report` summarizes the queue.

## Scheduling (cron / JSON mode)

There's no background daemon. To act on scheduled tasks interactively, run
`tasks.py next` (or `tasks.py list --due`) — due tasks surface, you confirm,
you post.

For unattended scheduling, use the machine-readable **`due`** command:

```bash
python3 scripts/tasks.py due        # prints {"ok":true,"count":N,"tasks":[...]}
                                    # exit 0 if any tasks are due, exit 3 if none
```

Because it exits 3 when nothing is due, it chains cleanly in cron:

```bash
# every hour: if anything is due, post it live (only for a trusted, pre-approved queue)
0 * * * * cd /path/to/shopee && python3 scripts/tasks.py due >/tmp/due.json 2>&1 \
  && for id in $(python3 -c "import json;print(*[t['id'] for t in json.load(open('/tmp/due.json'))['tasks']])"); do \
       python3 scripts/post.py --task $id --platform all --live; done
```

Note: unattended `--live` posting removes the human confirmation step, so only
enable it for a queue the user has explicitly pre-approved. Otherwise have the
scheduler surface `due` output to the user and post after they confirm. This
`due` JSON is also what you'd feed the `schedule`/scheduled-tasks skill.

## When something fails
- **Missing credentials** → `config.py --check`, then `references/credentials-setup.md`.
- **API / auth error** → the script prints the platform's error JSON; check the
  relevant `references/*.md` for scope/approval requirements (several APIs need
  app review before they'll post on a user's behalf).
- **Rate limited** → back off; don't retry live posts blindly (a partial post
  may already be public).

## Reference files
- `references/credentials-setup.md` — where to get every key; required scopes and approvals.
- `references/shopee-affiliate-api.md` — affiliate auth signing + queries.
- `references/shopee-open-platform-api.md` — seller auth flow + endpoints.
- `references/social-apis.md` — TikTok / Meta / X / Telegram / WhatsApp posting details.
