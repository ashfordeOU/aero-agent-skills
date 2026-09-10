#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10C Annex F Technology Matrix DRD.

Exercises scripts/e10_tech_matrix_drd_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - a Technology
Matrix document is section-complete only when it carries all required
DRD sections; a technology row is field-complete only when it carries
current TRL, target TRL, and mission applicability; a TRL value is
valid only when it is an integer from 1 to 9; a row regresses only
when its target TRL is below its current TRL; applicability is
resolved only when it is 'applicable' or 'not applicable'; the matrix
is ready only when there are no missing sections, no missing fields,
no invalid TRLs, no regressions, and no unresolved applicability.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e10_tech_matrix_drd_logic as tm  # noqa: E402


class SectionGapsTest(unittest.TestCase):
    def test_no_gaps_when_all_present(self):
        self.assertEqual(tm.section_gaps(tm.REQUIRED_DRD_SECTIONS), [])

    def test_missing_sections_listed_in_order(self):
        self.assertEqual(
            tm.section_gaps(["purpose and scope"]),
            ["applicable and reference documents", "technology matrix"],
        )

    def test_empty_input_lists_all_sections(self):
        self.assertEqual(tm.section_gaps([]), list(tm.REQUIRED_DRD_SECTIONS))


class RowFieldGapsTest(unittest.TestCase):
    def test_no_gaps_when_all_present(self):
        row = {"current trl": 4, "target trl": 6, "mission applicability": "applicable"}
        self.assertEqual(tm.row_field_gaps(row), [])

    def test_missing_fields_listed_in_order(self):
        row = {"target trl": 6}
        self.assertEqual(
            tm.row_field_gaps(row),
            ["current trl", "mission applicability"],
        )


class MatrixFieldGapsTest(unittest.TestCase):
    def test_complete_rows_no_gaps(self):
        rows = {
            "Star tracker": {"current trl": 5, "target trl": 7, "mission applicability": "applicable"},
        }
        self.assertEqual(tm.matrix_field_gaps(rows), {})

    def test_incomplete_row_reported_by_name(self):
        rows = {
            "Star tracker": {"current trl": 5},
        }
        self.assertEqual(
            tm.matrix_field_gaps(rows),
            {"Star tracker": ["target trl", "mission applicability"]},
        )


class InvalidTrlsTest(unittest.TestCase):
    def test_valid_trls_not_flagged(self):
        rows = {"Tech A": {"current trl": 1, "target trl": 9, "mission applicability": "applicable"}}
        self.assertEqual(tm.invalid_trls(rows), [])

    def test_out_of_range_trl_flagged(self):
        rows = {"Tech A": {"current trl": 10, "target trl": 6, "mission applicability": "applicable"}}
        self.assertEqual(tm.invalid_trls(rows), [("Tech A", "current trl", 10)])

    def test_non_integer_trl_flagged(self):
        rows = {"Tech A": {"current trl": "6-7", "target trl": 6, "mission applicability": "applicable"}}
        self.assertEqual(tm.invalid_trls(rows), [("Tech A", "current trl", "6-7")])

    def test_missing_field_not_double_reported(self):
        rows = {"Tech A": {"target trl": 6, "mission applicability": "applicable"}}
        self.assertEqual(tm.invalid_trls(rows), [])


class TrlRegressionsTest(unittest.TestCase):
    def test_target_at_or_above_current_no_regression(self):
        rows = {
            "Tech A": {"current trl": 4, "target trl": 4, "mission applicability": "applicable"},
            "Tech B": {"current trl": 4, "target trl": 7, "mission applicability": "applicable"},
        }
        self.assertEqual(tm.trl_regressions(rows), [])

    def test_target_below_current_flagged(self):
        rows = {"Tech A": {"current trl": 6, "target trl": 4, "mission applicability": "applicable"}}
        self.assertEqual(tm.trl_regressions(rows), ["Tech A"])

    def test_invalid_trl_not_checked_for_regression(self):
        rows = {"Tech A": {"current trl": "n/a", "target trl": 4, "mission applicability": "applicable"}}
        self.assertEqual(tm.trl_regressions(rows), [])


class UnresolvedApplicabilityTest(unittest.TestCase):
    def test_resolved_values_not_flagged(self):
        rows = {
            "Tech A": {"current trl": 4, "target trl": 6, "mission applicability": "applicable"},
            "Tech B": {"current trl": 4, "target trl": 6, "mission applicability": "not applicable"},
        }
        self.assertEqual(tm.unresolved_applicability(rows), [])

    def test_tbd_flagged(self):
        rows = {"Tech A": {"current trl": 4, "target trl": 6, "mission applicability": "TBD"}}
        self.assertEqual(tm.unresolved_applicability(rows), ["Tech A"])

    def test_missing_flagged(self):
        rows = {"Tech A": {"current trl": 4, "target trl": 6}}
        self.assertEqual(tm.unresolved_applicability(rows), ["Tech A"])


class TechMatrixReadyTest(unittest.TestCase):
    def test_ready_when_clean(self):
        rows = {
            "Tech A": {"current trl": 4, "target trl": 6, "mission applicability": "applicable"},
        }
        ready, issues = tm.tech_matrix_ready(tm.REQUIRED_DRD_SECTIONS, rows)
        self.assertTrue(ready)
        self.assertEqual(issues["missing_sections"], [])
        self.assertEqual(issues["missing_fields"], {})
        self.assertEqual(issues["invalid_trls"], [])
        self.assertEqual(issues["trl_regressions"], [])
        self.assertEqual(issues["unresolved_applicability"], [])

    def test_not_ready_reports_every_issue_type(self):
        rows = {
            "Tech A": {"current trl": 6, "target trl": 4, "mission applicability": "applicable"},
            "Tech B": {"current trl": 12, "target trl": 5},
        }
        ready, issues = tm.tech_matrix_ready(["purpose and scope"], rows)
        self.assertFalse(ready)
        self.assertEqual(
            issues["missing_sections"],
            ["applicable and reference documents", "technology matrix"],
        )
        self.assertEqual(issues["missing_fields"], {"Tech B": ["mission applicability"]})
        self.assertEqual(issues["invalid_trls"], [("Tech B", "current trl", 12)])
        self.assertEqual(issues["trl_regressions"], ["Tech A"])
        self.assertEqual(issues["unresolved_applicability"], ["Tech B"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
