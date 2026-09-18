#!/usr/bin/env python3
"""Gate 3 contract test for e2007-radiated-electric-emission-setup.

stdlib unittest, offline, deterministic. Run:
    python3 test_e2007_radiated_electric_emission_setup.py
"""

import unittest

from e2007_radiated_electric_emission_setup_logic import (
    BASELINE_PARAMETERS,
    CATEGORY_CONFORMING,
    CATEGORY_DECLARED_DEVIATION,
    CATEGORY_NONCONFORMING,
    POLARIZATIONS,
    REGIME_AT_BOUNDARY,
    REGIME_FAR_FIELD,
    REGIME_NEAR_FIELD,
    UNIT_FACES,
    VERDICT_CONFORMING,
    VERDICT_REJECTED,
    assess_bench_layout,
    categorize_parameter,
    derive_layout,
    missing_presentations,
    near_field_boundary_m,
    normalize_face,
    normalize_parameter,
    normalize_polarization,
    parameter_bounds,
    parameter_deviation,
    relative_overrun,
    separation_regime,
    validate_presentations,
)

# Independent reference values, computed once from the free-space wavelength
# at the stated frequency divided by two pi. Hard-coded so the test does not
# re-derive them from the module it is grading.
BOUNDARY_AT_30_MHZ_M = 1.590448386
BOUNDARY_AT_1_GHZ_M = 0.047713452


def clean_bench():
    return {
        "antenna-to-unit-separation-m": 1.0,
        "antenna-boresight-height-m": 1.0,
        "unit-edge-to-plane-edge-m": 0.10,
        "cable-run-length-along-plane-m": 2.0,
        "unit-to-plane-bond-resistance-mohm": 1.2,
        "absorber-to-antenna-clearance-m": 0.8,
    }


def full_presentations():
    return [(face, plane) for face in UNIT_FACES for plane in POLARIZATIONS]


class TestNames(unittest.TestCase):
    def test_every_baseline_parameter_normalizes(self):
        for name in BASELINE_PARAMETERS:
            self.assertEqual(normalize_parameter(name.upper()), name)

    def test_unrecognized_parameter_rejected(self):
        with self.assertRaises(ValueError):
            normalize_parameter("chamber-volume-m3")

    def test_non_string_parameter_rejected(self):
        with self.assertRaises(ValueError):
            normalize_parameter(5)

    def test_every_face_normalizes(self):
        for face in UNIT_FACES:
            self.assertEqual(normalize_face(" %s " % face.upper()), face)

    def test_unrecognized_face_rejected(self):
        with self.assertRaises(ValueError):
            normalize_face("bottom")

    def test_unrecognized_polarization_rejected(self):
        with self.assertRaises(ValueError):
            normalize_polarization("circular")


class TestBounds(unittest.TestCase):
    def test_nominal_band_is_symmetric(self):
        low, high = parameter_bounds("antenna-to-unit-separation-m")
        self.assertAlmostEqual(low, 0.95, places=9)
        self.assertAlmostEqual(high, 1.05, places=9)

    def test_maximum_band_starts_at_zero(self):
        low, high = parameter_bounds("unit-to-plane-bond-resistance-mohm")
        self.assertAlmostEqual(low, 0.0, places=9)
        self.assertAlmostEqual(high, 2.5, places=9)

    def test_minimum_band_is_open_above(self):
        low, high = parameter_bounds("absorber-to-antenna-clearance-m")
        self.assertAlmostEqual(low, 0.5, places=9)
        self.assertTrue(high == float("inf"))


class TestDerivation(unittest.TestCase):
    def test_baseline_is_returned_when_nothing_is_declared(self):
        layout = derive_layout()
        self.assertAlmostEqual(
            layout["antenna-to-unit-separation-m"]["nominal"], 1.0, places=9
        )

    def test_chosen_separation_moves_the_absorber_clearance(self):
        layout = derive_layout(separation_m=3.0)
        self.assertAlmostEqual(
            layout["absorber-to-antenna-clearance-m"]["limit"], 1.5, places=9
        )

    def test_derivation_does_not_mutate_the_baseline(self):
        derive_layout(separation_m=3.0)
        self.assertAlmostEqual(
            BASELINE_PARAMETERS["antenna-to-unit-separation-m"]["nominal"], 1.0, places=9
        )

    def test_non_positive_separation_rejected(self):
        with self.assertRaises(ValueError):
            derive_layout(separation_m=0.0)

    def test_delta_widens_a_tolerance(self):
        layout = derive_layout(deltas={"antenna-boresight-height-m": {"tolerance": 0.2}})
        low, high = parameter_bounds("antenna-boresight-height-m", layout["antenna-boresight-height-m"])
        self.assertAlmostEqual(high - low, 0.4, places=9)

    def test_delta_changing_the_kind_rejected(self):
        with self.assertRaises(ValueError):
            derive_layout(deltas={"antenna-boresight-height-m": {"kind": "maximum"}})

    def test_delta_with_an_unknown_field_rejected(self):
        with self.assertRaises(ValueError):
            derive_layout(deltas={"antenna-boresight-height-m": {"limit": 2.0}})

    def test_delta_collapsing_the_band_rejected(self):
        with self.assertRaises(ValueError):
            derive_layout(deltas={"antenna-boresight-height-m": {"tolerance": 0.0}})

    def test_delta_on_an_unknown_parameter_rejected(self):
        with self.assertRaises(ValueError):
            derive_layout(deltas={"chamber-volume-m3": {"limit": 2.0}})

    def test_non_mapping_deltas_rejected(self):
        with self.assertRaises(ValueError):
            derive_layout(deltas=[("antenna-boresight-height-m", 0.2)])


