#!/usr/bin/env python3
"""Gate 3 contract test for e20-electromagnetic-effects-verification-report.

Stdlib unittest, offline, deterministic. Run:
    python3 test_e20_electromagnetic_effects_verification_report.py
"""

import unittest

import e20_electromagnetic_effects_verification_report_logic as logic


def emission_activity(**over):
    rec = {
        "method": "radiated-emission-electric-field",
        "applicable_limit": 40.0,
        "measured_level": 34.0,
        "unit": "dBuV/m",
        "required_margin": 6.0,
        "requirement": "EMC-0101",
    }
    rec.update(over)
    return rec


def susceptibility_activity(**over):
    rec = {
        "method": "radiated-susceptibility-electric-field",
        "applicable_limit": 20.0,
        "measured_level": 26.0,
        "unit": "V/m",
        "required_margin": 6.0,
        "requirement": "EMC-0201",
    }
    rec.update(over)
    return rec


def good_report(**over):
    rep = {
        "sections": [
            "identification",
            "verification-matrix",
            "results",
            "deviation-register",
            "conclusion",
        ],
        "activities": [emission_activity(), susceptibility_activity()],
        "deviations": [],
        "mandated_methods": [
            "radiated-emission-electric-field",
            "radiated-susceptibility-electric-field",
        ],
        "default_required_margin": 6.0,
    }
    rep.update(over)
    return rep


class TestMethodCategorization(unittest.TestCase):
    def test_emission_method_maps_to_emission_family(self):
        self.assertEqual(
            logic.categorize_verification_activity("radiated-emission-electric-field"),
            "emission",
        )

    def test_susceptibility_method_maps_to_susceptibility_family(self):
        self.assertEqual(
            logic.categorize_verification_activity(
                "conducted-susceptibility-bulk-current-injection"
            ),
            "susceptibility",
        )

    def test_electrostatic_and_magnetic_families_are_distinct(self):
        self.assertEqual(
            logic.categorize_verification_activity("electrostatic-discharge-immunity"),
            "electrostatic",
        )
        self.assertEqual(
            logic.categorize_verification_activity("magnetic-moment-characterisation"),
            "magnetic",
        )

    def test_bonding_and_isolation_map_to_grounding(self):
        self.assertEqual(
            logic.categorize_verification_activity("bonding-resistance-measurement"),
            "grounding",
        )
        self.assertEqual(
            logic.categorize_verification_activity("isolation-resistance-measurement"),
            "grounding",
        )

    def test_free_form_label_is_normalized_before_lookup(self):
        self.assertEqual(
            logic.categorize_verification_activity("Radiated Emission  Electric_Field"),
            "emission",
        )

    def test_uncategorized_method_raises(self):
        with self.assertRaises(ValueError):
            logic.categorize_verification_activity("thermal-vacuum-soak")

    def test_empty_method_raises(self):
        with self.assertRaises(ValueError):
            logic.categorize_verification_activity("   ")

    def test_non_string_method_raises(self):
        with self.assertRaises(ValueError):
            logic.categorize_verification_activity(17)


class TestMarginSense(unittest.TestCase):
    def test_emission_is_lower_is_better(self):
        self.assertEqual(logic.margin_sense("emission"), "lower-is-better")

    def test_susceptibility_is_higher_is_better(self):
        self.assertEqual(logic.margin_sense("susceptibility"), "higher-is-better")

    def test_unknown_family_raises(self):
        with self.assertRaises(ValueError):
            logic.margin_sense("acoustic")


class TestMarginRecomputation(unittest.TestCase):
    def test_emission_margin_is_limit_minus_measured(self):
        self.assertAlmostEqual(
            logic.compute_demonstrated_margin(40.0, 34.0, "emission"), 6.0
        )

    def test_susceptibility_margin_is_measured_minus_required(self):
        self.assertAlmostEqual(
            logic.compute_demonstrated_margin(20.0, 26.0, "susceptibility"), 6.0
        )

    def test_sense_inversion_changes_the_sign(self):
        as_emission = logic.compute_demonstrated_margin(20.0, 26.0, "emission")
        as_susceptibility = logic.compute_demonstrated_margin(20.0, 26.0, "susceptibility")
        self.assertAlmostEqual(as_emission, -as_susceptibility)
        self.assertLess(as_emission, 0.0)

    def test_grounding_margin_uses_resistance_units(self):
        self.assertAlmostEqual(
            logic.compute_demonstrated_margin(10.0, 2.5, "grounding"), 7.5
        )

    def test_non_finite_limit_raises(self):
        with self.assertRaises(ValueError):
            logic.compute_demonstrated_margin(float("inf"), 3.0, "emission")

    def test_non_numeric_measured_level_raises(self):
        with self.assertRaises(ValueError):
            logic.compute_demonstrated_margin(40.0, "34", "emission")

    def test_boolean_is_not_accepted_as_a_level(self):
        with self.assertRaises(ValueError):
            logic.compute_demonstrated_margin(40.0, True, "emission")


