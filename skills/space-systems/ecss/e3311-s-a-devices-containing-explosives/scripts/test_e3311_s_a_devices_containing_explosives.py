"""Contract test for the e3311 safe and arm device leaf (unittest)."""

import copy
import unittest

from e3311_s_a_devices_containing_explosives_logic import (
    DEFAULT_SA_POLICY,
    STANDARD_GRAVITY_M_S2,
    VERDICT_MET,
    VERDICT_NOT_MET,
    arming_time_verdict,
    assess_sa_device,
    assess_sa_devices,
    de_arm_verdict,
    independence_verdict,
    inertial_torque_nm,
    interrupt_offset_ratio,
    interrupt_verdict,
    monitoring_verdict,
    retention_verdict,
    validate_arming_event,
    validate_sa_device,
    validate_sa_policy,
    validate_shock_case,
)


def event(eid="ARM-CMD", **kw):
    record = {
        "id": eid,
        "stimulus": "arm-command",
        "source": "sequencer-a",
        "reversible": True,
    }
    record.update(kw)
    return record


def device(did="SAD-1", **kw):
    record = {
        "id": did,
        "rotor_charge_diameter_mm": 3.00,
        "safe_offset_mm": 4.50,
        "barrier_thickness_mm": 4.00,
        "rotor_mass_kg": 0.040,
        "rotor_offset_arm_m": 0.012,
        "safe_lock_torque_nm": 0.500,
        "safe_position_monitored": True,
        "armed_position_monitored": True,
        "monitor_isolation_mohm": 100.0,
        "de_arm_capable": True,
        "arming_time_s": 0.250,
        "arming_time_window_s": (0.100, 0.500),
        "arming_events": [
            event("ARM-CMD", source="sequencer-a"),
            event("SEP-BREAKWIRE", stimulus="separation-breakwire", source="umbilical"),
        ],
    }
    record.update(kw)
    return copy.deepcopy(record)


def case(**kw):
    record = {"shock_acceleration_g": 50.0}
    record.update(kw)
    return record


class TestPolicyValidation(unittest.TestCase):
    def test_default_policy_is_valid(self):
        self.assertIs(validate_sa_policy(DEFAULT_SA_POLICY), DEFAULT_SA_POLICY)

    def test_a_non_mapping_policy_raises(self):
        with self.assertRaises(ValueError):
            validate_sa_policy(2.0)

    def test_requiring_fewer_than_two_arming_events_raises(self):
        with self.assertRaises(ValueError):
            validate_sa_policy(
                dict(DEFAULT_SA_POLICY, min_independent_arming_events=1)
            )

    def test_a_non_boolean_de_arm_requirement_raises(self):
        with self.assertRaises(ValueError):
            validate_sa_policy(dict(DEFAULT_SA_POLICY, require_de_arm="yes"))


class TestRecordValidation(unittest.TestCase):
    def test_a_valid_device_normalizes(self):
        record = validate_sa_device(device())
        self.assertEqual(record["id"], "SAD-1")
        self.assertEqual(len(record["arming_events"]), 2)

    def test_a_device_with_no_arming_events_raises(self):
        with self.assertRaises(ValueError):
            validate_sa_device(device(arming_events=[]))

    def test_duplicate_arming_event_ids_raise(self):
        with self.assertRaises(ValueError):
            validate_sa_device(
                device(arming_events=[event("ARM-CMD"), event("ARM-CMD")])
            )

    def test_an_arming_event_without_a_source_raises(self):
        record = event()
        del record["source"]
        with self.assertRaises(ValueError):
            validate_arming_event(record)

    def test_an_inverted_arming_window_raises(self):
        with self.assertRaises(ValueError):
            validate_sa_device(device(arming_time_window_s=(0.5, 0.1)))

    def test_a_single_valued_arming_window_raises(self):
        with self.assertRaises(ValueError):
            validate_sa_device(device(arming_time_window_s=(0.5,)))

    def test_a_negative_safe_offset_raises(self):
        with self.assertRaises(ValueError):
            validate_sa_device(device(safe_offset_mm=-1.0))

    def test_a_non_boolean_monitoring_declaration_raises(self):
        with self.assertRaises(ValueError):
            validate_sa_device(device(safe_position_monitored="yes"))

    def test_a_zero_shock_case_raises(self):
        with self.assertRaises(ValueError):
            validate_shock_case(case(shock_acceleration_g=0.0))


class TestInterruptGate(unittest.TestCase):
    def test_offset_ratio_is_the_offset_in_charge_diameters(self):
        self.assertAlmostEqual(interrupt_offset_ratio(device()), 1.5, places=9)

    def test_a_fully_out_of_line_rotor_passes(self):
        self.assertTrue(interrupt_verdict(device())["compliant"])

    def test_an_offset_landing_exactly_on_one_diameter_passes(self):
        verdict = interrupt_verdict(device(safe_offset_mm=3.00))
        self.assertAlmostEqual(verdict["offset_ratio"], 1.0, places=9)
        self.assertTrue(verdict["compliant"])

    def test_a_partly_in_line_rotor_fails(self):
        verdict = interrupt_verdict(device(safe_offset_mm=1.20))
        self.assertFalse(verdict["compliant"])
        self.assertTrue(any("interrupt the train" in f for f in verdict["findings"]))

    def test_a_thin_barrier_fails_on_its_own(self):
        verdict = interrupt_verdict(device(barrier_thickness_mm=0.50))
        self.assertFalse(verdict["compliant"])
        self.assertTrue(any("barrier" in f for f in verdict["findings"]))


