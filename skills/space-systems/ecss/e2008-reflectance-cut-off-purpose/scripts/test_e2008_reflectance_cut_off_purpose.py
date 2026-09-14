"""Contract tests for the clause 8.7.5.3.2 cut-off purpose logic."""

import unittest

from e2008_reflectance_cut_off_purpose_logic import (
    BAND_WIDTH_SHORTFALL,
    COMMON_OBJECTIVE,
    CUT_OFF_NOT_RECORDED,
    CUT_OFF_RECORD_INADEQUATE,
    CUT_OFF_RECORD_NOT_REQUIRED,
    DEFAULT_BAND_POLICY,
    HIGH_REFLECTANCE_BAND_DESCRIBED,
    assess_cut_off_purpose,
    band_centre_nm,
    band_is_high_reflectance,
    band_width_nm,
    edge_is_credible,
    function_inventory,
    record_objectives,
    scan_reaches_the_edge,
    validate_band_policy,
)

FUNCTIONS = [
    "solar-reflector-band-placement",
    "thermal-control-absorptance-budget",
]


def _policy(**overrides):
    policy = dict(DEFAULT_BAND_POLICY)
    policy.update(overrides)
    return policy


def _case(**overrides):
    case = {
        "band_functions": list(FUNCTIONS),
        "band": {"peak_percent": 92.0},
        "measurement": {
            "cut_on_nm": 350.0,
            "cut_off_nm": 1120.0,
            "scan_upper_nm": 1200.0,
        },
    }
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(validate_band_policy(DEFAULT_BAND_POLICY), DEFAULT_BAND_POLICY)

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_band_policy("peak")

    def test_a_peak_floor_beyond_full_reflection_rejected(self):
        with self.assertRaises(ValueError):
            validate_band_policy(_policy(min_band_peak_percent=140.0))

    def test_a_negative_scan_margin_rejected(self):
        with self.assertRaises(ValueError):
            validate_band_policy(_policy(scan_margin_nm=-5.0))

    def test_a_zero_minimum_band_width_rejected(self):
        with self.assertRaises(ValueError):
            validate_band_policy(_policy(min_described_band_width_nm=0.0))

    def test_a_credible_ceiling_under_the_minimum_width_rejected(self):
        with self.assertRaises(ValueError):
            validate_band_policy(_policy(max_credible_wavelength_nm=40.0))


class FunctionTests(unittest.TestCase):
    def test_each_function_contributes_an_objective(self):
        objectives = record_objectives(FUNCTIONS)
        self.assertIn("band-placement-against-the-solar-spectrum", objectives)
        self.assertIn("solar-absorptance-integral-bounds", objectives)

    def test_the_shared_objective_is_appended_once(self):
        objectives = record_objectives(FUNCTIONS)
        self.assertEqual(objectives.count(COMMON_OBJECTIVE), 1)

    def test_no_function_yields_no_objective(self):
        self.assertEqual(record_objectives([]), ())

    def test_a_repeated_function_is_grouped_once(self):
        grouped = function_inventory(
            ["ultraviolet-rejection-stack", "ultraviolet-rejection-stack"]
        )
        self.assertEqual(grouped, ("ultraviolet-rejection-stack",))

    def test_an_unknown_function_rejected(self):
        with self.assertRaises(ValueError):
            function_inventory(["anti-reflection-coating"])

    def test_a_non_collection_function_list_rejected(self):
        with self.assertRaises(ValueError):
            function_inventory("ultraviolet-rejection-stack")


