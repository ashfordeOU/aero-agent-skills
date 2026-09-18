"""Contract tests for the clause 7.2.3 layout parasitic-effect logic."""

import math
import unittest

from q6012_parasitic_effect_analysis_logic import (
    EPS0,
    MIN_LENGTH_RADIUS_RATIO,
    REACTANCE_TOLERANCE,
    assess_parasitic_effects,
    bond_wire_inductance_nh,
    capacitive_reactance_ohm,
    coupling_capacitance_ff,
    evaluate_coupling_pair,
    evaluate_net,
    inductive_reactance_ohm,
    insertion_phase_error_deg,
    isolation_db,
    self_resonant_frequency_ghz,
    track_inductance_nh,
    validate_positive,
)

# A 25 um diameter gold bond wire of a typical span, and an on-die track.
WIRE = {
    "name": "rf-in-bond",
    "kind": "bond_wire",
    "length_um": 800.0,
    "radius_um": 12.5,
    "shunt_capacitance_ff": 25.0,
}
TRACK = {
    "name": "drain-feed-track",
    "kind": "track",
    "length_um": 400.0,
    "width_um": 20.0,
    "thickness_um": 4.0,
    "shunt_capacitance_ff": 45.0,
}
PAIR = {
    "name": "in-to-out-sidewall",
    "length_um": 300.0,
    "separation_um": 40.0,
    "facing_height_um": 4.0,
    "relative_permittivity": 12.9,
}


def base_spec(**overrides):
    spec = {
        "nets": [dict(WIRE), dict(TRACK)],
        "coupling_pairs": [dict(PAIR)],
        "max_frequency_ghz": 18.0,
        "reference_impedance_ohm": 50.0,
        "max_reactance_ratio": 2.0,
        "max_phase_error_deg": 45.0,
        "min_isolation_db": 20.0,
        "resonance_margin_factor": 1.5,
    }
    spec.update(overrides)
    return spec


class ValidatePositiveTests(unittest.TestCase):
    def test_returns_float(self):
        self.assertAlmostEqual(validate_positive("x", 3), 3.0, places=9)

    def test_zero_rejected(self):
        with self.assertRaises(ValueError):
            validate_positive("x", 0.0)

    def test_negative_rejected(self):
        with self.assertRaises(ValueError):
            validate_positive("x", -1.0)

    def test_boolean_rejected(self):
        with self.assertRaises(ValueError):
            validate_positive("x", True)

    def test_string_rejected(self):
        with self.assertRaises(ValueError):
            validate_positive("x", "3")

    def test_non_finite_rejected(self):
        with self.assertRaises(ValueError):
            validate_positive("x", float("nan"))


class BondWireInductanceTests(unittest.TestCase):
    def test_typical_span_is_of_order_one_nh_per_mm(self):
        value = bond_wire_inductance_nh(1000.0, 12.5)
        self.assertGreater(value, 0.5)
        self.assertLess(value, 2.0)

    def test_longer_wire_has_more_inductance(self):
        short = bond_wire_inductance_nh(400.0, 12.5)
        long_wire = bond_wire_inductance_nh(1200.0, 12.5)
        self.assertGreater(long_wire, 3.0 * short * 0.9)

    def test_thicker_wire_has_less_inductance(self):
        thin = bond_wire_inductance_nh(800.0, 12.5)
        thick = bond_wire_inductance_nh(800.0, 25.0)
        self.assertLess(thick, thin)

    def test_loop_factor_scales_the_path(self):
        flat = bond_wire_inductance_nh(800.0, 12.5, 1.0)
        looped = bond_wire_inductance_nh(800.0, 12.5, 1.3)
        self.assertGreater(looped, flat)

    def test_loop_factor_below_unity_rejected(self):
        with self.assertRaises(ValueError):
            bond_wire_inductance_nh(800.0, 12.5, 0.8)

    def test_stubby_wire_outside_formula_validity_rejected(self):
        with self.assertRaises(ValueError):
            bond_wire_inductance_nh(30.0, 12.5)

    def test_validity_floor_is_the_named_constant(self):
        self.assertAlmostEqual(MIN_LENGTH_RADIUS_RATIO, 4.0, places=9)

    def test_zero_radius_rejected(self):
        with self.assertRaises(ValueError):
            bond_wire_inductance_nh(800.0, 0.0)


class TrackInductanceTests(unittest.TestCase):
    def test_positive_for_a_long_thin_track(self):
        self.assertGreater(track_inductance_nh(400.0, 20.0, 4.0), 0.0)

    def test_wider_track_has_less_inductance(self):
        narrow = track_inductance_nh(400.0, 10.0, 4.0)
        wide = track_inductance_nh(400.0, 60.0, 4.0)
        self.assertLess(wide, narrow)

    def test_short_fat_track_rejected(self):
        with self.assertRaises(ValueError):
            track_inductance_nh(5.0, 40.0, 10.0)

    def test_non_numeric_width_rejected(self):
        with self.assertRaises(ValueError):
            track_inductance_nh(400.0, "20", 4.0)


