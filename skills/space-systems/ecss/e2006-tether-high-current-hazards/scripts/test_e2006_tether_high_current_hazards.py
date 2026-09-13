#!/usr/bin/env python3
"""Gate 3 contract test for e2006-tether-high-current-hazards.

stdlib unittest, offline, deterministic. Run:
python3 test_e2006_tether_high_current_hazards.py
"""

import unittest

import e2006_tether_high_current_hazards_logic as logic


def tether_segment(**over):
    seg = {
        "name": "tether-conductor-leg",
        "kind": "tether-conductor",
        "resistance_ohm": 5.0,
        "thermal_conductance_w_per_k": 2.0,
        "sink_temperature_c": 20.0,
        "insulation_rating_c": 150.0,
        "rated_current_a": 5.0,
        "allowable_drop_v": 15.0,
        "material": "copper",
        "cross_section_mm2": 1.0,
        "protection_clearing_time_s": 0.02,
    }
    seg.update(over)
    return seg


def return_segment(**over):
    seg = {
        "name": "structural-return-leg",
        "kind": "structural-return-path",
        "resistance_ohm": 0.01,
        "thermal_conductance_w_per_k": 0.5,
        "sink_temperature_c": 20.0,
        "insulation_rating_c": 120.0,
        "rated_current_a": 10.0,
        "allowable_drop_v": 1.0,
        "joint_resistance_ohm": 0.001,
        "max_joint_resistance_ohm": 0.0025,
        "material": "aluminium",
        "cross_section_mm2": 4.0,
        "protection_clearing_time_s": 0.02,
    }
    seg.update(over)
    return seg


def loop_config(**over):
    cfg = {
        "operating_current_a": 2.0,
        "fault_current_a": 40.0,
        "loop_drop_budget_v": 12.0,
        "segments": [tether_segment(), return_segment()],
    }
    cfg.update(over)
    return cfg


class TestSegmentCategorization(unittest.TestCase):
    def test_tether_conductor_is_tether_family(self):
        self.assertEqual(logic.categorize_segment("tether-conductor"), "tether")

    def test_structural_return_is_return_family(self):
        self.assertEqual(logic.categorize_segment("structural-return-path"), "return")

    def test_bonding_strap_is_return_family(self):
        self.assertEqual(logic.categorize_segment("bonding-strap"), "return")

    def test_slip_ring_is_interface_family(self):
        self.assertEqual(logic.categorize_segment("deployer-slip-ring"), "interface")

    def test_kind_is_case_and_space_insensitive(self):
        self.assertEqual(logic.categorize_segment("  Tether-Shield "), "tether")

    def test_unknown_kind_raises(self):
        with self.assertRaises(ValueError):
            logic.categorize_segment("solar-array-string")

    def test_empty_kind_raises(self):
        with self.assertRaises(ValueError):
            logic.categorize_segment("   ")

    def test_non_string_kind_raises(self):
        with self.assertRaises(ValueError):
            logic.categorize_segment(7)


class TestElectricalQuantities(unittest.TestCase):
    def test_voltage_drop(self):
        self.assertAlmostEqual(logic.voltage_drop_v(2.0, 5.0), 10.0, places=9)

    def test_zero_current_gives_zero_drop(self):
        self.assertAlmostEqual(logic.voltage_drop_v(0.0, 5.0), 0.0, places=12)

    def test_dissipation_is_quadratic_in_current(self):
        self.assertAlmostEqual(logic.dissipation_w(2.0, 5.0), 20.0, places=9)
        self.assertAlmostEqual(logic.dissipation_w(4.0, 5.0), 80.0, places=9)

    def test_negative_current_raises(self):
        with self.assertRaises(ValueError):
            logic.voltage_drop_v(-1.0, 5.0)

    def test_negative_resistance_raises(self):
        with self.assertRaises(ValueError):
            logic.dissipation_w(1.0, -5.0)

    def test_non_finite_current_raises(self):
        with self.assertRaises(ValueError):
            logic.dissipation_w(float("inf"), 1.0)

    def test_temperature_rise_is_power_over_conductance(self):
        self.assertAlmostEqual(logic.temperature_rise_k(20.0, 2.0), 10.0, places=9)

    def test_zero_thermal_conductance_raises(self):
        with self.assertRaises(ValueError):
            logic.temperature_rise_k(20.0, 0.0)

    def test_conductor_temperature_adds_sink(self):
        self.assertAlmostEqual(logic.conductor_temperature_c(20.0, 10.0), 30.0, places=9)

    def test_sink_below_absolute_zero_raises(self):
        with self.assertRaises(ValueError):
            logic.conductor_temperature_c(-300.0, 1.0)

    def test_negative_rise_raises(self):
        with self.assertRaises(ValueError):
            logic.conductor_temperature_c(20.0, -1.0)


