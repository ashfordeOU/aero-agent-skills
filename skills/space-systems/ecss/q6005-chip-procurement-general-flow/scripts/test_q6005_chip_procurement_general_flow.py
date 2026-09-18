"""Contract test for the ECSS-Q-ST-60-05C clause 8.1 chip procurement flow leaf.

Offline, deterministic, stdlib unittest.
Run: python3 test_q6005_chip_procurement_general_flow.py
"""

import unittest

from q6005_chip_procurement_general_flow_logic import (
    DEFAULT_OWNERS,
    MANDATORY_PREREQUISITES,
    OPTIONAL_ACTIVITIES,
    RESPONSIBLE_PARTIES,
    audit_flow,
    build_flow,
    canonical_flow,
    canonical_prerequisites,
    critical_path,
    default_owner,
    flow_duration_days,
    known_activities,
    mandatory_activities,
    normalize_activity,
    plan_chip_procurement,
    reachable_from,
    schedule_flow,
    topological_order,
)


def entry(activity, predecessors=None, duration_days=2, owner=None):
    """One activity entry, defaulted to the canonical owner and two days."""
    return {
        "activity": activity,
        "duration_days": duration_days,
        "owner": owner or DEFAULT_OWNERS.get(activity, "hybrid-manufacturer"),
        "predecessors": list(predecessors or []),
    }


def without(activity):
    """The canonical flow with one activity and every link to it removed."""
    kept = []
    for record in canonical_flow():
        if record["activity"] == activity:
            continue
        record = dict(record)
        record["predecessors"] = [p for p in record["predecessors"] if p != activity]
        kept.append(record)
    return kept


class ArrangementTests(unittest.TestCase):
    def test_the_specification_is_the_only_activity_with_no_prerequisite(self):
        roots = [a for a in mandatory_activities() if not canonical_prerequisites(a)]
        self.assertEqual(roots, ["procurement-specification-issue"])

    def test_release_to_assembly_follows_receipt_inspection(self):
        self.assertIn(
            "incoming-receipt-inspection",
            canonical_prerequisites("release-to-hybrid-assembly"),
        )

    def test_optional_activities_are_not_mandatory(self):
        for name in OPTIONAL_ACTIVITIES:
            self.assertNotIn(name, mandatory_activities())

    def test_every_known_activity_resolves_its_prerequisites(self):
        for name in known_activities():
            self.assertIsInstance(canonical_prerequisites(name), tuple)

    def test_unknown_activity_rejected(self):
        with self.assertRaises(ValueError):
            canonical_prerequisites("haggle-with-the-broker")

    def test_every_mandatory_activity_has_a_default_owner(self):
        for name in mandatory_activities():
            self.assertIn(default_owner(name), RESPONSIBLE_PARTIES)

    def test_an_optional_activity_has_no_default_owner(self):
        with self.assertRaises(ValueError):
            default_owner("supplier-line-audit")


class NormalizeActivityTests(unittest.TestCase):
    def test_a_complete_entry_round_trips(self):
        record = normalize_activity(entry("wafer-lot-acceptance", ["purchase-order-placement"]))
        self.assertEqual(record["activity"], "wafer-lot-acceptance")
        self.assertEqual(record["predecessors"], ["purchase-order-placement"])

    def test_non_mapping_rejected(self):
        with self.assertRaises(ValueError):
            normalize_activity(["wafer-lot-acceptance"])

    def test_unknown_activity_name_rejected(self):
        with self.assertRaises(ValueError):
            normalize_activity(entry("die-blessing-ceremony"))

    def test_a_zero_duration_rejected(self):
        with self.assertRaises(ValueError):
            normalize_activity(entry("die-visual-inspection", duration_days=0))

    def test_a_fractional_duration_rejected(self):
        with self.assertRaises(ValueError):
            normalize_activity(entry("die-visual-inspection", duration_days=1.5))

    def test_an_unknown_owner_rejected(self):
        with self.assertRaises(ValueError):
            normalize_activity(entry("die-visual-inspection", owner="the-intern"))

    def test_a_self_referencing_predecessor_rejected(self):
        with self.assertRaises(ValueError):
            normalize_activity(
                entry("die-visual-inspection", ["die-visual-inspection"])
            )

    def test_a_repeated_predecessor_rejected(self):
        with self.assertRaises(ValueError):
            normalize_activity(
                entry(
                    "die-visual-inspection",
                    ["die-electrical-probe", "die-electrical-probe"],
                )
            )

    def test_predecessors_must_be_a_sequence(self):
        raw = entry("die-visual-inspection")
        raw["predecessors"] = "die-electrical-probe"
        with self.assertRaises(ValueError):
            normalize_activity(raw)


