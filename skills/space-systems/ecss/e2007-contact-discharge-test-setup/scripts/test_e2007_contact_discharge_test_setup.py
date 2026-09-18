"""Contract tests for the clause 5.4.14.3 contact discharge setup logic."""

import math
import unittest

from e2007_contact_discharge_test_setup_logic import (
    AIR_DISCHARGE_POINT,
    CONFORMING,
    CONTACT_POINT,
    DECLARED_DEVIATION,
    NONCONFORMING,
    NOT_A_DISCHARGE_POINT,
    SLACK_NOTICE_M,
    VERDICT_CONFORMING,
    VERDICT_NONCONFORMING,
    VERDICT_WITH_DEVIATIONS,
    apply_setup_deltas,
    assess_contact_discharge_setup,
    band_margin,
    categorize_discharge_point,
    categorize_parameter,
    delivered_charge_c,
    governing_parameter,
    group_discharge_points,
    network_time_constant_s,
    nominal_peak_current_a,
    return_cable_slack_m,
    stored_energy_j,
    validate_band,
    validate_bench,
    validate_discharge_point,
)


BASELINE_BANDS = {
    "bond_resistance_ohm": (0.0, 0.01),
    "discharge_resistance_ohm": (313.5, 346.5),
    "generator_return_cable_length_m": (1.5, 2.5),
    "insulating_support_thickness_m": (0.04, 0.06),
    "return_cable_to_unit_separation_m": (0.2, 1.0),
    "storage_capacitance_f": (142.5e-12, 157.5e-12),
    "tip_approach_angle_deg": (80.0, 100.0),
}


def make_point(**overrides):
    """Return a well-formed contact-capable discharge point."""
    point = {
        "point_id": "chassis-face-A",
        "surface_finish": "bare-conductive",
        "surface_resistance_ohm": 0.05,
        "accessible": True,
        "intended_application": "contact",
    }
    point.update(overrides)
    return point


def make_bench(**overrides):
    """Return a well-formed realized contact discharge bench."""
    bench = {
        "generator_mode": "contact",
        "tip_type": "contact-tip",
        "charge_voltage_v": 4000.0,
        "discharge_resistance_ohm": 330.0,
        "storage_capacitance_f": 150e-12,
        "generator_return_cable_length_m": 2.0,
        "return_path_length_m": 1.6,
        "return_cable_to_unit_separation_m": 0.5,
        "insulating_support_thickness_m": 0.05,
        "bond_resistance_ohm": 0.004,
        "tip_approach_angle_deg": 90.0,
        "declared_deviations": (),
        "discharge_points": [
            make_point(point_id="chassis-face-A"),
            make_point(
                point_id="connector-shell-J3",
                surface_finish="conductive-plating",
                surface_resistance_ohm=0.2,
            ),
        ],
    }
    bench.update(overrides)
    return bench


class BandTests(unittest.TestCase):
    def test_band_pair_is_returned_as_floats(self):
        self.assertEqual(validate_band((1, 2), "b"), (1.0, 2.0))

    def test_inverted_band_rejected(self):
        with self.assertRaises(ValueError):
            validate_band((2.0, 1.0), "b")

    def test_collapsed_band_rejected(self):
        with self.assertRaises(ValueError):
            validate_band((1.0, 1.0), "b")

    def test_non_pair_band_rejected(self):
        with self.assertRaises(ValueError):
            validate_band([1.0, 2.0, 3.0], "b")

    def test_band_margin_is_centred_at_one_half(self):
        self.assertAlmostEqual(band_margin(1.5, (1.0, 2.0)), 0.5, places=9)

    def test_band_margin_is_negative_outside(self):
        self.assertAlmostEqual(band_margin(2.5, (1.0, 2.0)), -0.5, places=9)


