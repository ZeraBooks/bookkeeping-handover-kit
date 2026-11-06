"""Generate fictional handover packets in samples/handovers/.

    python3 scripts/generate_samples.py

Six fictional businesses moving to an outsourced bookkeeper with a June 30,
2026 cutover. Each packet ties: bank opening balances = last statement +
deposits in transit - outstanding checks, card and loan balances = statement
+ charges after the statement date, A/R and A/P = their aging reports, and
opening debits = credits. samples/invalid/ gets one broken packet per rule.
Seeded, so the files are the same every run.
"""
import csv
import datetime as dt
import json
import os
import random
import shutil
from decimal import Decimal

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "samples")
CUT = dt.date(2026, 6, 30)
OB_COLS = ["account_number", "account_name", "account_type", "opening_debit", "opening_credit", "support_type", "support_document",
           "support_balance", "support_date", "reconciling_items_total", "notes"]
IT_COLS = ["account_number", "date", "ref", "description", "amount"]
AG_COLS = ["number", "party", "date", "due_date", "original_amount", "open_balance"]
BIZ = [
    ("juniper-lane-bakery", "Juniper Lane Bakery LLC", 1.0, True, True),
    ("okafor-family-dental", "Okafor Family Dental PC", 2.0, True, False),
    ("brightwater-landscaping", "Brightwater Landscaping Inc", 1.4, False, True),
    ("redline-freight", "Redline Freight Co", 2.6, True, True),
    ("vega-cpa", "Marisol Vega CPA", 0.6, False, False),
    ("ironwood-property", "Ironwood Property Management", 1.2, True, True),
]
PARTIES_AR = ["Blue Ridge HOA", "Hartwell Manufacturing", "Lakeview Clinic", "Ortega Holdings", "Pinecrest Schools"]
PARTIES_AP = ["Sysco Foods", "Valley Propane Co", "Grainger", "Hartwell Insurance Agency", "Riverbend Printing"]


def m(rng, lo, hi, s):
    return (Decimal(rng.randint(int(lo * 100), int(hi * 100))) * Decimal(str(s)) / 100).quantize(Decimal("0.01"))


def write(path, cols, rows):
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, lineterminator="\r\n")
        w.writeheader()
        w.writerows(rows)


def row(num, name, typ, bal, st, doc="", sbal="", sdate="", recon="", notes=""):
    return {"account_number": num, "account_name": name, "account_type": typ, "opening_debit": f"{bal:.2f}" if bal > 0 else "",
            "opening_credit": f"{-bal:.2f}" if bal < 0 else "", "support_type": st, "support_document": doc, "support_balance": sbal,
            "support_date": sdate, "reconciling_items_total": recon, "notes": notes}