class TestGrading(unittest.TestCase):
    def test_margin_above_requirement_is_compliant(self):
        self.assertEqual(logic.grade_margin(8.0, 6.0), logic.GRADE_COMPLIANT)

    def test_margin_exactly_on_requirement_is_compliant(self):
        self.assertEqual(logic.grade_margin(6.0, 6.0), logic.GRADE_COMPLIANT)

    def test_representation_error_on_the_boundary_stays_compliant(self):
        # 0.1 + 0.2 lands a few ULPs above 0.3; the physical case is on the
        # boundary and must not be downgraded by the representation.
        margin = (40.3 - 40.0) - 0.0
        self.assertEqual(logic.grade_margin(margin, 0.3), logic.GRADE_COMPLIANT)

    def test_sum_of_decibel_terms_on_the_boundary_stays_compliant(self):
        margin = 0.1 + 0.2
        self.assertEqual(logic.grade_margin(margin, 0.3), logic.GRADE_COMPLIANT)

    def test_positive_but_short_margin_is_marginal(self):
        self.assertEqual(logic.grade_margin(2.0, 6.0), logic.GRADE_MARGINAL)

    def test_zero_margin_is_marginal_not_compliant(self):
        self.assertEqual(logic.grade_margin(0.0, 6.0), logic.GRADE_MARGINAL)

    def test_negative_margin_is_non_compliant(self):
        self.assertEqual(logic.grade_margin(-0.5, 6.0), logic.GRADE_NON_COMPLIANT)

    def test_zero_requirement_makes_zero_margin_compliant(self):
        self.assertEqual(logic.grade_margin(0.0, 0.0), logic.GRADE_COMPLIANT)

    def test_negative_requirement_raises(self):
        with self.assertRaises(ValueError):
            logic.grade_margin(3.0, -1.0)

    def test_non_numeric_margin_raises(self):
        with self.assertRaises(ValueError):
            logic.grade_margin("3 dB", 1.0)


class TestActivityEvaluation(unittest.TestCase):
    def test_compliant_emission_activity(self):
        out = logic.evaluate_activity(emission_activity())
        self.assertEqual(out["family"], "emission")
        self.assertEqual(out["grade"], logic.GRADE_COMPLIANT)
        self.assertAlmostEqual(out["demonstrated_margin"], 6.0)

    def test_failed_susceptibility_activity_is_non_compliant(self):
        out = logic.evaluate_activity(susceptibility_activity(measured_level=18.0))
        self.assertEqual(out["grade"], logic.GRADE_NON_COMPLIANT)
        self.assertAlmostEqual(out["demonstrated_margin"], -2.0)

    def test_activity_without_required_margin_uses_the_report_default(self):
        rec = emission_activity()
        del rec["required_margin"]
        out = logic.evaluate_activity(rec, default_required_margin=10.0)
        self.assertAlmostEqual(out["required_margin"], 10.0)
        self.assertEqual(out["grade"], logic.GRADE_MARGINAL)

    def test_missing_measured_level_raises(self):
        rec = emission_activity()
        del rec["measured_level"]
        with self.assertRaises(ValueError):
            logic.evaluate_activity(rec)

    def test_missing_unit_raises(self):
        rec = emission_activity()
        del rec["unit"]
        with self.assertRaises(ValueError):
            logic.evaluate_activity(rec)

    def test_blank_unit_raises(self):
        with self.assertRaises(ValueError):
            logic.evaluate_activity(emission_activity(unit="  "))

    def test_non_mapping_activity_raises(self):
        with self.assertRaises(ValueError):
            logic.evaluate_activity(["radiated-emission-electric-field", 40.0])


