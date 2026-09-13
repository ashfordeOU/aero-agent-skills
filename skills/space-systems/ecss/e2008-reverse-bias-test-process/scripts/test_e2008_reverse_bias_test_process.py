"""Contract tests for the clause 6.4.3.14.2 reverse current-voltage record logic."""

import unittest

from e2008_reverse_bias_test_process_logic import (
    DIODE_COUPLINGS,
    assess_assembly,
    assess_reverse_bias_process,
    is_illuminated,
    largest_voltage_step,
    normalize_coupling,
    peak_dissipation,
    record_is_required,
    sweep_extent_v,
    validate_requirement,
    validate_sweep,
    validate_sweep_point,
)

# A sweep out to sixteen volts of reverse bias in two-volt steps, under one
# sun. The current climbs as the assembly is pushed past its knee.
POINTS = [
    {"reverse_voltage_v": 0.0, "reverse_current_a": 0.480},
    {"reverse_voltage_v": 2.0, "reverse_current_a": 0.484},
    {"reverse_voltage_v": 4.0, "reverse_current_a": 0.490},
    {"reverse_voltage_v": 6.0, "reverse_current_a": 0.500},
    {"reverse_voltage_v": 8.0, "reverse_current_a": 0.520},
    {"reverse_voltage_v": 10.0, "reverse_current_a": 0.560},
    {"reverse_voltage_v": 12.0, "reverse_current_a": 0.640},
    {"reverse_voltage_v": 14.0, "reverse_current_a": 0.800},
    {"reverse_voltage_v": 16.0, "reverse_current_a": 1.100},
]

REQUIREMENT = {
    "min_irradiance_w_m2": 1000.0,
    "required_extent_v": 15.0,
    "max_step_v": 2.0,
}


def _sweep(points=None, irradiance_w_m2=1367.0):
    return {
        "irradiance_w_m2": irradiance_w_m2,
        "points": [dict(p) for p in (points if points is not None else POINTS)],
    }


def _assembly(assembly_id="a1", diode_coupling="no-protection-diode", sweep=True,
              **sweep_overrides):
    record = {"assembly_id": assembly_id, "diode_coupling": diode_coupling}
    if sweep:
        record["sweep"] = _sweep(**sweep_overrides)
    return record


class CouplingTests(unittest.TestCase):
    def test_cell_coupled_diode_exempts_the_assembly(self):
        self.assertFalse(record_is_required("cell-coupled-protection-diode"))

    def test_string_coupled_diode_does_not_exempt(self):
        self.assertTrue(record_is_required("string-coupled-protection-diode"))

    def test_section_coupled_diode_does_not_exempt(self):
        self.assertTrue(record_is_required("section-coupled-protection-diode"))

    def test_absent_diode_leaves_the_assembly_in_scope(self):
        self.assertTrue(record_is_required("no-protection-diode"))

    def test_case_and_space_are_absorbed(self):
        self.assertEqual(
            normalize_coupling("  Cell-Coupled-Protection-Diode "),
            "cell-coupled-protection-diode",
        )

    def test_unknown_placement_rejected(self):
        with self.assertRaises(ValueError):
            normalize_coupling("diode-somewhere")

    def test_non_string_placement_rejected(self):
        with self.assertRaises(ValueError):
            normalize_coupling(None)

    def test_exactly_one_placement_exempts(self):
        self.assertEqual(sum(1 for v in DIODE_COUPLINGS.values() if v), 1)


class IlluminationTests(unittest.TestCase):
    def test_one_sun_clears_the_floor(self):
        self.assertTrue(is_illuminated(1367.0, 1000.0))

    def test_irradiance_exactly_on_the_floor_counts_as_illuminated(self):
        self.assertTrue(is_illuminated(1000.0, 1000.0))

    def test_dark_sweep_is_not_illuminated(self):
        self.assertFalse(is_illuminated(0.0, 1000.0))

    def test_negative_irradiance_rejected(self):
        with self.assertRaises(ValueError):
            is_illuminated(-5.0, 1000.0)

    def test_zero_floor_rejected(self):
        with self.assertRaises(ValueError):
            is_illuminated(1000.0, 0.0)