class TestDeviation(unittest.TestCase):
    def test_value_inside_the_band_has_no_deviation(self):
        self.assertAlmostEqual(
            parameter_deviation("antenna-to-unit-separation-m", 1.02), 0.0, places=9
        )

    def test_value_above_a_nominal_band_reports_the_overrun(self):
        self.assertAlmostEqual(
            parameter_deviation("antenna-to-unit-separation-m", 1.20), 0.15, places=9
        )

    def test_value_below_a_minimum_reports_a_negative_deviation(self):
        self.assertAlmostEqual(
            parameter_deviation("absorber-to-antenna-clearance-m", 0.30), -0.20, places=9
        )

    def test_value_on_a_maximum_limit_is_inside_the_band(self):
        self.assertAlmostEqual(
            parameter_deviation("unit-to-plane-bond-resistance-mohm", 2.5), 0.0, places=9
        )

    def test_negative_measurement_rejected(self):
        with self.assertRaises(ValueError):
            parameter_deviation("antenna-boresight-height-m", -0.1)

    def test_overrun_is_expressed_against_the_parameter_scale(self):
        self.assertAlmostEqual(
            relative_overrun("antenna-to-unit-separation-m", 1.20), 3.0, places=9
        )


class TestCategorization(unittest.TestCase):
    def test_in_band_value_is_conforming(self):
        self.assertEqual(
            categorize_parameter("antenna-boresight-height-m", 1.01),
            CATEGORY_CONFORMING,
        )

    def test_out_of_band_value_is_nonconforming(self):
        self.assertEqual(
            categorize_parameter("antenna-boresight-height-m", 1.30),
            CATEGORY_NONCONFORMING,
        )

    def test_declared_deviation_is_categorized_separately(self):
        self.assertEqual(
            categorize_parameter(
                "antenna-boresight-height-m",
                1.30,
                declared_deviations=["antenna-boresight-height-m"],
            ),
            CATEGORY_DECLARED_DEVIATION,
        )

    def test_non_collection_declaration_rejected(self):
        with self.assertRaises(ValueError):
            categorize_parameter(
                "antenna-boresight-height-m", 1.30, declared_deviations="all"
            )


class TestNearField(unittest.TestCase):
    def test_boundary_at_thirty_megahertz(self):
        self.assertAlmostEqual(
            near_field_boundary_m(30.0e6), BOUNDARY_AT_30_MHZ_M, places=6
        )

    def test_boundary_at_one_gigahertz(self):
        self.assertAlmostEqual(
            near_field_boundary_m(1.0e9), BOUNDARY_AT_1_GHZ_M, places=6
        )

    def test_boundary_shrinks_with_frequency(self):
        self.assertGreater(near_field_boundary_m(30.0e6), near_field_boundary_m(1.0e9))

    def test_non_positive_frequency_rejected(self):
        with self.assertRaises(ValueError):
            near_field_boundary_m(0.0)

    def test_one_metre_at_thirty_megahertz_is_near_field(self):
        self.assertEqual(separation_regime(1.0, 30.0e6), REGIME_NEAR_FIELD)

    def test_one_metre_at_one_gigahertz_is_far_field(self):
        self.assertEqual(separation_regime(1.0, 1.0e9), REGIME_FAR_FIELD)

    def test_separation_on_the_boundary_is_reported_as_such(self):
        boundary = near_field_boundary_m(200.0e6)
        self.assertEqual(separation_regime(boundary, 200.0e6), REGIME_AT_BOUNDARY)

    def test_non_positive_separation_rejected(self):
        with self.assertRaises(ValueError):
            separation_regime(0.0, 30.0e6)


