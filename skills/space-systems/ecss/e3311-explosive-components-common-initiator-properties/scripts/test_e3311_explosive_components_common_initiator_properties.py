"""Contract test for the e3311 common explosive-component property leaf (stdlib unittest)."""

import unittest

from e3311_explosive_components_common_initiator_properties_logic import (
    COMMON_PROPERTIES,
    COMPONENT_KINDS,
    DEFAULT_COMMON_PROPERTY_POLICY,
    VERDICT_MET,
    VERDICT_NOT_MET,
    applicable_properties,
    assess_autoignition,
    assess_common_properties,
    assess_component_set,
    assess_function_time,
    assess_insulation_resistance,
    assess_seal_leak_rate,
    assess_service_life,
    assess_temperature_envelope,
    validate_common_property_policy,
)


def operating(**kw):
    block = {
        "qualified_low_c": -60.0,
        "qualified_high_c": 90.0,
        "required_low_c": -40.0,
        "required_high_c": 70.0,
    }
    block.update(kw)
    return block


def storage(**kw):
    block = {
        "qualified_low_c": -65.0,
        "qualified_high_c": 95.0,
        "required_low_c": -50.0,
        "required_high_c": 80.0,
    }
    block.update(kw)
    return block


def insulation(**kw):
    block = {"resistance_ohm": 1.0e7, "test_voltage_v": 500.0}
    block.update(kw)
    return block


def life(**kw):
    block = {"declared_life_years": 15.0, "storage_years": 5.0, "mission_years": 7.0}
    block.update(kw)
    return block


def autoignition(**kw):
    block = {"autoignition_temperature_c": 200.0, "max_operating_temperature_c": 70.0}
    block.update(kw)
    return block


def properties(**kw):
    block = {
        "operating-temperature-range": operating(),
        "storage-temperature-range": storage(),
        "seal-leak-rate": 1.0e-7,
        "insulation-resistance": insulation(),
        "service-life": life(),
        "autoignition-temperature": autoignition(),
        "function-time": 4.0,
    }
    block.update(kw)
    return block


def component(kind="initiator", **kw):
    props = properties()
    for name in list(props):
        if name not in applicable_properties(kind):
            del props[name]
    props.update(kw)
    return {"kind": kind, "properties": props}


class TestPolicyValidation(unittest.TestCase):
    def test_default_policy_is_valid(self):
        self.assertIs(
            validate_common_property_policy(DEFAULT_COMMON_PROPERTY_POLICY),
            DEFAULT_COMMON_PROPERTY_POLICY,
        )

    def test_non_mapping_policy_raises(self):
        with self.assertRaises(ValueError):
            validate_common_property_policy(["autoignition_margin_k", 50.0])

    def test_negative_temperature_margin_raises(self):
        policy = dict(DEFAULT_COMMON_PROPERTY_POLICY, operating_temperature_margin_k=-1.0)
        with self.assertRaises(ValueError):
            validate_common_property_policy(policy)

    def test_zero_leak_rate_limit_raises(self):
        policy = dict(DEFAULT_COMMON_PROPERTY_POLICY, max_seal_leak_rate_scc_s=0.0)
        with self.assertRaises(ValueError):
            validate_common_property_policy(policy)


class TestApplicability(unittest.TestCase):
    def test_an_initiator_carries_every_common_property(self):
        self.assertEqual(
            sorted(applicable_properties("initiator")), sorted(COMMON_PROPERTIES)
        )

    def test_a_packaged_charge_does_not_carry_function_time(self):
        self.assertNotIn("function-time", applicable_properties("packaged-charge"))

    def test_every_kind_resolves(self):
        for kind in COMPONENT_KINDS:
            self.assertTrue(applicable_properties(kind))

    def test_an_unknown_kind_raises(self):
        with self.assertRaises(ValueError):
            applicable_properties("flare")


