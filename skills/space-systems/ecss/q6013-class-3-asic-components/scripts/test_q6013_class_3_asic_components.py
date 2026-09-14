"""Contract tests for the clause 6.6.2 class 3 delegated ASIC assurance rules.

Every workflow step the SKILL.md sets out is exercised here, together with the
stop conditions the gate 3 contract reviews: a device kind this class never
delegates, a non-delegable objective resting on the supplier's own word, a
rated envelope the mission overruns, a credited total landing exactly on the
floor, and evidence offered against an objective the catalogue does not name.
"""

import unittest

from q6013_class_3_asic_components_logic import (
    ASSURANCE_BELOW_FLOOR,
    DEFAULT_ASIC_POLICY,
    DEFAULT_OBJECTIVES,
    DELEGABLE_DEVICE_KINDS,
    DELEGATED_ASSURANCE_ACCEPTED,
    DELEGATION_ROUTE_CLOSED,
    EVIDENCE_STRENGTHS,
    MANDATORY_OBJECTIVE_UNEVIDENCED,
    RATED_ENVELOPE_SHORTFALL,
    assess_delegated_asic_assurance,
    assurance_meets_floor,
    credit_objective,
    credited_basis_points,
    envelope_shortfalls,
    evidence_credit_percent,
    route_is_delegable,
    validate_asic_policy,
    validate_device,
    validate_mission_envelope,
    validate_objectives,
)


def _device(**overrides):
    device = {
        "reference": "ASIC-7710",
        "kind": "catalogue-standard-product",
        "rated_temp_min_c": -40,
        "rated_temp_max_c": 85,
        "rated_total_dose_krad": 30,
    }
    device.update(overrides)
    return device


def _mission(**overrides):
    mission = {"temp_min_c": -30, "temp_max_c": 70, "total_dose_krad": 20}
    mission.update(overrides)
    return mission


def _evidence(**overrides):
    evidence = {name: "independent-audit" for name in DEFAULT_OBJECTIVES}
    evidence.update(overrides)
    return evidence


def _policy(**overrides):
    policy = dict(DEFAULT_ASIC_POLICY)
    policy.update(overrides)
    return policy


def _case(**overrides):
    case = {"device": _device(), "mission": _mission(), "evidence": _evidence()}
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        settings = validate_asic_policy(None)
        self.assertEqual(settings["assurance_floor_percent"], 70)
        self.assertEqual(settings["min_strength_non_delegable"], "third-party-report")

    def test_unknown_policy_key_rejected(self):
        with self.assertRaises(ValueError):
            validate_asic_policy({"assurance_floor": 70})

    def test_floor_outside_a_percentage_rejected(self):
        with self.assertRaises(ValueError):
            validate_asic_policy({"assurance_floor_percent": 101})

    def test_unknown_minimum_strength_rejected(self):
        with self.assertRaises(ValueError):
            validate_asic_policy({"min_strength_non_delegable": "a-phone-call"})

    def test_non_boolean_envelope_switch_rejected(self):
        with self.assertRaises(ValueError):
            validate_asic_policy({"envelope_shortfall_stops": "yes"})


class ObjectiveCatalogueTests(unittest.TestCase):
    def test_default_objective_weights_sum_to_a_round_total(self):
        self.assertEqual(sum(e["weight"] for e in DEFAULT_OBJECTIVES.values()), 100)

    def test_two_objectives_are_held_non_delegable(self):
        flagged = [n for n, e in DEFAULT_OBJECTIVES.items() if e["non_delegable"]]
        self.assertEqual(len(flagged), 2)

    def test_zero_weight_objective_rejected(self):
        with self.assertRaises(ValueError):
            validate_objectives({"a": {"weight": 0}})

    def test_non_integer_weight_rejected(self):
        with self.assertRaises(ValueError):
            validate_objectives({"a": {"weight": 10.0}})

    def test_empty_catalogue_rejected(self):
        with self.assertRaises(ValueError):
            validate_objectives({})


