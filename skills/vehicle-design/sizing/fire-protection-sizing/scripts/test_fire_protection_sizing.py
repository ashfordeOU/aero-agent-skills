"""Contract test for vehicle-design/sizing/fire-protection-sizing.

Deterministic stdlib unittest suite. Run offline:

    python3 scripts/test_fire_protection_sizing.py

Covers the wave-35 contract: the Class C cargo and engine nacelle zone
worked examples (agent mass, vapor volume, closure), the concentration
closure identity and linear volume scaling, the installed agent rollup
from bottle and shot count, the discharge nozzle count with the
powerplant floor, the coverage verdict (installed below required FAIL,
equal PASS), the fire_protection_summary convenience dict, dict key
conventions, determinism, and ValueError rejection of non-physical
inputs.
"""

import unittest

import fire_protection_sizing_logic as fps

CARGO_VOLUME = 40.0
CARGO_CONC = 5.0
CARGO_MASS = 13.324450366422385
CARGO_VAPOR = 2.1052631578947367

ENGINE_VOLUME = 1.8
ENGINE_CONC = 6.0
ENGINE_MASS = 0.7271747912739026
ENGINE_INSTALLED = 2.9086991650956104


class TestAgentMass(unittest.TestCase):
    """agent_mass total-flooding sizing for the reference zones."""

    def test_cargo_worked_example_mass(self):
        out = fps.agent_mass(CARGO_VOLUME, CARGO_CONC)
        self.assertAlmostEqual(out["mass_kg"], CARGO_MASS, delta=1e-6)
        self.assertAlmostEqual(out["mass_kg"], 13.32, delta=1e-2)

    def test_cargo_vapor_volume(self):
        out = fps.agent_mass(CARGO_VOLUME, CARGO_CONC)
        self.assertAlmostEqual(out["vapor_volume_m3"], CARGO_VAPOR, delta=1e-6)
        self.assertAlmostEqual(out["vapor_volume_m3"], 2.105, delta=1e-3)

    def test_cargo_closure_identity_five_percent(self):
        out = fps.agent_mass(CARGO_VOLUME, CARGO_CONC)
        self.assertAlmostEqual(out["closure_fraction"], 0.05, delta=1e-4)

    def test_engine_zone_worked_example_mass(self):
        out = fps.agent_mass(ENGINE_VOLUME, ENGINE_CONC)
        self.assertAlmostEqual(out["mass_kg"], ENGINE_MASS, delta=1e-6)
        self.assertAlmostEqual(out["mass_kg"], 0.727, delta=1e-3)

    def test_engine_zone_closure_six_percent(self):
        out = fps.agent_mass(ENGINE_VOLUME, ENGINE_CONC)
        self.assertAlmostEqual(out["closure_fraction"], 0.06, delta=1e-4)

    def test_mass_scales_linearly_with_volume_doubling(self):
        half = fps.agent_mass(CARGO_VOLUME, CARGO_CONC)["mass_kg"]
        double = fps.agent_mass(2 * CARGO_VOLUME, CARGO_CONC)["mass_kg"]
        self.assertAlmostEqual(double, 2 * half, delta=1e-6)
        self.assertAlmostEqual(double, 26.64, delta=1e-2)

    def test_mass_zero_or_negative_volume_raises(self):
        for bad in (0.0, -1.0, -40.0):
            with self.assertRaises(ValueError):
                fps.agent_mass(bad, CARGO_CONC)

    def test_mass_concentration_out_of_range_raises(self):
        for bad in (0.0, 100.0, -5.0, 150.0):
            with self.assertRaises(ValueError):
                fps.agent_mass(CARGO_VOLUME, bad)

    def test_mass_nonpositive_spec_volume_raises(self):
        for bad in (0.0, -0.1):
            with self.assertRaises(ValueError):
                fps.agent_mass(CARGO_VOLUME, CARGO_CONC, spec_volume_m3_kg=bad)

    def test_agent_mass_dict_keys(self):
        self.assertEqual(
            list(fps.agent_mass(CARGO_VOLUME, CARGO_CONC).keys()),
            ["mass_kg", "vapor_volume_m3", "closure_fraction"])

    def test_agent_mass_determinism(self):
        first = fps.agent_mass(CARGO_VOLUME, CARGO_CONC)
        second = fps.agent_mass(CARGO_VOLUME, CARGO_CONC)
        self.assertEqual(first, second)


