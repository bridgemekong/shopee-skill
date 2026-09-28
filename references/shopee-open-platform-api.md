# Shopee Open Platform (Seller) API

REST, signed with HMAC-SHA256. Live host `https://partner.shopeemobile.com`;
sandbox `https://partner.test-stable.shopeemobile.com`. Implemented by
`scripts/shopee_shop.py`.

## Authentication (shop-level calls)
```
base_string = partner_id + api_path + timestamp + access_token + shop_id
sign        = HMAC_SHA256( key = partner_key, msg = base_string )   # hex digest
```
Pass as query params on every call: `partner_id`, `timestamp`, `access_token`,
`shop_id`, `sign` (plus the call's own params). `timestamp` is unix seconds and
must be within a few minutes of Shopee's clock.

## Getting `access_token` + `shop_id` (one-time auth flow)
1. Build the authorization URL (signed with `partner_id + /api/v2/shop/auth_partner
   + timestamp`) and have the **shop owner** open it in their browser and approve.
2. Shopee redirects back to your `redirect` URL with `code` and `shop_id`.
3. Call `POST /api/v2/auth/token/get` with `{partner_id, code, shop_id}` (signed)
   to receive `access_token` (valid ~4h) and `refresh_token`.
4. Store `shop_id`, `access_token`, `refresh_token` in credentials.json.
5. Refresh later via `POST /api/v2/auth/access_token/get` with the
   `refresh_token`.

This browser approval is done by the shop owner — Claude does not type the
owner's Shopee password anywhere.

## Operations the script uses

### List items (`items`)
`GET /api/v2/product/get_item_list?...&offset=0&page_size=50&item_status=NORMAL`
→ `response.item[]` with `item_id`, and `has_next_page`.

### Item base info (`item`)
`GET /api/v2/product/get_item_base_info?...&item_id_list=<id>`
→ `response.item_list[]` with `item_name`, `item_sku`, price info, `item_status`.
The script also composes a public product link
`https://shopee.com/product/<shop_id>/<item_id>` — swap the domain for your
region's storefront (e.g. `shopee.co.th`, `shopee.com.my`) if needed.

## Notes / gotchas
- **Error shape:** success responses have `"error": ""`; a non-empty `error`
  plus `message` means failure. The script treats non-empty `error` as failure.
- **Clock skew** is the most common cause of `invalid_sign`. Keep the system
  clock accurate.
- Some endpoints are shop-level (need `shop_id` in the base string, as above);
  others are merchant- or public-level with a different base string. The two
  the script uses are shop-level.
- To promote shop items as an affiliate, feed the composed product link into
  `shopee_affiliate.py link` to get a tracked short link.
