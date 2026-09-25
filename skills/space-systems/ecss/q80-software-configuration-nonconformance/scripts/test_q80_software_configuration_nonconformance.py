"""Contract tests for the software configuration and nonconformance logic."""

import hashlib
import unittest

from q80_software_configuration_nonconformance_logic import (
    CONTROLLED_FAMILIES,
    SCMP_PROVISIONS,
    check_controlled_documents,
    check_delivery,
    check_ncr_disposition,
    check_scf_currency,
    check_scm_plan,
    integrity_value,
    qualifies_as_nonconformance,
    spr_transition,
)

IMAGE = b"OBSW build 3.4.1"


def _delivery(**over):
    d = {"name": "OBSW", "version": "3.4.1", "scf_ref": "SCF-12", "release_document": "SRelD-12",
         "distribution_caveats": "none",
         "integrity": {"algorithm": "sha256", "value": hashlib.sha256(IMAGE).hexdigest()}}
    d.update(over)
    return d


class PlanTests(unittest.TestCase):
    def test_generator_provision_only_when_used(self):
        full = {k: "s.%d" % i for i, k in enumerate(SCMP_PROVISIONS)}
        del full["generator-customisation-under-control"]
        self.assertEqual(check_scm_plan(full), [])
        self.assertEqual(check_scm_plan(full, uses_code_generator=True),
                         ["generator-customisation-under-control"])

    def test_empty_plan(self):
        self.assertEqual(len(check_scm_plan({})), len(SCMP_PROVISIONS) - 1)


class DocumentTests(unittest.TestCase):
    def test_register(self):
        reg = [{"id": "D1", "family": "planning", "controlled": True},
               {"id": "D2", "family": "traceability-matrices", "controlled": False},
               {"id": "D3", "family": "slides"}]
        res = check_controlled_documents(reg)
        self.assertEqual(res["uncontrolled"], ["D2"])
        self.assertEqual(res["unknown_family"], ["D3"])
        self.assertIn("retirement-docs", res["missing_families"])
        self.assertEqual(len(res["missing_families"]), len(CONTROLLED_FAMILIES) - 2)


class DeliveryTests(unittest.TestCase):
    def test_good_delivery(self):
        res = check_delivery(_delivery(), IMAGE)
        self.assertEqual(res["verdict"], "accept")
        self.assertEqual(res["recomputed"], integrity_value(IMAGE))

    def test_corrupted_bytes(self):
        res = check_delivery(_delivery(), IMAGE + b"!")
        self.assertIn("integrity value does not match the delivered bytes", res["findings"])

    def test_missing_label_items(self):
        res = check_delivery(_delivery(release_document="", distribution_caveats=""),
                             marking_required=True)
        self.assertEqual(res["verdict"], "reject")
        self.assertEqual(len(res["findings"]), 3)

    def test_unsupported_algorithm(self):
        with self.assertRaises(ValueError):
            integrity_value(b"x", "md5")


class ScfTests(unittest.TestCase):
    def test_currency(self):
        res = check_scf_currency({"cdr": "BL-2", "qr": "BL-3"},
                                 {"cdr": "BL-2", "qr": "BL-4"}, "ar")
        self.assertEqual(res, [("qr", "file describes BL-3, baseline presented is BL-4"),
                               ("ar", "no configuration file")])
        self.assertEqual(check_scf_currency({}, {}, "pdr"), [])


class SprTests(unittest.TestCase):
    def test_full_path(self):
        spr = {"state": "open", "item": "OBSW", "description": "TM gap",
               "recommended_solution": "fix buffer", "final_disposition": "fix",
               "modifications": "tm.c r512", "tests_rerun": "VAL-TM-*"}
        for st in ("analysed", "dispositioned", "implemented", "verified", "closed"):
            spr = spr_transition(spr, st)
        self.assertEqual(spr["state"], "closed")

    def test_illegal_and_incomplete(self):
        with self.assertRaises(ValueError):
            spr_transition({"state": "open"}, "closed")
        with self.assertRaises(ValueError):
            spr_transition({"state": "verified", "item": "x"}, "closed")
        with self.assertRaises(ValueError):
            spr_transition({"state": "open"}, "rejected")

    def test_use_as_is_closes_without_fix(self):
        spr = {"state": "dispositioned", "item": "x", "description": "cosmetic",
               "final_disposition": "use-as-is"}
        self.assertEqual(spr_transition(spr, "closed")["state"], "closed")


class NcrTests(unittest.TestCase):
    def test_interface(self):
        self.assertFalse(qualifies_as_nonconformance({"baselined": True}, "cdr", "pdr")[0])
        self.assertEqual(qualifies_as_nonconformance({"procured": True}, "pdr", "cdr"),
                         (True, "problem in procured software"))
        self.assertFalse(qualifies_as_nonconformance({}, "pdr", "qr")[0])

    def test_disposition_checks(self):
        roles = ["software-product-assurance", "software-engineering"]
        self.assertEqual(check_ncr_disposition({"disposition": "fix", "fix_kind": "patch"}, roles), [])
        self.assertIn("return to supplier used for software that was not procured",
                      check_ncr_disposition({"disposition": "return-to-supplier"}, roles))
        found = check_ncr_disposition({"disposition": "use-as-is",
                                       "possible_security_impact": True}, ["software-engineering"])
        self.assertEqual(len(found), 3)


if __name__ == "__main__":
    unittest.main()
