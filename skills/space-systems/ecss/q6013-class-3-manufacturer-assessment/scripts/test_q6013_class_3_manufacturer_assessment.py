"""Contract test for the ECSS-Q-ST-60-13C clause 6.2.3.2 manufacturer leaf.

Offline, deterministic, stdlib unittest.
Run: python3 test_q6013_class_3_manufacturer_assessment.py
"""

import unittest

from q6013_class_3_manufacturer_assessment_logic import (
    AGE_TOLERANCE,
    CAPABILITY_CONTROLS,
    CLASS_3_CAPABILITY_FLOOR,
    CORE_CONTROLS,
    EVIDENCE_LEVEL_CEILING,
    MATURITY_LEVELS,
    SURVEILLANCE_BASE_MONTHS,
    SURVEILLANCE_FLOOR_MONTHS,
    SURVEILLANCE_SHORTENING_MONTHS,
    VERDICTS,
    assess_control,
    assess_manufacturer,
    control_is_known,
    credited_level,
    evidence_ceiling,
    evidence_within_interval,
    governing_control,
    maturity_level,
    normalize_control,
    surveillance_interval_months,
)


def audited_submission(**overrides):
    """Every control documented and audited on site, with named exceptions."""
    controls = []
    for name in CAPABILITY_CONTROLS:
        entry = {
            "control": name,
            "maturity": "control-documented-and-audited",
            "evidence_basis": "on-site-audit",
        }
        if name in overrides:
            entry.update(overrides[name])
        controls.append(entry)
    return controls


class ControlSetTests(unittest.TestCase):
    def test_every_core_control_is_part_of_the_control_set(self):
        for name in CORE_CONTROLS:
            self.assertIn(name, CAPABILITY_CONTROLS)

    def test_the_core_group_is_smaller_than_the_control_set(self):
        self.assertLess(len(CORE_CONTROLS), len(CAPABILITY_CONTROLS))

    def test_unknown_control_rejected(self):
        with self.assertRaises(ValueError):
            control_is_known("vibes-management-system")


class LevelLadderTests(unittest.TestCase):
    def test_an_absent_control_sits_at_the_bottom_of_the_ladder(self):
        self.assertEqual(maturity_level("control-absent"), 0)

    def test_the_ladder_rises_from_informal_to_audited(self):
        self.assertLess(
            maturity_level("control-informal"),
            maturity_level("control-documented"),
        )
        self.assertLess(
            maturity_level("control-documented"),
            maturity_level("control-documented-and-audited"),
        )

    def test_unknown_maturity_rejected(self):
        with self.assertRaises(ValueError):
            maturity_level("they-seemed-organised")

    def test_no_evidence_supports_no_level_at_all(self):
        self.assertEqual(evidence_ceiling("no-evidence"), 0)

    def test_a_catalogue_statement_cannot_support_a_documented_control(self):
        self.assertLess(evidence_ceiling("catalogue-statement"), CLASS_3_CAPABILITY_FLOOR)

    def test_a_questionnaire_cannot_support_an_audited_control(self):
        self.assertLess(
            evidence_ceiling("self-declared-questionnaire"),
            maturity_level("control-documented-and-audited"),
        )

    def test_every_ceiling_sits_inside_the_level_ladder(self):
        top = max(MATURITY_LEVELS.values())
        for ceiling in EVIDENCE_LEVEL_CEILING.values():
            self.assertGreaterEqual(ceiling, 0)
            self.assertLessEqual(ceiling, top)

    def test_unknown_evidence_basis_rejected(self):
        with self.assertRaises(ValueError):
            evidence_ceiling("a-friend-vouched")

    def test_credit_is_the_lower_of_the_claim_and_its_evidence(self):
        self.assertEqual(
            credited_level("control-documented-and-audited", "catalogue-statement"), 1
        )
        self.assertEqual(
            credited_level("control-informal", "on-site-audit"), 1
        )


class NormaliseControlTests(unittest.TestCase):
    def test_an_unmentioned_control_defaults_to_absent_and_unevidenced(self):
        entry = normalize_control({"control": "discontinuance-notice"})
        self.assertEqual(entry["maturity"], "control-absent")
        self.assertEqual(entry["evidence_basis"], "no-evidence")

    def test_non_mapping_control_rejected(self):
        with self.assertRaises(ValueError):
            normalize_control("discontinuance-notice")


