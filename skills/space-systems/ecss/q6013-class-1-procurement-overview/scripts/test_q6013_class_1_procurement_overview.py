"""Contract tests for the clause 4.3.1 purchasing-duty logic."""

import unittest

from q6013_class_1_procurement_overview_logic import (
    BASE_DUTIES,
    CHANNEL_EXTRA_DUTIES,
    COVERAGE_TOLERANCE,
    PERMITTED_ROLES,
    assess_procurement_overview,
    build_duty_register,
    duty_coverage,
    grade_duty,
    required_duties,
    validate_assignment,
    validate_supply_channel,
)


def _assignments(channel="manufacturer-direct", **overrides):
    duties = required_duties(channel)
    owners = {
        "specify-part-requirements": "component-engineering",
        "flow-down-to-supplier": "procurement-authority",
        "verify-supplier-approval": "procurement-authority",
        "verify-delivered-conformance": "component-engineering",
        "record-traceability": "supplier",
        "establish-manufacturer-traceability": "supplier",
        "counterfeit-avoidance-screening": "component-engineering",
    }
    built = []
    for duty in duties:
        entry = {
            "duty": duty,
            "owner": owners[duty],
            "evidence": "PA-2041 section covering %s" % duty,
        }
        if duty in overrides:
            patch = overrides[duty]
            if patch is None:
                continue
            entry.update(patch)
        built.append(entry)
    return built


def _spec(channel="manufacturer-direct", assignments=None, coverage_floor=1.0):
    return {
        "supply_channel": channel,
        "assignments": _assignments(channel) if assignments is None else assignments,
        "coverage_floor": coverage_floor,
    }


class SupplyChannelTests(unittest.TestCase):
    def test_channel_normalized(self):
        self.assertEqual(validate_supply_channel("Franchised Distributor"),
                         "franchised-distributor")

    def test_undeclared_channel_rejected(self):
        with self.assertRaises(ValueError):
            validate_supply_channel(None)

    def test_blank_channel_rejected(self):
        with self.assertRaises(ValueError):
            validate_supply_channel("   ")

    def test_unknown_channel_rejected(self):
        with self.assertRaises(ValueError):
            validate_supply_channel("a-friend-of-the-project")

    def test_non_string_channel_rejected(self):
        with self.assertRaises(ValueError):
            validate_supply_channel(7)


class RegisterTests(unittest.TestCase):
    def test_direct_purchase_carries_the_base_register_only(self):
        self.assertEqual(required_duties("manufacturer-direct"), tuple(BASE_DUTIES))

    def test_open_market_adds_traceability_and_screening_duties(self):
        duties = required_duties("open-market")
        self.assertEqual(len(duties), len(BASE_DUTIES) + 2)
        self.assertIn("establish-manufacturer-traceability", duties)
        self.assertIn("counterfeit-avoidance-screening", duties)

    def test_independent_distributor_carries_the_same_extra_duties(self):
        self.assertEqual(
            CHANNEL_EXTRA_DUTIES["independent-distributor"],
            CHANNEL_EXTRA_DUTIES["open-market"],
        )

    def test_franchised_route_does_not_add_extra_duties(self):
        self.assertEqual(required_duties("franchised-distributor"), tuple(BASE_DUTIES))


class AssignmentValidationTests(unittest.TestCase):
    def test_duty_and_owner_normalized(self):
        record = validate_assignment(
            {"duty": "Record Traceability", "owner": "Supplier", "evidence": "PA-2041"}
        )
        self.assertEqual(record["duty"], "record-traceability")
        self.assertEqual(record["owner"], "supplier")

    def test_missing_duty_key_rejected(self):
        with self.assertRaises(ValueError):
            validate_assignment({"owner": "supplier"})

    def test_non_mapping_assignment_rejected(self):
        with self.assertRaises(ValueError):
            validate_assignment(["record-traceability", "supplier"])

    def test_non_string_evidence_rejected(self):
        with self.assertRaises(ValueError):
            validate_assignment({"duty": "record-traceability", "owner": "supplier",
                                 "evidence": 2041})

    def test_evidence_whitespace_is_stripped(self):
        record = validate_assignment({"duty": "record-traceability", "owner": "supplier",
                                      "evidence": "   "})
        self.assertEqual(record["evidence"], "")


class DutyGradingTests(unittest.TestCase):
    def test_assigned_and_evidenced_duty_is_discharged(self):
        record = grade_duty("record-traceability",
                            {"duty": "record-traceability", "owner": "supplier",
                             "evidence": "PA-2041"})
        self.assertEqual(record["state"], "discharged")
        self.assertEqual(record["reason"], "")

    def test_unassigned_duty_is_open(self):
        record = grade_duty("record-traceability", None)
        self.assertEqual(record["state"], "open")

    def test_duty_with_no_owner_is_open(self):
        record = grade_duty("record-traceability",
                            {"duty": "record-traceability", "evidence": "PA-2041"})
        self.assertEqual(record["state"], "open")

    def test_owner_outside_the_permitted_roles_is_open(self):
        record = grade_duty("record-traceability",
                            {"duty": "record-traceability", "owner": "a-passing-broker",
                             "evidence": "PA-2041"})
        self.assertEqual(record["state"], "open")
        self.assertIn("permitted role", record["reason"])

    def test_assigned_but_unevidenced_duty_is_open(self):
        record = grade_duty("record-traceability",
                            {"duty": "record-traceability", "owner": "supplier"})
        self.assertEqual(record["state"], "open")
        self.assertIn("no evidence", record["reason"])

    def test_grading_an_assignment_for_another_duty_rejected(self):
        with self.assertRaises(ValueError):
            grade_duty("record-traceability",
                       {"duty": "flow-down-to-supplier", "owner": "supplier",
                        "evidence": "PA-2041"})

    def test_every_permitted_role_is_accepted(self):
        for role in PERMITTED_ROLES:
            record = grade_duty("record-traceability",
                                {"duty": "record-traceability", "owner": role,
                                 "evidence": "PA-2041"})
            self.assertEqual(record["state"], "discharged")


