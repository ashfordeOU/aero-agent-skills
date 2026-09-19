"""Contract test for the e3311 power/plug/receptacle leaf (stdlib unittest)."""

import unittest

from e3311_power_plug_receptacle_provisions_logic import (
    DEFAULT_POWER_PLUG_POLICY,
    PLUG_KINDS,
    RECEPTACLE_PROVISIONS,
    VERDICT_MET,
    VERDICT_NOT_MET,
    assess_arm_receptacle,
    assess_plug_set,
    assess_power_plug_receptacle_provisions,
    assess_power_provisions,
    delivered_bridge_current_a,
    firing_loop_resistance_ohm,
    line_drop_fraction,
    validate_power_plug_policy,
)


def receptacle(**kw):
    provisions = {name: True for name in RECEPTACLE_PROVISIONS}
    provisions.update(kw)
    return provisions


def plugs(**kw):
    base = {
        "safe-plug": {
            "keying_code": "K-A",
            "identification_colour": "green",
            "mates_with": ["arm-receptacle"],
        },
        "arm-plug": {
            "keying_code": "K-B",
            "identification_colour": "red",
            "mates_with": ["arm-receptacle"],
        },
        "test-plug": {
            "keying_code": "K-C",
            "identification_colour": "yellow",
            "mates_with": ["test-receptacle"],
        },
    }
    base.update(kw)
    return base


def power(**kw):
    case = {
        "all_fire_current_a": 2.0,
        "initiator_count": 1,
        "source_voltage_v": 5.0,
        "source_resistance_ohm": 0.05,
        "harness_resistance_ohm": 0.20,
        "bridge_resistance_ohm": 1.0,
    }
    case.update(kw)
    return case


def full_case(**kw):
    case = {
        "power_provisions": power(),
        "receptacle_provisions": receptacle(),
        "plugs": plugs(),
    }
    case.update(kw)
    return case


class TestPolicyValidation(unittest.TestCase):
    def test_default_policy_is_valid(self):
        self.assertIs(
            validate_power_plug_policy(DEFAULT_POWER_PLUG_POLICY),
            DEFAULT_POWER_PLUG_POLICY,
        )

    def test_non_mapping_policy_raises(self):
        with self.assertRaises(ValueError):
            validate_power_plug_policy(["all_fire_current_margin", 1.5])

    def test_margin_below_unity_raises(self):
        policy = dict(DEFAULT_POWER_PLUG_POLICY, all_fire_current_margin=0.9)
        with self.assertRaises(ValueError):
            validate_power_plug_policy(policy)

    def test_drop_fraction_at_unity_raises(self):
        policy = dict(DEFAULT_POWER_PLUG_POLICY, line_drop_fraction_limit=1.0)
        with self.assertRaises(ValueError):
            validate_power_plug_policy(policy)

    def test_unknown_receptacle_provision_in_policy_raises(self):
        policy = dict(
            DEFAULT_POWER_PLUG_POLICY, required_receptacle_provisions=("gold-paint",)
        )
        with self.assertRaises(ValueError):
            validate_power_plug_policy(policy)


