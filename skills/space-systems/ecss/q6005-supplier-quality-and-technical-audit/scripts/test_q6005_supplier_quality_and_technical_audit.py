#!/usr/bin/env python3
"""Contract test for the ECSS-Q-ST-60-05 clause 6.3.3 on-site audit leaf.

Offline, deterministic, stdlib unittest.
Run: python3 test_q6005_supplier_quality_and_technical_audit.py
"""

import unittest

from q6005_supplier_quality_and_technical_audit_logic import (
    AUDIT_AREAS,
    AUDIT_AXES,
    AUDIT_TOLERANCE,
    AXIS_ACCEPTANCE_INDEX,
    BASE_AUDIT_VALIDITY_MONTHS,
    FINDING_SEVERITIES,
    KNOWN_AUDIT_ROLES,
    MANDATORY_AUDIT_AREAS,
    MATURITY_CREDIT,
    MINIMUM_AUDIT_VALIDITY_MONTHS,
    OFF_SITE_EXAMINATION_MODES,
    ON_SITE_EXAMINATION_MODES,
    REQUIRED_AUDIT_ROLES,
    VALIDITY_PENALTY_PER_OPEN_MAJOR_MONTHS,
    VERDICTS,
    area_axis,
    area_weight,
    assess_area,
    assess_supplier_audit,
    audit_validity_months,
    axis_index,
    examination_is_on_site,
    maturity_credit,
    missing_team_roles,
    normalize_area,
    normalize_finding,
    open_finding_counts,
)

SPARE_AREA = "equipment-maintenance-and-capacity"
QUALITY_AREA = "process-control-and-monitoring"
TECHNICAL_AREA = "wire-bond-and-interconnect-capability"


def full_team():
    """An audit team carrying both required roles."""
    return [
        {"name": "auditor-one", "role": "quality-auditor"},
        {"name": "auditor-two", "role": "technology-specialist"},
    ]


def walked_areas(**overrides):
    """Every area walked on site and found established, with named exceptions."""
    areas = []
    for name in sorted(AUDIT_AREAS):
        entry = {
            "area": name,
            "examination": "walked-on-site",
            "maturity": "established-and-effective",
        }
        if name in overrides:
            entry.update(overrides[name])
        areas.append(entry)
    return areas


def run(**overrides):
    """Grade one audit case."""
    case = {
        "supplier_id": "SUP-01",
        "line_id": "LINE-A",
        "team": full_team(),
        "areas": walked_areas(),
        "findings": (),
    }
    case.update(overrides)
    return assess_supplier_audit(**case)


class AuditAreaTests(unittest.TestCase):
    def test_every_area_reports_against_a_published_axis(self):
        for name in AUDIT_AREAS:
            self.assertIn(area_axis(name), AUDIT_AXES)

    def test_every_mandatory_area_is_a_published_area(self):
        for name in MANDATORY_AUDIT_AREAS:
            self.assertIn(name, AUDIT_AREAS)

    def test_both_axes_carry_at_least_one_mandatory_area(self):
        covered = {area_axis(name) for name in MANDATORY_AUDIT_AREAS}
        self.assertEqual(covered, set(AUDIT_AXES))

    def test_an_unknown_area_name_is_rejected(self):
        with self.assertRaises(ValueError):
            area_weight("the-canteen")

    def test_an_unknown_maturity_level_is_rejected(self):
        with self.assertRaises(ValueError):
            maturity_credit("seemed-alright")

    def test_an_area_record_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            normalize_area([QUALITY_AREA, "walked-on-site"])

    def test_an_area_defaults_to_not_examined_when_nobody_named_a_mode(self):
        record = normalize_area({"area": SPARE_AREA})
        self.assertEqual(record["examination"], "not-examined")
        self.assertEqual(record["maturity"], "not-established")


