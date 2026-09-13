#!/usr/bin/env python3
"""Gate 3 contract test for e2001-multicarrier-analysis-margins.

Stdlib unittest, offline, deterministic. Run:
    python3 test_e2001_multicarrier_analysis_margins.py
"""

import math
import unittest

from e2001_multicarrier_analysis_margins_logic import (
    CONTRIBUTIONS,
    EQUIPMENT_TYPES,
    HERITAGE_LEVELS,
    MAX_SINGLE_CONTRIBUTION_DB,
    accumulate_contributions,
    assess_analysis_case,
    assess_unit,
    normalize_contribution,
    peak_envelope_power_w,
    peak_to_average_ratio_db,
    resolve_nominal_margin,
    to_dbw,
)


def contributions(geometry=1.5, sey=2.0, solver=1.5, phasing=1.0, extra=None):
    """Build a declared contribution list covering every mandatory category."""
    out = [
        {"category": "geometry-tolerance", "value_db": geometry},
        {"category": "secondary-emission-yield-uncertainty", "value_db": sey},
        {"category": "field-solver-uncertainty", "value_db": solver},
        {"category": "carrier-phasing-uncertainty", "value_db": phasing},
    ]
    if extra:
        out.extend(extra)
    return out


def case(case_id="omux-iris", equipment="waveguide-passive-component",
         heritage="flight-proven-recurring", carriers=(50.0, 50.0), contribs=None):
    return {
        "case_id": case_id,
        "equipment_type": equipment,
        "heritage": heritage,
        "carrier_powers_w": list(carriers),
        "contributions": contribs if contribs is not None else contributions(),
    }


class TestPeakEnvelopePower(unittest.TestCase):
    def test_two_equal_carriers_give_four_times_single_carrier_power(self):
        self.assertAlmostEqual(peak_envelope_power_w([50.0, 50.0]), 200.0)

    def test_n_equal_carriers_scale_with_n_squared(self):
        for n in (2, 3, 4, 8):
            with self.subTest(n=n):
                self.assertAlmostEqual(
                    peak_envelope_power_w([25.0] * n), 25.0 * n * n
                )

    def test_unequal_carriers_add_as_voltages(self):
        expected = (math.sqrt(40.0) + math.sqrt(10.0)) ** 2
        self.assertAlmostEqual(peak_envelope_power_w([40.0, 10.0]), expected)

    def test_single_carrier_is_refused_as_not_multicarrier(self):
        with self.assertRaises(ValueError):
            peak_envelope_power_w([100.0])

    def test_empty_carrier_set_is_refused(self):
        with self.assertRaises(ValueError):
            peak_envelope_power_w([])

    def test_non_sequence_carrier_set_is_refused(self):
        with self.assertRaises(ValueError):
            peak_envelope_power_w("50,50")

    def test_zero_carrier_power_is_refused(self):
        with self.assertRaises(ValueError):
            peak_envelope_power_w([50.0, 0.0])

    def test_negative_carrier_power_is_refused(self):
        with self.assertRaises(ValueError):
            peak_envelope_power_w([50.0, -1.0])

    def test_non_numeric_carrier_power_is_refused(self):
        with self.assertRaises(ValueError):
            peak_envelope_power_w([50.0, "50"])

    def test_boolean_carrier_power_is_refused(self):
        with self.assertRaises(ValueError):
            peak_envelope_power_w([50.0, True])

    def test_infinite_carrier_power_is_refused(self):
        with self.assertRaises(ValueError):
            peak_envelope_power_w([50.0, float("inf")])


class TestDecibelHelpers(unittest.TestCase):
    def test_one_watt_is_zero_decibel_watt(self):
        self.assertAlmostEqual(to_dbw(1.0), 0.0)

    def test_hundred_watt_is_twenty_decibel_watt(self):
        self.assertAlmostEqual(to_dbw(100.0), 20.0)

    def test_zero_watt_has_no_decibel_value(self):
        with self.assertRaises(ValueError):
            to_dbw(0.0)

    def test_peak_to_average_ratio_of_equal_carriers_is_ten_log_n(self):
        for n in (2, 4, 10):
            with self.subTest(n=n):
                self.assertAlmostEqual(
                    peak_to_average_ratio_db([12.5] * n), 10.0 * math.log10(n)
                )


