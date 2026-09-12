#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-20C clause 6.3.4.2 charging
protection programme analysis and test planning.

Exercises scripts/e20_charging_programme_analysis_and_testing_logic.py
(stdlib unittest, offline). Contract: a programme activity maps to
exactly one family and an unrecognized activity raises; the mandatory
task set follows the charging regime and always contains both families;
a required task that is absent, None or left open is reported; the
steady-state dielectric field is current density times bulk
resistivity, checked against the breakdown strength derated by a safety
factor; the bleed-off time constant is permittivity times resistivity,
checked against the programme limit; the differential potential is the
magnitude of the surface-to-structure difference against a
discharge-onset threshold; every analysis severity parameter must be
enveloped by a planned test value; a limit met exactly within
representation error passes; and the aggregated review is compliant
only when every finding list is empty.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e20_charging_programme_analysis_and_testing_logic as cp  # noqa: E402


def _geo_tasks():
    return {
        "absolute_potential_analysis": "complete",
        "differential_potential_analysis": "planned",
        "bleed_off_path_analysis": "in_work",
        "electron_beam_surface_charging_test": "planned",
        "discharge_susceptibility_test": "planned",
    }


def _clean_item():
    """A GEO surface-charging item that satisfies every 6.3.4.2 check."""
    return {
        "item_id": "SC-OSR-01",
        "charging_regime": "geo_surface_charging",
        "planned_tasks": _geo_tasks(),
        "electron_current_density_a_per_m2": 1.0e-12,
        "bulk_resistivity_ohm_m": 1.0e14,
        "breakdown_strength_v_per_m": 2.0e7,
        "field_safety_factor": 2.0,
        "relative_permittivity": 3.0,
        "maximum_bleed_off_s": 3600.0,
        "surface_potential_v": -1200.0,
        "structure_potential_v": -100.0,
        "discharge_onset_v": 1500.0,
        "analysis_case": {
            "electron_flux_a_per_m2": 1.0e-12,
            "electron_energy_ev": 20000.0,
            "exposure_duration_s": 3600.0,
        },
        "test_case": {
            "electron_flux_a_per_m2": 2.0e-12,
            "electron_energy_ev": 25000.0,
            "exposure_duration_s": 7200.0,
        },
    }


class TestCategorizeChargingTask(unittest.TestCase):
    def test_potential_task_is_analysis_family(self):
        self.assertEqual(
            cp.categorize_charging_task("absolute_potential_analysis"),
            "analysis",
        )

    def test_deep_dielectric_task_is_analysis_family(self):
        self.assertEqual(
            cp.categorize_charging_task("deep_dielectric_field_analysis"),
            "analysis",
        )

    def test_electron_beam_task_is_test_family(self):
        self.assertEqual(
            cp.categorize_charging_task("electron_beam_surface_charging_test"),
            "test",
        )

    def test_bleed_off_measurement_is_test_family(self):
        self.assertEqual(
            cp.categorize_charging_task("bleed_off_resistance_measurement"),
            "test",
        )

    def test_families_are_disjoint(self):
        self.assertEqual(
            cp.ANALYSIS_TASK_KINDS & cp.TEST_TASK_KINDS, frozenset()
        )

    def test_unrecognized_task_raises(self):
        with self.assertRaises(ValueError):
            cp.categorize_charging_task("paint_touch_up")


class TestRequiredProgrammeTasks(unittest.TestCase):
    def test_geo_regime_pulls_five_tasks(self):
        self.assertEqual(
            len(cp.required_programme_tasks("geo_surface_charging")), 5
        )

    def test_internal_regime_pulls_dielectric_field_task(self):
        self.assertIn(
            "deep_dielectric_field_analysis",
            cp.required_programme_tasks("internal_dielectric_charging"),
        )

    def test_every_regime_pulls_both_families(self):
        for regime in cp.CHARGING_REGIME_TASKS:
            families = {
                cp.categorize_charging_task(task)
                for task in cp.required_programme_tasks(regime)
            }
            self.assertEqual(families, {"analysis", "test"})

    def test_array_regime_pulls_bleed_off_measurement(self):
        self.assertIn(
            "bleed_off_resistance_measurement",
            cp.required_programme_tasks("solar_array_triple_junction"),
        )

    def test_unrecognized_regime_raises(self):
        with self.assertRaises(ValueError):
            cp.required_programme_tasks("interplanetary_dust_charging")


