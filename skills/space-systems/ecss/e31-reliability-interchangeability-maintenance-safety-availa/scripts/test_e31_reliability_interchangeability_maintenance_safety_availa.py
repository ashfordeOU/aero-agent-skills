"""Contract tests for the clauses 4.4.9 to 4.4.13 dependability logic."""

import math
import unittest

from e31_reliability_interchangeability_maintenance_safety_availa_logic import (
    HAZARDOUS_OUTCOMES,
    PROBABILITY_TOLERANCE,
    assess_dependability,
    availability,
    element_reliability,
    heater_chain_reliability,
    interchangeability_findings,
    parallel_reliability,
    recommend_thermostat_topology,
    series_reliability,
    thermostat_topology_risk,
)

MISSION_HOURS = 43800.0  # five years on orbit
# One heater line: element, wiring, switch, control device.
LINE = [2.0e-7, 1.0e-8, 3.0e-7, 5.0e-7]


class ElementReliabilityTests(unittest.TestCase):
    def test_zero_failure_rate_never_fails(self):
        self.assertAlmostEqual(element_reliability(0.0, MISSION_HOURS), 1.0, places=12)

    def test_reliability_follows_the_exponential_law(self):
        value = element_reliability(1.0e-6, 1.0e6)
        self.assertAlmostEqual(value, math.exp(-1.0), places=12)

    def test_longer_mission_lowers_reliability(self):
        short = element_reliability(1.0e-6, 1.0e4)
        long_run = element_reliability(1.0e-6, 1.0e5)
        self.assertGreater(short, long_run)

    def test_negative_rate_rejected(self):
        with self.assertRaises(ValueError):
            element_reliability(-1.0e-6, MISSION_HOURS)

    def test_zero_mission_rejected(self):
        with self.assertRaises(ValueError):
            element_reliability(1.0e-6, 0.0)

    def test_boolean_rate_rejected(self):
        with self.assertRaises(ValueError):
            element_reliability(True, MISSION_HOURS)


class CombinationTests(unittest.TestCase):
    def test_series_multiplies(self):
        self.assertAlmostEqual(series_reliability([0.9, 0.8]), 0.72, places=12)

    def test_series_of_one_is_itself(self):
        self.assertAlmostEqual(series_reliability([0.93]), 0.93, places=12)

    def test_parallel_beats_its_best_branch(self):
        value = parallel_reliability([0.9, 0.9])
        self.assertAlmostEqual(value, 0.99, places=12)
        self.assertGreater(value, 0.9)

    def test_parallel_of_one_is_itself(self):
        self.assertAlmostEqual(parallel_reliability([0.9]), 0.9, places=12)

    def test_series_would_understate_a_redundant_block(self):
        self.assertLess(series_reliability([0.9, 0.9]), parallel_reliability([0.9, 0.9]))

    def test_empty_series_rejected(self):
        with self.assertRaises(ValueError):
            series_reliability([])

    def test_probability_above_one_rejected(self):
        with self.assertRaises(ValueError):
            parallel_reliability([1.2])

    def test_negative_probability_rejected(self):
        with self.assertRaises(ValueError):
            series_reliability([-0.1])


