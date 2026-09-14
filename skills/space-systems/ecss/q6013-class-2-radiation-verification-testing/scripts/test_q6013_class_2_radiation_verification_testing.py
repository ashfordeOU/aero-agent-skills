"""Contract tests for the clause 5.3.8 intermediate class radiation logic.

The cases walk the verification one gate at a time: the requirement built from
the mission dose, the design margin and the heritage penalty; the similarity
test that decides whether heritage data may be read at all; the low dose rate
refusal; the worst-case reduction across heritage lots; the margin comparison
at its boundary; the single-event threshold; and the four-way disposition.
Boundary equalities are asserted with a tolerance rather than a strict
inequality, because a multiplied margin can land either side of a bound.
"""

import unittest

from q6013_class_2_radiation_verification_testing_logic import (
    CLASS_TWO_DESIGN_MARGIN,
    HERITAGE_PENALTY,
    LOW_DOSE_RATE_LIMIT,
    MAX_DATE_CODE_GAP_WEEKS,
    MIN_LOT_SAMPLE,
    achieved_margin,
    assess_class_2_radiation_verification,
    evaluate_similarity,
    low_dose_rate_concern,
    required_capability,
    single_event_check,
    worst_case_capability,
)


def _similarity(**overrides):
    claim = {
        "same_manufacturer": True,
        "same_wafer_process": True,
        "same_assembly_site": True,
        "date_code_gap_weeks": 26,
    }
    claim.update(overrides)
    return claim


def _lot_spec(**overrides):
    spec = {
        "part_id": "AD590JH-FL-0072",
        "family": "cmos-digital",
        "mission_dose": 20.0,
        "evidence_kind": "lot-specific",
        "lot_capability": 40.0,
        "lot_sample_size": 4,
        "sample_from_flight_lot": True,
    }
    spec.update(overrides)
    return spec


def _heritage_spec(**overrides):
    spec = {
        "part_id": "AD590JH-FL-0072",
        "family": "cmos-digital",
        "mission_dose": 20.0,
        "evidence_kind": "heritage-similarity",
        "heritage_lots": [{"id": "HL-1", "capability": 70.0}],
        "similarity": _similarity(),
        "mission_dose_rate": 1.0,
        "low_dose_rate_data": False,
    }
    spec.update(overrides)
    return spec


class RequirementTests(unittest.TestCase):
    def test_lot_specific_requirement_is_dose_times_margin(self):
        result = required_capability(20.0, 2.0, "lot-specific")
        self.assertAlmostEqual(result["required"], 40.0, places=9)
        self.assertAlmostEqual(result["heritage_penalty"], 1.0, places=9)

    def test_heritage_requirement_carries_the_penalty(self):
        result = required_capability(20.0, 2.0, "heritage-similarity")
        self.assertAlmostEqual(result["required"], 20.0 * 2.0 * HERITAGE_PENALTY, places=9)

    def test_unpenalised_requirement_is_kept_alongside(self):
        result = required_capability(20.0, 2.0, "heritage-similarity")
        self.assertAlmostEqual(result["unpenalised"], 40.0, places=9)

    def test_class_default_margin_is_applied_when_none_is_given(self):
        result = required_capability(10.0)
        self.assertAlmostEqual(result["design_margin"], CLASS_TWO_DESIGN_MARGIN, places=9)

    def test_margin_below_unity_rejected(self):
        with self.assertRaises(ValueError):
            required_capability(20.0, 0.8, "lot-specific")

    def test_margin_of_exactly_unity_accepted(self):
        self.assertAlmostEqual(required_capability(20.0, 1.0)["required"], 20.0, places=9)

    def test_zero_mission_dose_rejected(self):
        with self.assertRaises(ValueError):
            required_capability(0.0, 2.0)

    def test_boolean_mission_dose_rejected(self):
        with self.assertRaises(ValueError):
            required_capability(True, 2.0)

    def test_unknown_evidence_kind_rejected(self):
        with self.assertRaises(ValueError):
            required_capability(20.0, 2.0, "vendor-datasheet")


class SimilarityTests(unittest.TestCase):
    def test_same_manufacturer_and_process_inside_the_window_is_admissible(self):
        self.assertTrue(evaluate_similarity(_similarity())["admissible"])

    def test_different_manufacturer_is_not_admissible(self):
        result = evaluate_similarity(_similarity(same_manufacturer=False))
        self.assertFalse(result["admissible"])
        self.assertEqual(len(result["reasons"]), 1)

    def test_different_wafer_process_is_not_admissible(self):
        self.assertFalse(evaluate_similarity(_similarity(same_wafer_process=False))["admissible"])

    def test_date_code_gap_at_the_window_edge_is_admissible(self):
        claim = _similarity(date_code_gap_weeks=MAX_DATE_CODE_GAP_WEEKS)
        self.assertTrue(evaluate_similarity(claim)["admissible"])

    def test_date_code_gap_beyond_the_window_is_not_admissible(self):
        claim = _similarity(date_code_gap_weeks=MAX_DATE_CODE_GAP_WEEKS + 1)
        self.assertFalse(evaluate_similarity(claim)["admissible"])

    def test_different_assembly_site_is_an_advisory_not_a_refusal(self):
        result = evaluate_similarity(_similarity(same_assembly_site=False))
        self.assertTrue(result["admissible"])
        self.assertEqual(len(result["advisories"]), 1)

    def test_negative_date_code_gap_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_similarity(_similarity(date_code_gap_weeks=-4))

    def test_missing_similarity_key_rejected(self):
        claim = _similarity()
        del claim["same_wafer_process"]
        with self.assertRaises(ValueError):
            evaluate_similarity(claim)