class TestIndependenceGate(unittest.TestCase):
    def test_two_events_from_two_sources_are_independent(self):
        verdict = independence_verdict(device())
        self.assertTrue(verdict["compliant"])
        self.assertEqual(verdict["independent_sources"], 2)

    def test_a_single_arming_event_fails(self):
        verdict = independence_verdict(device(arming_events=[event()]))
        self.assertFalse(verdict["compliant"])

    def test_two_events_from_one_source_are_not_independent(self):
        verdict = independence_verdict(
            device(
                arming_events=[
                    event("ARM-A", source="sequencer-a"),
                    event("ARM-B", source="sequencer-a"),
                ]
            )
        )
        self.assertFalse(verdict["compliant"])
        self.assertEqual(verdict["declared_events"], 2)
        self.assertEqual(verdict["independent_sources"], 1)
        self.assertIn("sequencer-a", verdict["shared_sources"])

    def test_a_shared_source_among_three_events_is_named(self):
        verdict = independence_verdict(
            device(
                arming_events=[
                    event("ARM-A", source="sequencer-a"),
                    event("ARM-B", source="sequencer-a"),
                    event("SEP", source="umbilical"),
                ]
            )
        )
        self.assertFalse(verdict["compliant"])
        self.assertEqual(verdict["shared_sources"]["sequencer-a"], ["ARM-A", "ARM-B"])


class TestRetentionGate(unittest.TestCase):
    def test_inertial_torque_is_mass_times_acceleration_times_arm(self):
        self.assertAlmostEqual(
            inertial_torque_nm(0.040, 50.0, 0.012),
            0.040 * 50.0 * STANDARD_GRAVITY_M_S2 * 0.012,
            places=12,
        )

    def test_a_negative_acceleration_raises(self):
        with self.assertRaises(ValueError):
            inertial_torque_nm(0.040, -50.0, 0.012)

    def test_a_strong_lock_clears_the_margin(self):
        verdict = retention_verdict(device(), case())
        self.assertTrue(verdict["compliant"])
        self.assertGreater(verdict["lock_margin"], 2.0)

    def test_a_margin_landing_exactly_on_the_requirement_passes(self):
        applied = inertial_torque_nm(0.040, 50.0, 0.012)
        verdict = retention_verdict(
            device(safe_lock_torque_nm=2.0 * applied), case()
        )
        self.assertAlmostEqual(verdict["lock_margin"], 2.0, places=9)
        self.assertTrue(verdict["compliant"])

    def test_a_severe_shock_breaks_the_lock_margin(self):
        verdict = retention_verdict(device(), case(shock_acceleration_g=4000.0))
        self.assertFalse(verdict["compliant"])
        self.assertTrue(any("inertial torque" in f for f in verdict["findings"]))


class TestRemainingGates(unittest.TestCase):
    def test_an_unmonitored_safe_position_fails(self):
        self.assertFalse(
            monitoring_verdict(device(safe_position_monitored=False))["compliant"]
        )

    def test_poor_monitor_isolation_fails(self):
        verdict = monitoring_verdict(device(monitor_isolation_mohm=1.0))
        self.assertFalse(verdict["compliant"])
        self.assertTrue(any("isolates" in f for f in verdict["findings"]))

    def test_an_arming_time_inside_the_window_passes(self):
        self.assertTrue(arming_time_verdict(device())["compliant"])

    def test_an_arming_time_exactly_on_the_upper_bound_passes(self):
        self.assertTrue(arming_time_verdict(device(arming_time_s=0.500))["compliant"])

    def test_a_slow_arming_time_fails(self):
        self.assertFalse(arming_time_verdict(device(arming_time_s=0.900))["compliant"])

    def test_a_device_that_cannot_de_arm_fails(self):
        self.assertFalse(de_arm_verdict(device(de_arm_capable=False))["compliant"])

    def test_de_arm_can_be_waived_by_policy(self):
        self.assertTrue(
            de_arm_verdict(
                device(de_arm_capable=False),
                dict(DEFAULT_SA_POLICY, require_de_arm=False),
            )["compliant"]
        )


class TestAssessment(unittest.TestCase):
    def test_a_sound_device_meets_the_clause(self):
        report = assess_sa_device(device(), case())
        self.assertTrue(report["compliant"])
        self.assertEqual(report["verdict"], VERDICT_MET)
        self.assertEqual(report["failed_gates"], [])

    def test_a_failing_device_names_every_failed_gate(self):
        report = assess_sa_device(
            device(safe_offset_mm=0.5, de_arm_capable=False), case()
        )
        self.assertEqual(report["verdict"], VERDICT_NOT_MET)
        self.assertIn("interrupt", report["failed_gates"])
        self.assertIn("de-arm", report["failed_gates"])

    def test_a_set_of_sound_devices_is_accepted(self):
        report = assess_sa_devices([device("SAD-1"), device("SAD-2")], case())
        self.assertTrue(report["compliant"])
        self.assertEqual(sorted(report["accepted"]), ["SAD-1", "SAD-2"])

    def test_duplicate_device_ids_raise_from_the_set(self):
        with self.assertRaises(ValueError):
            assess_sa_devices([device("SAD-1"), device("SAD-1")], case())

    def test_one_bad_device_fails_the_set(self):
        report = assess_sa_devices(
            [device("SAD-1"), device("SAD-2", barrier_thickness_mm=0.1)], case()
        )
        self.assertEqual(report["rejected"], ["SAD-2"])
        self.assertEqual(report["verdict"], VERDICT_NOT_MET)

    def test_an_empty_device_set_raises(self):
        with self.assertRaises(ValueError):
            assess_sa_devices([], case())


if __name__ == "__main__":
    unittest.main()
