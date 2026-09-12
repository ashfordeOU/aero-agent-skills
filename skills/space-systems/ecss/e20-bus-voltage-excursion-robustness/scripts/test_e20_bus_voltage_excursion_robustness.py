#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-20C clause 5.7.4 robustness to fuse
blowing and primary bus voltage excursions.

Exercises scripts/e20_bus_voltage_excursion_robustness_logic.py (stdlib
unittest, offline). Contract: a protection device kind maps to exactly
one category and an unrecognized kind raises; the rating a circuit
needs is its steady current over the derating factor; a fault current
that cannot reach the blow ratio is reported; the let-through energy is
current squared times clearing time and is checked against the harness
withstand; an upstream device must not begin to melt before the
downstream one has cleared, with a coordination ratio of margin; a bus
excursion is categorized by magnitude against the nominal window and by
duration against the transient limit; an equipment is reported for a
voltage beyond its absolute limits, a sustained departure it does not
ride through, or a transient outside its operating window it cannot
recover from unaided; a computed figure sitting exactly on a limit is
compliant even when it overshoots in the last place; and the aggregated
review is robust only when every list is empty.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e20_bus_voltage_excursion_robustness_logic as br  # noqa: E402


def _clean_circuit():
    """A protected circuit that satisfies every clause 5.7.4 check."""
    return {
        "circuit_id": "pld_feed_1",
        "device_kind": "cartridge_fuse",
        "rating_a": 5.0,
        "steady_current_a": 2.0,
        "derating_factor": 0.5,
        "fault_current_a": 40.0,
        "minimum_blow_ratio": 5.0,
        "clearing_time_s": 0.005,
        "harness_withstand_i2t_a2s": 20.0,
        "requires_in_flight_reset": False,
    }


def _clean_pair():
    return {
        "pair_id": "main_to_pld",
        "upstream_minimum_melting_i2t_a2s": 100.0,
        "downstream_let_through_i2t_a2s": 8.0,
        "selectivity_ratio": 2.0,
    }


def _bus_envelope():
    return {
        "nominal_min_v": 26.0,
        "nominal_max_v": 29.0,
        "transient_duration_limit_s": 0.1,
    }


def _clean_equipment():
    return {
        "equipment_id": "avionics_1",
        "absolute_min_voltage_v": 0.0,
        "operating_min_voltage_v": 22.0,
        "operating_max_voltage_v": 32.0,
        "absolute_max_voltage_v": 50.0,
        "rides_through_sustained_excursion": True,
        "recovers_without_ground_command": True,
    }


def _clean_excursions():
    return [
        {"excursion_id": "nominal_ripple", "voltage_v": 27.5, "duration_s": 0.0},
        {"excursion_id": "load_step_dip", "voltage_v": 24.0, "duration_s": 0.05},
    ]


def _clean_subsystem():
    return {
        "circuits": [_clean_circuit()],
        "selectivity_pairs": [_clean_pair()],
        "bus_envelope": _bus_envelope(),
        "equipment": [_clean_equipment()],
        "excursions": _clean_excursions(),
    }


class TestProtectionDeviceCategorization(unittest.TestCase):
    def test_wire_fuse_is_single_shot(self):
        self.assertEqual(
            br.categorize_protection_device("wire_fuse"), "single_shot"
        )

    def test_cartridge_fuse_is_single_shot(self):
        self.assertEqual(
            br.categorize_protection_device("cartridge_fuse"), "single_shot"
        )

    def test_latching_current_limiter_is_resettable(self):
        self.assertEqual(
            br.categorize_protection_device("latching_current_limiter"),
            "resettable",
        )

    def test_foldback_limiter_is_resettable(self):
        self.assertEqual(
            br.categorize_protection_device("foldback_current_limiter"),
            "resettable",
        )

    def test_circuit_breaker_is_resettable(self):
        self.assertEqual(
            br.categorize_protection_device("circuit_breaker"), "resettable"
        )

    def test_every_known_kind_maps_to_a_known_category(self):
        for kind in br.PROTECTION_DEVICE_KINDS:
            self.assertIn(
                br.categorize_protection_device(kind),
                {"single_shot", "resettable"},
            )

    def test_unrecognized_device_kind_raises(self):
        with self.assertRaises(ValueError):
            br.categorize_protection_device("thermal_wish")

    def test_unhashable_device_kind_raises_value_error(self):
        with self.assertRaises(ValueError):
            br.categorize_protection_device(["wire_fuse"])


