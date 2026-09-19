"""Contract tests for the clause 5.6.12.3 unwanted RF emission logic."""

import unittest

from e50_unwanted_rf_emissions_logic import (
    IN_BAND,
    LIMITS_EXCEEDED,
    MARGIN_SHORT,
    OUT_OF_BAND,
    SPURIOUS,
    WITHIN_LIMITS,
    assess_emission,
    assess_emission_set,
    emission_domain,
    mask_limit_dbc,
    normalize_mask,
    validate_bandwidth,
    validate_frequency,
    validate_level_dbc,
)

CENTRE = 8400000000.0
BANDWIDTH = 10000000.0

MASK = [
    (0.5, -20.0),
    (1.0, -40.0),
    (2.5, -60.0),
]

SPURIOUS_LIMIT = -60.0


class ValidationTests(unittest.TestCase):
    def test_positive_frequency_accepted(self):
        self.assertAlmostEqual(validate_frequency(CENTRE), CENTRE, places=6)

    def test_zero_frequency_rejected(self):
        with self.assertRaises(ValueError):
            validate_frequency(0.0)

    def test_negative_bandwidth_rejected(self):
        with self.assertRaises(ValueError):
            validate_bandwidth(-1.0)

    def test_level_at_the_carrier_accepted(self):
        self.assertAlmostEqual(validate_level_dbc(0.0), 0.0, places=9)

    def test_level_above_the_carrier_rejected(self):
        with self.assertRaises(ValueError):
            validate_level_dbc(3.0)

    def test_boolean_level_rejected(self):
        with self.assertRaises(ValueError):
            validate_level_dbc(True)


class MaskTests(unittest.TestCase):
    def test_mask_is_sorted_by_offset(self):
        normalized = normalize_mask([(2.5, -60.0), (0.5, -20.0), (1.0, -40.0)])
        self.assertAlmostEqual(normalized[0][0], 0.5, places=9)
        self.assertAlmostEqual(normalized[-1][0], 2.5, places=9)

    def test_single_breakpoint_mask_rejected(self):
        with self.assertRaises(ValueError):
            normalize_mask([(0.5, -20.0)])

    def test_duplicate_offsets_rejected(self):
        with self.assertRaises(ValueError):
            normalize_mask([(0.5, -20.0), (0.5, -40.0)])

    def test_mapping_breakpoints_accepted(self):
        normalized = normalize_mask(
            [
                {"offset_ratio": 0.5, "limit_dbc": -20.0},
                {"offset_ratio": 1.0, "limit_dbc": -40.0},
            ]
        )
        self.assertEqual(len(normalized), 2)

    def test_limit_at_a_breakpoint_is_the_breakpoint_value(self):
        self.assertAlmostEqual(mask_limit_dbc(MASK, 1.0), -40.0, places=9)

    def test_limit_between_breakpoints_is_interpolated(self):
        self.assertAlmostEqual(mask_limit_dbc(MASK, 0.75), -30.0, places=9)

    def test_limit_below_the_first_breakpoint_is_held_flat(self):
        self.assertAlmostEqual(mask_limit_dbc(MASK, 0.1), -20.0, places=9)

    def test_limit_beyond_the_last_breakpoint_is_held_flat(self):
        self.assertAlmostEqual(mask_limit_dbc(MASK, 4.0), -60.0, places=9)

    def test_negative_offset_rejected(self):
        with self.assertRaises(ValueError):
            mask_limit_dbc(MASK, -0.1)


class DomainTests(unittest.TestCase):
    def test_carrier_itself_is_in_band(self):
        self.assertEqual(emission_domain(CENTRE, BANDWIDTH, CENTRE), IN_BAND)

    def test_exactly_at_the_band_edge_is_in_band(self):
        edge = CENTRE + BANDWIDTH / 2.0
        self.assertEqual(emission_domain(CENTRE, BANDWIDTH, edge), IN_BAND)

    def test_just_outside_the_band_edge_is_out_of_band(self):
        frequency = CENTRE + BANDWIDTH
        self.assertEqual(emission_domain(CENTRE, BANDWIDTH, frequency), OUT_OF_BAND)

    def test_exactly_at_the_spurious_boundary_is_out_of_band(self):
        frequency = CENTRE + 2.5 * BANDWIDTH
        self.assertEqual(emission_domain(CENTRE, BANDWIDTH, frequency), OUT_OF_BAND)

    def test_beyond_the_spurious_boundary_is_spurious(self):
        frequency = CENTRE + 4.0 * BANDWIDTH
        self.assertEqual(emission_domain(CENTRE, BANDWIDTH, frequency), SPURIOUS)

    def test_the_domain_is_symmetric_about_the_carrier(self):
        below = emission_domain(CENTRE, BANDWIDTH, CENTRE - 4.0 * BANDWIDTH)
        above = emission_domain(CENTRE, BANDWIDTH, CENTRE + 4.0 * BANDWIDTH)
        self.assertEqual(below, above)


