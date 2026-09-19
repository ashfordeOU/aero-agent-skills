"""Contract test for the actuator-firing-parameter-specification leaf."""

import unittest

from e2021_actuator_firing_parameter_specification_logic import (
    DEFAULT_MARGIN_POLICY,
    FINDING_ALL_FIRE_MARGIN_SHORT,
    FINDING_FIRING_BELOW_ALL_FIRE,
    FINDING_NO_FIRE_MARGIN_SHORT,
    FINDING_NO_FIRE_NOT_BELOW_ALL_FIRE,
    FINDING_PARAMETER_ABSENT,
    FINDING_PULSE_SHORTER_THAN_ALL_FIRE,
    REQUIRED_PARAMETERS,
    all_fire_margin,
    assess_firing_parameter_specification,
    consistency_findings,
    firing_pulse_energy_j,
    missing_parameters,
    no_fire_margin,
    no_fire_power_w,
    specification_completeness,
    validate_policy,
    validate_specification,
)


def spec(**kw):
    record = {
        "no_fire_current_a": 1.0,
        "all_fire_current_a": 3.5,
        "all_fire_duration_s": 0.010,
        "bridge_resistance_ohm": 1.5,
        "recommended_firing_current_a": 7.0,
        "firing_pulse_duration_s": 0.050,
        "maximum_monitoring_current_a": 0.05,
    }
    record.update(kw)
    return record


class TestValidateSpecification(unittest.TestCase):
    def test_full_specification_normalizes_to_floats(self):
        declared = validate_specification(spec())
        self.assertEqual(len(declared), len(REQUIRED_PARAMETERS))
        for value in declared.values():
            self.assertIsInstance(value, float)

    def test_partial_specification_is_allowed(self):
        declared = validate_specification({"no_fire_current_a": 1.0})
        self.assertEqual(sorted(declared), ["no_fire_current_a"])

    def test_non_mapping_raises(self):
        with self.assertRaises(ValueError):
            validate_specification([1.0, 3.5])

    def test_unknown_parameter_raises(self):
        with self.assertRaises(ValueError):
            validate_specification(spec(no_fire_curent_a=1.0))

    def test_non_numeric_value_raises(self):
        with self.assertRaises(ValueError):
            validate_specification(spec(no_fire_current_a="one amp"))

    def test_boolean_value_raises(self):
        with self.assertRaises(ValueError):
            validate_specification(spec(bridge_resistance_ohm=True))

    def test_zero_value_raises(self):
        with self.assertRaises(ValueError):
            validate_specification(spec(all_fire_duration_s=0.0))

    def test_negative_value_raises(self):
        with self.assertRaises(ValueError):
            validate_specification(spec(bridge_resistance_ohm=-1.5))

    def test_infinite_value_raises(self):
        with self.assertRaises(ValueError):
            validate_specification(spec(all_fire_current_a=float("inf")))


class TestPolicy(unittest.TestCase):
    def test_default_policy_is_returned_unasked(self):
        self.assertEqual(validate_policy(), DEFAULT_MARGIN_POLICY)

    def test_policy_override_is_merged(self):
        resolved = validate_policy({"all_fire_margin_min": 2.5})
        self.assertAlmostEqual(resolved["all_fire_margin_min"], 2.5, places=9)
        self.assertAlmostEqual(
            resolved["no_fire_margin_min"],
            DEFAULT_MARGIN_POLICY["no_fire_margin_min"],
            places=9,
        )

    def test_unknown_policy_key_raises(self):
        with self.assertRaises(ValueError):
            validate_policy({"fire_margin": 2.0})

    def test_policy_minimum_below_one_raises(self):
        with self.assertRaises(ValueError):
            validate_policy({"all_fire_margin_min": 0.8})

    def test_non_mapping_policy_raises(self):
        with self.assertRaises(ValueError):
            validate_policy([1.5, 2.0])