class BuildFlowTests(unittest.TestCase):
    def test_the_canonical_arrangement_builds(self):
        flow = build_flow(canonical_flow())
        self.assertEqual(len(flow), len(mandatory_activities()))

    def test_an_empty_flow_rejected(self):
        with self.assertRaises(ValueError):
            build_flow([])

    def test_a_non_sequence_flow_rejected(self):
        with self.assertRaises(ValueError):
            build_flow(entry("procurement-specification-issue"))

    def test_a_duplicate_activity_rejected(self):
        with self.assertRaises(ValueError):
            build_flow(
                [entry("procurement-specification-issue")] * 2
            )

    def test_a_predecessor_outside_the_flow_rejected(self):
        with self.assertRaises(ValueError):
            build_flow(
                [entry("die-visual-inspection", ["die-electrical-probe"])]
            )


class TopologicalOrderTests(unittest.TestCase):
    def test_the_canonical_order_starts_at_the_specification(self):
        order = topological_order(build_flow(canonical_flow()))
        self.assertEqual(order[0], "procurement-specification-issue")

    def test_the_canonical_order_ends_at_release_to_assembly(self):
        order = topological_order(build_flow(canonical_flow()))
        self.assertEqual(order[-1], "release-to-hybrid-assembly")

    def test_every_predecessor_precedes_its_activity(self):
        flow = build_flow(canonical_flow())
        order = topological_order(flow)
        for name, record in flow.items():
            for ref in record["predecessors"]:
                self.assertLess(order.index(ref), order.index(name))

    def test_a_cycle_is_rejected(self):
        flow = build_flow(
            [
                entry("procurement-specification-issue", ["die-source-selection"]),
                entry("die-source-selection", ["procurement-specification-issue"]),
            ]
        )
        with self.assertRaises(ValueError):
            topological_order(flow)

    def test_an_empty_flow_mapping_rejected(self):
        with self.assertRaises(ValueError):
            topological_order({})


class ReachabilityTests(unittest.TestCase):
    def setUp(self):
        self.flow = build_flow(canonical_flow())

    def test_release_follows_the_specification(self):
        self.assertIn(
            "release-to-hybrid-assembly",
            reachable_from(self.flow, "procurement-specification-issue"),
        )

    def test_nothing_follows_the_last_activity(self):
        self.assertEqual(reachable_from(self.flow, "release-to-hybrid-assembly"), set())

    def test_an_activity_outside_the_flow_rejected(self):
        with self.assertRaises(ValueError):
            reachable_from(self.flow, "supplier-line-audit")


class ScheduleTests(unittest.TestCase):
    def test_the_first_activity_starts_on_day_zero(self):
        schedule = schedule_flow(build_flow(canonical_flow()))
        self.assertEqual(schedule["procurement-specification-issue"]["start_day"], 0)

    def test_a_chain_of_ten_two_day_activities_takes_twenty_days(self):
        self.assertEqual(flow_duration_days(build_flow(canonical_flow())), 20)

    def test_an_activity_starts_when_its_last_predecessor_finishes(self):
        flow = build_flow(canonical_flow())
        schedule = schedule_flow(flow)
        self.assertEqual(
            schedule["die-electrical-probe"]["start_day"],
            schedule["wafer-lot-acceptance"]["finish_day"],
        )

    def test_a_parallel_branch_does_not_extend_a_shorter_chain(self):
        activities = canonical_flow()
        activities.append(
            entry("supplier-line-audit", ["die-source-selection"], duration_days=1,
                  owner="customer")
        )
        self.assertEqual(flow_duration_days(build_flow(activities)), 20)

    def test_a_longer_parallel_branch_is_not_on_the_chain_unless_it_is_joined(self):
        activities = canonical_flow()
        activities.append(
            entry("die-radiation-lot-verification", ["wafer-lot-acceptance"],
                  duration_days=30, owner="die-supplier")
        )
        self.assertEqual(flow_duration_days(build_flow(activities)), 38)

    def test_the_critical_path_runs_end_to_end(self):
        path = critical_path(build_flow(canonical_flow()))
        self.assertEqual(path[0], "procurement-specification-issue")
        self.assertEqual(path[-1], "release-to-hybrid-assembly")
        self.assertEqual(len(path), len(mandatory_activities()))


