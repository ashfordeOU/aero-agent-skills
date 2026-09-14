#!/usr/bin/env python3
"""Contract test for the coverglass surface resistivity leaf (offline)."""

import copy
import math
import unittest

from e2008_coverglass_surface_resistivity_logic import (
    AMBIENT_HUMIDITY_BAND_PERCENT,
    CONCENTRIC_RING,
    FOUR_POINT_COLLINEAR,
    FOUR_POINT_THIN_FILM_FACTOR,
    KNOWN_CONDUCTIVE_COATINGS,
    KNOWN_NON_CONDUCTIVE_COATINGS,
    MAX_PROBE_SPAN_SHARE,
    OBLIGATION_MET,
    OBLIGATION_NOT_TRIGGERED,
    OBLIGATION_OUTSTANDING,
    REDUCTION_ROUTES,
    assess_surface_resistivity,
    concentric_ring_geometry_factor,
    conductive_layers,
    current_within_band,
    humidity_within_band,
    layer_is_conductive,
    measurement_required,
    missing_measurement_evidence,
    probe_span_within_specimen,
    reduce_site_readings,
    sheet_resistance_from_concentric_ring,
    sheet_resistance_from_four_point,
    site_spread_ratio,
)

BARE_STACK = (
    {"material": "magnesium-fluoride"},
    {"material": "tantalum-pentoxide"},
)

COATED_STACK = (
    {"material": "magnesium-fluoride"},
    {"material": "indium-tin-oxide"},
)

CURRENT_BAND = {"minimum_a": 1.0e-11, "maximum_a": 1.0e-4}

RING_SITES = (
    {
        "resistance_ohm": 1.1e7,
        "inner_diameter_mm": 10.0,
        "outer_diameter_mm": 20.0,
        "current_a": 1.0e-7,
    },
    {
        "resistance_ohm": 1.3e7,
        "inner_diameter_mm": 10.0,
        "outer_diameter_mm": 20.0,
        "current_a": 1.0e-7,
    },
)

COATED_CASE = {
    "coating_stack": COATED_STACK,
    "reduction_route": CONCENTRIC_RING,
    "site_readings": RING_SITES,
    "surface_resistivity_ceiling_ohm_per_square": 1.0e9,
    "ambient_humidity_percent": 45.0,
    "probe_current_band_a": CURRENT_BAND,
}

FOUR_POINT_CASE = {
    "coating_stack": COATED_STACK,
    "reduction_route": FOUR_POINT_COLLINEAR,
    "site_readings": (
        {"voltage_v": 0.5, "current_a": 1.0e-6},
        {"voltage_v": 0.55, "current_a": 1.0e-6},
    ),
    "surface_resistivity_ceiling_ohm_per_square": 1.0e7,
    "ambient_humidity_percent": 45.0,
    "probe_current_band_a": CURRENT_BAND,
    "probe_spacing_mm": 1.0,
    "probe_count": 4,
    "specimen_span_mm": 40.0,
}


def _coated(**overrides):
    case = copy.deepcopy(COATED_CASE)
    case.update(overrides)
    return case


def _four_point(**overrides):
    case = copy.deepcopy(FOUR_POINT_CASE)
    case.update(overrides)
    return case


