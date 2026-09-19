"""Contract tests for the clause 4.3.2 mechanical interface requirements logic."""

import math
import unittest

from e31_mechanical_interface_requirements_logic import (
    ARCSEC_PER_RADIAN,
    CONDUCTANCE_TOLERANCE_W_PER_K,
    FILLER_PRESSURE_CURVES,
    alignment_contribution_arcsec,
    assess_mechanical_interfaces,
    assess_mount,
    conductance_margin_fraction,
    contact_pressure_pa,
    differential_expansion_m,
    filler_coefficient_w_per_m2k,
    interface_conductance_w_per_k,
    interface_hardware_mass_kg,
    required_conductance_w_per_k,
    validate_positive,
)


def base_mount(**overrides):
    """Return a representative unit-to-panel mounting interface record."""
    mount = {
        "name": "transponder-baseplate",
        "filler": "thermal-filler-pad",
        "preload_per_bolt_n": 2500.0,
        "bolt_count": 8,
        "contact_area_m2": 0.04,
        "effective_area_m2": 0.035,
        "dissipation_w": 45.0,
        "allowed_rise_k": 4.0,
        "alpha_item_per_k": 23.0e-6,
        "alpha_panel_per_k": 2.0e-6,
        "delta_temperature_k": 90.0,
        "footprint_m": 0.18,
        "allowable_slip_m": 1.0e-3,
        "lever_arm_m": 0.25,
        "alignment_allocation_arcsec": 400.0,
        "hardware_mass_kg": 0.22,
    }
    mount.update(overrides)
    return mount


class ValidatePositiveTests(unittest.TestCase):
    def test_returns_float(self):
        self.assertEqual(validate_positive("x", 3), 3.0)

    def test_zero_rejected_by_default(self):
        with self.assertRaises(ValueError):
            validate_positive("x", 0.0)

    def test_zero_allowed_when_asked(self):
        self.assertEqual(validate_positive("x", 0.0, allow_zero=True), 0.0)

    def test_boolean_rejected(self):
        with self.assertRaises(ValueError):
            validate_positive("x", True)

    def test_non_finite_rejected(self):
        with self.assertRaises(ValueError):
            validate_positive("x", float("nan"))


class ContactPressureTests(unittest.TestCase):
    def test_pressure_is_total_preload_over_area(self):
        self.assertAlmostEqual(contact_pressure_pa(1000.0, 4, 0.02), 200000.0, places=6)

    def test_more_bolts_raise_the_pressure(self):
        low = contact_pressure_pa(1000.0, 4, 0.02)
        high = contact_pressure_pa(1000.0, 8, 0.02)
        self.assertAlmostEqual(high / low, 2.0, places=12)

    def test_zero_bolts_rejected(self):
        with self.assertRaises(ValueError):
            contact_pressure_pa(1000.0, 0, 0.02)

    def test_float_bolt_count_rejected(self):
        with self.assertRaises(ValueError):
            contact_pressure_pa(1000.0, 4.0, 0.02)

    def test_zero_area_rejected(self):
        with self.assertRaises(ValueError):
            contact_pressure_pa(1000.0, 4, 0.0)


class FillerCoefficientTests(unittest.TestCase):
    def test_tabulated_point_returned_exactly(self):
        self.assertAlmostEqual(
            filler_coefficient_w_per_m2k("thermal-grease", 5.0e5), 4800.0, places=9
        )

    def test_interpolates_between_points(self):
        value = filler_coefficient_w_per_m2k("bare-metal-to-metal", 3.0e5)
        self.assertAlmostEqual(value, 300.0 + 0.5 * (900.0 - 300.0), places=9)

    def test_grease_beats_bare_metal_at_the_same_pressure(self):
        grease = filler_coefficient_w_per_m2k("thermal-grease", 1.0e6)
        bare = filler_coefficient_w_per_m2k("bare-metal-to-metal", 1.0e6)
        self.assertGreater(grease, bare * 2.0)

    def test_insulating_stack_is_the_poorest_option(self):
        stack = filler_coefficient_w_per_m2k("insulating-washer-stack", 1.0e6)
        bare = filler_coefficient_w_per_m2k("bare-metal-to-metal", 1.0e6)
        self.assertLess(stack, bare)

    def test_unknown_filler_rejected(self):
        with self.assertRaises(ValueError):
            filler_coefficient_w_per_m2k("kapton-tape", 1.0e6)

    def test_pressure_below_the_curve_refused(self):
        with self.assertRaises(ValueError):
            filler_coefficient_w_per_m2k("thermal-filler-pad", 1.0e4)

    def test_pressure_above_the_curve_refused(self):
        with self.assertRaises(ValueError):
            filler_coefficient_w_per_m2k("thermal-filler-pad", 5.0e7)

    def test_every_curve_increases_with_pressure(self):
        for name, curve in FILLER_PRESSURE_CURVES.items():
            for index in range(1, len(curve)):
                self.assertGreater(curve[index][0], curve[index - 1][0], name)
                self.assertGreater(curve[index][1], curve[index - 1][1], name)


