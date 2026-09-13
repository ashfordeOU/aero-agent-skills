#!/usr/bin/env python3
"""Gate 3 contract test for e2006-floating-conductive-part-exceptions."""

import math
import unittest

from e2006_floating_conductive_part_exceptions_logic import (
    DEFAULT_EXCEPTION_LIMITS,
    VACUUM_PERMITTIVITY,
    assess_floating_inventory,
    bounding_floating_potential,
    categorize_energy_band,
    default_exception_limits,
    evaluate_floating_part,
    isolated_body_capacitance,
    leakage_clamped_potential,
    parallel_plate_capacitance,
    peak_discharge_current,
    resolve_capacitance,
    resolve_exception_limits,
    stored_energy,
    within_limit,
)

V_GEO = 1000.0   # bounding surface potential, V
J_GEO = 1.0e-6   # A/m^2


def fastener_part(**overrides):
    part = {
        "id": "panel-fastener-head",
        "exposed_area_m2": 5.0e-5,
        "equivalent_radius_m": 0.004,
    }
    part.update(overrides)
    return part


def radome_insert(**overrides):
    part = {
        "id": "radome-insert",
        "exposed_area_m2": 1.0e-3,
        "standoff_gap_m": 1.0e-4,
        "relative_permittivity": 3.5,
    }
    part.update(overrides)
    return part


class RatioMixin(unittest.TestCase):
    def assertRatio(self, value, expected, places=12):
        self.assertAlmostEqual(value / expected, 1.0, places=places)


class TestExceptionLimits(RatioMixin):
    def test_defaults_are_positive(self):
        for key, value in DEFAULT_EXCEPTION_LIMITS.items():
            self.assertGreater(value, 0.0, key)

    def test_defaults_are_returned_as_a_fresh_copy(self):
        first = default_exception_limits()
        first["max_capacitance_f"] = 1.0
        self.assertRatio(default_exception_limits()["max_capacitance_f"], 1.0e-10)

    def test_no_overrides_returns_the_defaults(self):
        self.assertEqual(resolve_exception_limits(), default_exception_limits())

    def test_override_replaces_one_limit(self):
        limits = resolve_exception_limits({"max_stored_energy_j": 1.0e-4})
        self.assertRatio(limits["max_stored_energy_j"], 1.0e-4)
        self.assertRatio(limits["max_exposed_area_m2"], 1.0e-4)

    def test_unknown_override_key_is_rejected(self):
        with self.assertRaises(ValueError):
            resolve_exception_limits({"max_voltage_v": 100.0})

    def test_non_positive_override_is_rejected(self):
        with self.assertRaises(ValueError):
            resolve_exception_limits({"max_capacitance_f": 0.0})

    def test_non_mapping_override_is_rejected(self):
        with self.assertRaises(ValueError):
            resolve_exception_limits([("max_capacitance_f", 1.0e-12)])


class TestCapacitanceGeometry(RatioMixin):
    def test_plate_capacitance_matches_the_formula(self):
        value = parallel_plate_capacitance(1.0e-3, 1.0e-4, relative_permittivity=3.5)
        self.assertRatio(value, VACUUM_PERMITTIVITY * 3.5 * 1.0e-3 / 1.0e-4)

    def test_thinner_standoff_raises_capacitance(self):
        thin = parallel_plate_capacitance(1.0e-3, 5.0e-5)
        thick = parallel_plate_capacitance(1.0e-3, 1.0e-4)
        self.assertRatio(thin / thick, 2.0)

    def test_permittivity_below_unity_is_rejected(self):
        with self.assertRaises(ValueError):
            parallel_plate_capacitance(1.0e-3, 1.0e-4, relative_permittivity=0.5)

    def test_zero_gap_is_rejected(self):
        with self.assertRaises(ValueError):
            parallel_plate_capacitance(1.0e-3, 0.0)

    def test_compact_body_capacitance_matches_the_formula(self):
        self.assertRatio(
            isolated_body_capacitance(0.004), 4.0 * math.pi * VACUUM_PERMITTIVITY * 0.004
        )

    def test_compact_body_capacitance_is_linear_in_radius(self):
        self.assertRatio(isolated_body_capacitance(0.008) / isolated_body_capacitance(0.004), 2.0)

    def test_zero_radius_is_rejected(self):
        with self.assertRaises(ValueError):
            isolated_body_capacitance(0.0)