class SweepValidationTests(unittest.TestCase):
    def test_valid_point_returns_floats(self):
        record = validate_sweep_point(POINTS[1])
        self.assertAlmostEqual(record["reverse_voltage_v"], 2.0, places=9)

    def test_missing_point_key_rejected(self):
        with self.assertRaises(ValueError):
            validate_sweep_point({"reverse_voltage_v": 2.0})

    def test_negative_current_rejected(self):
        with self.assertRaises(ValueError):
            validate_sweep_point(
                {"reverse_voltage_v": 2.0, "reverse_current_a": -0.1}
            )

    def test_single_point_is_not_a_sweep(self):
        with self.assertRaises(ValueError):
            validate_sweep(POINTS[:1])

    def test_repeated_voltage_rejected(self):
        points = [dict(p) for p in POINTS[:3]]
        points[2]["reverse_voltage_v"] = points[1]["reverse_voltage_v"]
        with self.assertRaises(ValueError):
            validate_sweep(points)

    def test_backward_step_rejected(self):
        points = [dict(p) for p in POINTS[:4]]
        points[3]["reverse_voltage_v"] = 1.0
        with self.assertRaises(ValueError):
            validate_sweep(points)

    def test_non_sequence_rejected(self):
        with self.assertRaises(ValueError):
            validate_sweep({"reverse_voltage_v": 2.0})


class SweepMetricTests(unittest.TestCase):
    def test_extent_is_the_last_reverse_voltage(self):
        self.assertAlmostEqual(sweep_extent_v(POINTS), 16.0, places=9)

    def test_uniform_sweep_has_the_nominal_step(self):
        self.assertAlmostEqual(largest_voltage_step(POINTS), 2.0, places=9)

    def test_widest_gap_is_reported(self):
        points = [dict(p) for p in POINTS]
        del points[5]
        self.assertAlmostEqual(largest_voltage_step(points), 4.0, places=9)

    def test_peak_dissipation_is_at_the_deepest_point(self):
        peak = peak_dissipation(POINTS)
        self.assertAlmostEqual(peak["reverse_voltage_v"], 16.0, places=9)
        self.assertAlmostEqual(peak["power_w"], 16.0 * 1.100, places=9)

    def test_peak_dissipation_need_not_be_the_last_point(self):
        points = [dict(p) for p in POINTS]
        points[-1]["reverse_current_a"] = 0.010
        peak = peak_dissipation(points)
        self.assertAlmostEqual(peak["reverse_voltage_v"], 14.0, places=9)


class RequirementTests(unittest.TestCase):
    def test_valid_requirement_returns_floats(self):
        wanted = validate_requirement(REQUIREMENT)
        self.assertAlmostEqual(wanted["required_extent_v"], 15.0, places=9)

    def test_missing_requirement_key_rejected(self):
        broken = dict(REQUIREMENT)
        del broken["max_step_v"]
        with self.assertRaises(ValueError):
            validate_requirement(broken)

    def test_zero_step_limit_rejected(self):
        with self.assertRaises(ValueError):
            validate_requirement(dict(REQUIREMENT, max_step_v=0.0))