def packet(rng, slug, name, s, payroll, sales_tax):
    items, ob = [], []
    # Checking: statement through June 30, two checks and a deposit outstanding.
    stmt = m(rng, 12000, 40000, s)
    chk = [(-m(rng, 200, 2500, s), dt.date(2026, 6, rng.randint(22, 29)), str(rng.randint(1040, 1990))) for _ in range(rng.randint(1, 3))]
    dep = m(rng, 500, 4000, s)
    for amt, d, ref in chk:
        items.append({"account_number": "1000", "date": d.isoformat(), "ref": ref, "description": f"Check {ref}", "amount": f"{amt:.2f}"})
    items.append({"account_number": "1000", "date": CUT.isoformat(), "ref": "", "description": "Deposit made after the bank's cutoff", "amount": f"{dep:.2f}"})
    recon = sum(a for a, _, _ in chk) + dep
    cash = stmt + recon
    ob.append(row("1000", "Operating checking ...4471", "asset", cash, "bank_statement", "checking-2026-06.pdf", f"{stmt:.2f}", CUT.isoformat(), f"{recon:.2f}"))
    sav = m(rng, 5000, 25000, s)
    ob.append(row("1010", "Savings ...0932", "asset", sav, "bank_statement", "savings-2026-06.pdf", f"{sav:.2f}", CUT.isoformat(), "0.00"))
    ar = []
    for i in range(rng.randint(3, 7)):
        d = CUT - dt.timedelta(days=rng.randint(3, 70))
        amt = m(rng, 400, 5000, s)
        open_ = amt if rng.random() < 0.8 else (amt / 2).quantize(Decimal("0.01"))
        ar.append({"number": f"INV-{2100 + i}", "party": rng.choice(PARTIES_AR), "date": d.isoformat(), "due_date": (d + dt.timedelta(days=30)).isoformat(),
                   "original_amount": f"{amt:.2f}", "open_balance": f"{open_:.2f}"})
    ar_total = sum(Decimal(x["open_balance"]) for x in ar)
    ob.append(row("1100", "Accounts receivable", "asset", ar_total, "ar_aging", "ar-aging-2026-06-30.pdf", f"{ar_total:.2f}"))
    eq = m(rng, 30000, 70000, s)
    ob.append(row("1500", "Equipment", "asset", eq, "fixed_asset_schedule", "fixed-assets-2025.xlsx"))
    acc = -m(rng, 5000, 20000, s)
    ob.append(row("1510", "Accumulated depreciation", "asset", acc, "fixed_asset_schedule", "fixed-assets-2025.xlsx", notes="Through June 30 per schedule"))
    ap = []
    for i in range(rng.randint(2, 5)):
        d = CUT - dt.timedelta(days=rng.randint(2, 40))
        amt = m(rng, 200, 3000, s)
        ap.append({"number": f"B-{rng.randint(10000, 99999)}", "party": rng.choice(PARTIES_AP), "date": d.isoformat(),
                   "due_date": (d + dt.timedelta(days=30)).isoformat(), "original_amount": f"{amt:.2f}", "open_balance": f"{amt:.2f}"})
    ap_total = sum(Decimal(x["open_balance"]) for x in ap)
    ob.append(row("2000", "Accounts payable", "liability", -ap_total, "ap_aging", "ap-aging-2026-06-30.pdf", f"{ap_total:.2f}"))
    # Card statement closes June 24; charges after that are reconciling items.
    card_stmt = m(rng, 800, 5000, s)
    after = [m(rng, 30, 600, s) for _ in range(rng.randint(1, 4))]
    for i, a in enumerate(after):
        items.append({"account_number": "2100", "date": dt.date(2026, 6, 25 + i).isoformat(), "ref": "", "description": "Card charge after the statement closed", "amount": f"{a:.2f}"})
    card = card_stmt + sum(after)
    ob.append(row("2100", "Business card ...9014", "liability", -card, "card_statement", "card-2026-06-24.pdf", f"{card_stmt:.2f}", "2026-06-24", f"{sum(after):.2f}"))
    if payroll:
        pl = m(rng, 1500, 6000, s)
        ob.append(row("2200", "Payroll liabilities", "liability", -pl, "payroll_report", "payroll-liabilities-2026-06-30.pdf", f"{pl:.2f}"))
    if sales_tax:
        stx = m(rng, 600, 3000, s)
        ob.append(row("2300", "Sales tax payable", "liability", -stx, "sales_tax_report", "sales-tax-liability-2026-06.pdf", f"{stx:.2f}"))
    loan = m(rng, 12000, 40000, s)
    ob.append(row("2700", "Equipment loan", "liability", -loan, "loan_statement", "loan-2026-06.pdf", f"{loan:.2f}", "2026-06-28", "0.00"))
    cap = m(rng, 10000, 20000, s)
    ob.append(row("3000", "Owner's capital", "equity", -cap, "trial_balance", "trial-balance-2026-06-30.pdf"))
    # Year-to-date P&L, so the trial balance is mid-year.
    rev = m(rng, 120000, 200000, s)
    exp = (rev * Decimal(str(rng.uniform(0.7, 0.9)))).quantize(Decimal("0.01"))
    ob.append(row("4000", "Revenue (year to date)", "revenue", -rev, "trial_balance", "trial-balance-2026-06-30.pdf"))
    ob.append(row("6000", "Expenses (year to date)", "expense", exp, "trial_balance", "trial-balance-2026-06-30.pdf", notes="Total of expense accounts; detail in the trial balance"))
    total = sum((Decimal(r["opening_debit"] or 0) - Decimal(r["opening_credit"] or 0)) for r in ob)
    if total < 5000:
        # Keep retained earnings a credit: more cash in savings.
        bump = Decimal(5000) - total + m(rng, 1000, 8000, s)
        r = next(x for x in ob if x["account_number"] == "1010")
        r["opening_debit"] = r["support_balance"] = f"{Decimal(r['opening_debit']) + bump:.2f}"
        total += bump
    ob.append(row("3900", "Retained earnings", "equity", -total, "trial_balance", "trial-balance-2026-06-30.pdf", notes="Prior years' retained earnings per the last tax return"))
    ob.sort(key=lambda r: r["account_number"])
    return ob, items, ar, ap


def main():
    rng = random.Random(20261105)
    for sub in ("handovers", "invalid"):
        shutil.rmtree(os.path.join(OUT, sub), ignore_errors=True)
        os.makedirs(os.path.join(OUT, sub))
    reqs = list(csv.DictReader(open(os.path.join(ROOT, "templates", "document-request.csv"), encoding="utf-8")))
    acc = list(csv.DictReader(open(os.path.join(ROOT, "templates", "access-checklist.csv"), encoding="utf-8")))
    index = []
    for slug, name, s, payroll, sales_tax in BIZ:
        ob, items, ar, ap = packet(rng, slug, name, s, payroll, sales_tax)
        f = os.path.join(OUT, "handovers", slug)
        os.makedirs(f)
        write(os.path.join(f, "opening-balances.csv"), OB_COLS, ob)
        write(os.path.join(f, "outstanding-items.csv"), IT_COLS, items)
        write(os.path.join(f, "ar-aging.csv"), AG_COLS, ar)
        write(os.path.join(f, "ap-aging.csv"), AG_COLS, ap)
        na = [d["id"] for d in reqs if (d["id"] == "D08" and not payroll) or (d["id"] == "D09" and not sales_tax)]
        h = {"business": name, "cutover_date": CUT.isoformat(), "first_month": "2026-07", "previous_bookkeeper": "Fictional in-house bookkeeper",
             "documents_received": [d["id"] for d in reqs if d["id"] not in na], "documents_not_applicable": na,
             "access": [{"id": a["id"], "system": a["system"], "granted": True, "method": "invite", "old_access_revoked": True} for a in acc],
             "fictional": True}
        json.dump(h, open(os.path.join(f, "handover.json"), "w", encoding="utf-8"), indent=2)
        index.append([slug, name, len(ob), len(items), len(ar), len(ap), sum(Decimal(r["opening_debit"] or 0) for r in ob)])
    with open(os.path.join(OUT, "index.csv"), "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\r\n")
        w.writerow(["packet", "business", "accounts", "outstanding_items", "open_invoices", "open_bills", "opening_total_debits"])
        w.writerows([r[:-1] + [f"{r[-1]:.2f}"] for r in index])
    make_invalid()
    print(f"{len(index)} packets")