class TestFaultWithstand(unittest.TestCase):
    def test_let_through_energy(self):
        self.assertAlmostEqual(logic.let_through_energy_a2s(40.0, 0.02), 32.0, places=9)

    def test_zero_clearing_time_gives_zero_energy(self):
        self.assertAlmostEqual(logic.let_through_energy_a2s(40.0, 0.0), 0.0, places=12)

    def test_negative_clearing_time_raises(self):
        with self.assertRaises(ValueError):
            logic.let_through_energy_a2s(40.0, -0.01)

    def test_copper_withstand(self):
        self.assertAlmostEqual(
            logic.adiabatic_withstand_a2s("copper", 1.0), 226.0 * 226.0, places=6
        )

    def test_withstand_scales_with_area_squared(self):
        one = logic.adiabatic_withstand_a2s("aluminium", 1.0)
        two = logic.adiabatic_withstand_a2s("aluminium", 2.0)
        self.assertAlmostEqual(two / one, 4.0, places=9)

    def test_unknown_material_raises(self):
        with self.assertRaises(ValueError):
            logic.adiabatic_withstand_a2s("kapton", 1.0)

    def test_zero_cross_section_raises(self):
        with self.assertRaises(ValueError):
            logic.adiabatic_withstand_a2s("copper", 0.0)

    def test_missing_protection_device_is_a_finding(self):
        seg = tether_segment()
        del seg["protection_clearing_time_s"]
        rep = logic.evaluate_fault_protection(seg, 40.0)
        self.assertFalse(rep["compliant"])
        self.assertIn("no protection device", rep["findings"][0])

    def test_fault_current_absent_everywhere_raises(self):
        with self.assertRaises(ValueError):
            logic.evaluate_fault_protection(tether_segment(), None)

    def test_excessive_fault_energy_is_a_finding(self):
        rep = logic.evaluate_fault_protection(tether_segment(), 4000.0)
        self.assertFalse(rep["compliant"])
        self.assertIn("let-through-energy", rep["findings"][0])

    def test_fault_energy_within_withstand_passes(self):
        rep = logic.evaluate_fault_protection(tether_segment(), 40.0)
        self.assertTrue(rep["compliant"])
        self.assertAlmostEqual(rep["let_through_a2s"], 32.0, places=9)


class TestWithinLimit(unittest.TestCase):
    def test_below_limit(self):
        self.assertTrue(logic.within_limit(0.29, 0.3))

    def test_exact_float_sum_at_limit_is_compliant(self):
        self.assertTrue(logic.within_limit(0.1 + 0.2, 0.3))

    def test_genuine_exceedance_still_fails(self):
        self.assertFalse(logic.within_limit(0.3001, 0.3))


class TestSegmentEvaluation(unittest.TestCase):
    def test_nominal_tether_segment_is_compliant(self):
        rep = logic.evaluate_segment(tether_segment(), 2.0)
        self.assertTrue(rep["compliant"])
        self.assertAlmostEqual(rep["voltage_drop_v"], 10.0, places=9)
        self.assertAlmostEqual(rep["dissipation_w"], 20.0, places=9)
        self.assertAlmostEqual(rep["temperature_rise_k"], 10.0, places=9)
        self.assertAlmostEqual(rep["conductor_temperature_c"], 30.0, places=9)

    def test_overheated_segment_is_flagged(self):
        rep = logic.evaluate_segment(tether_segment(insulation_rating_c=25.0), 2.0)
        self.assertFalse(rep["compliant"])
        self.assertTrue(any("insulation rating" in f for f in rep["findings"]))

    def test_temperature_exactly_at_rating_is_compliant(self):
        seg = tether_segment(
            resistance_ohm=0.2,
            thermal_conductance_w_per_k=1.0,
            sink_temperature_c=0.1,
            insulation_rating_c=0.3,
            allowable_drop_v=1.0,
        )
        rep = logic.evaluate_segment(seg, 1.0)
        self.assertTrue(rep["compliant"], rep["findings"])

    def test_current_exactly_at_rated_is_compliant(self):
        rep = logic.evaluate_segment(tether_segment(rated_current_a=2.0), 2.0)
        self.assertTrue(rep["compliant"], rep["findings"])

    def test_overcurrent_is_flagged(self):
        rep = logic.evaluate_segment(tether_segment(rated_current_a=1.0), 2.0)
        self.assertTrue(any("rated current" in f for f in rep["findings"]))

    def test_missing_rated_current_is_a_finding_not_a_pass(self):
        seg = tether_segment()
        del seg["rated_current_a"]
        rep = logic.evaluate_segment(seg, 2.0)
        self.assertFalse(rep["compliant"])
        self.assertTrue(any("no rated-current" in f for f in rep["findings"]))

    def test_voltage_drop_allocation_exceeded_is_flagged(self):
        rep = logic.evaluate_segment(tether_segment(allowable_drop_v=1.0), 2.0)
        self.assertTrue(any("voltage-drop" in f for f in rep["findings"]))

    def test_segment_without_name_raises(self):
        seg = tether_segment()
        del seg["name"]
        with self.assertRaises(ValueError):
            logic.evaluate_segment(seg, 2.0)

    def test_segment_not_a_mapping_raises(self):
        with self.assertRaises(ValueError):
            logic.evaluate_segment(["tether-conductor"], 2.0)

    def test_missing_insulation_rating_raises(self):
        seg = tether_segment()
        del seg["insulation_rating_c"]
        with self.assertRaises(ValueError):
            logic.evaluate_segment(seg, 2.0)