class BandGeometryTests(unittest.TestCase):
    def test_the_width_spans_the_two_edges(self):
        self.assertAlmostEqual(band_width_nm(350.0, 1120.0), 770.0, places=9)

    def test_the_centre_is_the_midpoint_of_the_edges(self):
        self.assertAlmostEqual(band_centre_nm(350.0, 1120.0), 735.0, places=9)

    def test_a_cut_off_below_the_cut_on_rejected(self):
        with self.assertRaises(ValueError):
            band_width_nm(1120.0, 350.0)

    def test_two_coincident_edges_rejected(self):
        with self.assertRaises(ValueError):
            band_width_nm(1120.0, 1120.0)

    def test_a_high_peak_is_a_high_reflectance_band(self):
        self.assertTrue(band_is_high_reflectance(92.0, _policy()))

    def test_a_peak_exactly_on_the_floor_is_a_high_reflectance_band(self):
        self.assertTrue(band_is_high_reflectance(60.0, _policy()))

    def test_a_low_peak_is_not_a_high_reflectance_band(self):
        self.assertFalse(band_is_high_reflectance(22.0, _policy()))

    def test_a_negative_peak_rejected(self):
        with self.assertRaises(ValueError):
            band_is_high_reflectance(-1.0, _policy())


class ScanCoverageTests(unittest.TestCase):
    def test_a_scan_running_past_the_edge_covers_it(self):
        self.assertTrue(scan_reaches_the_edge(1200.0, 1120.0, _policy()))

    def test_a_scan_ending_exactly_at_the_margin_covers_the_edge(self):
        self.assertTrue(scan_reaches_the_edge(1140.0, 1120.0, _policy()))

    def test_a_scan_ending_on_the_edge_does_not_cover_it(self):
        self.assertFalse(scan_reaches_the_edge(1120.0, 1120.0, _policy()))

    def test_a_scan_stopping_inside_the_band_does_not_cover_the_edge(self):
        self.assertFalse(scan_reaches_the_edge(1000.0, 1120.0, _policy()))

    def test_an_edge_inside_the_credible_range_is_credible(self):
        self.assertTrue(edge_is_credible(1120.0, _policy()))

    def test_an_edge_exactly_on_the_credible_ceiling_is_credible(self):
        self.assertTrue(edge_is_credible(2500.0, _policy()))

    def test_an_edge_beyond_the_credible_ceiling_is_not(self):
        self.assertFalse(edge_is_credible(4200.0, _policy()))

    def test_a_zero_scan_limit_rejected(self):
        with self.assertRaises(ValueError):
            scan_reaches_the_edge(0.0, 1120.0, _policy())