class DeltaResolutionTests(unittest.TestCase):
    def test_baseline_passes_through_untouched(self):
        resolved = apply_setup_deltas(BASELINE_BANDS, None)
        self.assertEqual(resolved["tip_approach_angle_deg"], (80.0, 100.0))

    def test_delta_moves_one_edge(self):
        resolved = apply_setup_deltas(
            BASELINE_BANDS, {"return_cable_to_unit_separation_m": {"minimum_delta": 0.1}}
        )
        self.assertAlmostEqual(
            resolved["return_cable_to_unit_separation_m"][0], 0.3, places=9
        )

    def test_unknown_baseline_parameter_rejected(self):
        bands = dict(BASELINE_BANDS)
        bands["coupling_plane_distance_m"] = (0.1, 0.2)
        with self.assertRaises(ValueError):
            apply_setup_deltas(bands, None)

    def test_delta_on_unknown_parameter_rejected(self):
        with self.assertRaises(ValueError):
            apply_setup_deltas(BASELINE_BANDS, {"plane_span_m": {"minimum_delta": 0.1}})

    def test_delta_with_unknown_key_rejected(self):
        with self.assertRaises(ValueError):
            apply_setup_deltas(
                BASELINE_BANDS, {"tip_approach_angle_deg": {"nominal_delta": 1.0}}
            )

    def test_delta_that_closes_a_band_rejected(self):
        with self.assertRaises(ValueError):
            apply_setup_deltas(
                BASELINE_BANDS, {"tip_approach_angle_deg": {"minimum_delta": 25.0}}
            )


class DischargePointTests(unittest.TestCase):
    def test_conductive_accessible_point_is_contact_capable(self):
        self.assertEqual(categorize_discharge_point(make_point()), CONTACT_POINT)

    def test_painted_surface_becomes_an_air_point(self):
        point = make_point(surface_finish="painted", surface_resistance_ohm=1e9)
        self.assertEqual(categorize_discharge_point(point), AIR_DISCHARGE_POINT)

    def test_conductive_finish_with_high_resistance_becomes_air(self):
        point = make_point(surface_resistance_ohm=50.0)
        self.assertEqual(categorize_discharge_point(point), AIR_DISCHARGE_POINT)

    def test_inaccessible_point_is_not_a_discharge_point(self):
        self.assertEqual(
            categorize_discharge_point(make_point(accessible=False)),
            NOT_A_DISCHARGE_POINT,
        )

    def test_unknown_surface_finish_rejected(self):
        with self.assertRaises(ValueError):
            validate_discharge_point(make_point(surface_finish="brushed"))

    def test_negative_surface_resistance_rejected(self):
        with self.assertRaises(ValueError):
            validate_discharge_point(make_point(surface_resistance_ohm=-1.0))

    def test_blank_point_id_rejected(self):
        with self.assertRaises(ValueError):
            validate_discharge_point(make_point(point_id="   "))

    def test_non_boolean_accessible_rejected(self):
        with self.assertRaises(ValueError):
            validate_discharge_point(make_point(accessible="yes"))

    def test_duplicate_point_id_rejected(self):
        with self.assertRaises(ValueError):
            group_discharge_points([make_point(), make_point()])

    def test_empty_point_list_rejected(self):
        with self.assertRaises(ValueError):
            group_discharge_points([])


class NetworkTests(unittest.TestCase):
    def test_peak_current_is_voltage_over_resistance(self):
        self.assertAlmostEqual(nominal_peak_current_a(3300.0, 330.0), 10.0, places=9)

    def test_zero_resistance_rejected(self):
        with self.assertRaises(ValueError):
            nominal_peak_current_a(4000.0, 0.0)

    def test_time_constant_is_the_rc_product(self):
        self.assertAlmostEqual(
            network_time_constant_s(330.0, 150e-12), 4.95e-8, places=15
        )

    def test_stored_energy_matches_half_c_v_squared(self):
        self.assertAlmostEqual(stored_energy_j(150e-12, 4000.0), 1.2e-3, places=12)

    def test_delivered_charge_matches_c_v(self):
        self.assertAlmostEqual(delivered_charge_c(150e-12, 4000.0), 6.0e-7, places=15)

    def test_negative_capacitance_rejected(self):
        with self.assertRaises(ValueError):
            stored_energy_j(-150e-12, 4000.0)

    def test_slack_is_cable_minus_path(self):
        self.assertAlmostEqual(return_cable_slack_m(2.0, 1.6), 0.4, places=9)

    def test_slack_goes_negative_for_a_short_cable(self):
        self.assertLess(return_cable_slack_m(1.0, 1.6), 0.0)

    def test_zero_path_length_rejected(self):
        with self.assertRaises(ValueError):
            return_cable_slack_m(2.0, 0.0)


