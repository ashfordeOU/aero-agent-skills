#!/usr/bin/env python3
"""Gate 3 contract test for e2007-emc-general-system-requirements.

Stdlib unittest, offline, deterministic.
"""

import unittest

import e2007_emc_general_system_requirements_logic as logic


def element(kind, state="baselined", milestone="pdr", owner="emc-lead", ident=None):
    return {
        "id": ident or ("doc-" + kind),
        "kind": kind,
        "state": state,
        "owner": owner,
        "milestone": milestone,
    }


def full_element_set():
    return [
        element("emc-control-plan", milestone="pdr"),
        element("grounding-and-bonding-policy", milestone="pdr"),
        element("electromagnetic-effects-verification-plan", milestone="cdr"),
        element("magnetic-cleanliness-policy", milestone="cdr"),
        element("charging-protection-programme", milestone="cdr"),
        element("radiation-hazard-policy", milestone="qr"),
    ]


class TestElementNormalization(unittest.TestCase):
    def test_normalize_element_happy_path(self):
        got = logic.normalize_element(element("emc-control-plan"))
        self.assertEqual(got["kind"], "emc-control-plan")
        self.assertEqual(got["owner"], "emc-lead")
        self.assertTrue(got["on_record"])

    def test_normalize_element_uppercase_kind_is_folded(self):
        got = logic.normalize_element(element("EMC-CONTROL-PLAN"))
        self.assertEqual(got["kind"], "emc-control-plan")

    def test_normalize_element_rejects_non_mapping(self):
        with self.assertRaises(ValueError):
            logic.normalize_element(["emc-control-plan"])

    def test_normalize_element_rejects_blank_id(self):
        rec = element("emc-control-plan")
        rec["id"] = "   "
        with self.assertRaises(ValueError):
            logic.normalize_element(rec)

    def test_normalize_element_rejects_unknown_kind(self):
        with self.assertRaises(ValueError):
            logic.normalize_element(element("thermal-control-plan"))

    def test_normalize_element_rejects_unknown_state(self):
        with self.assertRaises(ValueError):
            logic.normalize_element(element("emc-control-plan", state="signed"))

    def test_normalize_element_rejects_blank_owner(self):
        with self.assertRaises(ValueError):
            logic.normalize_element(element("emc-control-plan", owner=""))

    def test_normalize_element_rejects_unknown_milestone(self):
        with self.assertRaises(ValueError):
            logic.normalize_element(element("emc-control-plan", milestone="frr"))

    def test_draft_element_is_not_on_record(self):
        got = logic.normalize_element(element("emc-control-plan", state="draft"))
        self.assertFalse(got["on_record"])

    def test_withdrawn_element_is_not_on_record(self):
        got = logic.normalize_element(element("emc-control-plan", state="withdrawn"))
        self.assertFalse(got["on_record"])

    def test_released_element_is_on_record(self):
        got = logic.normalize_element(element("emc-control-plan", state="released"))
        self.assertTrue(got["on_record"])

    def test_normalize_elements_rejects_duplicate_kind(self):
        recs = [element("emc-control-plan"), element("emc-control-plan", ident="dup")]
        with self.assertRaises(ValueError):
            logic.normalize_elements(recs)

    def test_normalize_elements_rejects_non_sequence(self):
        with self.assertRaises(ValueError):
            logic.normalize_elements({"kind": "emc-control-plan"})

    def test_normalize_elements_returns_every_record(self):
        self.assertEqual(len(logic.normalize_elements(full_element_set())), 6)


class TestCoverage(unittest.TestCase):
    def test_no_missing_elements_for_full_set(self):
        elements = logic.normalize_elements(full_element_set())
        self.assertEqual(logic.missing_mandatory_elements(elements), ())

    def test_missing_elements_are_reported(self):
        recs = full_element_set()[:-2]
        elements = logic.normalize_elements(recs)
        missing = logic.missing_mandatory_elements(elements)
        self.assertIn("radiation-hazard-policy", missing)
        self.assertIn("charging-protection-programme", missing)

    def test_draft_mandatory_element_is_unapproved_not_missing(self):
        recs = full_element_set()
        recs[0]["state"] = "draft"
        elements = logic.normalize_elements(recs)
        self.assertEqual(logic.missing_mandatory_elements(elements), ())
        self.assertEqual(
            logic.unapproved_mandatory_elements(elements), ("emc-control-plan",)
        )

    def test_draft_optional_element_is_not_a_finding(self):
        recs = full_element_set()
        recs.append(element("lightning-protection-policy", state="draft"))
        elements = logic.normalize_elements(recs)
        self.assertEqual(logic.unapproved_mandatory_elements(elements), ())

    def test_coverage_ratio_is_one_for_full_set(self):
        elements = logic.normalize_elements(full_element_set())
        self.assertAlmostEqual(logic.policy_coverage_ratio(elements), 1.0, places=12)

    def test_coverage_ratio_for_partial_set(self):
        elements = logic.normalize_elements(full_element_set()[:3])
        self.assertAlmostEqual(logic.policy_coverage_ratio(elements), 0.5, places=12)

    def test_coverage_ratio_ignores_draft_elements(self):
        recs = full_element_set()
        recs[0]["state"] = "draft"
        elements = logic.normalize_elements(recs)
        self.assertAlmostEqual(
            logic.policy_coverage_ratio(elements), 5.0 / 6.0, places=12
        )

    def test_coverage_meets_target_when_exactly_equal(self):
        self.assertTrue(logic.coverage_meets_target(1.0, 1.0))

    def test_coverage_meets_target_absorbs_last_place_error(self):
        target = 5.0 / 6.0
        ratio = target - 5e-16
        self.assertLess(ratio, target)
        self.assertTrue(logic.coverage_meets_target(ratio, target))

    def test_coverage_below_target_is_rejected(self):
        self.assertFalse(logic.coverage_meets_target(0.5, 5.0 / 6.0))

    def test_coverage_target_above_one_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.coverage_meets_target(1.0, 1.5)

    def test_coverage_target_must_be_numeric(self):
        with self.assertRaises(ValueError):
            logic.coverage_meets_target(1.0, "all")

    def test_negative_tolerance_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.coverage_meets_target(1.0, 1.0, tolerance=-1e-9)


