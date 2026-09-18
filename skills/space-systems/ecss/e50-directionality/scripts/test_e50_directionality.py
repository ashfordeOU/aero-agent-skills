"""Contract test for the space-link directionality leaf (stdlib unittest)."""

import unittest

from e50_directionality_logic import (
    DIRECTION_BIDIRECTIONAL,
    DIRECTION_FORWARD_ONLY,
    DIRECTION_RETURN_ONLY,
    DUPLEX_ALTERNATING,
    DUPLEX_NOT_DECLARED,
    DUPLEX_SIMULTANEOUS,
    FORWARD,
    LATENCY_TOLERANCE_S,
    RETURN,
    alternating_response_time_s,
    assess_directionality,
    assess_link,
    declared_directions,
    direction_findings,
    idle_directions,
    required_directions,
    response_time_findings,
    response_time_s,
    simultaneity_declaration_findings,
    simultaneous_only_services,
    unsupported_services,
    validate_link,
)


def link(lid="SL-1", **kw):
    record = {
        "id": lid,
        "directionality": DIRECTION_BIDIRECTIONAL,
        "duplex": DUPLEX_SIMULTANEOUS,
        "services": ["telecommand-delivery", "telemetry-delivery"],
        "one_way_propagation_s": 1.25,
        "turnaround_time_s": 0.5,
        "slot_wait_time_s": 0.0,
    }
    record.update(kw)
    return record


class TestValidateLink(unittest.TestCase):
    def test_defaults_are_filled_in(self):
        norm = validate_link(
            {
                "id": "SL-1",
                "directionality": DIRECTION_FORWARD_ONLY,
                "services": ["telecommand-delivery"],
            }
        )
        self.assertEqual(norm["duplex"], DUPLEX_NOT_DECLARED)
        self.assertEqual(norm["one_way_propagation_s"], 0.0)
        self.assertEqual(norm["turnaround_time_s"], 0.0)
        self.assertIsNone(norm["max_response_time_s"])

    def test_non_mapping_raises(self):
        with self.assertRaises(ValueError):
            validate_link(["SL-1"])

    def test_empty_id_raises(self):
        with self.assertRaises(ValueError):
            validate_link(link(""))

    def test_unknown_directionality_raises(self):
        with self.assertRaises(ValueError):
            validate_link(link(directionality="omnidirectional"))

    def test_unknown_duplex_raises(self):
        with self.assertRaises(ValueError):
            validate_link(link(duplex="sometimes"))

    def test_unknown_service_raises(self):
        with self.assertRaises(ValueError):
            validate_link(link(services=["coffee-delivery"]))

    def test_empty_service_list_raises(self):
        with self.assertRaises(ValueError):
            validate_link(link(services=[]))

    def test_duplicate_service_raises(self):
        with self.assertRaises(ValueError):
            validate_link(
                link(services=["telemetry-delivery", "telemetry-delivery"])
            )

    def test_negative_turnaround_raises(self):
        with self.assertRaises(ValueError):
            validate_link(link(turnaround_time_s=-0.1))

    def test_boolean_propagation_raises(self):
        with self.assertRaises(ValueError):
            validate_link(link(one_way_propagation_s=True))

    def test_non_positive_allowance_raises(self):
        with self.assertRaises(ValueError):
            validate_link(link(max_response_time_s=0.0))


class TestDirectionDerivation(unittest.TestCase):
    def test_forward_only_carries_forward(self):
        self.assertEqual(declared_directions(DIRECTION_FORWARD_ONLY), (FORWARD,))

    def test_return_only_carries_return(self):
        self.assertEqual(declared_directions(DIRECTION_RETURN_ONLY), (RETURN,))

    def test_bidirectional_carries_both_in_canonical_order(self):
        self.assertEqual(
            declared_directions(DIRECTION_BIDIRECTIONAL), (FORWARD, RETURN)
        )

    def test_unknown_directionality_raises(self):
        with self.assertRaises(ValueError):
            declared_directions("half")

    def test_telecommand_needs_forward_only(self):
        self.assertEqual(required_directions(["telecommand-delivery"]), (FORWARD,))

    def test_ranging_needs_both_directions(self):
        self.assertEqual(
            required_directions(["two-way-ranging"]), (FORWARD, RETURN)
        )

    def test_required_directions_deduplicates_across_services(self):
        self.assertEqual(
            required_directions(["telemetry-delivery", "essential-telemetry"]),
            (RETURN,),
        )

    def test_required_directions_rejects_empty(self):
        with self.assertRaises(ValueError):
            required_directions([])


class TestDirectionFindings(unittest.TestCase):
    def test_return_service_on_a_forward_only_link_is_unsupported(self):
        bad = link(
            directionality=DIRECTION_FORWARD_ONLY,
            duplex="not-applicable",
            services=["telecommand-delivery", "telemetry-delivery"],
        )
        self.assertEqual(unsupported_services(bad), ["telemetry-delivery"])
        self.assertIn(
            "service-needs-a-direction-the-link-does-not-carry",
            direction_findings(bad),
        )

    def test_matched_declaration_has_no_direction_finding(self):
        self.assertEqual(direction_findings(link()), [])

    def test_idle_return_direction_is_reported(self):
        idle = link(services=["telecommand-delivery"])
        self.assertEqual(idle_directions(idle), [RETURN])
        self.assertIn(
            "declared-direction-carries-no-allocated-service",
            direction_findings(idle),
        )