class AssessEmissionTests(unittest.TestCase):
    def test_in_band_component_is_reported_and_not_graded(self):
        result = assess_emission(
            {"frequency_hz": CENTRE, "level_dbc": 0.0},
            CENTRE,
            BANDWIDTH,
            MASK,
            SPURIOUS_LIMIT,
        )
        self.assertFalse(result["graded"])
        self.assertIsNone(result["limit_dbc"])
        self.assertTrue(result["compliant"])

    def test_out_of_band_component_is_graded_against_the_mask(self):
        result = assess_emission(
            {"frequency_hz": CENTRE + BANDWIDTH, "level_dbc": -50.0},
            CENTRE,
            BANDWIDTH,
            MASK,
            SPURIOUS_LIMIT,
        )
        self.assertEqual(result["domain"], OUT_OF_BAND)
        self.assertAlmostEqual(result["limit_dbc"], -40.0, places=9)
        self.assertAlmostEqual(result["margin_db"], 10.0, places=9)

    def test_spurious_component_is_graded_against_the_flat_limit(self):
        result = assess_emission(
            {"frequency_hz": CENTRE + 10.0 * BANDWIDTH, "level_dbc": -75.0},
            CENTRE,
            BANDWIDTH,
            MASK,
            SPURIOUS_LIMIT,
        )
        self.assertEqual(result["domain"], SPURIOUS)
        self.assertAlmostEqual(result["margin_db"], 15.0, places=9)

    def test_component_exactly_on_its_limit_is_compliant(self):
        result = assess_emission(
            {"frequency_hz": CENTRE + BANDWIDTH, "level_dbc": -40.0},
            CENTRE,
            BANDWIDTH,
            MASK,
            SPURIOUS_LIMIT,
        )
        self.assertAlmostEqual(result["margin_db"], 0.0, places=9)
        self.assertTrue(result["compliant"])
        self.assertFalse(result["comfortable"])

    def test_component_over_its_limit_is_not_compliant(self):
        result = assess_emission(
            {"frequency_hz": CENTRE + BANDWIDTH, "level_dbc": -35.0},
            CENTRE,
            BANDWIDTH,
            MASK,
            SPURIOUS_LIMIT,
        )
        self.assertFalse(result["compliant"])
        self.assertAlmostEqual(result["margin_db"], -5.0, places=9)

    def test_offset_ratio_is_reported(self):
        result = assess_emission(
            {"frequency_hz": CENTRE + 2.0 * BANDWIDTH, "level_dbc": -70.0},
            CENTRE,
            BANDWIDTH,
            MASK,
            SPURIOUS_LIMIT,
        )
        self.assertAlmostEqual(result["offset_ratio"], 2.0, places=9)

    def test_component_without_a_level_rejected(self):
        with self.assertRaises(ValueError):
            assess_emission(
                {"frequency_hz": CENTRE}, CENTRE, BANDWIDTH, MASK, SPURIOUS_LIMIT
            )

    def test_negative_required_margin_rejected(self):
        with self.assertRaises(ValueError):
            assess_emission(
                {"frequency_hz": CENTRE + BANDWIDTH, "level_dbc": -50.0},
                CENTRE,
                BANDWIDTH,
                MASK,
                SPURIOUS_LIMIT,
                required_margin_db=-1.0,
            )


class EmissionSetTests(unittest.TestCase):
    CLEAN = [
        {"frequency_hz": CENTRE, "level_dbc": 0.0},
        {"frequency_hz": CENTRE + BANDWIDTH, "level_dbc": -55.0},
        {"frequency_hz": CENTRE - 2.0 * BANDWIDTH, "level_dbc": -70.0},
        {"frequency_hz": CENTRE + 12.0 * BANDWIDTH, "level_dbc": -80.0},
    ]

    def test_a_clean_set_is_within_limits(self):
        result = assess_emission_set(
            self.CLEAN, CENTRE, BANDWIDTH, MASK, SPURIOUS_LIMIT
        )
        self.assertEqual(result["verdict"], WITHIN_LIMITS)
        self.assertTrue(result["compliant"])

    def test_domain_counts_separate_the_wanted_emission(self):
        result = assess_emission_set(
            self.CLEAN, CENTRE, BANDWIDTH, MASK, SPURIOUS_LIMIT
        )
        self.assertEqual(result["domain_counts"][IN_BAND], 1)
        self.assertEqual(result["graded_count"], 3)

    def test_a_thin_margin_is_its_own_verdict(self):
        components = list(self.CLEAN) + [
            {"frequency_hz": CENTRE + 2.5 * BANDWIDTH, "level_dbc": -61.0}
        ]
        result = assess_emission_set(
            components, CENTRE, BANDWIDTH, MASK, SPURIOUS_LIMIT
        )
        self.assertEqual(result["verdict"], MARGIN_SHORT)
        self.assertTrue(result["compliant"])

    def test_an_exceedance_governs_the_verdict(self):
        components = list(self.CLEAN) + [
            {"frequency_hz": CENTRE + 20.0 * BANDWIDTH, "level_dbc": -45.0}
        ]
        result = assess_emission_set(
            components, CENTRE, BANDWIDTH, MASK, SPURIOUS_LIMIT
        )
        self.assertEqual(result["verdict"], LIMITS_EXCEEDED)
        self.assertEqual(result["exceedance_count"], 1)

    def test_findings_quantify_the_overshoot(self):
        components = list(self.CLEAN) + [
            {"frequency_hz": CENTRE + 20.0 * BANDWIDTH, "level_dbc": -45.0}
        ]
        result = assess_emission_set(
            components, CENTRE, BANDWIDTH, MASK, SPURIOUS_LIMIT
        )
        self.assertTrue(any("over its limit" in f for f in result["findings"]))

    def test_worst_margin_ignores_the_wanted_emission(self):
        result = assess_emission_set(
            self.CLEAN, CENTRE, BANDWIDTH, MASK, SPURIOUS_LIMIT
        )
        self.assertAlmostEqual(result["worst_margin_db"], 15.0, places=9)
        self.assertEqual(result["worst_component"]["domain"], OUT_OF_BAND)

    def test_empty_component_set_rejected(self):
        with self.assertRaises(ValueError):
            assess_emission_set([], CENTRE, BANDWIDTH, MASK, SPURIOUS_LIMIT)

    def test_non_list_component_set_rejected(self):
        with self.assertRaises(ValueError):
            assess_emission_set(
                self.CLEAN[0], CENTRE, BANDWIDTH, MASK, SPURIOUS_LIMIT
            )


if __name__ == "__main__":
    unittest.main()
