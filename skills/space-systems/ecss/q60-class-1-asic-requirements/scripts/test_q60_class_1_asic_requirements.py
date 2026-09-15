"""Contract tests for the clause 4.6.2 class 1 ASIC routing decision.

Every workflow step the SKILL.md sets out is exercised here, together with the
stop conditions the gate 3 contract reviews: a heritage record missing an axis,
a reuse claim with no evidence reference, a silicon or design change that
voids the heritage, an assembly-only change, a lapsed qualification and a break
in production.
"""

import unittest

from q60_class_1_asic_requirements_logic import (
    ACTIVITY_SETS,
    ASSEMBLY_AXES,
    DEFAULT_ROUTING_POLICY,
    DELTA_QUALIFICATION,
    DESIGN_AXES,
    FULL_DEVELOPMENT,
    HERITAGE_AXES,
    HERITAGE_EVIDENCE_INCOMPLETE,
    REQUIRED_REUSE_EVIDENCE,
    REUSE_ROUTE,
    SILICON_AXES,
    activity_set_for_route,
    changed_axes,
    group_changed_axes,
    heritage_delta_index,
    missing_reuse_evidence,
    qualification_is_current,
    route_asic_requirements,
    validate_case,
    validate_heritage,
    validate_routing_policy,
)


def _heritage(**overrides):
    record = {
        "foundry": "foundry-north",
        "process_node_nm": 65,
        "mask_set_revision": "m-04",
        "design_database_version": "db-2.7",
        "functional_scope": "payload-controller",
        "package_type": "cqfp-256",
        "die_attach_process": "eutectic",
    }
    record.update(overrides)
    return record


def _evidence(**overrides):
    record = {name: "ref-%s" % name for name in REQUIRED_REUSE_EVIDENCE}
    record.update(overrides)
    return record


def _policy(**overrides):
    policy = dict(DEFAULT_ROUTING_POLICY)
    policy.update(overrides)
    return policy


def _case(**overrides):
    case = {
        "part_id": "asic-7741",
        "declared_route": "reuse",
        "candidate": _heritage(),
        "qualified": _heritage(),
        "evidence": _evidence(),
        "qualification_age_months": 18,
        "production_break": False,
    }
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        settings = validate_routing_policy(None)
        self.assertEqual(settings["max_qualification_age_months"], 60)
        self.assertTrue(settings["production_break_forces_delta"])

    def test_unknown_policy_key_rejected(self):
        with self.assertRaises(ValueError):
            validate_routing_policy({"max_age_years": 5})

    def test_non_integer_validity_rejected(self):
        with self.assertRaises(ValueError):
            validate_routing_policy({"max_qualification_age_months": 60.0})

    def test_non_boolean_flag_rejected(self):
        with self.assertRaises(ValueError):
            validate_routing_policy({"assembly_change_stays_on_reuse": "yes"})


class HeritageValidationTests(unittest.TestCase):
    def test_every_axis_survives_validation(self):
        record = validate_heritage(_heritage(), "candidate")
        self.assertEqual(sorted(record), sorted(HERITAGE_AXES))

    def test_missing_axis_stops_the_routing(self):
        broken = _heritage()
        del broken["mask_set_revision"]
        with self.assertRaises(ValueError):
            validate_heritage(broken, "candidate")

    def test_blank_axis_stops_the_routing(self):
        with self.assertRaises(ValueError):
            validate_heritage(_heritage(foundry="   "), "candidate")

    def test_unknown_axis_rejected(self):
        with self.assertRaises(ValueError):
            validate_heritage(_heritage(wafer_diameter="200mm"), "candidate")

    def test_non_positive_numeric_axis_rejected(self):
        with self.assertRaises(ValueError):
            validate_heritage(_heritage(process_node_nm=0), "candidate")

    def test_axis_groups_do_not_overlap(self):
        self.assertEqual(
            len(set(SILICON_AXES) | set(DESIGN_AXES) | set(ASSEMBLY_AXES)),
            len(HERITAGE_AXES),
        )


class CaseValidationTests(unittest.TestCase):
    def test_declared_route_is_checked(self):
        with self.assertRaises(ValueError):
            validate_case(_case(declared_route="second-source"))

    def test_reuse_without_a_qualified_heritage_rejected(self):
        case = _case()
        del case["qualified"]
        with self.assertRaises(ValueError):
            validate_case(case)

    def test_new_development_needs_no_qualified_heritage(self):
        record = validate_case({
            "part_id": "asic-new",
            "declared_route": "new-development",
        })
        self.assertIsNone(record["qualified"])

    def test_blank_evidence_reference_rejected(self):
        with self.assertRaises(ValueError):
            validate_case(_case(evidence={"qualification_report": "  "}))

    def test_negative_qualification_age_rejected(self):
        with self.assertRaises(ValueError):
            validate_case(_case(qualification_age_months=-1))

    def test_non_boolean_production_break_rejected(self):
        with self.assertRaises(ValueError):
            validate_case(_case(production_break="no"))