class TestMissingProgrammeTasks(unittest.TestCase):
    def test_complete_programme_reports_nothing(self):
        self.assertEqual(
            cp.missing_programme_tasks(_geo_tasks(), "geo_surface_charging"),
            [],
        )

    def test_absent_task_is_missing(self):
        tasks = _geo_tasks()
        del tasks["discharge_susceptibility_test"]
        self.assertEqual(
            cp.missing_programme_tasks(tasks, "geo_surface_charging"),
            ["discharge_susceptibility_test"],
        )

    def test_none_status_is_missing(self):
        tasks = _geo_tasks()
        tasks["bleed_off_path_analysis"] = None
        self.assertEqual(
            cp.missing_programme_tasks(tasks, "geo_surface_charging"),
            ["bleed_off_path_analysis"],
        )

    def test_not_planned_status_is_missing(self):
        tasks = _geo_tasks()
        tasks["electron_beam_surface_charging_test"] = "not_planned"
        self.assertEqual(
            cp.missing_programme_tasks(tasks, "geo_surface_charging"),
            ["electron_beam_surface_charging_test"],
        )

    def test_result_is_sorted_and_deterministic(self):
        tasks = {"absolute_potential_analysis": "planned"}
        first = cp.missing_programme_tasks(tasks, "geo_surface_charging")
        second = cp.missing_programme_tasks(tasks, "geo_surface_charging")
        self.assertEqual(first, sorted(first))
        self.assertEqual(first, second)
        self.assertEqual(len(first), 4)

    def test_extra_recognized_task_does_not_count(self):
        tasks = _geo_tasks()
        tasks["dielectric_breakdown_screening"] = "planned"
        self.assertEqual(
            cp.missing_programme_tasks(tasks, "geo_surface_charging"), []
        )

    def test_unrecognized_planned_task_raises(self):
        tasks = _geo_tasks()
        tasks["thermal_vacuum_bakeout"] = "planned"
        with self.assertRaises(ValueError):
            cp.missing_programme_tasks(tasks, "geo_surface_charging")

    def test_unrecognized_status_raises(self):
        tasks = _geo_tasks()
        tasks["absolute_potential_analysis"] = "maybe_later"
        with self.assertRaises(ValueError):
            cp.missing_programme_tasks(tasks, "geo_surface_charging")


class TestPlanningFindings(unittest.TestCase):
    def test_complete_programme_yields_no_finding(self):
        self.assertEqual(
            cp.planning_findings(
                "SC-OSR-01", _geo_tasks(), "geo_surface_charging"
            ),
            [],
        )

    def test_finding_carries_family_and_regime(self):
        tasks = _geo_tasks()
        tasks["discharge_susceptibility_test"] = "not_planned"
        findings = cp.planning_findings(
            "SC-OSR-01", tasks, "geo_surface_charging"
        )
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["family"], "test")
        self.assertEqual(findings[0]["regime"], "geo_surface_charging")
        self.assertEqual(
            findings[0]["issue"], "charging_programme_task_not_planned"
        )

    def test_empty_programme_reports_every_required_task(self):
        findings = cp.planning_findings(
            "SC-OSR-01", {}, "internal_dielectric_charging"
        )
        self.assertEqual(len(findings), 4)


