#!/usr/bin/env python3
"""Gate 3 contract test for e2007-radiated-electric-susceptibility-setup.

stdlib unittest, offline, deterministic. Run:
    python3 test_e2007_radiated_electric_susceptibility_setup.py
"""

import math
import unittest

from e2007_radiated_electric_susceptibility_setup_logic import (
    BASELINE_ARRANGEMENT,
    CATEGORY_CONFORMING,
    CATEGORY_DECLARED_DEVIATION,
    CATEGORY_NONCONFORMING,
    REQUIRED_PROVISIONS,
    VERDICT_CONFORMING,
    VERDICT_REJECTED,
    assess_chamber_arrangement,
    categorize_parameter,
    derive_arrangement,
    illuminated_span,
    illumination_coverage,
    normalize_parameter,
    parameter_bounds,
    parameter_deviation,
    required_span,
    validate_illumination,
    validate_provisions,
)


def on_nominal_chamber(**over):
    record = {}
    for key, spec in BASELINE_ARRANGEMENT.items():
        if spec["kind"] == "nominal":
            record[key] = spec["nominal"]
        elif spec["kind"] == "maximum":
            record[key] = spec["limit"] / 2.0
        else:
            record[key] = spec["limit"] * 2.0
    record.update(over)
    return record


def good_provisions(**over):
    record = dict((name, True) for name in REQUIRED_PROVISIONS)
    record.update(over)
    return record


def good_illumination(**over):
    record = {
        "antenna-beamwidth-deg": 60.0,
        "unit-face-width-m": 0.50,
        "harness-lateral-span-m": 0.40,
    }
    record.update(over)
    return record


class TestParameterNames(unittest.TestCase):
    def test_every_baseline_parameter_normalizes(self):
        for key in BASELINE_ARRANGEMENT:
            self.assertEqual(normalize_parameter(" %s " % key.upper()), key)

    def test_unrecognized_parameter_rejected(self):
        with self.assertRaises(ValueError):
            normalize_parameter("turntable-rotation-rate-deg-s")

    def test_non_string_parameter_rejected(self):
        with self.assertRaises(ValueError):
            normalize_parameter(1.25)


class TestParameterBounds(unittest.TestCase):
    def test_nominal_band_brackets_the_nominal_value(self):
        low, high = parameter_bounds("antenna-to-unit-separation-m")
        self.assertAlmostEqual(low, 0.95, places=9)
        self.assertAlmostEqual(high, 1.05, places=9)

    def test_maximum_band_starts_at_zero(self):
        low, high = parameter_bounds("unit-to-plane-bond-resistance-mohm")
        self.assertAlmostEqual(low, 0.0, places=9)
        self.assertAlmostEqual(high, 2.5, places=9)

    def test_minimum_band_is_open_above_its_floor(self):
        low, high = parameter_bounds("absorber-to-antenna-clearance-m")
        self.assertAlmostEqual(low, 0.50, places=9)
        self.assertEqual(high, float("inf"))

    def test_non_positive_tolerance_rejected(self):
        with self.assertRaises(ValueError):
            parameter_bounds(
                "antenna-to-unit-separation-m",
                {"kind": "nominal", "nominal": 1.0, "tolerance": 0.0},
            )

    def test_non_positive_limit_rejected(self):
        with self.assertRaises(ValueError):
            parameter_bounds(
                "unit-to-plane-bond-resistance-mohm", {"kind": "maximum", "limit": 0.0}
            )


