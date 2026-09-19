"""Contract test for the e3311 integral initiator connectors leaf."""

import unittest

from e3311_integral_initiator_connectors_logic import (
    COMPLIANT,
    DEFAULT_CONNECTOR_POLICY,
    NOT_COMPLIANT,
    VERDICT_MET,
    VERDICT_NOT_MET,
    assess_connector_set,
    assess_initiator_connector,
    bonding_verdict,
    connector_resistance_ohm,
    delivered_current_a,
    firing_loop_resistance_ohm,
    firing_loop_verdict,
    insulation_verdict,
    keying_conflicts,
    mate_life_verdict,
    sealing_verdict,
    shorting_verdict,
    validate_connector_policy,
    validate_firing_circuit,
    validate_initiator,
    validate_initiators,
)


def initiator(iid="NSI-A", **kw):
    record = {
        "id": iid,
        "circuit_id": "FC-1",
        "keying_code": "KEY-A",
        "bridgewire_resistance_ohm": 1.00,
        "all_fire_current_a": 3.50,
        "contact_resistance_ohm": 0.005,
        "contact_count": 2,
        "insulation_resistance_mohm": 500.0,
        "rated_mate_demate_cycles": 100,
        "planned_mate_demate_cycles": 20,
        "shell_bonding_resistance_mohm": 2.5,
        "seal_leak_rate_scc_s": 1.0e-8,
        "pins_shorted_until_mate": True,
    }
    record.update(kw)
    return record


def circuit(**kw):
    record = {
        "firing_voltage_v": 28.0,
        "source_resistance_ohm": 0.20,
        "harness_resistance_ohm": 0.30,
    }
    record.update(kw)
    return record


def unit_set():
    return [
        initiator("NSI-A", circuit_id="FC-1", keying_code="KEY-A"),
        initiator("NSI-B", circuit_id="FC-2", keying_code="KEY-B"),
    ]


class TestPolicyValidation(unittest.TestCase):
    def test_default_policy_is_valid(self):
        self.assertIs(
            validate_connector_policy(DEFAULT_CONNECTOR_POLICY),
            DEFAULT_CONNECTOR_POLICY,
        )

    def test_a_non_mapping_policy_raises(self):
        with self.assertRaises(ValueError):
            validate_connector_policy("1.5")

    def test_an_all_fire_margin_below_unity_raises(self):
        with self.assertRaises(ValueError):
            validate_connector_policy(
                dict(DEFAULT_CONNECTOR_POLICY, all_fire_margin=0.9)
            )

    def test_a_connector_share_above_one_raises(self):
        with self.assertRaises(ValueError):
            validate_connector_policy(
                dict(DEFAULT_CONNECTOR_POLICY, max_connector_share_of_loop=1.4)
            )

    def test_a_non_boolean_shorting_flag_raises(self):
        with self.assertRaises(ValueError):
            validate_connector_policy(
                dict(DEFAULT_CONNECTOR_POLICY, require_pin_shorting="yes")
            )


class TestRecordValidation(unittest.TestCase):
    def test_a_valid_initiator_normalizes(self):
        record = validate_initiator(initiator())
        self.assertEqual(record["id"], "NSI-A")
        self.assertEqual(record["contact_count"], 2)

    def test_an_empty_id_raises(self):
        with self.assertRaises(ValueError):
            validate_initiator(initiator(id="   "))

    def test_a_missing_keying_code_raises(self):
        record = initiator()
        del record["keying_code"]
        with self.assertRaises(ValueError):
            validate_initiator(record)

    def test_a_single_contact_connector_raises(self):
        with self.assertRaises(ValueError):
            validate_initiator(initiator(contact_count=1))

    def test_a_boolean_contact_count_raises(self):
        with self.assertRaises(ValueError):
            validate_initiator(initiator(contact_count=True))

    def test_a_negative_bridgewire_resistance_raises(self):
        with self.assertRaises(ValueError):
            validate_initiator(initiator(bridgewire_resistance_ohm=-1.0))

    def test_a_non_boolean_shorting_declaration_raises(self):
        with self.assertRaises(ValueError):
            validate_initiator(initiator(pins_shorted_until_mate="shorted"))

    def test_duplicate_initiator_ids_raise(self):
        with self.assertRaises(ValueError):
            validate_initiators([initiator("NSI-A"), initiator("NSI-A")])

    def test_an_empty_initiator_list_raises(self):
        with self.assertRaises(ValueError):
            validate_initiators([])

    def test_a_zero_firing_voltage_raises(self):
        with self.assertRaises(ValueError):
            validate_firing_circuit(circuit(firing_voltage_v=0.0))