class TestCompleteness(unittest.TestCase):
    def test_full_specification_misses_nothing(self):
        self.assertEqual(missing_parameters(spec()), ())
        self.assertAlmostEqual(specification_completeness(spec()), 1.0, places=9)

    def test_absent_parameter_is_named(self):
        partial = spec()
        del partial["maximum_monitoring_current_a"]
        self.assertEqual(missing_parameters(partial), ("maximum_monitoring_current_a",))

    def test_completeness_is_a_fraction_of_seven(self):
        partial = spec()
        del partial["maximum_monitoring_current_a"]
        del partial["firing_pulse_duration_s"]
        self.assertAlmostEqual(specification_completeness(partial), 5.0 / 7.0, places=9)


class TestMargins(unittest.TestCase):
    def test_all_fire_margin_is_the_current_ratio(self):
        self.assertAlmostEqual(all_fire_margin(spec()), 2.0, places=9)

    def test_no_fire_margin_is_the_current_ratio(self):
        self.assertAlmostEqual(no_fire_margin(spec()), 20.0, places=9)

    def test_all_fire_margin_without_its_inputs_raises(self):
        partial = spec()
        del partial["all_fire_current_a"]
        with self.assertRaises(ValueError):
            all_fire_margin(partial)

    def test_no_fire_margin_without_its_inputs_raises(self):
        partial = spec()
        del partial["maximum_monitoring_current_a"]
        with self.assertRaises(ValueError):
            no_fire_margin(partial)


class TestDerivedQuantities(unittest.TestCase):
    def test_pulse_energy_is_current_squared_times_resistance_and_time(self):
        self.assertAlmostEqual(
            firing_pulse_energy_j(spec()), 7.0 * 7.0 * 1.5 * 0.050, places=9
        )

    def test_no_fire_power_is_current_squared_times_resistance(self):
        self.assertAlmostEqual(no_fire_power_w(spec()), 1.0 * 1.0 * 1.5, places=9)

    def test_pulse_energy_without_the_resistance_raises(self):
        partial = spec()
        del partial["bridge_resistance_ohm"]
        with self.assertRaises(ValueError):
            firing_pulse_energy_j(partial)

    def test_no_fire_power_without_the_no_fire_level_raises(self):
        partial = spec()
        del partial["no_fire_current_a"]
        with self.assertRaises(ValueError):
            no_fire_power_w(partial)


