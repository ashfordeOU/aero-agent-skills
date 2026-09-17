#!/usr/bin/env python3
"""Contract test for the class 2 ASIC referral to the dedicated standard (offline)."""

import copy
import unittest

from q60_class_2_asic_requirements_logic import (
    ALWAYS_REPERFORMED,
    ASIC_CATEGORIES,
    ASSEMBLY_AXES,
    BASE_ACTIVITIES,
    CATEGORY_EXTRA_ACTIVITIES,
    DEFAULT_REFERRAL_POLICY,
    DELTA_DEVELOPMENT,
    DESIGN_AXES,
    FULL_DEVELOPMENT,
    HERITAGE_AXES,
    PROCUREMENT_ORIGINS,
    QUALIFICATION_LAPSED,
    REFERRAL_BLOCKED,
    REQUIRED_REUSE_EVIDENCE,
    REVIEWED_REUSE,
    SILICON_AXES,
    activity_plan,
    assess_asic_referral,
    changed_axes,
    group_changed_axes,
    inheritance_split,
    missing_reuse_evidence,
    qualification_is_current,
    reperform_ratio,
    route_asic_referral,
    validate_build_record,
    validate_case,
    validate_referral_policy,
)

REFERENCED = {
    "foundry": "FAB-ONE",
    "technology_node_nm": 65,
    "mask_set_revision": "M3",
    "process_option": "baseline",
    "design_database_revision": "DB-14",
    "cell_library_revision": "LIB-7",
    "functional_scope": "payload-controller",
    "package_type": "CQFP-208",
    "die_attach_process": "eutectic",
    "lid_seal_process": "seam-weld",
}


def _candidate(**overrides):
    record = copy.deepcopy(REFERENCED)
    record.update(overrides)
    return record


def _case(**overrides):
    case = {
        "part_number": "ASIC-9001",
        "category": "standard-cell",
        "origin": "catalogue-reuse",
        "referenced": copy.deepcopy(REFERENCED),
        "candidate": _candidate(),
        "evidence": list(REQUIRED_REUSE_EVIDENCE),
        "qualification_age_months": 24,
    }
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_is_returned_when_omitted(self):
        self.assertEqual(validate_referral_policy(), DEFAULT_REFERRAL_POLICY)

    def test_policy_override_is_merged(self):
        merged = validate_referral_policy({"qualification_validity_months": 36})
        self.assertEqual(merged["qualification_validity_months"], 36)
        self.assertEqual(
            merged["silicon_movements_forcing_full_development"],
            DEFAULT_REFERRAL_POLICY["silicon_movements_forcing_full_development"],
        )

    def test_unknown_policy_key_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_referral_policy({"grace_period": 4})

    def test_zero_validity_window_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_referral_policy({"qualification_validity_months": 0})

    def test_boolean_threshold_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_referral_policy(
                {"silicon_movements_forcing_full_development": True}
            )


class BuildRecordTests(unittest.TestCase):
    def test_complete_record_validates(self):
        self.assertEqual(
            sorted(validate_build_record("referenced", REFERENCED)),
            sorted(HERITAGE_AXES),
        )

    def test_missing_axis_is_rejected(self):
        record = copy.deepcopy(REFERENCED)
        del record["lid_seal_process"]
        with self.assertRaises(ValueError):
            validate_build_record("referenced", record)

    def test_blank_axis_is_rejected(self):
        record = copy.deepcopy(REFERENCED)
        record["foundry"] = "  "
        with self.assertRaises(ValueError):
            validate_build_record("referenced", record)

    def test_axis_groups_partition_the_heritage_axes(self):
        self.assertEqual(
            len(SILICON_AXES) + len(DESIGN_AXES) + len(ASSEMBLY_AXES),
            len(HERITAGE_AXES),
        )


class MovementTests(unittest.TestCase):
    def test_identical_builds_move_no_axis(self):
        self.assertEqual(changed_axes(REFERENCED, _candidate()), ())

    def test_single_moved_axis_is_reported(self):
        moved = changed_axes(REFERENCED, _candidate(package_type="CQFP-256"))
        self.assertEqual(moved, ("package_type",))

    def test_movements_are_grouped_by_kind(self):
        moved = changed_axes(
            REFERENCED, _candidate(foundry="FAB-TWO", functional_scope="bus-controller")
        )
        grouped = group_changed_axes(moved)
        self.assertEqual(grouped["silicon"], ("foundry",))
        self.assertEqual(grouped["design"], ("functional_scope",))
        self.assertEqual(grouped["assembly"], ())

    def test_unknown_axis_cannot_be_grouped(self):
        with self.assertRaises(ValueError):
            group_changed_axes(("wafer_diameter",))