class AssemblyAssessmentTests(unittest.TestCase):
    def test_good_record_produces_no_findings(self):
        outcome = assess_assembly(_assembly(), REQUIREMENT)
        self.assertEqual(outcome["findings"], [])
        self.assertTrue(outcome["record_present"])
        self.assertTrue(outcome["illuminated"])

    def test_exempt_assembly_without_a_record_is_clean(self):
        outcome = assess_assembly(
            _assembly(diode_coupling="cell-coupled-protection-diode", sweep=False),
            REQUIREMENT,
        )
        self.assertFalse(outcome["record_required"])
        self.assertEqual(outcome["findings"], [])

    def test_in_scope_assembly_without_a_record_is_a_finding(self):
        outcome = assess_assembly(_assembly(sweep=False), REQUIREMENT)
        self.assertEqual(len(outcome["findings"]), 1)
        self.assertIn("owes a reverse current-voltage record", outcome["findings"][0])

    def test_dark_sweep_is_a_finding(self):
        outcome = assess_assembly(_assembly(irradiance_w_m2=5.0), REQUIREMENT)
        self.assertFalse(outcome["illuminated"])
        self.assertIn("dark reverse curve", outcome["findings"][0])

    def test_short_sweep_is_a_finding(self):
        outcome = assess_assembly(_assembly(points=POINTS[:5]), REQUIREMENT)
        self.assertAlmostEqual(outcome["extent_v"], 8.0, places=9)
        self.assertIn("short of the 15 V required", outcome["findings"][0])

    def test_extent_exactly_on_the_requirement_is_accepted(self):
        points = [dict(p) for p in POINTS]
        points[-1]["reverse_voltage_v"] = 15.0
        outcome = assess_assembly(_assembly(points=points), REQUIREMENT)
        self.assertAlmostEqual(
            outcome["extent_v"], outcome["peak_dissipation"]["reverse_voltage_v"],
            places=9,
        )
        self.assertEqual(outcome["findings"], [])

    def test_coarse_step_is_a_finding(self):
        points = [dict(p) for p in POINTS]
        del points[5]
        outcome = assess_assembly(_assembly(points=points), REQUIREMENT)
        self.assertAlmostEqual(outcome["largest_step_v"], 4.0, places=9)
        self.assertIn("wider than the 2 V", outcome["findings"][0])

    def test_missing_assembly_key_rejected(self):
        broken = _assembly()
        del broken["diode_coupling"]
        with self.assertRaises(ValueError):
            assess_assembly(broken, REQUIREMENT)

    def test_blank_assembly_id_rejected(self):
        with self.assertRaises(ValueError):
            assess_assembly(_assembly(assembly_id="   "), REQUIREMENT)

    def test_sweep_missing_irradiance_rejected(self):
        broken = _assembly()
        del broken["sweep"]["irradiance_w_m2"]
        with self.assertRaises(ValueError):
            assess_assembly(broken, REQUIREMENT)


class ProcessReconciliationTests(unittest.TestCase):
    def _spec(self, assemblies=None):
        return {
            "assemblies": assemblies if assemblies is not None else [
                _assembly("a1"),
                _assembly("a2", diode_coupling="string-coupled-protection-diode"),
                _assembly("a3", diode_coupling="cell-coupled-protection-diode",
                          sweep=False),
            ],
            "requirement": dict(REQUIREMENT),
        }

    def test_complete_campaign_passes(self):
        result = assess_reverse_bias_process(self._spec())
        self.assertTrue(result["passed"])
        self.assertEqual(result["records_required"], 2)
        self.assertEqual(result["records_taken"], 2)
        self.assertEqual(result["exempt_ids"], ("a3",))

    def test_missing_record_fails_the_campaign(self):
        assemblies = self._spec()["assemblies"]
        del assemblies[1]["sweep"]
        result = assess_reverse_bias_process({"assemblies": assemblies,
                                              "requirement": dict(REQUIREMENT)})
        self.assertFalse(result["passed"])
        self.assertEqual(result["records_taken"], 1)

    def test_findings_gather_from_every_assembly(self):
        assemblies = self._spec()["assemblies"]
        assemblies[0]["sweep"]["irradiance_w_m2"] = 2.0
        del assemblies[1]["sweep"]
        result = assess_reverse_bias_process({"assemblies": assemblies,
                                              "requirement": dict(REQUIREMENT)})
        self.assertEqual(len(result["findings"]), 2)

    def test_duplicate_assembly_id_rejected(self):
        with self.assertRaises(ValueError):
            assess_reverse_bias_process(
                self._spec([_assembly("a1"), _assembly("a1")])
            )

    def test_empty_assembly_set_rejected(self):
        with self.assertRaises(ValueError):
            assess_reverse_bias_process({"assemblies": [],
                                         "requirement": dict(REQUIREMENT)})

    def test_missing_spec_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_reverse_bias_process({"assemblies": [_assembly()]})

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_reverse_bias_process(["assemblies"])


if __name__ == "__main__":
    unittest.main()