class ConductanceTests(unittest.TestCase):
    def test_conductance_is_coefficient_times_area(self):
        self.assertAlmostEqual(
            interface_conductance_w_per_k(2000.0, 0.03), 60.0, places=9
        )

    def test_required_conductance_is_load_over_rise(self):
        self.assertAlmostEqual(
            required_conductance_w_per_k(40.0, 5.0), 8.0, places=9
        )

    def test_zero_allowed_rise_rejected(self):
        with self.assertRaises(ValueError):
            required_conductance_w_per_k(40.0, 0.0)

    def test_margin_is_zero_when_achieved_equals_required(self):
        self.assertAlmostEqual(conductance_margin_fraction(8.0, 8.0), 0.0, places=12)

    def test_margin_is_negative_when_short(self):
        self.assertAlmostEqual(conductance_margin_fraction(6.0, 8.0), -0.25, places=12)


class ExpansionTests(unittest.TestCase):
    def test_differential_growth_uses_the_mismatch(self):
        value = differential_expansion_m(23.0e-6, 3.0e-6, 100.0, 0.2)
        self.assertAlmostEqual(value, 20.0e-6 * 100.0 * 0.2, places=15)

    def test_matched_materials_give_no_growth(self):
        self.assertAlmostEqual(
            differential_expansion_m(16.0e-6, 16.0e-6, 120.0, 0.3), 0.0, places=15
        )

    def test_sign_of_the_mismatch_does_not_matter(self):
        forward = differential_expansion_m(23.0e-6, 3.0e-6, 80.0, 0.15)
        reverse = differential_expansion_m(3.0e-6, 23.0e-6, 80.0, 0.15)
        self.assertAlmostEqual(forward, reverse, places=15)

    def test_negative_cte_accepted(self):
        value = differential_expansion_m(23.0e-6, -1.0e-6, 100.0, 0.1)
        self.assertAlmostEqual(value, 24.0e-6 * 100.0 * 0.1, places=15)

    def test_zero_swing_rejected(self):
        with self.assertRaises(ValueError):
            differential_expansion_m(23.0e-6, 3.0e-6, 0.0, 0.2)

    def test_non_numeric_cte_rejected(self):
        with self.assertRaises(ValueError):
            differential_expansion_m("23e-6", 3.0e-6, 100.0, 0.2)


class AlignmentTests(unittest.TestCase):
    def test_small_angle_matches_the_ratio(self):
        value = alignment_contribution_arcsec(1.0e-4, 0.5)
        self.assertAlmostEqual(value, (1.0e-4 / 0.5) * ARCSEC_PER_RADIAN, places=4)

    def test_zero_slip_gives_no_tilt(self):
        self.assertAlmostEqual(alignment_contribution_arcsec(0.0, 0.4), 0.0, places=12)

    def test_longer_lever_arm_reduces_the_tilt(self):
        short = alignment_contribution_arcsec(2.0e-4, 0.1)
        long_arm = alignment_contribution_arcsec(2.0e-4, 0.4)
        self.assertGreater(short, long_arm)

    def test_zero_lever_arm_rejected(self):
        with self.assertRaises(ValueError):
            alignment_contribution_arcsec(1.0e-4, 0.0)


class HardwareMassTests(unittest.TestCase):
    def test_mass_sums_the_records(self):
        mounts = [base_mount(), base_mount(name="b", hardware_mass_kg=0.18)]
        self.assertAlmostEqual(interface_hardware_mass_kg(mounts), 0.40, places=12)

    def test_contingency_scales_the_total(self):
        mounts = [base_mount()]
        self.assertAlmostEqual(
            interface_hardware_mass_kg(mounts, 0.20), 0.22 * 1.20, places=12
        )

    def test_missing_mass_is_unknown_not_zero(self):
        mount = base_mount()
        del mount["hardware_mass_kg"]
        with self.assertRaises(ValueError):
            interface_hardware_mass_kg([mount])

    def test_empty_mount_list_rejected(self):
        with self.assertRaises(ValueError):
            interface_hardware_mass_kg([])