class TestTemperatureEnvelope(unittest.TestCase):
    def test_a_generous_envelope_passes(self):
        result = assess_temperature_envelope(operating(), 10.0, "operating")
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["low_margin_k"], 20.0, places=12)
        self.assertAlmostEqual(result["high_margin_k"], 20.0, places=12)

    def test_an_envelope_exactly_on_the_margin_passes(self):
        block = operating(qualified_low_c=-50.0, qualified_high_c=80.0)
        result = assess_temperature_envelope(block, 10.0, "operating")
        self.assertAlmostEqual(result["low_margin_k"], 10.0, places=9)
        self.assertAlmostEqual(result["high_margin_k"], 10.0, places=9)
        self.assertTrue(result["compliant"])

    def test_a_tight_cold_end_fails_alone(self):
        block = operating(qualified_low_c=-42.0)
        result = assess_temperature_envelope(block, 10.0, "operating")
        self.assertFalse(result["compliant"])
        self.assertEqual(len(result["findings"]), 1)
        self.assertIn("cold end", result["findings"][0])

    def test_a_tight_hot_end_fails_alone(self):
        block = operating(qualified_high_c=72.0)
        result = assess_temperature_envelope(block, 10.0, "operating")
        self.assertFalse(result["compliant"])
        self.assertIn("hot end", result["findings"][0])

    def test_an_inverted_qualified_range_raises(self):
        block = operating(qualified_low_c=100.0, qualified_high_c=-100.0)
        with self.assertRaises(ValueError):
            assess_temperature_envelope(block, 10.0, "operating")

    def test_a_missing_required_high_raises(self):
        block = operating()
        del block["required_high_c"]
        with self.assertRaises(ValueError):
            assess_temperature_envelope(block, 10.0, "operating")


class TestScalarProperties(unittest.TestCase):
    def test_a_tight_seal_passes(self):
        self.assertTrue(assess_seal_leak_rate(1.0e-8)["compliant"])

    def test_a_leak_rate_exactly_on_the_limit_passes(self):
        result = assess_seal_leak_rate(1.0e-6)
        self.assertAlmostEqual(result["leak_rate_scc_s"], 1.0e-6, places=15)
        self.assertTrue(result["compliant"])

    def test_a_leaky_seal_fails(self):
        self.assertFalse(assess_seal_leak_rate(1.0e-4)["compliant"])

    def test_a_negative_leak_rate_raises(self):
        with self.assertRaises(ValueError):
            assess_seal_leak_rate(-1.0e-8)

    def test_a_healthy_insulation_passes(self):
        self.assertTrue(assess_insulation_resistance(insulation())["compliant"])

    def test_a_low_insulation_resistance_fails(self):
        result = assess_insulation_resistance(insulation(resistance_ohm=1.0e5))
        self.assertFalse(result["compliant"])

    def test_an_insulation_measured_at_too_low_a_voltage_fails(self):
        result = assess_insulation_resistance(insulation(test_voltage_v=50.0))
        self.assertFalse(result["compliant"])
        self.assertTrue(any("does not demonstrate" in f for f in result["findings"]))

    def test_a_service_life_covering_storage_and_mission_passes(self):
        self.assertTrue(assess_service_life(life())["compliant"])

    def test_a_service_life_exactly_equal_to_the_need_passes(self):
        result = assess_service_life(life(declared_life_years=12.0))
        self.assertAlmostEqual(result["required_life_years"], 12.0, places=9)
        self.assertTrue(result["compliant"])

    def test_a_life_that_ignores_storage_fails(self):
        result = assess_service_life(life(declared_life_years=8.0))
        self.assertFalse(result["compliant"])

    def test_a_wide_autoignition_separation_passes(self):
        self.assertTrue(assess_autoignition(autoignition())["compliant"])

    def test_a_separation_exactly_on_the_margin_passes(self):
        result = assess_autoignition(autoignition(autoignition_temperature_c=120.0))
        self.assertAlmostEqual(result["separation_k"], 50.0, places=9)
        self.assertTrue(result["compliant"])

    def test_a_narrow_autoignition_separation_fails(self):
        result = assess_autoignition(autoignition(autoignition_temperature_c=90.0))
        self.assertFalse(result["compliant"])

    def test_a_prompt_function_time_passes(self):
        self.assertTrue(assess_function_time(4.0)["compliant"])

    def test_a_function_time_exactly_on_the_limit_passes(self):
        result = assess_function_time(10.0)
        self.assertAlmostEqual(result["function_time_ms"], 10.0, places=9)
        self.assertTrue(result["compliant"])

    def test_a_slow_function_time_fails(self):
        self.assertFalse(assess_function_time(40.0)["compliant"])