class TestRequiredRating(unittest.TestCase):
    def test_rating_is_steady_current_over_the_derating_factor(self):
        self.assertAlmostEqual(br.required_rating_a(2.0, 0.5), 4.0, places=9)

    def test_no_derating_leaves_the_steady_current(self):
        self.assertAlmostEqual(br.required_rating_a(3.0, 1.0), 3.0, places=9)

    def test_zero_steady_current_needs_nothing(self):
        self.assertAlmostEqual(br.required_rating_a(0.0, 0.5), 0.0, places=9)

    def test_negative_steady_current_raises(self):
        with self.assertRaises(ValueError):
            br.required_rating_a(-1.0, 0.5)

    def test_zero_derating_factor_raises(self):
        with self.assertRaises(ValueError):
            br.required_rating_a(2.0, 0.0)

    def test_derating_factor_above_one_raises(self):
        with self.assertRaises(ValueError):
            br.required_rating_a(2.0, 1.5)


class TestLetThroughEnergy(unittest.TestCase):
    def test_energy_is_current_squared_times_time(self):
        self.assertAlmostEqual(br.let_through_i2t(40.0, 0.005), 8.0, places=9)

    def test_zero_fault_current_passes_no_energy(self):
        self.assertAlmostEqual(br.let_through_i2t(0.0, 0.005), 0.0, places=9)

    def test_instant_clearing_passes_no_energy(self):
        self.assertAlmostEqual(br.let_through_i2t(40.0, 0.0), 0.0, places=9)

    def test_negative_fault_current_raises(self):
        with self.assertRaises(ValueError):
            br.let_through_i2t(-1.0, 0.005)

    def test_negative_clearing_time_raises(self):
        with self.assertRaises(ValueError):
            br.let_through_i2t(40.0, -0.005)


class TestCircuitValidation(unittest.TestCase):
    def test_missing_circuit_key_raises(self):
        circuit = _clean_circuit()
        del circuit["minimum_blow_ratio"]
        with self.assertRaises(ValueError):
            br.protection_findings(circuit)

    def test_non_positive_rating_raises(self):
        circuit = _clean_circuit()
        circuit["rating_a"] = 0.0
        with self.assertRaises(ValueError):
            br.protection_findings(circuit)

    def test_negative_fault_current_raises(self):
        circuit = _clean_circuit()
        circuit["fault_current_a"] = -1.0
        with self.assertRaises(ValueError):
            br.protection_findings(circuit)

    def test_non_positive_blow_ratio_raises(self):
        circuit = _clean_circuit()
        circuit["minimum_blow_ratio"] = 0.0
        with self.assertRaises(ValueError):
            br.protection_findings(circuit)

    def test_unrecognized_device_kind_raises_through_the_circuit(self):
        circuit = _clean_circuit()
        circuit["device_kind"] = "hope"
        with self.assertRaises(ValueError):
            br.protection_findings(circuit)


