#!/usr/bin/env python3
"""Gate 3 contract test for the ECSS-E-ST-20C clause 7.2.1.2.2 antenna
engineering process steps leaf. Stdlib unittest, offline, deterministic."""

import unittest

import e20_antenna_engineering_process_steps_logic as ap


def nominal_project():
    """A geostationary spot-beam project standing at the design decision."""
    return {
        "completed_steps": list(ap.PROCESS_STEPS[:-1]),
        "available_inputs": ["selected-antenna-concept", "verification-approach"],
        "required_radiated_power_dbw": 44.0,
        "transmitter_power_dbw": 13.0,
        "feeder_loss_db": 1.0,
        "orbit_altitude_m": 35786.0e3,
        "coverage_radius_m": 1000.0e3,
    }


class StepValidationTests(unittest.TestCase):
    def test_canonical_step_is_accepted(self):
        self.assertEqual(
            ap.validate_process_step("antenna-concept-selection"),
            "antenna-concept-selection",
        )

    def test_underscores_and_case_are_normalised(self):
        self.assertEqual(
            ap.validate_process_step("  Antenna_Design_Decision "),
            "antenna-design-decision",
        )

    def test_unrecognised_step_is_rejected(self):
        with self.assertRaises(ValueError):
            ap.validate_process_step("antenna-manufacturing")

    def test_blank_step_is_rejected(self):
        with self.assertRaises(ValueError):
            ap.validate_process_step("   ")

    def test_non_string_step_is_rejected(self):
        with self.assertRaises(ValueError):
            ap.validate_process_step(3)

    def test_sequence_positions_run_from_the_analysis_to_the_decision(self):
        self.assertEqual(ap.process_step_index("mission-transmission-reception-analysis"), 0)
        self.assertEqual(
            ap.process_step_index("antenna-design-decision"), len(ap.PROCESS_STEPS) - 1
        )

    def test_every_step_declares_its_entry_data(self):
        for step in ap.PROCESS_STEPS:
            self.assertIn(step, ap.STEP_ENTRY_DATA)
            self.assertTrue(ap.STEP_ENTRY_DATA[step])

    def test_entry_data_names_are_registry_shaped(self):
        for names in ap.STEP_ENTRY_DATA.values():
            for name in names:
                self.assertEqual(name, name.strip().lower())
                self.assertNotIn(" ", name)


class OrderTests(unittest.TestCase):
    def test_sequential_completion_is_in_order(self):
        review = ap.check_step_order(list(ap.PROCESS_STEPS[:3]))
        self.assertTrue(review["ordered"])
        self.assertEqual(review["findings"], [])

    def test_a_gap_in_the_sequence_is_reported(self):
        review = ap.check_step_order(
            ["mission-transmission-reception-analysis", "antenna-concept-selection"]
        )
        self.assertFalse(review["ordered"])
        self.assertEqual(len(review["findings"]), 2)

    def test_nothing_completed_is_trivially_in_order(self):
        self.assertTrue(ap.check_step_order([])["ordered"])

    def test_everything_completed_is_in_order(self):
        self.assertTrue(ap.check_step_order(list(ap.PROCESS_STEPS))["ordered"])

    def test_a_set_of_steps_is_accepted(self):
        review = ap.check_step_order({"mission-transmission-reception-analysis"})
        self.assertTrue(review["ordered"])

    def test_repeated_entries_are_folded(self):
        review = ap.check_step_order(
            [
                "mission-transmission-reception-analysis",
                "mission-transmission-reception-analysis",
            ]
        )
        self.assertEqual(review["completed"], ["mission-transmission-reception-analysis"])

    def test_a_bare_string_is_rejected(self):
        with self.assertRaises(ValueError):
            ap.check_step_order("mission-transmission-reception-analysis")

    def test_an_unrecognised_member_is_rejected(self):
        with self.assertRaises(ValueError):
            ap.check_step_order(["mission-transmission-reception-analysis", "launch"])