class TestConcentrationClosure(unittest.TestCase):
    """concentration_closure identity and bounds."""

    def test_closure_of_computed_mass_equals_target(self):
        frac = fps.concentration_closure(CARGO_VOLUME, CARGO_MASS, fps.S_AGENT_DEFAULT)
        self.assertAlmostEqual(frac, 0.05, delta=1e-6)

    def test_closure_zero_mass_is_zero(self):
        frac = fps.concentration_closure(CARGO_VOLUME, 0.0, fps.S_AGENT_DEFAULT)
        self.assertEqual(frac, 0.0)

    def test_closure_increases_with_mass(self):
        low = fps.concentration_closure(CARGO_VOLUME, 1.0, fps.S_AGENT_DEFAULT)
        high = fps.concentration_closure(CARGO_VOLUME, 20.0, fps.S_AGENT_DEFAULT)
        self.assertGreater(high, low)

    def test_closure_value_errors(self):
        with self.assertRaises(ValueError):
            fps.concentration_closure(0.0, 1.0, fps.S_AGENT_DEFAULT)
        with self.assertRaises(ValueError):
            fps.concentration_closure(CARGO_VOLUME, -0.5, fps.S_AGENT_DEFAULT)
        with self.assertRaises(ValueError):
            fps.concentration_closure(CARGO_VOLUME, 1.0, 0.0)


class TestInstalledAgent(unittest.TestCase):
    """installed_agent rollup from bottles and shots."""

    def test_engine_installation_two_bottles_two_shots(self):
        out = fps.installed_agent(ENGINE_MASS, 2, 2)
        self.assertAlmostEqual(out["installed_kg"], ENGINE_INSTALLED, delta=1e-6)
        self.assertAlmostEqual(out["installed_kg"], 2.91, delta=1e-2)
        self.assertEqual(out["mass_per_shot_kg"], ENGINE_MASS)

    def test_single_bottle_single_shot_equals_per_shot(self):
        out = fps.installed_agent(ENGINE_MASS, 1, 1)
        self.assertAlmostEqual(out["installed_kg"], ENGINE_MASS, delta=1e-12)

    def test_installed_scales_with_shots_and_bottles(self):
        base = fps.installed_agent(ENGINE_MASS, 2, 2)["installed_kg"]
        double = fps.installed_agent(ENGINE_MASS, 2, 4)["installed_kg"]
        self.assertAlmostEqual(double, 2 * base, delta=1e-6)

    def test_installed_agent_value_errors(self):
        with self.assertRaises(ValueError):
            fps.installed_agent(0.0, 2, 2)
        with self.assertRaises(ValueError):
            fps.installed_agent(-1.0, 2, 2)
        with self.assertRaises(ValueError):
            fps.installed_agent(ENGINE_MASS, 0, 2)
        with self.assertRaises(ValueError):
            fps.installed_agent(ENGINE_MASS, 2, 0)

    def test_installed_agent_dict_keys(self):
        self.assertEqual(
            list(fps.installed_agent(ENGINE_MASS, 2, 2).keys()),
            ["installed_kg", "mass_per_shot_kg"])


