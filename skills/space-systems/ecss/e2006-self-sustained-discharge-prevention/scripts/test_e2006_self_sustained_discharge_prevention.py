#!/usr/bin/env python3
"""Contract test for the clause 8.2 self-sustained-discharge prevention leaf."""

import unittest

from e2006_self_sustained_discharge_prevention_logic import (
    BARRIER_FACTORS,
    REGIME_PERMANENT,
    REGIME_QUENCHED,
    REGIME_TEMPORARY,
    TRANSIENT_ENERGY_LIMIT_J,
    apply_mitigations,
    assess_equipment,
    categorize_conductor_pair,
    evaluate_arc_regime,
    summarize_assessment,
    sustaining_current_threshold,
    sustaining_voltage_threshold,
    transient_arc_energy_j,
    verify_demonstration_evidence,
)


def quiet_pair(**over):
    base = {
        "pair_id": "P1",
        "gap_mm": 1.0,
        "potential_v": 30.0,
        "available_current_a": 0.2,
        "barrier": "bare-gap",
    }
    base.update(over)
    return base


def latching_pair(**over):
    base = {
        "pair_id": "P9",
        "gap_mm": 0.5,
        "potential_v": 120.0,
        "available_current_a": 4.0,
        "barrier": "bare-gap",
    }
    base.update(over)
    return base


class TestCategorizeConductorPair(unittest.TestCase):
    def test_bare_gap_is_an_unprotected_pair(self):
        rec = categorize_conductor_pair(quiet_pair())
        self.assertEqual(rec["category"], "unprotected-pair")

    def test_encapsulant_is_a_barrier_protected_pair(self):
        rec = categorize_conductor_pair(quiet_pair(barrier="silicone-encapsulant"))
        self.assertEqual(rec["category"], "barrier-protected-pair")

    def test_numeric_fields_are_normalized_to_float(self):
        rec = categorize_conductor_pair(quiet_pair(gap_mm=2, potential_v=50))
        self.assertIsInstance(rec["gap_mm"], float)
        self.assertAlmostEqual(rec["gap_mm"], 2.0)
        self.assertAlmostEqual(rec["potential_v"], 50.0)

    def test_zero_potential_and_zero_current_are_accepted(self):
        rec = categorize_conductor_pair(quiet_pair(potential_v=0.0, available_current_a=0.0))
        self.assertAlmostEqual(rec["potential_v"], 0.0)
        self.assertAlmostEqual(rec["available_current_a"], 0.0)

    def test_non_mapping_pair_is_rejected(self):
        with self.assertRaises(ValueError):
            categorize_conductor_pair(["P1", 1.0])

    def test_missing_pair_id_is_rejected(self):
        bad = quiet_pair()
        del bad["pair_id"]
        with self.assertRaises(ValueError):
            categorize_conductor_pair(bad)

    def test_blank_pair_id_is_rejected(self):
        with self.assertRaises(ValueError):
            categorize_conductor_pair(quiet_pair(pair_id="   "))

    def test_uncategorized_barrier_is_rejected(self):
        with self.assertRaises(ValueError):
            categorize_conductor_pair(quiet_pair(barrier="kapton-ish"))

    def test_zero_gap_is_rejected(self):
        with self.assertRaises(ValueError):
            categorize_conductor_pair(quiet_pair(gap_mm=0.0))

    def test_negative_gap_is_rejected(self):
        with self.assertRaises(ValueError):
            categorize_conductor_pair(quiet_pair(gap_mm=-1.0))

    def test_negative_potential_is_rejected(self):
        with self.assertRaises(ValueError):
            categorize_conductor_pair(quiet_pair(potential_v=-5.0))

    def test_negative_available_current_is_rejected(self):
        with self.assertRaises(ValueError):
            categorize_conductor_pair(quiet_pair(available_current_a=-0.1))

    def test_boolean_gap_is_rejected_as_non_numeric(self):
        with self.assertRaises(ValueError):
            categorize_conductor_pair(quiet_pair(gap_mm=True))

    def test_string_current_is_rejected(self):
        with self.assertRaises(ValueError):
            categorize_conductor_pair(quiet_pair(available_current_a="4 A"))

    def test_non_finite_potential_is_rejected(self):
        with self.assertRaises(ValueError):
            categorize_conductor_pair(quiet_pair(potential_v=float("inf")))


