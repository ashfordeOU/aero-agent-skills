"""Contract test for the e3311 shaped charges leaf (stdlib unittest)."""

import math
import unittest

from e3311_shaped_charges_logic import (
    DEFAULT_SHAPED_CHARGE_POLICY,
    VERDICT_MET,
    VERDICT_NOT_MET,
    alignment_efficiency,
    alignment_verdict,
    assess_charge_array,
    assess_shaped_charge,
    backup_clearance_verdict,
    keep_out_radius_mm,
    keep_out_verdict,
    penetration_capability_mm,
    performance_verdict,
    residual_penetration_mm,
    standoff_deviation_fraction,
    standoff_efficiency,
    standoff_verdict,
    sympathetic_spacing_verdict,
    validate_charge,
    validate_charges,
    validate_shaped_charge_policy,
)


def charge(cid="LSC-1", **kw):
    record = {
        "id": cid,
        "kind": "linear-shaped-charge",
        "charge_diameter_mm": 25.0,
        "nominal_penetration_mm": 60.0,
        "optimum_standoff_mm": 50.0,
        "installed_standoff_mm": 52.0,
        "standoff_sensitivity": 0.80,
        "misalignment_deg": 1.0,
        "target_thickness_mm": 30.0,
        "clearance_to_sensitive_mm": 400.0,
        "clearance_behind_target_mm": 80.0,
    }
    record.update(kw)
    return record


class TestPolicyValidation(unittest.TestCase):
    def test_default_policy_is_valid(self):
        self.assertIs(
            validate_shaped_charge_policy(DEFAULT_SHAPED_CHARGE_POLICY),
            DEFAULT_SHAPED_CHARGE_POLICY,
        )

    def test_a_non_mapping_policy_raises(self):
        with self.assertRaises(ValueError):
            validate_shaped_charge_policy("1.5 CD")

    def test_a_penetration_margin_below_unity_raises(self):
        with self.assertRaises(ValueError):
            validate_shaped_charge_policy(
                dict(DEFAULT_SHAPED_CHARGE_POLICY, min_penetration_margin=0.8)
            )

    def test_a_misalignment_limit_beyond_ninety_degrees_raises(self):
        with self.assertRaises(ValueError):
            validate_shaped_charge_policy(
                dict(DEFAULT_SHAPED_CHARGE_POLICY, max_misalignment_deg=120.0)
            )


class TestRecordValidation(unittest.TestCase):
    def test_a_valid_charge_normalizes(self):
        record = validate_charge(charge())
        self.assertEqual(record["kind"], "linear-shaped-charge")

    def test_an_unknown_charge_kind_raises(self):
        with self.assertRaises(ValueError):
            validate_charge(charge(kind="bursting-charge"))

    def test_a_charge_turned_fully_away_raises(self):
        with self.assertRaises(ValueError):
            validate_charge(charge(misalignment_deg=90.0))

    def test_a_negative_misalignment_raises(self):
        with self.assertRaises(ValueError):
            validate_charge(charge(misalignment_deg=-2.0))

    def test_a_zero_optimum_standoff_raises(self):
        with self.assertRaises(ValueError):
            validate_charge(charge(optimum_standoff_mm=0.0))

    def test_duplicate_charge_ids_raise(self):
        with self.assertRaises(ValueError):
            validate_charges([charge("LSC-1"), charge("LSC-1")])

    def test_an_empty_charge_list_raises(self):
        with self.assertRaises(ValueError):
            validate_charges([])


