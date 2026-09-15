"""Contract tests for the clause 4.5.1 receiving control entry-point logic."""

import unittest

from q60_class_1_quality_control_general_logic import (
    AGE_TRIGGER_MONTHS,
    ALWAYS_OWED,
    BOUND_TOLERANCE,
    CONTROL_ACTIVITIES,
    coverage_fraction,
    entry_disposition,
    lot_admissibility,
    ordered_control_plan,
    outstanding_controls,
    plan_class_1_receiving_controls,
    required_controls,
    sample_size,
)

DESTRUCTIVE = [name for name, destructive in CONTROL_ACTIVITIES if destructive]
NON_DESTRUCTIVE = [name for name, destructive in CONTROL_ACTIVITIES if not destructive]


def _lot(**over):
    base = {
        "lot_code": "LOT-6021-C",
        "quantity": 400,
        "data_package_accepted": True,
        "hermetic_package": False,
        "qualified_source": True,
        "radiation_duty": False,
        "months_since_manufacture": 6.0,
        "controls_closed": [],
    }
    base.update(over)
    return base


class AdmissibilityTests(unittest.TestCase):
    def test_a_sound_lot_is_admissible(self):
        self.assertEqual(lot_admissibility(_lot()), [])

    def test_a_lot_without_an_identity_is_stopped(self):
        self.assertIn("lot-identity-not-traceable", lot_admissibility(_lot(lot_code="  ")))

    def test_a_lot_without_a_quantity_is_stopped(self):
        self.assertIn("delivered-quantity-not-stated", lot_admissibility(_lot(quantity=0)))

    def test_a_rejected_data_package_stops_the_lot(self):
        reasons = lot_admissibility(_lot(data_package_accepted=False))
        self.assertIn("data-package-not-accepted", reasons)

    def test_reasons_accumulate(self):
        reasons = lot_admissibility(_lot(lot_code="", quantity=-3,
                                         data_package_accepted=False))
        self.assertEqual(len(reasons), 3)

    def test_lot_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            lot_admissibility(["LOT-6021-C"])


class RequiredControlTests(unittest.TestCase):
    def test_the_baseline_activities_are_always_owed(self):
        owed = required_controls(_lot())
        self.assertTrue(set(ALWAYS_OWED) <= set(owed))

    def test_a_hermetic_package_adds_particle_noise_detection(self):
        owed = required_controls(_lot(hermetic_package=True))
        self.assertIn("particle-impact-noise-detection", owed)

    def test_a_non_hermetic_package_does_not(self):
        self.assertNotIn("particle-impact-noise-detection", required_controls(_lot()))

    def test_an_unqualified_source_adds_solderability(self):
        owed = required_controls(_lot(qualified_source=False))
        self.assertIn("solderability-verification", owed)

    def test_radiation_duty_adds_its_lot_verification(self):
        owed = required_controls(_lot(radiation_duty=True))
        self.assertIn("radiation-lot-verification", owed)

    def test_an_aged_lot_adds_solderability(self):
        owed = required_controls(_lot(months_since_manufacture=AGE_TRIGGER_MONTHS + 6.0))
        self.assertIn("solderability-verification", owed)

    def test_a_lot_exactly_on_the_age_trigger_does_not_add_it(self):
        owed = required_controls(_lot(months_since_manufacture=AGE_TRIGGER_MONTHS))
        self.assertNotIn("solderability-verification", owed)

    def test_a_non_boolean_flag_rejected(self):
        with self.assertRaises(ValueError):
            required_controls(_lot(hermetic_package="yes"))

    def test_a_negative_age_rejected(self):
        with self.assertRaises(ValueError):
            required_controls(_lot(months_since_manufacture=-1.0))


class OrderingTests(unittest.TestCase):
    def test_every_non_destructive_activity_precedes_the_destructive_ones(self):
        plan = ordered_control_plan([name for name, _d in CONTROL_ACTIVITIES])
        first_destructive = min(plan.index(name) for name in DESTRUCTIVE)
        last_non_destructive = max(plan.index(name) for name in NON_DESTRUCTIVE)
        self.assertLess(last_non_destructive, first_destructive)

    def test_the_data_package_review_leads_the_plan(self):
        plan = ordered_control_plan(["destructive-physical-analysis",
                                     "data-package-review"])
        self.assertEqual(plan[0], "data-package-review")

    def test_activity_names_compare_case_insensitively(self):
        plan = ordered_control_plan(["DATA-PACKAGE-REVIEW"])
        self.assertEqual(plan, ["data-package-review"])

    def test_unknown_activity_rejected(self):
        with self.assertRaises(ValueError):
            ordered_control_plan(["x-ray-tomography"])

    def test_a_repeated_activity_rejected(self):
        with self.assertRaises(ValueError):
            ordered_control_plan(["data-package-review", "data-package-review"])

    def test_activities_must_be_a_sequence(self):
        with self.assertRaises(ValueError):
            ordered_control_plan("data-package-review")


