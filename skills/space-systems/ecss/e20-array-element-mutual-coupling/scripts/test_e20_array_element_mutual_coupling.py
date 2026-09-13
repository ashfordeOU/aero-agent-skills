#!/usr/bin/env python3
"""Contract test for the clause 7.2.2.2.3 mutual-coupling leaf.

stdlib unittest, offline, deterministic. Run: python3 test_e20_array_element_mutual_coupling.py
"""

import math
import unittest

from e20_array_element_mutual_coupling_logic import (
    COUPLING_FLOOR_DB,
    MAX_COUPLING_DB,
    _le,
    active_reflection_coefficient,
    active_standing_wave_ratio,
    aperture_efficiency,
    aperture_efficiency_loss_db,
    assess_mutual_coupling,
    build_coupling_matrix,
    categorize_coupling_regime,
    coupling_coefficient,
    coupling_magnitude_db,
    edge_element_ids,
    excitation_error_rms,
    neighbour_count,
    pair_geometry,
    realized_excitations,
    scan_blindness_screen,
    scan_excitations,
    sidelobe_level_penalty_db,
)


def line_array(count, spacing):
    return [
        {"id": "e%d" % (i + 1), "x_wavelengths": i * spacing, "y_wavelengths": 0.0}
        for i in range(count)
    ]


class CouplingMagnitudeTests(unittest.TestCase):
    def test_reference_spacing_h_plane(self):
        self.assertAlmostEqual(coupling_magnitude_db(0.5, "h-plane"), -18.0, places=9)

    def test_e_plane_couples_more_than_h_plane(self):
        self.assertAlmostEqual(coupling_magnitude_db(0.5, "e-plane"), -15.0, places=9)

    def test_diagonal_couples_less_than_h_plane(self):
        self.assertAlmostEqual(coupling_magnitude_db(0.5, "diagonal"), -21.0, places=9)

    def test_doubling_the_spacing_costs_six_db(self):
        near = coupling_magnitude_db(0.5, "h-plane")
        far = coupling_magnitude_db(1.0, "h-plane")
        self.assertAlmostEqual(near - far, 20.0 * math.log10(2.0), places=9)

    def test_surface_wave_decay_term_lowers_coupling(self):
        plain = coupling_magnitude_db(1.0, "h-plane")
        decayed = coupling_magnitude_db(1.0, "h-plane", extra_decay_db=6.0)
        self.assertAlmostEqual(plain - decayed, 3.0, places=9)

    def test_far_pair_saturates_at_the_floor(self):
        self.assertAlmostEqual(coupling_magnitude_db(1.0e6), COUPLING_FLOOR_DB, places=9)

    def test_very_close_pair_saturates_at_the_cap(self):
        self.assertAlmostEqual(coupling_magnitude_db(0.005), MAX_COUPLING_DB, places=9)

    def test_zero_spacing_rejected(self):
        with self.assertRaises(ValueError):
            coupling_magnitude_db(0.0)

    def test_negative_spacing_rejected(self):
        with self.assertRaises(ValueError):
            coupling_magnitude_db(-0.5)

    def test_unknown_plane_rejected(self):
        with self.assertRaises(ValueError):
            coupling_magnitude_db(0.5, "k-plane")

    def test_negative_decay_rejected(self):
        with self.assertRaises(ValueError):
            coupling_magnitude_db(0.5, "h-plane", extra_decay_db=-1.0)

    def test_non_numeric_spacing_rejected(self):
        with self.assertRaises(ValueError):
            coupling_magnitude_db("half")

    def test_coefficient_magnitude_and_phase(self):
        term = coupling_coefficient(0.5, "e-plane")
        self.assertAlmostEqual(abs(term), 10.0 ** (-15.0 / 20.0), places=9)
        self.assertAlmostEqual(term.real, -10.0 ** (-15.0 / 20.0), places=9)
        self.assertAlmostEqual(term.imag, 0.0, places=9)