class TestMilestones(unittest.TestCase):
    def test_milestone_index_follows_review_sequence(self):
        self.assertLess(logic.milestone_index("pdr"), logic.milestone_index("cdr"))
        self.assertLess(logic.milestone_index("cdr"), logic.milestone_index("ar"))

    def test_milestone_index_rejects_unknown_review(self):
        with self.assertRaises(ValueError):
            logic.milestone_index("orr")

    def test_late_baseline_is_flagged(self):
        recs = full_element_set()
        recs[0]["milestone"] = "qr"
        elements = logic.normalize_elements(recs)
        late = logic.late_baseline_elements(elements)
        self.assertEqual(late, (("emc-control-plan", "qr", "pdr"),))

    def test_on_time_baseline_is_not_flagged(self):
        elements = logic.normalize_elements(full_element_set())
        self.assertEqual(logic.late_baseline_elements(elements), ())

    def test_early_baseline_is_not_flagged(self):
        recs = full_element_set()
        recs[2]["milestone"] = "srr"
        elements = logic.normalize_elements(recs)
        self.assertEqual(logic.late_baseline_elements(elements), ())

    def test_draft_element_is_not_a_late_baseline_finding(self):
        recs = full_element_set()
        recs[0]["milestone"] = "ar"
        recs[0]["state"] = "draft"
        elements = logic.normalize_elements(recs)
        self.assertEqual(logic.late_baseline_elements(elements), ())


class TestUnitRoles(unittest.TestCase):
    def test_transmitter_is_an_intentional_emitter(self):
        got = logic.categorize_unit({"id": "tx-1", "transmit_power_w": 12.0})
        self.assertEqual(got["roles"], (logic.ROLE_INTENTIONAL_EMITTER,))

    def test_receiver_with_threshold_holds_two_roles(self):
        got = logic.categorize_unit(
            {
                "id": "rx-1",
                "receive_sensitivity_dbm": -110.0,
                "susceptibility_threshold_dbm": -60.0,
            }
        )
        self.assertEqual(
            got["roles"],
            (logic.ROLE_INTENTIONAL_RECEIVER, logic.ROLE_SUSCEPTIBLE_VICTIM),
        )

    def test_switching_converter_is_a_non_intentional_source(self):
        got = logic.categorize_unit({"id": "pcdu", "switching_converter": True})
        self.assertEqual(got["roles"], (logic.ROLE_NON_INTENTIONAL_SOURCE,))

    def test_clocked_digital_unit_is_a_non_intentional_source(self):
        got = logic.categorize_unit({"id": "obc", "clocked_digital": True})
        self.assertEqual(got["roles"], (logic.ROLE_NON_INTENTIONAL_SOURCE,))

    def test_zero_transmit_power_is_not_an_emitter(self):
        got = logic.categorize_unit(
            {"id": "heater", "transmit_power_w": 0.0, "switching_converter": True}
        )
        self.assertEqual(got["roles"], (logic.ROLE_NON_INTENTIONAL_SOURCE,))

    def test_uncategorized_unit_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.categorize_unit({"id": "bracket"})

    def test_negative_transmit_power_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.categorize_unit({"id": "tx-2", "transmit_power_w": -5.0})

    def test_unit_record_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            logic.categorize_unit("tx-3")

    def test_unit_needs_a_non_blank_id(self):
        with self.assertRaises(ValueError):
            logic.categorize_unit({"id": " ", "transmit_power_w": 1.0})

    def test_non_numeric_sensitivity_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.categorize_unit({"id": "rx-2", "receive_sensitivity_dbm": "low"})

    def test_non_numeric_susceptibility_threshold_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.categorize_unit(
                {"id": "rx-3", "susceptibility_threshold_dbm": "medium"}
            )

    def test_role_inventory_counts_every_role(self):
        units = [
            {"id": "tx-1", "transmit_power_w": 12.0},
            {"id": "rx-1", "receive_sensitivity_dbm": -110.0},
            {"id": "pcdu", "switching_converter": True},
            {"id": "obc", "clocked_digital": True, "susceptibility_threshold_dbm": -50.0},
        ]
        counts = logic.role_inventory(units)
        self.assertEqual(counts[logic.ROLE_INTENTIONAL_EMITTER], 1)
        self.assertEqual(counts[logic.ROLE_INTENTIONAL_RECEIVER], 1)
        self.assertEqual(counts[logic.ROLE_NON_INTENTIONAL_SOURCE], 2)
        self.assertEqual(counts[logic.ROLE_SUSCEPTIBLE_VICTIM], 1)

    def test_role_inventory_rejects_non_sequence(self):
        with self.assertRaises(ValueError):
            logic.role_inventory({"id": "tx-1", "transmit_power_w": 1.0})