class ActivityTests(unittest.TestCase):
    def test_every_category_has_an_activity_plan(self):
        for category in ASIC_CATEGORIES:
            self.assertGreaterEqual(len(activity_plan(category)), len(BASE_ACTIVITIES))

    def test_mixed_signal_adds_the_most_activities(self):
        self.assertEqual(
            len(activity_plan("analogue-mixed-signal")) - len(BASE_ACTIVITIES),
            len(CATEGORY_EXTRA_ACTIVITIES["analogue-mixed-signal"]),
        )

    def test_unknown_category_has_no_plan(self):
        with self.assertRaises(ValueError):
            activity_plan("photonic-array")

    def test_unmoved_heritage_inherits_all_but_the_per_order_activities(self):
        split = inheritance_split(
            "standard-cell", {"silicon": (), "design": (), "assembly": ()}
        )
        self.assertEqual(split["reperformed"], ALWAYS_REPERFORMED)
        self.assertEqual(
            len(split["inherited"]), len(split["plan"]) - len(ALWAYS_REPERFORMED)
        )

    def test_assembly_movement_reopens_package_qualification(self):
        split = inheritance_split(
            "standard-cell", {"silicon": (), "design": (), "assembly": ("package_type",)}
        )
        self.assertIn("package-qualification-testing", split["reperformed"])
        self.assertIn("functional-verification-campaign", split["inherited"])

    def test_silicon_movement_reopens_radiation_evaluation(self):
        split = inheritance_split(
            "standard-cell", {"silicon": ("foundry",), "design": (), "assembly": ()}
        )
        self.assertIn("radiation-hardness-evaluation", split["reperformed"])
        self.assertIn("functional-verification-campaign", split["inherited"])

    def test_unknown_movement_group_is_rejected(self):
        with self.assertRaises(ValueError):
            inheritance_split("standard-cell", {"thermal": ("case_temperature",)})

    def test_reperform_ratio_of_an_untouched_plan(self):
        split = inheritance_split(
            "standard-cell", {"silicon": (), "design": (), "assembly": ()}
        )
        self.assertAlmostEqual(
            reperform_ratio(split), len(ALWAYS_REPERFORMED) / len(split["plan"]), places=9
        )

    def test_reperform_ratio_rejects_a_non_split(self):
        with self.assertRaises(ValueError):
            reperform_ratio({"inherited": ()})


class EvidenceTests(unittest.TestCase):
    def test_complete_evidence_leaves_nothing_missing(self):
        self.assertEqual(missing_reuse_evidence(REQUIRED_REUSE_EVIDENCE), ())

    def test_absent_evidence_is_named(self):
        partial = [item for item in REQUIRED_REUSE_EVIDENCE if item != "delta-analysis-note"]
        self.assertEqual(missing_reuse_evidence(partial), ("delta-analysis-note",))

    def test_evidence_of_wrong_type_is_rejected(self):
        with self.assertRaises(ValueError):
            missing_reuse_evidence("delta-analysis-note")

    def test_qualification_inside_the_window_is_current(self):
        self.assertTrue(qualification_is_current(84))

    def test_qualification_past_the_window_is_not_current(self):
        self.assertFalse(qualification_is_current(85))

    def test_negative_age_is_rejected(self):
        with self.assertRaises(ValueError):
            qualification_is_current(-1)


class CaseValidationTests(unittest.TestCase):
    def test_new_development_needs_no_heritage(self):
        validated = validate_case(
            {"part_number": "ASIC-1", "category": "full-custom", "origin": "new-development"}
        )
        self.assertIsNone(validated["referenced"])

    def test_unknown_origin_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_case(_case(origin="borrowed"))

    def test_blank_part_number_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_case(_case(part_number=" "))

    def test_reuse_without_an_age_is_rejected(self):
        case = _case()
        del case["qualification_age_months"]
        with self.assertRaises(ValueError):
            validate_case(case)

    def test_origins_are_the_three_declared_ones(self):
        self.assertEqual(
            PROCUREMENT_ORIGINS, ("new-development", "re-target", "catalogue-reuse")
        )