class TestDerivation(unittest.TestCase):
    def test_no_delta_reproduces_the_baseline_arrangement(self):
        derived = derive_arrangement()
        self.assertEqual(sorted(derived), sorted(BASELINE_ARRANGEMENT))
        self.assertAlmostEqual(
            derived["antenna-to-unit-separation-m"]["nominal"], 1.0, places=9
        )

    def test_declared_delta_moves_a_bound(self):
        derived = derive_arrangement({"antenna-to-unit-separation-m": {"nominal": 3.0}})
        low, high = parameter_bounds(
            "antenna-to-unit-separation-m", derived["antenna-to-unit-separation-m"]
        )
        self.assertAlmostEqual(low, 2.95, places=9)
        self.assertAlmostEqual(high, 3.05, places=9)

    def test_derivation_does_not_mutate_the_baseline(self):
        derive_arrangement({"exposed-harness-run-m": {"nominal": 0.5}})
        self.assertAlmostEqual(
            BASELINE_ARRANGEMENT["exposed-harness-run-m"]["nominal"], 1.5, places=9
        )

    def test_unknown_delta_parameter_rejected(self):
        with self.assertRaises(ValueError):
            derive_arrangement({"amplifier-rack-depth-m": {"nominal": 1.0}})

    def test_delta_changing_the_parameter_kind_rejected(self):
        with self.assertRaises(ValueError):
            derive_arrangement({"exposed-harness-run-m": {"kind": "maximum"}})

    def test_delta_with_a_field_the_parameter_does_not_have_rejected(self):
        with self.assertRaises(ValueError):
            derive_arrangement({"exposed-harness-run-m": {"limit": 3.0}})

    def test_delta_collapsing_the_band_rejected(self):
        with self.assertRaises(ValueError):
            derive_arrangement({"exposed-harness-run-m": {"tolerance": 0.0}})

    def test_non_mapping_delta_set_rejected(self):
        with self.assertRaises(ValueError):
            derive_arrangement(["exposed-harness-run-m"])

    def test_non_mapping_replacement_rejected(self):
        with self.assertRaises(ValueError):
            derive_arrangement({"exposed-harness-run-m": 1.2})


class TestIlluminatedSpan(unittest.TestCase):
    def test_ninety_degree_beam_spans_twice_the_separation(self):
        self.assertAlmostEqual(illuminated_span(2.0, 90.0), 4.0, places=9)

    def test_span_scales_with_separation(self):
        near = illuminated_span(1.0, 60.0)
        far = illuminated_span(2.0, 60.0)
        self.assertAlmostEqual(far, 2.0 * near, places=9)

    def test_sixty_degree_beam_matches_the_closed_form(self):
        self.assertAlmostEqual(
            illuminated_span(1.0, 60.0),
            2.0 * math.tan(math.radians(30.0)),
            places=9,
        )

    def test_non_positive_separation_rejected(self):
        with self.assertRaises(ValueError):
            illuminated_span(0.0, 60.0)

    def test_beamwidth_at_or_above_a_half_turn_rejected(self):
        with self.assertRaises(ValueError):
            illuminated_span(1.0, 180.0)

    def test_non_positive_beamwidth_rejected(self):
        with self.assertRaises(ValueError):
            illuminated_span(1.0, 0.0)

    def test_non_numeric_separation_rejected(self):
        with self.assertRaises(ValueError):
            illuminated_span("1.0", 60.0)


class TestRequiredSpan(unittest.TestCase):
    def test_span_is_the_face_plus_the_harness_beside_it(self):
        self.assertAlmostEqual(required_span(0.5, 0.4), 0.9, places=9)

    def test_a_harness_kept_behind_the_unit_adds_nothing(self):
        self.assertAlmostEqual(required_span(0.5, 0.0), 0.5, places=9)

    def test_non_positive_face_width_rejected(self):
        with self.assertRaises(ValueError):
            required_span(0.0, 0.4)

    def test_negative_harness_span_rejected(self):
        with self.assertRaises(ValueError):
            required_span(0.5, -0.1)


class TestIlluminationCoverage(unittest.TestCase):
    def test_nominal_chamber_covers_the_unit_and_harness(self):
        coverage = illumination_coverage(1.0, good_illumination())
        self.assertTrue(coverage["covered"])
        self.assertAlmostEqual(coverage["required_span_m"], 0.9, places=9)

    def test_margin_is_the_footprint_less_the_span_required(self):
        coverage = illumination_coverage(1.0, good_illumination())
        self.assertAlmostEqual(
            coverage["margin_m"],
            coverage["illuminated_span_m"] - coverage["required_span_m"],
            places=9,
        )

    def test_a_wide_unit_outgrows_the_footprint(self):
        coverage = illumination_coverage(
            1.0, good_illumination(**{"unit-face-width-m": 1.20})
        )
        self.assertFalse(coverage["covered"])

    def test_a_span_landing_exactly_on_the_footprint_still_counts_as_covered(self):
        footprint = illuminated_span(1.0, 60.0)
        illumination = good_illumination(
            **{"unit-face-width-m": 0.5, "harness-lateral-span-m": footprint - 0.5}
        )
        coverage = illumination_coverage(1.0, illumination)
        self.assertAlmostEqual(coverage["margin_m"], 0.0, places=9)
        self.assertTrue(coverage["covered"])

    def test_backing_the_antenna_off_recovers_a_wide_unit(self):
        illumination = good_illumination(**{"unit-face-width-m": 1.20})
        self.assertFalse(illumination_coverage(1.0, illumination)["covered"])
        self.assertTrue(illumination_coverage(2.0, illumination)["covered"])

    def test_illumination_missing_a_field_rejected(self):
        broken = good_illumination()
        del broken["antenna-beamwidth-deg"]
        with self.assertRaises(ValueError):
            validate_illumination(broken)

    def test_illumination_with_an_invented_field_rejected(self):
        with self.assertRaises(ValueError):
            validate_illumination(good_illumination(**{"chamber-length-m": 6.0}))

    def test_non_mapping_illumination_rejected(self):
        with self.assertRaises(ValueError):
            validate_illumination(["antenna-beamwidth-deg"])