class TestDielectricField(unittest.TestCase):
    def test_field_is_current_density_times_resistivity(self):
        self.assertAlmostEqual(
            cp.dielectric_steady_state_field_v_per_m(2.0e-12, 1.0e14),
            200.0,
            places=6,
        )

    def test_zero_flux_gives_zero_field(self):
        self.assertAlmostEqual(
            cp.dielectric_steady_state_field_v_per_m(0.0, 1.0e15), 0.0, places=9
        )

    def test_negative_current_density_raises(self):
        with self.assertRaises(ValueError):
            cp.dielectric_steady_state_field_v_per_m(-1.0e-12, 1.0e14)

    def test_zero_resistivity_raises(self):
        with self.assertRaises(ValueError):
            cp.dielectric_steady_state_field_v_per_m(1.0e-12, 0.0)

    def test_field_below_allowable_passes(self):
        self.assertEqual(
            cp.dielectric_field_findings("D1", 1.0e6, 2.0e7, 2.0), []
        )

    def test_field_above_allowable_is_flagged(self):
        findings = cp.dielectric_field_findings("D1", 1.5e7, 2.0e7, 2.0)
        self.assertEqual(len(findings), 1)
        self.assertEqual(
            findings[0]["issue"],
            "internal_dielectric_field_exceeds_allowable",
        )
        self.assertAlmostEqual(findings[0]["allowable_v_per_m"], 1.0e7, places=3)

    def test_field_exactly_at_allowable_passes_despite_ulp_drift(self):
        # The computed field lands a few ULPs above the stated allowable;
        # the physically compliant case must still pass.
        field = cp.dielectric_steady_state_field_v_per_m(1.0e-12, 1.0e14)
        self.assertEqual(cp.dielectric_field_findings("D1", field, 200.0, 2.0), [])

    def test_safety_factor_below_one_raises(self):
        with self.assertRaises(ValueError):
            cp.dielectric_field_findings("D1", 1.0e6, 2.0e7, 0.5)

    def test_negative_field_raises(self):
        with self.assertRaises(ValueError):
            cp.dielectric_field_findings("D1", -1.0, 2.0e7, 2.0)

    def test_zero_breakdown_strength_raises(self):
        with self.assertRaises(ValueError):
            cp.dielectric_field_findings("D1", 1.0e6, 0.0, 2.0)


class TestBleedOff(unittest.TestCase):
    def test_time_constant_uses_vacuum_permittivity(self):
        expected = cp.VACUUM_PERMITTIVITY_F_PER_M * 3.0 * 1.0e14
        self.assertAlmostEqual(
            cp.bleed_off_time_constant_s(3.0, 1.0e14), expected, places=6
        )

    def test_higher_resistivity_lengthens_the_time_constant(self):
        slow = cp.bleed_off_time_constant_s(3.0, 1.0e16)
        fast = cp.bleed_off_time_constant_s(3.0, 1.0e14)
        self.assertGreater(slow, fast)

    def test_relative_permittivity_below_one_raises(self):
        with self.assertRaises(ValueError):
            cp.bleed_off_time_constant_s(0.5, 1.0e14)

    def test_non_positive_resistivity_raises(self):
        with self.assertRaises(ValueError):
            cp.bleed_off_time_constant_s(3.0, -1.0e14)

    def test_fast_bleed_off_passes(self):
        self.assertEqual(cp.bleed_off_findings("D1", 100.0, 3600.0), [])

    def test_slow_bleed_off_is_flagged(self):
        findings = cp.bleed_off_findings("D1", 7200.0, 3600.0)
        self.assertEqual(len(findings), 1)
        self.assertEqual(
            findings[0]["issue"], "bleed_off_time_constant_too_long"
        )

    def test_time_constant_exactly_at_limit_passes(self):
        tau = cp.bleed_off_time_constant_s(3.0, 1.0e14)
        self.assertEqual(cp.bleed_off_findings("D1", tau, tau), [])

    def test_negative_time_constant_raises(self):
        with self.assertRaises(ValueError):
            cp.bleed_off_findings("D1", -1.0, 3600.0)

    def test_non_positive_limit_raises(self):
        with self.assertRaises(ValueError):
            cp.bleed_off_findings("D1", 100.0, 0.0)