class ExaminationModeTests(unittest.TestCase):
    def test_an_on_site_mode_counts_as_audited(self):
        for mode in ON_SITE_EXAMINATION_MODES:
            self.assertTrue(examination_is_on_site(mode))

    def test_an_off_site_mode_does_not_count_as_audited(self):
        for mode in OFF_SITE_EXAMINATION_MODES:
            self.assertFalse(examination_is_on_site(mode))

    def test_an_unknown_examination_mode_is_an_input_error(self):
        with self.assertRaises(ValueError):
            examination_is_on_site("phoned-them-about-it")

    def test_a_desk_review_earns_no_credit_however_mature_it_claimed_to_be(self):
        record = assess_area(
            {
                "area": SPARE_AREA,
                "examination": "desk-review",
                "maturity": "established-and-effective",
            }
        )
        self.assertAlmostEqual(record["weighted_credit"], 0.0, places=9)
        self.assertIn("area-not-examined-on-site", record["findings"])

    def test_a_desk_review_of_a_mandatory_area_is_an_uncovered_mandatory(self):
        record = assess_area({"area": QUALITY_AREA, "examination": "desk-review"})
        self.assertTrue(record["uncovered_mandatory"])
        self.assertIn("mandatory-area-not-audited-on-site", record["findings"])

    def test_a_desk_review_of_an_optional_area_is_not_an_uncovered_mandatory(self):
        record = assess_area({"area": SPARE_AREA, "examination": "desk-review"})
        self.assertFalse(record["uncovered_mandatory"])

    def test_a_walked_area_found_established_earns_its_full_weight(self):
        record = assess_area(
            {
                "area": TECHNICAL_AREA,
                "examination": "walked-on-site",
                "maturity": "established-and-effective",
            }
        )
        self.assertAlmostEqual(record["weighted_credit"], area_weight(TECHNICAL_AREA), places=9)
        self.assertEqual(record["findings"], [])


class AxisIndexTests(unittest.TestCase):
    def test_a_fully_walked_audit_reaches_a_full_index_on_both_axes(self):
        records = [assess_area(entry) for entry in walked_areas()]
        for axis in AUDIT_AXES:
            self.assertAlmostEqual(axis_index(records, axis), 1.0, places=9)

    def test_an_unknown_axis_is_rejected(self):
        records = [assess_area(entry) for entry in walked_areas()]
        with self.assertRaises(ValueError):
            axis_index(records, "commercial-standing")

    def test_an_axis_with_no_record_carries_no_weight_and_is_rejected(self):
        records = [assess_area({"area": QUALITY_AREA, "examination": "walked-on-site"})]
        with self.assertRaises(ValueError):
            axis_index(records, "technical-capability")

    def test_a_weak_technical_area_moves_only_the_technical_axis(self):
        records = [
            assess_area(entry)
            for entry in walked_areas(**{TECHNICAL_AREA: {"maturity": "not-established"}})
        ]
        self.assertAlmostEqual(axis_index(records, "quality-system"), 1.0, places=9)
        self.assertLess(axis_index(records, "technical-capability"), 1.0 - 1e-6)


class TeamCompositionTests(unittest.TestCase):
    def test_a_full_team_leaves_no_role_missing(self):
        self.assertEqual(missing_team_roles(full_team()), [])

    def test_a_team_without_a_technology_specialist_is_short_that_role(self):
        team = [{"name": "auditor-one", "role": "quality-auditor"}]
        self.assertEqual(missing_team_roles(team), ["technology-specialist"])

    def test_an_observer_does_not_stand_in_for_a_required_role(self):
        team = [{"name": "guest", "role": "observer"}]
        self.assertEqual(missing_team_roles(team), list(REQUIRED_AUDIT_ROLES))

    def test_an_unknown_role_is_rejected(self):
        with self.assertRaises(ValueError):
            missing_team_roles([{"name": "someone", "role": "line-manager"}])

    def test_a_nameless_team_member_is_rejected(self):
        with self.assertRaises(ValueError):
            missing_team_roles([{"name": "  ", "role": "quality-auditor"}])

    def test_every_required_role_is_a_known_role(self):
        for role in REQUIRED_AUDIT_ROLES:
            self.assertIn(role, KNOWN_AUDIT_ROLES)


