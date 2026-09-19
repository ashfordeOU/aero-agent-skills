"""Contract tests for the clause 4.7.5.4.12 / 4.7.6 release and locking logic."""

import math
import unittest

from e3301_release_locking_devices_incl_pyrotechnics_logic import (
    ACTUATION_MEANS,
    MARGIN_TOLERANCE_DB,
    PRELOAD_TOLERANCE,
    assess_release_locking_design,
    contamination_findings,
    contamination_total,
    induced_shock_g,
    locking_findings,
    preload_margin,
    redundancy_findings,
    shock_findings,
    shock_margin_db,
    validate_device,
)


def good_device(**overrides):
    device = {
        "id": "HDRM-1",
        "actuation": "pyrotechnic",
        "initiators": 2,
        "firing_paths": 2,
        "preload_n": 24000.0,
        "worst_case_load_n": 12000.0,
        "positive_lock": True,
        "release_confirmed": True,
        "particulate_mg": 1.5,
        "outgassed_mg": 0.5,
        "source_level_g": 3000.0,
    }
    device.update(overrides)
    return device


NEIGHBOURS = [
    {"id": "STAR-TRACKER", "distance_m": 1.2, "qualified_g": 2000.0, "joints": 1},
    {"id": "REACTION-WHEEL", "distance_m": 2.0, "qualified_g": 1500.0, "joints": 2},
]


class ValidateDeviceTests(unittest.TestCase):
    def test_normalises_actuation_case(self):
        record = validate_device(good_device(actuation="Pyrotechnic"))
        self.assertEqual(record["actuation"], "pyrotechnic")

    def test_every_recognised_means_validates(self):
        for means in ACTUATION_MEANS:
            record = validate_device(good_device(actuation=means))
            self.assertEqual(record["actuation"], means)

    def test_unknown_actuation_rejected(self):
        with self.assertRaises(ValueError):
            validate_device(good_device(actuation="wishful-thinking"))

    def test_missing_key_rejected(self):
        device = good_device()
        del device["preload_n"]
        with self.assertRaises(ValueError):
            validate_device(device)

    def test_non_mapping_rejected(self):
        with self.assertRaises(ValueError):
            validate_device(["HDRM-1"])

    def test_zero_preload_rejected(self):
        with self.assertRaises(ValueError):
            validate_device(good_device(preload_n=0.0))

    def test_negative_initiator_count_rejected(self):
        with self.assertRaises(ValueError):
            validate_device(good_device(initiators=-1))

    def test_boolean_initiator_count_rejected(self):
        with self.assertRaises(ValueError):
            validate_device(good_device(initiators=True))

    def test_zero_initiators_rejected(self):
        with self.assertRaises(ValueError):
            validate_device(good_device(initiators=0))

    def test_negative_particulate_rejected(self):
        with self.assertRaises(ValueError):
            validate_device(good_device(particulate_mg=-0.1))

    def test_empty_identifier_rejected(self):
        with self.assertRaises(ValueError):
            validate_device(good_device(id="   "))


class RedundancyTests(unittest.TestCase):
    def test_dual_initiator_dual_path_is_clean(self):
        self.assertEqual(redundancy_findings(good_device()), [])

    def test_single_initiator_is_a_single_point_failure(self):
        findings = redundancy_findings(good_device(initiators=1))
        self.assertEqual(len(findings), 1)
        self.assertIn("initiator", findings[0])

    def test_shared_firing_circuit_is_flagged(self):
        findings = redundancy_findings(good_device(firing_paths=1))
        self.assertEqual(len(findings), 1)
        self.assertIn("firing path", findings[0])

    def test_missing_release_confirmation_is_flagged(self):
        findings = redundancy_findings(good_device(release_confirmed=False))
        self.assertEqual(len(findings), 1)

    def test_non_critical_device_is_not_graded_for_redundancy(self):
        device = good_device(initiators=1, firing_paths=1,
                             release_confirmed=False, mission_critical=False)
        self.assertEqual(redundancy_findings(device), [])

    def test_redundancy_applies_to_non_explosive_means_too(self):
        findings = redundancy_findings(good_device(actuation="shape-memory-alloy",
                                                   initiators=1))
        self.assertEqual(len(findings), 1)