class TestDeviation(unittest.TestCase):
    def test_value_on_nominal_has_no_deviation(self):
        self.assertAlmostEqual(
            parameter_deviation("antenna-to-unit-separation-m", 1.0), 0.0, places=9
        )

    def test_value_on_the_band_edge_has_no_deviation(self):
        self.assertAlmostEqual(
            parameter_deviation("antenna-to-unit-separation-m", 1.05), 0.0, places=9
        )

    def test_value_above_the_band_reports_the_overrun(self):
        self.assertAlmostEqual(
            parameter_deviation("antenna-to-unit-separation-m", 1.30), 0.25, places=9
        )

    def test_value_below_the_band_reports_a_negative_deviation(self):
        self.assertAlmostEqual(
            parameter_deviation("exposed-harness-run-m", 1.20), -0.20, places=9
        )

    def test_bond_resistance_over_its_limit_reports_the_overrun(self):
        self.assertAlmostEqual(
            parameter_deviation("unit-to-plane-bond-resistance-mohm", 4.0),
            1.5,
            places=9,
        )

    def test_absorber_clearance_below_its_floor_reports_the_shortfall(self):
        self.assertAlmostEqual(
            parameter_deviation("absorber-to-antenna-clearance-m", 0.30),
            -0.20,
            places=9,
        )

    def test_absorber_clearance_far_above_its_floor_is_never_a_deviation(self):
        self.assertAlmostEqual(
            parameter_deviation("absorber-to-antenna-clearance-m", 9.0), 0.0, places=9
        )

    def test_negative_measured_value_rejected(self):
        with self.assertRaises(ValueError):
            parameter_deviation("exposed-harness-run-m", -0.5)

    def test_non_finite_measured_value_rejected(self):
        with self.assertRaises(ValueError):
            parameter_deviation("exposed-harness-run-m", float("nan"))


class TestCategorization(unittest.TestCase):
    def test_in_band_parameter_is_conforming(self):
        self.assertEqual(
            categorize_parameter("exposed-harness-run-m", 1.5), CATEGORY_CONFORMING
        )

    def test_out_of_band_parameter_without_a_departure_is_nonconforming(self):
        self.assertEqual(
            categorize_parameter("exposed-harness-run-m", 2.4), CATEGORY_NONCONFORMING
        )

    def test_out_of_band_parameter_under_a_departure_is_a_declared_deviation(self):
        self.assertEqual(
            categorize_parameter(
                "exposed-harness-run-m",
                2.4,
                None,
                ("exposed-harness-run-m",),
            ),
            CATEGORY_DECLARED_DEVIATION,
        )

    def test_a_departure_does_not_change_an_in_band_parameter(self):
        self.assertEqual(
            categorize_parameter(
                "exposed-harness-run-m", 1.5, None, ("exposed-harness-run-m",)
            ),
            CATEGORY_CONFORMING,
        )

    def test_non_collection_declared_deviations_rejected(self):
        with self.assertRaises(ValueError):
            categorize_parameter("exposed-harness-run-m", 2.4, None, "everything")


class TestProvisions(unittest.TestCase):
    def test_complete_provisions_normalize(self):
        self.assertEqual(validate_provisions(good_provisions()), good_provisions())

    def test_missing_provision_rejected(self):
        broken = good_provisions()
        del broken["unit-bonded-to-ground-plane"]
        with self.assertRaises(ValueError):
            validate_provisions(broken)

    def test_non_boolean_provision_rejected(self):
        with self.assertRaises(ValueError):
            validate_provisions(good_provisions(**{"unit-bonded-to-ground-plane": 1}))

    def test_invented_provision_rejected(self):
        with self.assertRaises(ValueError):
            validate_provisions(good_provisions(**{"coffee-machine-unplugged": True}))