class TestCapability(unittest.TestCase):
    def test_standoff_deviation_is_symmetric_about_the_optimum(self):
        self.assertAlmostEqual(
            standoff_deviation_fraction(charge(installed_standoff_mm=45.0)),
            standoff_deviation_fraction(charge(installed_standoff_mm=55.0)),
            places=12,
        )

    def test_standoff_efficiency_is_one_at_the_optimum(self):
        self.assertAlmostEqual(
            standoff_efficiency(charge(installed_standoff_mm=50.0)), 1.0, places=12
        )

    def test_standoff_efficiency_never_goes_negative(self):
        self.assertAlmostEqual(
            standoff_efficiency(
                charge(installed_standoff_mm=500.0, standoff_sensitivity=2.0)
            ),
            0.0,
            places=12,
        )

    def test_alignment_efficiency_is_the_cosine_of_the_angle(self):
        self.assertAlmostEqual(
            alignment_efficiency(charge(misalignment_deg=30.0)),
            math.cos(math.radians(30.0)),
            places=12,
        )

    def test_alignment_efficiency_is_one_when_square(self):
        self.assertAlmostEqual(
            alignment_efficiency(charge(misalignment_deg=0.0)), 1.0, places=12
        )

    def test_capability_applies_both_efficiencies_to_the_nominal(self):
        expected = (
            60.0
            * standoff_efficiency(charge())
            * alignment_efficiency(charge())
        )
        self.assertAlmostEqual(
            penetration_capability_mm(charge()), expected, places=12
        )

    def test_residual_is_the_capability_past_the_target(self):
        self.assertAlmostEqual(
            residual_penetration_mm(charge()),
            penetration_capability_mm(charge()) - 30.0,
            places=12,
        )

    def test_residual_is_zero_when_the_target_is_thicker_than_the_jet(self):
        self.assertAlmostEqual(
            residual_penetration_mm(charge(target_thickness_mm=400.0)),
            0.0,
            places=12,
        )


class TestGates(unittest.TestCase):
    def test_a_well_installed_charge_clears_the_penetration_margin(self):
        verdict = performance_verdict(charge())
        self.assertTrue(verdict["compliant"])
        self.assertGreater(verdict["penetration_margin"], 1.5)

    def test_a_margin_landing_exactly_on_the_requirement_passes(self):
        target = penetration_capability_mm(charge()) / 1.5
        verdict = performance_verdict(charge(target_thickness_mm=target))
        self.assertAlmostEqual(verdict["penetration_margin"], 1.5, places=9)
        self.assertTrue(verdict["compliant"])

    def test_a_thick_target_fails_the_penetration_margin(self):
        verdict = performance_verdict(charge(target_thickness_mm=50.0))
        self.assertFalse(verdict["compliant"])
        self.assertTrue(any("as installed" in f for f in verdict["findings"]))

    def test_a_standoff_exactly_on_the_tolerance_passes(self):
        verdict = standoff_verdict(charge(installed_standoff_mm=60.0))
        self.assertAlmostEqual(verdict["deviation_fraction"], 0.20, places=12)
        self.assertTrue(verdict["compliant"])

    def test_a_standoff_outside_the_tolerance_fails(self):
        verdict = standoff_verdict(charge(installed_standoff_mm=75.0))
        self.assertFalse(verdict["compliant"])
        self.assertTrue(any("deviation" in f for f in verdict["findings"]))

    def test_a_misalignment_exactly_on_the_limit_passes(self):
        self.assertTrue(alignment_verdict(charge(misalignment_deg=5.0))["compliant"])

    def test_a_large_misalignment_fails(self):
        verdict = alignment_verdict(charge(misalignment_deg=12.0))
        self.assertFalse(verdict["compliant"])
        self.assertTrue(any("off normal" in f for f in verdict["findings"]))

    def test_the_keep_out_radius_scales_with_the_charge_diameter(self):
        self.assertAlmostEqual(keep_out_radius_mm(charge()), 250.0, places=9)

    def test_sensitive_hardware_inside_the_keep_out_radius_fails(self):
        verdict = keep_out_verdict(charge(clearance_to_sensitive_mm=120.0))
        self.assertFalse(verdict["compliant"])
        self.assertTrue(any("keep-out radius" in f for f in verdict["findings"]))

    def test_clearance_exactly_on_the_keep_out_radius_passes(self):
        self.assertTrue(
            keep_out_verdict(charge(clearance_to_sensitive_mm=250.0))["compliant"]
        )

    def test_structure_inside_the_residual_jet_fails(self):
        verdict = backup_clearance_verdict(charge(clearance_behind_target_mm=5.0))
        self.assertFalse(verdict["compliant"])
        self.assertTrue(any("residual jet" in f for f in verdict["findings"]))

    def test_no_residual_jet_needs_no_clearance(self):
        self.assertTrue(
            backup_clearance_verdict(
                charge(target_thickness_mm=400.0, clearance_behind_target_mm=0.0)
            )["compliant"]
        )