class GeometryTests(unittest.TestCase):
    def test_pair_along_x_is_an_e_plane_pair(self):
        spacing, plane = pair_geometry(
            {"id": "a", "x_wavelengths": 0.0, "y_wavelengths": 0.0},
            {"id": "b", "x_wavelengths": 0.5, "y_wavelengths": 0.0},
        )
        self.assertAlmostEqual(spacing, 0.5, places=9)
        self.assertEqual(plane, "e-plane")

    def test_pair_along_y_is_an_h_plane_pair(self):
        spacing, plane = pair_geometry(
            {"id": "a", "x_wavelengths": 0.0, "y_wavelengths": 0.0},
            {"id": "b", "x_wavelengths": 0.0, "y_wavelengths": 0.7},
        )
        self.assertAlmostEqual(spacing, 0.7, places=9)
        self.assertEqual(plane, "h-plane")

    def test_offset_pair_is_a_diagonal_pair(self):
        spacing, plane = pair_geometry(
            {"id": "a", "x_wavelengths": 0.0, "y_wavelengths": 0.0},
            {"id": "b", "x_wavelengths": 0.5, "y_wavelengths": 0.5},
        )
        self.assertAlmostEqual(spacing, math.sqrt(0.5), places=9)
        self.assertEqual(plane, "diagonal")

    def test_coincident_radiators_rejected(self):
        with self.assertRaises(ValueError):
            pair_geometry(
                {"id": "a", "x_wavelengths": 1.0, "y_wavelengths": 1.0},
                {"id": "b", "x_wavelengths": 1.0, "y_wavelengths": 1.0},
            )

    def test_non_mapping_element_rejected(self):
        with self.assertRaises(ValueError):
            pair_geometry(("a", 0.0, 0.0), {"id": "b", "x_wavelengths": 1.0, "y_wavelengths": 0.0})

    def test_missing_coordinate_rejected(self):
        with self.assertRaises(ValueError):
            pair_geometry({"id": "a", "x_wavelengths": 0.0}, {"id": "b", "x_wavelengths": 1.0})


class CouplingMatrixTests(unittest.TestCase):
    def test_matrix_covers_every_ordered_pair(self):
        matrix = build_coupling_matrix(line_array(4, 0.6))
        self.assertEqual(len(matrix), 4 * 3)

    def test_matrix_is_reciprocal_in_magnitude(self):
        matrix = build_coupling_matrix(line_array(3, 0.6))
        self.assertAlmostEqual(abs(matrix[("e1", "e3")]), abs(matrix[("e3", "e1")]), places=12)

    def test_nearest_pair_couples_hardest(self):
        matrix = build_coupling_matrix(line_array(3, 0.6))
        self.assertGreater(abs(matrix[("e1", "e2")]), abs(matrix[("e1", "e3")]))

    def test_single_radiator_rejected(self):
        with self.assertRaises(ValueError):
            build_coupling_matrix(line_array(1, 0.6))

    def test_duplicate_radiator_id_rejected(self):
        elements = line_array(2, 0.6)
        elements[1]["id"] = "e1"
        with self.assertRaises(ValueError):
            build_coupling_matrix(elements)

    def test_missing_radiator_id_rejected(self):
        elements = line_array(2, 0.6)
        del elements[0]["id"]
        with self.assertRaises(ValueError):
            build_coupling_matrix(elements)

    def test_non_list_lattice_rejected(self):
        with self.assertRaises(ValueError):
            build_coupling_matrix("e1,e2")


class RegimeTests(unittest.TestCase):
    def test_strong_regime(self):
        self.assertEqual(categorize_coupling_regime(-8.0), "strong")

    def test_strong_regime_boundary_is_inclusive(self):
        self.assertEqual(categorize_coupling_regime(-12.0), "strong")

    def test_moderate_regime(self):
        self.assertEqual(categorize_coupling_regime(-15.0), "moderate")

    def test_weak_regime(self):
        self.assertEqual(categorize_coupling_regime(-25.0), "weak")

    def test_negligible_regime(self):
        self.assertEqual(categorize_coupling_regime(-40.0), "negligible")

    def test_active_pair_rejected(self):
        with self.assertRaises(ValueError):
            categorize_coupling_regime(1.0)

    def test_non_numeric_regime_input_rejected(self):
        with self.assertRaises(ValueError):
            categorize_coupling_regime(None)