class RoutingTests(unittest.TestCase):
    def test_new_development_goes_to_the_full_flow(self):
        routing = route_asic_referral(
            {"part_number": "ASIC-1", "category": "gate-array", "origin": "new-development"}
        )
        self.assertEqual(routing["route"], FULL_DEVELOPMENT)

    def test_unmoved_current_heritage_is_a_reviewed_reuse(self):
        self.assertEqual(route_asic_referral(_case())["route"], REVIEWED_REUSE)

    def test_one_moved_axis_is_a_delta(self):
        routing = route_asic_referral(
            _case(candidate=_candidate(package_type="CQFP-256"))
        )
        self.assertEqual(routing["route"], DELTA_DEVELOPMENT)

    def test_two_silicon_movements_force_the_full_flow(self):
        routing = route_asic_referral(
            _case(candidate=_candidate(foundry="FAB-TWO", mask_set_revision="M4"))
        )
        self.assertEqual(routing["route"], FULL_DEVELOPMENT)

    def test_missing_evidence_blocks_the_referral(self):
        routing = route_asic_referral(_case(evidence=["heritage-usage-record"]))
        self.assertEqual(routing["route"], REFERRAL_BLOCKED)
        self.assertIn("delta-analysis-note", routing["missing_evidence"])

    def test_lapsed_qualification_is_a_finding_and_blocks_a_plain_reuse(self):
        routing = route_asic_referral(_case(qualification_age_months=96))
        self.assertIn(QUALIFICATION_LAPSED, routing["findings"])
        self.assertEqual(routing["route"], DELTA_DEVELOPMENT)

    def test_threshold_override_changes_the_full_flow_trigger(self):
        routing = route_asic_referral(
            _case(candidate=_candidate(foundry="FAB-TWO")),
            {"silicon_movements_forcing_full_development": 1},
        )
        self.assertEqual(routing["route"], FULL_DEVELOPMENT)


class AssessmentTests(unittest.TestCase):
    def test_reviewed_reuse_inherits_most_of_the_plan(self):
        result = assess_asic_referral(_case())
        self.assertEqual(result["route"], REVIEWED_REUSE)
        self.assertTrue(result["referred"])
        self.assertEqual(result["reperformed_activities"], ALWAYS_REPERFORMED)

    def test_full_development_inherits_nothing(self):
        result = assess_asic_referral(
            {"part_number": "ASIC-2", "category": "full-custom", "origin": "new-development"}
        )
        self.assertEqual(result["inherited_activities"], ())
        self.assertAlmostEqual(result["reperform_ratio"], 1.0, places=9)

    def test_blocked_referral_inherits_nothing_and_is_not_referred(self):
        result = assess_asic_referral(_case(evidence=[]))
        self.assertEqual(result["route"], REFERRAL_BLOCKED)
        self.assertFalse(result["referred"])
        self.assertAlmostEqual(result["reperform_ratio"], 1.0, places=9)

    def test_delta_reports_the_axes_that_moved(self):
        result = assess_asic_referral(
            _case(candidate=_candidate(die_attach_process="adhesive"))
        )
        self.assertEqual(result["moved_axes"], ("die_attach_process",))
        self.assertIn("package-qualification-testing", result["reperformed_activities"])

    def test_mixed_signal_delta_carries_its_extra_activities(self):
        result = assess_asic_referral(
            _case(
                category="analogue-mixed-signal",
                candidate=_candidate(cell_library_revision="LIB-8"),
            )
        )
        self.assertIn("analogue-block-characterisation", result["reperformed_activities"])
        self.assertIn("mixed-signal-isolation-analysis", result["activity_plan"])

    def test_reperform_ratio_sits_between_zero_and_one(self):
        result = assess_asic_referral(_case())
        self.assertGreater(result["reperform_ratio"], 0.0)
        self.assertLess(result["reperform_ratio"], 1.0)

    def test_case_of_wrong_type_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_asic_referral("ASIC-9001")


if __name__ == "__main__":
    unittest.main(verbosity=0)