class EvidenceStrengthTests(unittest.TestCase):
    def test_strengths_are_ranked_from_audit_down_to_nothing(self):
        self.assertGreater(
            EVIDENCE_STRENGTHS["independent-audit"]["rank"],
            EVIDENCE_STRENGTHS["supplier-declaration"]["rank"],
        )
        self.assertEqual(EVIDENCE_STRENGTHS["none"]["credit_percent"], 0)

    def test_audit_carries_full_credit(self):
        self.assertEqual(evidence_credit_percent("independent-audit"), 100)

    def test_unknown_strength_rejected(self):
        with self.assertRaises(ValueError):
            evidence_credit_percent("a-conversation")

    def test_non_delegable_objective_on_a_declaration_earns_nothing(self):
        item = credit_objective(
            "functional-verification-coverage",
            {"weight": 25, "non_delegable": True},
            "supplier-declaration",
            "third-party-report",
        )
        self.assertTrue(item["refused"])
        self.assertEqual(item["basis_points"], 0)

    def test_delegable_objective_on_a_declaration_earns_half(self):
        item = credit_objective(
            "design-review-records",
            {"weight": 10, "non_delegable": False},
            "supplier-declaration",
            "third-party-report",
        )
        self.assertFalse(item["refused"])
        self.assertEqual(item["basis_points"], 500)

    def test_credited_totals_use_the_whole_catalogue_weight(self):
        credits = [credit_objective(n, e, "independent-audit", "third-party-report")
                   for n, e in sorted(validate_objectives().items())]
        totals = credited_basis_points(credits, validate_objectives())
        self.assertEqual(totals["credited"], totals["total"])
        self.assertEqual(totals["total"], 10000)


class DeviceValidationTests(unittest.TestCase):
    def test_device_without_reference_rejected(self):
        with self.assertRaises(ValueError):
            validate_device(_device(reference="  "))

    def test_unknown_device_kind_rejected(self):
        with self.assertRaises(ValueError):
            validate_device(_device(kind="analogue-module"))

    def test_device_with_prose_rated_temperature_rejected(self):
        with self.assertRaises(ValueError):
            validate_device(_device(rated_temp_max_c="industrial"))

    def test_inverted_rated_temperature_range_rejected(self):
        with self.assertRaises(ValueError):
            validate_device(_device(rated_temp_min_c=90))

    def test_negative_rated_dose_rejected(self):
        with self.assertRaises(ValueError):
            validate_device(_device(rated_total_dose_krad=-5))

    def test_mission_envelope_needs_integer_bounds(self):
        with self.assertRaises(ValueError):
            validate_mission_envelope(_mission(temp_min_c=None))

    def test_inverted_mission_temperature_range_rejected(self):
        with self.assertRaises(ValueError):
            validate_mission_envelope(_mission(temp_min_c=80, temp_max_c=70))


class RouteTests(unittest.TestCase):
    def test_catalogue_product_is_delegable(self):
        self.assertTrue(route_is_delegable("catalogue-standard-product"))

    def test_full_custom_device_is_not_delegable(self):
        self.assertFalse(route_is_delegable("full-custom"))

    def test_only_two_kinds_are_delegable(self):
        self.assertEqual(len(DELEGABLE_DEVICE_KINDS), 2)

    def test_unknown_kind_rejected_by_the_route_check(self):
        with self.assertRaises(ValueError):
            route_is_delegable("photonic-die")


class EnvelopeTests(unittest.TestCase):
    def test_covered_envelope_opens_no_activity(self):
        self.assertEqual(envelope_shortfalls(_device(), _mission()), [])

    def test_hot_end_overrun_opens_one_activity(self):
        shortfalls = envelope_shortfalls(_device(), _mission(temp_max_c=105))
        self.assertEqual(len(shortfalls), 1)
        self.assertEqual(shortfalls[0]["activity"], "hot-end-application-uprating")

    def test_cold_end_overrun_opens_one_activity(self):
        shortfalls = envelope_shortfalls(_device(), _mission(temp_min_c=-55))
        self.assertEqual(shortfalls[0]["axis"], "temperature-low-end")

    def test_dose_overrun_opens_the_dose_activity(self):
        shortfalls = envelope_shortfalls(_device(), _mission(total_dose_krad=50))
        self.assertEqual(shortfalls[0]["activity"], "application-total-dose-testing")

    def test_each_overrun_axis_opens_its_own_activity(self):
        shortfalls = envelope_shortfalls(
            _device(), _mission(temp_min_c=-55, temp_max_c=105, total_dose_krad=50)
        )
        self.assertEqual(len(shortfalls), 3)


class FloorArithmeticTests(unittest.TestCase):
    def test_credit_exactly_on_the_floor_is_met(self):
        self.assertTrue(assurance_meets_floor(7000, 10000, 70))

    def test_credit_one_point_below_the_floor_is_not_met(self):
        self.assertFalse(assurance_meets_floor(6999, 10000, 70))

    def test_credit_above_the_total_rejected(self):
        with self.assertRaises(ValueError):
            assurance_meets_floor(10001, 10000, 70)

    def test_float_credit_rejected(self):
        with self.assertRaises(ValueError):
            assurance_meets_floor(7000.0, 10000, 70)