class TestConsistency(unittest.TestCase):
    def test_a_sound_specification_has_no_findings(self):
        self.assertEqual(consistency_findings(spec()), [])

    def test_no_fire_above_all_fire_is_a_finding(self):
        codes = [
            f["code"]
            for f in consistency_findings(spec(no_fire_current_a=4.0))
        ]
        self.assertIn(FINDING_NO_FIRE_NOT_BELOW_ALL_FIRE, codes)

    def test_no_fire_equal_to_all_fire_is_a_finding(self):
        codes = [
            f["code"] for f in consistency_findings(spec(no_fire_current_a=3.5))
        ]
        self.assertIn(FINDING_NO_FIRE_NOT_BELOW_ALL_FIRE, codes)

    def test_firing_current_below_all_fire_is_a_finding(self):
        codes = [
            f["code"]
            for f in consistency_findings(spec(recommended_firing_current_a=3.0))
        ]
        self.assertIn(FINDING_FIRING_BELOW_ALL_FIRE, codes)
        self.assertNotIn(FINDING_ALL_FIRE_MARGIN_SHORT, codes)

    def test_thin_all_fire_margin_is_a_finding(self):
        thin = spec(recommended_firing_current_a=4.0)
        self.assertLess(all_fire_margin(thin), DEFAULT_MARGIN_POLICY["all_fire_margin_min"])
        codes = [f["code"] for f in consistency_findings(thin)]
        self.assertIn(FINDING_ALL_FIRE_MARGIN_SHORT, codes)

    def test_a_margin_exactly_on_the_policy_minimum_passes(self):
        exact = spec(recommended_firing_current_a=3.5 * 1.5)
        self.assertAlmostEqual(
            all_fire_margin(exact), DEFAULT_MARGIN_POLICY["all_fire_margin_min"], places=9
        )
        codes = [f["code"] for f in consistency_findings(exact)]
        self.assertNotIn(FINDING_ALL_FIRE_MARGIN_SHORT, codes)

    def test_thin_no_fire_margin_is_a_finding(self):
        thin = spec(maximum_monitoring_current_a=0.8)
        codes = [f["code"] for f in consistency_findings(thin)]
        self.assertIn(FINDING_NO_FIRE_MARGIN_SHORT, codes)

    def test_no_fire_margin_exactly_on_the_policy_minimum_passes(self):
        exact = spec(maximum_monitoring_current_a=0.5)
        self.assertAlmostEqual(
            no_fire_margin(exact), DEFAULT_MARGIN_POLICY["no_fire_margin_min"], places=9
        )
        codes = [f["code"] for f in consistency_findings(exact)]
        self.assertNotIn(FINDING_NO_FIRE_MARGIN_SHORT, codes)

    def test_short_firing_pulse_is_a_finding(self):
        codes = [
            f["code"] for f in consistency_findings(spec(firing_pulse_duration_s=0.005))
        ]
        self.assertIn(FINDING_PULSE_SHORTER_THAN_ALL_FIRE, codes)

    def test_pulse_exactly_the_all_fire_duration_passes(self):
        codes = [
            f["code"] for f in consistency_findings(spec(firing_pulse_duration_s=0.010))
        ]
        self.assertNotIn(FINDING_PULSE_SHORTER_THAN_ALL_FIRE, codes)

    def test_a_stricter_policy_turns_a_sound_margin_into_a_finding(self):
        codes = [
            f["code"]
            for f in consistency_findings(spec(), {"all_fire_margin_min": 2.5})
        ]
        self.assertIn(FINDING_ALL_FIRE_MARGIN_SHORT, codes)

    def test_findings_are_sorted_by_code_then_subject(self):
        bad = spec(no_fire_current_a=4.0, maximum_monitoring_current_a=3.0)
        keys = [(f["code"], f["subject"]) for f in consistency_findings(bad)]
        self.assertEqual(keys, sorted(keys))


class TestAssessment(unittest.TestCase):
    def test_a_sound_specification_is_compliant(self):
        report = assess_firing_parameter_specification(spec())
        self.assertTrue(report["compliant"])
        self.assertEqual(report["missing_parameters"], ())
        self.assertAlmostEqual(report["all_fire_margin"], 2.0, places=9)
        self.assertAlmostEqual(report["no_fire_margin"], 20.0, places=9)

    def test_absent_parameter_blocks_compliance(self):
        partial = spec()
        del partial["all_fire_duration_s"]
        report = assess_firing_parameter_specification(partial)
        self.assertFalse(report["compliant"])
        self.assertIn(FINDING_PARAMETER_ABSENT, report["finding_codes"])

    def test_derived_quantities_are_none_when_their_inputs_are_absent(self):
        partial = spec()
        del partial["bridge_resistance_ohm"]
        report = assess_firing_parameter_specification(partial)
        self.assertIsNone(report["firing_pulse_energy_j"])
        self.assertIsNone(report["no_fire_power_w"])
        self.assertAlmostEqual(report["all_fire_margin"], 2.0, places=9)

    def test_report_carries_the_resolved_policy(self):
        report = assess_firing_parameter_specification(spec(), {"no_fire_margin_min": 3.0})
        self.assertAlmostEqual(report["policy"]["no_fire_margin_min"], 3.0, places=9)

    def test_inverted_levels_block_compliance(self):
        report = assess_firing_parameter_specification(spec(no_fire_current_a=4.0))
        self.assertFalse(report["compliant"])
        self.assertIn(FINDING_NO_FIRE_NOT_BELOW_ALL_FIRE, report["finding_codes"])

    def test_declared_parameters_are_listed_sorted(self):
        report = assess_firing_parameter_specification(spec())
        self.assertEqual(report["declared_parameters"], tuple(sorted(REQUIRED_PARAMETERS)))


if __name__ == "__main__":
    unittest.main()
