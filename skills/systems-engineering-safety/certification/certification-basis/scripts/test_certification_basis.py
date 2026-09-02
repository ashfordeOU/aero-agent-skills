#!/usr/bin/env python3
"""Contract test for certification_basis_logic (gate 3, stdlib unittest).

Exercises the certification basis determination logic:
- regulation applicability by product type and category (transport airplane
  maps to FAR-25 / CS-25, normal airplane to Part 23, rotorcraft to Part 27
  or 29, engines to Part 33, propellers to Part 35)
- special condition detection for novel or unusual design features
- certification path selection (TC, amended TC, STC, TSO, minor change)
- edge cases and error handling

Runs standalone:
    python3 scripts/test_certification_basis.py
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import certification_basis_logic as cbl  # noqa: E402


class RegulationApplicabilityTests(unittest.TestCase):
    """Category and product type must map to the governing airworthiness parts."""

    def test_transport_airplane_maps_to_far_25(self):
        rec = cbl.regulation_for("airplane", "transport", "FAA")
        self.assertEqual(rec["id"], "far-25")
        self.assertEqual(rec["part"], 25)

    def test_transport_airplane_maps_to_cs_25_for_easa(self):
        rec = cbl.regulation_for("airplane", "transport", "EASA")
        self.assertEqual(rec["id"], "cs-25")

    def test_normal_category_airplane_maps_to_part_23(self):
        for cat in ("normal", "utility", "acrobatic", "commuter"):
            rec = cbl.regulation_for("airplane", cat, "FAA")
            self.assertEqual(rec["part"], 23, "category %s" % cat)

    def test_rotorcraft_category_mapping(self):
        self.assertEqual(cbl.regulation_for("rotorcraft", "normal", "FAA")["id"], "far-27")
        self.assertEqual(cbl.regulation_for("rotorcraft", "transport", "FAA")["id"], "far-29")
        self.assertEqual(cbl.regulation_for("rotorcraft", "normal", "EASA")["id"], "cs-27")
        self.assertEqual(cbl.regulation_for("rotorcraft", "transport", "EASA")["id"], "cs-29")

    def test_engine_maps_to_part_33_and_propeller_to_part_35(self):
        self.assertEqual(cbl.regulation_for("engine", None, "FAA")["id"], "far-33")
        self.assertEqual(cbl.regulation_for("engine", None, "EASA")["id"], "cs-e")
        self.assertEqual(cbl.regulation_for("propeller", None, "FAA")["id"], "far-35")
        self.assertEqual(cbl.regulation_for("propeller", None, "EASA")["id"], "cs-p")

    def test_applicable_regulations_returns_pair(self):
        regs = cbl.applicable_regulations("airplane", "transport")
        ids = [r["id"] for r in regs]
        self.assertIn("far-25", ids)
        self.assertIn("cs-25", ids)

    def test_subparts_exist_for_known_regulations(self):
        self.assertIn("E Powerplant", cbl.subparts_for("far-25"))
        self.assertIn("C Tests and Inspections", cbl.subparts_for("far-35"))
        with self.assertRaises(ValueError):
            cbl.subparts_for("far-999")

    def test_paragraph_mapping_for_systems_area(self):
        pars = cbl.paragraphs_for("far-25", "systems")
        self.assertIn("25.1309", pars)
        self.assertIn("25.671", cbl.paragraphs_for("far-25", "flight-controls"))


class SpecialConditionTests(unittest.TestCase):
    """Novel or unusual features must flag a special condition."""

    def test_novel_fly_by_wire_flags_special_condition(self):
        verdicts = cbl.detect_special_conditions(
            ["full-authority fly-by-wire flight controls without mechanical backup"]
        )
        self.assertTrue(verdicts[0]["special_condition"])
        self.assertEqual(verdicts[0]["keyword"], "fly-by-wire")

    def test_lithium_battery_flags_special_condition(self):
        verdicts = cbl.detect_special_conditions(["lithium battery main ship power"])
        self.assertTrue(verdicts[0]["special_condition"])
        self.assertEqual(verdicts[0]["keyword"], "lithium-battery")

    def test_conventional_feature_does_not_flag(self):
        verdicts = cbl.detect_special_conditions(
            ["conventional mechanical flight controls", "conventional aluminum wing structure"]
        )
        self.assertTrue(all(not v["special_condition"] for v in verdicts))

    def test_empty_feature_list_yields_no_verdicts(self):
        self.assertEqual(cbl.detect_special_conditions([]), [])

    def test_multiple_features_flagged_independently(self):
        verdicts = cbl.detect_special_conditions(
            ["electric propulsion for the main drive", "proven legacy hydraulic system"]
        )
        self.assertEqual(sum(1 for v in verdicts if v["special_condition"]), 1)


class CertificationPathTests(unittest.TestCase):
    """Path selection must follow the change context and modifier role."""

    def test_new_type_design_takes_type_certificate(self):
        path = cbl.select_certification_path("airplane", "new_type_design")
        self.assertEqual(path["path"], "type-certificate")
        self.assertIn("certification-basis", path["finding_types"])
        self.assertIn("certification-program", path["finding_types"])

    def test_modification_by_other_takes_stc(self):
        path = cbl.select_certification_path(
            "airplane", "major_change", modifier_role="other"
        )
        self.assertEqual(path["path"], "supplemental-type-certificate")

    def test_major_change_by_holder_takes_amended_tc(self):
        path = cbl.select_certification_path(
            "airplane", "major_change", modifier_role="type_certificate_holder"
        )
        self.assertEqual(path["path"], "amended-type-certificate")

    def test_minor_change_by_holder_is_recorded(self):
        path = cbl.select_certification_path(
            "airplane", "minor_change", modifier_role="type_certificate_holder"
        )
        self.assertEqual(path["path"], "minor-change")

    def test_tso_article_takes_tso_authorization(self):
        path = cbl.select_certification_path(
            "article", "none", modifier_role="other", article_tso=True
        )
        self.assertEqual(path["path"], "tso-authorization")

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            cbl.select_certification_path("airship", "major_change")
        with self.assertRaises(ValueError):
            cbl.select_certification_path("airplane", "huge_change")
        with self.assertRaises(ValueError):
            cbl.select_certification_path("airplane", "major_change", modifier_role="nobody")


class EdgeCaseTests(unittest.TestCase):
    """Validation and aggregate behavior must be deterministic."""

    def test_unknown_product_type_raises(self):
        with self.assertRaises(ValueError):
            cbl.regulation_for("airship", None)
        with self.assertRaises(ValueError):
            cbl.certification_basis("airship", None)

    def test_wrong_category_for_type_raises(self):
        with self.assertRaises(ValueError):
            cbl.regulation_for("rotorcraft", "utility")
        with self.assertRaises(ValueError):
            cbl.regulation_for("airplane", "transport", "ESA")

    def test_aggregate_certification_basis_consistency(self):
        basis = cbl.certification_basis(
            "airplane",
            "transport",
            features=["fly-by-wire envelope protection", "conventional aluminum wing"],
            change_kind="major_change",
            modifier_role="other",
        )
        self.assertEqual(basis["product"], "airplane")
        self.assertEqual(basis["category"], "transport")
        self.assertEqual(basis["certification_path"]["path"], "supplemental-type-certificate")
        flagged = [v for v in basis["special_conditions"] if v["special_condition"]]
        self.assertEqual(len(flagged), 1)
        self.assertIn("far-25", [r["id"] for r in basis["regulations"]])
        self.assertIn("special condition", basis["basis_summary"])
        self.assertIn("supplemental-type-certificate", basis["basis_summary"])

    def test_determinism_repeated_calls(self):
        a = cbl.certification_basis("rotorcraft", "normal", features=["morphing rotor blades"])
        b = cbl.certification_basis("rotorcraft", "normal", features=["morphing rotor blades"])
        self.assertEqual(a["basis_summary"], b["basis_summary"])
        self.assertEqual(
            a["special_conditions"][0]["special_condition"],
            b["special_conditions"][0]["special_condition"],
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
