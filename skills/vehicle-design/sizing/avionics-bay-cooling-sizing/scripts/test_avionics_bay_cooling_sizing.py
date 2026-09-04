"""Contract test for vehicle-design/sizing/avionics-bay-cooling-sizing.

Deterministic stdlib unittest suite. Run offline:

    python3 scripts/test_avionics_bay_cooling_sizing.py

Covers the wave-35 contract: reference bay heat load rollup, cooling
mass flow from the allowable temperature rise, volumetric and CFM
conversion, per-LRU case temperatures and verdicts, the bay PASS/FAIL
verdict, the scaling identities (halving the rise doubles the flow,
doubling the heat doubles the flow, doubling the conductance halves
the rise, zero-power LRU sits at the inlet air temperature), dict key
conventions, determinism, and ValueError rejection of non-physical
inputs.
"""

import unittest

import avionics_bay_cooling_sizing_logic as abc

REF_POWERS = [400, 350, 300, 550, 450, 450]
REF_LIMITS = [60, 60, 60, 65, 60, 60]


class TestBayHeatLoad(unittest.TestCase):
    """bay_heat_load rollup of the LRU dissipations."""

    def test_reference_six_lru_sum(self):
        result = abc.bay_heat_load(REF_POWERS)
        self.assertAlmostEqual(result["total_w"], 2500.0, places=6)
        self.assertEqual(result["per_lru_w"], REF_POWERS)

    def test_single_lru(self):
        result = abc.bay_heat_load([120.0])
        self.assertAlmostEqual(result["total_w"], 120.0, places=9)
        self.assertEqual(result["per_lru_w"], [120.0])

    def test_empty_dict_raises(self):
        with self.assertRaises(ValueError):
            abc.bay_heat_load({})

    def test_negative_power_raises(self):
        with self.assertRaises(ValueError):
            abc.bay_heat_load([400, -50, 300])

    def test_dict_input_preserves_labels(self):
        result = abc.bay_heat_load({"nav": 400.0, "comm": 350.0})
        self.assertAlmostEqual(result["total_w"], 750.0, places=9)
        self.assertEqual(result["per_lru_w"],
                         {"nav": 400.0, "comm": 350.0})


class TestCoolingMassFlow(unittest.TestCase):
    """cooling_mass_flow sizing from the allowable temperature rise."""

    def test_reference_bay_mass_flow(self):
        result = abc.cooling_mass_flow(2500.0, 25.0, 55.0)
        self.assertAlmostEqual(result["mass_flow_kg_s"],
                               0.08291873963515754, places=8)
        # independently verified magnitude bound at prep
        self.assertGreater(result["mass_flow_kg_s"], 0.08)
        self.assertLess(result["mass_flow_kg_s"], 0.09)

    def test_exhaust_temp_equals_limit(self):
        result = abc.cooling_mass_flow(2500.0, 25.0, 55.0)
        self.assertEqual(result["exhaust_temp_c"], 55.0)

    def test_zero_heat_zero_flow(self):
        result = abc.cooling_mass_flow(0.0, 25.0, 55.0)
        self.assertEqual(result["mass_flow_kg_s"], 0.0)
        self.assertEqual(result["exhaust_temp_c"], 55.0)

    def test_doubled_rise_halves_flow(self):
        base = abc.cooling_mass_flow(2500.0, 25.0, 55.0)
        wide = abc.cooling_mass_flow(2500.0, 25.0, 85.0)
        self.assertAlmostEqual(wide["mass_flow_kg_s"],
                               base["mass_flow_kg_s"] / 2.0, places=9)

    def test_doubled_heat_doubles_flow(self):
        base = abc.cooling_mass_flow(2500.0, 25.0, 55.0)
        heavy = abc.cooling_mass_flow(5000.0, 25.0, 55.0)
        self.assertAlmostEqual(heavy["mass_flow_kg_s"],
                               2.0 * base["mass_flow_kg_s"], places=9)

    def test_negative_heat_raises(self):
        with self.assertRaises(ValueError):
            abc.cooling_mass_flow(-1.0, 25.0, 55.0)

    def test_nonpositive_temperature_difference_raises(self):
        with self.assertRaises(ValueError):
            abc.cooling_mass_flow(2500.0, 55.0, 55.0)
        with self.assertRaises(ValueError):
            abc.cooling_mass_flow(2500.0, 60.0, 55.0)


class TestVolumetricFlow(unittest.TestCase):
    """volumetric_flow conversion to m3/s and CFM."""

    def test_reference_bay_volumetric(self):
        result = abc.volumetric_flow(0.08291873963515754)
        self.assertAlmostEqual(result["flow_m3_s"],
                               0.06909894969596463, places=8)
        # independently verified magnitude bound at prep
        self.assertAlmostEqual(result["flow_cfm"], 146.4, places=1)

    def test_one_kg_s_reference(self):
        result = abc.volumetric_flow(1.0)
        self.assertAlmostEqual(result["flow_m3_s"],
                               1.0 / 1.2, places=6)
        self.assertAlmostEqual(result["flow_cfm"], 1765.7, places=1)

    def test_negative_mass_flow_raises(self):
        with self.assertRaises(ValueError):
            abc.volumetric_flow(-0.1)

    def test_nonpositive_density_raises(self):
        with self.assertRaises(ValueError):
            abc.volumetric_flow(0.5, density=0.0)
        with self.assertRaises(ValueError):
            abc.volumetric_flow(0.5, density=-1.2)