class HeaterChainTests(unittest.TestCase):
    def test_single_line_chain_equals_its_series_product(self):
        chain = heater_chain_reliability([LINE], MISSION_HOURS)
        expected = series_reliability(
            [element_reliability(rate, MISSION_HOURS) for rate in LINE]
        )
        self.assertAlmostEqual(chain["chain_reliability"], expected, places=12)

    def test_second_line_raises_the_chain(self):
        single = heater_chain_reliability([LINE], MISSION_HOURS)
        double = heater_chain_reliability([LINE, LINE], MISSION_HOURS)
        self.assertGreater(double["chain_reliability"], single["chain_reliability"])

    def test_redundant_block_is_the_parallel_combination(self):
        chain = heater_chain_reliability([LINE, LINE], MISSION_HOURS)
        expected = parallel_reliability(chain["line_reliabilities"])
        self.assertAlmostEqual(chain["redundant_block"], expected, places=12)

    def test_shared_element_caps_the_redundant_block(self):
        plain = heater_chain_reliability([LINE, LINE], MISSION_HOURS)
        shared = heater_chain_reliability([LINE, LINE], MISSION_HOURS, [2.0e-5])
        self.assertLess(shared["chain_reliability"], plain["chain_reliability"])
        self.assertLessEqual(
            shared["chain_reliability"], shared["shared_reliability"]
        )

    def test_no_shared_element_leaves_the_block_untouched(self):
        chain = heater_chain_reliability([LINE, LINE], MISSION_HOURS)
        self.assertAlmostEqual(chain["shared_reliability"], 1.0, places=12)

    def test_line_reliability_is_reported_per_line(self):
        chain = heater_chain_reliability([LINE, LINE[:2]], MISSION_HOURS)
        self.assertEqual(len(chain["line_reliabilities"]), 2)
        self.assertGreater(chain["line_reliabilities"][1], chain["line_reliabilities"][0])

    def test_empty_line_list_rejected(self):
        with self.assertRaises(ValueError):
            heater_chain_reliability([], MISSION_HOURS)

    def test_empty_line_rejected(self):
        with self.assertRaises(ValueError):
            heater_chain_reliability([[]], MISSION_HOURS)

    def test_non_sequence_shared_elements_rejected(self):
        with self.assertRaises(ValueError):
            heater_chain_reliability([LINE], MISSION_HOURS, 2.0e-5)


class ThermostatTopologyTests(unittest.TestCase):
    def test_series_doubles_the_loss_of_heating_exposure(self):
        one = thermostat_topology_risk(1, 0.01, 0.02, "series")
        two = thermostat_topology_risk(2, 0.01, 0.02, "series")
        self.assertGreater(two["loss_of_heating"], one["loss_of_heating"])

    def test_series_squares_the_loss_of_cutoff(self):
        two = thermostat_topology_risk(2, 0.01, 0.02, "series")
        self.assertAlmostEqual(two["loss_of_cutoff"], 0.02 * 0.02, places=12)

    def test_parallel_squares_the_loss_of_heating(self):
        two = thermostat_topology_risk(2, 0.01, 0.02, "parallel")
        self.assertAlmostEqual(two["loss_of_heating"], 0.01 * 0.01, places=12)

    def test_parallel_doubles_the_loss_of_cutoff_exposure(self):
        two = thermostat_topology_risk(2, 0.01, 0.02, "parallel")
        self.assertAlmostEqual(two["loss_of_cutoff"], 1.0 - 0.98 * 0.98, places=12)

    def test_single_device_is_the_same_either_way(self):
        series = thermostat_topology_risk(1, 0.01, 0.02, "series")
        parallel = thermostat_topology_risk(1, 0.01, 0.02, "parallel")
        self.assertAlmostEqual(
            series["loss_of_heating"], parallel["loss_of_heating"], places=12
        )
        self.assertAlmostEqual(
            series["loss_of_cutoff"], parallel["loss_of_cutoff"], places=12
        )

    def test_zero_count_rejected(self):
        with self.assertRaises(ValueError):
            thermostat_topology_risk(0, 0.01, 0.02, "series")

    def test_boolean_count_rejected(self):
        with self.assertRaises(ValueError):
            thermostat_topology_risk(True, 0.01, 0.02, "series")

    def test_unknown_topology_rejected(self):
        with self.assertRaises(ValueError):
            thermostat_topology_risk(2, 0.01, 0.02, "cascade")

    def test_impossible_probability_pair_rejected(self):
        with self.assertRaises(ValueError):
            thermostat_topology_risk(2, 0.7, 0.5, "series")

    def test_freezing_hazard_recommends_parallel(self):
        result = recommend_thermostat_topology(2, 0.01, 0.02, "loss_of_heating")
        self.assertEqual(result["recommended"], "parallel")

    def test_runaway_hazard_recommends_series(self):
        result = recommend_thermostat_topology(2, 0.01, 0.02, "loss_of_cutoff")
        self.assertEqual(result["recommended"], "series")

    def test_recommendation_reports_the_lower_hazard_probability(self):
        result = recommend_thermostat_topology(2, 0.01, 0.02, "loss_of_heating")
        self.assertAlmostEqual(result["hazardous_probability"], 0.0001, places=12)

    def test_single_device_tie_falls_back_to_series(self):
        result = recommend_thermostat_topology(1, 0.01, 0.02, "loss_of_heating")
        self.assertEqual(result["recommended"], "series")

    def test_unknown_hazard_rejected(self):
        with self.assertRaises(ValueError):
            recommend_thermostat_topology(2, 0.01, 0.02, "loss_of_power")

    def test_hazard_vocabulary_is_the_two_failure_modes(self):
        self.assertEqual(len(HAZARDOUS_OUTCOMES), 2)


