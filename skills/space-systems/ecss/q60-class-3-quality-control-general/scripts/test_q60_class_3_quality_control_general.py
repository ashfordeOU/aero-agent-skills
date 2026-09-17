"""Contract tests for the clause 6.5.1 post-receipt control route logic."""

import unittest

from q60_class_3_quality_control_general_logic import (
    CONTROL_ACTIVITIES,
    PROFILE_ATTRIBUTES,
    RECORD_STATUSES,
    RELEASE_VERDICTS,
    applicable_activities,
    assess_control_route,
    mandatory_activities,
    omission_admissible,
    ordering_findings,
    release_verdict,
    resolve_route,
    route_completeness,
)

BASE_ROUTE = (
    "documentation-review",
    "receiving-inspection",
    "external-visual-examination",
    "serialisation-and-bagging",
)

GOOD_JUSTIFICATION = {"reference": "NCR-0091", "approved_by": "Product Assurance"}


def all_closed(route):
    return {name: "closed" for name in route}


class ApplicabilityTests(unittest.TestCase):
    def test_a_plain_lot_owes_only_the_mandatory_activities(self):
        self.assertEqual(applicable_activities({}), mandatory_activities())

    def test_a_radiation_sensitive_lot_brings_its_verification_in(self):
        owed = applicable_activities({"radiation_sensitive": True})
        self.assertIn("radiation-lot-verification", owed)

    def test_a_false_attribute_brings_nothing_in(self):
        self.assertEqual(
            applicable_activities({"radiation_sensitive": False}), mandatory_activities()
        )

    def test_several_attributes_stack(self):
        owed = applicable_activities(
            {"radiation_sensitive": True, "cavity_device": True}
        )
        self.assertEqual(len(owed), len(mandatory_activities()) + 2)

    def test_an_unknown_attribute_is_rejected(self):
        with self.assertRaises(ValueError):
            applicable_activities({"gold_plated": True})

    def test_a_non_boolean_attribute_is_rejected(self):
        with self.assertRaises(ValueError):
            applicable_activities({"cavity_device": "yes"})

    def test_every_profile_attribute_triggers_an_activity(self):
        for attribute in PROFILE_ATTRIBUTES:
            owed = applicable_activities({attribute: True})
            self.assertGreater(len(owed), len(mandatory_activities()))


class RouteResolutionTests(unittest.TestCase):
    def test_the_mandatory_route_resolves_in_dependency_order(self):
        self.assertEqual(resolve_route(mandatory_activities()), BASE_ROUTE)

    def test_a_prerequisite_always_precedes_what_needs_it(self):
        route = resolve_route(
            applicable_activities({"destructive_analysis_required": True})
        )
        self.assertLess(
            route.index("external-visual-examination"),
            route.index("destructive-physical-analysis"),
        )

    def test_the_order_is_the_same_every_time(self):
        first = resolve_route(applicable_activities({"cavity_device": True}))
        second = resolve_route(list(reversed(applicable_activities({"cavity_device": True}))))
        self.assertEqual(first, second)

    def test_a_prerequisite_missing_from_the_route_is_refused(self):
        with self.assertRaises(ValueError):
            resolve_route(["external-visual-examination"])

    def test_an_unknown_activity_is_refused(self):
        with self.assertRaises(ValueError):
            resolve_route(["receiving-inspection", "tea-break"])

    def test_a_repeated_activity_is_refused(self):
        with self.assertRaises(ValueError):
            resolve_route(["receiving-inspection", "receiving-inspection"])

    def test_an_empty_route_resolves_to_nothing(self):
        self.assertEqual(resolve_route([]), ())

    def test_every_activity_declares_a_weight_and_its_prerequisites(self):
        for name, entry in CONTROL_ACTIVITIES.items():
            self.assertGreater(entry["weight"], 0)
            for prerequisite in entry["requires"]:
                self.assertIn(prerequisite, CONTROL_ACTIVITIES)