class TestFiringLoopArithmetic(unittest.TestCase):
    def test_loop_resistance_adds_the_single_bridge(self):
        self.assertAlmostEqual(
            firing_loop_resistance_ohm(0.05, 0.20, 1.0, 1), 1.25, places=12
        )

    def test_parallel_bridges_lower_the_loop_resistance(self):
        self.assertAlmostEqual(
            firing_loop_resistance_ohm(0.05, 0.20, 1.0, 4), 0.50, places=12
        )

    def test_delivered_current_for_one_initiator(self):
        self.assertAlmostEqual(
            delivered_bridge_current_a(5.0, 0.05, 0.20, 1.0, 1), 4.0, places=12
        )

    def test_adding_initiators_starves_each_bridge(self):
        one = delivered_bridge_current_a(5.0, 0.05, 0.20, 1.0, 1)
        four = delivered_bridge_current_a(5.0, 0.05, 0.20, 1.0, 4)
        self.assertLess(four, one)
        self.assertAlmostEqual(four, 2.5, places=12)

    def test_line_drop_fraction_is_the_series_share(self):
        self.assertAlmostEqual(line_drop_fraction(0.05, 0.20, 1.0, 1), 0.20, places=12)

    def test_zero_bridge_resistance_raises(self):
        with self.assertRaises(ValueError):
            firing_loop_resistance_ohm(0.05, 0.20, 0.0, 1)

    def test_zero_initiator_count_raises(self):
        with self.assertRaises(ValueError):
            firing_loop_resistance_ohm(0.05, 0.20, 1.0, 0)

    def test_boolean_initiator_count_raises(self):
        with self.assertRaises(ValueError):
            firing_loop_resistance_ohm(0.05, 0.20, 1.0, True)

    def test_negative_harness_resistance_raises(self):
        with self.assertRaises(ValueError):
            firing_loop_resistance_ohm(0.05, -0.1, 1.0, 1)

    def test_zero_source_voltage_raises(self):
        with self.assertRaises(ValueError):
            delivered_bridge_current_a(0.0, 0.05, 0.20, 1.0, 1)


class TestPowerProvisions(unittest.TestCase):
    def test_a_healthy_source_passes(self):
        result = assess_power_provisions(power())
        self.assertTrue(result["compliant"])

    def test_a_case_exactly_on_the_required_current_passes(self):
        policy = dict(DEFAULT_POWER_PLUG_POLICY, all_fire_current_margin=2.0)
        result = assess_power_provisions(power(), policy)
        self.assertAlmostEqual(result["delivered_current_a"], 4.0, places=9)
        self.assertAlmostEqual(result["required_current_a"], 4.0, places=9)
        self.assertTrue(result["compliant"])

    def test_a_case_exactly_on_the_drop_limit_passes(self):
        case = power(
            source_resistance_ohm=0.05,
            harness_resistance_ohm=0.20,
            bridge_resistance_ohm=0.75,
        )
        result = assess_power_provisions(case)
        self.assertAlmostEqual(result["line_drop_fraction"], 0.25, places=12)
        self.assertTrue(result["compliant"])

    def test_a_long_harness_breaks_the_drop_limit(self):
        result = assess_power_provisions(power(harness_resistance_ohm=2.0))
        self.assertFalse(result["compliant"])
        self.assertTrue(
            any("firing voltage" in f for f in result["findings"])
        )

    def test_four_simultaneous_initiators_starve_the_design(self):
        result = assess_power_provisions(power(initiator_count=4, all_fire_current_a=2.0))
        self.assertFalse(result["compliant"])
        self.assertAlmostEqual(result["delivered_current_a"], 2.5, places=12)

    def test_a_missing_all_fire_current_raises(self):
        case = power()
        del case["all_fire_current_a"]
        with self.assertRaises(ValueError):
            assess_power_provisions(case)

    def test_a_non_mapping_power_case_raises(self):
        with self.assertRaises(ValueError):
            assess_power_provisions("5 volts")


class TestArmReceptacle(unittest.TestCase):
    def test_a_complete_provision_set_passes(self):
        result = assess_arm_receptacle(receptacle())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["provisions_absent"], [])

    def test_a_missing_provision_is_named(self):
        result = assess_arm_receptacle(
            receptacle(**{"arm-receptacle-uniquely-keyed": False})
        )
        self.assertFalse(result["compliant"])
        self.assertIn("arm-receptacle-uniquely-keyed", result["provisions_absent"])

    def test_an_undeclared_provision_raises(self):
        provisions = receptacle()
        del provisions["arm-receptacle-externally-accessible"]
        with self.assertRaises(ValueError):
            assess_arm_receptacle(provisions)

    def test_an_unknown_provision_key_raises(self):
        with self.assertRaises(ValueError):
            assess_arm_receptacle(receptacle(**{"gold-paint": True}))

    def test_a_non_boolean_provision_state_raises(self):
        provisions = receptacle()
        provisions["arm-receptacle-captive-retention"] = 1
        with self.assertRaises(ValueError):
            assess_arm_receptacle(provisions)


