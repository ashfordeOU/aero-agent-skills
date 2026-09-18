#!/usr/bin/env python3
"""Gate 3 contract test for e2007-radio-frequency-conducted-emission-setup.

stdlib unittest, offline, deterministic. Run:
    python3 test_e2007_radio_frequency_conducted_emission_setup.py
"""

import unittest

from e2007_radio_frequency_conducted_emission_setup_logic import (
    BASELINE_PARAMETERS,
    CATEGORY_CONFORMING,
    CATEGORY_DECLARED_DEVIATION,
    CATEGORY_NONCONFORMING,
    REQUIRED_PROVISIONS,
    VERDICT_CONFORMING,
    VERDICT_REJECTED,
    assess_bench_arrangement,
    categorize_parameter,
    derive_arrangement,
    normalize_parameter,
    parameter_bounds,
    parameter_deviation,
    validate_provisions,
)


def on_nominal_bench(**over):
    record = {}
    for key, spec in BASELINE_PARAMETERS.items():
        if spec["kind"] == "nominal":
            record[key] = spec["nominal"]
        else:
            record[key] = spec["limit"] / 2.0
    record.update(over)
    return record


def good_provisions(**over):
    record = dict((name, True) for name in REQUIRED_PROVISIONS)
    record.update(over)
    return record


class TestParameterNames(unittest.TestCase):
    def test_every_baseline_parameter_normalizes(self):
        for key in BASELINE_PARAMETERS:
            self.assertEqual(normalize_parameter(" %s " % key.upper()), key)

    def test_unrecognized_parameter_rejected(self):
        with self.assertRaises(ValueError):
            normalize_parameter("chamber-absorber-depth-m")

    def test_non_string_parameter_rejected(self):
        with self.assertRaises(ValueError):
            normalize_parameter(3.0)


class TestParameterBounds(unittest.TestCase):
    def test_nominal_band_brackets_the_nominal_value(self):
        low, high = parameter_bounds("power-lead-length-m")
        self.assertAlmostEqual(low, 1.9, places=9)
        self.assertAlmostEqual(high, 2.1, places=9)

    def test_maximum_band_starts_at_zero(self):
        low, high = parameter_bounds("eut-to-plane-bond-resistance-mohm")
        self.assertAlmostEqual(low, 0.0, places=9)
        self.assertAlmostEqual(high, 2.5, places=9)

    def test_non_positive_tolerance_rejected(self):
        with self.assertRaises(ValueError):
            parameter_bounds(
                "power-lead-length-m",
                {"kind": "nominal", "nominal": 2.0, "tolerance": 0.0},
            )

    def test_non_positive_limit_rejected(self):
        with self.assertRaises(ValueError):
            parameter_bounds(
                "eut-to-plane-bond-resistance-mohm", {"kind": "maximum", "limit": 0.0}
            )


class TestDerivation(unittest.TestCase):
    def test_no_delta_reproduces_the_general_arrangement(self):
        derived = derive_arrangement()
        self.assertEqual(sorted(derived), sorted(BASELINE_PARAMETERS))
        self.assertAlmostEqual(
            derived["power-lead-length-m"]["nominal"], 2.0, places=9
        )

    def test_declared_delta_moves_a_bound(self):
        derived = derive_arrangement({"probe-to-connector-distance-m": {"nominal": 0.10}})
        low, high = parameter_bounds("probe-to-connector-distance-m", derived["probe-to-connector-distance-m"])
        self.assertAlmostEqual(low, 0.09, places=9)
        self.assertAlmostEqual(high, 0.11, places=9)

    def test_derivation_does_not_mutate_the_baseline(self):
        derive_arrangement({"power-lead-length-m": {"nominal": 1.0}})
        self.assertAlmostEqual(
            BASELINE_PARAMETERS["power-lead-length-m"]["nominal"], 2.0, places=9
        )

    def test_unknown_delta_parameter_rejected(self):
        with self.assertRaises(ValueError):
            derive_arrangement({"turntable-diameter-m": {"nominal": 1.0}})

    def test_delta_changing_the_parameter_kind_rejected(self):
        with self.assertRaises(ValueError):
            derive_arrangement({"power-lead-length-m": {"kind": "maximum"}})

    def test_delta_with_a_field_the_parameter_does_not_have_rejected(self):
        with self.assertRaises(ValueError):
            derive_arrangement({"power-lead-length-m": {"limit": 3.0}})

    def test_delta_collapsing_the_band_rejected(self):
        with self.assertRaises(ValueError):
            derive_arrangement({"power-lead-length-m": {"tolerance": 0.0}})

    def test_non_mapping_delta_set_rejected(self):
        with self.assertRaises(ValueError):
            derive_arrangement(["power-lead-length-m"])

    def test_non_mapping_replacement_rejected(self):
        with self.assertRaises(ValueError):
            derive_arrangement({"power-lead-length-m": 2.5})