class TestSimultaneityDeclaration(unittest.TestCase):
    def test_bidirectional_without_simultaneity_is_a_finding(self):
        self.assertIn(
            "bidirectional-link-without-a-declared-simultaneity",
            simultaneity_declaration_findings(link(duplex=DUPLEX_NOT_DECLARED)),
        )

    def test_simultaneity_on_a_one_way_link_is_a_finding(self):
        one_way = link(
            directionality=DIRECTION_RETURN_ONLY,
            duplex=DUPLEX_SIMULTANEOUS,
            services=["telemetry-delivery"],
        )
        self.assertIn(
            "simultaneity-declared-on-a-one-way-link",
            simultaneity_declaration_findings(one_way),
        )

    def test_declared_bidirectional_link_is_clean(self):
        self.assertEqual(simultaneity_declaration_findings(link()), [])

    def test_simultaneous_only_services_are_picked_out(self):
        loop = link(services=["telemetry-delivery", "two-way-ranging"])
        self.assertEqual(simultaneous_only_services(loop), ["two-way-ranging"])


class TestResponseTime(unittest.TestCase):
    def test_simultaneous_link_pays_the_round_trip_only(self):
        self.assertAlmostEqual(response_time_s(link()), 2.5, places=9)

    def test_alternating_link_pays_two_turnarounds_and_the_slot_wait(self):
        alt = link(duplex=DUPLEX_ALTERNATING, slot_wait_time_s=0.25)
        self.assertAlmostEqual(response_time_s(alt), 2.5 + 1.0 + 0.25, places=9)

    def test_one_way_link_has_no_response_time(self):
        one_way = link(
            directionality=DIRECTION_FORWARD_ONLY,
            duplex="not-applicable",
            services=["telecommand-delivery"],
        )
        self.assertIsNone(response_time_s(one_way))

    def test_undeclared_simultaneity_has_no_response_time(self):
        self.assertIsNone(response_time_s(link(duplex=DUPLEX_NOT_DECLARED)))

    def test_alternating_helper_rejects_a_negative_turnaround(self):
        with self.assertRaises(ValueError):
            alternating_response_time_s(1.0, -1.0, 0.0)

    def test_allowance_met_exactly_is_not_a_finding(self):
        exact = link(max_response_time_s=2.5)
        self.assertAlmostEqual(response_time_s(exact), exact["max_response_time_s"], places=9)
        self.assertEqual(response_time_findings(exact), [])

    def test_allowance_missed_is_a_finding(self):
        late = link(max_response_time_s=2.5 - 1.0e-6)
        self.assertIn(
            "two-way-response-time-exceeds-the-service-allowance",
            response_time_findings(late),
        )

    def test_tolerance_absorbs_a_sub_picosecond_overrun(self):
        near = link(max_response_time_s=2.5 - LATENCY_TOLERANCE_S / 2.0)
        self.assertEqual(response_time_findings(near), [])

    def test_ranging_on_an_alternating_link_is_a_finding(self):
        alt = link(
            duplex=DUPLEX_ALTERNATING,
            services=["telecommand-delivery", "telemetry-delivery", "two-way-ranging"],
        )
        self.assertIn(
            "simultaneous-two-way-service-on-an-alternating-link",
            response_time_findings(alt),
        )


class TestAssessLink(unittest.TestCase):
    def test_clean_link_is_compliant(self):
        result = assess_link(link())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["required_directions"], [FORWARD, RETURN])

    def test_broken_link_collects_every_finding(self):
        broken = link(
            directionality=DIRECTION_FORWARD_ONLY,
            duplex=DUPLEX_ALTERNATING,
            services=["telecommand-delivery", "two-way-ranging"],
        )
        result = assess_link(broken)
        self.assertFalse(result["compliant"])
        self.assertIn(
            "service-needs-a-direction-the-link-does-not-carry", result["findings"]
        )
        self.assertIn("simultaneity-declared-on-a-one-way-link", result["findings"])


class TestAssessDirectionality(unittest.TestCase):
    def test_schedule_groups_links_by_directionality(self):
        report = assess_directionality(
            [
                link("SL-1"),
                link(
                    "SL-2",
                    directionality=DIRECTION_RETURN_ONLY,
                    duplex="not-applicable",
                    services=["telemetry-delivery"],
                ),
            ]
        )
        self.assertEqual(report["bidirectional_ids"], ["SL-1"])
        self.assertEqual(report["one_way_ids"], ["SL-2"])
        self.assertTrue(report["compliant"])

    def test_duplicate_link_id_raises(self):
        with self.assertRaises(ValueError):
            assess_directionality([link("SL-1"), link("SL-1")])

    def test_empty_link_set_raises(self):
        with self.assertRaises(ValueError):
            assess_directionality([])

    def test_non_list_input_raises(self):
        with self.assertRaises(ValueError):
            assess_directionality(link())


if __name__ == "__main__":
    unittest.main()