class CouplingCapacitanceTests(unittest.TestCase):
    def test_matches_the_parallel_plate_value(self):
        value = coupling_capacitance_ff(300.0, 40.0, 4.0, 12.9)
        expected = EPS0 * 12.9 * (300e-6 * 4e-6) / 40e-6 * 1e15
        self.assertAlmostEqual(value, expected, places=9)

    def test_wider_separation_lowers_the_capacitance(self):
        near = coupling_capacitance_ff(300.0, 20.0, 4.0, 12.9)
        far = coupling_capacitance_ff(300.0, 80.0, 4.0, 12.9)
        self.assertAlmostEqual(near / far, 4.0, places=9)

    def test_permittivity_below_unity_rejected(self):
        with self.assertRaises(ValueError):
            coupling_capacitance_ff(300.0, 40.0, 4.0, 0.5)

    def test_zero_separation_rejected(self):
        with self.assertRaises(ValueError):
            coupling_capacitance_ff(300.0, 0.0, 4.0, 12.9)


class ReactanceTests(unittest.TestCase):
    def test_inductive_reactance_value(self):
        self.assertAlmostEqual(
            inductive_reactance_ohm(1.0, 10.0), 2.0 * math.pi * 10.0, places=9
        )

    def test_inductive_reactance_rises_with_frequency(self):
        low = inductive_reactance_ohm(1.0, 2.0)
        high = inductive_reactance_ohm(1.0, 20.0)
        self.assertAlmostEqual(high / low, 10.0, places=9)

    def test_capacitive_reactance_falls_with_frequency(self):
        low = capacitive_reactance_ohm(50.0, 2.0)
        high = capacitive_reactance_ohm(50.0, 20.0)
        self.assertAlmostEqual(low / high, 10.0, places=9)

    def test_reactances_cross_at_the_self_resonance(self):
        f_sr = self_resonant_frequency_ghz(1.2, 80.0)
        self.assertAlmostEqual(
            inductive_reactance_ohm(1.2, f_sr),
            capacitive_reactance_ohm(80.0, f_sr),
            places=6,
        )

    def test_self_resonance_falls_as_capacitance_grows(self):
        light = self_resonant_frequency_ghz(1.2, 20.0)
        heavy = self_resonant_frequency_ghz(1.2, 80.0)
        self.assertAlmostEqual(light / heavy, 2.0, places=9)

    def test_zero_frequency_rejected(self):
        with self.assertRaises(ValueError):
            inductive_reactance_ohm(1.0, 0.0)


class PhaseAndIsolationTests(unittest.TestCase):
    def test_phase_error_is_zero_limit_for_a_vanishing_reactance(self):
        self.assertLess(insertion_phase_error_deg(1e-9, 50.0), 1e-6)

    def test_phase_error_at_twice_the_impedance_is_forty_five_degrees(self):
        self.assertAlmostEqual(insertion_phase_error_deg(100.0, 50.0), 45.0, places=9)

    def test_phase_error_grows_with_reactance(self):
        small = insertion_phase_error_deg(10.0, 50.0)
        large = insertion_phase_error_deg(90.0, 50.0)
        self.assertGreater(large, small)

    def test_isolation_at_equal_reactance_and_half_impedance(self):
        self.assertAlmostEqual(
            isolation_db(25.0, 50.0), 20.0 * math.log10(math.sqrt(2.0)), places=9
        )

    def test_tighter_coupling_lowers_the_isolation(self):
        loose = isolation_db(5000.0, 50.0)
        tight = isolation_db(100.0, 50.0)
        self.assertGreater(loose, tight)

    def test_isolation_rejects_a_zero_reactance(self):
        with self.assertRaises(ValueError):
            isolation_db(0.0, 50.0)


class EvaluateNetTests(unittest.TestCase):
    def test_bond_wire_record_carries_every_field(self):
        record = evaluate_net(dict(WIRE), 18.0, 50.0)
        for key in (
            "name",
            "inductance_nh",
            "series_reactance_ohm",
            "reactance_ratio",
            "phase_error_deg",
            "self_resonance_ghz",
        ):
            self.assertIn(key, record)

    def test_reactance_ratio_is_reactance_over_impedance(self):
        record = evaluate_net(dict(WIRE), 18.0, 50.0)
        self.assertAlmostEqual(
            record["reactance_ratio"], record["series_reactance_ohm"] / 50.0, places=9
        )

    def test_track_net_uses_the_track_expression(self):
        record = evaluate_net(dict(TRACK), 18.0, 50.0)
        self.assertAlmostEqual(
            record["inductance_nh"], track_inductance_nh(400.0, 20.0, 4.0), places=9
        )

    def test_unknown_kind_rejected(self):
        bad = dict(WIRE)
        bad["kind"] = "ribbon"
        with self.assertRaises(ValueError):
            evaluate_net(bad, 18.0, 50.0)

    def test_missing_name_rejected(self):
        bad = dict(WIRE)
        del bad["name"]
        with self.assertRaises(ValueError):
            evaluate_net(bad, 18.0, 50.0)

    def test_missing_shunt_capacitance_rejected(self):
        bad = dict(WIRE)
        del bad["shunt_capacitance_ff"]
        with self.assertRaises(ValueError):
            evaluate_net(bad, 18.0, 50.0)

    def test_non_mapping_net_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_net(["rf-in-bond"], 18.0, 50.0)

    def test_coupling_pair_record_is_consistent(self):
        record = evaluate_coupling_pair(dict(PAIR), 18.0, 50.0)
        self.assertAlmostEqual(
            record["coupling_reactance_ohm"],
            capacitive_reactance_ohm(record["coupling_capacitance_ff"], 18.0),
            places=9,
        )

    def test_coupling_pair_without_name_rejected(self):
        bad = dict(PAIR)
        bad["name"] = "  "
        with self.assertRaises(ValueError):
            evaluate_coupling_pair(bad, 18.0, 50.0)


