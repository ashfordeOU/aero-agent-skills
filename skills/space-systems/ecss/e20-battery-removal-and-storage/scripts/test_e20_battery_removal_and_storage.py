#!/usr/bin/env python3
"""Gate 3 contract test for e20-battery-removal-and-storage (stdlib, offline)."""

import unittest

from e20_battery_removal_and_storage_logic import (
    ACCESS_PATHS,
    acceptance_status_after_removal,
    categorize_access_path,
    evaluate_storage_envelope,
    maintenance_charge_interval_days,
    plan_removal_and_storage,
    project_storage_state_of_charge,
    required_reverification,
    self_discharge_rate_pct_per_month,
    validate_module,
)

FULL_ALLOWANCE = [
    "visual-condition-check",
    "insulation-resistance-check",
    "fastener-torque-recheck",
    "harness-continuity-check",
    "bonding-resistance-check",
    "battery-capacity-retest",
    "cell-health-assessment",
]


def module(**overrides):
    """Nominal, compliant battery module storage plan."""
    base = {
        "module_id": "BAT-M1",
        "access_path": "panel-removal",
        "initial_soc_pct": 60.0,
        "base_self_discharge_pct_per_month": 3.0,
        "storage_temp_c": 20.0,
        "storage_days": 90.0,
        "min_storage_soc_pct": 40.0,
        "min_storage_temp_c": 0.0,
        "max_storage_temp_c": 30.0,
        "max_storage_days": 180.0,
        "storage_humidity_pct": 45.0,
        "max_storage_humidity_pct": 60.0,
    }
    base.update(overrides)
    return base


class ValidationTests(unittest.TestCase):
    def test_nominal_module_validates_and_normalizes(self):
        rec = validate_module(module())
        self.assertEqual(rec["module_id"], "BAT-M1")
        self.assertEqual(rec["access_path"], "panel-removal")
        self.assertAlmostEqual(rec["initial_soc_pct"], 60.0)

    def test_non_mapping_module_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_module(["not", "a", "mapping"])

    def test_missing_field_is_rejected(self):
        bad = module()
        del bad["storage_temp_c"]
        with self.assertRaises(ValueError):
            validate_module(bad)

    def test_blank_module_id_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_module(module(module_id="   "))

    def test_unknown_access_path_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_module(module(access_path="magic-hatch"))

    def test_boolean_numeric_field_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_module(module(storage_days=True))

    def test_out_of_range_percentage_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_module(module(initial_soc_pct=140.0))

    def test_inverted_temperature_band_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_module(module(min_storage_temp_c=40.0, max_storage_temp_c=10.0))

    def test_initial_soc_at_or_below_floor_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_module(module(initial_soc_pct=40.0, min_storage_soc_pct=40.0))

    def test_non_positive_self_discharge_rate_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_module(module(base_self_discharge_pct_per_month=0.0))

    def test_negative_storage_duration_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_module(module(storage_days=-1.0))


class AccessPathTests(unittest.TestCase):
    def test_every_access_path_is_categorized(self):
        for path in ACCESS_PATHS:
            record = categorize_access_path(path)
            self.assertIn("removable", record)
            self.assertIn("tasks", record)

    def test_direct_hatch_access_keeps_qualified_interfaces_intact(self):
        record = categorize_access_path("direct-hatch-access")
        self.assertFalse(record["breaks_qualified_interface"])
        self.assertTrue(record["removable"])

    def test_stack_teardown_breaks_qualified_interfaces(self):
        record = categorize_access_path("stack-teardown")
        self.assertTrue(record["breaks_qualified_interface"])
        self.assertIn("workmanship-vibration-retest", record["tasks"])

    def test_unknown_access_path_categorization_is_rejected(self):
        with self.assertRaises(ValueError):
            categorize_access_path("slide-out-drawer")


class SelfDischargeTests(unittest.TestCase):
    def test_rate_at_reference_temperature_is_the_base_rate(self):
        self.assertAlmostEqual(self_discharge_rate_pct_per_month(3.0, 20.0), 3.0)

    def test_rate_doubles_ten_kelvin_above_reference(self):
        self.assertAlmostEqual(self_discharge_rate_pct_per_month(3.0, 30.0), 6.0)

    def test_rate_halves_ten_kelvin_below_reference(self):
        self.assertAlmostEqual(self_discharge_rate_pct_per_month(3.0, 10.0), 1.5)

    def test_rate_accepts_the_modelled_temperature_boundary(self):
        self.assertAlmostEqual(self_discharge_rate_pct_per_month(1.0, 60.0), 16.0)

    def test_rate_outside_the_modelled_band_is_rejected(self):
        with self.assertRaises(ValueError):
            self_discharge_rate_pct_per_month(3.0, 61.0)

    def test_non_positive_base_rate_is_rejected(self):
        with self.assertRaises(ValueError):
            self_discharge_rate_pct_per_month(-2.0, 20.0)


