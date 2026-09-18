"""Contract test for the q40-hazard-closeout leaf (stdlib unittest)."""

import unittest

from q40_hazard_closeout_logic import (
    SVTL_STATUSES,
    close_out_hazard,
    close_out_log,
    closure_fraction,
    control_findings,
    hazard_level_findings,
    svtl_entries,
    untracked_controls,
    validate_hazard,
)


def control(cid="HC-1", status="closed", evidence="VR-1", accepted=True, tracked=True):
    entry = None
    if tracked:
        entry = {
            "status": status,
            "evidence_ref": evidence,
            "evidence_accepted": accepted,
            "verification_method": "test",
        }
    return {"id": cid, "svtl_entry": entry}


def hazard(hid="HZ-1", severity="critical", controls=None, **kw):
    record = {
        "id": hid,
        "severity": severity,
        "controls": controls if controls is not None else [control("HC-1"), control("HC-2")],
        "review_board_endorsed": True,
    }
    record.update(kw)
    return record


class TestValidateHazard(unittest.TestCase):
    def test_a_complete_report_normalises(self):
        norm = validate_hazard(hazard())
        self.assertEqual(norm["severity"], "critical")
        self.assertEqual(len(norm["controls"]), 2)

    def test_non_mapping_raises(self):
        with self.assertRaises(ValueError):
            validate_hazard("HZ-1")

    def test_a_hazard_with_no_controls_raises(self):
        with self.assertRaises(ValueError):
            validate_hazard(hazard(controls=[]))

    def test_unknown_severity_raises(self):
        with self.assertRaises(ValueError):
            validate_hazard(hazard(severity="irritating"))

    def test_unknown_svtl_status_raises(self):
        with self.assertRaises(ValueError):
            validate_hazard(hazard(controls=[control(status="nearly-done")]))

    def test_a_repeated_control_id_raises(self):
        with self.assertRaises(ValueError):
            validate_hazard(hazard(controls=[control("HC-1"), control("HC-1")]))

    def test_a_non_mapping_svtl_entry_raises(self):
        with self.assertRaises(ValueError):
            validate_hazard(hazard(controls=[{"id": "HC-1", "svtl_entry": "closed"}]))

    def test_a_non_boolean_endorsement_raises(self):
        with self.assertRaises(ValueError):
            validate_hazard(hazard(review_board_endorsed="yes"))

    def test_an_empty_control_id_raises(self):
        with self.assertRaises(ValueError):
            validate_hazard(hazard(controls=[control("  ")]))


class TestSvtl(unittest.TestCase):
    def test_every_tracked_control_contributes_a_row(self):
        rows = svtl_entries(hazard())
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["hazard_id"], "HZ-1")
        self.assertEqual(rows[0]["control_id"], "HC-1")

    def test_an_untracked_control_contributes_no_row(self):
        rows = svtl_entries(hazard(controls=[control("HC-1"), control("HC-2", tracked=False)]))
        self.assertEqual(len(rows), 1)

    def test_untracked_controls_are_named(self):
        names = untracked_controls(hazard(controls=[control("HC-1"),
                                                    control("HC-2", tracked=False)]))
        self.assertEqual(names, ["HC-2"])

    def test_a_fully_tracked_hazard_has_no_untracked_controls(self):
        self.assertEqual(untracked_controls(hazard()), [])

    def test_the_svtl_status_vocabulary_is_three_states(self):
        self.assertEqual(SVTL_STATUSES, ("open", "in-work", "closed"))


class TestControlFindings(unittest.TestCase):
    def test_a_clean_hazard_has_no_control_findings(self):
        self.assertEqual(control_findings(hazard()), [])

    def test_an_untracked_control_is_a_finding(self):
        found = control_findings(hazard(controls=[control("HC-1", tracked=False)]))
        self.assertIn("no SVTL entry", found[0]["reason"])

    def test_an_in_work_entry_is_a_finding(self):
        found = control_findings(hazard(controls=[control("HC-1", status="in-work")]))
        self.assertIn("not closed", found[0]["reason"])

    def test_a_closed_entry_without_evidence_is_a_finding(self):
        found = control_findings(hazard(controls=[control("HC-1", evidence=None)]))
        self.assertIn("no evidence reference", found[0]["reason"])

    def test_unaccepted_evidence_is_a_finding(self):
        found = control_findings(hazard(controls=[control("HC-1", accepted=False)]))
        self.assertIn("has not been accepted", found[0]["reason"])

    def test_each_control_produces_at_most_one_finding(self):
        found = control_findings(hazard(controls=[control("HC-1", status="open",
                                                          evidence=None)]))
        self.assertEqual(len(found), 1)

    def test_findings_are_collected_across_controls(self):
        found = control_findings(hazard(controls=[control("HC-1", status="open"),
                                                  control("HC-2", accepted=False),
                                                  control("HC-3")]))
        self.assertEqual(len(found), 2)