class TestCoverage(unittest.TestCase):
    def test_full_coverage_returns_no_gap(self):
        gaps = logic.check_activity_coverage(
            [emission_activity(), susceptibility_activity()],
            ["radiated-emission-electric-field", "radiated-susceptibility-electric-field"],
        )
        self.assertEqual(gaps, [])

    def test_absent_mandated_method_is_a_gap(self):
        gaps = logic.check_activity_coverage(
            [emission_activity()],
            ["radiated-emission-electric-field", "magnetic-moment-characterisation"],
        )
        self.assertEqual(gaps, ["magnetic-moment-characterisation"])

    def test_gap_list_is_deduplicated_and_sorted(self):
        gaps = logic.check_activity_coverage(
            [emission_activity()],
            [
                "magnetic-moment-characterisation",
                "bonding-resistance-measurement",
                "magnetic-moment-characterisation",
            ],
        )
        self.assertEqual(
            gaps, ["bonding-resistance-measurement", "magnetic-moment-characterisation"]
        )

    def test_uncategorized_mandated_method_raises(self):
        with self.assertRaises(ValueError):
            logic.check_activity_coverage([emission_activity()], ["sine-vibration-run"])

    def test_activity_without_method_key_raises(self):
        with self.assertRaises(ValueError):
            logic.check_activity_coverage([{"unit": "dB"}], [])

    def test_non_list_activities_raises(self):
        with self.assertRaises(ValueError):
            logic.check_activity_coverage("radiated-emission-electric-field", [])


class TestDeviationRegister(unittest.TestCase):
    def test_corrective_action_entry_is_accepted(self):
        out = logic.validate_deviation(
            {
                "activity": "radiated-emission-electric-field",
                "description": "narrowband spur at 120 MHz",
                "disposition": "corrective-action",
            }
        )
        self.assertFalse(out["closes_campaign"])
        self.assertIsNone(out["waiver_reference"])

    def test_waiver_entry_needs_a_reference(self):
        with self.assertRaises(ValueError):
            logic.validate_deviation(
                {
                    "activity": "radiated-emission-electric-field",
                    "description": "narrowband spur at 120 MHz",
                    "disposition": "waiver",
                }
            )

    def test_waiver_entry_with_reference_closes_the_campaign(self):
        out = logic.validate_deviation(
            {
                "activity": "radiated-emission-electric-field",
                "description": "narrowband spur at 120 MHz",
                "disposition": "waiver",
                "waiver_reference": "RFW-2210",
            }
        )
        self.assertTrue(out["closes_campaign"])
        self.assertEqual(out["waiver_reference"], "RFW-2210")

    def test_blank_waiver_reference_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.validate_deviation(
                {
                    "activity": "radiated-emission-electric-field",
                    "description": "spur",
                    "disposition": "waiver",
                    "waiver_reference": "   ",
                }
            )

    def test_unrecognized_disposition_raises(self):
        with self.assertRaises(ValueError):
            logic.validate_deviation(
                {
                    "activity": "radiated-emission-electric-field",
                    "description": "spur",
                    "disposition": "noted",
                }
            )

    def test_empty_description_raises(self):
        with self.assertRaises(ValueError):
            logic.validate_deviation(
                {
                    "activity": "radiated-emission-electric-field",
                    "description": "",
                    "disposition": "retest",
                }
            )

    def test_deviation_naming_an_absent_activity_raises(self):
        with self.assertRaises(ValueError):
            logic.validate_deviation(
                {
                    "activity": "magnetic-moment-characterisation",
                    "description": "residual moment high",
                    "disposition": "retest",
                },
                known_methods={"radiated-emission-electric-field"},
            )

    def test_register_validates_every_entry(self):
        entries = logic.register_deviations(
            [
                {
                    "activity": "radiated-emission-electric-field",
                    "description": "spur",
                    "disposition": "retest",
                },
                {
                    "activity": "radiated-susceptibility-electric-field",
                    "description": "reset at 1.2 GHz",
                    "disposition": "waiver",
                    "waiver_reference": "RFW-9",
                },
            ]
        )
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[1]["waiver_reference"], "RFW-9")

    def test_non_list_register_raises(self):
        with self.assertRaises(ValueError):
            logic.register_deviations({"activity": "x"})