class TestProtectionFindings(unittest.TestCase):
    def test_well_rated_circuit_reports_nothing(self):
        self.assertEqual(br.protection_findings(_clean_circuit()), [])

    def test_rating_below_the_derated_steady_current_is_reported(self):
        circuit = _clean_circuit()
        circuit["rating_a"] = 3.0
        findings = br.protection_findings(circuit)
        issues = {f["issue"] for f in findings}
        self.assertIn("protection_rating_below_derated_steady_current", issues)

    def test_rating_exactly_at_the_derated_requirement_is_compliant(self):
        circuit = _clean_circuit()
        circuit["rating_a"] = 4.0
        self.assertEqual(br.protection_findings(circuit), [])

    def test_summed_steady_current_at_the_rating_is_compliant(self):
        steady_a = 0.0
        for _ in range(3):
            steady_a += 0.1
        self.assertGreater(steady_a, 0.3)  # overshoots in binary
        circuit = _clean_circuit()
        circuit["steady_current_a"] = steady_a
        circuit["derating_factor"] = 1.0
        circuit["rating_a"] = 0.3
        circuit["fault_current_a"] = 10.0
        self.assertEqual(br.protection_findings(circuit), [])

    def test_fault_current_too_small_to_clear_is_reported(self):
        circuit = _clean_circuit()
        circuit["fault_current_a"] = 10.0
        findings = br.protection_findings(circuit)
        self.assertEqual(len(findings), 1)
        self.assertEqual(
            findings[0]["issue"], "fault_current_cannot_clear_protection"
        )
        self.assertAlmostEqual(findings[0]["blow_ratio"], 2.0, places=9)

    def test_fault_current_exactly_at_the_blow_ratio_is_compliant(self):
        circuit = _clean_circuit()
        circuit["fault_current_a"] = 25.0
        self.assertEqual(br.protection_findings(circuit), [])

    def test_single_shot_device_needing_a_reset_is_reported(self):
        circuit = _clean_circuit()
        circuit["requires_in_flight_reset"] = True
        findings = br.protection_findings(circuit)
        self.assertEqual(len(findings), 1)
        self.assertEqual(
            findings[0]["issue"], "single_shot_device_on_circuit_needing_reset"
        )

    def test_resettable_device_needing_a_reset_is_fine(self):
        circuit = _clean_circuit()
        circuit["device_kind"] = "latching_current_limiter"
        circuit["requires_in_flight_reset"] = True
        self.assertEqual(br.protection_findings(circuit), [])

    def test_two_protection_defects_are_reported_together(self):
        circuit = _clean_circuit()
        circuit["rating_a"] = 3.0
        circuit["fault_current_a"] = 6.0
        self.assertEqual(len(br.protection_findings(circuit)), 2)


class TestHarnessFindings(unittest.TestCase):
    def test_harness_absorbing_the_let_through_reports_nothing(self):
        self.assertEqual(br.harness_findings(_clean_circuit()), [])

    def test_let_through_beyond_the_withstand_is_reported(self):
        circuit = _clean_circuit()
        circuit["harness_withstand_i2t_a2s"] = 4.0
        findings = br.harness_findings(circuit)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["issue"], "harness_i2t_withstand_exceeded")
        self.assertAlmostEqual(findings[0]["let_through_i2t_a2s"], 8.0, places=9)

    def test_let_through_exactly_at_the_withstand_is_compliant(self):
        circuit = _clean_circuit()
        circuit["harness_withstand_i2t_a2s"] = 8.0
        self.assertEqual(br.harness_findings(circuit), [])

    def test_computed_let_through_at_the_withstand_is_compliant(self):
        circuit = _clean_circuit()
        circuit["steady_current_a"] = 0.1
        circuit["derating_factor"] = 0.5
        circuit["rating_a"] = 0.2
        circuit["fault_current_a"] = 1.1
        circuit["clearing_time_s"] = 0.1
        circuit["harness_withstand_i2t_a2s"] = 0.121
        self.assertGreater(br.let_through_i2t(1.1, 0.1), 0.121)
        self.assertEqual(br.harness_findings(circuit), [])
        self.assertEqual(br.protection_findings(circuit), [])

    def test_missing_clearing_time_raises(self):
        circuit = _clean_circuit()
        del circuit["clearing_time_s"]
        with self.assertRaises(ValueError):
            br.harness_findings(circuit)

    def test_non_positive_harness_withstand_raises(self):
        circuit = _clean_circuit()
        circuit["harness_withstand_i2t_a2s"] = 0.0
        with self.assertRaises(ValueError):
            br.harness_findings(circuit)