class ShockTests(unittest.TestCase):
    def test_level_decays_with_distance(self):
        near = induced_shock_g(3000.0, 0.5)
        far = induced_shock_g(3000.0, 3.0)
        self.assertLess(far, near / 2.0)

    def test_zero_distance_no_joint_returns_the_source_level(self):
        self.assertAlmostEqual(induced_shock_g(3000.0, 0.0), 3000.0, places=9)

    def test_each_joint_applies_its_attenuation(self):
        one = induced_shock_g(3000.0, 0.0, joints=1, joint_attenuation=0.5)
        two = induced_shock_g(3000.0, 0.0, joints=2, joint_attenuation=0.5)
        self.assertAlmostEqual(two, one * 0.5, places=9)

    def test_joint_attenuation_above_unity_rejected(self):
        with self.assertRaises(ValueError):
            induced_shock_g(3000.0, 1.0, joints=1, joint_attenuation=1.4)

    def test_negative_distance_rejected(self):
        with self.assertRaises(ValueError):
            induced_shock_g(3000.0, -1.0)

    def test_factor_of_two_is_about_six_db(self):
        self.assertAlmostEqual(shock_margin_db(200.0, 100.0), 6.020599913, places=6)

    def test_equal_levels_give_zero_db(self):
        self.assertAlmostEqual(shock_margin_db(1500.0, 1500.0), 0.0, places=9)

    def test_zero_induced_level_rejected(self):
        with self.assertRaises(ValueError):
            shock_margin_db(1500.0, 0.0)

    def test_neighbour_record_per_unit(self):
        result = shock_findings(good_device(), NEIGHBOURS, 3.0)
        self.assertEqual(len(result["records"]), 2)

    def test_under_qualified_neighbour_is_flagged(self):
        close = [{"id": "OPTICS", "distance_m": 0.05, "qualified_g": 500.0}]
        result = shock_findings(good_device(), close, 3.0)
        self.assertEqual(len(result["findings"]), 1)
        self.assertFalse(result["records"][0]["compliant"])

    def test_exact_boundary_margin_is_compliant(self):
        induced = induced_shock_g(3000.0, 1.0)
        qualified = induced * (10.0 ** (6.0 / 20.0))
        unit = [{"id": "BOUNDARY", "distance_m": 1.0, "qualified_g": qualified}]
        result = shock_findings(good_device(), unit, 6.0)
        self.assertAlmostEqual(result["records"][0]["margin_db"], 6.0, places=9)
        self.assertTrue(result["records"][0]["compliant"])

    def test_malformed_neighbour_rejected(self):
        with self.assertRaises(ValueError):
            shock_findings(good_device(), [{"id": "X"}], 3.0)


class LockingTests(unittest.TestCase):
    def test_margin_is_the_fractional_excess(self):
        self.assertAlmostEqual(preload_margin(15000.0, 10000.0), 0.5, places=9)

    def test_equal_preload_and_load_is_zero_margin(self):
        self.assertAlmostEqual(preload_margin(10000.0, 10000.0), 0.0, places=9)

    def test_zero_load_rejected(self):
        with self.assertRaises(ValueError):
            preload_margin(10000.0, 0.0)

    def test_healthy_lock_is_clean(self):
        result = locking_findings(good_device(), 0.5)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_short_preload_is_flagged(self):
        result = locking_findings(good_device(preload_n=13000.0), 0.5)
        self.assertFalse(result["compliant"])
        self.assertEqual(len(result["findings"]), 1)

    def test_friction_only_lock_is_flagged(self):
        result = locking_findings(good_device(positive_lock=False), 0.5)
        self.assertFalse(result["compliant"])
        self.assertIn("positive", result["findings"][0])

    def test_exact_boundary_preload_is_compliant(self):
        device = good_device(preload_n=15000.0, worst_case_load_n=10000.0)
        result = locking_findings(device, 0.5)
        self.assertAlmostEqual(result["margin"], 0.5, places=9)
        self.assertTrue(result["compliant"])
        self.assertLessEqual(abs(result["margin"] - 0.5), PRELOAD_TOLERANCE)