class PrerequisiteTests(unittest.TestCase):
    def test_the_first_step_has_no_prerequisites(self):
        review = ap.check_step_prerequisites("mission-transmission-reception-analysis", [])
        self.assertTrue(review["ready"])

    def test_open_predecessors_are_listed(self):
        review = ap.check_step_prerequisites("antenna-concept-selection", [])
        self.assertFalse(review["ready"])
        self.assertEqual(len(review["missing_prerequisites"]), 3)

    def test_closed_predecessors_make_the_step_ready(self):
        review = ap.check_step_prerequisites(
            "antenna-concept-selection", list(ap.PROCESS_STEPS[:3])
        )
        self.assertTrue(review["ready"])

    def test_unrecognised_step_is_rejected(self):
        with self.assertRaises(ValueError):
            ap.check_step_prerequisites("antenna-painting", [])


class EntryDataTests(unittest.TestCase):
    def test_complete_entry_data_passes(self):
        review = ap.check_step_entry_data(
            "antenna-design-decision",
            ["selected-antenna-concept", "verification-approach"],
        )
        self.assertTrue(review["complete"])

    def test_missing_entry_data_is_listed(self):
        review = ap.check_step_entry_data(
            "antenna-design-decision", ["selected-antenna-concept"]
        )
        self.assertFalse(review["complete"])
        self.assertEqual(review["missing_entry_data"], ["verification-approach"])

    def test_entry_data_names_are_normalised(self):
        review = ap.check_step_entry_data(
            "antenna-design-decision",
            ["Selected Antenna Concept", "verification_approach"],
        )
        self.assertTrue(review["complete"])

    def test_surplus_data_is_harmless(self):
        review = ap.check_step_entry_data(
            "antenna-design-decision",
            ["selected-antenna-concept", "verification-approach", "mass-budget"],
        )
        self.assertTrue(review["complete"])

    def test_a_bare_string_of_inputs_is_rejected(self):
        with self.assertRaises(ValueError):
            ap.check_step_entry_data("antenna-design-decision", "verification-approach")

    def test_a_non_string_input_name_is_rejected(self):
        with self.assertRaises(ValueError):
            ap.check_step_entry_data("antenna-design-decision", [7])

    def test_an_empty_input_name_is_rejected(self):
        with self.assertRaises(ValueError):
            ap.check_step_entry_data("antenna-design-decision", ["  "])


class NextStepTests(unittest.TestCase):
    def test_nothing_closed_points_at_the_mission_analysis(self):
        self.assertEqual(ap.next_process_step([]), ap.PROCESS_STEPS[0])

    def test_partial_completion_points_at_the_first_open_step(self):
        self.assertEqual(
            ap.next_process_step(list(ap.PROCESS_STEPS[:2])), ap.PROCESS_STEPS[2]
        )

    def test_full_completion_points_at_nothing(self):
        self.assertIsNone(ap.next_process_step(list(ap.PROCESS_STEPS)))


class GainDerivationTests(unittest.TestCase):
    def test_required_gain_arithmetic(self):
        self.assertAlmostEqual(ap.derive_required_antenna_gain_dbi(44.0, 13.0, 1.0), 32.0)

    def test_a_stronger_transmitter_relaxes_the_antenna(self):
        strong = ap.derive_required_antenna_gain_dbi(44.0, 16.0, 1.0)
        weak = ap.derive_required_antenna_gain_dbi(44.0, 13.0, 1.0)
        self.assertAlmostEqual(weak - strong, 3.0)

    def test_a_longer_feeder_raises_the_requirement(self):
        short = ap.derive_required_antenna_gain_dbi(44.0, 13.0, 1.0)
        long_run = ap.derive_required_antenna_gain_dbi(44.0, 13.0, 2.5)
        self.assertAlmostEqual(long_run - short, 1.5)

    def test_negative_feeder_attenuation_is_rejected(self):
        with self.assertRaises(ValueError):
            ap.derive_required_antenna_gain_dbi(44.0, 13.0, -1.0)

    def test_non_numeric_demand_is_rejected(self):
        with self.assertRaises(ValueError):
            ap.derive_required_antenna_gain_dbi("44", 13.0, 1.0)