class ProjectionTests(unittest.TestCase):
    def test_projected_state_of_charge_is_computed(self):
        soc = project_storage_state_of_charge(60.0, 3.0, 20.0, 90.0)
        self.assertAlmostEqual(soc, 51.0)

    def test_projection_floors_at_zero_rather_than_going_negative(self):
        soc = project_storage_state_of_charge(10.0, 3.0, 60.0, 3650.0)
        self.assertAlmostEqual(soc, 0.0)

    def test_zero_duration_leaves_state_of_charge_untouched(self):
        soc = project_storage_state_of_charge(77.5, 3.0, 25.0, 0.0)
        self.assertAlmostEqual(soc, 77.5)

    def test_negative_duration_is_rejected(self):
        with self.assertRaises(ValueError):
            project_storage_state_of_charge(60.0, 3.0, 20.0, -5.0)

    def test_out_of_range_initial_state_of_charge_is_rejected(self):
        with self.assertRaises(ValueError):
            project_storage_state_of_charge(120.0, 3.0, 20.0, 10.0)

    def test_maintenance_interval_matches_the_linear_drain(self):
        days = maintenance_charge_interval_days(60.0, 40.0, 3.0, 20.0)
        self.assertAlmostEqual(days, 200.0)

    def test_warmer_storage_shortens_the_maintenance_interval(self):
        cold = maintenance_charge_interval_days(60.0, 40.0, 3.0, 10.0)
        warm = maintenance_charge_interval_days(60.0, 40.0, 3.0, 30.0)
        self.assertAlmostEqual(cold, 4.0 * warm)

    def test_floor_above_initial_state_of_charge_is_rejected(self):
        with self.assertRaises(ValueError):
            maintenance_charge_interval_days(30.0, 40.0, 3.0, 20.0)


class EnvelopeTests(unittest.TestCase):
    def test_nominal_plan_has_no_storage_breach(self):
        projected, breaches = evaluate_storage_envelope(module())
        self.assertAlmostEqual(projected, 51.0)
        self.assertEqual(breaches, [])

    def test_state_of_charge_exactly_at_the_floor_is_not_a_breach(self):
        projected, breaches = evaluate_storage_envelope(
            module(initial_soc_pct=70.0, storage_days=300.0, max_storage_days=400.0)
        )
        self.assertAlmostEqual(projected, 40.0)
        self.assertEqual(breaches, [])

    def test_temperature_at_the_upper_band_edge_is_not_an_excursion(self):
        _, breaches = evaluate_storage_envelope(
            module(storage_temp_c=30.0, initial_soc_pct=90.0)
        )
        self.assertNotIn("storage-temperature-excursion", breaches)

    def test_warm_storage_outside_the_band_is_flagged(self):
        _, breaches = evaluate_storage_envelope(
            module(storage_temp_c=40.0, initial_soc_pct=90.0)
        )
        self.assertIn("storage-temperature-excursion", breaches)

    def test_long_storage_flags_deep_discharge_and_shelf_life(self):
        projected, breaches = evaluate_storage_envelope(module(storage_days=600.0))
        self.assertAlmostEqual(projected, 0.0)
        self.assertIn("deep-discharge-below-floor", breaches)
        self.assertIn("shelf-life-exceeded", breaches)

    def test_humidity_above_limit_is_flagged(self):
        _, breaches = evaluate_storage_envelope(module(storage_humidity_pct=80.0))
        self.assertEqual(breaches, ["humidity-limit-exceeded"])


class ReverificationTests(unittest.TestCase):
    def test_task_set_follows_the_access_path(self):
        tasks = required_reverification("harness-demate")
        self.assertIn("harness-continuity-check", tasks)
        self.assertIn("bonding-resistance-check", tasks)

    def test_breaches_add_tasks_without_duplicating_them(self):
        tasks = required_reverification(
            "panel-removal",
            ["deep-discharge-below-floor", "humidity-limit-exceeded"],
        )
        self.assertIn("cell-health-assessment", tasks)
        self.assertEqual(len(tasks), len(set(tasks)))

    def test_unknown_breach_is_rejected(self):
        with self.assertRaises(ValueError):
            required_reverification("panel-removal", ["cosmic-ray-strike"])

    def test_acceptance_preserved_when_the_allowance_covers_every_task(self):
        state, uncovered = acceptance_status_after_removal(
            ("visual-condition-check",), FULL_ALLOWANCE, True
        )
        self.assertEqual(state, "preserved-with-delta-reverification")
        self.assertEqual(uncovered, ())

    def test_acceptance_lost_when_a_task_sits_outside_the_allowance(self):
        state, uncovered = acceptance_status_after_removal(
            ("workmanship-vibration-retest",), FULL_ALLOWANCE, True
        )
        self.assertEqual(state, "invalidated-reverification-not-covered")
        self.assertEqual(uncovered, ("workmanship-vibration-retest",))

    def test_non_boolean_removability_is_rejected(self):
        with self.assertRaises(ValueError):
            acceptance_status_after_removal((), FULL_ALLOWANCE, "yes")

    def test_non_collection_allowance_is_rejected(self):
        with self.assertRaises(ValueError):
            acceptance_status_after_removal((), "visual-condition-check", True)


class PlanTests(unittest.TestCase):
    def test_nominal_plan_is_compliant(self):
        out = plan_removal_and_storage(module(), FULL_ALLOWANCE)
        self.assertTrue(out["compliant"])
        self.assertEqual(out["acceptance_state"], "preserved-with-delta-reverification")
        self.assertAlmostEqual(out["projected_soc_pct"], 51.0)
        self.assertAlmostEqual(out["maintenance_charge_interval_days"], 200.0)

    def test_non_removable_module_loses_acceptance_status(self):
        out = plan_removal_and_storage(module(access_path="non-removable"), FULL_ALLOWANCE)
        self.assertFalse(out["compliant"])
        self.assertEqual(out["acceptance_state"], "invalidated-module-not-removable")

    def test_stack_teardown_exceeds_a_delta_only_allowance(self):
        out = plan_removal_and_storage(module(access_path="stack-teardown"), FULL_ALLOWANCE)
        self.assertEqual(out["acceptance_state"], "invalidated-reverification-not-covered")
        self.assertIn("workmanship-vibration-retest", out["uncovered_reverification"])

    def test_storage_breach_alone_blocks_compliance(self):
        out = plan_removal_and_storage(module(storage_humidity_pct=95.0), FULL_ALLOWANCE)
        self.assertFalse(out["compliant"])
        self.assertEqual(out["storage_breaches"], ("humidity-limit-exceeded",))


if __name__ == "__main__":
    unittest.main()