class LowDoseRateTests(unittest.TestCase):
    def test_sensitive_family_at_a_low_rate_is_a_concern(self):
        self.assertTrue(low_dose_rate_concern("bipolar-linear", LOW_DOSE_RATE_LIMIT / 10.0))

    def test_rate_exactly_at_the_limit_is_a_concern(self):
        self.assertTrue(low_dose_rate_concern("optocoupler", LOW_DOSE_RATE_LIMIT))

    def test_sensitive_family_at_a_high_rate_is_not_a_concern(self):
        self.assertFalse(low_dose_rate_concern("bipolar-linear", 1.0))

    def test_insensitive_family_at_a_low_rate_is_not_a_concern(self):
        self.assertFalse(low_dose_rate_concern("cmos-digital", LOW_DOSE_RATE_LIMIT / 10.0))

    def test_zero_dose_rate_rejected(self):
        with self.assertRaises(ValueError):
            low_dose_rate_concern("bipolar-linear", 0.0)


class HeritageReductionTests(unittest.TestCase):
    def test_worst_case_is_taken_not_the_mean(self):
        lots = [
            {"id": "HL-1", "capability": 90.0},
            {"id": "HL-2", "capability": 48.0},
            {"id": "HL-3", "capability": 72.0},
        ]
        result = worst_case_capability(lots)
        self.assertAlmostEqual(result["capability"], 48.0, places=9)
        self.assertEqual(result["governing_lot"], "HL-2")

    def test_single_lot_governs_itself(self):
        self.assertEqual(worst_case_capability([{"id": "HL-1", "capability": 60.0}])["lot_count"], 1)

    def test_empty_heritage_set_rejected(self):
        with self.assertRaises(ValueError):
            worst_case_capability([])

    def test_repeated_heritage_lot_id_rejected(self):
        lots = [{"id": "HL-1", "capability": 60.0}, {"id": "HL-1", "capability": 70.0}]
        with self.assertRaises(ValueError):
            worst_case_capability(lots)

    def test_non_positive_heritage_capability_rejected(self):
        with self.assertRaises(ValueError):
            worst_case_capability([{"id": "HL-1", "capability": 0.0}])

    def test_achieved_margin_is_a_ratio(self):
        self.assertAlmostEqual(achieved_margin(40.0, 20.0), 2.0, places=9)


class SingleEventTests(unittest.TestCase):
    def test_no_requirement_means_nothing_to_compare(self):
        result = single_event_check(None, None)
        self.assertFalse(result["declared"])
        self.assertTrue(result["meets"])

    def test_measurement_above_the_requirement_meets_it(self):
        self.assertTrue(single_event_check(37.0, 60.0)["meets"])

    def test_measurement_exactly_at_the_requirement_meets_it(self):
        self.assertTrue(single_event_check(37.0, 37.0)["meets"])

    def test_measurement_below_the_requirement_fails(self):
        self.assertFalse(single_event_check(37.0, 20.0)["meets"])

    def test_requirement_without_a_measurement_is_missing_evidence(self):
        result = single_event_check(37.0, None)
        self.assertTrue(result["evidence_missing"])
        self.assertFalse(result["meets"])


