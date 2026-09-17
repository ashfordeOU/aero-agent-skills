"""Contract tests for the clause 5.5.1 class 2 receiving control entry point."""

import unittest

from q60_class_2_quality_control_general_logic import (
    AGE_TRIGGER_MONTHS,
    BASELINE_OWED,
    BOUND_TOLERANCE,
    CONTROL_ACTIVITIES,
    CREDITABLE_ACTIVITIES,
    EVIDENCE_VALIDITY_MONTHS,
    baseline_controls,
    coverage_fraction,
    credited_controls,
    entry_disposition,
    lot_admissibility,
    ordered_control_plan,
    outstanding_controls,
    plan_class_2_receiving_controls,
    required_controls,
    sample_size,
    upscreening_required,
)

DESTRUCTIVE = [name for name, destructive in CONTROL_ACTIVITIES if destructive]
NON_DESTRUCTIVE = [name for name, destructive in CONTROL_ACTIVITIES if not destructive]


def _lot(**over):
    base = {
        "lot_code": "LOT-6052-B",
        "quantity": 300,
        "date_code": "2431",
        "conformity_certificate": True,
        "hermetic_package": False,
        "temperature_extremes_duty": False,
        "radiation_duty": False,
        "qualified_source": True,
        "months_since_manufacture": 6.0,
        "procured_flow": "space",
        "required_flow": "space",
        "manufacturer_evidence": [],
        "controls_closed": [],
    }
    base.update(over)
    return base


class AdmissibilityTests(unittest.TestCase):
    def test_a_sound_lot_is_admissible(self):
        self.assertEqual(lot_admissibility(_lot()), [])

    def test_a_lot_without_an_identity_is_stopped(self):
        reasons = lot_admissibility(_lot(lot_code="   "))
        self.assertIn("lot-identity-not-traceable", reasons)

    def test_a_lot_without_a_quantity_is_stopped(self):
        reasons = lot_admissibility(_lot(quantity=0))
        self.assertIn("delivered-quantity-not-stated", reasons)

    def test_a_lot_without_a_date_code_is_stopped(self):
        reasons = lot_admissibility(_lot(date_code=""))
        self.assertIn("date-code-not-stated", reasons)

    def test_a_missing_conformity_certificate_stops_the_lot(self):
        reasons = lot_admissibility(_lot(conformity_certificate=False))
        self.assertIn("conformity-certificate-missing", reasons)

    def test_reasons_accumulate(self):
        reasons = lot_admissibility(
            _lot(lot_code="", quantity=-2, date_code="  ",
                 conformity_certificate=False)
        )
        self.assertEqual(len(reasons), 4)

    def test_lot_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            lot_admissibility(["LOT-6052-B"])


class UpscreeningTests(unittest.TestCase):
    def test_a_matching_flow_owes_no_upscreening(self):
        self.assertFalse(upscreening_required(_lot()))

    def test_a_commercial_part_in_a_space_application_owes_upscreening(self):
        self.assertTrue(
            upscreening_required(_lot(procured_flow="commercial",
                                      required_flow="space"))
        )

    def test_a_flow_above_the_demand_owes_no_upscreening(self):
        self.assertFalse(
            upscreening_required(_lot(procured_flow="space",
                                      required_flow="military"))
        )

    def test_an_unknown_flow_grade_rejected(self):
        with self.assertRaises(ValueError):
            upscreening_required(_lot(procured_flow="industrial"))


class BaselineControlTests(unittest.TestCase):
    def test_the_baseline_activities_are_always_owed(self):
        owed = baseline_controls(_lot())
        self.assertTrue(set(BASELINE_OWED) <= set(owed))

    def test_a_hermetic_package_adds_particle_noise_detection(self):
        owed = baseline_controls(_lot(hermetic_package=True))
        self.assertIn("particle-impact-noise-detection", owed)

    def test_a_non_hermetic_package_does_not(self):
        self.assertNotIn("particle-impact-noise-detection",
                         baseline_controls(_lot()))

    def test_temperature_duty_adds_the_extremes_measurement(self):
        owed = baseline_controls(_lot(temperature_extremes_duty=True))
        self.assertIn("electrical-measurement-at-temperature-extremes", owed)

    def test_radiation_duty_adds_its_lot_verification(self):
        owed = baseline_controls(_lot(radiation_duty=True))
        self.assertIn("radiation-lot-verification", owed)

    def test_an_unqualified_source_adds_solderability_and_destructive_analysis(self):
        owed = baseline_controls(_lot(qualified_source=False))
        self.assertIn("solderability-verification", owed)
        self.assertIn("destructive-physical-analysis", owed)

    def test_an_aged_lot_adds_solderability(self):
        owed = baseline_controls(
            _lot(months_since_manufacture=AGE_TRIGGER_MONTHS + 6.0)
        )
        self.assertIn("solderability-verification", owed)

    def test_a_lot_exactly_on_the_age_trigger_does_not_add_it(self):
        owed = baseline_controls(_lot(months_since_manufacture=AGE_TRIGGER_MONTHS))
        self.assertNotIn("solderability-verification", owed)

    def test_upscreening_pulls_in_its_delta(self):
        owed = baseline_controls(_lot(procured_flow="automotive",
                                      required_flow="space"))
        self.assertIn("electrical-measurement-at-temperature-extremes", owed)
        self.assertIn("destructive-physical-analysis", owed)

    def test_a_non_boolean_flag_rejected(self):
        with self.assertRaises(ValueError):
            baseline_controls(_lot(hermetic_package="yes"))

    def test_a_negative_age_rejected(self):
        with self.assertRaises(ValueError):
            baseline_controls(_lot(months_since_manufacture=-1.0))