class TestAssessment(unittest.TestCase):
    def test_nominal_chamber_conforms(self):
        result = assess_chamber_arrangement(
            on_nominal_chamber(), good_provisions(), good_illumination()
        )
        self.assertEqual(result["verdict"], VERDICT_CONFORMING)
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["counts"][CATEGORY_CONFORMING], len(BASELINE_ARRANGEMENT))

    def test_out_of_band_parameter_rejects_the_arrangement(self):
        result = assess_chamber_arrangement(
            on_nominal_chamber(**{"harness-height-above-ground-plane-m": 0.20}),
            good_provisions(),
            good_illumination(),
        )
        self.assertEqual(result["verdict"], VERDICT_REJECTED)
        self.assertEqual(result["governing_parameter"], "harness-height-above-ground-plane-m")

    def test_declared_deviation_is_carried_as_a_limitation_not_a_finding(self):
        result = assess_chamber_arrangement(
            on_nominal_chamber(**{"field-probe-lateral-offset-m": 0.50}),
            good_provisions(),
            good_illumination(),
            None,
            ("field-probe-lateral-offset-m",),
        )
        self.assertEqual(result["verdict"], VERDICT_CONFORMING)
        self.assertEqual(len(result["limitations"]), 1)
        self.assertEqual(result["counts"][CATEGORY_DECLARED_DEVIATION], 1)

    def test_absent_provision_rejects_an_otherwise_clean_chamber(self):
        result = assess_chamber_arrangement(
            on_nominal_chamber(),
            good_provisions(**{"field-probe-clear-of-unit-shadow": False}),
            good_illumination(),
        )
        self.assertEqual(result["verdict"], VERDICT_REJECTED)
        self.assertTrue(
            any("field-probe-clear-of-unit-shadow" in f for f in result["findings"])
        )

    def test_a_unit_wider_than_the_footprint_rejects_the_arrangement(self):
        result = assess_chamber_arrangement(
            on_nominal_chamber(),
            good_provisions(),
            good_illumination(**{"unit-face-width-m": 1.20}),
        )
        self.assertEqual(result["verdict"], VERDICT_REJECTED)
        self.assertFalse(result["coverage"]["covered"])

    def test_governing_parameter_is_the_furthest_outside_its_band(self):
        result = assess_chamber_arrangement(
            on_nominal_chamber(
                **{
                    "exposed-harness-run-m": 1.75,
                    "antenna-to-unit-separation-m": 1.40,
                }
            ),
            good_provisions(),
            good_illumination(),
        )
        self.assertEqual(result["governing_parameter"], "antenna-to-unit-separation-m")

    def test_declared_delta_admits_a_chamber_the_baseline_would_reject(self):
        measured = on_nominal_chamber(**{"antenna-to-unit-separation-m": 3.0})
        rejected = assess_chamber_arrangement(
            measured, good_provisions(), good_illumination()
        )
        self.assertEqual(rejected["verdict"], VERDICT_REJECTED)
        accepted = assess_chamber_arrangement(
            measured,
            good_provisions(),
            good_illumination(),
            {"antenna-to-unit-separation-m": {"nominal": 3.0}},
        )
        self.assertEqual(accepted["verdict"], VERDICT_CONFORMING)

    def test_record_omitting_a_parameter_rejected(self):
        measured = on_nominal_chamber()
        del measured["absorber-to-antenna-clearance-m"]
        with self.assertRaises(ValueError):
            assess_chamber_arrangement(
                measured, good_provisions(), good_illumination()
            )

    def test_parameter_given_twice_under_two_spellings_rejected(self):
        measured = on_nominal_chamber()
        measured["EXPOSED-HARNESS-RUN-M"] = 1.5
        with self.assertRaises(ValueError):
            assess_chamber_arrangement(
                measured, good_provisions(), good_illumination()
            )

    def test_non_mapping_measurement_record_rejected(self):
        with self.assertRaises(ValueError):
            assess_chamber_arrangement(
                ["antenna-to-unit-separation-m"], good_provisions(), good_illumination()
            )

    def test_every_parameter_is_reported_with_its_band_and_category(self):
        result = assess_chamber_arrangement(
            on_nominal_chamber(), good_provisions(), good_illumination()
        )
        self.assertEqual(len(result["parameters"]), len(BASELINE_ARRANGEMENT))
        for entry in result["parameters"]:
            self.assertIn("allowed_band", entry)
            self.assertIn(entry["category"], (
                CATEGORY_CONFORMING,
                CATEGORY_DECLARED_DEVIATION,
                CATEGORY_NONCONFORMING,
            ))


if __name__ == "__main__":
    unittest.main(verbosity=0)