class TestDeviation(unittest.TestCase):
    def test_value_on_nominal_has_no_deviation(self):
        self.assertAlmostEqual(
            parameter_deviation("power-lead-length-m", 2.0), 0.0, places=9
        )

    def test_value_on_the_band_edge_has_no_deviation(self):
        self.assertAlmostEqual(
            parameter_deviation("power-lead-length-m", 2.1), 0.0, places=9
        )

    def test_value_above_the_band_reports_the_overrun(self):
        self.assertAlmostEqual(
            parameter_deviation("power-lead-length-m", 2.4), 0.3, places=9
        )

    def test_value_below_the_band_reports_a_negative_deviation(self):
        self.assertAlmostEqual(
            parameter_deviation("power-lead-length-m", 1.5), -0.4, places=9
        )

    def test_bond_resistance_over_its_limit_reports_the_overrun(self):
        self.assertAlmostEqual(
            parameter_deviation("eut-to-plane-bond-resistance-mohm", 4.0),
            1.5,
            places=9,
        )

    def test_negative_measured_value_rejected(self):
        with self.assertRaises(ValueError):
            parameter_deviation("power-lead-length-m", -0.5)

    def test_non_numeric_measured_value_rejected(self):
        with self.assertRaises(ValueError):
            parameter_deviation("power-lead-length-m", "two metres")

    def test_derived_band_changes_the_deviation(self):
        derived = derive_arrangement({"power-lead-length-m": {"nominal": 2.5}})
        self.assertAlmostEqual(
            parameter_deviation("power-lead-length-m", 2.4, derived), 0.0, places=9
        )


class TestCategorization(unittest.TestCase):
    def test_in_band_value_is_conforming(self):
        self.assertEqual(
            categorize_parameter("power-lead-length-m", 2.05), CATEGORY_CONFORMING
        )

    def test_out_of_band_value_is_nonconforming(self):
        self.assertEqual(
            categorize_parameter("power-lead-length-m", 2.4), CATEGORY_NONCONFORMING
        )

    def test_declared_departure_downgrades_to_a_deviation(self):
        self.assertEqual(
            categorize_parameter(
                "power-lead-length-m",
                2.4,
                declared_deviations=("power-lead-length-m",),
            ),
            CATEGORY_DECLARED_DEVIATION,
        )

    def test_declaring_another_parameter_does_not_help(self):
        self.assertEqual(
            categorize_parameter(
                "power-lead-length-m",
                2.4,
                declared_deviations=("probe-to-connector-distance-m",),
            ),
            CATEGORY_NONCONFORMING,
        )

    def test_unrecognized_declared_deviation_rejected(self):
        with self.assertRaises(ValueError):
            categorize_parameter(
                "power-lead-length-m", 2.0, declared_deviations=("bench-height-m",)
            )

    def test_non_collection_declared_deviations_rejected(self):
        with self.assertRaises(ValueError):
            categorize_parameter(
                "power-lead-length-m", 2.0, declared_deviations="power-lead-length-m"
            )


class TestProvisions(unittest.TestCase):
    def test_complete_provisions_normalize(self):
        checked = validate_provisions(good_provisions())
        self.assertEqual(sorted(checked), sorted(REQUIRED_PROVISIONS))

    def test_missing_provision_rejected(self):
        record = good_provisions()
        del record[REQUIRED_PROVISIONS[0]]
        with self.assertRaises(ValueError):
            validate_provisions(record)

    def test_non_boolean_provision_rejected(self):
        record = good_provisions()
        record[REQUIRED_PROVISIONS[0]] = "yes"
        with self.assertRaises(ValueError):
            validate_provisions(record)

    def test_unrecognized_provision_rejected(self):
        record = good_provisions()
        record["chamber-door-closed"] = True
        with self.assertRaises(ValueError):
            validate_provisions(record)

    def test_non_mapping_provisions_rejected(self):
        with self.assertRaises(ValueError):
            validate_provisions(list(REQUIRED_PROVISIONS))