class OmissionTests(unittest.TestCase):
    def test_an_attribute_driven_activity_may_be_omitted_on_a_record(self):
        verdict = omission_admissible("radiation-lot-verification", GOOD_JUSTIFICATION)
        self.assertTrue(verdict["admissible"])

    def test_a_mandatory_activity_may_never_be_omitted(self):
        verdict = omission_admissible("documentation-review", GOOD_JUSTIFICATION)
        self.assertFalse(verdict["admissible"])
        self.assertTrue(any("every received lot" in r for r in verdict["reasons"]))

    def test_an_omission_with_no_record_is_refused(self):
        verdict = omission_admissible("radiation-lot-verification", None)
        self.assertFalse(verdict["admissible"])

    def test_an_omission_with_no_approver_is_refused(self):
        verdict = omission_admissible(
            "radiation-lot-verification", {"reference": "NCR-0091"}
        )
        self.assertFalse(verdict["admissible"])
        self.assertTrue(any("approved by" in r for r in verdict["reasons"]))

    def test_an_omission_with_no_reference_is_refused(self):
        verdict = omission_admissible(
            "radiation-lot-verification", {"approved_by": "Product Assurance"}
        )
        self.assertFalse(verdict["admissible"])

    def test_an_unknown_activity_cannot_be_omitted(self):
        with self.assertRaises(ValueError):
            omission_admissible("tea-break", GOOD_JUSTIFICATION)


class OrderingTests(unittest.TestCase):
    def test_a_route_closed_in_order_reports_nothing(self):
        self.assertEqual(ordering_findings(BASE_ROUTE, all_closed(BASE_ROUTE)), ())

    def test_an_activity_closed_before_its_prerequisite_is_reported(self):
        findings = ordering_findings(
            BASE_ROUTE, {"external-visual-examination": "closed"}
        )
        self.assertEqual(len(findings), 1)
        self.assertIn("receiving-inspection", findings[0])

    def test_an_open_activity_out_of_order_is_not_a_breach(self):
        self.assertEqual(
            ordering_findings(BASE_ROUTE, {"external-visual-examination": "open"}), ()
        )

    def test_a_record_with_an_unknown_status_is_rejected(self):
        with self.assertRaises(ValueError):
            ordering_findings(BASE_ROUTE, {"receiving-inspection": "nearly"})

    def test_a_record_naming_an_unknown_activity_is_rejected(self):
        with self.assertRaises(ValueError):
            ordering_findings(BASE_ROUTE, {"tea-break": "closed"})

    def test_a_status_may_be_given_bare_or_inside_a_record(self):
        bare = ordering_findings(BASE_ROUTE, {"external-visual-examination": "closed"})
        wrapped = ordering_findings(
            BASE_ROUTE, {"external-visual-examination": {"status": "closed"}}
        )
        self.assertEqual(bare, wrapped)

    def test_every_recognised_status_is_accepted(self):
        for status in RECORD_STATUSES:
            ordering_findings(BASE_ROUTE, {"receiving-inspection": status})


class CompletenessTests(unittest.TestCase):
    def test_a_fully_closed_route_is_complete(self):
        entry = route_completeness(BASE_ROUTE, all_closed(BASE_ROUTE))
        self.assertTrue(entry["complete"])
        self.assertAlmostEqual(entry["index"], 1.0, places=9)

    def test_the_index_is_weighted_not_counted(self):
        entry = route_completeness(
            BASE_ROUTE,
            {"documentation-review": "closed", "receiving-inspection": "closed"},
        )
        self.assertEqual(entry["weight_total"], 9)
        self.assertEqual(entry["weight_closed"], 6)
        self.assertAlmostEqual(entry["index"], 6 / 9, places=9)

    def test_an_unrecorded_activity_counts_as_open(self):
        entry = route_completeness(BASE_ROUTE, {})
        self.assertEqual(len(entry["open"]), len(BASE_ROUTE))
        self.assertAlmostEqual(entry["index"], 0.0, places=9)

    def test_a_failed_activity_is_separated_from_an_open_one(self):
        entry = route_completeness(BASE_ROUTE, {"receiving-inspection": "failed"})
        self.assertEqual(entry["failed"], ("receiving-inspection",))
        self.assertNotIn("receiving-inspection", entry["open"])

    def test_an_empty_route_is_rejected(self):
        with self.assertRaises(ValueError):
            route_completeness([], {})

    def test_records_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            route_completeness(BASE_ROUTE, ["closed"])