class TestFiringLoop(unittest.TestCase):
    def test_connector_resistance_sums_over_contacts(self):
        self.assertAlmostEqual(
            connector_resistance_ohm(initiator()), 0.010, places=9
        )

    def test_loop_resistance_adds_every_series_term(self):
        self.assertAlmostEqual(
            firing_loop_resistance_ohm(initiator(), circuit()), 1.510, places=9
        )

    def test_delivered_current_follows_ohms_law(self):
        self.assertAlmostEqual(
            delivered_current_a(initiator(), circuit()), 28.0 / 1.510, places=9
        )

    def test_a_healthy_loop_clears_the_all_fire_margin(self):
        verdict = firing_loop_verdict(initiator(), circuit())
        self.assertTrue(verdict["compliant"])
        self.assertGreater(verdict["all_fire_margin"], 1.5)

    def test_a_margin_landing_exactly_on_the_requirement_passes(self):
        # 28 V into a 5.333... ohm loop delivers exactly 1.50 x all-fire.
        loop_needed = 28.0 / (1.5 * 3.50)
        bridgewire = loop_needed - 0.5 - 0.010
        verdict = firing_loop_verdict(
            initiator(bridgewire_resistance_ohm=bridgewire), circuit()
        )
        self.assertAlmostEqual(verdict["all_fire_margin"], 1.50, places=9)
        self.assertTrue(verdict["compliant"])

    def test_a_weak_source_fails_the_all_fire_margin(self):
        verdict = firing_loop_verdict(
            initiator(), circuit(firing_voltage_v=6.0)
        )
        self.assertFalse(verdict["compliant"])
        self.assertTrue(
            any("all-fire current" in f for f in verdict["findings"])
        )

    def test_a_high_contact_resistance_is_reported(self):
        verdict = firing_loop_verdict(
            initiator(contact_resistance_ohm=0.050), circuit()
        )
        self.assertFalse(verdict["compliant"])
        self.assertTrue(any("mated contacts" in f for f in verdict["findings"]))

    def test_a_connector_dominating_the_loop_is_reported(self):
        verdict = firing_loop_verdict(
            initiator(
                bridgewire_resistance_ohm=0.05, contact_resistance_ohm=0.010
            ),
            circuit(source_resistance_ohm=0.0, harness_resistance_ohm=0.0),
        )
        self.assertFalse(verdict["compliant"])
        self.assertTrue(
            any("firing loop" in f for f in verdict["findings"])
        )