class TestCapacitanceFormResolution(RatioMixin):
    def test_explicit_capacitance_is_used_as_declared(self):
        part = {"id": "shim", "exposed_area_m2": 1.0e-5, "capacitance_f": 2.0e-12}
        self.assertRatio(resolve_capacitance(part), 2.0e-12)

    def test_compact_body_form_is_resolved(self):
        self.assertRatio(resolve_capacitance(fastener_part()), isolated_body_capacitance(0.004))

    def test_standoff_form_uses_the_exposed_area(self):
        self.assertRatio(
            resolve_capacitance(radome_insert()),
            parallel_plate_capacitance(1.0e-3, 1.0e-4, relative_permittivity=3.5),
        )

    def test_no_declared_form_is_rejected(self):
        with self.assertRaises(ValueError):
            resolve_capacitance({"id": "shim", "exposed_area_m2": 1.0e-5})

    def test_two_declared_forms_are_rejected(self):
        with self.assertRaises(ValueError):
            resolve_capacitance(fastener_part(capacitance_f=2.0e-12))

    def test_permittivity_with_a_compact_body_is_rejected(self):
        with self.assertRaises(ValueError):
            resolve_capacitance(fastener_part(relative_permittivity=3.5))

    def test_non_mapping_part_is_rejected(self):
        with self.assertRaises(ValueError):
            resolve_capacitance(["panel-fastener-head"])


class TestFloatingPotential(RatioMixin):
    def test_part_with_no_leakage_path_floats_to_the_environment(self):
        self.assertRatio(bounding_floating_potential(V_GEO), V_GEO)

    def test_negative_environment_potential_uses_its_magnitude(self):
        self.assertRatio(bounding_floating_potential(-V_GEO), V_GEO)

    def test_leakage_path_clamps_below_the_environment(self):
        potential = bounding_floating_potential(
            V_GEO,
            current_density_a_m2=J_GEO,
            exposed_area_m2=5.0e-5,
            leakage_resistance_ohm=1.0e12,
        )
        self.assertRatio(potential, 50.0)

    def test_weak_leakage_path_does_not_clamp(self):
        potential = bounding_floating_potential(
            V_GEO,
            current_density_a_m2=J_GEO,
            exposed_area_m2=5.0e-5,
            leakage_resistance_ohm=1.0e16,
        )
        self.assertRatio(potential, V_GEO)

    def test_clamped_potential_formula(self):
        self.assertRatio(leakage_clamped_potential(J_GEO, 5.0e-5, 1.0e12), 50.0)

    def test_leakage_path_without_area_is_rejected(self):
        with self.assertRaises(ValueError):
            bounding_floating_potential(
                V_GEO, current_density_a_m2=J_GEO, leakage_resistance_ohm=1.0e12
            )

    def test_zero_environment_potential_is_rejected(self):
        with self.assertRaises(ValueError):
            bounding_floating_potential(0.0)

    def test_negative_leakage_resistance_is_rejected(self):
        with self.assertRaises(ValueError):
            leakage_clamped_potential(J_GEO, 5.0e-5, -1.0e12)