class VerdictTests(unittest.TestCase):
    def test_a_closed_route_releases_the_lot(self):
        self.assertEqual(release_verdict(0, 0, 0, 0), "release-to-stores")

    def test_an_open_conditional_holds_the_release_against_it(self):
        self.assertEqual(release_verdict(0, 1, 0, 0), "release-pending-conditional")

    def test_an_open_mandatory_quarantines_the_lot(self):
        self.assertEqual(release_verdict(1, 0, 0, 0), "hold-in-quarantine")

    def test_an_ordering_breach_quarantines_the_lot(self):
        self.assertEqual(release_verdict(0, 0, 0, 1), "hold-in-quarantine")

    def test_a_failed_activity_outranks_everything(self):
        self.assertEqual(release_verdict(0, 0, 1, 1), "reject-lot")

    def test_every_verdict_returned_is_a_known_verdict(self):
        for mandatory in (0, 1):
            for conditional in (0, 1):
                for failed in (0, 1):
                    for breaches in (0, 1):
                        self.assertIn(
                            release_verdict(mandatory, conditional, failed, breaches),
                            RELEASE_VERDICTS,
                        )

    def test_a_negative_count_is_rejected(self):
        with self.assertRaises(ValueError):
            release_verdict(-1, 0, 0, 0)

    def test_a_boolean_count_is_rejected(self):
        with self.assertRaises(ValueError):
            release_verdict(True, 0, 0, 0)


class AssessRouteTests(unittest.TestCase):
    def test_a_plain_lot_with_everything_closed_goes_to_stores(self):
        result = assess_control_route({}, all_closed(BASE_ROUTE))
        self.assertEqual(result["verdict"], "release-to-stores")
        self.assertTrue(result["route_clear"])
        self.assertAlmostEqual(result["completeness"]["index"], 1.0, places=9)

    def test_an_untouched_lot_is_held(self):
        result = assess_control_route({})
        self.assertEqual(result["verdict"], "hold-in-quarantine")
        self.assertEqual(len(result["mandatory_open"]), len(BASE_ROUTE))

    def test_a_dependency_the_profile_never_triggered_is_pulled_in(self):
        result = assess_control_route({"manufacturer_screening_incomplete": True})
        self.assertEqual(result["pulled_in"], ("lot-homogeneity-check",))
        self.assertIn("lot-homogeneity-check", result["route"])

    def test_an_open_conditional_leaves_the_release_pending(self):
        records = all_closed(BASE_ROUTE)
        result = assess_control_route({"cavity_device": True}, records)
        self.assertEqual(result["verdict"], "release-pending-conditional")
        self.assertEqual(
            result["conditional_open"], ("particle-impact-noise-detection",)
        )

    def test_an_admissible_omission_removes_the_activity_from_the_route(self):
        result = assess_control_route(
            {"radiation_sensitive": True},
            all_closed(BASE_ROUTE),
            {"radiation-lot-verification": GOOD_JUSTIFICATION},
        )
        self.assertEqual(result["omitted"], ("radiation-lot-verification",))
        self.assertNotIn("radiation-lot-verification", result["route"])
        self.assertEqual(result["verdict"], "release-to-stores")

    def test_an_omission_of_a_mandatory_activity_is_refused(self):
        result = assess_control_route(
            {}, all_closed(BASE_ROUTE), {"documentation-review": GOOD_JUSTIFICATION}
        )
        self.assertEqual(result["omitted"], ())
        self.assertTrue(
            any("not admissible" in note for note in result["findings"])
        )

    def test_an_omission_something_else_depends_on_is_refused(self):
        result = assess_control_route(
            {"manufacturer_screening_incomplete": True},
            None,
            {"lot-homogeneity-check": GOOD_JUSTIFICATION},
        )
        self.assertEqual(result["omitted"], ())
        self.assertTrue(
            any("depends on it" in note for note in result["findings"])
        )
        self.assertIn("lot-homogeneity-check", result["route"])

    def test_an_activity_closed_out_of_order_quarantines_the_lot(self):
        records = all_closed(BASE_ROUTE)
        records["receiving-inspection"] = "open"
        result = assess_control_route({}, records)
        self.assertEqual(result["verdict"], "hold-in-quarantine")
        self.assertTrue(result["ordering_breaches"])

    def test_a_failed_activity_rejects_the_lot(self):
        records = all_closed(BASE_ROUTE)
        records["external-visual-examination"] = "failed"
        result = assess_control_route({}, records)
        self.assertEqual(result["verdict"], "reject-lot")
        self.assertTrue(any("failed" in note for note in result["findings"]))

    def test_omitting_something_not_in_the_route_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_control_route({}, None, {"radiation-lot-verification": GOOD_JUSTIFICATION})

    def test_omissions_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            assess_control_route({}, None, ["radiation-lot-verification"])

    def test_the_route_length_matches_the_resolved_route(self):
        result = assess_control_route({"destructive_analysis_required": True})
        self.assertEqual(result["route_length"], len(result["route"]))
        self.assertEqual(result["route_length"], len(BASE_ROUTE) + 1)


if __name__ == "__main__":
    unittest.main()
