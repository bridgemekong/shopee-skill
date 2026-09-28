#!/usr/bin/env python3
"""Shopee Open Platform (Seller) API client.

Capabilities:
  items — list the shop's product item ids
  item  — get base info for one item (name, price, status) + its public link

Auth (see references/shopee-open-platform-api.md): shop-level calls are signed
with HMAC-SHA256 over a base string:
    base = partner_id + api_path + timestamp + access_token + shop_id
    sign = HMAC_SHA256(partner_key, base)
and passed as query params: partner_id, timestamp, access_token, shop_id, sign.

The access_token comes from the shop-authorization flow (documented in the
reference) and is stored in credentials.json. Run with --check to validate
credentials without calling the network. Python 3 stdlib only.
"""
import argparse
import hashlib
import hmac
import time
import urllib.parse

import config
from common import http, emit


def _signed_url(cfg, api_path, extra_params=None):
    ts = int(time.time())
    partner_id = str(cfg["partner_id"])
    shop_id = str(cfg["shop_id"])
    token = cfg["access_token"]
    base = f"{partner_id}{api_path}{ts}{token}{shop_id}"
    sign = hmac.new(cfg["partner_key"].encode("utf-8"),
                    base.encode("utf-8"), hashlib.sha256).hexdigest()
    params = {
        "partner_id": partner_id,
        "timestamp": ts,
        "access_token": token,
        "shop_id": shop_id,
        "sign": sign,
    }
    params.update(extra_params or {})
    return f"{cfg['base_url']}{api_path}?{urllib.parse.urlencode(params)}"


def cmd_items(args):
    cfg = config.section("shopee_shop")
    api_path = "/api/v2/product/get_item_list"
    url = _signed_url(cfg, api_path, {
        "offset": args.offset, "page_size": args.limit, "item_status": "NORMAL",
    })
    if args.check:
        emit(True, dry_run=True, would_call=api_path)
    status, data = http("GET", url)
    if status == 200 and isinstance(data, dict) and not data.get("error"):
        resp = data.get("response", {})
        emit(True, has_next=resp.get("has_next_page"),
             items=resp.get("item", []), raw=data)
    emit(False, status=status, response=data)


def cmd_item(args):
    cfg = config.section("shopee_shop")
    api_path = "/api/v2/product/get_item_base_info"
    url = _signed_url(cfg, api_path, {"item_id_list": args.id})
    if args.check:
        emit(True, dry_run=True, would_call=api_path, item_id=args.id)
    status, data = http("GET", url)
    if status == 200 and isinstance(data, dict) and not data.get("error"):
        items = (data.get("response") or {}).get("item_list", [])
        link = f"https://shopee.com/product/{cfg['shop_id']}/{args.id}"
        emit(True, item=items[0] if items else None, product_link=link, raw=data)
    emit(False, status=status, response=data)


def main():
    p = argparse.ArgumentParser(description="Shopee Open Platform (Seller) API client")
    sub = p.add_subparsers(dest="cmd", required=True)

    pi = sub.add_parser("items", help="list shop item ids")
    pi.add_argument("--offset", type=int, default=0)
    pi.add_argument("--limit", type=int, default=50)
    pi.add_argument("--check", action="store_true")
    pi.set_defaults(func=cmd_items)

    pit = sub.add_parser("item", help="get one item's base info + link")
    pit.add_argument("--id", type=int, required=True, help="item_id")
    pit.add_argument("--check", action="store_true")
    pit.set_defaults(func=cmd_item)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