class TestSustainingThresholds(unittest.TestCase):
    def test_bare_gap_voltage_threshold_matches_the_model(self):
        self.assertAlmostEqual(sustaining_voltage_threshold(1.0, "bare-gap"), 80.0)

    def test_voltage_threshold_grows_with_gap(self):
        narrow = sustaining_voltage_threshold(0.5, "bare-gap")
        wide = sustaining_voltage_threshold(2.0, "bare-gap")
        self.assertGreater(wide, narrow)

    def test_barrier_raises_the_voltage_threshold(self):
        bare = sustaining_voltage_threshold(1.0, "bare-gap")
        potted = sustaining_voltage_threshold(1.0, "silicone-encapsulant")
        self.assertAlmostEqual(potted, bare * BARRIER_FACTORS["silicone-encapsulant"])

    def test_bare_gap_current_threshold_matches_the_model(self):
        self.assertAlmostEqual(sustaining_current_threshold(1.0, "bare-gap"), 0.60)

    def test_current_threshold_grows_with_gap(self):
        self.assertGreater(
            sustaining_current_threshold(3.0, "bare-gap"),
            sustaining_current_threshold(1.0, "bare-gap"),
        )

    def test_every_known_barrier_resolves_to_a_finite_threshold(self):
        for barrier in BARRIER_FACTORS:
            self.assertGreater(sustaining_voltage_threshold(1.0, barrier), 0.0)
            self.assertGreater(sustaining_current_threshold(1.0, barrier), 0.0)

    def test_voltage_threshold_rejects_unknown_barrier(self):
        with self.assertRaises(ValueError):
            sustaining_voltage_threshold(1.0, "mystery-potting")

    def test_current_threshold_rejects_unknown_barrier(self):
        with self.assertRaises(ValueError):
            sustaining_current_threshold(1.0, "mystery-potting")

    def test_voltage_threshold_rejects_zero_gap(self):
        with self.assertRaises(ValueError):
            sustaining_voltage_threshold(0.0, "bare-gap")

    def test_current_threshold_rejects_negative_gap(self):
        with self.assertRaises(ValueError):
            sustaining_current_threshold(-2.0, "bare-gap")


class TestApplyMitigations(unittest.TestCase):
    def test_no_mitigation_leaves_the_drive_untouched(self):
        volts, amps, credited = apply_mitigations(latching_pair())
        self.assertAlmostEqual(volts, 120.0)
        self.assertAlmostEqual(amps, 4.0)
        self.assertEqual(credited, [])

    def test_current_limiting_caps_the_available_current(self):
        volts, amps, credited = apply_mitigations(
            latching_pair(), [{"type": "current-limiting", "limit_a": 0.4}]
        )
        self.assertAlmostEqual(amps, 0.4)
        self.assertAlmostEqual(volts, 120.0)
        self.assertEqual(credited, ["current-limiting"])

    def test_current_limiting_above_the_source_capability_changes_nothing(self):
        _, amps, _ = apply_mitigations(
            latching_pair(), [{"type": "current-limiting", "limit_a": 9.0}]
        )
        self.assertAlmostEqual(amps, 4.0)

    def test_string_segmentation_divides_the_gap_potential(self):
        volts, _, _ = apply_mitigations(
            latching_pair(), [{"type": "string-segmentation", "segments": 4}]
        )
        self.assertAlmostEqual(volts, 30.0)

    def test_blocking_diode_removes_the_bypassed_current_share(self):
        _, amps, _ = apply_mitigations(
            latching_pair(), [{"type": "series-blocking-diode", "bypass_fraction": 0.75}]
        )
        self.assertAlmostEqual(amps, 1.0)

    def test_mitigations_compose_in_order(self):
        volts, amps, credited = apply_mitigations(
            latching_pair(),
            [
                {"type": "string-segmentation", "segments": 2},
                {"type": "current-limiting", "limit_a": 0.5},
            ],
        )
        self.assertAlmostEqual(volts, 60.0)
        self.assertAlmostEqual(amps, 0.5)
        self.assertEqual(credited, ["string-segmentation", "current-limiting"])

    def test_mitigations_must_be_a_list(self):
        with self.assertRaises(ValueError):
            apply_mitigations(latching_pair(), {"type": "current-limiting", "limit_a": 1.0})

    def test_uncategorized_mitigation_is_rejected(self):
        with self.assertRaises(ValueError):
            apply_mitigations(latching_pair(), [{"type": "hope"}])

    def test_current_limiting_needs_a_positive_rating(self):
        with self.assertRaises(ValueError):
            apply_mitigations(latching_pair(), [{"type": "current-limiting", "limit_a": 0.0}])

    def test_single_segment_is_not_a_segmentation(self):
        with self.assertRaises(ValueError):
            apply_mitigations(
                latching_pair(), [{"type": "string-segmentation", "segments": 1}]
            )

    def test_non_integer_segment_count_is_rejected(self):
        with self.assertRaises(ValueError):
            apply_mitigations(
                latching_pair(), [{"type": "string-segmentation", "segments": 2.5}]
            )

    def test_full_bypass_fraction_is_rejected(self):
        with self.assertRaises(ValueError):
            apply_mitigations(
                latching_pair(), [{"type": "series-blocking-diode", "bypass_fraction": 1.0}]
            )

    def test_negative_bypass_fraction_is_rejected(self):
        with self.assertRaises(ValueError):
            apply_mitigations(
                latching_pair(), [{"type": "series-blocking-diode", "bypass_fraction": -0.2}]
            )

    def test_non_mapping_mitigation_entry_is_rejected(self):
        with self.assertRaises(ValueError):
            apply_mitigations(latching_pair(), ["current-limiting"])