class AssessMountTests(unittest.TestCase):
    def test_nominal_mount_is_compliant(self):
        record = assess_mount(base_mount())
        self.assertTrue(record["compliant"])
        self.assertEqual(record["findings"], [])

    def test_insulating_stack_fails_the_conductance_requirement(self):
        record = assess_mount(base_mount(filler="insulating-washer-stack"))
        self.assertFalse(record["compliant"])
        self.assertTrue(any("conductance" in f for f in record["findings"]))

    def test_conductance_exactly_on_the_requirement_is_accepted(self):
        mount = base_mount()
        record = assess_mount(mount)
        achieved = record["conductance_w_per_k"]
        tuned = base_mount(dissipation_w=achieved * 4.0)
        tuned_record = assess_mount(tuned)
        self.assertAlmostEqual(
            tuned_record["conductance_w_per_k"],
            tuned_record["required_conductance_w_per_k"],
            places=9,
        )
        self.assertTrue(tuned_record["compliant"])

    def test_tolerance_is_small_enough_to_be_a_rounding_allowance(self):
        self.assertLess(CONDUCTANCE_TOLERANCE_W_PER_K, 1e-6)

    def test_large_cte_mismatch_trips_the_slip_finding(self):
        record = assess_mount(base_mount(allowable_slip_m=1.0e-5))
        self.assertFalse(record["compliant"])
        self.assertTrue(any("slip" in f for f in record["findings"]))

    def test_tight_alignment_allocation_trips_the_alignment_finding(self):
        record = assess_mount(base_mount(alignment_allocation_arcsec=1.0))
        self.assertFalse(record["compliant"])
        self.assertTrue(any("alignment" in f for f in record["findings"]))

    def test_missing_key_rejected(self):
        mount = base_mount()
        del mount["lever_arm_m"]
        with self.assertRaises(ValueError):
            assess_mount(mount)

    def test_non_mapping_rejected(self):
        with self.assertRaises(ValueError):
            assess_mount(["transponder"])


class AssessInterfacesTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "mounts": [base_mount(), base_mount(name="tx-bracket",
                                                dissipation_w=12.0,
                                                hardware_mass_kg=0.09)],
            "mass_allocation_kg": 0.6,
            "mass_contingency_fraction": 0.10,
        }
        spec.update(overrides)
        return spec

    def test_nominal_assessment_is_compliant(self):
        result = assess_mechanical_interfaces(self._spec())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])
        self.assertEqual(len(result["mounts"]), 2)

    def test_mass_margin_reported(self):
        result = assess_mechanical_interfaces(self._spec())
        expected = (0.6 - (0.31 * 1.10)) / 0.6
        self.assertAlmostEqual(result["mass_margin_fraction"], expected, places=12)

    def test_mass_overrun_raises_a_finding(self):
        result = assess_mechanical_interfaces(self._spec(mass_allocation_kg=0.2))
        self.assertFalse(result["compliant"])
        self.assertTrue(any("hardware mass" in f for f in result["findings"]))

    def test_duplicate_names_are_a_traceability_finding(self):
        spec = self._spec()
        spec["mounts"][1]["name"] = spec["mounts"][0]["name"]
        result = assess_mechanical_interfaces(spec)
        self.assertFalse(result["compliant"])
        self.assertTrue(any("share a name" in f for f in result["findings"]))

    def test_empty_mount_sequence_rejected(self):
        with self.assertRaises(ValueError):
            assess_mechanical_interfaces(self._spec(mounts=[]))

    def test_missing_allocation_rejected(self):
        spec = self._spec()
        del spec["mass_allocation_kg"]
        with self.assertRaises(ValueError):
            assess_mechanical_interfaces(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_mechanical_interfaces("mounts")

    def test_findings_aggregate_from_every_mount(self):
        spec = self._spec()
        spec["mounts"][0]["filler"] = "insulating-washer-stack"
        spec["mounts"][1]["filler"] = "insulating-washer-stack"
        result = assess_mechanical_interfaces(spec)
        self.assertGreaterEqual(len(result["findings"]), 2)

    def test_conductance_grows_with_preload(self):
        low = assess_mount(base_mount(preload_per_bolt_n=1000.0))
        high = assess_mount(base_mount(preload_per_bolt_n=4000.0))
        self.assertGreater(
            high["conductance_w_per_k"], low["conductance_w_per_k"] * 1.05
        )

    def test_arcsec_constant_matches_the_definition(self):
        self.assertAlmostEqual(ARCSEC_PER_RADIAN, math.degrees(1.0) * 3600.0, places=6)


if __name__ == "__main__":
    unittest.main()