class AssessmentTests(unittest.TestCase):
    def test_audited_catalogue_device_is_accepted(self):
        result = assess_delegated_asic_assurance(_case())
        self.assertEqual(result["verdict"], DELEGATED_ASSURANCE_ACCEPTED)
        self.assertTrue(result["accepted"])
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["credited_fraction"], 1.0, places=9)

    def test_full_custom_device_closes_the_route_before_evidence_is_read(self):
        result = assess_delegated_asic_assurance(_case(device=_device(kind="full-custom")))
        self.assertEqual(result["verdict"], DELEGATION_ROUTE_CLOSED)
        self.assertFalse(result["route_delegable"])
        self.assertEqual(result["per_objective"], [])

    def test_non_delegable_objective_on_a_declaration_stops_the_device(self):
        result = assess_delegated_asic_assurance(
            _case(evidence=_evidence(**{"test-vector-fault-coverage": "supplier-declaration"}))
        )
        self.assertEqual(result["verdict"], MANDATORY_OBJECTIVE_UNEVIDENCED)
        self.assertEqual(result["refused_objectives"], ["test-vector-fault-coverage"])
        self.assertIn("test-vector-fault-coverage", result["reopened_activities"])

    def test_refusal_outranks_an_envelope_shortfall(self):
        result = assess_delegated_asic_assurance(
            _case(
                mission=_mission(total_dose_krad=50),
                evidence=_evidence(**{"functional-verification-coverage": "none"}),
            )
        )
        self.assertEqual(result["verdict"], MANDATORY_OBJECTIVE_UNEVIDENCED)

    def test_envelope_shortfall_stops_an_otherwise_audited_device(self):
        result = assess_delegated_asic_assurance(_case(mission=_mission(temp_max_c=105)))
        self.assertEqual(result["verdict"], RATED_ENVELOPE_SHORTFALL)
        self.assertIn("hot-end-application-uprating", result["reopened_activities"])

    def test_envelope_shortfall_can_be_left_as_an_activity_only(self):
        result = assess_delegated_asic_assurance(
            _case(
                mission=_mission(temp_max_c=105),
                policy=_policy(envelope_shortfall_stops=False),
            )
        )
        self.assertEqual(result["verdict"], DELEGATED_ASSURANCE_ACCEPTED)
        self.assertEqual(len(result["envelope_shortfalls"]), 1)

    def test_weak_delegable_evidence_drops_below_the_floor(self):
        result = assess_delegated_asic_assurance(
            _case(evidence=_evidence(**{
                "design-rule-compliance": "none",
                "technology-and-radiation-data": "none",
                "design-review-records": "none",
            }))
        )
        self.assertEqual(result["verdict"], ASSURANCE_BELOW_FLOOR)
        self.assertEqual(result["credited_basis_points"], 5500)

    def test_credit_landing_exactly_on_the_floor_is_accepted(self):
        result = assess_delegated_asic_assurance(
            _case(evidence={
                "functional-verification-coverage": "third-party-report",
                "test-vector-fault-coverage": "independent-audit",
                "design-rule-compliance": "independent-audit",
                "technology-and-radiation-data": "none",
                "design-review-records": "supplier-declaration",
                "configuration-and-change-control": "supplier-declaration",
            })
        )
        self.assertEqual(result["credited_basis_points"], 7000)
        self.assertTrue(result["assurance_meets_floor"])
        self.assertEqual(result["verdict"], DELEGATED_ASSURANCE_ACCEPTED)

    def test_objective_with_no_evidence_defaults_to_nothing(self):
        evidence = _evidence()
        del evidence["design-review-records"]
        result = assess_delegated_asic_assurance(_case(evidence=evidence))
        self.assertEqual(result["credited_basis_points"], 9000)

    def test_evidence_against_an_unknown_objective_rejected(self):
        with self.assertRaises(ValueError):
            assess_delegated_asic_assurance(
                _case(evidence=_evidence(**{"vendor-goodwill": "independent-audit"}))
            )

    def test_missing_mission_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_delegated_asic_assurance({"device": _device(), "evidence": _evidence()})

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_delegated_asic_assurance(["device"])

    def test_non_mapping_evidence_rejected(self):
        with self.assertRaises(ValueError):
            assess_delegated_asic_assurance(_case(evidence=["independent-audit"]))


if __name__ == "__main__":
    unittest.main()