class TestSelectivityFindings(unittest.TestCase):
    def test_coordinated_pair_reports_nothing(self):
        self.assertEqual(br.selectivity_findings(_clean_pair()), [])

    def test_upstream_melting_too_early_is_reported(self):
        pair = _clean_pair()
        pair["upstream_minimum_melting_i2t_a2s"] = 10.0
        findings = br.selectivity_findings(pair)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["issue"], "protection_selectivity_not_ensured")
        self.assertAlmostEqual(findings[0]["required_i2t_a2s"], 16.0, places=9)

    def test_upstream_exactly_at_the_required_energy_is_compliant(self):
        pair = _clean_pair()
        pair["upstream_minimum_melting_i2t_a2s"] = 16.0
        self.assertEqual(br.selectivity_findings(pair), [])

    def test_computed_requirement_at_the_upstream_energy_is_compliant(self):
        pair = _clean_pair()
        pair["downstream_let_through_i2t_a2s"] = 0.1
        pair["selectivity_ratio"] = 3.0
        pair["upstream_minimum_melting_i2t_a2s"] = 0.3
        self.assertGreater(0.1 * 3.0, 0.3)  # overshoots in binary
        self.assertEqual(br.selectivity_findings(pair), [])

    def test_missing_pair_key_raises(self):
        pair = _clean_pair()
        del pair["selectivity_ratio"]
        with self.assertRaises(ValueError):
            br.selectivity_findings(pair)

    def test_selectivity_ratio_below_one_raises(self):
        pair = _clean_pair()
        pair["selectivity_ratio"] = 0.9
        with self.assertRaises(ValueError):
            br.selectivity_findings(pair)

    def test_non_positive_upstream_energy_raises(self):
        pair = _clean_pair()
        pair["upstream_minimum_melting_i2t_a2s"] = 0.0
        with self.assertRaises(ValueError):
            br.selectivity_findings(pair)

    def test_non_positive_downstream_energy_raises(self):
        pair = _clean_pair()
        pair["downstream_let_through_i2t_a2s"] = 0.0
        with self.assertRaises(ValueError):
            br.selectivity_findings(pair)


class TestBusEnvelope(unittest.TestCase):
    def test_valid_envelope_is_normalized(self):
        limits = br.validate_bus_envelope(_bus_envelope())
        self.assertAlmostEqual(limits["nominal_min_v"], 26.0, places=9)
        self.assertAlmostEqual(limits["transient_duration_limit_s"], 0.1, places=9)

    def test_missing_envelope_key_raises(self):
        envelope = _bus_envelope()
        del envelope["transient_duration_limit_s"]
        with self.assertRaises(ValueError):
            br.validate_bus_envelope(envelope)

    def test_non_positive_envelope_value_raises(self):
        envelope = _bus_envelope()
        envelope["transient_duration_limit_s"] = 0.0
        with self.assertRaises(ValueError):
            br.validate_bus_envelope(envelope)

    def test_inverted_nominal_window_raises(self):
        envelope = _bus_envelope()
        envelope["nominal_min_v"] = 30.0
        with self.assertRaises(ValueError):
            br.validate_bus_envelope(envelope)


class TestBusExcursionCategorization(unittest.TestCase):
    def test_inside_the_nominal_window(self):
        self.assertEqual(
            br.categorize_bus_excursion(27.5, 0.0, _bus_envelope()),
            "within_nominal_window",
        )

    def test_lower_nominal_edge_is_inside(self):
        self.assertEqual(
            br.categorize_bus_excursion(26.0, 10.0, _bus_envelope()),
            "within_nominal_window",
        )

    def test_upper_nominal_edge_is_inside(self):
        self.assertEqual(
            br.categorize_bus_excursion(29.0, 10.0, _bus_envelope()),
            "within_nominal_window",
        )

    def test_brief_dip_is_an_undervoltage_transient(self):
        self.assertEqual(
            br.categorize_bus_excursion(20.0, 0.05, _bus_envelope()),
            "undervoltage_transient",
        )

    def test_long_dip_is_a_sustained_undervoltage(self):
        self.assertEqual(
            br.categorize_bus_excursion(20.0, 5.0, _bus_envelope()),
            "sustained_undervoltage",
        )

    def test_brief_surge_is_an_overvoltage_transient(self):
        self.assertEqual(
            br.categorize_bus_excursion(35.0, 0.05, _bus_envelope()),
            "overvoltage_transient",
        )

    def test_long_surge_is_a_sustained_overvoltage(self):
        self.assertEqual(
            br.categorize_bus_excursion(35.0, 5.0, _bus_envelope()),
            "sustained_overvoltage",
        )

    def test_duration_exactly_at_the_transient_limit_is_transient(self):
        self.assertEqual(
            br.categorize_bus_excursion(20.0, 0.1, _bus_envelope()),
            "undervoltage_transient",
        )

    def test_negative_voltage_raises(self):
        with self.assertRaises(ValueError):
            br.categorize_bus_excursion(-1.0, 0.05, _bus_envelope())

    def test_negative_duration_raises(self):
        with self.assertRaises(ValueError):
            br.categorize_bus_excursion(20.0, -0.05, _bus_envelope())

    def test_invalid_envelope_propagates(self):
        with self.assertRaises(ValueError):
            br.categorize_bus_excursion(20.0, 0.05, {"nominal_min_v": 26.0})