class ManufacturerCreditTests(unittest.TestCase):
    def test_current_evidence_from_a_qualified_source_is_credited(self):
        credited = credited_controls(
            _lot(manufacturer_evidence=["external-visual-examination"])
        )
        self.assertEqual(credited, ["external-visual-examination"])

    def test_a_credited_activity_leaves_the_project_plan(self):
        owed = required_controls(
            _lot(manufacturer_evidence=["external-visual-examination"])
        )
        self.assertNotIn("external-visual-examination", owed)

    def test_the_conformity_review_can_never_be_credited(self):
        credited = credited_controls(
            _lot(manufacturer_evidence=["certificate-of-conformity-review"])
        )
        self.assertEqual(credited, [])

    def test_evidence_for_an_activity_the_lot_never_owed_credits_nothing(self):
        credited = credited_controls(
            _lot(manufacturer_evidence=["particle-impact-noise-detection"])
        )
        self.assertEqual(credited, [])

    def test_an_unqualified_source_withdraws_all_credit(self):
        credited = credited_controls(
            _lot(qualified_source=False,
                 manufacturer_evidence=["external-visual-examination"])
        )
        self.assertEqual(credited, [])

    def test_evidence_past_the_validity_window_credits_nothing(self):
        credited = credited_controls(
            _lot(evidence_age_months=EVIDENCE_VALIDITY_MONTHS + 1.0,
                 manufacturer_evidence=["external-visual-examination"])
        )
        self.assertEqual(credited, [])

    def test_evidence_exactly_on_the_validity_window_still_counts(self):
        credited = credited_controls(
            _lot(evidence_age_months=EVIDENCE_VALIDITY_MONTHS,
                 manufacturer_evidence=["external-visual-examination"])
        )
        self.assertEqual(credited, ["external-visual-examination"])

    def test_an_upscreened_lot_gets_no_credit_at_all(self):
        credited = credited_controls(
            _lot(procured_flow="commercial", required_flow="space",
                 manufacturer_evidence=["external-visual-examination"])
        )
        self.assertEqual(credited, [])

    def test_every_creditable_activity_is_a_known_activity(self):
        known = {name for name, _d in CONTROL_ACTIVITIES}
        self.assertTrue(set(CREDITABLE_ACTIVITIES) <= known)

    def test_unknown_evidence_rejected(self):
        with self.assertRaises(ValueError):
            credited_controls(_lot(manufacturer_evidence=["x-ray-tomography"]))

    def test_evidence_must_be_a_sequence(self):
        with self.assertRaises(ValueError):
            credited_controls(_lot(manufacturer_evidence="visual"))


class OrderingTests(unittest.TestCase):
    def test_every_non_destructive_activity_precedes_the_destructive_ones(self):
        plan = ordered_control_plan([name for name, _d in CONTROL_ACTIVITIES])
        first_destructive = min(plan.index(name) for name in DESTRUCTIVE)
        last_non_destructive = max(plan.index(name) for name in NON_DESTRUCTIVE)
        self.assertLess(last_non_destructive, first_destructive)

    def test_the_conformity_review_leads_the_plan(self):
        plan = ordered_control_plan(["destructive-physical-analysis",
                                     "certificate-of-conformity-review"])
        self.assertEqual(plan[0], "certificate-of-conformity-review")

    def test_activity_names_compare_case_insensitively(self):
        self.assertEqual(ordered_control_plan(["EXTERNAL-VISUAL-EXAMINATION"]),
                         ["external-visual-examination"])

    def test_unknown_activity_rejected(self):
        with self.assertRaises(ValueError):
            ordered_control_plan(["tea-break"])

    def test_a_repeated_activity_rejected(self):
        with self.assertRaises(ValueError):
            ordered_control_plan(["external-visual-examination",
                                  "external-visual-examination"])