class ParameterGradingTests(unittest.TestCase):
    def test_value_inside_band_is_conforming(self):
        self.assertEqual(categorize_parameter(90.0, (80.0, 100.0)), CONFORMING)

    def test_value_exactly_on_the_edge_is_conforming(self):
        self.assertEqual(categorize_parameter(80.0, (80.0, 100.0)), CONFORMING)

    def test_undeclared_excursion_is_nonconforming(self):
        self.assertEqual(categorize_parameter(110.0, (80.0, 100.0)), NONCONFORMING)

    def test_declared_excursion_is_a_deviation(self):
        self.assertEqual(
            categorize_parameter(110.0, (80.0, 100.0), True), DECLARED_DEVIATION
        )

    def test_governing_parameter_is_the_tightest_one(self):
        bench = validate_bench(make_bench(tip_approach_angle_deg=81.0))
        self.assertEqual(
            governing_parameter(bench, BASELINE_BANDS), "tip_approach_angle_deg"
        )

    def test_governing_parameter_needs_the_realized_value(self):
        with self.assertRaises(ValueError):
            governing_parameter({"bond_resistance_ohm": 0.004}, BASELINE_BANDS)


class ValidateBenchTests(unittest.TestCase):
    def test_well_formed_bench_normalizes(self):
        bench = validate_bench(make_bench())
        self.assertEqual(bench["generator_mode"], "contact")
        self.assertEqual(bench["tip_type"], "contact-tip")
        self.assertEqual(len(bench["point_categories"]), 2)

    def test_unknown_generator_mode_rejected(self):
        with self.assertRaises(ValueError):
            validate_bench(make_bench(generator_mode="spark-gap"))

    def test_unknown_tip_type_rejected(self):
        with self.assertRaises(ValueError):
            validate_bench(make_bench(tip_type="blunt"))

    def test_boolean_charge_voltage_rejected(self):
        with self.assertRaises(ValueError):
            validate_bench(make_bench(charge_voltage_v=True))

    def test_non_finite_capacitance_rejected(self):
        with self.assertRaises(ValueError):
            validate_bench(make_bench(storage_capacitance_f=float("nan")))

    def test_negative_bond_resistance_rejected(self):
        with self.assertRaises(ValueError):
            validate_bench(make_bench(bond_resistance_ohm=-0.001))

    def test_zero_bond_resistance_accepted(self):
        self.assertEqual(validate_bench(make_bench(bond_resistance_ohm=0.0))[
            "bond_resistance_ohm"], 0.0)

    def test_approach_angle_over_half_turn_rejected(self):
        with self.assertRaises(ValueError):
            validate_bench(make_bench(tip_approach_angle_deg=200.0))

    def test_deviation_naming_an_ungraded_parameter_rejected(self):
        with self.assertRaises(ValueError):
            validate_bench(make_bench(declared_deviations=["plane_span_m"]))

    def test_string_deviation_list_rejected(self):
        with self.assertRaises(ValueError):
            validate_bench(make_bench(declared_deviations="bond_resistance_ohm"))

    def test_missing_discharge_points_rejected(self):
        bench = make_bench()
        del bench["discharge_points"]
        with self.assertRaises(ValueError):
            validate_bench(bench)