class TestChargingProgramme(unittest.TestCase):
    def test_geo_regime_drives_internal_charging(self):
        tasks = logic.required_charging_tasks("geo")
        self.assertIn(logic.TASK_INTERNAL, tasks)
        self.assertIn(logic.TASK_SURFACE, tasks)

    def test_low_inclination_leo_does_not_drive_surface_charging(self):
        tasks = logic.required_charging_tasks("leo-low-inclination")
        self.assertNotIn(logic.TASK_SURFACE, tasks)
        self.assertIn(logic.TASK_ESD_SUSCEPTIBILITY, tasks)

    def test_polar_leo_drives_auroral_charging(self):
        self.assertIn(logic.TASK_AURORAL, logic.required_charging_tasks("leo-polar"))

    def test_unknown_orbit_regime_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.required_charging_tasks("lunar-transfer")

    def test_missing_charging_task_is_reported(self):
        found = logic.charging_programme_findings(
            [logic.TASK_SURFACE, logic.TASK_ESD_SUSCEPTIBILITY], "geo"
        )
        self.assertIn(logic.TASK_INTERNAL, found["missing"])
        self.assertIn(logic.TASK_GROUNDING_RETURN, found["missing"])

    def test_over_declared_task_is_reported_separately(self):
        declared = list(logic.required_charging_tasks("leo-low-inclination"))
        declared.append(logic.TASK_INTERNAL)
        found = logic.charging_programme_findings(declared, "leo-low-inclination")
        self.assertEqual(found["missing"], ())
        self.assertEqual(found["over_declared"], (logic.TASK_INTERNAL,))

    def test_blank_charging_task_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.charging_programme_findings(["  "], "geo")

    def test_charging_tasks_must_be_a_sequence(self):
        with self.assertRaises(ValueError):
            logic.charging_programme_findings("surface-charging-protection", "geo")


class TestAssessment(unittest.TestCase):
    def setUp(self):
        self.units = [
            {"id": "tx-1", "transmit_power_w": 12.0},
            {"id": "rx-1", "receive_sensitivity_dbm": -110.0},
        ]

    def test_complete_programme_is_compliant(self):
        report = logic.assess_emc_policy(
            full_element_set(),
            self.units,
            "geo",
            logic.required_charging_tasks("geo"),
        )
        self.assertTrue(report["compliant"])
        self.assertEqual(report["findings"], ())
        self.assertAlmostEqual(report["coverage_ratio"], 1.0, places=12)

    def test_missing_element_makes_the_programme_non_compliant(self):
        report = logic.assess_emc_policy(
            full_element_set()[:-1],
            self.units,
            "geo",
            logic.required_charging_tasks("geo"),
        )
        self.assertFalse(report["compliant"])
        self.assertTrue(
            any(f.startswith("missing-policy-element:") for f in report["findings"])
        )

    def test_missing_charging_task_makes_the_programme_non_compliant(self):
        report = logic.assess_emc_policy(
            full_element_set(), self.units, "geo", [logic.TASK_SURFACE]
        )
        self.assertFalse(report["compliant"])
        self.assertIn(
            "missing-charging-task:%s" % logic.TASK_INTERNAL, report["findings"]
        )

    def test_late_baseline_appears_in_the_findings(self):
        recs = full_element_set()
        recs[0]["milestone"] = "ar"
        report = logic.assess_emc_policy(
            recs, self.units, "geo", logic.required_charging_tasks("geo")
        )
        self.assertFalse(report["compliant"])
        self.assertTrue(any(f.startswith("late-baseline:") for f in report["findings"]))

    def test_assessment_propagates_a_bad_unit_record(self):
        with self.assertRaises(ValueError):
            logic.assess_emc_policy(
                full_element_set(),
                [{"id": "bracket"}],
                "geo",
                logic.required_charging_tasks("geo"),
            )

    def test_assessment_reports_the_role_inventory(self):
        report = logic.assess_emc_policy(
            full_element_set(),
            self.units,
            "leo-polar",
            logic.required_charging_tasks("leo-polar"),
        )
        self.assertEqual(report["role_inventory"][logic.ROLE_INTENTIONAL_EMITTER], 1)
        self.assertEqual(report["orbit_regime"], "leo-polar")


if __name__ == "__main__":
    unittest.main()
