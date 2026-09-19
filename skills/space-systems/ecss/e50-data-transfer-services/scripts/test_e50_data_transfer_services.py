"""Contract tests for the clause 5.7.2.1 data transfer services logic."""

import unittest

from e50_data_transfer_services_logic import (
    INADEQUATE,
    SERVED,
    UNSERVED,
    assess_data_transfer_services,
    assess_flow,
    assign_flows,
    eligible_services,
    normalise_flow,
    normalise_service,
    service_load,
    validate_latency,
    validate_name,
    validate_rate,
)

BULK = {"name": "bulk", "capacity_bps": 10000000.0, "latency_bound_s": 1.0, "assured": False}
CTRL = {"name": "ctrl", "capacity_bps": 1000000.0, "latency_bound_s": 0.01, "assured": True}
PAYLOAD = {"name": "payload", "rate_bps": 8000000.0, "deadline_s": 2.0}
COMMAND = {"name": "command", "rate_bps": 500000.0, "deadline_s": 0.02, "needs_assured": True}


class ValidationTests(unittest.TestCase):
    def test_zero_rate_accepted_for_a_service(self):
        self.assertAlmostEqual(validate_rate(0), 0.0, places=9)

    def test_negative_rate_rejected(self):
        with self.assertRaises(ValueError):
            validate_rate(-1.0)

    def test_boolean_rate_rejected(self):
        with self.assertRaises(ValueError):
            validate_rate(True)

    def test_text_rate_rejected(self):
        with self.assertRaises(ValueError):
            validate_rate("10000000")

    def test_infinite_rate_rejected(self):
        with self.assertRaises(ValueError):
            validate_rate(float("inf"))

    def test_zero_latency_rejected(self):
        with self.assertRaises(ValueError):
            validate_latency(0.0)

    def test_negative_latency_rejected(self):
        with self.assertRaises(ValueError):
            validate_latency(-0.5)

    def test_blank_name_rejected(self):
        with self.assertRaises(ValueError):
            validate_name("   ")

    def test_name_is_trimmed(self):
        self.assertEqual(validate_name("  bulk "), "bulk")

    def test_non_mapping_service_rejected(self):
        with self.assertRaises(ValueError):
            normalise_service(["bulk", 1.0])

    def test_non_boolean_assurance_rejected(self):
        with self.assertRaises(ValueError):
            normalise_service(dict(BULK, assured="yes"))

    def test_service_defaults_to_unassured(self):
        service = normalise_service(
            {"name": "bulk", "capacity_bps": 1.0, "latency_bound_s": 1.0}
        )
        self.assertFalse(service["assured"])

    def test_zero_rate_flow_rejected(self):
        with self.assertRaises(ValueError):
            normalise_flow({"name": "idle", "rate_bps": 0.0, "deadline_s": 1.0})

    def test_non_boolean_flow_assurance_rejected(self):
        with self.assertRaises(ValueError):
            normalise_flow(dict(PAYLOAD, needs_assured=1))

    def test_duplicate_service_name_rejected(self):
        with self.assertRaises(ValueError):
            assess_data_transfer_services([BULK, dict(BULK)], [PAYLOAD])

    def test_duplicate_flow_name_rejected(self):
        with self.assertRaises(ValueError):
            assess_data_transfer_services([BULK], [PAYLOAD, dict(PAYLOAD)])

    def test_empty_flow_set_rejected(self):
        with self.assertRaises(ValueError):
            assess_data_transfer_services([BULK], [])

    def test_non_list_services_rejected(self):
        with self.assertRaises(ValueError):
            assess_data_transfer_services(BULK, [PAYLOAD])