class TestEvaluateArcRegime(unittest.TestCase):
    def test_low_drive_quenches(self):
        out = evaluate_arc_regime(quiet_pair())
        self.assertEqual(out["regime"], REGIME_QUENCHED)

    def test_high_potential_with_starved_current_is_temporary(self):
        out = evaluate_arc_regime(latching_pair(available_current_a=0.3))
        self.assertEqual(out["regime"], REGIME_TEMPORARY)

    def test_high_potential_and_ample_current_latches(self):
        out = evaluate_arc_regime(latching_pair())
        self.assertEqual(out["regime"], REGIME_PERMANENT)

    def test_current_alone_cannot_sustain_without_the_voltage(self):
        out = evaluate_arc_regime(quiet_pair(available_current_a=25.0))
        self.assertEqual(out["regime"], REGIME_QUENCHED)

    def test_potential_exactly_at_the_threshold_still_quenches(self):
        threshold = sustaining_voltage_threshold(1.0, "bare-gap")
        out = evaluate_arc_regime(quiet_pair(potential_v=threshold))
        self.assertEqual(out["regime"], REGIME_QUENCHED)
        self.assertAlmostEqual(out["voltage_margin_v"], 0.0)

    def test_segmentation_landing_exactly_on_the_threshold_quenches(self):
        # 0.1 * 3 is not exactly 0.3 in binary floating point; a pair that is
        # mathematically at the sustaining voltage must not read as an
        # exceedance because of that representation error.
        threshold = sustaining_voltage_threshold(1.0, "bare-gap")
        out = evaluate_arc_regime(
            quiet_pair(potential_v=threshold * 3.0),
            [{"type": "string-segmentation", "segments": 3}],
        )
        self.assertEqual(out["regime"], REGIME_QUENCHED)

    def test_current_exactly_at_the_threshold_stays_temporary(self):
        threshold = sustaining_current_threshold(0.5, "bare-gap")
        out = evaluate_arc_regime(latching_pair(available_current_a=threshold))
        self.assertEqual(out["regime"], REGIME_TEMPORARY)
        self.assertAlmostEqual(out["current_margin_a"], 0.0)

    def test_limiting_the_current_downgrades_a_latching_pair(self):
        out = evaluate_arc_regime(
            latching_pair(), [{"type": "current-limiting", "limit_a": 0.2}]
        )
        self.assertEqual(out["regime"], REGIME_TEMPORARY)

    def test_segmentation_can_quench_a_latching_pair(self):
        out = evaluate_arc_regime(
            latching_pair(), [{"type": "string-segmentation", "segments": 8}]
        )
        self.assertEqual(out["regime"], REGIME_QUENCHED)

    def test_encapsulation_reports_the_raised_thresholds(self):
        bare = evaluate_arc_regime(latching_pair())
        potted = evaluate_arc_regime(latching_pair(barrier="ceramic-standoff"))
        self.assertGreater(potted["voltage_threshold_v"], bare["voltage_threshold_v"])
        self.assertEqual(potted["category"], "barrier-protected-pair")

    def test_regime_record_carries_the_credited_mitigations(self):
        out = evaluate_arc_regime(
            latching_pair(), [{"type": "current-limiting", "limit_a": 0.2}]
        )
        self.assertEqual(out["credited_mitigations"], ["current-limiting"])

    def test_bad_pair_propagates_the_value_error(self):
        with self.assertRaises(ValueError):
            evaluate_arc_regime(quiet_pair(gap_mm=0.0))