class TestEnergyAndDischarge(RatioMixin):
    def test_stored_energy_formula(self):
        self.assertRatio(stored_energy(2.0e-12, 1000.0), 1.0e-6)

    def test_energy_is_quadratic_in_potential(self):
        full = stored_energy(1.0e-12, 1000.0)
        half = stored_energy(1.0e-12, 500.0)
        self.assertRatio(full / half, 4.0)

    def test_energy_ignores_the_sign_of_the_potential(self):
        self.assertRatio(stored_energy(1.0e-12, -1000.0), stored_energy(1.0e-12, 1000.0))

    def test_zero_capacitance_is_rejected(self):
        with self.assertRaises(ValueError):
            stored_energy(0.0, 1000.0)

    def test_peak_discharge_current_formula(self):
        self.assertRatio(peak_discharge_current(1.0e-10, 1000.0, 1.0e-8), 10.0)

    def test_faster_rise_time_raises_the_peak_current(self):
        fast = peak_discharge_current(1.0e-10, 1000.0, 1.0e-9)
        slow = peak_discharge_current(1.0e-10, 1000.0, 1.0e-8)
        self.assertRatio(fast / slow, 10.0)

    def test_zero_rise_time_is_rejected(self):
        with self.assertRaises(ValueError):
            peak_discharge_current(1.0e-10, 1000.0, 0.0)

    def test_energy_bands(self):
        self.assertEqual(categorize_energy_band(1.0e-9), "benign")
        self.assertEqual(categorize_energy_band(1.0e-5), "upset-credible")
        self.assertEqual(categorize_energy_band(1.0e-2), "damage-credible")

    def test_energy_band_edges_are_upper_exclusive(self):
        self.assertEqual(categorize_energy_band(1.0e-6), "upset-credible")
        self.assertEqual(categorize_energy_band(1.0e-3), "damage-credible")

    def test_negative_energy_is_rejected(self):
        with self.assertRaises(ValueError):
            categorize_energy_band(-1.0e-9)


class TestLimitComparison(RatioMixin):
    def test_below_limit_passes(self):
        self.assertTrue(within_limit(5.0e-5, 1.0e-4))

    def test_above_limit_fails(self):
        self.assertFalse(within_limit(2.0e-4, 1.0e-4))

    def test_exact_limit_passes(self):
        self.assertTrue(within_limit(1.0e-4, 1.0e-4))

    def test_product_of_powers_of_ten_drifts_over_the_limit(self):
        drifted = stored_energy(2.0e-12, 1000.0)
        self.assertGreater(drifted, 1.0e-6)
        self.assertTrue(within_limit(drifted, 1.0e-6))

    def test_drift_absorption_does_not_raise_the_limit(self):
        self.assertFalse(within_limit(1.0e-6 * (1.0 + 1.0e-6), 1.0e-6))