class CoverageTests(unittest.TestCase):
    def test_full_register_is_full_coverage(self):
        built = build_duty_register("manufacturer-direct", _assignments())
        self.assertAlmostEqual(duty_coverage(built["duties"]), 1.0, places=9)

    def test_one_open_duty_of_five_gives_four_fifths(self):
        assignments = _assignments(**{"record-traceability": None})
        built = build_duty_register("manufacturer-direct", assignments)
        self.assertAlmostEqual(duty_coverage(built["duties"]), 0.8, places=9)

    def test_empty_graded_register_rejected(self):
        with self.assertRaises(ValueError):
            duty_coverage([])

    def test_malformed_duty_record_rejected(self):
        with self.assertRaises(ValueError):
            duty_coverage([{"duty": "record-traceability"}])

    def test_duplicate_duty_assignment_rejected(self):
        assignments = _assignments() + [
            {"duty": "record-traceability", "owner": "supplier", "evidence": "PA-2041"}
        ]
        with self.assertRaises(ValueError):
            build_duty_register("manufacturer-direct", assignments)

    def test_assignment_outside_the_register_is_reported(self):
        assignments = _assignments() + [
            {"duty": "counterfeit-avoidance-screening", "owner": "supplier",
             "evidence": "PA-2041"}
        ]
        built = build_duty_register("manufacturer-direct", assignments)
        self.assertEqual(built["extraneous"], ["counterfeit-avoidance-screening"])


class OverviewAssessmentTests(unittest.TestCase):
    def test_fully_discharged_direct_purchase_is_acceptable(self):
        result = assess_procurement_overview(_spec())
        self.assertTrue(result["acceptable"])
        self.assertEqual(result["findings"], [])

    def test_coverage_exactly_at_the_floor_is_met(self):
        assignments = _assignments(**{"record-traceability": None})
        result = assess_procurement_overview(
            _spec(assignments=assignments, coverage_floor=0.8)
        )
        self.assertAlmostEqual(result["coverage"], result["coverage_floor"], places=9)
        self.assertTrue(result["coverage_met"])

    def test_open_duty_is_still_a_finding_at_a_met_floor(self):
        assignments = _assignments(**{"record-traceability": None})
        result = assess_procurement_overview(
            _spec(assignments=assignments, coverage_floor=0.8)
        )
        self.assertFalse(result["acceptable"])
        self.assertIn("record-traceability", result["open_duties"])

    def test_open_market_purchase_reusing_the_direct_register_is_short(self):
        assignments = _assignments("manufacturer-direct")
        result = assess_procurement_overview(
            _spec(channel="open-market", assignments=assignments)
        )
        self.assertFalse(result["acceptable"])
        self.assertIn("establish-manufacturer-traceability", result["open_duties"])
        self.assertIn("counterfeit-avoidance-screening", result["open_duties"])

    def test_open_market_purchase_with_the_full_register_is_acceptable(self):
        result = assess_procurement_overview(_spec(channel="open-market"))
        self.assertTrue(result["acceptable"])

    def test_unevidenced_duty_lowers_coverage(self):
        assignments = _assignments(**{"flow-down-to-supplier": {"evidence": ""}})
        result = assess_procurement_overview(
            _spec(assignments=assignments, coverage_floor=0.0)
        )
        self.assertAlmostEqual(result["coverage"], 0.8, places=9)
        self.assertFalse(result["acceptable"])

    def test_coverage_below_floor_is_named(self):
        assignments = _assignments(**{"record-traceability": None,
                                      "verify-supplier-approval": None})
        result = assess_procurement_overview(
            _spec(assignments=assignments, coverage_floor=0.9)
        )
        self.assertFalse(result["coverage_met"])
        self.assertTrue(any("below the declared floor" in f for f in result["findings"]))

    def test_missing_spec_key_rejected(self):
        spec = _spec()
        del spec["coverage_floor"]
        with self.assertRaises(ValueError):
            assess_procurement_overview(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_procurement_overview(["supply_channel"])

    def test_floor_outside_the_unit_interval_rejected(self):
        with self.assertRaises(ValueError):
            assess_procurement_overview(_spec(coverage_floor=1.4))

    def test_boolean_floor_rejected(self):
        with self.assertRaises(ValueError):
            assess_procurement_overview(_spec(coverage_floor=True))

    def test_every_open_duty_is_named_not_only_the_first(self):
        assignments = _assignments(**{"record-traceability": None,
                                      "verify-supplier-approval": None})
        result = assess_procurement_overview(
            _spec(assignments=assignments, coverage_floor=0.0)
        )
        self.assertEqual(len(result["open_duties"]), 2)

    def test_tolerance_is_small_enough_to_be_representation_only(self):
        self.assertLess(COVERAGE_TOLERANCE, 1e-6)


if __name__ == "__main__":
    unittest.main()