class TestSingleGates(unittest.TestCase):
    def test_open_pins_before_mate_fail_the_shorting_gate(self):
        verdict = shorting_verdict(initiator(pins_shorted_until_mate=False))
        self.assertFalse(verdict["compliant"])

    def test_shorting_can_be_waived_by_policy(self):
        verdict = shorting_verdict(
            initiator(pins_shorted_until_mate=False),
            dict(DEFAULT_CONNECTOR_POLICY, require_pin_shorting=False),
        )
        self.assertTrue(verdict["compliant"])

    def test_low_insulation_resistance_fails(self):
        self.assertFalse(
            insulation_verdict(initiator(insulation_resistance_mohm=10.0))[
                "compliant"
            ]
        )

    def test_insulation_exactly_on_the_floor_passes(self):
        self.assertTrue(
            insulation_verdict(initiator(insulation_resistance_mohm=100.0))[
                "compliant"
            ]
        )

    def test_mate_life_requires_the_planned_count_times_the_margin(self):
        verdict = mate_life_verdict(initiator(planned_mate_demate_cycles=20))
        self.assertAlmostEqual(verdict["required_cycles"], 40.0, places=9)
        self.assertTrue(verdict["compliant"])

    def test_mate_life_exactly_on_the_requirement_passes(self):
        verdict = mate_life_verdict(
            initiator(rated_mate_demate_cycles=40, planned_mate_demate_cycles=20)
        )
        self.assertTrue(verdict["compliant"])

    def test_too_few_rated_cycles_fail(self):
        self.assertFalse(
            mate_life_verdict(
                initiator(
                    rated_mate_demate_cycles=30, planned_mate_demate_cycles=20
                )
            )["compliant"]
        )

    def test_poor_shell_bonding_fails(self):
        self.assertFalse(
            bonding_verdict(initiator(shell_bonding_resistance_mohm=25.0))[
                "compliant"
            ]
        )

    def test_a_leaking_integral_seal_fails(self):
        self.assertFalse(
            sealing_verdict(initiator(seal_leak_rate_scc_s=1.0e-4))["compliant"]
        )


class TestKeying(unittest.TestCase):
    def test_distinct_keys_on_distinct_circuits_produce_no_conflict(self):
        self.assertEqual(keying_conflicts(unit_set()), [])

    def test_a_shared_key_across_circuits_is_a_conflict(self):
        units = unit_set()
        units[1]["keying_code"] = "KEY-A"
        conflicts = keying_conflicts(units)
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0]["circuits"], ["FC-1", "FC-2"])

    def test_a_shared_key_on_one_circuit_is_not_a_conflict(self):
        units = unit_set()
        units[1]["keying_code"] = "KEY-A"
        units[1]["circuit_id"] = "FC-1"
        self.assertEqual(keying_conflicts(units), [])


class TestAssessment(unittest.TestCase):
    def test_a_sound_unit_is_accepted(self):
        result = assess_initiator_connector(initiator(), circuit())
        self.assertEqual(result["outcome"], COMPLIANT)
        self.assertEqual(result["failed_gates"], [])

    def test_a_failing_unit_names_every_failed_gate(self):
        result = assess_initiator_connector(
            initiator(
                pins_shorted_until_mate=False, insulation_resistance_mohm=1.0
            ),
            circuit(),
        )
        self.assertEqual(result["outcome"], NOT_COMPLIANT)
        self.assertIn("shorting", result["failed_gates"])
        self.assertIn("insulation", result["failed_gates"])

    def test_a_clean_set_meets_the_clause(self):
        report = assess_connector_set(unit_set(), circuit())
        self.assertTrue(report["compliant"])
        self.assertEqual(report["verdict"], VERDICT_MET)
        self.assertEqual(sorted(report["accepted"]), ["NSI-A", "NSI-B"])

    def test_a_keying_conflict_alone_fails_the_set(self):
        units = unit_set()
        units[1]["keying_code"] = "KEY-A"
        report = assess_connector_set(units, circuit())
        self.assertEqual(report["rejected"], [])
        self.assertFalse(report["compliant"])
        self.assertEqual(report["verdict"], VERDICT_NOT_MET)

    def test_a_rejected_unit_fails_the_set(self):
        units = unit_set()
        units[0]["seal_leak_rate_scc_s"] = 1.0e-3
        report = assess_connector_set(units, circuit())
        self.assertEqual(report["rejected"], ["NSI-A"])
        self.assertEqual(report["verdict"], VERDICT_NOT_MET)

    def test_a_bad_circuit_raises_from_the_set_assessment(self):
        with self.assertRaises(ValueError):
            assess_connector_set(unit_set(), circuit(firing_voltage_v=-28.0))


if __name__ == "__main__":
    unittest.main()