class TestPartEvaluation(RatioMixin):
    def test_small_fastener_gets_the_exception(self):
        result = evaluate_floating_part(fastener_part(), V_GEO)
        self.assertEqual(result["disposition"], "exception-granted")
        self.assertEqual(result["failed_criteria"], [])
        self.assertEqual(result["energy_band"], "benign")
        self.assertFalse(result["clamped_by_leakage_path"])

    def test_large_insert_fails_all_three_criteria(self):
        result = evaluate_floating_part(radome_insert(), V_GEO)
        self.assertEqual(result["disposition"], "grounding-required")
        self.assertEqual(
            result["failed_criteria"], ["capacitance", "exposed-area", "stored-energy"]
        )
        self.assertEqual(result["energy_band"], "upset-credible")

    def test_small_part_can_still_fail_on_energy_alone(self):
        part = {"id": "shim", "exposed_area_m2": 5.0e-5, "capacitance_f": 1.0e-10}
        result = evaluate_floating_part(part, V_GEO)
        self.assertEqual(result["failed_criteria"], ["stored-energy"])
        self.assertEqual(result["disposition"], "grounding-required")

    def test_a_bleed_path_can_rescue_that_same_part(self):
        part = {
            "id": "shim",
            "exposed_area_m2": 5.0e-5,
            "capacitance_f": 1.0e-10,
            "leakage_resistance_ohm": 1.0e12,
        }
        result = evaluate_floating_part(part, V_GEO, current_density_a_m2=J_GEO)
        self.assertEqual(result["disposition"], "exception-granted")
        self.assertTrue(result["clamped_by_leakage_path"])
        self.assertRatio(result["floating_potential_v"], 50.0)

    def test_exact_energy_limit_is_granted_despite_representation_drift(self):
        part = {"id": "clip", "exposed_area_m2": 5.0e-5, "capacitance_f": 2.0e-12}
        result = evaluate_floating_part(part, V_GEO)
        self.assertGreater(result["stored_energy_j"], 1.0e-6)
        self.assertTrue(result["criteria"]["stored-energy"])
        self.assertEqual(result["disposition"], "exception-granted")

    def test_tighter_programme_limits_refuse_a_default_grant(self):
        result = evaluate_floating_part(
            fastener_part(), V_GEO, limits={"max_stored_energy_j": 1.0e-9}
        )
        self.assertEqual(result["failed_criteria"], ["stored-energy"])

    def test_rise_time_override_changes_the_peak_current(self):
        slow = evaluate_floating_part(fastener_part(discharge_rise_time_s=1.0e-6), V_GEO)
        fast = evaluate_floating_part(fastener_part(), V_GEO)
        self.assertRatio(fast["peak_discharge_current_a"] / slow["peak_discharge_current_a"], 100.0)

    def test_peak_current_is_consistent_with_the_capacitance(self):
        result = evaluate_floating_part(fastener_part(), V_GEO)
        self.assertRatio(
            result["peak_discharge_current_a"],
            peak_discharge_current(result["capacitance_f"], V_GEO, 1.0e-8),
        )

    def test_missing_required_key_is_rejected(self):
        part = fastener_part()
        del part["exposed_area_m2"]
        with self.assertRaises(ValueError):
            evaluate_floating_part(part, V_GEO)

    def test_unknown_part_key_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_floating_part(fastener_part(material="titanium"), V_GEO)

    def test_blank_part_id_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_floating_part(fastener_part(id="   "), V_GEO)

    def test_zero_exposed_area_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_floating_part(fastener_part(exposed_area_m2=0.0), V_GEO)

    def test_part_without_a_capacitance_form_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_floating_part({"id": "shim", "exposed_area_m2": 5.0e-5}, V_GEO)

    def test_non_mapping_part_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_floating_part("panel-fastener-head", V_GEO)


class TestInventoryAssessment(RatioMixin):
    def inventory(self):
        return [
            fastener_part(),
            radome_insert(),
            {"id": "harness-shield-tail", "exposed_area_m2": 2.0e-5, "capacitance_f": 1.5e-12},
        ]

    def test_inventory_counts_both_dispositions(self):
        summary = assess_floating_inventory(self.inventory(), V_GEO)
        self.assertEqual(summary["counts"]["exception-granted"], 2)
        self.assertEqual(summary["counts"]["grounding-required"], 1)
        self.assertFalse(summary["compliant"])

    def test_inventory_lists_the_parts_needing_grounding(self):
        summary = assess_floating_inventory(self.inventory(), V_GEO)
        self.assertEqual(summary["grounding_required"], ["radome-insert"])

    def test_inventory_reports_the_failure_drivers(self):
        summary = assess_floating_inventory(self.inventory(), V_GEO)
        self.assertEqual(
            summary["failure_drivers"],
            {"capacitance": 1, "exposed-area": 1, "stored-energy": 1},
        )

    def test_inventory_identifies_the_highest_energy_part(self):
        summary = assess_floating_inventory(self.inventory(), V_GEO)
        self.assertEqual(summary["highest_energy_id"], "radome-insert")
        self.assertGreater(summary["highest_energy_j"], 1.0e-5)

    def test_all_granted_inventory_is_compliant(self):
        parts = [p for p in self.inventory() if p["id"] != "radome-insert"]
        summary = assess_floating_inventory(parts, V_GEO)
        self.assertTrue(summary["compliant"])
        self.assertEqual(summary["failure_drivers"], {})

    def test_duplicate_part_id_is_rejected(self):
        parts = self.inventory()
        parts[2]["id"] = "panel-fastener-head"
        with self.assertRaises(ValueError):
            assess_floating_inventory(parts, V_GEO)

    def test_empty_inventory_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_floating_inventory([], V_GEO)

    def test_non_sequence_inventory_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_floating_inventory({"id": "shim"}, V_GEO)


if __name__ == "__main__":
    unittest.main()