def make_invalid():
    base = os.path.join(OUT, "handovers", "juniper-lane-bakery")
    cases = []

    def case(name, rule, why, fn):
        f = os.path.join(OUT, "invalid", name)
        shutil.copytree(base, f)
        fn(f)
        cases.append({"folder": f"samples/invalid/{name}", "must_fail": rule, "what_is_wrong": why})

    def edit(f, fname, cols, fn):
        p = os.path.join(f, fname)
        rows = list(csv.DictReader(open(p, encoding="utf-8")))
        fn(rows)
        write(p, cols, rows)

    def edit_h(f, fn):
        p = os.path.join(f, "handover.json")
        h = json.load(open(p))
        fn(h)
        json.dump(h, open(p, "w"), indent=2)

    def setrow(rows, num, **kw):
        next(r for r in rows if r["account_number"] == num).update(kw)

    case("no-opening-balances", "HO-001", "opening-balances.csv missing", lambda f: os.remove(os.path.join(f, "opening-balances.csv")))
    case("does-not-balance", "HO-002", "savings typed $100 high with nothing to offset it",
         lambda f: edit(f, "opening-balances.csv", OB_COLS, lambda r: setrow(r, "1010", opening_debit=f"{Decimal(next(x for x in r if x['account_number'] == '1010')['opening_debit']) + 100:.2f}")))
    case("both-sides", "HO-003", "a row with a debit and a credit",
         lambda f: edit(f, "opening-balances.csv", OB_COLS, lambda r: setrow(r, "1500", opening_credit="10.00")))

    def cash_from_statement(rows):
        r = next(x for x in rows if x["account_number"] == "1000")
        diff = Decimal(r["support_balance"]) - Decimal(r["opening_debit"])
        r["opening_debit"] = r["support_balance"]
        re_ = next(x for x in rows if x["account_number"] == "3900")
        re_["opening_credit"] = f"{Decimal(re_['opening_credit']) + diff:.2f}"
    case("cash-equals-statement", "HO-004", "opening cash taken straight from the statement, ignoring outstanding checks and the late deposit",
         lambda f: edit(f, "opening-balances.csv", OB_COLS, cash_from_statement))
    case("card-charges-missing", "HO-005", "card charges after the statement date left out of the items list",
         lambda f: edit(f, "outstanding-items.csv", IT_COLS, lambda r: [r.remove(x) for x in [y for y in r if y["account_number"] == "2100"]]))
    case("old-statement", "HO-006", "the checking statement is from April, not the last one before cutover",
         lambda f: edit(f, "opening-balances.csv", OB_COLS, lambda r: setrow(r, "1000", support_date="2026-04-30")))
    case("aging-short", "HO-007", "the A/R aging is missing an invoice that's in the opening balance",
         lambda f: edit(f, "ar-aging.csv", AG_COLS, lambda r: r.pop(0)))
    case("missing-documents", "HO-008", "no bank reconciliation report and no trial balance received",
         lambda f: edit_h(f, lambda h: h.update(documents_received=[d for d in h["documents_received"] if d not in ("D01", "D03")])))

    def pw(h):
        h["access"][0]["method"] = "shared_password"
        h["access"][4]["old_access_revoked"] = False
    case("shared-password", "HO-009", "bank access by a shared password and the old bookkeeper still in the software (warnings)", lambda f: edit_h(f, pw))
    case("stale-check", "HO-010", "a check from February still listed as outstanding (warning)",
         lambda f: (edit(f, "outstanding-items.csv", IT_COLS, lambda r: r[0].update(date="2026-02-10"))))
    case("items-total-wrong", "HO-011", "reconciling_items_total doesn't match the items file",
         lambda f: edit(f, "opening-balances.csv", OB_COLS, lambda r: setrow(r, "1000", reconciling_items_total="0.00")))
    case("no-statement", "HO-012", "the loan has no statement attached",
         lambda f: edit(f, "opening-balances.csv", OB_COLS, lambda r: setrow(r, "2700", support_document="", support_balance="", support_date="")))
    json.dump(cases, open(os.path.join(OUT, "invalid", "expected.json"), "w"), indent=2)


if __name__ == "__main__":
    main()