class CoverageGeometryTests(unittest.TestCase):
    def test_geostationary_spot_subtends_a_narrow_half_angle(self):
        half_angle = ap.edge_of_coverage_half_angle_deg(35786.0e3, 1000.0e3)
        self.assertAlmostEqual(half_angle, 1.5906, places=3)

    def test_the_same_footprint_is_far_wider_from_low_orbit(self):
        low = ap.edge_of_coverage_half_angle_deg(700.0e3, 1000.0e3)
        high = ap.edge_of_coverage_half_angle_deg(35786.0e3, 1000.0e3)
        self.assertGreater(low, 10.0 * high)

    def test_a_footprint_past_the_horizon_is_rejected(self):
        with self.assertRaises(ValueError):
            ap.edge_of_coverage_half_angle_deg(700.0e3, 4000.0e3)

    def test_zero_altitude_is_rejected(self):
        with self.assertRaises(ValueError):
            ap.edge_of_coverage_half_angle_deg(0.0, 1000.0e3)

    def test_negative_footprint_is_rejected(self):
        with self.assertRaises(ValueError):
            ap.edge_of_coverage_half_angle_deg(700.0e3, -1000.0e3)

    def test_beamwidth_is_twice_the_half_angle(self):
        self.assertAlmostEqual(ap.half_power_beamwidth_from_half_angle_deg(1.5906), 3.1812)

    def test_a_half_angle_beyond_a_quadrant_is_rejected(self):
        with self.assertRaises(ValueError):
            ap.half_power_beamwidth_from_half_angle_deg(95.0)

    def test_a_zero_half_angle_is_rejected(self):
        with self.assertRaises(ValueError):
            ap.half_power_beamwidth_from_half_angle_deg(0.0)


class DirectivityTests(unittest.TestCase):
    def test_ten_degree_beam_directivity(self):
        self.assertAlmostEqual(ap.directivity_from_beamwidth_dbi(10.0), 24.9136, places=4)

    def test_halving_the_beamwidth_adds_six_decibels(self):
        wide = ap.directivity_from_beamwidth_dbi(10.0)
        narrow = ap.directivity_from_beamwidth_dbi(5.0)
        self.assertAlmostEqual(narrow - wide, 6.0206, places=4)

    def test_beamwidth_beyond_a_hemisphere_is_rejected(self):
        with self.assertRaises(ValueError):
            ap.directivity_from_beamwidth_dbi(200.0)

    def test_zero_beamwidth_is_rejected(self):
        with self.assertRaises(ValueError):
            ap.directivity_from_beamwidth_dbi(0.0)

    def test_directivity_and_beamwidth_round_trip(self):
        beamwidth = ap.beamwidth_from_directivity_deg(ap.directivity_from_beamwidth_dbi(4.0))
        self.assertAlmostEqual(beamwidth, 4.0, places=9)

    def test_a_directivity_no_single_beam_holds_is_rejected(self):
        with self.assertRaises(ValueError):
            ap.beamwidth_from_directivity_deg(-10.0)

    def test_achievable_gain_sits_below_the_directivity(self):
        directivity = ap.directivity_from_beamwidth_dbi(3.1812)
        self.assertAlmostEqual(ap.achievable_gain_dbi(directivity) - directivity, -2.2185, places=4)

    def test_a_loss_free_aperture_reaches_the_directivity(self):
        self.assertAlmostEqual(ap.achievable_gain_dbi(30.0, 1.0), 30.0)

    def test_an_efficiency_above_unity_is_rejected(self):
        with self.assertRaises(ValueError):
            ap.achievable_gain_dbi(30.0, 1.4)

    def test_a_zero_efficiency_is_rejected(self):
        with self.assertRaises(ValueError):
            ap.achievable_gain_dbi(30.0, 0.0)


