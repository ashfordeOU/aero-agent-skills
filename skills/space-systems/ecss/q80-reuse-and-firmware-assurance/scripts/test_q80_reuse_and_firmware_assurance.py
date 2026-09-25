"""Contract tests for the reuse and firmware assurance logic."""

import hashlib
import unittest

from q80_reuse_and_firmware_assurance_logic import (
    QUALITY_EVIDENCE,
    SECURITY_ASPECTS,
    SERVICE_HISTORY_ITEMS,
    SUITABILITY_ASPECTS,
    categorize_existing,
    check_intended_reuse,
    check_licences,
    check_programmable_device,
    choose_recovery,
    grade_existing_software,
    grade_service_history,
)

BITSTREAM = b"fpga bitstream rev C"


def _device(**over):
    d = {"programming_procedure": True, "duplication_procedure": True,
         "marking_hw_ref": "PN-77", "marking_sw_ref": "FW-3.1", "marking_indelible": True,
         "programmed_on": "2026-03-01", "calibration_valid_until": "2026-06-30",
         "scf_digest": hashlib.sha256(BITSTREAM).hexdigest()}
    d.update(over)
    return d


class CategorizeTests(unittest.TestCase):
    def test_kinds(self):
        self.assertEqual(categorize_existing({"origin": "open-source"}), "open-source")
        self.assertEqual(categorize_existing({"origin": "cots", "is_tool": True}), "tool")
        with self.assertRaises(ValueError):
            categorize_existing({"origin": "found-on-a-disk"})


class GradeTests(unittest.TestCase):
    def test_full(self):
        item = {"evidence": set(QUALITY_EVIDENCE), "suitability": set(SUITABILITY_ASPECTS),
                "security": set(SECURITY_ASPECTS), "benefit_analysis": True}
        res = grade_existing_software(item, "B", sensitive=True)
        self.assertEqual(res["level"], "full")
        self.assertEqual(res["corrective_actions"], [])

    def test_category_d_relaxes_unit_tests(self):
        ev = set(QUALITY_EVIDENCE) - {"unit-tests-and-coverage"}
        item = {"evidence": ev, "suitability": set(SUITABILITY_ASPECTS),
                "security": {"authorisation-for-use", "security-sensitivity"},
                "benefit_analysis": True}
        self.assertEqual(grade_existing_software(item, "D")["level"], "full")
        self.assertIn("unit-tests-and-coverage", grade_existing_software(item, "C")["quality_gaps"])

    def test_insufficient_and_security(self):
        res = grade_existing_software({"evidence": {"user-doc"}}, "A", sensitive=True)
        self.assertEqual(res["level"], "insufficient")
        self.assertEqual(res["security_gaps"], list(SECURITY_ASPECTS))
        self.assertIn("record why reuse is preferred over new development",
                      res["corrective_actions"])


class RecoveryTests(unittest.TestCase):
    def test_choose(self):
        self.assertEqual(choose_recovery(False, True), ["reverse-engineering"])
        self.assertEqual(choose_recovery(False, False),
                         ["user-doc-based-vv-and-testing", "service-history"])

    def test_service_history(self):
        hist = {k: "documented" for k in SERVICE_HISTORY_ITEMS}
        hist.update(operating_hours=50000, errors_found=5)
        res = grade_service_history(hist)
        self.assertTrue(res["usable"])
        self.assertEqual(res["error_rate_per_1000h"], 0.1)
        self.assertFalse(grade_service_history({"operating_hours": 10})["usable"])


class LicenceTests(unittest.TestCase):
    def test_distribution_rules(self):
        comps = {"libfoo": "GPL-2.0-only", "libbar": "LGPL-2.1-only", "libbaz": "MIT",
                 "blob": "", "odd": "SSPL-1.0"}
        internal = dict(check_licences(comps, "internal", modified=["libbar"]))
        self.assertNotIn("libfoo", internal)
        self.assertIn("blob", internal)
        shipped = dict(check_licences(comps, "binary-to-customer", modified=["libbar"]))
        self.assertIn("libfoo", shipped)
        self.assertIn("libbar", shipped)
        self.assertNotIn("libbaz", shipped)
        self.assertIn("legal review", shipped["odd"])

    def test_agpl_even_internal(self):
        self.assertEqual(len(check_licences({"x": "AGPL-3.0-only"}, "internal")), 1)


class IntendedReuseTests(unittest.TestCase):
    def test_platform_limitation(self):
        comp = {"separate_docs": True, "self_contained_docs": True,
                "ts_requirements": {"maintainability", "portability", "verification"},
                "cm_provisions": {"long-lifetime", "environment-evolution", "transfer-to-next-project"},
                "target_platforms": ["leon3", "leon4", "x86"], "tested_platforms": ["leon3", "x86"]}
        self.assertEqual(check_intended_reuse(comp),
                         ["not tested on leon4 and the certificate of conformance states no limitation"])
        comp["coc_limitations"] = "leon4 not validated"
        self.assertEqual(check_intended_reuse(comp), [])


class DeviceTests(unittest.TestCase):
    def test_good_device(self):
        self.assertEqual(check_programmable_device(_device(), BITSTREAM), [])

    def test_calibration_and_digest(self):
        found = check_programmable_device(_device(programmed_on="2026-07-15"), BITSTREAM + b"x")
        self.assertIn("programming equipment out of calibration on 2026-07-15", found)
        self.assertIn("programmed image does not match the configuration file digest", found)

    def test_marking(self):
        found = check_programmable_device(_device(marking_sw_ref="", marking_required=True))
        self.assertIn("marking does not identify both hardware and software references", found)
        self.assertIn("protective marking required and absent", found)


if __name__ == "__main__":
    unittest.main()