class TestTransientArcEnergy(unittest.TestCase):
    def test_energy_is_the_product_of_drive_and_duration(self):
        self.assertAlmostEqual(transient_arc_energy_j(100.0, 0.5, 0.002), 0.1)

    def test_zero_duration_deposits_nothing(self):
        self.assertAlmostEqual(transient_arc_energy_j(100.0, 0.5, 0.0), 0.0)

    def test_negative_duration_is_rejected(self):
        with self.assertRaises(ValueError):
            transient_arc_energy_j(100.0, 0.5, -0.001)

    def test_negative_current_is_rejected(self):
        with self.assertRaises(ValueError):
            transient_arc_energy_j(100.0, -0.5, 0.001)

    def test_non_numeric_voltage_is_rejected(self):
        with self.assertRaises(ValueError):
            transient_arc_energy_j("100", 0.5, 0.001)


class TestDemonstrationEvidence(unittest.TestCase):
    def test_missing_evidence_is_a_finding(self):
        findings = verify_demonstration_evidence(None, REGIME_QUENCHED)
        self.assertEqual(len(findings), 1)

    def test_test_based_evidence_closes_a_quenched_pair(self):
        findings = verify_demonstration_evidence(
            {"method": "secondary-arc-test", "reference": "TR-114"}, REGIME_QUENCHED
        )
        self.assertEqual(findings, [])

    def test_analysis_alone_closes_a_quenched_pair(self):
        findings = verify_demonstration_evidence(
            {"method": "arc-propagation-analysis", "reference": "AR-7"}, REGIME_QUENCHED
        )
        self.assertEqual(findings, [])

    def test_analysis_alone_does_not_close_a_temporary_arc(self):
        findings = verify_demonstration_evidence(
            {"method": "arc-propagation-analysis", "reference": "AR-7"}, REGIME_TEMPORARY
        )
        self.assertEqual(len(findings), 1)

    def test_similarity_closes_a_temporary_arc(self):
        findings = verify_demonstration_evidence(
            {"method": "similarity-to-qualified-design", "reference": "QR-2"},
            REGIME_TEMPORARY,
        )
        self.assertEqual(findings, [])

    def test_evidence_without_a_reference_is_a_finding(self):
        findings = verify_demonstration_evidence(
            {"method": "secondary-arc-test", "reference": ""}, REGIME_QUENCHED
        )
        self.assertEqual(len(findings), 1)

    def test_uncategorized_evidence_method_is_rejected(self):
        with self.assertRaises(ValueError):
            verify_demonstration_evidence({"method": "vendor-says-so"}, REGIME_QUENCHED)

    def test_uncategorized_regime_is_rejected(self):
        with self.assertRaises(ValueError):
            verify_demonstration_evidence(None, "sparkly")

    def test_non_mapping_evidence_is_rejected(self):
        with self.assertRaises(ValueError):
            verify_demonstration_evidence("TR-114", REGIME_QUENCHED)