class TestNominalMarginResolution(unittest.TestCase):
    def test_recurring_high_power_chain_owes_its_base_margin(self):
        resolved = resolve_nominal_margin(
            "high-power-transmit-chain", "flight-proven-recurring"
        )
        self.assertAlmostEqual(resolved["required_margin_db"], 8.0)
        self.assertAlmostEqual(resolved["heritage_increment_db"], 0.0)

    def test_new_design_owes_more_than_a_recurring_design(self):
        recurring = resolve_nominal_margin(
            "waveguide-passive-component", "flight-proven-recurring"
        )
        modified = resolve_nominal_margin(
            "waveguide-passive-component", "modified-design"
        )
        new = resolve_nominal_margin("waveguide-passive-component", "new-design")
        self.assertLess(recurring["required_margin_db"], modified["required_margin_db"])
        self.assertLess(modified["required_margin_db"], new["required_margin_db"])

    def test_every_equipment_type_resolves_for_every_heritage_level(self):
        for equipment in EQUIPMENT_TYPES:
            for heritage in HERITAGE_LEVELS:
                with self.subTest(equipment=equipment, heritage=heritage):
                    resolved = resolve_nominal_margin(equipment, heritage)
                    self.assertGreater(resolved["required_margin_db"], 0.0)

    def test_equipment_type_is_matched_case_and_whitespace_insensitively(self):
        resolved = resolve_nominal_margin(
            "  Waveguide-Passive-Component ", "New-Design"
        )
        self.assertEqual(resolved["equipment_type"], "waveguide-passive-component")
        self.assertEqual(resolved["heritage"], "new-design")

    def test_uncategorized_equipment_type_is_refused(self):
        with self.assertRaises(ValueError):
            resolve_nominal_margin("mystery-box", "new-design")

    def test_uncategorized_heritage_level_is_refused(self):
        with self.assertRaises(ValueError):
            resolve_nominal_margin("output-multiplexer", "somewhat-proven")

    def test_non_string_equipment_type_is_refused(self):
        with self.assertRaises(ValueError):
            resolve_nominal_margin(7, "new-design")


class TestContributionNormalization(unittest.TestCase):
    def test_recognized_contribution_is_normalized(self):
        item = normalize_contribution(
            {"category": "  Geometry-Tolerance ", "value_db": 1.25}
        )
        self.assertEqual(item["category"], "geometry-tolerance")
        self.assertAlmostEqual(item["value_db"], 1.25)

    def test_uncategorized_contribution_is_refused(self):
        with self.assertRaises(ValueError):
            normalize_contribution({"category": "vibes", "value_db": 1.0})

    def test_contribution_without_a_value_is_refused(self):
        with self.assertRaises(ValueError):
            normalize_contribution({"category": "thermal-drift"})

    def test_negative_contribution_is_refused(self):
        with self.assertRaises(ValueError):
            normalize_contribution({"category": "thermal-drift", "value_db": -0.5})

    def test_contribution_above_the_single_entry_ceiling_is_refused(self):
        with self.assertRaises(ValueError):
            normalize_contribution(
                {
                    "category": "thermal-drift",
                    "value_db": MAX_SINGLE_CONTRIBUTION_DB + 0.5,
                }
            )

    def test_contribution_exactly_at_the_ceiling_is_accepted(self):
        item = normalize_contribution(
            {"category": "thermal-drift", "value_db": MAX_SINGLE_CONTRIBUTION_DB}
        )
        self.assertAlmostEqual(item["value_db"], MAX_SINGLE_CONTRIBUTION_DB)

    def test_non_mapping_contribution_is_refused(self):
        with self.assertRaises(ValueError):
            normalize_contribution(["thermal-drift", 1.0])

    def test_boolean_contribution_value_is_refused(self):
        with self.assertRaises(ValueError):
            normalize_contribution({"category": "thermal-drift", "value_db": True})


class TestContributionAccumulation(unittest.TestCase):
    def test_declared_contributions_sum_to_the_applied_margin(self):
        result = accumulate_contributions(contributions())
        self.assertAlmostEqual(result["total_db"], 6.0)
        self.assertEqual(result["findings"], [])

    def test_optional_contribution_adds_to_the_total(self):
        result = accumulate_contributions(
            contributions(extra=[{"category": "thermal-drift", "value_db": 0.75}])
        )
        self.assertAlmostEqual(result["total_db"], 6.75)

    def test_duplicate_contribution_category_is_refused(self):
        entries = contributions()
        entries.append({"category": "geometry-tolerance", "value_db": 0.5})
        with self.assertRaises(ValueError):
            accumulate_contributions(entries)

    def test_empty_contribution_list_is_refused(self):
        with self.assertRaises(ValueError):
            accumulate_contributions([])

    def test_non_sequence_contribution_list_is_refused(self):
        with self.assertRaises(ValueError):
            accumulate_contributions("geometry-tolerance")

    def test_missing_mandatory_contribution_is_a_finding(self):
        entries = [
            e for e in contributions() if e["category"] != "field-solver-uncertainty"
        ]
        result = accumulate_contributions(entries)
        self.assertEqual(len(result["findings"]), 1)
        self.assertIn("field-solver-uncertainty", result["findings"][0])

    def test_contribution_below_its_credibility_floor_is_a_finding(self):
        result = accumulate_contributions(contributions(sey=0.25))
        self.assertEqual(len(result["findings"]), 1)
        self.assertIn("credibility floor", result["findings"][0])

    def test_contribution_exactly_at_its_floor_is_not_a_finding(self):
        floor = CONTRIBUTIONS["secondary-emission-yield-uncertainty"]["floor_db"]
        result = accumulate_contributions(contributions(sey=floor))
        self.assertEqual(result["findings"], [])