class FeasibilityTests(unittest.TestCase):
    def test_a_demand_below_the_achievable_gain_is_feasible(self):
        assessment = ap.assess_gain_feasibility(32.0, 32.64)
        self.assertTrue(assessment["feasible"])
        self.assertAlmostEqual(assessment["shortfall_db"], 0.0)

    def test_a_demand_above_the_achievable_gain_reports_the_shortfall(self):
        assessment = ap.assess_gain_feasibility(35.0, 32.64)
        self.assertFalse(assessment["feasible"])
        self.assertAlmostEqual(assessment["shortfall_db"], 2.36)

    def test_a_demand_on_the_boundary_survives_the_round_off(self):
        # The two decibel figures are built from different logarithms; a
        # physically equal pair can differ in the last places. The limit
        # is not relaxed, the representation error is absorbed.
        achievable = 32.64325539316714
        assessment = ap.assess_gain_feasibility(achievable + 1e-13, achievable)
        self.assertTrue(assessment["feasible"])

    def test_a_non_numeric_demand_is_rejected(self):
        with self.assertRaises(ValueError):
            ap.assess_gain_feasibility(None, 32.64)


class ConceptSelectionTests(unittest.TestCase):
    def test_a_narrow_beam_calls_for_a_reflector(self):
        self.assertEqual(ap.select_antenna_concept(3.18), ap.REFLECTOR_ANTENNA)

    def test_an_intermediate_beam_calls_for_a_horn(self):
        self.assertEqual(ap.select_antenna_concept(25.0), ap.HORN_ANTENNA)

    def test_a_wide_beam_calls_for_a_low_gain_element(self):
        self.assertEqual(ap.select_antenna_concept(104.0), ap.LOW_GAIN_ELEMENT_ANTENNA)

    def test_multiple_simultaneous_beams_call_for_an_array(self):
        self.assertEqual(ap.select_antenna_concept(3.18, 8), ap.PHASED_ARRAY_ANTENNA)

    def test_electronic_steering_calls_for_an_array(self):
        self.assertEqual(
            ap.select_antenna_concept(104.0, 1, True), ap.PHASED_ARRAY_ANTENNA
        )

    def test_the_narrow_band_edge_stays_with_the_reflector(self):
        self.assertEqual(ap.select_antenna_concept(10.0), ap.REFLECTOR_ANTENNA)

    def test_a_band_edge_recovered_from_a_rounded_directivity_stays_put(self):
        # A directivity quoted to ten decimal places re-derives a 10 degree
        # beam as fractionally wider than 10; it is still a narrow beam.
        beamwidth = ap.beamwidth_from_directivity_deg(24.9136169383)
        self.assertGreater(beamwidth, ap.NARROW_BEAM_LIMIT_DEG)
        self.assertEqual(ap.select_antenna_concept(beamwidth), ap.REFLECTOR_ANTENNA)

    def test_the_intermediate_band_edge_stays_with_the_horn(self):
        self.assertEqual(ap.select_antenna_concept(60.0), ap.HORN_ANTENNA)

    def test_just_past_the_intermediate_edge_is_a_low_gain_element(self):
        self.assertEqual(ap.select_antenna_concept(60.5), ap.LOW_GAIN_ELEMENT_ANTENNA)

    def test_a_beam_count_below_one_is_rejected(self):
        with self.assertRaises(ValueError):
            ap.select_antenna_concept(3.18, 0)

    def test_a_non_integer_beam_count_is_rejected(self):
        with self.assertRaises(ValueError):
            ap.select_antenna_concept(3.18, 2.5)

    def test_a_non_boolean_steering_flag_is_rejected(self):
        with self.assertRaises(ValueError):
            ap.select_antenna_concept(3.18, 1, "yes")

    def test_a_beamwidth_beyond_a_hemisphere_is_rejected(self):
        with self.assertRaises(ValueError):
            ap.select_antenna_concept(190.0)


