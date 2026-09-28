# Shopee Affiliate Open API

GraphQL over a single endpoint (region-specific). Default:
`https://open-api.affiliate.shopee.com/graphql`. Implemented by
`scripts/shopee_affiliate.py`.

## Authentication
Every request is signed. Given the raw request body `payload` (the exact JSON
string you POST):

```
timestamp = current unix seconds
signature = SHA256( app_id + timestamp + payload + secret )   # hex digest
```

Sent as a header:

```
Authorization: SHA256 Credential=<app_id>, Timestamp=<timestamp>, Signature=<signature>
Content-Type: application/json
```

The signature covers the byte-exact payload, so the script signs the same
serialized string it sends (compact separators, no re-encoding).

## Operations the script uses

### Generate short link (`link`)
```graphql
mutation ($input: GenerateShortLinkInput!) {
  generateShortLink(input: $input) { shortLink }
}
# variables: { "input": { "originUrl": "<shopee product url>", "subIds": ["campaignTag"] } }
```
`subIds` are your tracking tags (up to 5 on the platform). Returns a short link
that attributes clicks/conversions to your affiliate account.

### Product offers (`offers`)
```graphql
query ($keyword: String, $limit: Int) {
  productOfferV2(keyword: $keyword, limit: $limit) {
    nodes { productName itemId commissionRate priceMin offerLink imageUrl }
  }
}
```
Find promotable products and their commission rates. There is also
`shopOfferV2` for shop-level offers if you need it.

### Conversion report (`report`)
```graphql
query ($start: Int, $end: Int) {
  conversionReport(purchaseTimeStart: $start, purchaseTimeEnd: $end) {
    nodes { orderId totalCommission conversionId purchaseTime }
  }
}
```
Times are unix seconds. Use it to see what your links earned.

## Notes / gotchas
- **Field names drift.** Shopee revises the affiliate schema periodically. If a
  query errors on an unknown field, fetch the current schema from the affiliate
  developer portal and adjust the query in `shopee_affiliate.py`. The auth
  signing is stable; the fields are what change.
- **Regional endpoints.** Some regions use a country-specific host. If you get
  auth/host errors, set `shopee_affiliate.base_url` in credentials.json to your
  region's GraphQL endpoint.
- Rate limits apply per app; back off on HTTP 429.