class NeighbourhoodTests(unittest.TestCase):
    def test_neighbour_count_inside_radius(self):
        elements = line_array(3, 0.5)
        self.assertEqual(neighbour_count(elements, "e2", 0.5), 2)

    def test_radius_boundary_counts_the_pair(self):
        elements = line_array(2, 0.1 + 0.2)
        self.assertEqual(neighbour_count(elements, "e1", 0.3), 1)

    def test_unknown_radiator_rejected(self):
        with self.assertRaises(ValueError):
            neighbour_count(line_array(3, 0.5), "e9", 1.0)

    def test_zero_radius_rejected(self):
        with self.assertRaises(ValueError):
            neighbour_count(line_array(3, 0.5), "e1", 0.0)

    def test_edge_radiators_identified(self):
        self.assertEqual(edge_element_ids(line_array(3, 0.5), 0.5), ["e1", "e3"])


class ActiveImpedanceTests(unittest.TestCase):
    def test_two_element_active_reflection(self):
        elements = line_array(2, 0.5)
        matrix = build_coupling_matrix(elements)
        gamma = active_reflection_coefficient("e1", {"e1": 1.0, "e2": 1.0}, matrix)
        self.assertAlmostEqual(gamma.real, -(10.0 ** (-15.0 / 20.0)), places=9)

    def test_self_reflection_adds_to_the_active_term(self):
        elements = line_array(2, 0.5)
        matrix = build_coupling_matrix(elements)
        bare = active_reflection_coefficient("e1", {"e1": 1.0, "e2": 1.0}, matrix)
        loaded = active_reflection_coefficient(
            "e1", {"e1": 1.0, "e2": 1.0}, matrix, self_reflection=0.05
        )
        self.assertAlmostEqual(loaded.real - bare.real, 0.05, places=9)

    def test_null_excitation_rejected(self):
        elements = line_array(2, 0.5)
        matrix = build_coupling_matrix(elements)
        with self.assertRaises(ValueError):
            active_reflection_coefficient("e1", {"e1": 0.0, "e2": 1.0}, matrix)

    def test_missing_excitation_rejected(self):
        elements = line_array(2, 0.5)
        matrix = build_coupling_matrix(elements)
        with self.assertRaises(ValueError):
            active_reflection_coefficient("e1", {"e1": 1.0}, matrix)

    def test_matched_radiator_has_unit_standing_wave_ratio(self):
        self.assertAlmostEqual(active_standing_wave_ratio(0.0), 1.0, places=12)

    def test_standing_wave_ratio_value(self):
        self.assertAlmostEqual(active_standing_wave_ratio(0.5), 3.0, places=12)

    def test_total_reflection_rejected(self):
        with self.assertRaises(ValueError):
            active_standing_wave_ratio(1.0)

    def test_reflection_above_unity_rejected(self):
        with self.assertRaises(ValueError):
            active_standing_wave_ratio(1.4)


class ExcitationTests(unittest.TestCase):
    def test_broadside_excitations_are_in_phase(self):
        elements = line_array(3, 0.5)
        out = scan_excitations(elements, {"e1": 1.0, "e2": 1.0, "e3": 1.0}, 0.0)
        for value in out.values():
            self.assertAlmostEqual(value.imag, 0.0, places=12)
            self.assertAlmostEqual(value.real, 1.0, places=12)

    def test_steered_excitation_carries_a_progressive_phase(self):
        elements = [
            {"id": "e1", "x_wavelengths": 0.0, "y_wavelengths": 0.0},
            {"id": "e2", "x_wavelengths": 1.0, "y_wavelengths": 0.0},
        ]
        out = scan_excitations(elements, {"e1": 1.0, "e2": 1.0}, 30.0)
        self.assertAlmostEqual(out["e2"].real, -1.0, places=9)

    def test_scan_beyond_the_hemisphere_rejected(self):
        with self.assertRaises(ValueError):
            scan_excitations(line_array(2, 0.5), {"e1": 1.0, "e2": 1.0}, 120.0)

    def test_negative_amplitude_rejected(self):
        with self.assertRaises(ValueError):
            scan_excitations(line_array(2, 0.5), {"e1": -1.0, "e2": 1.0}, 0.0)

    def test_missing_amplitude_rejected(self):
        with self.assertRaises(ValueError):
            scan_excitations(line_array(2, 0.5), {"e1": 1.0}, 0.0)

    def test_realized_excitation_absorbs_the_coupled_term(self):
        elements = line_array(2, 0.5)
        matrix = build_coupling_matrix(elements)
        realized = realized_excitations({"e1": 1.0, "e2": 1.0}, matrix)
        self.assertAlmostEqual(realized["e1"].real, 1.0 - 10.0 ** (-15.0 / 20.0), places=9)

    def test_realized_excitation_rejects_empty_set(self):
        with self.assertRaises(ValueError):
            realized_excitations({}, {})