class DeltaTests(unittest.TestCase):
    def test_identical_heritage_moves_no_axis(self):
        self.assertEqual(changed_axes(_heritage(), _heritage()), [])

    def test_a_foundry_change_is_a_silicon_change(self):
        moved = changed_axes(_heritage(foundry="foundry-south"), _heritage())
        self.assertEqual(group_changed_axes(moved)["silicon"], ["foundry"])

    def test_a_package_change_is_an_assembly_change(self):
        moved = changed_axes(_heritage(package_type="cqfp-352"), _heritage())
        self.assertEqual(group_changed_axes(moved)["assembly"], ["package_type"])

    def test_a_database_change_is_a_design_change(self):
        moved = changed_axes(_heritage(design_database_version="db-3.0"), _heritage())
        self.assertEqual(group_changed_axes(moved)["design"], ["design_database_version"])

    def test_unknown_axis_in_a_group_call_rejected(self):
        with self.assertRaises(ValueError):
            group_changed_axes(["wafer_diameter"])

    def test_delta_index_of_an_unchanged_build(self):
        self.assertAlmostEqual(heritage_delta_index([]), 0.0, places=9)

    def test_delta_index_of_a_wholly_changed_build(self):
        self.assertAlmostEqual(heritage_delta_index(list(HERITAGE_AXES)), 1.0, places=9)

    def test_delta_index_counts_each_axis_once(self):
        self.assertAlmostEqual(
            heritage_delta_index(["foundry", "foundry"]),
            1.0 / float(len(HERITAGE_AXES)),
            places=9,
        )


class EvidenceAndCurrencyTests(unittest.TestCase):
    def test_a_complete_evidence_set_leaves_nothing_missing(self):
        self.assertEqual(missing_reuse_evidence(_evidence()), [])

    def test_a_missing_reference_is_named(self):
        evidence = _evidence()
        del evidence["radiation_evaluation"]
        self.assertEqual(missing_reuse_evidence(evidence), ["radiation_evaluation"])

    def test_non_mapping_evidence_rejected(self):
        with self.assertRaises(ValueError):
            missing_reuse_evidence(["qualification_report"])

    def test_qualification_on_its_validity_bound_is_still_current(self):
        self.assertTrue(qualification_is_current(60))

    def test_qualification_past_its_validity_is_not_current(self):
        self.assertFalse(qualification_is_current(61))

    def test_negative_age_rejected(self):
        with self.assertRaises(ValueError):
            qualification_is_current(-2)

    def test_activity_set_is_known_for_every_route(self):
        for route in ACTIVITY_SETS:
            self.assertIsInstance(activity_set_for_route(route), list)

    def test_unknown_route_has_no_activity_set(self):
        with self.assertRaises(ValueError):
            activity_set_for_route("second-source-route")


class RoutingTests(unittest.TestCase):
    def test_an_unchanged_current_build_takes_the_reuse_route(self):
        result = route_asic_requirements(_case())
        self.assertEqual(result["route"], REUSE_ROUTE)
        self.assertTrue(result["referred_to_dedicated_standard"])
        self.assertEqual(result["findings"], [])

    def test_a_new_development_takes_the_full_flow(self):
        result = route_asic_requirements({
            "part_id": "asic-new",
            "declared_route": "new-development",
        })
        self.assertEqual(result["route"], FULL_DEVELOPMENT)
        self.assertIn("prototype-validation", result["required_activities"])

    def test_a_silicon_change_takes_the_full_flow(self):
        result = route_asic_requirements(
            _case(candidate=_heritage(process_node_nm=45), declared_route="re-target")
        )
        self.assertEqual(result["route"], FULL_DEVELOPMENT)
        self.assertEqual(result["changed_axis_groups"]["silicon"], ["process_node_nm"])

    def test_a_design_change_takes_the_full_flow(self):
        result = route_asic_requirements(
            _case(candidate=_heritage(functional_scope="payload-controller-rev-b"))
        )
        self.assertEqual(result["route"], FULL_DEVELOPMENT)

    def test_an_assembly_change_takes_the_delta_route(self):
        result = route_asic_requirements(
            _case(candidate=_heritage(package_type="cqfp-352"))
        )
        self.assertEqual(result["route"], DELTA_QUALIFICATION)
        self.assertIn("delta-qualification-testing", result["required_activities"])

    def test_an_assembly_change_can_stay_on_reuse_by_policy(self):
        result = route_asic_requirements(
            _case(candidate=_heritage(die_attach_process="adhesive"),
                  policy=_policy(assembly_change_stays_on_reuse=True))
        )
        self.assertEqual(result["route"], REUSE_ROUTE)

    def test_a_lapsed_qualification_takes_the_delta_route(self):
        result = route_asic_requirements(_case(qualification_age_months=72))
        self.assertEqual(result["route"], DELTA_QUALIFICATION)
        self.assertFalse(result["qualification_current"])

    def test_a_production_break_takes_the_delta_route(self):
        result = route_asic_requirements(_case(production_break=True))
        self.assertEqual(result["route"], DELTA_QUALIFICATION)

    def test_a_production_break_can_be_waived_by_policy(self):
        result = route_asic_requirements(
            _case(production_break=True,
                  policy=_policy(production_break_forces_delta=False))
        )
        self.assertEqual(result["route"], REUSE_ROUTE)

    def test_missing_evidence_stops_the_referral(self):
        evidence = _evidence()
        del evidence["lot_acceptance_data"]
        result = route_asic_requirements(_case(evidence=evidence))
        self.assertEqual(result["route"], HERITAGE_EVIDENCE_INCOMPLETE)
        self.assertFalse(result["referred_to_dedicated_standard"])
        self.assertEqual(result["required_activities"], [])

    def test_missing_evidence_outranks_a_silicon_change(self):
        result = route_asic_requirements(
            _case(candidate=_heritage(foundry="foundry-south"), evidence={})
        )
        self.assertEqual(result["route"], HERITAGE_EVIDENCE_INCOMPLETE)

    def test_the_delta_index_travels_with_the_route(self):
        result = route_asic_requirements(
            _case(candidate=_heritage(package_type="cqfp-352"))
        )
        self.assertAlmostEqual(
            result["heritage_delta_index"], 1.0 / float(len(HERITAGE_AXES)), places=9
        )

    def test_non_mapping_case_refused(self):
        with self.assertRaises(ValueError):
            route_asic_requirements(["asic-7741"])


if __name__ == "__main__":
    unittest.main()