class TestPlugSet(unittest.TestCase):
    def test_a_well_keyed_set_passes(self):
        result = assess_plug_set(plugs())
        self.assertTrue(result["compliant"])

    def test_every_kind_is_accounted_for(self):
        result = assess_plug_set(plugs())
        seen = set()
        for kinds in result["keying_codes"].values():
            seen.update(kinds)
        self.assertEqual(sorted(seen), sorted(PLUG_KINDS))

    def test_a_shared_keying_code_is_a_finding(self):
        bad = plugs()
        bad["test-plug"] = dict(bad["test-plug"], keying_code="K-B")
        result = assess_plug_set(bad)
        self.assertFalse(result["compliant"])
        self.assertTrue(any("keying code" in f for f in result["findings"]))

    def test_a_shared_identification_colour_is_a_finding(self):
        bad = plugs()
        bad["safe-plug"] = dict(bad["safe-plug"], identification_colour="red")
        result = assess_plug_set(bad)
        self.assertFalse(result["compliant"])
        self.assertTrue(
            any("identification colour" in f for f in result["findings"])
        )

    def test_a_test_plug_that_fits_the_arm_receptacle_is_a_finding(self):
        bad = plugs()
        bad["test-plug"] = dict(
            bad["test-plug"], mates_with=["test-receptacle", "arm-receptacle"]
        )
        result = assess_plug_set(bad)
        self.assertFalse(result["compliant"])
        self.assertTrue(any("arm-receptacle" in f for f in result["findings"]))

    def test_an_arm_plug_that_misses_its_own_receptacle_is_a_finding(self):
        bad = plugs()
        bad["arm-plug"] = dict(bad["arm-plug"], mates_with=["test-receptacle"])
        result = assess_plug_set(bad)
        self.assertFalse(result["compliant"])

    def test_a_missing_plug_kind_raises(self):
        bad = plugs()
        del bad["test-plug"]
        with self.assertRaises(ValueError):
            assess_plug_set(bad)

    def test_an_empty_keying_code_raises(self):
        bad = plugs()
        bad["arm-plug"] = dict(bad["arm-plug"], keying_code="  ")
        with self.assertRaises(ValueError):
            assess_plug_set(bad)

    def test_an_unknown_mating_target_raises(self):
        bad = plugs()
        bad["safe-plug"] = dict(bad["safe-plug"], mates_with=["umbilical"])
        with self.assertRaises(ValueError):
            assess_plug_set(bad)


class TestFullAssessment(unittest.TestCase):
    def test_a_sound_installation_is_met(self):
        report = assess_power_plug_receptacle_provisions(full_case())
        self.assertEqual(report["verdict"], VERDICT_MET)
        self.assertEqual(report["failed_parts"], [])
        self.assertEqual(report["findings"], [])

    def test_one_broken_part_names_only_itself(self):
        case = full_case(power_provisions=power(harness_resistance_ohm=2.0))
        report = assess_power_plug_receptacle_provisions(case)
        self.assertEqual(report["verdict"], VERDICT_NOT_MET)
        self.assertEqual(report["failed_parts"], ["power-provisions"])

    def test_two_broken_parts_are_both_named(self):
        bad_plugs = plugs()
        bad_plugs["safe-plug"] = dict(bad_plugs["safe-plug"], keying_code="K-B")
        case = full_case(
            receptacle_provisions=receptacle(
                **{"arm-receptacle-armed-as-last-operation": False}
            ),
            plugs=bad_plugs,
        )
        report = assess_power_plug_receptacle_provisions(case)
        self.assertEqual(report["failed_parts"], ["arm-receptacle", "plug-set"])
        self.assertGreaterEqual(len(report["findings"]), 2)

    def test_every_part_appears_in_the_report(self):
        report = assess_power_plug_receptacle_provisions(full_case())
        for name in ("power-provisions", "arm-receptacle", "plug-set"):
            self.assertIn(name, report["parts"])

    def test_a_non_mapping_case_raises(self):
        with self.assertRaises(ValueError):
            assess_power_plug_receptacle_provisions("arm plug fitted")


if __name__ == "__main__":
    unittest.main()
