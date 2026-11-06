# Bookkeeping handover kit

Handing your books to an outsourced bookkeeper takes four things: the documents they need (a trial balance, the last statement for every bank, card and loan account, the bank reconciliation, A/R and A/P aging), access to your systems by invite rather than shared passwords, a month-zero opening balance for every account, and proof that those opening balances tie to the last statements. With [ZeraBooks outsourced bookkeeping](https://www.zerabooks.com/outsourced-bookkeeping), our team does the books on our own AI bookkeeping ledger after a free first call, with a read-only login for you and an upload portal for documents.

This repo is that list as files anyone can use, with any bookkeeper: a 14-item document request, an 8-system access checklist, an opening balance template with a support document for every line, six fictional handover packets that tie, twelve that don't, and a Python checker.

- Templates: [`templates/document-request.csv`](templates/document-request.csv), [`templates/access-checklist.csv`](templates/access-checklist.csv), [`templates/opening-balances.csv`](templates/opening-balances.csv)
- Schemas: [`schema/`](schema/)
- Checker: [`cli/check_handover.py`](cli/check_handover.py) (Python 3.8+, standard library)
- Samples: [`samples/`](samples/), all fictional
- Release zip: [latest](https://github.com/ZeraBooks/bookkeeping-handover-kit/releases/latest)

## 1. Pick the cutover date

The cutover is the last day of the old books, usually the last day of the last month that was reconciled. Everything below is as of that date. The new bookkeeper starts on the day after.

## 2. Send the documents

[`templates/document-request.csv`](templates/document-request.csv) lists 14 documents, who has each one and why the new bookkeeper needs it. The ones people forget:

- **The bank reconciliation report**, not just the statement. It lists the checks and deposits that hadn't cleared. Without it, month one won't reconcile and nobody will know why.
- **Card statements that close before the cutover.** A card statement closing June 24 doesn't include June 25 to 30. Those charges are reconciling items.
- **The last tax return.** Retained earnings and depreciation should agree with what was filed.
- **Notes on anything odd.** Suspense balances, loans from the owner, known errors.

## 3. Grant access, the right way

[`templates/access-checklist.csv`](templates/access-checklist.csv) covers banks, cards, payroll, payment processors, the accounting software, bill pay, the sales tax portal and a shared upload folder. Two rules for every line:

- **Use the system's own invite** (accountant access, team user, delegate). Never send a password. An invite can be removed later; a shared password can't be taken back.
- **Remove the previous bookkeeper's access** on the same day.

## 4. Fill in the opening balances

[`templates/opening-balances.csv`](templates/opening-balances.csv) has one row per account with its balance on the cutover date and the document that supports it:

| support_type | Ties to |
|---|---|
| `bank_statement` | The last statement's closing balance, plus deposits in transit, minus outstanding checks |
| `card_statement`, `loan_statement` | The statement balance owed, plus charges after the statement date |
| `ar_aging`, `ap_aging` | The aging report's total |
| `payroll_report`, `sales_tax_report`, `fixed_asset_schedule`, `trial_balance` | That document |

List the reconciling items (outstanding checks, deposits in transit, card charges after the statement date) in `outstanding-items.csv`, signed from the book side: an outstanding check is negative, a deposit in transit positive, a card charge after the statement positive (more owed).

## 5. Check it

```bash
python3 cli/check_handover.py samples/handovers/juniper-lane-bakery
python3 cli/check_handover.py samples/handovers/*
python3 cli/check_handover.py my-packet/ --json
```

| ID | Check |
|---|---|
| HO-001 | `handover.json` and `opening-balances.csv` present |
| HO-002 | Opening debits equal credits |
| HO-003 | One side per row |
| HO-004 | Bank: statement + outstanding items = opening balance |
| HO-005 | Card and loan: statement + later charges = opening balance owed |
| HO-006 | The statement is the last one before the cutover (within 31 days) |
| HO-007 | A/R and A/P equal their aging reports |
| HO-008 | Every required document received or marked not applicable |
| HO-009 | Access by invite, granted, and the old bookkeeper's access removed (warnings) |
| HO-010 | Outstanding items dated on or before the cutover; anything over 90 days flagged |
| HO-011 | `reconciling_items_total` matches the items file |
| HO-012 | Every bank, card and loan account has a statement, balance and date |

The most common handover mistake is HO-004: opening cash taken straight from the bank statement.

```
$ python3 cli/check_handover.py samples/invalid/cash-equals-statement
ERROR   HO-004: 1000 Operating checking ...4471: statement 17398.73 + outstanding items -3806.94 = 13591.79, opening balance is 17398.73 (off by 3806.94)
```

Those three checks were written in June. When they clear in July, they'd hit cash a second time.

## Samples

`scripts/generate_samples.py` builds six fictional packets with a June 30, 2026 cutover: a bakery, a dental office, a landscaper, a freight company, a CPA practice and a property manager. Each has `handover.json` (documents received, access granted), `opening-balances.csv` (mid-year, so revenue and expenses carry year-to-date totals), `outstanding-items.csv`, `ar-aging.csv` and `ap-aging.csv`. Businesses without payroll or sales tax mark those documents not applicable.

| Folder | What |
|---|---|
| `samples/handovers/` | 6 packets that are ready for month one |
| `samples/invalid/` | 12 broken packets, one per rule, with `expected.json` |
| `samples/index.csv` | One row per packet |

## How ZeraBooks takes over books

With [ZeraBooks outsourced bookkeeping](https://www.zerabooks.com/outsourced-bookkeeping), our team records your transactions, reconciles your accounts and prepares your reports on our own [AI bookkeeping](https://www.zerabooks.com/ai-bookkeeping) ledger. You send statements, bills and invoices through an upload portal and get a read-only login to see the work as it's done. Plans start at $150 a month (USD) for businesses anywhere, priced after a free call; catch-up and cleanup are quoted on their own.

## Tests

```bash
python3 scripts/generate_samples.py
python3 -m unittest discover -s tests -v
```

## License and citation

Code MIT ([`LICENSE`](LICENSE)). Templates, samples, schemas and docs CC BY 4.0 ([`LICENSE-SAMPLES`](LICENSE-SAMPLES)). See [`CITATION.cff`](CITATION.cff). `MANIFEST.json` and `checksums.txt` list every data file with its SHA-256.

Related: [ZeraBooks/bookkeeping-onboarding-checklist](https://github.com/ZeraBooks/bookkeeping-onboarding-checklist) covers collecting every month's statements for a new client; [ZeraBooks/bank-reconciliation-proof-of-cash](https://github.com/ZeraBooks/bank-reconciliation-proof-of-cash) covers the monthly reconciliation that starts after the handover.
