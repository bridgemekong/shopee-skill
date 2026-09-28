# Credentials setup

All keys live in **`~/.shopee-skill/credentials.json`** (override the folder
with the `SHOPEE_SKILL_HOME` env var). Start by copying the template:

```bash
mkdir -p ~/.shopee-skill
cp "$SKILL_DIR/assets/credentials.example.json" ~/.shopee-skill/credentials.json
chmod 600 ~/.shopee-skill/credentials.json
```

Then fill in **only the sections you actually need**. Check progress with:

```bash
python3 "$SKILL_DIR/scripts/config.py" --check
```

> **Claude never types these secrets into a website.** The user obtains each
> key from the provider's developer console and pastes it into the file above.
> Claude only reads the file. If a provider requires an interactive login to
> mint a token, the *user* does that login in their own browser.

---

## `shopee_affiliate`
For generating tracked affiliate links and pulling conversions.
1. Join the **Shopee Affiliate Programme** for your region, then apply for
   **Affiliate Open API** access (approval-based, per region).
2. From the affiliate developer portal, get your **App ID** and **App Secret**.
3. Fill `app_id`, `secret`. Set `base_url` to your region's endpoint if it
   differs from the default.

## `shopee_shop` (Seller / Open Platform)
For pulling your own shop's listings and links.
1. Register at **Shopee Open Platform** (open.shopee.com) and create an app to
   get a **partner_id** and **partner_key**.
2. Authorize your shop to the app via the shop-authorization redirect flow
   (details in `shopee-open-platform-api.md`). That yields a **shop_id**, an
   **access_token**, and a **refresh_token**.
3. Fill `partner_id`, `partner_key`, `shop_id`, `access_token`, `refresh_token`.
   Use the sandbox `base_url` (`partner.test-stable.shopeemobile.com`) while testing.

## `tiktok`
Posting requires the **TikTok Content Posting API**.
1. Create an app in the **TikTok for Developers** portal; add the
   *Content Posting API* product and the `video.publish` scope.
2. Complete the OAuth flow to get a **user access token**; paste it as
   `access_token`.
3. Until your app passes TikTok's audit, posts are forced to `SELF_ONLY`
   (private) — expected during development.

## `meta` (Instagram + Facebook)
Uses the **Meta Graph API**.
1. Create an app at **developers.facebook.com**; add *Facebook Login* and
   *Instagram Graph API*.
2. Connect an **Instagram Business/Creator** account to a **Facebook Page**.
3. Generate a long-lived **Page access token** with `pages_manage_posts`,
   `instagram_basic`, `instagram_content_publish`.
4. Fill `access_token`, `ig_user_id` (the IG Business user id), `fb_page_id`.
   App Review is required before posting for accounts you don't own.

## `x` (Twitter)
1. Create a project/app in the **X Developer Portal** with **Write** permission.
2. Get an OAuth 2.0 **user-context access token** with `tweet.write` +
   `tweet.read` + `users.read`; paste it as `access_token`.

## `telegram`
Simplest to set up.
1. Message **@BotFather**, `/newbot`, copy the **bot token** → `bot_token`.
2. Add the bot to your channel/group as an admin (or use your own chat).
3. Get the **chat_id** (e.g. `@yourchannel`, or a numeric id from
   `getUpdates`) → `chat_id`.

## `whatsapp` (stub)
The `post.py` WhatsApp backend is a documented placeholder. Real posting needs
the **WhatsApp Cloud API**: a verified Business phone number, a
`phone_number_id`, and pre-approved message templates. Fill `access_token` and
`phone_number_id` only when you build that out.

---

### Security notes
- Keep `credentials.json` at `chmod 600`, outside any git repo. It is *not*
  inside the skill directory by design.
- Tokens expire. Shopee Shop `access_token` refreshes via `refresh_token`;
  Meta page tokens are long-lived but not permanent; re-run `config.py --check`
  if calls start returning auth errors.