class AssessParasiticEffectsTests(unittest.TestCase):
    def test_generous_budgets_are_compliant(self):
        result = assess_parasitic_effects(base_spec())
        self.assertTrue(result["compliant"], result["findings"])
        self.assertEqual(result["findings"], [])

    def test_two_net_records_returned(self):
        result = assess_parasitic_effects(base_spec())
        self.assertEqual(len(result["net_records"]), 2)

    def test_dominant_reactance_net_is_the_bond_wire(self):
        result = assess_parasitic_effects(base_spec())
        self.assertEqual(result["dominant_reactance_net"], "rf-in-bond")

    def test_tight_reactance_budget_raises_a_finding(self):
        result = assess_parasitic_effects(base_spec(max_reactance_ratio=0.01))
        self.assertFalse(result["compliant"])
        self.assertTrue(any("series reactance" in f for f in result["findings"]))

    def test_tight_phase_budget_raises_a_finding(self):
        result = assess_parasitic_effects(base_spec(max_phase_error_deg=0.01))
        self.assertTrue(any("phase error" in f for f in result["findings"]))

    def test_high_resonance_floor_raises_a_finding(self):
        result = assess_parasitic_effects(base_spec(resonance_margin_factor=50.0))
        self.assertTrue(any("self-resonates" in f for f in result["findings"]))

    def test_resonance_floor_is_the_declared_multiple(self):
        result = assess_parasitic_effects(base_spec(resonance_margin_factor=3.0))
        self.assertAlmostEqual(result["resonance_floor_ghz"], 54.0, places=9)

    def test_high_isolation_requirement_raises_a_finding(self):
        result = assess_parasitic_effects(base_spec(min_isolation_db=200.0))
        self.assertTrue(any("isolation" in f for f in result["findings"]))

    def test_no_declared_pairs_is_itself_a_finding(self):
        result = assess_parasitic_effects(base_spec(coupling_pairs=[]))
        self.assertFalse(result["compliant"])
        self.assertTrue(any("no conductor pairs" in f for f in result["findings"]))

    def test_budget_exactly_met_stays_compliant(self):
        spec = base_spec()
        probe = assess_parasitic_effects(spec)
        ratio = max(r["reactance_ratio"] for r in probe["net_records"])
        result = assess_parasitic_effects(base_spec(max_reactance_ratio=ratio))
        self.assertTrue(any("series reactance" in f for f in result["findings"]) is False)

    def test_tolerance_is_a_named_constant(self):
        self.assertAlmostEqual(REACTANCE_TOLERANCE, 1e-9, places=15)

    def test_duplicate_net_names_rejected(self):
        duplicate = dict(TRACK)
        duplicate["name"] = "rf-in-bond"
        with self.assertRaises(ValueError):
            assess_parasitic_effects(base_spec(nets=[dict(WIRE), duplicate]))

    def test_empty_net_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_parasitic_effects(base_spec(nets=[]))

    def test_missing_key_rejected(self):
        spec = base_spec()
        del spec["reference_impedance_ohm"]
        with self.assertRaises(ValueError):
            assess_parasitic_effects(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_parasitic_effects(["nets"])

    def test_resonance_margin_below_unity_rejected(self):
        with self.assertRaises(ValueError):
            assess_parasitic_effects(base_spec(resonance_margin_factor=0.5))

    def test_negative_max_frequency_rejected(self):
        with self.assertRaises(ValueError):
            assess_parasitic_effects(base_spec(max_frequency_ghz=-18.0))

    def test_reactance_scales_with_the_top_frequency(self):
        low = assess_parasitic_effects(base_spec(max_frequency_ghz=9.0))
        high = assess_parasitic_effects(base_spec(max_frequency_ghz=18.0))
        low_x = low["net_records"][0]["series_reactance_ohm"]
        high_x = high["net_records"][0]["series_reactance_ohm"]
        self.assertAlmostEqual(high_x / low_x, 2.0, places=9)


if __name__ == "__main__":
    unittest.main()