class TestBondingJoint(unittest.TestCase):
    def test_good_joint_has_no_finding(self):
        self.assertEqual(logic.evaluate_bonding_joint(return_segment()), [])

    def test_high_joint_resistance_is_flagged(self):
        findings = logic.evaluate_bonding_joint(return_segment(joint_resistance_ohm=0.01))
        self.assertEqual(len(findings), 1)
        self.assertIn("bonding-joint resistance", findings[0])

    def test_missing_joint_resistance_is_a_finding(self):
        seg = return_segment()
        del seg["joint_resistance_ohm"]
        self.assertIn("no bonding-joint resistance", logic.evaluate_bonding_joint(seg)[0])

    def test_missing_joint_maximum_is_a_finding(self):
        seg = return_segment()
        del seg["max_joint_resistance_ohm"]
        self.assertIn("no maximum bonding-joint", logic.evaluate_bonding_joint(seg)[0])

    def test_joint_check_runs_only_on_return_family(self):
        rep = logic.evaluate_segment(tether_segment(), 2.0)
        self.assertFalse(any("bonding-joint" in f for f in rep["findings"]))

    def test_return_segment_joint_finding_reaches_segment_report(self):
        rep = logic.evaluate_segment(return_segment(joint_resistance_ohm=0.02), 2.0)
        self.assertFalse(rep["compliant"])
        self.assertTrue(any("bonding-joint" in f for f in rep["findings"]))


class TestLoopAssessment(unittest.TestCase):
    def test_nominal_loop_is_compliant(self):
        report = logic.assess_high_current_hazards(loop_config())
        self.assertTrue(report["compliant"], report["findings"])
        self.assertEqual(report["families"], ["return", "tether"])

    def test_loop_voltage_drop_is_summed(self):
        report = logic.assess_high_current_hazards(loop_config())
        self.assertAlmostEqual(report["loop_voltage_drop_v"], 10.02, places=9)

    def test_loop_dissipation_is_summed(self):
        report = logic.assess_high_current_hazards(loop_config())
        self.assertAlmostEqual(report["loop_dissipation_w"], 20.04, places=9)

    def test_loop_without_return_segment_is_flagged(self):
        report = logic.assess_high_current_hazards(
            loop_config(segments=[tether_segment()], loop_drop_budget_v=12.0)
        )
        self.assertFalse(report["compliant"])
        self.assertTrue(any("does not close" in f for f in report["findings"]))

    def test_loop_drop_budget_exceeded_is_flagged(self):
        report = logic.assess_high_current_hazards(loop_config(loop_drop_budget_v=5.0))
        self.assertTrue(any("exceeds budget" in f for f in report["findings"]))

    def test_findings_are_prefixed_with_segment_name(self):
        report = logic.assess_high_current_hazards(
            loop_config(segments=[tether_segment(insulation_rating_c=25.0), return_segment()])
        )
        self.assertTrue(any(f.startswith("tether-conductor-leg:") for f in report["findings"]))

    def test_empty_segment_list_raises(self):
        with self.assertRaises(ValueError):
            logic.assess_high_current_hazards(loop_config(segments=[]))

    def test_config_not_a_mapping_raises(self):
        with self.assertRaises(ValueError):
            logic.assess_high_current_hazards("tether-loop")

    def test_missing_operating_current_raises(self):
        cfg = loop_config()
        del cfg["operating_current_a"]
        with self.assertRaises(ValueError):
            logic.assess_high_current_hazards(cfg)

    def test_fault_finding_propagates_to_loop_report(self):
        report = logic.assess_high_current_hazards(loop_config(fault_current_a=6000.0))
        self.assertFalse(report["compliant"])
        self.assertTrue(any("let-through-energy" in f for f in report["findings"]))


if __name__ == "__main__":
    unittest.main()