class TestDifferentialPotential(unittest.TestCase):
    def test_difference_of_two_negative_potentials(self):
        self.assertAlmostEqual(
            cp.differential_potential_v(-1200.0, -100.0), 1100.0, places=6
        )

    def test_sign_order_does_not_matter(self):
        self.assertAlmostEqual(
            cp.differential_potential_v(-100.0, -1200.0), 1100.0, places=6
        )

    def test_equal_potentials_give_zero(self):
        self.assertAlmostEqual(
            cp.differential_potential_v(-500.0, -500.0), 0.0, places=9
        )

    def test_non_finite_potential_raises(self):
        with self.assertRaises(ValueError):
            cp.differential_potential_v(float("inf"), -100.0)

    def test_nan_structure_potential_raises(self):
        with self.assertRaises(ValueError):
            cp.differential_potential_v(-100.0, float("nan"))

    def test_below_onset_passes(self):
        self.assertEqual(
            cp.differential_potential_findings("S1", 400.0, 1000.0), []
        )

    def test_above_onset_is_flagged(self):
        findings = cp.differential_potential_findings("S1", 1400.0, 1000.0)
        self.assertEqual(len(findings), 1)
        self.assertEqual(
            findings[0]["issue"],
            "differential_potential_above_discharge_onset",
        )

    def test_onset_met_exactly_by_a_summed_value_passes(self):
        differential = cp.differential_potential_v(-0.1 - 0.2, 0.0)
        self.assertEqual(
            cp.differential_potential_findings("S1", differential, 0.3), []
        )

    def test_non_positive_onset_raises(self):
        with self.assertRaises(ValueError):
            cp.differential_potential_findings("S1", 400.0, 0.0)


class TestTestEnvelope(unittest.TestCase):
    def test_enveloping_test_passes(self):
        item = _clean_item()
        self.assertEqual(
            cp.test_envelope_findings(
                "SC-OSR-01", item["analysis_case"], item["test_case"]
            ),
            [],
        )

    def test_under_severe_parameter_is_flagged(self):
        item = _clean_item()
        test_case = dict(item["test_case"])
        test_case["electron_energy_ev"] = 10000.0
        findings = cp.test_envelope_findings(
            "SC-OSR-01", item["analysis_case"], test_case
        )
        self.assertEqual(len(findings), 1)
        self.assertEqual(
            findings[0]["issue"], "test_severity_below_analysis_prediction"
        )
        self.assertEqual(findings[0]["parameter"], "electron_energy_ev")

    def test_absent_parameter_is_reported_separately(self):
        item = _clean_item()
        test_case = dict(item["test_case"])
        del test_case["exposure_duration_s"]
        findings = cp.test_envelope_findings(
            "SC-OSR-01", item["analysis_case"], test_case
        )
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["issue"], "test_parameter_not_planned")

    def test_none_parameter_counts_as_not_planned(self):
        item = _clean_item()
        test_case = dict(item["test_case"])
        test_case["exposure_duration_s"] = None
        findings = cp.test_envelope_findings(
            "SC-OSR-01", item["analysis_case"], test_case
        )
        self.assertEqual(findings[0]["issue"], "test_parameter_not_planned")

    def test_equal_severity_passes_despite_summation_drift(self):
        # 0.1 + 0.2 lands a few ULPs above 0.3; a test planned at the
        # predicted value is compliant and must not be flagged.
        findings = cp.test_envelope_findings(
            "SC-OSR-01", {"exposure_duration_s": 0.1 + 0.2},
            {"exposure_duration_s": 0.3},
        )
        self.assertEqual(findings, [])

    def test_findings_are_ordered_by_parameter_name(self):
        findings = cp.test_envelope_findings(
            "SC-OSR-01",
            {"zeta_severity": 5.0, "alpha_severity": 5.0},
            {},
        )
        self.assertEqual(
            [f["parameter"] for f in findings],
            ["alpha_severity", "zeta_severity"],
        )

    def test_empty_analysis_case_raises(self):
        with self.assertRaises(ValueError):
            cp.test_envelope_findings("SC-OSR-01", {}, {"a": 1.0})

    def test_negative_analysis_severity_raises(self):
        with self.assertRaises(ValueError):
            cp.test_envelope_findings(
                "SC-OSR-01", {"electron_energy_ev": -1.0}, {}
            )

    def test_negative_test_severity_raises(self):
        with self.assertRaises(ValueError):
            cp.test_envelope_findings(
                "SC-OSR-01",
                {"electron_energy_ev": 10.0},
                {"electron_energy_ev": -5.0},
            )