class ApertureConsequenceTests(unittest.TestCase):
    def test_uniform_taper_is_fully_efficient(self):
        self.assertAlmostEqual(aperture_efficiency({"a": 1.0, "b": 1.0, "c": 1.0}), 1.0, places=12)

    def test_tapered_set_is_less_efficient(self):
        self.assertLess(aperture_efficiency({"a": 1.0, "b": 0.2}), 1.0)

    def test_empty_excitation_set_rejected(self):
        with self.assertRaises(ValueError):
            aperture_efficiency({})

    def test_powerless_excitation_set_rejected(self):
        with self.assertRaises(ValueError):
            aperture_efficiency({"a": 0.0, "b": 0.0})

    def test_uniform_coupling_costs_no_taper_efficiency(self):
        elements = line_array(2, 0.5)
        matrix = build_coupling_matrix(elements)
        commanded = {"e1": 1.0, "e2": 1.0}
        realized = realized_excitations(commanded, matrix)
        self.assertAlmostEqual(aperture_efficiency_loss_db(commanded, realized), 0.0, places=9)

    def test_excitation_error_rms_value(self):
        elements = line_array(2, 0.5)
        matrix = build_coupling_matrix(elements)
        commanded = {"e1": 1.0, "e2": 1.0}
        realized = realized_excitations(commanded, matrix)
        self.assertAlmostEqual(
            excitation_error_rms(commanded, realized), 10.0 ** (-15.0 / 20.0), places=9
        )

    def test_excitation_error_rms_rejects_mismatched_sets(self):
        with self.assertRaises(ValueError):
            excitation_error_rms({"e1": 1.0}, {"e2": 1.0})

    def test_excitation_error_rms_rejects_powerless_reference(self):
        with self.assertRaises(ValueError):
            excitation_error_rms({"e1": 0.0}, {"e1": 0.1})

    def test_no_error_means_no_sidelobe_penalty(self):
        self.assertAlmostEqual(sidelobe_level_penalty_db(0.0, 16, -25.0), 0.0, places=12)

    def test_sidelobe_penalty_value(self):
        penalty = sidelobe_level_penalty_db(0.1, 10, -25.0)
        expected = 10.0 * math.log10((10.0 ** -2.5 + 0.001) / 10.0 ** -2.5)
        self.assertAlmostEqual(penalty, expected, places=9)

    def test_sidelobe_penalty_rejects_negative_error(self):
        with self.assertRaises(ValueError):
            sidelobe_level_penalty_db(-0.1, 10, -25.0)

    def test_sidelobe_penalty_rejects_lone_radiator(self):
        with self.assertRaises(ValueError):
            sidelobe_level_penalty_db(0.1, 1, -25.0)

    def test_sidelobe_penalty_rejects_non_integer_count(self):
        with self.assertRaises(ValueError):
            sidelobe_level_penalty_db(0.1, 10.5, -25.0)

    def test_sidelobe_penalty_rejects_peak_level_design(self):
        with self.assertRaises(ValueError):
            sidelobe_level_penalty_db(0.1, 10, 0.0)