class TestAssessEquipment(unittest.TestCase):
    def good_item(self, **over):
        item = {
            "equipment_id": "PCDU-A",
            "pairs": [quiet_pair()],
            "transient_duration_s": 0.001,
            "evidence": {"method": "secondary-arc-test", "reference": "TR-114"},
        }
        item.update(over)
        return item

    def test_a_quenched_item_with_evidence_is_compliant(self):
        out = assess_equipment(self.good_item())
        self.assertTrue(out["compliant"])
        self.assertEqual(out["worst_regime"], REGIME_QUENCHED)
        self.assertEqual(out["findings"], [])

    def test_a_latching_pair_fails_the_clause(self):
        out = assess_equipment(self.good_item(pairs=[quiet_pair(), latching_pair()]))
        self.assertFalse(out["compliant"])
        self.assertEqual(out["worst_regime"], REGIME_PERMANENT)

    def test_worst_regime_is_the_escalating_pair(self):
        out = assess_equipment(
            self.good_item(pairs=[quiet_pair(), latching_pair(available_current_a=0.3)])
        )
        self.assertEqual(out["worst_regime"], REGIME_TEMPORARY)

    def test_a_temporary_arc_within_the_energy_limit_is_compliant(self):
        out = assess_equipment(
            self.good_item(
                pairs=[latching_pair(available_current_a=0.3)],
                transient_duration_s=1e-6,
            )
        )
        self.assertTrue(out["compliant"])

    def test_a_temporary_arc_over_the_energy_limit_is_a_finding(self):
        out = assess_equipment(
            self.good_item(
                pairs=[latching_pair(available_current_a=0.3)],
                transient_duration_s=1.0,
            )
        )
        self.assertFalse(out["compliant"])
        self.assertTrue(any("above the" in f for f in out["findings"]))

    def test_energy_exactly_at_the_limit_is_compliant(self):
        # 120 V x 0.3 A x duration is built to land exactly on the limit.
        duration = TRANSIENT_ENERGY_LIMIT_J / (120.0 * 0.3)
        out = assess_equipment(
            self.good_item(
                pairs=[latching_pair(available_current_a=0.3)],
                transient_duration_s=duration,
            )
        )
        self.assertTrue(out["compliant"])
        self.assertAlmostEqual(
            out["pair_results"][0]["transient_energy_j"], TRANSIENT_ENERGY_LIMIT_J
        )

    def test_missing_evidence_makes_the_item_non_compliant(self):
        out = assess_equipment(self.good_item(evidence=None))
        self.assertFalse(out["compliant"])

    def test_equipment_needs_at_least_one_pair(self):
        with self.assertRaises(ValueError):
            assess_equipment(self.good_item(pairs=[]))

    def test_equipment_needs_an_identifier(self):
        with self.assertRaises(ValueError):
            assess_equipment(self.good_item(equipment_id=""))

    def test_non_mapping_equipment_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_equipment(["PCDU-A"])

    def test_negative_transient_duration_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_equipment(self.good_item(transient_duration_s=-1.0))


class TestSummarizeAssessment(unittest.TestCase):
    def clean(self):
        return {
            "equipment_id": "PCDU-A",
            "pairs": [quiet_pair()],
            "transient_duration_s": 0.001,
            "evidence": {"method": "secondary-arc-test", "reference": "TR-114"},
        }

    def dirty(self):
        return {
            "equipment_id": "SADM-B",
            "pairs": [latching_pair()],
            "transient_duration_s": 0.001,
            "evidence": {"method": "secondary-arc-test", "reference": "TR-115"},
        }

    def test_all_clean_meets_the_clause(self):
        out = summarize_assessment([self.clean()])
        self.assertTrue(out["clause_8_2_met"])
        self.assertEqual(out["assessed"], 1)
        self.assertEqual(out["non_compliant"], [])

    def test_one_latching_item_fails_the_roll_up(self):
        out = summarize_assessment([self.clean(), self.dirty()])
        self.assertFalse(out["clause_8_2_met"])
        self.assertEqual(out["non_compliant"], ["SADM-B"])
        self.assertEqual(out["latching_equipment"], ["SADM-B"])

    def test_roll_up_keeps_every_assessment(self):
        out = summarize_assessment([self.clean(), self.dirty()])
        self.assertEqual(len(out["assessments"]), 2)

    def test_empty_roll_up_is_rejected(self):
        with self.assertRaises(ValueError):
            summarize_assessment([])

    def test_non_list_roll_up_is_rejected(self):
        with self.assertRaises(ValueError):
            summarize_assessment(self.clean())


if __name__ == "__main__":
    unittest.main()
