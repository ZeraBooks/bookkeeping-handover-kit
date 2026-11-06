#!/usr/bin/env python3
"""Check a bookkeeping handover packet before month one starts.

    python3 cli/check_handover.py samples/handovers/juniper-lane-bakery
    python3 cli/check_handover.py samples/handovers/*  --json

A packet folder holds handover.json, opening-balances.csv and, as needed,
outstanding-items.csv, ar-aging.csv and ap-aging.csv (see schema/ and
templates/). The main check: every bank, card and loan opening balance ties
to the last statement through the listed outstanding items, and A/R and A/P
tie to their aging reports. Exit 0 = ready, 1 = errors, 2 = can't read.

Part of https://github.com/ZeraBooks/bookkeeping-handover-kit
(ZeraBooks, https://www.zerabooks.com/outsourced-bookkeeping).
"""
import argparse
import csv
import datetime as dt
import json
import os
import sys
from decimal import Decimal

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D0 = Decimal("0")
STATEMENT_TYPES = {"bank_statement", "card_statement", "loan_statement"}


class Issue:
    def __init__(self, rule, severity, message):
        self.rule, self.severity, self.message = rule, severity, message

    def __repr__(self):
        return f"{self.severity.upper():7} {self.rule}: {self.message}"


def dec(v):
    return Decimal(v) if v and v.strip() else D0


def read(path):
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8-sig", newline="") as fh:
        return [{k: (v or "").strip() for k, v in r.items()} for r in csv.DictReader(fh)]


def requests():
    return read(os.path.join(ROOT, "templates", "document-request.csv"))


def check(folder):
    issues = []
    hp = os.path.join(folder, "handover.json")
    ob = read(os.path.join(folder, "opening-balances.csv"))
    if not os.path.exists(hp) or ob is None:
        return [Issue("HO-001", "error", "handover.json and opening-balances.csv are both needed")], {}
    h = json.load(open(hp, encoding="utf-8"))
    cutover = dt.date.fromisoformat(h["cutover_date"])
    items = read(os.path.join(folder, "outstanding-items.csv")) or []
    td = tc = D0
    for r in ob:
        d, c = dec(r["opening_debit"]), dec(r["opening_credit"])
        if d and c:
            issues.append(Issue("HO-003", "error", f"{r['account_number']} {r['account_name']} has both a debit and a credit"))
        td += d
        tc += c
    if td != tc:
        issues.append(Issue("HO-002", "error", f"opening debits {td} vs credits {tc} (off by {td - tc})"))

    by_acct = {}
    for it in items:
        by_acct.setdefault(it["account_number"], []).append(it)
        day = dt.date.fromisoformat(it["date"])
        if day > cutover:
            issues.append(Issue("HO-010", "error", f"outstanding item {it['ref']} {it['amount']} is dated {day}, after the cutover"))
        elif (cutover - day).days > 90:
            issues.append(Issue("HO-010", "warning", f"{it['description']} {it['amount']} from {day} has been outstanding over 90 days: ask whether to void it"))

    for r in ob:
        st = r["support_type"]
        acct = r["account_number"]
        label = f"{acct} {r['account_name']}"
        net = dec(r["opening_debit"]) - dec(r["opening_credit"])
        recon = sum((dec(i["amount"]) for i in by_acct.get(acct, [])), D0)
        if r.get("reconciling_items_total", "") and dec(r["reconciling_items_total"]) != recon:
            issues.append(Issue("HO-011", "error", f"{label}: reconciling_items_total says {r['reconciling_items_total']}, outstanding-items.csv adds to {recon}"))
        if st in STATEMENT_TYPES:
            if not r["support_document"] or not r["support_balance"] or not r["support_date"]:
                issues.append(Issue("HO-012", "error", f"{label}: no statement document, balance or date"))
                continue
            sdate = dt.date.fromisoformat(r["support_date"])
            if sdate > cutover or (cutover - sdate).days > 31:
                issues.append(Issue("HO-006", "error", f"{label}: statement dated {sdate} isn't the last one before the {cutover} cutover"))
            printed = dec(r["support_balance"])
            if st == "bank_statement":
                book = printed + recon
                if net != book:
                    issues.append(Issue("HO-004", "error", f"{label}: statement {printed} + outstanding items {recon} = {book}, opening balance is {net} (off by {net - book})"))
            else:
                owed = -net
                book = printed + recon
                if owed != book:
                    issues.append(Issue("HO-005", "error", f"{label}: statement owes {printed} + items {recon} = {book}, opening balance owes {owed} (off by {owed - book})"))
        elif st in ("ar_aging", "ap_aging"):
            rows = read(os.path.join(folder, "ar-aging.csv" if st == "ar_aging" else "ap-aging.csv"))
            if rows is None:
                issues.append(Issue("HO-007", "error", f"{label}: {st.replace('_', ' ')} file is missing"))
                continue
            total = sum((dec(x["open_balance"]) for x in rows), D0)
            bal = net if st == "ar_aging" else -net
            if total != bal:
                issues.append(Issue("HO-007", "error", f"{label}: aging adds to {total}, opening balance is {bal} (off by {bal - total})"))
            if r["support_balance"] and dec(r["support_balance"]) != total:
                issues.append(Issue("HO-007", "error", f"{label}: support_balance {r['support_balance']} vs aging rows {total}"))

    got = set(h.get("documents_received", [])) | set(h.get("documents_not_applicable", []))
    for d in requests():
        if d["id"] not in got:
            sev = "error" if d["required"] == "yes" else "warning"
            issues.append(Issue("HO-008", sev, f"{d['id']} {d['document']}: not received and not marked not applicable"))
    for a in h.get("access", []):
        if a.get("method") == "shared_password":
            issues.append(Issue("HO-009", "warning", f"{a['id']}: access by a shared password. Use the system's own invite so access can be removed later"))
        if not a.get("old_access_revoked"):
            issues.append(Issue("HO-009", "warning", f"{a['id']}: the previous bookkeeper's access hasn't been removed"))
        if not a.get("granted"):
            issues.append(Issue("HO-009", "warning", f"{a['id']}: access not granted yet"))
    return issues, {"business": h["business"], "cutover": h["cutover_date"], "accounts": len(ob), "opening_total": str(td), "outstanding_items": len(items)}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Check a bookkeeping handover packet.")
    ap.add_argument("folder", nargs="+")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    worst, out = 0, []
    for f in a.folder:
        try:
            issues, s = check(f)
        except (OSError, ValueError, KeyError) as exc:
            print(f"could not read {f}: {exc}", file=sys.stderr)
            worst = 2
            continue
        errors = [i for i in issues if i.severity == "error"]
        worst = max(worst, 1 if errors else 0)
        if a.json:
            out.append({"folder": f, "ok": not errors, "summary": s, "issues": [vars(i) for i in issues]})
        else:
            for i in issues:
                print(i)
            print(f"{f}: " + ("ready for month one" if not errors else f"{len(errors)} error(s)"))
    if a.json:
        print(json.dumps(out, indent=2))
    return worst


if __name__ == "__main__":
    sys.exit(main())