class ScanScreenTests(unittest.TestCase):
    def test_screen_reports_one_record_per_angle(self):
        elements = line_array(4, 0.6)
        matrix = build_coupling_matrix(elements)
        amplitudes = {element["id"]: 1.0 for element in elements}
        records = scan_blindness_screen(elements, amplitudes, matrix, [0.0, 30.0, 60.0])
        self.assertEqual(len(records), 3)
        self.assertEqual(records[1]["scan_theta_deg"], 30.0)

    def test_loose_lattice_is_not_blind(self):
        elements = line_array(4, 0.6)
        matrix = build_coupling_matrix(elements)
        amplitudes = {element["id"]: 1.0 for element in elements}
        records = scan_blindness_screen(elements, amplitudes, matrix, [0.0, 45.0])
        self.assertFalse(any(record["blind"] for record in records))

    def test_tight_lattice_is_flagged_blind(self):
        elements = line_array(6, 0.05)
        matrix = build_coupling_matrix(elements)
        amplitudes = {element["id"]: 1.0 for element in elements}
        records = scan_blindness_screen(elements, amplitudes, matrix, [0.0])
        self.assertTrue(records[0]["blind"])

    def test_empty_angle_sweep_rejected(self):
        elements = line_array(3, 0.6)
        matrix = build_coupling_matrix(elements)
        with self.assertRaises(ValueError):
            scan_blindness_screen(elements, {"e1": 1.0, "e2": 1.0, "e3": 1.0}, matrix, [])

    def test_blindness_threshold_outside_range_rejected(self):
        elements = line_array(3, 0.6)
        matrix = build_coupling_matrix(elements)
        with self.assertRaises(ValueError):
            scan_blindness_screen(
                elements, {"e1": 1.0, "e2": 1.0, "e3": 1.0}, matrix, [0.0], blindness_gamma=1.0
            )


class AssessmentTests(unittest.TestCase):
    def compliant_config(self):
        return {
            "elements": line_array(6, 1.5),
            "design_sidelobe_db": -20.0,
            "neighbour_radius_wavelengths": 1.6,
            "scan_angles_deg": [0.0, 30.0],
        }

    def test_loose_lattice_is_compliant(self):
        result = assess_mutual_coupling(self.compliant_config())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_assessment_reports_the_worst_pair(self):
        result = assess_mutual_coupling(self.compliant_config())
        self.assertIn(result["worst_pair"], result["pair_coupling_db"])
        self.assertAlmostEqual(
            result["worst_pair_coupling_db"],
            max(result["pair_coupling_db"].values()),
            places=12,
        )

    def test_assessment_categorizes_every_pair(self):
        result = assess_mutual_coupling(self.compliant_config())
        self.assertEqual(set(result["pair_regimes"]), set(result["pair_coupling_db"]))
        for regime in result["pair_regimes"].values():
            self.assertIn(regime, ("strong", "moderate", "weak", "negligible"))

    def test_assessment_lists_the_edge_radiators(self):
        result = assess_mutual_coupling(self.compliant_config())
        self.assertEqual(result["edge_elements"], ["e1", "e6"])

    def test_tight_lattice_raises_findings(self):
        result = assess_mutual_coupling({"elements": line_array(2, 0.4)})
        self.assertFalse(result["compliant"])
        self.assertTrue(any("couples at" in finding for finding in result["findings"]))

    def test_tightened_allocation_turns_a_pass_into_a_finding(self):
        config = self.compliant_config()
        config["limits"] = {"max_pair_coupling_db": -60.0}
        result = assess_mutual_coupling(config)
        self.assertFalse(result["compliant"])

    def test_unknown_allocation_key_rejected(self):
        config = self.compliant_config()
        config["limits"] = {"max_coupling": -30.0}
        with self.assertRaises(ValueError):
            assess_mutual_coupling(config)

    def test_lattice_of_one_rejected(self):
        with self.assertRaises(ValueError):
            assess_mutual_coupling({"elements": line_array(1, 0.5)})

    def test_non_mapping_config_rejected(self):
        with self.assertRaises(ValueError):
            assess_mutual_coupling(["e1", "e2"])

    def test_total_self_reflection_rejected(self):
        config = self.compliant_config()
        config["self_reflection"] = 1.0
        with self.assertRaises(ValueError):
            assess_mutual_coupling(config)

    def test_scan_sweep_is_carried_into_the_result(self):
        result = assess_mutual_coupling(self.compliant_config())
        self.assertEqual(len(result["scan_blindness"]), 2)


class ToleranceTests(unittest.TestCase):
    def test_representation_error_does_not_break_an_equal_comparison(self):
        self.assertTrue(_le(0.1 + 0.2, 0.3))

    def test_a_real_exceedance_is_still_caught(self):
        self.assertFalse(_le(0.31, 0.3))


if __name__ == "__main__":
    unittest.main()