class PurposeAssessmentTests(unittest.TestCase):
    def test_a_kept_edge_describes_the_band(self):
        result = assess_cut_off_purpose(_case())
        self.assertEqual(result["verdict"], HIGH_REFLECTANCE_BAND_DESCRIBED)
        self.assertEqual(result["findings"], [])
        self.assertTrue(result["required"])

    def test_the_width_and_centre_are_reported(self):
        result = assess_cut_off_purpose(_case())
        self.assertAlmostEqual(result["band_width_nm"], 770.0, places=9)
        self.assertAlmostEqual(result["band_centre_nm"], 735.0, places=9)

    def test_the_objectives_name_what_the_edge_feeds(self):
        result = assess_cut_off_purpose(_case())
        self.assertIn("solar-absorptance-integral-bounds", result["objectives"])
        self.assertIn(COMMON_OBJECTIVE, result["objectives"])

    def test_no_declared_function_means_no_edge_needs_keeping(self):
        result = assess_cut_off_purpose(_case(band_functions=[]))
        self.assertEqual(result["verdict"], CUT_OFF_RECORD_NOT_REQUIRED)
        self.assertFalse(result["required"])

    def test_a_low_peak_band_is_not_a_high_reflectance_band_to_describe(self):
        result = assess_cut_off_purpose(_case(band={"peak_percent": 18.0}))
        self.assertEqual(result["verdict"], CUT_OFF_RECORD_NOT_REQUIRED)
        self.assertFalse(result["band_is_high_reflectance"])

    def test_a_peak_exactly_on_the_floor_still_needs_the_edge(self):
        result = assess_cut_off_purpose(_case(band={"peak_percent": 60.0}))
        self.assertTrue(result["required"])

    def test_a_required_but_unkept_edge_is_its_own_verdict(self):
        result = assess_cut_off_purpose(_case(measurement=None))
        self.assertEqual(result["verdict"], CUT_OFF_NOT_RECORDED)
        self.assertIsNone(result["cut_off_nm"])

    def test_a_measurement_block_with_no_edge_is_not_a_kept_edge(self):
        result = assess_cut_off_purpose(
            _case(measurement={"cut_on_nm": 350.0, "scan_upper_nm": 1200.0})
        )
        self.assertEqual(result["verdict"], CUT_OFF_NOT_RECORDED)

    def test_the_objectives_survive_an_unkept_edge(self):
        result = assess_cut_off_purpose(_case(measurement=None))
        self.assertIn(COMMON_OBJECTIVE, result["objectives"])

    def test_a_scan_stopping_inside_the_band_makes_the_record_inadequate(self):
        result = assess_cut_off_purpose(
            _case(
                measurement={
                    "cut_on_nm": 350.0,
                    "cut_off_nm": 1120.0,
                    "scan_upper_nm": 1125.0,
                }
            )
        )
        self.assertEqual(result["verdict"], CUT_OFF_RECORD_INADEQUATE)
        self.assertFalse(result["scan_reaches_the_edge"])

    def test_an_edge_beyond_the_credible_range_makes_the_record_inadequate(self):
        result = assess_cut_off_purpose(
            _case(
                measurement={
                    "cut_on_nm": 350.0,
                    "cut_off_nm": 4200.0,
                    "scan_upper_nm": 4400.0,
                }
            )
        )
        self.assertEqual(result["verdict"], CUT_OFF_RECORD_INADEQUATE)
        self.assertFalse(result["edge_is_credible"])

    def test_an_edge_without_its_partner_gives_no_band_width(self):
        result = assess_cut_off_purpose(
            _case(measurement={"cut_off_nm": 1120.0, "scan_upper_nm": 1200.0})
        )
        self.assertEqual(result["verdict"], CUT_OFF_RECORD_INADEQUATE)
        self.assertIsNone(result["band_width_nm"])

    def test_every_inadequacy_is_reported_not_only_the_first(self):
        result = assess_cut_off_purpose(
            _case(measurement={"cut_off_nm": 4200.0, "scan_upper_nm": 4205.0})
        )
        self.assertEqual(len(result["findings"]), 3)

    def test_a_band_too_narrow_to_describe_is_its_own_verdict(self):
        result = assess_cut_off_purpose(
            _case(
                measurement={
                    "cut_on_nm": 1100.0,
                    "cut_off_nm": 1120.0,
                    "scan_upper_nm": 1200.0,
                }
            )
        )
        self.assertEqual(result["verdict"], BAND_WIDTH_SHORTFALL)
        self.assertAlmostEqual(result["band_width_nm"], 20.0, places=9)

    def test_a_width_exactly_on_the_floor_describes_the_band(self):
        result = assess_cut_off_purpose(
            _case(
                measurement={
                    "cut_on_nm": 1070.0,
                    "cut_off_nm": 1120.0,
                    "scan_upper_nm": 1200.0,
                }
            )
        )
        self.assertEqual(result["verdict"], HIGH_REFLECTANCE_BAND_DESCRIBED)
        self.assertAlmostEqual(
            result["band_width_nm"],
            float(DEFAULT_BAND_POLICY["min_described_band_width_nm"]),
            places=9,
        )

    def test_an_absent_function_key_rejected(self):
        case = _case()
        del case["band_functions"]
        with self.assertRaises(ValueError):
            assess_cut_off_purpose(case)

    def test_a_missing_band_block_rejected(self):
        case = _case()
        del case["band"]
        with self.assertRaises(ValueError):
            assess_cut_off_purpose(case)

    def test_a_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_cut_off_purpose(["band_functions"])

    def test_a_non_mapping_measurement_rejected(self):
        with self.assertRaises(ValueError):
            assess_cut_off_purpose(_case(measurement=[1120.0]))


if __name__ == "__main__":
    unittest.main()
