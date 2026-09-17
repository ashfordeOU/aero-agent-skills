"""Contract tests for the clause 8 retinned part lot acceptance logic."""

import unittest

from q60_retinned_part_acceptance_logic import (
    ATTRIBUTES,
    COSMETIC_ACCEPT_PERCENT,
    FULL_INSPECTION_LOT_SIZE,
    MAX_DIP_COUNT,
    MAX_DIP_DWELL_S,
    MAX_SAMPLE_SIZE,
    MAX_TOTAL_DWELL_S,
    MIN_RESIDUAL_LEAD_PERCENT,
    MIN_SAMPLE_SIZE,
    PROCESS_TOLERANCE,
    SAMPLE_PERCENT,
    VERDICTS,
    accept_number,
    assess_retinned_lot,
    evaluate_attribute_result,
    evaluate_attribute_results,
    normalize_token,
    residual_finish_is_lead_bearing,
    retin_sample_size,
    thermal_exposure_findings,
    total_dwell_seconds,
    validate_attribute,
    validate_process,
)


def _process(**overrides):
    process = {
        "dip_temperature_c": 245.0,
        "dwell_seconds": 3.0,
        "dip_count": 2,
        "part_max_process_temperature_c": 260.0,
        "resulting_lead_mass_percent": 37.0,
    }
    process.update(overrides)
    return process


def _results(**overrides):
    rejects = {token: 0 for token in ATTRIBUTES}
    rejects.update(overrides)
    return [
        {"attribute": token, "rejects": count}
        for token, count in sorted(rejects.items())
    ]


def _lot(**overrides):
    lot = {
        "lot_id": "RT-2291",
        "lot_size": 1000,
        "process": _process(),
        "results": _results(),
        "process_qualified": True,
    }
    lot.update(overrides)
    return lot


class TokenTests(unittest.TestCase):
    def test_token_normalization_is_hyphenated_lower_case(self):
        self.assertEqual(
            normalize_token("Retinned_Lead Solderability"),
            "retinned-lead-solderability",
        )

    def test_every_attribute_validates(self):
        for token in ATTRIBUTES:
            self.assertEqual(validate_attribute(token), token)

    def test_unknown_attribute_rejected(self):
        with self.assertRaises(ValueError):
            validate_attribute("paint-adhesion")

    def test_blank_attribute_rejected(self):
        with self.assertRaises(ValueError):
            validate_attribute("  ")