class AssessControlTests(unittest.TestCase):
    def test_an_audited_control_is_credited_in_full_with_no_finding(self):
        record = assess_control(
            {
                "control": "quality-management-system",
                "maturity": "control-documented-and-audited",
                "evidence_basis": "on-site-audit",
            }
        )
        self.assertEqual(record["credited_level"], 3)
        self.assertEqual(record["findings"], [])

    def test_a_claim_above_its_evidence_is_capped_and_the_cap_is_reported(self):
        record = assess_control(
            {
                "control": "failure-analysis-response",
                "maturity": "control-documented-and-audited",
                "evidence_basis": "self-declared-questionnaire",
            }
        )
        self.assertEqual(record["credited_level"], 2)
        self.assertIn("control-level-capped-by-evidence", record["findings"])

    def test_a_core_control_under_the_floor_is_named_as_core(self):
        record = assess_control(
            {
                "control": "date-code-lot-traceability",
                "maturity": "control-documented",
                "evidence_basis": "catalogue-statement",
            }
        )
        self.assertTrue(record["core"])
        self.assertIn("core-control-below-class-3-floor", record["findings"])

    def test_a_supporting_control_under_the_floor_is_named_as_supporting(self):
        record = assess_control(
            {
                "control": "discontinuance-notice",
                "maturity": "control-absent",
                "evidence_basis": "no-evidence",
            }
        )
        self.assertFalse(record["core"])
        self.assertIn("supporting-control-below-class-3-floor", record["findings"])


class GoverningControlTests(unittest.TestCase):
    def test_the_weakest_core_control_fixes_the_capability_level(self):
        records = [
            assess_control(
                {
                    "control": "quality-management-system",
                    "maturity": "control-documented-and-audited",
                    "evidence_basis": "on-site-audit",
                }
            ),
            assess_control(
                {
                    "control": "process-change-notification",
                    "maturity": "control-informal",
                    "evidence_basis": "on-site-audit",
                }
            ),
            assess_control(
                {
                    "control": "date-code-lot-traceability",
                    "maturity": "control-documented",
                    "evidence_basis": "remote-audit",
                }
            ),
        ]
        self.assertEqual(
            governing_control(records), ("process-change-notification", 1)
        )

    def test_governing_control_rejects_a_set_with_no_core_control(self):
        records = [
            assess_control(
                {
                    "control": "discontinuance-notice",
                    "maturity": "control-documented",
                    "evidence_basis": "remote-audit",
                }
            )
        ]
        with self.assertRaises(ValueError):
            governing_control(records)

    def test_governing_control_rejects_a_non_sequence(self):
        with self.assertRaises(ValueError):
            governing_control({"control": "quality-management-system"})


class SurveillanceIntervalTests(unittest.TestCase):
    def test_a_top_level_manufacturer_with_no_shortfall_waits_the_base_interval(self):
        self.assertEqual(
            surveillance_interval_months(3, 0), SURVEILLANCE_BASE_MONTHS[3]
        )

    def test_each_supporting_shortfall_pulls_the_visit_forward(self):
        self.assertEqual(
            surveillance_interval_months(3, 2),
            SURVEILLANCE_BASE_MONTHS[3] - 2 * SURVEILLANCE_SHORTENING_MONTHS,
        )

    def test_the_interval_never_falls_through_its_floor(self):
        self.assertEqual(
            surveillance_interval_months(0, 3), SURVEILLANCE_FLOOR_MONTHS
        )

    def test_a_level_outside_the_ladder_rejected(self):
        with self.assertRaises(ValueError):
            surveillance_interval_months(7, 0)

    def test_a_negative_shortfall_count_rejected(self):
        with self.assertRaises(ValueError):
            surveillance_interval_months(3, -1)

    def test_evidence_landing_on_the_interval_is_still_inside_it(self):
        self.assertTrue(evidence_within_interval(24.0, 24))

    def test_evidence_past_the_interval_falls_outside(self):
        self.assertFalse(evidence_within_interval(24.0 + 1.0, 24))

    def test_negative_evidence_age_rejected(self):
        with self.assertRaises(ValueError):
            evidence_within_interval(-1.0, 24)

    def test_non_numeric_evidence_age_rejected(self):
        with self.assertRaises(ValueError):
            evidence_within_interval("last spring", 24)