class DispositionTests(unittest.TestCase):
    def test_lot_specific_capability_at_the_requirement_is_verified(self):
        result = assess_class_2_radiation_verification(_lot_spec())
        self.assertAlmostEqual(result["requirement"]["required"], 40.0, places=9)
        self.assertAlmostEqual(result["achieved_margin"], CLASS_TWO_DESIGN_MARGIN, places=9)
        self.assertEqual(result["disposition"], "verified")

    def test_lot_specific_capability_below_the_requirement_is_rejected(self):
        result = assess_class_2_radiation_verification(_lot_spec(lot_capability=30.0))
        self.assertEqual(result["disposition"], "rejected")
        self.assertEqual(len(result["reject_reasons"]), 1)

    def test_sample_below_the_floor_makes_the_evidence_invalid(self):
        spec = _lot_spec(lot_sample_size=MIN_LOT_SAMPLE - 1)
        self.assertEqual(
            assess_class_2_radiation_verification(spec)["disposition"], "evidence-invalid"
        )

    def test_units_from_another_lot_make_the_evidence_invalid(self):
        spec = _lot_spec(sample_from_flight_lot=False)
        self.assertEqual(
            assess_class_2_radiation_verification(spec)["disposition"], "evidence-invalid"
        )

    def test_invalid_evidence_outranks_a_capability_shortfall(self):
        spec = _lot_spec(lot_capability=10.0, sample_from_flight_lot=False)
        result = assess_class_2_radiation_verification(spec)
        self.assertEqual(result["disposition"], "evidence-invalid")
        self.assertEqual(result["reject_reasons"], [])

    def test_heritage_capability_clearing_the_penalty_is_verified(self):
        result = assess_class_2_radiation_verification(_heritage_spec())
        self.assertAlmostEqual(result["requirement"]["required"], 60.0, places=9)
        self.assertEqual(result["disposition"], "verified")

    def test_heritage_capability_exactly_at_the_penalised_requirement_is_verified(self):
        spec = _heritage_spec(heritage_lots=[{"id": "HL-1", "capability": 60.0}])
        result = assess_class_2_radiation_verification(spec)
        self.assertAlmostEqual(result["capability"], result["requirement"]["required"], places=9)
        self.assertEqual(result["disposition"], "verified")

    def test_heritage_clearing_the_margin_but_not_the_penalty_needs_a_lot_test(self):
        spec = _heritage_spec(heritage_lots=[{"id": "HL-1", "capability": 45.0}])
        result = assess_class_2_radiation_verification(spec)
        self.assertEqual(result["disposition"], "lot-test-required")

    def test_heritage_far_below_the_margin_is_rejected(self):
        spec = _heritage_spec(heritage_lots=[{"id": "HL-1", "capability": 12.0}])
        self.assertEqual(
            assess_class_2_radiation_verification(spec)["disposition"], "rejected"
        )

    def test_inadmissible_similarity_makes_the_evidence_invalid(self):
        spec = _heritage_spec(similarity=_similarity(same_wafer_process=False))
        self.assertEqual(
            assess_class_2_radiation_verification(spec)["disposition"], "evidence-invalid"
        )

    def test_low_dose_rate_family_without_low_rate_data_needs_a_lot_test(self):
        spec = _heritage_spec(
            family="bipolar-linear",
            mission_dose_rate=LOW_DOSE_RATE_LIMIT / 100.0,
            low_dose_rate_data=False,
        )
        result = assess_class_2_radiation_verification(spec)
        self.assertEqual(result["disposition"], "lot-test-required")
        self.assertEqual(len(result["test_reasons"]), 1)

    def test_low_dose_rate_family_with_low_rate_data_is_verified(self):
        spec = _heritage_spec(
            family="bipolar-linear",
            mission_dose_rate=LOW_DOSE_RATE_LIMIT / 100.0,
            low_dose_rate_data=True,
        )
        self.assertEqual(assess_class_2_radiation_verification(spec)["disposition"], "verified")

    def test_worst_heritage_lot_governs_the_verdict(self):
        spec = _heritage_spec(
            heritage_lots=[
                {"id": "HL-1", "capability": 90.0},
                {"id": "HL-2", "capability": 45.0},
            ]
        )
        result = assess_class_2_radiation_verification(spec)
        self.assertEqual(result["governing_lot"], "HL-2")
        self.assertEqual(result["disposition"], "lot-test-required")

    def test_single_event_shortfall_rejects_a_dose_pass(self):
        spec = _lot_spec(required_let=37.0, measured_let=15.0)
        result = assess_class_2_radiation_verification(spec)
        self.assertTrue(result["meets_dose_requirement"])
        self.assertEqual(result["disposition"], "rejected")

    def test_declared_single_event_requirement_without_a_measurement_is_invalid(self):
        spec = _lot_spec(required_let=37.0)
        self.assertEqual(
            assess_class_2_radiation_verification(spec)["disposition"], "evidence-invalid"
        )

    def test_dose_sensitive_family_on_heritage_carries_an_advisory(self):
        result = assess_class_2_radiation_verification(_heritage_spec())
        self.assertTrue(any("dose sensitive" in note for note in result["advisories"]))

    def test_missing_heritage_key_rejected(self):
        spec = _heritage_spec()
        del spec["similarity"]
        with self.assertRaises(ValueError):
            assess_class_2_radiation_verification(spec)

    def test_missing_lot_specific_key_rejected(self):
        spec = _lot_spec()
        del spec["lot_sample_size"]
        with self.assertRaises(ValueError):
            assess_class_2_radiation_verification(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_class_2_radiation_verification(["not", "a", "mapping"])

    def test_blank_part_id_rejected(self):
        with self.assertRaises(ValueError):
            assess_class_2_radiation_verification(_lot_spec(part_id="  "))


if __name__ == "__main__":
    unittest.main()