class EligibilityTests(unittest.TestCase):
    def test_latency_bound_inside_the_deadline_is_eligible(self):
        names = [s["name"] for s in eligible_services(PAYLOAD, [normalise_service(BULK)])]
        self.assertEqual(names, ["bulk"])

    def test_latency_bound_beyond_the_deadline_is_not_eligible(self):
        tight = dict(PAYLOAD, deadline_s=0.5)
        self.assertEqual(eligible_services(tight, [normalise_service(BULK)]), [])

    def test_latency_bound_exactly_on_the_deadline_is_eligible(self):
        exact = dict(PAYLOAD, deadline_s=1.0)
        self.assertEqual(len(eligible_services(exact, [normalise_service(BULK)])), 1)

    def test_unassured_service_cannot_carry_an_assured_flow(self):
        loose = dict(BULK, latency_bound_s=0.005)
        self.assertEqual(eligible_services(COMMAND, [normalise_service(loose)]), [])

    def test_assured_service_can_carry_an_unassured_flow(self):
        relaxed = dict(PAYLOAD, deadline_s=0.02)
        self.assertEqual(len(eligible_services(relaxed, [normalise_service(CTRL)])), 1)


class AssignmentTests(unittest.TestCase):
    def test_each_flow_lands_on_a_service_it_fits(self):
        services = [normalise_service(BULK), normalise_service(CTRL)]
        flows = [normalise_flow(PAYLOAD), normalise_flow(COMMAND)]
        self.assertEqual(
            assign_flows(services, flows), {"payload": "bulk", "command": "ctrl"}
        )

    def test_a_flow_with_no_eligible_service_is_unassigned(self):
        services = [normalise_service(BULK)]
        flows = [normalise_flow(COMMAND)]
        self.assertIsNone(assign_flows(services, flows)["command"])

    def test_assignment_is_stable_across_input_order(self):
        services = [normalise_service(BULK), normalise_service(CTRL)]
        forward = assign_flows(services, [normalise_flow(PAYLOAD), normalise_flow(COMMAND)])
        reverse = assign_flows(
            list(reversed(services)), [normalise_flow(COMMAND), normalise_flow(PAYLOAD)]
        )
        self.assertEqual(forward, reverse)

    def test_load_sums_the_flows_on_a_service(self):
        services = [normalise_service(BULK)]
        flows = [
            normalise_flow(dict(PAYLOAD, name="a", rate_bps=3000000.0)),
            normalise_flow(dict(PAYLOAD, name="b", rate_bps=4000000.0)),
        ]
        load = service_load(services, flows, {"a": "bulk", "b": "bulk"})
        self.assertAlmostEqual(load["bulk"], 7000000.0, places=9)

    def test_load_ignores_an_unassigned_flow(self):
        services = [normalise_service(BULK)]
        flows = [normalise_flow(PAYLOAD)]
        self.assertAlmostEqual(service_load(services, flows, {"payload": None})["bulk"], 0.0, places=9)

    def test_assignment_to_an_unknown_service_rejected(self):
        services = [normalise_service(BULK)]
        flows = [normalise_flow(PAYLOAD)]
        with self.assertRaises(ValueError):
            service_load(services, flows, {"payload": "nosuch"})


class FlowVerdictTests(unittest.TestCase):
    def test_unserved_flow_reports_the_hole(self):
        result = assess_flow(normalise_flow(PAYLOAD), None, 0.0)
        self.assertEqual(result["verdict"], UNSERVED)
        self.assertIsNone(result["service"])

    def test_served_flow_reports_no_reasons(self):
        result = assess_flow(normalise_flow(PAYLOAD), normalise_service(BULK), 8000000.0)
        self.assertEqual(result["verdict"], SERVED)
        self.assertEqual(result["reasons"], [])

    def test_flow_at_exactly_the_service_capacity_is_served(self):
        result = assess_flow(normalise_flow(PAYLOAD), normalise_service(BULK), 10000000.0)
        self.assertEqual(result["verdict"], SERVED)
        self.assertAlmostEqual(result["rate_shortfall_bps"], 0.0, places=9)

    def test_overloaded_service_makes_the_flow_inadequate(self):
        result = assess_flow(normalise_flow(PAYLOAD), normalise_service(BULK), 12000000.0)
        self.assertEqual(result["verdict"], INADEQUATE)
        self.assertAlmostEqual(result["rate_shortfall_bps"], 2000000.0, places=9)

    def test_latency_margin_is_reported(self):
        result = assess_flow(normalise_flow(PAYLOAD), normalise_service(BULK), 1.0)
        self.assertAlmostEqual(result["latency_margin_s"], 1.0, places=9)

    def test_missing_assurance_is_named_in_the_reasons(self):
        loose = normalise_service(dict(BULK, latency_bound_s=0.005))
        result = assess_flow(normalise_flow(COMMAND), loose, 1.0)
        self.assertEqual(result["verdict"], INADEQUATE)
        self.assertTrue(any("assured delivery" in r for r in result["reasons"]))