class TestPresentations(unittest.TestCase):
    def test_full_log_validates(self):
        self.assertEqual(len(validate_presentations(full_presentations())), 10)

    def test_empty_log_rejected(self):
        with self.assertRaises(ValueError):
            validate_presentations([])

    def test_repeated_presentation_rejected(self):
        log = full_presentations()
        log.append(log[0])
        with self.assertRaises(ValueError):
            validate_presentations(log)

    def test_malformed_entry_rejected(self):
        with self.assertRaises(ValueError):
            validate_presentations([("front",)])

    def test_full_log_has_no_gaps(self):
        self.assertEqual(missing_presentations(full_presentations()), ())

    def test_single_polarization_log_reports_every_missing_plane(self):
        log = [(face, "vertical") for face in UNIT_FACES]
        self.assertEqual(len(missing_presentations(log)), len(UNIT_FACES))

    def test_unpresented_face_is_reported(self):
        log = [entry for entry in full_presentations() if entry[0] != "top"]
        self.assertEqual(
            missing_presentations(log),
            (("top", "vertical"), ("top", "horizontal")),
        )


class TestBenchAssessment(unittest.TestCase):
    def test_clean_bench_conforms(self):
        report = assess_bench_layout(clean_bench(), full_presentations())
        self.assertEqual(report["verdict"], VERDICT_CONFORMING)
        self.assertEqual(report["findings"], [])

    def test_every_parameter_is_graded(self):
        report = assess_bench_layout(clean_bench(), full_presentations())
        self.assertEqual(len(report["parameters"]), len(BASELINE_PARAMETERS))

    def test_missing_parameter_is_refused(self):
        bench = clean_bench()
        del bench["antenna-boresight-height-m"]
        with self.assertRaises(ValueError):
            assess_bench_layout(bench, full_presentations())

    def test_non_mapping_measurements_refused(self):
        with self.assertRaises(ValueError):
            assess_bench_layout([("antenna-boresight-height-m", 1.0)], full_presentations())

    def test_out_of_band_separation_rejects_the_layout(self):
        bench = clean_bench()
        bench["antenna-to-unit-separation-m"] = 1.4
        report = assess_bench_layout(bench, full_presentations())
        self.assertEqual(report["verdict"], VERDICT_REJECTED)
        self.assertEqual(report["governing_parameter"], "antenna-to-unit-separation-m")

    def test_declared_deviation_is_a_limitation_not_a_finding(self):
        bench = clean_bench()
        bench["antenna-boresight-height-m"] = 1.3
        report = assess_bench_layout(
            bench,
            full_presentations(),
            declared_deviations=["antenna-boresight-height-m"],
        )
        self.assertEqual(report["verdict"], VERDICT_CONFORMING)
        self.assertEqual(len(report["limitations"]), 2)

    def test_unpresented_face_rejects_the_layout(self):
        log = [entry for entry in full_presentations() if entry[0] != "rear"]
        report = assess_bench_layout(clean_bench(), log)
        self.assertEqual(report["verdict"], VERDICT_REJECTED)
        self.assertEqual(len(report["presentation_gaps"]), 2)

    def test_near_field_separation_is_a_limitation(self):
        report = assess_bench_layout(clean_bench(), full_presentations())
        self.assertEqual(report["separation_regime"], REGIME_NEAR_FIELD)
        self.assertEqual(len(report["limitations"]), 1)

    def test_high_start_frequency_puts_the_bench_in_the_far_field(self):
        report = assess_bench_layout(
            clean_bench(), full_presentations(), lowest_frequency_hz=1.0e9
        )
        self.assertEqual(report["separation_regime"], REGIME_FAR_FIELD)
        self.assertEqual(report["limitations"], [])

    def test_a_wider_separation_moves_the_absorber_requirement(self):
        bench = clean_bench()
        bench["antenna-to-unit-separation-m"] = 3.0
        bench["absorber-to-antenna-clearance-m"] = 1.0
        report = assess_bench_layout(
            bench, full_presentations(), separation_m=3.0, lowest_frequency_hz=1.0e9
        )
        self.assertEqual(report["verdict"], VERDICT_REJECTED)
        self.assertEqual(
            report["governing_parameter"], "absorber-to-antenna-clearance-m"
        )

    def test_duplicate_parameter_spelling_refused(self):
        bench = clean_bench()
        bench["ANTENNA-BORESIGHT-HEIGHT-M"] = 1.0
        with self.assertRaises(ValueError):
            assess_bench_layout(bench, full_presentations())

    def test_bond_resistance_on_its_limit_still_conforms(self):
        bench = clean_bench()
        bench["unit-to-plane-bond-resistance-mohm"] = 2.5
        report = assess_bench_layout(
            bench, full_presentations(), lowest_frequency_hz=1.0e9
        )
        self.assertEqual(report["verdict"], VERDICT_CONFORMING)

    def test_boundary_is_echoed_back_on_the_report(self):
        report = assess_bench_layout(clean_bench(), full_presentations())
        self.assertAlmostEqual(
            report["near_field_boundary_m"], BOUNDARY_AT_30_MHZ_M, places=6
        )


if __name__ == "__main__":
    unittest.main()