class ProcessReviewTests(unittest.TestCase):
    def test_nominal_project_is_ready_for_the_design_decision(self):
        review = ap.review_antenna_engineering_process(nominal_project())
        self.assertTrue(review["ready_for_design_decision"])
        self.assertEqual(review["findings"], [])
        self.assertEqual(review["next_step"], "antenna-design-decision")

    def test_nominal_project_figures(self):
        review = ap.review_antenna_engineering_process(nominal_project())
        self.assertAlmostEqual(review["required_gain_dbi"], 32.0)
        self.assertAlmostEqual(review["edge_of_coverage_half_angle_deg"], 1.5906, places=3)
        self.assertAlmostEqual(review["half_power_beamwidth_deg"], 3.1812, places=3)
        self.assertAlmostEqual(review["directivity_dbi"], 34.8617, places=3)
        self.assertAlmostEqual(review["achievable_gain_dbi"], 32.6433, places=3)

    def test_nominal_project_selects_a_reflector(self):
        review = ap.review_antenna_engineering_process(nominal_project())
        self.assertEqual(review["selected_concept"], ap.REFLECTOR_ANTENNA)

    def test_an_out_of_order_project_is_flagged(self):
        project = nominal_project()
        project["completed_steps"] = [
            "mission-transmission-reception-analysis",
            "antenna-concept-selection",
        ]
        review = ap.review_antenna_engineering_process(project)
        self.assertFalse(review["ready_for_design_decision"])
        self.assertFalse(review["order"]["ordered"])

    def test_missing_entry_data_blocks_the_next_step(self):
        project = nominal_project()
        project["available_inputs"] = ["selected-antenna-concept"]
        review = ap.review_antenna_engineering_process(project)
        self.assertFalse(review["ready_for_design_decision"])
        self.assertTrue(any("verification-approach" in f for f in review["findings"]))

    def test_a_link_the_coverage_cannot_hold_is_flagged(self):
        project = nominal_project()
        project["required_radiated_power_dbw"] = 50.0
        review = ap.review_antenna_engineering_process(project)
        self.assertFalse(review["feasibility"]["feasible"])
        self.assertAlmostEqual(review["feasibility"]["shortfall_db"], 5.3567, places=3)

    def test_a_multi_beam_payload_changes_the_concept(self):
        project = nominal_project()
        project["beam_count"] = 16
        review = ap.review_antenna_engineering_process(project)
        self.assertEqual(review["selected_concept"], ap.PHASED_ARRAY_ANTENNA)

    def test_a_low_orbit_wide_footprint_selects_a_low_gain_element(self):
        project = nominal_project()
        project["orbit_altitude_m"] = 700.0e3
        project["required_radiated_power_dbw"] = 10.0
        review = ap.review_antenna_engineering_process(project)
        self.assertEqual(review["selected_concept"], ap.LOW_GAIN_ELEMENT_ANTENNA)
        self.assertAlmostEqual(review["half_power_beamwidth_deg"], 103.983, places=2)

    def test_a_closed_sequence_leaves_no_next_step(self):
        project = nominal_project()
        project["completed_steps"] = list(ap.PROCESS_STEPS)
        review = ap.review_antenna_engineering_process(project)
        self.assertIsNone(review["next_step"])
        self.assertTrue(review["entry_data"]["complete"])

    def test_a_lower_aperture_efficiency_can_break_feasibility(self):
        project = nominal_project()
        project["aperture_efficiency"] = 0.3
        review = ap.review_antenna_engineering_process(project)
        self.assertFalse(review["feasibility"]["feasible"])

    def test_a_missing_required_key_is_rejected(self):
        project = nominal_project()
        del project["coverage_radius_m"]
        with self.assertRaises(ValueError):
            ap.review_antenna_engineering_process(project)

    def test_a_non_mapping_project_is_rejected(self):
        with self.assertRaises(ValueError):
            ap.review_antenna_engineering_process(list(ap.PROCESS_STEPS))

    def test_a_footprint_past_the_horizon_stops_the_review(self):
        project = nominal_project()
        project["orbit_altitude_m"] = 500.0e3
        project["coverage_radius_m"] = 4000.0e3
        with self.assertRaises(ValueError):
            ap.review_antenna_engineering_process(project)


if __name__ == "__main__":
    unittest.main()