class CoatingApplicabilityTests(unittest.TestCase):
    def test_a_transparent_conducting_oxide_layer_conducts(self):
        self.assertTrue(layer_is_conductive({"material": "indium-tin-oxide"}))

    def test_an_anti_reflection_layer_does_not_conduct(self):
        self.assertFalse(layer_is_conductive({"material": "magnesium-fluoride"}))

    def test_the_two_material_lists_do_not_overlap(self):
        self.assertEqual(
            set(KNOWN_CONDUCTIVE_COATINGS) & set(KNOWN_NON_CONDUCTIVE_COATINGS), set()
        )

    def test_an_explicit_declaration_overrides_the_material_lookup(self):
        self.assertTrue(
            layer_is_conductive(
                {"material": "magnesium-fluoride", "conductive": True}
            )
        )

    def test_an_uncharacterised_material_is_refused_not_read_as_insulating(self):
        with self.assertRaises(ValueError):
            layer_is_conductive({"material": "proprietary-front-coating"})

    def test_a_non_boolean_conductivity_flag_is_refused(self):
        with self.assertRaises(ValueError):
            layer_is_conductive({"material": "indium-tin-oxide", "conductive": "yes"})

    def test_a_layer_naming_no_material_is_refused(self):
        with self.assertRaises(ValueError):
            layer_is_conductive({})

    def test_a_bare_stack_owes_no_measurement(self):
        self.assertFalse(measurement_required(BARE_STACK))
        self.assertEqual(conductive_layers(BARE_STACK), ())

    def test_a_coated_stack_owes_a_measurement(self):
        self.assertTrue(measurement_required(COATED_STACK))
        self.assertEqual(conductive_layers(COATED_STACK), ("indium-tin-oxide",))

    def test_an_absent_stack_is_refused_rather_than_read_as_bare(self):
        with self.assertRaises(ValueError):
            measurement_required(None)

    def test_a_stack_that_is_not_a_sequence_is_refused(self):
        with self.assertRaises(ValueError):
            conductive_layers({"material": "indium-tin-oxide"})

    def test_an_empty_stack_owes_nothing(self):
        self.assertFalse(measurement_required(()))


class GeometryTests(unittest.TestCase):
    def test_the_ring_factor_follows_the_diameter_ratio(self):
        self.assertAlmostEqual(
            concentric_ring_geometry_factor(10.0, 20.0),
            2.0 * math.pi / math.log(2.0),
            places=12,
        )

    def test_a_wider_outer_electrode_lowers_the_ring_factor(self):
        near = concentric_ring_geometry_factor(10.0, 12.0)
        far = concentric_ring_geometry_factor(10.0, 40.0)
        self.assertGreater(near, far)

    def test_an_outer_electrode_inside_the_inner_one_is_refused(self):
        with self.assertRaises(ValueError):
            concentric_ring_geometry_factor(20.0, 10.0)

    def test_equal_electrode_diameters_are_refused(self):
        with self.assertRaises(ValueError):
            concentric_ring_geometry_factor(20.0, 20.0)

    def test_the_thin_film_factor_is_the_collinear_constant(self):
        self.assertAlmostEqual(
            FOUR_POINT_THIN_FILM_FACTOR, math.pi / math.log(2.0), places=12
        )

    def test_a_short_probe_array_fits_inside_the_specimen(self):
        self.assertTrue(probe_span_within_specimen(1.0, 4, 40.0))

    def test_a_probe_array_spanning_the_specimen_does_not_fit(self):
        self.assertFalse(probe_span_within_specimen(10.0, 4, 40.0))

    def test_a_span_landing_on_the_share_limit_still_fits(self):
        specimen = 40.0
        spacing = MAX_PROBE_SPAN_SHARE * specimen / 3.0
        self.assertTrue(probe_span_within_specimen(spacing, 4, specimen))

    def test_a_single_probe_cannot_form_a_span(self):
        with self.assertRaises(ValueError):
            probe_span_within_specimen(1.0, 1, 40.0)

    def test_a_fractional_probe_count_is_refused(self):
        with self.assertRaises(ValueError):
            probe_span_within_specimen(1.0, 3.5, 40.0)


