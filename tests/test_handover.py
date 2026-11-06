import contextlib
import csv
import glob
import io
import json
import os
import sys
import unittest
from decimal import Decimal

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "cli"))
import check_handover as ch  # noqa: E402


class Packets(unittest.TestCase):
    def packets(self):
        return sorted(glob.glob(os.path.join(ROOT, "samples", "handovers", "*")))

    def test_every_packet_is_ready(self):
        self.assertEqual(len(self.packets()), 6)
        for p in self.packets():
            issues, _ = ch.check(p)
            self.assertEqual(issues, [], p)

    def test_cash_ties_by_hand(self):
        p = os.path.join(ROOT, "samples", "handovers", "juniper-lane-bakery")
        ob = {r["account_number"]: r for r in csv.DictReader(open(os.path.join(p, "opening-balances.csv")))}
        items = [Decimal(r["amount"]) for r in csv.DictReader(open(os.path.join(p, "outstanding-items.csv"))) if r["account_number"] == "1000"]
        self.assertEqual(Decimal(ob["1000"]["support_balance"]) + sum(items), Decimal(ob["1000"]["opening_debit"]))

    def test_invalid_packets_fail_their_rule(self):
        cases = json.load(open(os.path.join(ROOT, "samples", "invalid", "expected.json")))
        self.assertEqual(len(cases), 12)
        for c in cases:
            issues, _ = ch.check(os.path.join(ROOT, c["folder"]))
            self.assertIn(c["must_fail"], {i.rule for i in issues}, c["folder"])

    def test_templates_have_ids(self):
        reqs = list(csv.DictReader(open(os.path.join(ROOT, "templates", "document-request.csv"))))
        self.assertEqual(len({r["id"] for r in reqs}), len(reqs))
        self.assertTrue(all(r["required"] for r in reqs))
        acc = list(csv.DictReader(open(os.path.join(ROOT, "templates", "access-checklist.csv"))))
        self.assertTrue(all(r["revoke_old_access"].startswith("Yes") for r in acc))

    def test_cli(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(ch.main(self.packets()), 0)
            self.assertEqual(ch.main([os.path.join(ROOT, "samples", "invalid", "cash-equals-statement")]), 1)


if __name__ == "__main__":
    unittest.main()