class SampleSizeTests(unittest.TestCase):
    def test_a_full_lot_activity_draws_the_whole_lot(self):
        self.assertEqual(sample_size("external-visual-examination", 300), 300)

    def test_the_destructive_analysis_sample_grows_with_the_lot(self):
        self.assertLess(sample_size("destructive-physical-analysis", 20),
                        sample_size("destructive-physical-analysis", 5000))

    def test_a_band_boundary_stays_in_the_lower_band(self):
        self.assertEqual(sample_size("destructive-physical-analysis", 100), 2)

    def test_one_part_past_a_boundary_moves_up_a_band(self):
        self.assertEqual(sample_size("destructive-physical-analysis", 101), 3)

    def test_a_sample_never_exceeds_the_lot(self):
        self.assertEqual(sample_size("solderability-verification", 2), 2)

    def test_the_radiation_sample_has_its_own_plan(self):
        self.assertEqual(sample_size("radiation-lot-verification", 150), 4)

    def test_a_non_integer_quantity_rejected(self):
        with self.assertRaises(ValueError):
            sample_size("destructive-physical-analysis", 300.0)

    def test_a_zero_quantity_rejected(self):
        with self.assertRaises(ValueError):
            sample_size("destructive-physical-analysis", 0)


class CoverageTests(unittest.TestCase):
    def test_nothing_closed_leaves_everything_outstanding(self):
        owed = required_controls(_lot())
        self.assertEqual(outstanding_controls(owed, []), owed)

    def test_closing_an_activity_removes_it(self):
        owed = required_controls(_lot())
        remaining = outstanding_controls(owed, ["external-visual-examination"])
        self.assertNotIn("external-visual-examination", remaining)

    def test_closing_an_activity_not_owed_changes_nothing(self):
        owed = required_controls(_lot())
        self.assertEqual(outstanding_controls(owed, ["radiation-lot-verification"]),
                         owed)

    def test_an_empty_plan_reads_zero_coverage(self):
        owed = required_controls(_lot())
        self.assertAlmostEqual(coverage_fraction(owed, []), 0.0, places=9)

    def test_a_fully_closed_plan_reads_one(self):
        owed = required_controls(_lot())
        self.assertAlmostEqual(coverage_fraction(owed, owed), 1.0, places=9)

    def test_one_of_three_reads_a_third(self):
        owed = required_controls(_lot())
        self.assertEqual(len(owed), 3)
        self.assertAlmostEqual(coverage_fraction(owed, owed[:1]),
                               1.0 / 3.0, places=9)

    def test_an_empty_owed_set_rejected(self):
        with self.assertRaises(ValueError):
            coverage_fraction([], [])

    def test_tolerance_is_the_documented_size(self):
        self.assertAlmostEqual(BOUND_TOLERANCE, 1e-9, places=12)


class DispositionTests(unittest.TestCase):
    def test_an_inadmissible_lot_overrides_the_plan_state(self):
        self.assertEqual(entry_disposition(["conformity-certificate-missing"], []),
                         "lot-not-admissible")

    def test_outstanding_work_reads_as_outstanding(self):
        self.assertEqual(entry_disposition([], ["destructive-physical-analysis"]),
                         "controls-outstanding")

    def test_a_closed_plan_reads_as_complete(self):
        self.assertEqual(entry_disposition([], []), "controls-complete")

    def test_reasons_must_be_a_sequence(self):
        with self.assertRaises(ValueError):
            entry_disposition("conformity-certificate-missing", [])


class PlanTests(unittest.TestCase):
    def test_a_fresh_lot_opens_with_outstanding_controls(self):
        result = plan_class_2_receiving_controls(_lot())
        self.assertEqual(result["disposition"], "controls-outstanding")
        self.assertTrue(result["admissible"])

    def test_a_fully_worked_lot_is_ready_for_release(self):
        owed = required_controls(_lot())
        result = plan_class_2_receiving_controls(_lot(controls_closed=owed))
        self.assertTrue(result["ready_for_release"])
        self.assertEqual(result["outstanding_controls"], [])

    def test_an_inadmissible_lot_draws_no_samples(self):
        result = plan_class_2_receiving_controls(_lot(conformity_certificate=False))
        self.assertEqual(result["disposition"], "lot-not-admissible")
        self.assertEqual(result["sample_sizes"], {})

    def test_the_sample_sizes_cover_every_owed_activity(self):
        result = plan_class_2_receiving_controls(_lot(hermetic_package=True))
        self.assertEqual(sorted(result["sample_sizes"]),
                         sorted(result["control_plan"]))

    def test_the_credited_activities_are_reported_separately(self):
        result = plan_class_2_receiving_controls(
            _lot(manufacturer_evidence=["external-visual-examination"])
        )
        self.assertIn("external-visual-examination",
                      result["credited_to_manufacturer"])
        self.assertIn("external-visual-examination", result["baseline_plan"])
        self.assertNotIn("external-visual-examination", result["control_plan"])

    def test_the_upscreening_flag_is_reported(self):
        result = plan_class_2_receiving_controls(
            _lot(procured_flow="commercial", required_flow="space")
        )
        self.assertTrue(result["upscreening_owed"])
        self.assertIn("destructive-physical-analysis",
                      result["destructive_activities"])

    def test_coverage_is_reported(self):
        owed = required_controls(_lot())
        result = plan_class_2_receiving_controls(_lot(controls_closed=owed[:2]))
        self.assertAlmostEqual(result["coverage_fraction"],
                               2.0 / len(owed), places=9)

    def test_lot_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            plan_class_2_receiving_controls([_lot()])


if __name__ == "__main__":
    unittest.main(verbosity=1)