class TestAnalysisCaseAssessment(unittest.TestCase):
    def test_covered_margin_gives_a_compliant_case(self):
        result = assess_analysis_case(case())
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["deficit_db"], 0.0)
        self.assertEqual(result["findings"], [])

    def test_margin_landing_exactly_on_the_requirement_stays_compliant(self):
        # 0.7 + 1.4 + 2.1 + 1.8 is 6.0 in exact arithmetic but can land a few
        # ULPs low in binary floating point; the requirement must not move.
        result = assess_analysis_case(case(contribs=contributions(0.7, 1.4, 2.1, 1.8)))
        self.assertAlmostEqual(result["applied_margin_db"], 6.0, places=9)
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["deficit_db"], 0.0)

    def test_shortfall_is_reported_with_its_size(self):
        result = assess_analysis_case(case(contribs=contributions(0.5, 1.0, 0.5, 0.5)))
        self.assertFalse(result["compliant"])
        self.assertAlmostEqual(result["deficit_db"], 3.5)
        self.assertTrue(any("shortfall" in f for f in result["findings"]))

    def test_new_design_can_fail_where_a_recurring_design_passes(self):
        recurring = assess_analysis_case(case())
        new = assess_analysis_case(case(heritage="new-design"))
        self.assertTrue(recurring["compliant"])
        self.assertFalse(new["compliant"])
        self.assertAlmostEqual(new["deficit_db"], 2.0)

    def test_analysis_power_level_is_the_peak_envelope_raised_by_the_requirement(self):
        result = assess_analysis_case(case())
        self.assertAlmostEqual(
            result["analysis_power_level_dbw"],
            result["peak_envelope_power_dbw"] + result["required_margin_db"],
        )

    def test_peak_envelope_of_two_equal_carriers_is_reported_in_watt_and_decibel(self):
        result = assess_analysis_case(case(carriers=(50.0, 50.0)))
        self.assertAlmostEqual(result["peak_envelope_power_w"], 200.0)
        self.assertAlmostEqual(result["peak_envelope_power_dbw"], 10.0 * math.log10(200.0))
        self.assertEqual(result["carrier_count"], 2)

    def test_case_without_an_identifier_is_refused(self):
        bad = case()
        bad["case_id"] = "   "
        with self.assertRaises(ValueError):
            assess_analysis_case(bad)

    def test_non_mapping_case_is_refused(self):
        with self.assertRaises(ValueError):
            assess_analysis_case(["omux-iris"])

    def test_case_with_a_single_carrier_is_refused(self):
        with self.assertRaises(ValueError):
            assess_analysis_case(case(carriers=(120.0,)))

    def test_findings_alone_make_a_case_non_compliant(self):
        entries = [
            e for e in contributions(2.0, 2.0, 2.0, 2.0)
            if e["category"] != "carrier-phasing-uncertainty"
        ]
        result = assess_analysis_case(case(contribs=entries))
        self.assertGreaterEqual(result["applied_margin_db"], result["required_margin_db"])
        self.assertFalse(result["compliant"])


class TestUnitAggregation(unittest.TestCase):
    def test_unit_with_every_case_covered_is_compliant(self):
        result = assess_unit([case("iris-a"), case("iris-b", carriers=(30.0, 30.0, 30.0))])
        self.assertTrue(result["compliant"])
        self.assertEqual(result["case_count"], 2)
        self.assertEqual(result["non_compliant_cases"], [])
        self.assertAlmostEqual(result["worst_deficit_db"], 0.0)

    def test_unit_reports_the_worst_shortfall_across_cases(self):
        result = assess_unit(
            [
                case("iris-a"),
                case("iris-b", heritage="new-design"),
                case("iris-c", equipment="high-power-transmit-chain"),
            ]
        )
        self.assertFalse(result["compliant"])
        self.assertEqual(result["non_compliant_cases"], ["iris-b", "iris-c"])
        self.assertAlmostEqual(result["worst_deficit_db"], 2.0)
        self.assertTrue(all(":" in f for f in result["findings"]))

    def test_duplicate_case_identifier_is_refused(self):
        with self.assertRaises(ValueError):
            assess_unit([case("iris-a"), case("iris-a")])

    def test_empty_case_list_is_refused(self):
        with self.assertRaises(ValueError):
            assess_unit([])

    def test_non_sequence_case_list_is_refused(self):
        with self.assertRaises(ValueError):
            assess_unit("iris-a")


if __name__ == "__main__":
    unittest.main()
