# AGENTS.md — how any AI agent should use this repo

This repo is a **model-agnostic skill**: a set of plain Python 3 CLIs that let
an AI agent (or a human) run the full "promote a Shopee product to socials"
workflow. It works with Claude Code, Cursor, Cline, Windsurf, GPT-based agents,
Gemini, local models — anything that can run a shell command and read JSON.

- **Claude Code / Claude:** the entry point is [`SKILL.md`](SKILL.md); it loads
  automatically as a skill.
- **Any other agent or human:** read [`README.md`](README.md) and call the
  scripts directly. Every script prints JSON on stdout, so you can parse results
  programmatically.

## Contract for agents
1. **Never type the user's passwords or API keys into a website.** The user
   places their own API keys in `~/.shopee-skill/credentials.json`
   (see `references/credentials-setup.md`). Scripts only read that file.
2. **Posting is public and irreversible.** `scripts/post.py` defaults to a
   dry-run; only add `--live` after the user has seen the exact caption + link +
   target and confirmed.
3. **Write captions in Thai and English** (Thai-first), unless the user asks for
   one language.
4. **Discover commands** by running any script with `-h`, and validate setup
   with `python3 scripts/config.py --check`.

## The workflow, as commands
```bash
python3 scripts/config.py --check                          # 1. what's configured
python3 scripts/shopee_affiliate.py link --url <url> --sub-id <tag>   # 2. tracked link
python3 scripts/tasks.py add --product <name> --link <url> --platforms telegram,x   # 3. task
python3 scripts/compose.py set --task <id> --platform x --caption "<TH + EN copy>"   # 4. caption
python3 scripts/post.py --task <id> --platform x            # 5. dry-run preview
python3 scripts/post.py --task <id> --platform x --live     # 6. publish (after confirm)
python3 scripts/tasks.py due                                # cron: JSON of due tasks
```

No third-party Python packages are required — standard library only.
