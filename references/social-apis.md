# Social posting APIs

All posting goes through `scripts/post.py` (dry-run by default; `--live`
publishes). Each backend reads its own section from credentials.json.

| Platform  | Backend arg | Posts what | Link clickable? | Needs media_url? | App review to post for others? |
|-----------|-------------|------------|-----------------|------------------|-------------------------------|
| Telegram  | `telegram`  | text + link message | yes | no | no |
| X         | `x`         | tweet (≤280) | yes | no | no (just Write access) |
| Facebook  | `facebook`  | page feed post + link | yes | no | yes (for pages you don't own) |
| Instagram | `instagram` | photo/video + caption | no | **yes** | yes |
| `meta`    | `meta`      | FB feed **and** IG (best effort) | mixed | IG part yes | yes |
| TikTok    | `tiktok`    | video (PULL_FROM_URL) | no | **yes** | yes (else SELF_ONLY) |
| WhatsApp  | `whatsapp`  | *(stub)* | — | — | yes |

`media_url` is read from an optional `"media_url"` field on the task in
`tasks.json` — a public image (IG photo) or video (IG Reel / TikTok) URL.

## Telegram — Bot API
`POST https://api.telegram.org/bot<token>/sendMessage`
form: `chat_id`, `text`. Simplest and most reliable; great for affiliate link
drops to a channel. No review needed.

## X (Twitter) — API v2
`POST https://api.twitter.com/2/tweets`
header: `Authorization: Bearer <user access token>` (OAuth 2.0 user context,
scope `tweet.write`); body: `{"text": "..."}`. Keep total ≤280 incl. the link.

## Facebook — Graph API
`POST https://graph.facebook.com/v20.0/<page_id>/feed`
form: `message`, `link`, `access_token`. The **link is clickable**, so include
the Shopee link in the message copy. Needs `pages_manage_posts`.

## Instagram — Graph API (2-step)
1. Create container: `POST /v20.0/<ig_user_id>/media`
   form: `image_url` (or `video_url`), `caption`, `access_token`.
2. Publish: `POST /v20.0/<ig_user_id>/media_publish`
   form: `creation_id`, `access_token`.
Captions can't contain clickable links — drive traffic via "link in bio". Needs
`instagram_content_publish`. **Requires a public `media_url`.**

## TikTok — Content Posting API
`POST https://open.tiktokapis.com/v2/post/publish/video/init/`
header: `Authorization: Bearer <token>`; body includes `post_info` (title,
`privacy_level`) and `source_info` (`source: PULL_FROM_URL`, `video_url`).
TikTok is video-only — no link cards. Until the app passes TikTok's audit,
`privacy_level` is forced to `SELF_ONLY`. **Requires a public video `media_url`.**

## WhatsApp — Cloud API (stub)
Real implementation: `POST https://graph.facebook.com/v20.0/<phone_number_id>/messages`
with a verified Business number and an approved message template. The backend
currently returns a clear "stub" error; wire it up when you have a Business
number provisioned.

## Posting discipline (enforced by SKILL.md)
- Preview with a dry run, show the user the exact text+link+target, get an
  explicit yes, then `--live`.
- On a rate limit (HTTP 429) don't blindly retry a live post — a partial post
  may already be public. Check the platform, then decide.