class AssessmentTests(unittest.TestCase):
    def test_clean_bench_is_conforming(self):
        result = assess_contact_discharge_setup(make_bench(), BASELINE_BANDS)
        self.assertEqual(result["verdict"], VERDICT_CONFORMING)
        self.assertEqual(result["findings"], [])

    def test_derived_network_quantities_are_reported(self):
        result = assess_contact_discharge_setup(make_bench(), BASELINE_BANDS)
        self.assertAlmostEqual(
            result["nominal_peak_current_a"], 4000.0 / 330.0, places=9
        )
        self.assertAlmostEqual(
            result["network_time_constant_s"], 330.0 * 150e-12, places=15
        )

    def test_air_tip_in_contact_mode_is_a_finding(self):
        result = assess_contact_discharge_setup(
            make_bench(tip_type="rounded-air-tip"), BASELINE_BANDS
        )
        self.assertEqual(result["verdict"], VERDICT_NONCONFORMING)
        self.assertTrue(any("contact application" in f for f in result["findings"]))

    def test_painted_point_declared_for_contact_is_a_finding(self):
        bench = make_bench(
            discharge_points=[
                make_point(
                    point_id="painted-lid",
                    surface_finish="painted",
                    surface_resistance_ohm=1e9,
                ),
                make_point(point_id="chassis-face-A"),
            ]
        )
        result = assess_contact_discharge_setup(bench, BASELINE_BANDS)
        self.assertEqual(result["verdict"], VERDICT_NONCONFORMING)
        self.assertTrue(any("painted-lid" in f for f in result["findings"]))

    def test_no_contact_capable_point_is_a_finding(self):
        bench = make_bench(
            discharge_points=[
                make_point(
                    point_id="painted-lid",
                    surface_finish="painted",
                    surface_resistance_ohm=1e9,
                    intended_application="air",
                )
            ]
        )
        result = assess_contact_discharge_setup(bench, BASELINE_BANDS)
        self.assertTrue(any("nothing for the contact mode" in f for f in result["findings"]))

    def test_short_return_cable_is_a_finding(self):
        bench = make_bench(generator_return_cable_length_m=1.5, return_path_length_m=2.0)
        result = assess_contact_discharge_setup(bench, BASELINE_BANDS)
        self.assertLess(result["return_cable_slack_m"], 0.0)
        self.assertTrue(any("return path" in f for f in result["findings"]))

    def test_undeclared_band_excursion_is_a_finding(self):
        bench = make_bench(bond_resistance_ohm=0.5)
        result = assess_contact_discharge_setup(bench, BASELINE_BANDS)
        self.assertEqual(result["categories"]["bond_resistance_ohm"], NONCONFORMING)
        self.assertEqual(result["verdict"], VERDICT_NONCONFORMING)

    def test_declared_excursion_becomes_a_limitation(self):
        bench = make_bench(
            bond_resistance_ohm=0.5, declared_deviations=["bond_resistance_ohm"]
        )
        result = assess_contact_discharge_setup(bench, BASELINE_BANDS)
        self.assertEqual(result["verdict"], VERDICT_WITH_DEVIATIONS)
        self.assertTrue(any("declared deviation" in n for n in result["limitations"]))

    def test_air_only_points_are_carried_as_a_limitation(self):
        bench = make_bench(
            discharge_points=[
                make_point(point_id="chassis-face-A"),
                make_point(
                    point_id="painted-lid",
                    surface_finish="painted",
                    surface_resistance_ohm=1e9,
                    intended_application="air",
                ),
            ]
        )
        result = assess_contact_discharge_setup(bench, BASELINE_BANDS)
        self.assertEqual(result["air_discharge_points"], ["painted-lid"])
        self.assertTrue(any("air only" in n for n in result["limitations"]))

    def test_large_slack_is_carried_as_a_limitation(self):
        bench = make_bench(
            generator_return_cable_length_m=2.5, return_path_length_m=1.0
        )
        result = assess_contact_discharge_setup(bench, BASELINE_BANDS)
        self.assertGreater(result["return_cable_slack_m"], SLACK_NOTICE_M)
        self.assertTrue(any("dressed away" in n for n in result["limitations"]))

    def test_delta_can_admit_a_bench_the_baseline_refuses(self):
        bench = make_bench(return_cable_to_unit_separation_m=1.4)
        strict = assess_contact_discharge_setup(bench, BASELINE_BANDS)
        self.assertEqual(strict["verdict"], VERDICT_NONCONFORMING)
        relaxed = assess_contact_discharge_setup(
            bench,
            BASELINE_BANDS,
            {"return_cable_to_unit_separation_m": {"maximum_delta": 0.5}},
        )
        self.assertEqual(relaxed["verdict"], VERDICT_CONFORMING)

    def test_energy_and_charge_scale_with_the_level(self):
        low = assess_contact_discharge_setup(
            make_bench(charge_voltage_v=2000.0), BASELINE_BANDS
        )
        high = assess_contact_discharge_setup(
            make_bench(charge_voltage_v=8000.0), BASELINE_BANDS
        )
        self.assertAlmostEqual(
            high["stored_energy_j"] / low["stored_energy_j"], 16.0, places=9
        )
        self.assertAlmostEqual(
            high["delivered_charge_c"] / low["delivered_charge_c"], 4.0, places=9
        )

    def test_result_carries_the_governing_parameter(self):
        result = assess_contact_discharge_setup(make_bench(), BASELINE_BANDS)
        self.assertIn(result["governing_parameter"], BASELINE_BANDS)

    def test_assessment_is_deterministic(self):
        first = assess_contact_discharge_setup(make_bench(), BASELINE_BANDS)
        second = assess_contact_discharge_setup(make_bench(), BASELINE_BANDS)
        self.assertEqual(first["verdict"], second["verdict"])
        self.assertEqual(first["findings"], second["findings"])
        self.assertEqual(first["limitations"], second["limitations"])

    def test_peak_current_stays_finite_for_every_graded_bench(self):
        result = assess_contact_discharge_setup(make_bench(), BASELINE_BANDS)
        self.assertTrue(math.isfinite(result["nominal_peak_current_a"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