class AuditTests(unittest.TestCase):
    def test_the_canonical_arrangement_audits_clean(self):
        self.assertEqual(audit_flow(build_flow(canonical_flow())), [])

    def test_a_missing_mandatory_activity_is_reported(self):
        findings = audit_flow(build_flow(without("die-visual-inspection")))
        self.assertIn(
            {"activity": "die-visual-inspection", "finding": "mandatory-activity-missing"},
            findings,
        )

    def test_a_forgotten_link_is_reported_even_when_both_activities_are_present(self):
        activities = []
        for record in canonical_flow():
            record = dict(record)
            if record["activity"] == "die-visual-inspection":
                record["predecessors"] = ["purchase-order-placement"]
            activities.append(record)
        findings = audit_flow(build_flow(activities))
        self.assertIn(
            {
                "activity": "die-visual-inspection",
                "finding": "prerequisite-link-missing",
                "prerequisite": "die-electrical-probe",
            },
            findings,
        )

    def test_an_owner_deviation_is_reported_but_does_not_break_the_flow(self):
        activities = []
        for record in canonical_flow():
            record = dict(record)
            if record["activity"] == "incoming-receipt-inspection":
                record["owner"] = "customer"
            activities.append(record)
        report = plan_chip_procurement(activities)
        self.assertEqual(report["owner_deviations"], ["incoming-receipt-inspection"])
        self.assertTrue(report["arrangement_complete"])

    def test_an_empty_flow_mapping_rejected(self):
        with self.assertRaises(ValueError):
            audit_flow({})


class PlanTests(unittest.TestCase):
    def test_the_canonical_arrangement_plans_complete(self):
        report = plan_chip_procurement(canonical_flow())
        self.assertTrue(report["arrangement_complete"])
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["total_duration_days"], 20)

    def test_a_missing_activity_makes_the_arrangement_incomplete(self):
        report = plan_chip_procurement(without("die-lot-traceability-record"))
        self.assertFalse(report["arrangement_complete"])

    def test_the_activity_order_lists_every_activity_once(self):
        report = plan_chip_procurement(canonical_flow())
        self.assertEqual(sorted(report["activity_order"]), list(mandatory_activities()))

    def test_the_schedule_covers_every_activity(self):
        report = plan_chip_procurement(canonical_flow())
        self.assertEqual(sorted(report["schedule"]), list(mandatory_activities()))

    def test_an_optional_activity_is_carried_without_a_finding(self):
        activities = canonical_flow()
        activities.append(
            entry("nonconformance-disposition", ["incoming-receipt-inspection"],
                  duration_days=1, owner="hybrid-manufacturer")
        )
        report = plan_chip_procurement(activities)
        self.assertEqual(report["findings"], [])
        self.assertIn("nonconformance-disposition", report["flow"])

    def test_durations_are_honoured_in_the_total(self):
        activities = [dict(r) for r in canonical_flow()]
        activities[0]["duration_days"] = 12
        report = plan_chip_procurement(activities)
        self.assertEqual(report["total_duration_days"], 30)

    def test_a_non_default_canonical_duration_scales_the_flow(self):
        self.assertEqual(
            plan_chip_procurement(canonical_flow(duration_days=3))["total_duration_days"],
            30,
        )

    def test_a_zero_canonical_duration_rejected(self):
        with self.assertRaises(ValueError):
            canonical_flow(duration_days=0)

    def test_a_fractional_canonical_duration_rejected(self):
        with self.assertRaises(ValueError):
            canonical_flow(duration_days=2.5)

    def test_the_canonical_flow_matches_the_arrangement(self):
        names = [record["activity"] for record in canonical_flow()]
        self.assertEqual(sorted(names), sorted(MANDATORY_PREREQUISITES))


if __name__ == "__main__":
    unittest.main()