class SampleSizeTests(unittest.TestCase):
    def test_a_very_small_lot_is_inspected_in_full(self):
        self.assertEqual(retin_sample_size(FULL_INSPECTION_LOT_SIZE), FULL_INSPECTION_LOT_SIZE)

    def test_a_lot_of_one_is_inspected_in_full(self):
        self.assertEqual(retin_sample_size(1), 1)

    def test_just_above_the_full_inspection_lot_takes_the_floor_sample(self):
        self.assertEqual(retin_sample_size(FULL_INSPECTION_LOT_SIZE + 1), MIN_SAMPLE_SIZE)

    def test_the_fraction_applies_once_it_beats_the_floor(self):
        self.assertEqual(retin_sample_size(100), 100 * SAMPLE_PERCENT // 100)

    def test_the_fraction_rounds_up(self):
        self.assertEqual(retin_sample_size(51), 6)

    def test_a_large_lot_is_capped(self):
        self.assertEqual(retin_sample_size(100000), MAX_SAMPLE_SIZE)

    def test_the_sample_never_exceeds_the_lot(self):
        for size in (1, 5, 9, 40, 400, 4000):
            self.assertLessEqual(retin_sample_size(size), size)

    def test_the_sample_never_shrinks_above_the_full_inspection_lot(self):
        previous = retin_sample_size(FULL_INSPECTION_LOT_SIZE + 1)
        for size in range(FULL_INSPECTION_LOT_SIZE + 2, 900):
            sample = retin_sample_size(size)
            self.assertGreaterEqual(sample, previous, "lot size %d" % size)
            previous = sample

    def test_zero_lot_size_rejected(self):
        with self.assertRaises(ValueError):
            retin_sample_size(0)

    def test_non_integer_lot_size_rejected(self):
        with self.assertRaises(ValueError):
            retin_sample_size(40.5)


class AcceptNumberTests(unittest.TestCase):
    def test_a_critical_attribute_accepts_on_zero(self):
        self.assertEqual(accept_number("retinned-lead-solderability", 50), 0)

    def test_a_destructive_attribute_accepts_on_zero(self):
        self.assertEqual(accept_number("retinned-lead-terminal-strength", 50), 0)

    def test_a_cosmetic_attribute_scales_with_the_sample(self):
        self.assertEqual(
            accept_number("retinned-finish-visual-inspection", 50),
            50 * COSMETIC_ACCEPT_PERCENT // 100,
        )

    def test_a_small_sample_leaves_a_cosmetic_attribute_on_zero(self):
        self.assertEqual(accept_number("retinned-finish-visual-inspection", 10), 0)

    def test_zero_sample_rejected(self):
        with self.assertRaises(ValueError):
            accept_number("retinned-finish-visual-inspection", 0)


class AttributeResultTests(unittest.TestCase):
    def test_a_clean_critical_attribute_is_accepted(self):
        item = evaluate_attribute_result("retinned-part-hermeticity", 0, 50)
        self.assertTrue(item["accepted"])

    def test_one_reject_fails_a_critical_attribute(self):
        item = evaluate_attribute_result("retinned-part-hermeticity", 1, 50)
        self.assertFalse(item["accepted"])

    def test_a_cosmetic_attribute_absorbs_up_to_its_accept_number(self):
        item = evaluate_attribute_result("retinned-lead-coplanarity-check", 2, 50)
        self.assertEqual(item["accept_number"], 2)
        self.assertTrue(item["accepted"])

    def test_a_cosmetic_attribute_fails_one_past_its_accept_number(self):
        item = evaluate_attribute_result("retinned-lead-coplanarity-check", 3, 50)
        self.assertFalse(item["accepted"])

    def test_more_rejects_than_the_sample_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_attribute_result("retinned-lead-coplanarity-check", 51, 50)

    def test_negative_rejects_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_attribute_result("retinned-lead-coplanarity-check", -1, 50)

    def test_duplicate_attribute_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_attribute_results(
                [
                    {"attribute": "retinned-part-hermeticity", "rejects": 0},
                    {"attribute": "retinned-part-hermeticity", "rejects": 1},
                ],
                50,
            )

    def test_empty_result_list_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_attribute_results([], 50)

    def test_non_mapping_result_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_attribute_results([["retinned-part-hermeticity", 0]], 50)


class ThermalExposureTests(unittest.TestCase):
    def test_a_process_inside_every_bound_raises_nothing(self):
        self.assertEqual(thermal_exposure_findings(validate_process(_process())), [])

    def test_a_dip_exactly_on_the_part_limit_is_allowed(self):
        process = validate_process(_process(dip_temperature_c=260.0))
        self.assertAlmostEqual(
            process["dip_temperature_c"],
            process["part_max_process_temperature_c"],
            places=9,
        )
        self.assertEqual(thermal_exposure_findings(process), [])

    def test_a_dip_above_the_part_limit_is_a_finding(self):
        process = validate_process(_process(dip_temperature_c=275.0))
        self.assertIn("dip-temperature-above-the-part-limit", thermal_exposure_findings(process))

    def test_a_dwell_exactly_on_the_single_dip_limit_is_allowed(self):
        process = validate_process(_process(dwell_seconds=MAX_DIP_DWELL_S, dip_count=1))
        self.assertAlmostEqual(process["dwell_seconds"], MAX_DIP_DWELL_S, places=9)
        self.assertEqual(thermal_exposure_findings(process), [])

    def test_a_long_dwell_is_a_finding(self):
        process = validate_process(_process(dwell_seconds=7.0, dip_count=1))
        self.assertIn("single-dip-dwell-above-the-limit", thermal_exposure_findings(process))

    def test_too_many_dips_is_a_finding(self):
        process = validate_process(_process(dwell_seconds=1.0, dip_count=MAX_DIP_COUNT + 1))
        self.assertIn("more-dips-than-permitted", thermal_exposure_findings(process))

    def test_total_dwell_exactly_on_the_budget_is_allowed(self):
        process = validate_process(_process(dwell_seconds=4.0, dip_count=2))
        total = total_dwell_seconds(process["dwell_seconds"], process["dip_count"])
        self.assertAlmostEqual(total, MAX_TOTAL_DWELL_S, places=9)
        self.assertEqual(thermal_exposure_findings(process), [])

    def test_total_dwell_over_the_budget_is_a_finding(self):
        process = validate_process(_process(dwell_seconds=4.5, dip_count=2))
        self.assertIn(
            "total-time-at-solder-temperature-above-the-limit",
            thermal_exposure_findings(process),
        )

    def test_findings_come_back_sorted(self):
        process = validate_process(
            _process(dip_temperature_c=300.0, dwell_seconds=9.0, dip_count=3)
        )
        findings = thermal_exposure_findings(process)
        self.assertEqual(findings, sorted(findings))
        self.assertEqual(len(findings), 4)

    def test_zero_dwell_rejected(self):
        with self.assertRaises(ValueError):
            validate_process(_process(dwell_seconds=0.0))

    def test_process_missing_a_key_rejected(self):
        process = _process()
        del process["dip_count"]
        with self.assertRaises(ValueError):
            validate_process(process)

    def test_the_boundary_tolerance_is_far_below_a_degree(self):
        self.assertLess(PROCESS_TOLERANCE, 1e-6)


class ResidualFinishTests(unittest.TestCase):
    def test_a_leaded_finish_passes(self):
        self.assertTrue(residual_finish_is_lead_bearing(37.0))

    def test_a_finish_exactly_on_the_threshold_passes(self):
        self.assertTrue(residual_finish_is_lead_bearing(MIN_RESIDUAL_LEAD_PERCENT))

    def test_a_finish_below_the_threshold_fails(self):
        self.assertFalse(residual_finish_is_lead_bearing(1.0))

    def test_lead_content_above_one_hundred_rejected(self):
        with self.assertRaises(ValueError):
            residual_finish_is_lead_bearing(120.0)


class LotAssessmentTests(unittest.TestCase):
    def test_a_clean_lot_is_accepted(self):
        result = assess_retinned_lot(_lot())
        self.assertEqual(result["verdict"], "lot-accepted")
        self.assertTrue(result["acceptable_as_evaluated"])
        self.assertEqual(result["findings"], [])

    def test_a_large_lot_draws_the_capped_sample(self):
        result = assess_retinned_lot(_lot())
        self.assertEqual(result["sample_size"], MAX_SAMPLE_SIZE)
        self.assertFalse(result["full_inspection"])

    def test_a_tiny_lot_is_marked_full_inspection(self):
        result = assess_retinned_lot(
            _lot(lot_size=6, results=_results())
        )
        self.assertTrue(result["full_inspection"])
        self.assertEqual(result["sample_size"], 6)

    def test_one_critical_reject_rejects_the_lot(self):
        result = assess_retinned_lot(
            _lot(results=_results(**{"retinned-lead-solderability": 1}))
        )
        self.assertEqual(result["verdict"], "lot-rejected")
        self.assertIn("retinned-lead-solderability", result["critical_failures"])

    def test_cosmetic_overshoot_alone_calls_for_screening(self):
        result = assess_retinned_lot(
            _lot(results=_results(**{"retinned-finish-visual-inspection": 3}))
        )
        self.assertEqual(result["verdict"], "screening-required")
        self.assertEqual(
            result["cosmetic_failures"], ["retinned-finish-visual-inspection"]
        )

    def test_a_thermal_finding_rejects_the_lot_even_with_clean_attributes(self):
        result = assess_retinned_lot(_lot(process=_process(dip_temperature_c=300.0)))
        self.assertEqual(result["verdict"], "lot-rejected")
        self.assertIn("dip-temperature-above-the-part-limit", result["thermal_findings"])

    def test_a_pure_tin_finish_after_retinning_rejects_the_lot(self):
        result = assess_retinned_lot(
            _lot(process=_process(resulting_lead_mass_percent=0.5))
        )
        self.assertEqual(result["verdict"], "lot-rejected")
        self.assertFalse(result["residual_finish_is_lead_bearing"])

    def test_an_unqualified_process_rejects_the_lot(self):
        result = assess_retinned_lot(_lot(process_qualified=False))
        self.assertEqual(result["verdict"], "lot-rejected")
        self.assertTrue(
            any("not qualified" in f for f in result["findings"]), result["findings"]
        )

    def test_the_process_qualification_flag_defaults_to_qualified(self):
        lot = _lot()
        del lot["process_qualified"]
        self.assertTrue(assess_retinned_lot(lot)["process_qualified"])

    def test_non_boolean_qualification_flag_rejected(self):
        with self.assertRaises(ValueError):
            assess_retinned_lot(_lot(process_qualified="yes"))

    def test_blank_lot_id_rejected(self):
        with self.assertRaises(ValueError):
            assess_retinned_lot(_lot(lot_id="   "))

    def test_missing_key_rejected(self):
        lot = _lot()
        del lot["process"]
        with self.assertRaises(ValueError):
            assess_retinned_lot(lot)

    def test_non_mapping_lot_rejected(self):
        with self.assertRaises(ValueError):
            assess_retinned_lot(["RT-2291"])

    def test_total_dwell_is_reported_on_the_result(self):
        result = assess_retinned_lot(_lot(process=_process(dwell_seconds=4.0, dip_count=2)))
        self.assertAlmostEqual(result["total_dwell_seconds"], MAX_TOTAL_DWELL_S, places=9)

    def test_verdict_is_always_from_the_fixed_vocabulary(self):
        for rejects in (0, 1, 3):
            result = assess_retinned_lot(
                _lot(results=_results(**{"retinned-finish-visual-inspection": rejects}))
            )
            self.assertIn(result["verdict"], VERDICTS)


if __name__ == "__main__":
    unittest.main()