class TestSections(unittest.TestCase):
    def test_complete_section_list_has_no_gap(self):
        self.assertEqual(logic.check_sections(list(logic.REQUIRED_SECTIONS)), [])

    def test_missing_deviation_register_is_reported(self):
        missing = logic.check_sections(
            ["identification", "verification-matrix", "results", "conclusion"]
        )
        self.assertEqual(missing, ["deviation-register"])

    def test_section_names_are_normalized(self):
        self.assertEqual(
            logic.check_sections(
                [
                    "Identification",
                    "Verification Matrix",
                    "Results",
                    "Deviation_Register",
                    "Conclusion",
                ]
            ),
            [],
        )

    def test_blank_section_name_raises(self):
        with self.assertRaises(ValueError):
            logic.check_sections(["identification", ""])


class TestSummary(unittest.TestCase):
    def test_summary_counts_each_band(self):
        evals = [
            logic.evaluate_activity(emission_activity()),
            logic.evaluate_activity(susceptibility_activity(measured_level=22.0)),
            logic.evaluate_activity(susceptibility_activity(measured_level=18.0)),
        ]
        summary = logic.summarize_margins(evals)
        self.assertEqual(summary["counts"][logic.GRADE_COMPLIANT], 1)
        self.assertEqual(summary["counts"][logic.GRADE_MARGINAL], 1)
        self.assertEqual(summary["counts"][logic.GRADE_NON_COMPLIANT], 1)
        self.assertEqual(summary["activity_count"], 3)

    def test_worst_entry_is_the_largest_shortfall(self):
        evals = [
            logic.evaluate_activity(emission_activity()),
            logic.evaluate_activity(susceptibility_activity(measured_level=18.0)),
        ]
        summary = logic.summarize_margins(evals)
        self.assertEqual(summary["worst"]["method"], "radiated-susceptibility-electric-field")
        self.assertAlmostEqual(summary["worst"]["shortfall"], -8.0)

    def test_empty_evaluation_list_raises(self):
        with self.assertRaises(ValueError):
            logic.summarize_margins([])


class TestReportAssessment(unittest.TestCase):
    def test_complete_report_is_acceptable(self):
        out = logic.assess_report(good_report())
        self.assertTrue(out["acceptable"])
        self.assertEqual(out["findings"], [])

    def test_missing_section_blocks_acceptance(self):
        rep = good_report(
            sections=["identification", "verification-matrix", "results", "conclusion"]
        )
        out = logic.assess_report(rep)
        self.assertFalse(out["acceptable"])
        self.assertEqual(out["missing_sections"], ["deviation-register"])

    def test_coverage_gap_blocks_acceptance(self):
        rep = good_report(
            mandated_methods=[
                "radiated-emission-electric-field",
                "radiated-susceptibility-electric-field",
                "bonding-resistance-measurement",
            ]
        )
        out = logic.assess_report(rep)
        self.assertFalse(out["acceptable"])
        self.assertEqual(out["coverage_gaps"], ["bonding-resistance-measurement"])

    def test_non_compliant_activity_blocks_acceptance(self):
        rep = good_report(
            activities=[emission_activity(), susceptibility_activity(measured_level=12.0)]
        )
        out = logic.assess_report(rep)
        self.assertFalse(out["acceptable"])
        self.assertTrue(
            any(f.startswith("non-compliant-activities") for f in out["findings"])
        )

    def test_marginal_activity_must_be_carried_in_the_register(self):
        rep = good_report(
            activities=[emission_activity(), susceptibility_activity(measured_level=23.0)]
        )
        out = logic.assess_report(rep)
        self.assertFalse(out["acceptable"])
        self.assertTrue(
            any(f.startswith("marginal-not-in-register") for f in out["findings"])
        )

    def test_marginal_activity_carried_in_the_register_is_acceptable(self):
        rep = good_report(
            activities=[emission_activity(), susceptibility_activity(measured_level=23.0)],
            deviations=[
                {
                    "activity": "radiated-susceptibility-electric-field",
                    "description": "margin short by 3 dB",
                    "disposition": "waiver",
                    "waiver_reference": "RFW-31",
                }
            ],
        )
        out = logic.assess_report(rep)
        self.assertTrue(out["acceptable"])

    def test_report_with_no_activity_raises(self):
        with self.assertRaises(ValueError):
            logic.assess_report(good_report(activities=[]))

    def test_report_missing_sections_key_raises(self):
        rep = good_report()
        del rep["sections"]
        with self.assertRaises(ValueError):
            logic.assess_report(rep)

    def test_non_mapping_report_raises(self):
        with self.assertRaises(ValueError):
            logic.assess_report(["identification"])


if __name__ == "__main__":
    unittest.main()