class AssessmentTests(unittest.TestCase):
    def test_a_sound_design_is_compliant(self):
        result = assess_data_transfer_services([BULK, CTRL], [PAYLOAD, COMMAND])
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_a_flow_with_no_service_fails_the_first_item(self):
        result = assess_data_transfer_services([BULK], [PAYLOAD, COMMAND])
        self.assertFalse(result["coverage_met"])
        self.assertIn("command", result["unserved"])

    def test_the_first_item_failure_is_named_in_the_findings(self):
        result = assess_data_transfer_services([BULK], [PAYLOAD, COMMAND])
        self.assertTrue(any("clause item 1" in f for f in result["findings"]))

    def test_an_oversubscribed_service_fails_the_second_item(self):
        big = dict(PAYLOAD, name="big", rate_bps=9000000.0)
        result = assess_data_transfer_services([BULK], [PAYLOAD, big])
        self.assertFalse(result["adequacy_met"])
        self.assertTrue(any("clause item 2" in f for f in result["findings"]))

    def test_utilisation_is_reported_per_service(self):
        result = assess_data_transfer_services([BULK, CTRL], [PAYLOAD, COMMAND])
        self.assertAlmostEqual(result["utilisation"]["bulk"]["utilisation"], 0.8, places=9)

    def test_spare_capacity_is_reported(self):
        result = assess_data_transfer_services([BULK, CTRL], [PAYLOAD, COMMAND])
        self.assertAlmostEqual(result["utilisation"]["ctrl"]["spare_bps"], 500000.0, places=9)

    def test_a_service_with_no_capacity_reports_no_utilisation(self):
        empty = {"name": "dead", "capacity_bps": 0.0, "latency_bound_s": 1.0}
        result = assess_data_transfer_services([BULK, empty], [PAYLOAD])
        self.assertIsNone(result["utilisation"]["dead"]["utilisation"])

    def test_flows_that_each_fit_can_together_overload_a_service(self):
        a = {"name": "a", "rate_bps": 6000000.0, "deadline_s": 2.0}
        b = {"name": "b", "rate_bps": 6000000.0, "deadline_s": 2.0}
        single = assess_data_transfer_services([BULK], [a])
        both = assess_data_transfer_services([BULK], [a, b])
        self.assertTrue(single["compliant"])
        self.assertFalse(both["compliant"])

    def test_an_explicit_assignment_is_honoured(self):
        result = assess_data_transfer_services(
            [BULK, CTRL], [PAYLOAD], {"payload": "ctrl"}
        )
        self.assertEqual(result["assignment"]["payload"], "ctrl")
        self.assertEqual(result["per_flow"][0]["verdict"], INADEQUATE)

    def test_a_non_mapping_assignment_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_data_transfer_services([BULK], [PAYLOAD], [("payload", "bulk")])

    def test_exact_fit_across_two_flows_stays_compliant(self):
        a = {"name": "a", "rate_bps": 6000000.0, "deadline_s": 2.0}
        b = {"name": "b", "rate_bps": 4000000.0, "deadline_s": 2.0}
        result = assess_data_transfer_services([BULK], [a, b])
        self.assertAlmostEqual(
            result["utilisation"]["bulk"]["carried_bps"], 10000000.0, places=9
        )
        self.assertTrue(result["compliant"])


if __name__ == "__main__":
    unittest.main()