class TestEquipmentValidation(unittest.TestCase):
    def test_valid_equipment_is_normalized(self):
        data = br.validate_equipment(_clean_equipment())
        self.assertEqual(data["equipment_id"], "avionics_1")
        self.assertTrue(data["rides_through_sustained_excursion"])

    def test_ride_through_flags_default_to_false(self):
        equipment = _clean_equipment()
        del equipment["rides_through_sustained_excursion"]
        del equipment["recovers_without_ground_command"]
        data = br.validate_equipment(equipment)
        self.assertFalse(data["rides_through_sustained_excursion"])
        self.assertFalse(data["recovers_without_ground_command"])

    def test_missing_equipment_id_raises(self):
        equipment = _clean_equipment()
        del equipment["equipment_id"]
        with self.assertRaises(ValueError):
            br.validate_equipment(equipment)

    def test_missing_voltage_limit_raises(self):
        equipment = _clean_equipment()
        del equipment["operating_max_voltage_v"]
        with self.assertRaises(ValueError):
            br.validate_equipment(equipment)

    def test_negative_voltage_limit_raises(self):
        equipment = _clean_equipment()
        equipment["absolute_min_voltage_v"] = -1.0
        with self.assertRaises(ValueError):
            br.validate_equipment(equipment)

    def test_operating_window_outside_the_absolute_window_raises(self):
        equipment = _clean_equipment()
        equipment["absolute_max_voltage_v"] = 30.0
        with self.assertRaises(ValueError):
            br.validate_equipment(equipment)

    def test_collapsed_operating_window_raises(self):
        equipment = _clean_equipment()
        equipment["operating_min_voltage_v"] = 32.0
        with self.assertRaises(ValueError):
            br.validate_equipment(equipment)


class TestExcursionFindings(unittest.TestCase):
    def test_equipment_riding_out_every_excursion_reports_nothing(self):
        self.assertEqual(
            br.excursion_findings(
                _clean_equipment(), _clean_excursions(), _bus_envelope()
            ),
            [],
        )

    def test_empty_excursion_list_reports_nothing(self):
        self.assertEqual(
            br.excursion_findings(_clean_equipment(), [], _bus_envelope()), []
        )

    def test_voltage_beyond_the_absolute_limit_is_reported(self):
        excursions = [
            {"excursion_id": "surge", "voltage_v": 60.0, "duration_s": 0.01}
        ]
        findings = br.excursion_findings(
            _clean_equipment(), excursions, _bus_envelope()
        )
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["issue"], "equipment_absolute_limit_exceeded")
        self.assertEqual(findings[0]["category"], "overvoltage_transient")

    def test_sustained_excursion_without_ride_through_is_reported(self):
        equipment = _clean_equipment()
        equipment["rides_through_sustained_excursion"] = False
        excursions = [
            {"excursion_id": "brownout", "voltage_v": 18.0, "duration_s": 5.0}
        ]
        findings = br.excursion_findings(equipment, excursions, _bus_envelope())
        self.assertEqual(len(findings), 1)
        self.assertEqual(
            findings[0]["issue"],
            "sustained_excursion_beyond_ride_through_capability",
        )

    def test_excursion_outside_the_operating_window_needing_ground_help(self):
        equipment = _clean_equipment()
        equipment["recovers_without_ground_command"] = False
        excursions = [
            {"excursion_id": "deep_dip", "voltage_v": 18.0, "duration_s": 0.05}
        ]
        findings = br.excursion_findings(equipment, excursions, _bus_envelope())
        self.assertEqual(len(findings), 1)
        self.assertEqual(
            findings[0]["issue"], "excursion_requires_ground_recovery"
        )

    def test_autonomous_recovery_clears_the_same_excursion(self):
        excursions = [
            {"excursion_id": "deep_dip", "voltage_v": 18.0, "duration_s": 0.05}
        ]
        self.assertEqual(
            br.excursion_findings(
                _clean_equipment(), excursions, _bus_envelope()
            ),
            [],
        )

    def test_excursion_inside_the_operating_window_is_not_reported(self):
        equipment = _clean_equipment()
        equipment["recovers_without_ground_command"] = False
        excursions = [
            {"excursion_id": "load_step", "voltage_v": 24.0, "duration_s": 0.05}
        ]
        self.assertEqual(
            br.excursion_findings(equipment, excursions, _bus_envelope()), []
        )

    def test_each_offending_excursion_yields_one_finding(self):
        equipment = _clean_equipment()
        equipment["rides_through_sustained_excursion"] = False
        excursions = [
            {"excursion_id": "brownout", "voltage_v": 18.0, "duration_s": 5.0},
            {"excursion_id": "surge", "voltage_v": 60.0, "duration_s": 0.01},
            {"excursion_id": "nominal", "voltage_v": 28.0, "duration_s": 1.0},
        ]
        findings = br.excursion_findings(equipment, excursions, _bus_envelope())
        self.assertEqual(len(findings), 2)

    def test_missing_excursion_key_raises(self):
        excursions = [{"excursion_id": "surge", "voltage_v": 60.0}]
        with self.assertRaises(ValueError):
            br.excursion_findings(
                _clean_equipment(), excursions, _bus_envelope()
            )