class ContaminationTests(unittest.TestCase):
    def test_totals_sum_both_streams(self):
        totals = contamination_total([good_device(), good_device(id="HDRM-2")])
        self.assertAlmostEqual(totals["particulate_mg"], 3.0, places=9)
        self.assertAlmostEqual(totals["outgassed_mg"], 1.0, places=9)
        self.assertAlmostEqual(totals["total_mg"], 4.0, places=9)

    def test_empty_device_set_rejected(self):
        with self.assertRaises(ValueError):
            contamination_total([])

    def test_within_budget_is_clean(self):
        result = contamination_findings([good_device()], 10.0)
        self.assertTrue(result["within_budget"])
        self.assertEqual(result["findings"], [])

    def test_over_budget_is_flagged(self):
        result = contamination_findings([good_device(particulate_mg=40.0)], 10.0)
        self.assertFalse(result["within_budget"])
        self.assertEqual(len(result["findings"]), 1)

    def test_exact_budget_is_accepted_at_the_limit(self):
        result = contamination_findings([good_device(particulate_mg=9.5)], 10.0)
        self.assertAlmostEqual(result["totals"]["total_mg"], 10.0, places=9)
        self.assertTrue(result["within_budget"])

    def test_zero_budget_rejected(self):
        with self.assertRaises(ValueError):
            contamination_findings([good_device()], 0.0)


class AssessmentTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "devices": [good_device()],
            "neighbours": NEIGHBOURS,
            "required_shock_margin_db": 3.0,
            "required_preload_margin": 0.5,
            "contamination_budget_mg": 10.0,
        }
        spec.update(overrides)
        return spec

    def test_healthy_design_reports_no_findings(self):
        result = assess_release_locking_design(self._spec())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_energetic_flag_tracks_the_actuation_means(self):
        result = assess_release_locking_design(self._spec())
        self.assertTrue(result["devices"][0]["energetic"])
        thermal = self._spec(devices=[good_device(actuation="thermal-knife")])
        self.assertFalse(assess_release_locking_design(thermal)["devices"][0]["energetic"])

    def test_single_initiator_fails_the_design(self):
        result = assess_release_locking_design(
            self._spec(devices=[good_device(initiators=1)])
        )
        self.assertFalse(result["compliant"])

    def test_findings_aggregate_across_devices(self):
        devices = [good_device(initiators=1), good_device(id="HDRM-2", firing_paths=1)]
        result = assess_release_locking_design(self._spec(devices=devices))
        self.assertEqual(len(result["findings"]), 2)

    def test_empty_device_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_release_locking_design(self._spec(devices=[]))

    def test_missing_spec_key_rejected(self):
        spec = self._spec()
        del spec["required_preload_margin"]
        with self.assertRaises(ValueError):
            assess_release_locking_design(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_release_locking_design(["devices"])

    def test_no_neighbours_still_grades_redundancy_and_locking(self):
        result = assess_release_locking_design(
            self._spec(neighbours=[], devices=[good_device(positive_lock=False)])
        )
        self.assertFalse(result["compliant"])
        self.assertEqual(result["devices"][0]["shock_records"], [])

    def test_shock_margin_tolerance_is_tight(self):
        self.assertLess(MARGIN_TOLERANCE_DB, 1e-6)

    def test_contamination_totals_reach_the_report(self):
        result = assess_release_locking_design(self._spec())
        self.assertAlmostEqual(result["contamination"]["total_mg"], 2.0, places=9)
        self.assertTrue(math.isfinite(result["devices"][0]["preload_margin"]))


if __name__ == "__main__":
    unittest.main()