class FindingTests(unittest.TestCase):
    def test_a_finding_defaults_to_open_when_nobody_recorded_a_closure(self):
        record = normalize_finding({"finding_id": "F-1", "severity": "minor"})
        self.assertFalse(record["closed_before_signature"])

    def test_an_unknown_severity_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_finding({"finding_id": "F-1", "severity": "annoying"})

    def test_a_finding_against_an_unknown_area_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_finding({"finding_id": "F-1", "severity": "minor", "area": "the-car-park"})

    def test_a_repeated_finding_identifier_is_rejected(self):
        findings = [
            {"finding_id": "F-1", "severity": "minor"},
            {"finding_id": "F-1", "severity": "major"},
        ]
        with self.assertRaises(ValueError):
            open_finding_counts(findings)

    def test_a_closed_finding_leaves_the_open_count_alone(self):
        counts = open_finding_counts(
            [{"finding_id": "F-1", "severity": "major", "closed_before_signature": True}]
        )
        self.assertEqual(counts["major"], 0)

    def test_open_findings_are_counted_by_severity(self):
        counts = open_finding_counts(
            [
                {"finding_id": "F-1", "severity": "major"},
                {"finding_id": "F-2", "severity": "major"},
                {"finding_id": "F-3", "severity": "minor"},
            ]
        )
        self.assertEqual(counts["major"], 2)
        self.assertEqual(counts["minor"], 1)
        self.assertEqual(counts["critical"], 0)