class TestNozzleCount(unittest.TestCase):
    """nozzle_count zone coverage."""

    def test_cargo_40_m3_ten_nozzles(self):
        self.assertEqual(fps.nozzle_count(CARGO_VOLUME, False), 10)

    def test_engine_zone_floor_two_nozzles(self):
        self.assertEqual(fps.nozzle_count(ENGINE_VOLUME, True), 2)

    def test_small_cargo_one_nozzle(self):
        self.assertEqual(fps.nozzle_count(1.0, False), 1)

    def test_partial_volume_rounds_up(self):
        self.assertEqual(fps.nozzle_count(5.0, False), 2)

    def test_powerplant_floor_below_one_m3(self):
        self.assertEqual(fps.nozzle_count(0.5, True), 2)

    def test_nozzle_count_value_errors(self):
        for bad in (0.0, -2.0):
            with self.assertRaises(ValueError):
                fps.nozzle_count(bad, False)


class TestCoverageVerdict(unittest.TestCase):
    """coverage_verdict PASS/FAIL comparison."""

    def test_fail_when_installed_below_required(self):
        out = fps.coverage_verdict(10.0, CARGO_MASS)
        self.assertEqual(out["verdict"], "FAIL")
        self.assertLess(out["margin_kg"], 0.0)

    def test_pass_when_installed_equal_to_required(self):
        out = fps.coverage_verdict(CARGO_MASS, CARGO_MASS)
        self.assertEqual(out["verdict"], "PASS")
        self.assertAlmostEqual(out["margin_kg"], 0.0, delta=1e-12)

    def test_pass_when_installed_above_required(self):
        out = fps.coverage_verdict(ENGINE_INSTALLED, ENGINE_MASS)
        self.assertEqual(out["verdict"], "PASS")

    def test_coverage_verdict_value_errors(self):
        with self.assertRaises(ValueError):
            fps.coverage_verdict(-1.0, CARGO_MASS)
        with self.assertRaises(ValueError):
            fps.coverage_verdict(10.0, -1.0)


class TestSummary(unittest.TestCase):
    """fire_protection_summary one-call convenience."""

    def test_summary_cargo_defaults_pass_equal(self):
        out = fps.fire_protection_summary(CARGO_VOLUME, CARGO_CONC, False)
        self.assertAlmostEqual(out["required_mass_kg"], CARGO_MASS, delta=1e-6)
        self.assertAlmostEqual(out["closure_fraction"], 0.05, delta=1e-4)
        self.assertAlmostEqual(out["installed_kg"], CARGO_MASS, delta=1e-6)
        self.assertEqual(out["nozzle_count"], 10)
        self.assertEqual(out["coverage_verdict"], "PASS")

    def test_summary_engine_zone_multi_bottle_pass(self):
        out = fps.fire_protection_summary(ENGINE_VOLUME, ENGINE_CONC, True,
                                          n_bottles=2, shots_per_bottle=2)
        self.assertAlmostEqual(out["required_mass_kg"], ENGINE_MASS, delta=1e-6)
        self.assertAlmostEqual(out["installed_kg"], ENGINE_INSTALLED, delta=1e-6)
        self.assertAlmostEqual(out["installed_kg"], 2.91, delta=1e-2)
        self.assertEqual(out["nozzle_count"], 2)
        self.assertEqual(out["coverage_verdict"], "PASS")

    def test_summary_dict_keys(self):
        out = fps.fire_protection_summary(CARGO_VOLUME, CARGO_CONC, False)
        self.assertEqual(list(out.keys()), [
            "required_mass_kg", "closure_fraction", "installed_kg",
            "nozzle_count", "coverage_verdict"])

    def test_summary_propagates_value_errors(self):
        with self.assertRaises(ValueError):
            fps.fire_protection_summary(0.0, CARGO_CONC, False)
        with self.assertRaises(ValueError):
            fps.fire_protection_summary(CARGO_VOLUME, 0.0, False)
        with self.assertRaises(ValueError):
            fps.fire_protection_summary(CARGO_VOLUME, CARGO_CONC, False, n_bottles=0)

    def test_summary_determinism(self):
        first = fps.fire_protection_summary(CARGO_VOLUME, CARGO_CONC, False)
        second = fps.fire_protection_summary(CARGO_VOLUME, CARGO_CONC, False)
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