class TestBenchAssessment(unittest.TestCase):
    def test_nominal_bench_conforms(self):
        report = assess_bench_arrangement(on_nominal_bench(), good_provisions())
        self.assertEqual(report["verdict"], VERDICT_CONFORMING)
        self.assertEqual(report["findings"], [])
        self.assertEqual(
            report["counts"][CATEGORY_CONFORMING], len(BASELINE_PARAMETERS)
        )

    def test_out_of_band_parameter_rejects_the_setup(self):
        report = assess_bench_arrangement(
            on_nominal_bench(**{"power-lead-length-m": 2.4}), good_provisions()
        )
        self.assertEqual(report["verdict"], VERDICT_REJECTED)
        self.assertEqual(report["governing_parameter"], "power-lead-length-m")
        self.assertTrue(any("outside its allowed band" in f for f in report["findings"]))

    def test_declared_deviation_is_a_limitation_not_a_finding(self):
        report = assess_bench_arrangement(
            on_nominal_bench(**{"power-lead-length-m": 2.4}),
            good_provisions(),
            declared_deviations=("power-lead-length-m",),
        )
        self.assertEqual(report["verdict"], VERDICT_CONFORMING)
        self.assertTrue(any("declared deviation" in l for l in report["limitations"]))

    def test_matching_delta_makes_the_same_bench_conform_outright(self):
        report = assess_bench_arrangement(
            on_nominal_bench(**{"power-lead-length-m": 2.4}),
            good_provisions(),
            deltas={"power-lead-length-m": {"nominal": 2.4}},
        )
        self.assertEqual(report["verdict"], VERDICT_CONFORMING)
        self.assertEqual(report["limitations"], [])

    def test_missing_bond_rejects_the_setup(self):
        report = assess_bench_arrangement(
            on_nominal_bench(), good_provisions(**{"ground-plane-bonded": False})
        )
        self.assertEqual(report["verdict"], VERDICT_REJECTED)
        self.assertTrue(
            any("required provision not in place" in f for f in report["findings"])
        )

    def test_bond_resistance_over_limit_rejects_the_setup(self):
        report = assess_bench_arrangement(
            on_nominal_bench(**{"eut-to-plane-bond-resistance-mohm": 6.0}),
            good_provisions(),
        )
        self.assertEqual(report["verdict"], VERDICT_REJECTED)
        self.assertEqual(
            report["governing_parameter"], "eut-to-plane-bond-resistance-mohm"
        )

    def test_incomplete_bench_record_rejected(self):
        record = on_nominal_bench()
        del record["probe-to-connector-distance-m"]
        with self.assertRaises(ValueError):
            assess_bench_arrangement(record, good_provisions())

    def test_duplicate_parameter_spelling_rejected(self):
        record = on_nominal_bench()
        record["POWER-LEAD-LENGTH-M"] = 2.0
        with self.assertRaises(ValueError):
            assess_bench_arrangement(record, good_provisions())

    def test_non_mapping_bench_record_rejected(self):
        with self.assertRaises(ValueError):
            assess_bench_arrangement([2.0, 0.05], good_provisions())

    def test_parameters_are_reported_in_a_stable_order(self):
        report = assess_bench_arrangement(on_nominal_bench(), good_provisions())
        names = [p["parameter"] for p in report["parameters"]]
        self.assertEqual(names, sorted(BASELINE_PARAMETERS))

    def test_allowed_band_is_reported_per_parameter(self):
        report = assess_bench_arrangement(on_nominal_bench(), good_provisions())
        entry = [
            p for p in report["parameters"] if p["parameter"] == "power-lead-length-m"
        ][0]
        self.assertAlmostEqual(entry["allowed_band"][0], 1.9, places=9)
        self.assertAlmostEqual(entry["allowed_band"][1], 2.1, places=9)

    def test_assessment_propagates_a_bad_delta(self):
        with self.assertRaises(ValueError):
            assess_bench_arrangement(
                on_nominal_bench(),
                good_provisions(),
                deltas={"power-lead-length-m": {"tolerance": 0.0}},
            )


if __name__ == "__main__":
    unittest.main()