class ValidityTermTests(unittest.TestCase):
    def test_an_audit_with_no_open_major_gets_the_full_term(self):
        self.assertAlmostEqual(audit_validity_months(0), BASE_AUDIT_VALIDITY_MONTHS, places=9)

    def test_each_open_major_strikes_its_penalty_off_the_term(self):
        self.assertAlmostEqual(
            audit_validity_months(2),
            BASE_AUDIT_VALIDITY_MONTHS - 2.0 * VALIDITY_PENALTY_PER_OPEN_MAJOR_MONTHS,
            places=9,
        )

    def test_a_term_falling_under_the_floor_is_not_worth_issuing(self):
        too_many = int(BASE_AUDIT_VALIDITY_MONTHS // VALIDITY_PENALTY_PER_OPEN_MAJOR_MONTHS)
        self.assertAlmostEqual(audit_validity_months(too_many), 0.0, places=9)

    def test_a_negative_open_major_count_is_rejected(self):
        with self.assertRaises(ValueError):
            audit_validity_months(-1)


class WholeAuditTests(unittest.TestCase):
    def test_a_fully_walked_audit_supports_the_validation(self):
        result = run()
        self.assertEqual(result["verdict"], "line-supports-category-two-validation")
        self.assertTrue(result["line_supports_validation"])
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["validity_months"], BASE_AUDIT_VALIDITY_MONTHS, places=9)

    def test_every_verdict_returned_is_one_of_the_published_verdicts(self):
        self.assertIn(run()["verdict"], VERDICTS)

    def test_a_team_short_of_a_role_leaves_the_audit_incomplete(self):
        result = run(team=[{"name": "auditor-one", "role": "quality-auditor"}])
        self.assertEqual(result["verdict"], "supplier-audit-incomplete")
        self.assertEqual(result["missing_team_roles"], ["technology-specialist"])

    def test_a_mandatory_area_seen_only_from_a_desk_leaves_the_audit_incomplete(self):
        result = run(areas=walked_areas(**{TECHNICAL_AREA: {"examination": "desk-review"}}))
        self.assertEqual(result["verdict"], "supplier-audit-incomplete")

    def test_a_weak_technical_axis_is_not_masked_by_a_strong_quality_axis(self):
        areas = walked_areas(
            **{
                TECHNICAL_AREA: {"maturity": "not-established"},
                "die-and-substrate-attach-capability": {"maturity": "partly-established"},
            }
        )
        result = run(areas=areas)
        self.assertAlmostEqual(result["axis_indices"]["quality-system"], 1.0, places=9)
        self.assertIn("technical-capability", result["axes_below_threshold"])
        self.assertEqual(result["verdict"], "line-does-not-support-category-two-validation")

    def test_a_weak_quality_axis_is_not_masked_by_a_strong_technical_axis(self):
        areas = walked_areas(
            **{
                QUALITY_AREA: {"maturity": "not-established"},
                "nonconformance-and-corrective-action": {"maturity": "not-established"},
            }
        )
        result = run(areas=areas)
        self.assertAlmostEqual(result["axis_indices"]["technical-capability"], 1.0, places=9)
        self.assertIn("quality-system", result["axes_below_threshold"])
        self.assertEqual(result["verdict"], "line-does-not-support-category-two-validation")

    def test_an_open_critical_finding_denies_the_line_on_a_complete_audit(self):
        result = run(findings=[{"finding_id": "F-1", "severity": "critical"}])
        self.assertEqual(result["verdict"], "line-does-not-support-category-two-validation")

    def test_a_closed_critical_finding_leaves_the_line_supported(self):
        result = run(
            findings=[
                {"finding_id": "F-1", "severity": "critical", "closed_before_signature": True}
            ]
        )
        self.assertEqual(result["verdict"], "line-supports-category-two-validation")

    def test_an_open_minor_finding_leaves_the_line_supported_with_open_actions(self):
        result = run(findings=[{"finding_id": "F-1", "severity": "minor", "area": SPARE_AREA}])
        self.assertEqual(result["verdict"], "line-supports-validation-with-open-actions")
        self.assertTrue(result["line_supports_validation"])

    def test_an_open_major_shortens_the_validity_term(self):
        result = run(findings=[{"finding_id": "F-1", "severity": "major"}])
        self.assertAlmostEqual(
            result["validity_months"],
            BASE_AUDIT_VALIDITY_MONTHS - VALIDITY_PENALTY_PER_OPEN_MAJOR_MONTHS,
            places=9,
        )

    def test_enough_open_majors_exhaust_the_term_and_deny_the_line(self):
        findings = [
            {"finding_id": "F-%d" % (i,), "severity": "major"}
            for i in range(int(BASE_AUDIT_VALIDITY_MONTHS // VALIDITY_PENALTY_PER_OPEN_MAJOR_MONTHS))
        ]
        result = run(findings=findings)
        self.assertAlmostEqual(result["validity_months"], 0.0, places=9)
        self.assertEqual(result["verdict"], "line-does-not-support-category-two-validation")

    def test_an_area_nobody_mentioned_is_graded_as_not_examined(self):
        result = run(areas=[{"area": SPARE_AREA, "examination": "walked-on-site"}])
        modes = {r["area"]: r["examination"] for r in result["area_records"]}
        self.assertEqual(modes[QUALITY_AREA], "not-examined")
        self.assertEqual(len(result["area_records"]), len(AUDIT_AREAS))

    def test_a_repeated_audit_area_is_rejected(self):
        areas = walked_areas() + [{"area": SPARE_AREA, "examination": "walked-on-site"}]
        with self.assertRaises(ValueError):
            run(areas=areas)

    def test_a_blank_line_identifier_is_rejected(self):
        with self.assertRaises(ValueError):
            run(line_id="   ")

    def test_a_non_sequence_area_argument_is_rejected(self):
        with self.assertRaises(ValueError):
            run(areas={"area": SPARE_AREA})


class ConstantsTests(unittest.TestCase):
    def test_the_tolerance_is_small_enough_to_separate_the_bounds(self):
        self.assertLess(AUDIT_TOLERANCE, 1e-6)

    def test_the_maturity_credits_span_the_published_scale(self):
        self.assertAlmostEqual(max(MATURITY_CREDIT.values()), 1.0, places=9)
        self.assertAlmostEqual(min(MATURITY_CREDIT.values()), 0.0, places=9)

    def test_each_axis_carries_its_own_acceptance_threshold(self):
        self.assertEqual(set(AXIS_ACCEPTANCE_INDEX), set(AUDIT_AXES))
        for axis in AUDIT_AXES:
            self.assertLess(AXIS_ACCEPTANCE_INDEX[axis], 1.0)

    def test_the_severities_are_ordered_from_worst_to_least(self):
        self.assertEqual(FINDING_SEVERITIES[0], "critical")
        self.assertEqual(FINDING_SEVERITIES[-1], "minor")

    def test_the_validity_floor_sits_under_the_full_term(self):
        self.assertLess(MINIMUM_AUDIT_VALIDITY_MONTHS, BASE_AUDIT_VALIDITY_MONTHS)


if __name__ == "__main__":
    unittest.main()