class InterchangeabilityTests(unittest.TestCase):
    NOMINAL = {"mount_conductance_w_per_k": 2.5, "heater_resistance_ohm": 120.0}
    TOLERANCE = {"mount_conductance_w_per_k": 0.10, "heater_resistance_ohm": 0.05}

    def test_identical_spare_has_no_finding(self):
        self.assertEqual(
            interchangeability_findings(self.NOMINAL, dict(self.NOMINAL), self.TOLERANCE),
            [],
        )

    def test_spare_inside_the_band_has_no_finding(self):
        spare = {"mount_conductance_w_per_k": 2.6, "heater_resistance_ohm": 123.0}
        self.assertEqual(
            interchangeability_findings(self.NOMINAL, spare, self.TOLERANCE), []
        )

    def test_spare_exactly_on_the_band_edge_passes(self):
        spare = {"mount_conductance_w_per_k": 2.75, "heater_resistance_ohm": 120.0}
        self.assertEqual(
            interchangeability_findings(self.NOMINAL, spare, self.TOLERANCE), []
        )

    def test_conductance_outside_the_band_is_a_finding(self):
        spare = {"mount_conductance_w_per_k": 3.5, "heater_resistance_ohm": 120.0}
        findings = interchangeability_findings(self.NOMINAL, spare, self.TOLERANCE)
        self.assertEqual(len(findings), 1)
        self.assertIn("mount_conductance_w_per_k", findings[0])

    def test_undeclared_parameter_is_a_finding(self):
        spare = {"mount_conductance_w_per_k": 2.5}
        findings = interchangeability_findings(self.NOMINAL, spare, self.TOLERANCE)
        self.assertEqual(len(findings), 1)
        self.assertIn("does not declare", findings[0])

    def test_missing_tolerance_rejected(self):
        with self.assertRaises(ValueError):
            interchangeability_findings(self.NOMINAL, dict(self.NOMINAL), {})

    def test_zero_nominal_rejected(self):
        with self.assertRaises(ValueError):
            interchangeability_findings(
                {"offset_k": 0.0}, {"offset_k": 0.0}, {"offset_k": 0.1}
            )

    def test_empty_nominal_rejected(self):
        with self.assertRaises(ValueError):
            interchangeability_findings({}, {}, {})


class AvailabilityTests(unittest.TestCase):
    def test_availability_is_uptime_over_total_time(self):
        self.assertAlmostEqual(availability(99.0, 1.0), 0.99, places=12)

    def test_instant_repair_gives_full_availability(self):
        self.assertAlmostEqual(availability(100.0, 0.0), 1.0, places=12)

    def test_longer_repair_lowers_availability(self):
        self.assertLess(availability(100.0, 10.0), availability(100.0, 1.0))

    def test_unrepairable_item_has_no_availability(self):
        with self.assertRaises(ValueError):
            availability(100.0, 1.0, False)

    def test_zero_mtbf_rejected(self):
        with self.assertRaises(ValueError):
            availability(0.0, 1.0)

    def test_negative_repair_time_rejected(self):
        with self.assertRaises(ValueError):
            availability(100.0, -1.0)


class AssessmentTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "heater_lines": [LINE, LINE],
            "mission_hours": MISSION_HOURS,
            "required_chain_reliability": 0.995,
            "thermostat_count": 2,
            "stuck_open_probability": 0.01,
            "stuck_closed_probability": 0.02,
            "hazardous_outcome": "loss_of_heating",
        }
        spec.update(overrides)
        return spec

    def test_redundant_design_is_compliant(self):
        result = assess_dependability(self._spec())
        self.assertTrue(result["compliant"])
        self.assertTrue(result["reliable"])

    def test_single_line_can_miss_the_required_reliability(self):
        result = assess_dependability(
            self._spec(heater_lines=[LINE], required_chain_reliability=0.999)
        )
        self.assertFalse(result["reliable"])
        self.assertIn("falls short", result["findings"][0])

    def test_threshold_exactly_met_is_reliable(self):
        chain = heater_chain_reliability([LINE], MISSION_HOURS)
        result = assess_dependability(self._spec(
            heater_lines=[LINE],
            required_chain_reliability=chain["chain_reliability"],
        ))
        self.assertTrue(result["reliable"])

    def test_freezing_hazard_drives_the_recommendation(self):
        result = assess_dependability(self._spec())
        self.assertEqual(result["recommended_topology"], "parallel")

    def test_runaway_hazard_flips_the_recommendation(self):
        result = assess_dependability(self._spec(hazardous_outcome="loss_of_cutoff"))
        self.assertEqual(result["recommended_topology"], "series")

    def test_dominant_shared_element_is_called_out(self):
        result = assess_dependability(self._spec(shared_elements=[2.0e-5]))
        self.assertTrue(
            any("shared element" in finding for finding in result["findings"])
        )

    def test_interchangeable_spare_keeps_the_verdict_clean(self):
        result = assess_dependability(self._spec(
            nominal_interface={"mount_conductance_w_per_k": 2.5},
            spare_interface={"mount_conductance_w_per_k": 2.6},
            interface_tolerances={"mount_conductance_w_per_k": 0.10},
        ))
        self.assertTrue(result["interchangeable"])
        self.assertTrue(result["compliant"])

    def test_out_of_band_spare_fails_the_verdict(self):
        result = assess_dependability(self._spec(
            nominal_interface={"mount_conductance_w_per_k": 2.5},
            spare_interface={"mount_conductance_w_per_k": 4.0},
            interface_tolerances={"mount_conductance_w_per_k": 0.10},
        ))
        self.assertFalse(result["interchangeable"])
        self.assertFalse(result["compliant"])

    def test_availability_is_reported_for_a_repairable_item(self):
        result = assess_dependability(self._spec(mtbf_hours=99.0, mttr_hours=1.0))
        self.assertAlmostEqual(result["availability"], 0.99, places=12)

    def test_availability_for_an_unrepairable_item_is_a_finding(self):
        result = assess_dependability(
            self._spec(mtbf_hours=99.0, mttr_hours=1.0, repairable=False)
        )
        self.assertIsNone(result["availability"])
        self.assertFalse(result["compliant"])

    def test_missing_key_rejected(self):
        spec = self._spec()
        del spec["thermostat_count"]
        with self.assertRaises(ValueError):
            assess_dependability(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_dependability(["heater_lines"])

    def test_required_reliability_above_one_rejected(self):
        with self.assertRaises(ValueError):
            assess_dependability(self._spec(required_chain_reliability=1.5))

    def test_tolerance_is_tight(self):
        self.assertLess(PROBABILITY_TOLERANCE, 1.0e-9)


if __name__ == "__main__":
    unittest.main()