class TestProgrammeReview(unittest.TestCase):
    def test_clean_item_is_compliant(self):
        review = cp.programme_review(_clean_item())
        self.assertTrue(cp.is_programme_compliant(review))

    def test_review_carries_all_five_finding_lists(self):
        review = cp.programme_review(_clean_item())
        self.assertEqual(
            sorted(review),
            [
                "bleed_off",
                "dielectric",
                "differential",
                "planning",
                "test_envelope",
            ],
        )

    def test_unplanned_test_breaks_compliance(self):
        item = _clean_item()
        item["planned_tasks"]["discharge_susceptibility_test"] = "not_planned"
        review = cp.programme_review(item)
        self.assertFalse(cp.is_programme_compliant(review))
        self.assertEqual(len(review["planning"]), 1)

    def test_resistive_dielectric_breaks_bleed_off_only(self):
        item = _clean_item()
        item["bulk_resistivity_ohm_m"] = 1.0e18
        item["breakdown_strength_v_per_m"] = 1.0e12
        review = cp.programme_review(item)
        self.assertEqual(review["dielectric"], [])
        self.assertEqual(len(review["bleed_off"]), 1)
        self.assertFalse(cp.is_programme_compliant(review))

    def test_high_surface_potential_breaks_differential_only(self):
        item = _clean_item()
        item["surface_potential_v"] = -6000.0
        review = cp.programme_review(item)
        self.assertEqual(len(review["differential"]), 1)
        self.assertEqual(review["planning"], [])
        self.assertEqual(review["test_envelope"], [])

    def test_review_does_not_mutate_the_input(self):
        item = _clean_item()
        snapshot = dict(item["analysis_case"])
        cp.programme_review(item)
        self.assertEqual(item["analysis_case"], snapshot)

    def test_unrecognized_regime_raises_through_review(self):
        item = _clean_item()
        item["charging_regime"] = "lunar_dust_charging"
        with self.assertRaises(ValueError):
            cp.programme_review(item)

    def test_review_is_deterministic(self):
        first_item = _clean_item()
        first_item["planned_tasks"] = {}
        second_item = _clean_item()
        second_item["planned_tasks"] = {}
        first = cp.programme_review(first_item)
        second = cp.programme_review(second_item)
        self.assertEqual(first["planning"], second["planning"])

    def test_default_safety_factor_is_applied_when_absent(self):
        item = _clean_item()
        del item["field_safety_factor"]
        item["electron_current_density_a_per_m2"] = 1.0e-10
        item["breakdown_strength_v_per_m"] = 1.0e4
        review = cp.programme_review(item)
        self.assertEqual(len(review["dielectric"]), 1)
        self.assertAlmostEqual(
            review["dielectric"][0]["allowable_v_per_m"],
            1.0e4 / cp.DEFAULT_FIELD_SAFETY_FACTOR,
            places=6,
        )

    def test_math_module_is_the_only_numeric_dependency(self):
        self.assertTrue(hasattr(math, "isclose"))


if __name__ == "__main__":
    unittest.main()