class TestSubsystemReview(unittest.TestCase):
    def test_clean_subsystem_is_robust(self):
        review = br.bus_robustness_review(_clean_subsystem())
        for key in ("protection", "harness", "selectivity", "excursion"):
            self.assertEqual(review[key], [])
        self.assertTrue(br.is_subsystem_robust(review))

    def test_under_rated_protection_reaches_the_review(self):
        subsystem = _clean_subsystem()
        subsystem["circuits"][0]["rating_a"] = 3.0
        review = br.bus_robustness_review(subsystem)
        self.assertEqual(len(review["protection"]), 1)
        self.assertFalse(br.is_subsystem_robust(review))

    def test_harness_overload_reaches_the_review(self):
        subsystem = _clean_subsystem()
        subsystem["circuits"][0]["harness_withstand_i2t_a2s"] = 1.0
        review = br.bus_robustness_review(subsystem)
        self.assertEqual(len(review["harness"]), 1)
        self.assertFalse(br.is_subsystem_robust(review))

    def test_uncoordinated_pair_reaches_the_review(self):
        subsystem = _clean_subsystem()
        subsystem["selectivity_pairs"][0][
            "upstream_minimum_melting_i2t_a2s"
        ] = 5.0
        review = br.bus_robustness_review(subsystem)
        self.assertEqual(len(review["selectivity"]), 1)
        self.assertFalse(br.is_subsystem_robust(review))

    def test_fragile_equipment_reaches_the_review(self):
        subsystem = _clean_subsystem()
        subsystem["equipment"][0]["absolute_min_voltage_v"] = 25.0
        subsystem["equipment"][0]["operating_min_voltage_v"] = 25.0
        review = br.bus_robustness_review(subsystem)
        self.assertEqual(len(review["excursion"]), 1)
        self.assertEqual(
            review["excursion"][0]["issue"], "equipment_absolute_limit_exceeded"
        )

    def test_duplicate_circuit_id_raises(self):
        subsystem = _clean_subsystem()
        subsystem["circuits"].append(_clean_circuit())
        with self.assertRaises(ValueError):
            br.bus_robustness_review(subsystem)

    def test_invalid_envelope_propagates_through_the_review(self):
        subsystem = _clean_subsystem()
        subsystem["bus_envelope"]["nominal_min_v"] = 40.0
        with self.assertRaises(ValueError):
            br.bus_robustness_review(subsystem)

    def test_review_does_not_mutate_its_input(self):
        subsystem = _clean_subsystem()
        before = repr(subsystem)
        br.bus_robustness_review(subsystem)
        self.assertEqual(repr(subsystem), before)

    def test_review_is_deterministic(self):
        subsystem = _clean_subsystem()
        self.assertEqual(
            br.bus_robustness_review(subsystem),
            br.bus_robustness_review(subsystem),
        )

    def test_multiple_circuits_are_all_reviewed(self):
        subsystem = _clean_subsystem()
        second = _clean_circuit()
        second["circuit_id"] = "pld_feed_2"
        second["rating_a"] = 3.0
        subsystem["circuits"].append(second)
        review = br.bus_robustness_review(subsystem)
        self.assertEqual(len(review["protection"]), 1)
        self.assertEqual(review["protection"][0]["circuit"], "pld_feed_2")


if __name__ == "__main__":
    unittest.main()