class ReductionTests(unittest.TestCase):
    def test_a_ring_reading_is_the_resistance_times_its_factor(self):
        self.assertAlmostEqual(
            sheet_resistance_from_concentric_ring(1.0e7, 10.0, 20.0),
            1.0e7 * 2.0 * math.pi / math.log(2.0),
            places=3,
        )

    def test_a_four_point_reading_is_the_ratio_times_the_thin_film_factor(self):
        self.assertAlmostEqual(
            sheet_resistance_from_four_point(0.5, 1.0e-6),
            0.5 / 1.0e-6 * FOUR_POINT_THIN_FILM_FACTOR,
            places=6,
        )

    def test_a_fixture_specific_factor_overrides_the_default(self):
        self.assertAlmostEqual(
            sheet_resistance_from_four_point(0.5, 1.0e-6, 4.0),
            2.0e6,
            places=6,
        )

    def test_a_zero_drive_current_cannot_form_a_sheet_resistance(self):
        with self.assertRaises(ValueError):
            sheet_resistance_from_four_point(0.5, 0.0)

    def test_a_negative_probe_voltage_is_refused(self):
        with self.assertRaises(ValueError):
            sheet_resistance_from_four_point(-0.5, 1.0e-6)

    def test_every_route_reduces_a_well_formed_site(self):
        for route in REDUCTION_ROUTES:
            self.assertIn(route, (CONCENTRIC_RING, FOUR_POINT_COLLINEAR))

    def test_an_unknown_reduction_route_is_refused(self):
        with self.assertRaises(ValueError):
            reduce_site_readings(RING_SITES, "two-terminal-ohmmeter")

    def test_an_empty_site_list_is_refused(self):
        with self.assertRaises(ValueError):
            reduce_site_readings((), CONCENTRIC_RING)

    def test_the_spread_is_the_worst_site_over_the_best(self):
        self.assertAlmostEqual(site_spread_ratio((2.0, 4.0)), 2.0, places=12)

    def test_an_even_coating_has_a_unit_spread(self):
        self.assertAlmostEqual(site_spread_ratio((3.0, 3.0, 3.0)), 1.0, places=12)


class AmbientTests(unittest.TestCase):
    def test_a_mid_band_ambient_holds(self):
        self.assertTrue(humidity_within_band(45.0))

    def test_an_ambient_on_the_band_edge_still_holds(self):
        low, high = AMBIENT_HUMIDITY_BAND_PERCENT
        self.assertTrue(humidity_within_band(low))
        self.assertTrue(humidity_within_band(high))

    def test_a_dry_bench_falls_outside_the_band(self):
        self.assertFalse(humidity_within_band(12.0))

    def test_a_negative_humidity_is_refused(self):
        with self.assertRaises(ValueError):
            humidity_within_band(-5.0)

    def test_a_drive_current_inside_the_electrometer_band_holds(self):
        self.assertTrue(current_within_band(1.0e-7, CURRENT_BAND))

    def test_a_drive_current_above_the_electrometer_band_does_not_hold(self):
        self.assertFalse(current_within_band(1.0e-2, CURRENT_BAND))

    def test_an_inverted_current_band_is_refused(self):
        with self.assertRaises(ValueError):
            current_within_band(1.0e-7, {"minimum_a": 1.0e-4, "maximum_a": 1.0e-11})


class ObligationTests(unittest.TestCase):
    def test_a_bare_coverglass_does_not_trigger_the_clause(self):
        result = assess_surface_resistivity({"coating_stack": BARE_STACK})
        self.assertEqual(result["verdict"], OBLIGATION_NOT_TRIGGERED)
        self.assertFalse(result["measurement_required"])
        self.assertTrue(result["accepted"])

    def test_a_coated_coverglass_with_no_record_leaves_the_obligation_open(self):
        result = assess_surface_resistivity({"coating_stack": COATED_STACK})
        self.assertEqual(result["verdict"], OBLIGATION_OUTSTANDING)
        self.assertTrue(result["measurement_required"])
        self.assertFalse(result["accepted"])
        self.assertTrue(any("is owed" in f for f in result["findings"]))

    def test_a_complete_record_is_missing_nothing(self):
        self.assertEqual(missing_measurement_evidence(COATED_CASE), ())

    def test_a_record_without_a_ceiling_is_incomplete(self):
        case = _coated()
        del case["surface_resistivity_ceiling_ohm_per_square"]
        self.assertEqual(
            missing_measurement_evidence(case),
            ("surface_resistivity_ceiling_ohm_per_square",),
        )

    def test_a_case_that_is_not_a_mapping_is_refused(self):
        with self.assertRaises(ValueError):
            assess_surface_resistivity("indium-tin-oxide")