class TestHazardLevelFindings(unittest.TestCase):
    def test_a_severe_hazard_needs_the_board(self):
        found = hazard_level_findings(hazard(review_board_endorsed=False))
        self.assertTrue(any("review board" in f for f in found))

    def test_a_minor_hazard_does_not_need_the_board(self):
        self.assertEqual(hazard_level_findings(
            hazard(severity="minor", review_board_endorsed=False)), [])

    def test_a_declared_residual_risk_needs_an_acceptance_reference(self):
        found = hazard_level_findings(hazard(residual_risk_declared=True))
        self.assertTrue(any("acceptance reference" in f for f in found))

    def test_a_referenced_residual_risk_is_accepted(self):
        self.assertEqual(hazard_level_findings(
            hazard(residual_risk_declared=True,
                   residual_risk_acceptance_ref="RRA-4")), [])

    def test_an_orphan_acceptance_reference_is_a_finding(self):
        found = hazard_level_findings(hazard(residual_risk_acceptance_ref="RRA-4"))
        self.assertTrue(any("no residual risk is declared" in f for f in found))


class TestCloseOutHazard(unittest.TestCase):
    def test_a_clean_hazard_closes(self):
        report = close_out_hazard(hazard())
        self.assertEqual(report["disposition"], "hazard-closed")
        self.assertTrue(report["closed"])
        self.assertEqual(report["findings"], [])
        self.assertIn("every control is closed", report["close_out_statement"])

    def test_closure_fraction_of_a_clean_hazard_is_one(self):
        self.assertAlmostEqual(closure_fraction(hazard()), 1.0, places=9)

    def test_closure_fraction_counts_only_clean_controls(self):
        record = hazard(controls=[control("HC-1"), control("HC-2", status="open"),
                                  control("HC-3"), control("HC-4", tracked=False)])
        self.assertAlmostEqual(closure_fraction(record), 0.5, places=9)

    def test_one_open_control_holds_the_whole_hazard_open(self):
        report = close_out_hazard(hazard(controls=[control("HC-1"),
                                                   control("HC-2", status="in-work")]))
        self.assertEqual(report["disposition"], "hazard-open")
        self.assertIn("close-out withheld", report["close_out_statement"])

    def test_a_hazard_level_finding_alone_holds_it_open(self):
        report = close_out_hazard(hazard(review_board_endorsed=False))
        self.assertFalse(report["closed"])
        self.assertEqual(report["control_findings"], [])
        self.assertEqual(len(report["hazard_findings"]), 1)

    def test_the_statement_names_the_hazard_and_its_severity(self):
        report = close_out_hazard(hazard("HZ-9", "major", review_board_endorsed=False))
        self.assertIn("HZ-9", report["close_out_statement"])
        self.assertIn("major", report["close_out_statement"])


class TestCloseOutLog(unittest.TestCase):
    def test_a_clean_log_closes(self):
        rollup = close_out_log([hazard("HZ-1"), hazard("HZ-2")])
        self.assertEqual(rollup["disposition"], "log-closed")
        self.assertAlmostEqual(rollup["closed_ratio"], 1.0, places=9)

    def test_the_rollup_counts_svtl_rows_by_status(self):
        rollup = close_out_log([hazard("HZ-1", controls=[control("HC-1"),
                                                         control("HC-2", status="open")])])
        self.assertEqual(rollup["svtl_status_counts"]["closed"], 1)
        self.assertEqual(rollup["svtl_status_counts"]["open"], 1)
        self.assertEqual(rollup["svtl_status_counts"]["in-work"], 0)

    def test_untracked_controls_are_counted_across_the_log(self):
        rollup = close_out_log([hazard("HZ-1", controls=[control("HC-1", tracked=False)]),
                                hazard("HZ-2", controls=[control("HC-2", tracked=False)])])
        self.assertEqual(rollup["untracked_control_count"], 2)

    def test_an_open_severe_hazard_blocks_the_log(self):
        rollup = close_out_log([hazard("HZ-1"),
                                hazard("HZ-2", "catastrophic",
                                       review_board_endorsed=False)])
        self.assertEqual(rollup["disposition"], "log-blocked")
        self.assertEqual(rollup["severe_open_hazard_ids"], ["HZ-2"])

    def test_an_open_minor_hazard_only_leaves_the_log_open(self):
        rollup = close_out_log([hazard("HZ-1"),
                                hazard("HZ-2", "minor",
                                       controls=[control("HC-1", status="open")])])
        self.assertEqual(rollup["disposition"], "log-open")
        self.assertEqual(rollup["severe_open_hazard_ids"], [])
        self.assertAlmostEqual(rollup["closed_ratio"], 0.5, places=9)

    def test_duplicate_hazard_ids_raise(self):
        with self.assertRaises(ValueError):
            close_out_log([hazard("HZ-1"), hazard("HZ-1")])

    def test_an_empty_log_raises(self):
        with self.assertRaises(ValueError):
            close_out_log([])


if __name__ == "__main__":
    unittest.main()