class ManufacturerVerdictTests(unittest.TestCase):
    def test_a_fully_audited_manufacturer_is_accepted_outright(self):
        report = assess_manufacturer("cots-foundry-a", audited_submission(), 6.0)
        self.assertEqual(report["verdict"], "class-3-manufacturer-accepted")
        self.assertEqual(report["capability_level"], 3)
        self.assertEqual(report["findings"], [])
        self.assertTrue(report["meets_class_3_floor"])

    def test_a_supporting_shortfall_leaves_actions_and_shortens_the_interval(self):
        report = assess_manufacturer(
            "cots-foundry-a",
            audited_submission(
                **{
                    "discontinuance-notice": {
                        "maturity": "control-absent",
                        "evidence_basis": "no-evidence",
                    }
                }
            ),
            6.0,
        )
        self.assertEqual(
            report["verdict"], "class-3-manufacturer-accepted-with-actions"
        )
        self.assertEqual(report["supporting_shortfalls"], ["discontinuance-notice"])
        self.assertEqual(
            report["surveillance_interval_months"],
            SURVEILLANCE_BASE_MONTHS[3] - SURVEILLANCE_SHORTENING_MONTHS,
        )

    def test_a_weak_core_control_sinks_an_otherwise_strong_submission(self):
        report = assess_manufacturer(
            "cots-foundry-a",
            audited_submission(
                **{
                    "date-code-lot-traceability": {
                        "maturity": "control-documented",
                        "evidence_basis": "catalogue-statement",
                    }
                }
            ),
            6.0,
        )
        self.assertEqual(report["verdict"], "class-3-manufacturer-rejected")
        self.assertEqual(report["governing_control"], "date-code-lot-traceability")
        self.assertFalse(report["meets_class_3_floor"])

    def test_overdue_evidence_turns_an_acceptance_into_actions(self):
        report = assess_manufacturer(
            "cots-foundry-a",
            audited_submission(),
            float(SURVEILLANCE_BASE_MONTHS[3]) + 1.0,
        )
        self.assertEqual(
            report["verdict"], "class-3-manufacturer-accepted-with-actions"
        )
        self.assertFalse(report["evidence_within_interval"])
        self.assertIn(
            {"control": "assessment", "finding": "surveillance-evidence-overdue"},
            report["findings"],
        )

    def test_an_unmentioned_control_is_graded_as_absent(self):
        report = assess_manufacturer("cots-foundry-a", [], 0.0)
        self.assertEqual(len(report["records"]), len(CAPABILITY_CONTROLS))
        self.assertEqual(report["capability_level"], 0)
        self.assertEqual(report["verdict"], "class-3-manufacturer-rejected")

    def test_every_verdict_name_is_one_the_module_publishes(self):
        seen = set()
        seen.add(assess_manufacturer("m", audited_submission(), 0.0)["verdict"])
        seen.add(assess_manufacturer("m", [], 0.0)["verdict"])
        seen.add(
            assess_manufacturer(
                "m",
                audited_submission(
                    **{
                        "discontinuance-notice": {
                            "maturity": "control-absent",
                            "evidence_basis": "no-evidence",
                        }
                    }
                ),
                0.0,
            )["verdict"]
        )
        self.assertEqual(seen, set(VERDICTS))

    def test_duplicate_control_declaration_rejected(self):
        with self.assertRaises(ValueError):
            assess_manufacturer(
                "cots-foundry-a",
                [
                    {"control": "quality-management-system"},
                    {"control": "quality-management-system"},
                ],
                0.0,
            )

    def test_blank_manufacturer_identifier_rejected(self):
        with self.assertRaises(ValueError):
            assess_manufacturer("   ", audited_submission(), 0.0)

    def test_non_sequence_control_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_manufacturer(
                "cots-foundry-a", {"control": "quality-management-system"}, 0.0
            )

    def test_tolerance_is_small_enough_to_leave_the_interval_meaningful(self):
        self.assertGreater(AGE_TOLERANCE, 0.0)
        self.assertLess(AGE_TOLERANCE, 1e-6)


if __name__ == "__main__":
    unittest.main()