class AssessmentTests(unittest.TestCase):
    def test_a_sound_ring_record_satisfies_the_obligation(self):
        result = assess_surface_resistivity(COATED_CASE)
        self.assertEqual(result["verdict"], OBLIGATION_MET)
        self.assertTrue(result["accepted"])
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["conductive_layers"], ("indium-tin-oxide",))

    def test_a_sound_four_point_record_satisfies_the_obligation(self):
        result = assess_surface_resistivity(FOUR_POINT_CASE)
        self.assertEqual(result["verdict"], OBLIGATION_MET)
        self.assertEqual(result["reduction_route"], FOUR_POINT_COLLINEAR)

    def test_the_worst_site_is_the_one_the_ceiling_is_applied_to(self):
        result = assess_surface_resistivity(COATED_CASE)
        self.assertAlmostEqual(
            result["worst_sheet_resistance_ohm_per_square"],
            max(result["site_sheet_resistance_ohm_per_square"]),
            places=6,
        )

    def test_a_site_over_the_ceiling_is_a_finding(self):
        result = assess_surface_resistivity(
            _coated(surface_resistivity_ceiling_ohm_per_square=1.0e6)
        )
        self.assertEqual(result["verdict"], OBLIGATION_OUTSTANDING)
        self.assertTrue(any("ceiling" in f for f in result["findings"]))

    def test_a_reading_landing_on_the_ceiling_is_accepted(self):
        result = assess_surface_resistivity(COATED_CASE)
        on_limit = result["worst_sheet_resistance_ohm_per_square"]
        again = assess_surface_resistivity(
            _coated(surface_resistivity_ceiling_ohm_per_square=on_limit)
        )
        self.assertEqual(again["verdict"], OBLIGATION_MET)

    def test_a_dry_bench_is_a_finding_against_the_ambient_band(self):
        result = assess_surface_resistivity(_coated(ambient_humidity_percent=8.0))
        self.assertEqual(result["verdict"], OBLIGATION_OUTSTANDING)
        self.assertTrue(any("ambient humidity" in f for f in result["findings"]))

    def test_a_drive_current_off_the_electrometer_band_is_a_finding(self):
        noisy = (
            dict(RING_SITES[0], current_a=1.0e-2),
            RING_SITES[1],
        )
        result = assess_surface_resistivity(_coated(site_readings=noisy))
        self.assertEqual(result["verdict"], OBLIGATION_OUTSTANDING)
        self.assertTrue(any("electrometer band" in f for f in result["findings"]))

    def test_an_oversized_probe_array_is_a_finding_on_the_four_point_route(self):
        result = assess_surface_resistivity(_four_point(probe_spacing_mm=12.0))
        self.assertEqual(result["verdict"], OBLIGATION_OUTSTANDING)
        self.assertTrue(any("thin-film correction" in f for f in result["findings"]))

    def test_an_uneven_coating_shows_in_the_site_spread(self):
        uneven = (
            RING_SITES[0],
            dict(RING_SITES[1], resistance_ohm=4.4e7),
        )
        result = assess_surface_resistivity(_coated(site_readings=uneven))
        self.assertGreater(result["site_spread_ratio"], 3.0)

    def test_an_uncharacterised_layer_stops_the_whole_judgement(self):
        with self.assertRaises(ValueError):
            assess_surface_resistivity(
                _coated(coating_stack=({"material": "proprietary-front-coating"},))
            )

    def test_several_defects_are_all_reported_not_just_the_first(self):
        result = assess_surface_resistivity(
            _coated(
                surface_resistivity_ceiling_ohm_per_square=1.0e6,
                ambient_humidity_percent=8.0,
            )
        )
        self.assertEqual(result["verdict"], OBLIGATION_OUTSTANDING)
        self.assertGreaterEqual(len(result["findings"]), 2)

    def test_a_bare_stack_reports_no_sites_and_no_worst_value(self):
        result = assess_surface_resistivity({"coating_stack": BARE_STACK})
        self.assertEqual(result["site_sheet_resistance_ohm_per_square"], ())
        self.assertIsNone(result["worst_sheet_resistance_ohm_per_square"])


if __name__ == "__main__":
    unittest.main()
