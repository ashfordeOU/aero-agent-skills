#!/usr/bin/env python3
"""Gate 3 contract test: additive manufacturing qualification.

Exercises scripts/additive_manufacturing_qualification_logic.py (stdlib
unittest, offline). Contract: docs/harness-contract.md gate 3 -
volumetric_energy_density() computes VED = laser power / (scan speed x
hatch spacing x layer height) from hand-computed reference values
(200 W, 800 mm/s, 0.1 mm hatch, 0.05 mm layer give 50.0 J/mm^3;
300 W, 1000 mm/s, 0.1 mm, 0.03 mm give 100.0 J/mm^3; 500 W, 2500 mm/s,
0.08 mm, 0.04 mm give 62.5 J/mm^3). build_parameter_set() records the
four build parameters plus the computed VED. witness_coupon_count()
derives the witness coupon count from the material property sample plan
(total samples plus one spare coupon per test type). build_qualification_record()
and validate_record() check qualification record completeness across the
four required fields. Invalid inputs raise ValueError.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import additive_manufacturing_qualification_logic as amql  # noqa: E402


class VolumetricEnergyDensityTest(unittest.TestCase):
    def test_reference_case_200w(self):
        # 200 / (800 x 0.1 x 0.05) = 200 / 4.0 = 50.0 J/mm^3
        self.assertAlmostEqual(
            amql.volumetric_energy_density(200, 800, 0.1, 0.05), 50.0, places=9
        )

    def test_reference_case_300w(self):
        # 300 / (1000 x 0.1 x 0.03) = 300 / 3.0 = 100.0 J/mm^3
        self.assertAlmostEqual(
            amql.volumetric_energy_density(300, 1000, 0.1, 0.03), 100.0, places=9
        )

    def test_reference_case_500w(self):
        # 500 / (2500 x 0.08 x 0.04) = 500 / 8.0 = 62.5 J/mm^3
        self.assertAlmostEqual(
            amql.volumetric_energy_density(500, 2500, 0.08, 0.04), 62.5, places=9
        )

    def test_halved_hatch_doubles_ved(self):
        # Same power, speed, layer; half the hatch spacing doubles VED.
        base = amql.volumetric_energy_density(200, 800, 0.1, 0.05)
        tight = amql.volumetric_energy_density(200, 800, 0.05, 0.05)
        self.assertAlmostEqual(tight, 2.0 * base, places=9)

    def test_non_numeric_raises(self):
        with self.assertRaises(ValueError):
            amql.volumetric_energy_density("hot", 800, 0.1, 0.05)
        with self.assertRaises(ValueError):
            amql.volumetric_energy_density(200, None, 0.1, 0.05)

    def test_non_positive_raises(self):
        with self.assertRaises(ValueError):
            amql.volumetric_energy_density(0, 800, 0.1, 0.05)
        with self.assertRaises(ValueError):
            amql.volumetric_energy_density(200, -800, 0.1, 0.05)
        with self.assertRaises(ValueError):
            amql.volumetric_energy_density(200, 800, 0.0, 0.05)


class ParameterSetTest(unittest.TestCase):
    def test_complete_parameter_set(self):
        ps = amql.build_parameter_set(
            process_id="LPBF-Ti64-B1",
            material="Ti-6Al-4V",
            laser_power=300,
            scan_speed=1000,
            hatch_spacing=0.1,
            layer_height=0.03,
        )
        self.assertEqual(ps["process_id"], "LPBF-Ti64-B1")
        self.assertEqual(ps["material"], "Ti-6Al-4V")
        self.assertEqual(ps["laser_power"], 300.0)
        self.assertEqual(ps["scan_speed"], 1000.0)
        self.assertEqual(ps["hatch_spacing"], 0.1)
        self.assertEqual(ps["layer_height"], 0.03)
        self.assertAlmostEqual(ps["volumetric_energy_density"], 100.0, places=9)

    def test_empty_process_id_rejected(self):
        with self.assertRaises(ValueError):
            amql.build_parameter_set(
                process_id=" ",
                material="Ti-6Al-4V",
                laser_power=300,
                scan_speed=1000,
                hatch_spacing=0.1,
                layer_height=0.03,
            )

    def test_empty_material_rejected(self):
        with self.assertRaises(ValueError):
            amql.build_parameter_set(
                process_id="LPBF-Ti64-B1",
                material="",
                laser_power=300,
                scan_speed=1000,
                hatch_spacing=0.1,
                layer_height=0.03,
            )

    def test_bad_parameter_propagates_value_error(self):
        with self.assertRaises(ValueError):
            amql.build_parameter_set(
                process_id="LPBF-Ti64-B1",
                material="Ti-6Al-4V",
                laser_power=300,
                scan_speed=1000,
                hatch_spacing=-0.1,
                layer_height=0.03,
            )


class WitnessCouponCountTest(unittest.TestCase):
    def test_two_test_plan(self):
        # tensile 3 + fatigue 5 = 8 samples, plus 2 spares = 10 coupons.
        plan = [
            {"test": "tensile", "samples": 3},
            {"test": "fatigue", "samples": 5},
        ]
        self.assertEqual(amql.witness_coupon_count(plan), 10)

    def test_single_test_plan(self):
        # hardness 4 + 1 spare = 5 coupons.
        self.assertEqual(
            amql.witness_coupon_count([{"test": "hardness", "samples": 4}]), 5
        )

    def test_three_test_plan(self):
        # 2 + 2 + 3 = 7 samples, plus 3 spares = 10 coupons.
        plan = [
            {"test": "tensile", "samples": 2},
            {"test": "fatigue", "samples": 2},
            {"test": "fracture toughness", "samples": 3},
        ]
        self.assertEqual(amql.witness_coupon_count(plan), 10)

    def test_empty_plan_rejected(self):
        with self.assertRaises(ValueError):
            amql.witness_coupon_count([])

    def test_non_list_plan_rejected(self):
        with self.assertRaises(ValueError):
            amql.witness_coupon_count("tensile x3")

    def test_malformed_entry_rejected(self):
        with self.assertRaises(ValueError):
            amql.witness_coupon_count([{"samples": 3}])
        with self.assertRaises(ValueError):
            amql.witness_coupon_count([{"test": "tensile"}])

    def test_zero_samples_rejected(self):
        with self.assertRaises(ValueError):
            amql.witness_coupon_count([{"test": "tensile", "samples": 0}])

    def test_bool_samples_rejected(self):
        with self.assertRaises(ValueError):
            amql.witness_coupon_count([{"test": "tensile", "samples": True}])

    def test_float_samples_rejected(self):
        with self.assertRaises(ValueError):
            amql.witness_coupon_count([{"test": "tensile", "samples": 3.0}])


class QualificationRecordTest(unittest.TestCase):
    def _complete_record(self):
        parameter_set = amql.build_parameter_set(
            process_id="LPBF-Ti64-B1",
            material="Ti-6Al-4V",
            laser_power=300,
            scan_speed=1000,
            hatch_spacing=0.1,
            layer_height=0.03,
        )
        return {
            "parameter_set": parameter_set,
            "witness_coupon_plan": [{"test": "tensile", "samples": 3}],
            "material_property_verification": [
                {"test": "tensile", "result": "895 MPa", "status": "pass"}
            ],
            "first_article_inspection": [
                {"check": "build file traceability", "status": "pass"},
                {"check": "dimensional report", "status": "pass"},
            ],
        }

    def test_complete_record(self):
        record = amql.build_qualification_record(**self._complete_record())
        self.assertTrue(record["complete"])
        self.assertEqual(record["missing"], [])
        self.assertEqual(len(record["checklist"]), 4)
        for item in record["checklist"]:
            self.assertTrue(item["present"])
        self.assertAlmostEqual(
            record["parameter_set"]["volumetric_energy_density"], 100.0, places=9
        )

    def test_missing_field_flagged(self):
        record = self._complete_record()
        del record["material_property_verification"]
        missing = amql.validate_record(record)
        self.assertIn("material_property_verification", missing)
        self.assertEqual(len(missing), 1)

    def test_empty_list_flagged_missing(self):
        record = self._complete_record()
        record["first_article_inspection"] = []
        missing = amql.validate_record(record)
        self.assertIn("first_article_inspection", missing)

    def test_validate_record_rejects_non_mapping(self):
        with self.assertRaises(ValueError):
            amql.validate_record("LPBF-Ti64-B1")

    def test_empty_parameter_set_rejected(self):
        record = self._complete_record()
        record["parameter_set"] = {}
        with self.assertRaises(ValueError):
            amql.build_qualification_record(**record)

    def test_empty_witness_plan_rejected(self):
        record = self._complete_record()
        record["witness_coupon_plan"] = []
        with self.assertRaises(ValueError):
            amql.build_qualification_record(**record)

    def test_empty_verification_rejected(self):
        record = self._complete_record()
        record["material_property_verification"] = []
        with self.assertRaises(ValueError):
            amql.build_qualification_record(**record)

    def test_empty_first_article_rejected(self):
        record = self._complete_record()
        record["first_article_inspection"] = []
        with self.assertRaises(ValueError):
            amql.build_qualification_record(**record)


if __name__ == "__main__":
    unittest.main()