class TestSympatheticSpacing(unittest.TestCase):
    def test_a_generous_spacing_passes(self):
        verdict = sympathetic_spacing_verdict(charge("A"), charge("B"), 200.0)
        self.assertTrue(verdict["compliant"])
        self.assertAlmostEqual(verdict["required_spacing_mm"], 150.0, places=9)

    def test_the_larger_diameter_drives_the_required_spacing(self):
        verdict = sympathetic_spacing_verdict(
            charge("A"), charge("B", charge_diameter_mm=40.0), 300.0
        )
        self.assertAlmostEqual(verdict["required_spacing_mm"], 240.0, places=9)

    def test_a_spacing_exactly_on_the_requirement_passes(self):
        self.assertTrue(
            sympathetic_spacing_verdict(charge("A"), charge("B"), 150.0)["compliant"]
        )

    def test_a_tight_spacing_fails(self):
        verdict = sympathetic_spacing_verdict(charge("A"), charge("B"), 90.0)
        self.assertFalse(verdict["compliant"])
        self.assertEqual(verdict["pair"], ("A", "B"))

    def test_a_zero_spacing_raises(self):
        with self.assertRaises(ValueError):
            sympathetic_spacing_verdict(charge("A"), charge("B"), 0.0)


class TestAssessment(unittest.TestCase):
    def test_a_sound_charge_passes_every_gate(self):
        result = assess_shaped_charge(charge())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["failed_gates"], [])

    def test_a_failing_charge_names_every_failed_gate(self):
        result = assess_shaped_charge(
            charge(installed_standoff_mm=90.0, clearance_to_sensitive_mm=10.0)
        )
        self.assertFalse(result["compliant"])
        self.assertIn("standoff", result["failed_gates"])
        self.assertIn("keep-out", result["failed_gates"])

    def test_a_clean_array_meets_the_clause(self):
        report = assess_charge_array(
            [charge("LSC-1"), charge("LSC-2")],
            [{"charges": ["LSC-1", "LSC-2"], "spacing_mm": 220.0}],
        )
        self.assertTrue(report["compliant"])
        self.assertEqual(report["verdict"], VERDICT_MET)

    def test_a_tight_pair_alone_fails_the_array(self):
        report = assess_charge_array(
            [charge("LSC-1"), charge("LSC-2")],
            [{"charges": ["LSC-1", "LSC-2"], "spacing_mm": 60.0}],
        )
        self.assertEqual(report["rejected"], [])
        self.assertEqual(report["failed_pairs"], [("LSC-1", "LSC-2")])
        self.assertEqual(report["verdict"], VERDICT_NOT_MET)

    def test_a_neighbour_entry_naming_an_unknown_charge_raises(self):
        with self.assertRaises(ValueError):
            assess_charge_array(
                [charge("LSC-1")],
                [{"charges": ["LSC-1", "LSC-9"], "spacing_mm": 200.0}],
            )

    def test_a_charge_declared_as_its_own_neighbour_raises(self):
        with self.assertRaises(ValueError):
            assess_charge_array(
                [charge("LSC-1")],
                [{"charges": ["LSC-1", "LSC-1"], "spacing_mm": 200.0}],
            )

    def test_a_duplicate_neighbour_pair_raises(self):
        with self.assertRaises(ValueError):
            assess_charge_array(
                [charge("LSC-1"), charge("LSC-2")],
                [
                    {"charges": ["LSC-1", "LSC-2"], "spacing_mm": 200.0},
                    {"charges": ["LSC-2", "LSC-1"], "spacing_mm": 210.0},
                ],
            )

    def test_an_array_with_no_declared_neighbours_is_graded_per_charge(self):
        report = assess_charge_array([charge("LSC-1")])
        self.assertTrue(report["compliant"])
        self.assertEqual(report["spacings"], [])


if __name__ == "__main__":
    unittest.main()