class SampleSizeTests(unittest.TestCase):
    def test_a_full_lot_activity_draws_the_whole_lot(self):
        self.assertEqual(sample_size("external-visual-examination", 400), 400)

    def test_the_destructive_analysis_sample_grows_with_the_lot(self):
        small = sample_size("destructive-physical-analysis", 8)
        large = sample_size("destructive-physical-analysis", 5000)
        self.assertLess(small, large)

    def test_a_band_boundary_stays_in_the_lower_band(self):
        self.assertEqual(sample_size("destructive-physical-analysis", 200), 5)

    def test_one_part_past_a_boundary_moves_up_a_band(self):
        self.assertEqual(sample_size("destructive-physical-analysis", 201), 8)

    def test_a_sample_never_exceeds_the_lot(self):
        self.assertEqual(sample_size("destructive-physical-analysis", 1), 1)

    def test_the_radiation_sample_has_its_own_plan(self):
        self.assertEqual(sample_size("radiation-lot-verification", 60), 5)

    def test_a_non_integer_quantity_rejected(self):
        with self.assertRaises(ValueError):
            sample_size("destructive-physical-analysis", 400.0)

    def test_a_zero_quantity_rejected(self):
        with self.assertRaises(ValueError):
            sample_size("destructive-physical-analysis", 0)

    def test_unknown_activity_rejected(self):
        with self.assertRaises(ValueError):
            sample_size("tea-break", 400)


class CoverageTests(unittest.TestCase):
    def test_nothing_closed_leaves_everything_outstanding(self):
        owed = required_controls(_lot())
        self.assertEqual(outstanding_controls(owed, []), owed)

    def test_closing_an_activity_removes_it(self):
        owed = required_controls(_lot())
        remaining = outstanding_controls(owed, ["data-package-review"])
        self.assertNotIn("data-package-review", remaining)

    def test_closing_an_activity_not_owed_changes_nothing(self):
        owed = required_controls(_lot())
        remaining = outstanding_controls(owed, ["radiation-lot-verification"])
        self.assertEqual(remaining, owed)

    def test_an_empty_plan_reads_zero_coverage(self):
        owed = required_controls(_lot())
        self.assertAlmostEqual(coverage_fraction(owed, []), 0.0, places=9)

    def test_a_fully_closed_plan_reads_one(self):
        owed = required_controls(_lot())
        self.assertAlmostEqual(coverage_fraction(owed, owed), 1.0, places=9)

    def test_half_a_plan_reads_a_half(self):
        owed = required_controls(_lot())
        half = owed[: len(owed) // 2]
        self.assertAlmostEqual(coverage_fraction(owed, half), 0.5, places=9)

    def test_an_empty_owed_set_rejected(self):
        with self.assertRaises(ValueError):
            coverage_fraction([], [])

    def test_tolerance_is_the_documented_size(self):
        self.assertAlmostEqual(BOUND_TOLERANCE, 1e-9, places=12)


class DispositionTests(unittest.TestCase):
    def test_an_inadmissible_lot_overrides_the_plan_state(self):
        self.assertEqual(entry_disposition(["data-package-not-accepted"], []),
                         "lot-not-admissible")

    def test_outstanding_work_reads_as_outstanding(self):
        self.assertEqual(entry_disposition([], ["destructive-physical-analysis"]),
                         "controls-outstanding")

    def test_a_closed_plan_reads_as_complete(self):
        self.assertEqual(entry_disposition([], []), "controls-complete")

    def test_reasons_must_be_a_sequence(self):
        with self.assertRaises(ValueError):
            entry_disposition("data-package-not-accepted", [])


class PlanTests(unittest.TestCase):
    def test_a_fresh_lot_opens_with_outstanding_controls(self):
        result = plan_class_1_receiving_controls(_lot())
        self.assertEqual(result["disposition"], "controls-outstanding")
        self.assertTrue(result["admissible"])

    def test_a_fully_worked_lot_is_ready_for_release(self):
        owed = required_controls(_lot())
        result = plan_class_1_receiving_controls(_lot(controls_closed=owed))
        self.assertTrue(result["ready_for_release"])
        self.assertEqual(result["outstanding_controls"], [])

    def test_an_inadmissible_lot_draws_no_samples(self):
        result = plan_class_1_receiving_controls(_lot(data_package_accepted=False))
        self.assertEqual(result["disposition"], "lot-not-admissible")
        self.assertEqual(result["sample_sizes"], {})

    def test_the_sample_sizes_cover_every_owed_activity(self):
        result = plan_class_1_receiving_controls(_lot(hermetic_package=True))
        self.assertEqual(sorted(result["sample_sizes"]), sorted(result["control_plan"]))

    def test_the_destructive_activities_are_named(self):
        result = plan_class_1_receiving_controls(_lot(radiation_duty=True))
        self.assertIn("radiation-lot-verification", result["destructive_activities"])
        self.assertNotIn("data-package-review", result["destructive_activities"])

    def test_coverage_is_reported(self):
        owed = required_controls(_lot())
        result = plan_class_1_receiving_controls(_lot(controls_closed=owed[:2]))
        self.assertAlmostEqual(result["coverage_fraction"], 2.0 / len(owed), places=9)

    def test_lot_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            plan_class_1_receiving_controls([_lot()])


if __name__ == "__main__":
    unittest.main(verbosity=1)