class TestComponentAssessment(unittest.TestCase):
    def test_a_sound_initiator_is_met(self):
        report = assess_common_properties(component("initiator"))
        self.assertEqual(report["verdict"], VERDICT_MET)
        self.assertEqual(report["failed_properties"], [])

    def test_a_packaged_charge_is_graded_without_function_time(self):
        report = assess_common_properties(component("packaged-charge"))
        self.assertEqual(report["verdict"], VERDICT_MET)
        self.assertNotIn("function-time", report["properties"])

    def test_declaring_function_time_on_a_packaged_charge_raises(self):
        bad = component("packaged-charge")
        bad["properties"]["function-time"] = 4.0
        with self.assertRaises(ValueError):
            assess_common_properties(bad)

    def test_a_missing_property_raises_rather_than_passing_silently(self):
        bad = component("detonator")
        del bad["properties"]["seal-leak-rate"]
        with self.assertRaises(ValueError):
            assess_common_properties(bad)

    def test_an_unknown_property_key_raises(self):
        bad = component("cartridge")
        bad["properties"]["colour"] = "red"
        with self.assertRaises(ValueError):
            assess_common_properties(bad)

    def test_one_failed_property_names_only_itself(self):
        bad = component("initiator")
        bad["properties"]["seal-leak-rate"] = 1.0e-3
        report = assess_common_properties(bad)
        self.assertEqual(report["verdict"], VERDICT_NOT_MET)
        self.assertEqual(report["failed_properties"], ["seal-leak-rate"])

    def test_several_failed_properties_are_all_named(self):
        bad = component("cartridge")
        bad["properties"]["seal-leak-rate"] = 1.0e-3
        bad["properties"]["service-life"] = life(declared_life_years=2.0)
        report = assess_common_properties(bad)
        self.assertEqual(
            sorted(report["failed_properties"]), ["seal-leak-rate", "service-life"]
        )

    def test_an_unknown_component_kind_raises(self):
        with self.assertRaises(ValueError):
            assess_common_properties({"kind": "flare", "properties": properties()})

    def test_a_non_mapping_component_raises(self):
        with self.assertRaises(ValueError):
            assess_common_properties("one initiator")


class TestComponentSet(unittest.TestCase):
    def test_a_sound_set_is_met(self):
        report = assess_component_set(
            {"ini-1": component("initiator"), "det-1": component("detonator")}
        )
        self.assertEqual(report["verdict"], VERDICT_MET)
        self.assertEqual(report["failed_components"], [])

    def test_one_bad_component_fails_the_set_and_is_named(self):
        bad = component("detonator")
        bad["properties"]["autoignition-temperature"] = autoignition(
            autoignition_temperature_c=80.0
        )
        report = assess_component_set({"ini-1": component("initiator"), "det-1": bad})
        self.assertEqual(report["verdict"], VERDICT_NOT_MET)
        self.assertEqual(report["failed_components"], ["det-1"])

    def test_set_findings_carry_the_component_name(self):
        bad = component("cartridge")
        bad["properties"]["seal-leak-rate"] = 1.0e-2
        report = assess_component_set({"car-9": bad})
        self.assertTrue(report["findings"][0].startswith("car-9:"))

    def test_an_empty_set_raises(self):
        with self.assertRaises(ValueError):
            assess_component_set({})

    def test_a_non_mapping_set_raises(self):
        with self.assertRaises(ValueError):
            assess_component_set(["ini-1"])


if __name__ == "__main__":
    unittest.main()
