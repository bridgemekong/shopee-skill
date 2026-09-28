#!/usr/bin/env python3
"""Shopee Affiliate Open API client.

Capabilities:
  link    — generate a tracked affiliate short link from a product URL
  offers  — search promotable product offers by keyword
  report  — pull a conversion report

Auth (see references/shopee-affiliate-api.md): the API is GraphQL over a single
endpoint. Each request is signed with:
    signature = SHA256(app_id + timestamp + payload + secret)
and sent as:
    Authorization: SHA256 Credential=<app_id>, Timestamp=<ts>, Signature=<sig>

Run with --check to validate credentials without calling the network.
Python 3 stdlib only.
"""
import argparse
import hashlib
import json
import time

import config
from common import http, emit


def _signed_headers(app_id, secret, payload):
    ts = int(time.time())
    base = f"{app_id}{ts}{payload}{secret}"
    sig = hashlib.sha256(base.encode("utf-8")).hexdigest()
    return {
        "Content-Type": "application/json",
        "Authorization": f"SHA256 Credential={app_id}, Timestamp={ts}, Signature={sig}",
    }


def _graphql(cfg, query, variables=None):
    payload = json.dumps({"query": query, "variables": variables or {}},
                         separators=(",", ":"), ensure_ascii=False)
    headers = _signed_headers(cfg["app_id"], cfg["secret"], payload)
    status, data = http("POST", cfg["base_url"], headers=headers, body=payload)
    return status, data


def cmd_link(args):
    cfg = config.section("shopee_affiliate")
    sub_ids = [args.sub_id] if args.sub_id else []
    query = """
    mutation ($input: GenerateShortLinkInput!) {
      generateShortLink(input: $input) { shortLink }
    }"""
    variables = {"input": {"originUrl": args.url, "subIds": sub_ids}}
    if args.check:
        emit(True, dry_run=True, would_send={"query": "generateShortLink", "variables": variables})
    status, data = _graphql(cfg, query, variables)
    if status == 200 and isinstance(data, dict) and not data.get("errors"):
        link = (data.get("data") or {}).get("generateShortLink", {}).get("shortLink")
        emit(True, short_link=link, raw=data)
    emit(False, status=status, response=data)


def cmd_offers(args):
    cfg = config.section("shopee_affiliate")
    query = """
    query ($keyword: String, $limit: Int) {
      productOfferV2(keyword: $keyword, limit: $limit) {
        nodes { productName itemId commissionRate priceMin offerLink imageUrl }
      }
    }"""
    variables = {"keyword": args.keyword, "limit": args.limit}
    if args.check:
        emit(True, dry_run=True, would_send={"query": "productOfferV2", "variables": variables})
    status, data = _graphql(cfg, query, variables)
    if status == 200 and isinstance(data, dict) and not data.get("errors"):
        nodes = (data.get("data") or {}).get("productOfferV2", {}).get("nodes", [])
        emit(True, count=len(nodes), offers=nodes)
    emit(False, status=status, response=data)


def cmd_report(args):
    cfg = config.section("shopee_affiliate")
    query = """
    query ($start: Int, $end: Int) {
      conversionReport(purchaseTimeStart: $start, purchaseTimeEnd: $end) {
        nodes { orderId totalCommission conversionId purchaseTime }
      }
    }"""
    variables = {"start": args.start, "end": args.end}
    if args.check:
        emit(True, dry_run=True, would_send={"query": "conversionReport", "variables": variables})
    status, data = _graphql(cfg, query, variables)
    if status == 200 and isinstance(data, dict) and not data.get("errors"):
        nodes = (data.get("data") or {}).get("conversionReport", {}).get("nodes", [])
        emit(True, count=len(nodes), conversions=nodes)
    emit(False, status=status, response=data)


def main():
    p = argparse.ArgumentParser(description="Shopee Affiliate Open API client")
    sub = p.add_subparsers(dest="cmd", required=True)

    pl = sub.add_parser("link", help="generate a tracked affiliate short link")
    pl.add_argument("--url", required=True, help="Shopee product URL")
    pl.add_argument("--sub-id", help="campaign / sub_id tracking tag")
    pl.add_argument("--check", action="store_true", help="validate only, no network call")
    pl.set_defaults(func=cmd_link)

    po = sub.add_parser("offers", help="search promotable product offers")
    po.add_argument("--keyword", required=True)
    po.add_argument("--limit", type=int, default=20)
    po.add_argument("--check", action="store_true")
    po.set_defaults(func=cmd_offers)

    pr = sub.add_parser("report", help="conversion report (unix seconds range)")
    pr.add_argument("--start", type=int, required=True, help="purchase time start (unix seconds)")
    pr.add_argument("--end", type=int, required=True, help="purchase time end (unix seconds)")
    pr.add_argument("--check", action="store_true")
    pr.set_defaults(func=cmd_report)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