class TestLruCaseTemperature(unittest.TestCase):
    """lru_case_temperature from power and case-to-air conductance."""

    def test_reference_300w_lru(self):
        result = abc.lru_case_temperature(300.0, 12.0, 25.0)
        self.assertAlmostEqual(result["rise_k"], 25.0, places=9)
        self.assertAlmostEqual(result["case_temp_c"], 50.0, places=9)

    def test_550w_lru_undersized_heat_path(self):
        result = abc.lru_case_temperature(550.0, 12.0, 25.0)
        self.assertAlmostEqual(result["rise_k"], 45.833333333333336,
                               places=6)
        self.assertAlmostEqual(result["case_temp_c"],
                               70.83333333333334, places=6)

    def test_zero_power_sits_at_inlet_temp(self):
        result = abc.lru_case_temperature(0.0, 12.0, 25.0)
        self.assertEqual(result["case_temp_c"], 25.0)
        self.assertEqual(result["rise_k"], 0.0)

    def test_doubled_conductance_halves_rise(self):
        base = abc.lru_case_temperature(300.0, 12.0, 25.0)
        doubled = abc.lru_case_temperature(300.0, 24.0, 25.0)
        self.assertAlmostEqual(doubled["rise_k"],
                               base["rise_k"] / 2.0, places=9)

    def test_nonphysical_power_and_conductance_raise(self):
        with self.assertRaises(ValueError):
            abc.lru_case_temperature(-5.0, 12.0, 25.0)
        with self.assertRaises(ValueError):
            abc.lru_case_temperature(300.0, 0.0, 25.0)
        with self.assertRaises(ValueError):
            abc.lru_case_temperature(300.0, -3.0, 25.0)


class TestCaseVerdict(unittest.TestCase):
    """case_verdict PASS/FAIL with the margin convention."""

    def test_pass_with_positive_margin(self):
        result = abc.case_verdict(50.0, 60.0)
        self.assertEqual(result["verdict"], "PASS")
        self.assertAlmostEqual(result["margin_k"], 10.0, places=9)

    def test_fail_with_negative_margin(self):
        result = abc.case_verdict(70.83333333333334, 65.0)
        self.assertEqual(result["verdict"], "FAIL")
        self.assertAlmostEqual(result["margin_k"], -5.833333333333329,
                               places=6)

    def test_equal_case_and_limit_passes_zero_margin(self):
        result = abc.case_verdict(60.0, 60.0)
        self.assertEqual(result["verdict"], "PASS")
        self.assertEqual(result["margin_k"], 0.0)

    def test_limit_below_absolute_zero_raises(self):
        with self.assertRaises(ValueError):
            abc.case_verdict(50.0, -300.0)

    def test_extreme_case_temps_accepted(self):
        self.assertEqual(abc.case_verdict(200.0, 60.0)["verdict"], "FAIL")
        self.assertEqual(abc.case_verdict(-40.0, 60.0)["verdict"], "PASS")


class TestBaySummary(unittest.TestCase):
    """bay_cooling_summary rollup and bay verdict."""

    def test_reference_summary_full_rollup(self):
        result = abc.bay_cooling_summary(REF_POWERS, 25.0, 55.0,
                                         REF_LIMITS)
        self.assertAlmostEqual(result["total_w"], 2500.0, places=6)
        self.assertAlmostEqual(result["mass_flow_kg_s"],
                               0.08291873963515754, places=8)
        self.assertAlmostEqual(result["flow_cfm"], 146.4, places=1)
        self.assertEqual(result["exhaust_temp_c"], 55.0)
        self.assertAlmostEqual(result["case_temps_c"][2], 50.0,
                               places=9)
        self.assertAlmostEqual(result["case_temps_c"][3],
                               70.83333333333334, places=6)
        self.assertEqual(result["case_verdicts"][2], "PASS")
        self.assertEqual(result["case_verdicts"][3], "FAIL")
        self.assertEqual(result["bay_verdict"], "FAIL")

    def test_reduced_set_all_pass_bay(self):
        powers = [400, 350, 300, 300, 350, 400]
        result = abc.bay_cooling_summary(powers, 25.0, 55.0, REF_LIMITS)
        self.assertEqual(result["bay_verdict"], "PASS")
        for verdict in result["case_verdicts"].values():
            self.assertEqual(verdict, "PASS")

    def test_summary_dict_keys_exactly_documented(self):
        result = abc.bay_cooling_summary(REF_POWERS, 25.0, 55.0,
                                         REF_LIMITS)
        self.assertEqual(
            sorted(result.keys()),
            ["bay_verdict", "case_temps_c", "case_verdicts",
             "exhaust_temp_c", "flow_cfm", "flow_m3_s",
             "mass_flow_kg_s", "total_w"])

    def test_limit_list_length_mismatch_raises(self):
        with self.assertRaises(ValueError):
            abc.bay_cooling_summary(REF_POWERS, 25.0, 55.0,
                                    [60, 60, 60])

    def test_determinism_identical_inputs(self):
        args = (REF_POWERS, 25.0, 55.0, REF_LIMITS)
        self.assertEqual(abc.bay_cooling_summary(*args),
                         abc.bay_cooling_summary(*args))

    def test_documented_module_constants(self):
        self.assertEqual(abc.AIR_CP, 1005.0)
        self.assertEqual(abc.DEFAULT_AIR_DENSITY, 1.2)
        self.assertEqual(abc.CFM_PER_M3S, 2118.88)


if __name__ == "__main__":
    unittest.main()
