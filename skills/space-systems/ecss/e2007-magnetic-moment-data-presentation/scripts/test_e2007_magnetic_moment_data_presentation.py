#!/usr/bin/env python3
"""Gate 3 contract test for e2007-magnetic-moment-data-presentation.

stdlib unittest, offline, deterministic. Run:
    python3 test_e2007_magnetic_moment_data_presentation.py
"""

import unittest

from e2007_magnetic_moment_data_presentation_logic import (
    AXIS_RESULTANT,
    FORM_PLOT,
    FORM_SUMMARY,
    FORM_TABLE,
    PRESENTATION_COMPLETE,
    PRESENTATION_DEFICIENT,
    REQUIRED_AXES,
    assess_magnetic_moment_data_presentation,
    implied_dipole_moment_am2,
    implied_moments,
    missing_axes,
    missing_distances,
    moment_consistency_findings,
    normalize_axis,
    normalize_form,
    presentation_form_findings,
    reported_distances,
    resultant_at_distance,
    resultant_consistency_findings,
    resultant_nt,
    rows_at_distance,
    validate_row,
    validate_rows,
)

# A 1 A*m2 source read on axis: 200 nT at 1 m, 25 nT at 2 m, 3.125 nT at 4 m.
DISTANCES = (1.0, 2.0, 4.0)
COMPONENTS = {
    1.0: (120.0, 160.0, 0.0),
    2.0: (15.0, 20.0, 0.0),
    4.0: (1.875, 2.5, 0.0),
}
RESULTANTS = {1.0: 200.0, 2.0: 25.0, 4.0: 3.125}


def table(distances=DISTANCES, with_resultant=True, axes=REQUIRED_AXES):
    rows = []
    for distance in distances:
        bx, by, bz = COMPONENTS[distance]
        values = {"x": bx, "y": by, "z": bz}
        for axis in axes:
            rows.append(
                {"distance_m": distance, "axis": axis, "field_nt": values[axis]}
            )
        if with_resultant:
            rows.append(
                {
                    "distance_m": distance,
                    "axis": AXIS_RESULTANT,
                    "field_nt": RESULTANTS[distance],
                }
            )
    return rows


def good_report(**over):
    record = {
        "presented_as": FORM_TABLE,
        "rows": table(),
        "required_distances_m": list(DISTANCES),
        "uncertainty_stated": True,
    }
    record.update(over)
    return record


class TestTokensAndRows(unittest.TestCase):
    def test_axis_label_is_case_normalized(self):
        self.assertEqual(normalize_axis(" Z "), "z")

    def test_the_resultant_is_a_recognized_axis_label(self):
        self.assertEqual(normalize_axis("Resultant"), AXIS_RESULTANT)

    def test_an_unknown_axis_label_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_axis("radial")

    def test_form_label_is_case_normalized(self):
        self.assertEqual(normalize_form("Per-Distance-Per-Axis-Table"), FORM_TABLE)

    def test_an_unknown_form_label_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_form("appendix")

    def test_a_good_row_normalizes(self):
        row = validate_row({"distance_m": 1.0, "axis": "X", "field_nt": 120.0})
        self.assertEqual(row["axis"], "x")
        self.assertAlmostEqual(row["field_nt"], 120.0, places=9)

    def test_a_zero_distance_row_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_row({"distance_m": 0.0, "axis": "x", "field_nt": 1.0})

    def test_a_negative_field_row_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_row({"distance_m": 1.0, "axis": "x", "field_nt": -1.0})

    def test_a_row_without_an_axis_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_row({"distance_m": 1.0, "field_nt": 1.0})

    def test_an_empty_table_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_rows([])

    def test_the_same_axis_reported_twice_at_one_distance_is_rejected(self):
        rows = table(distances=(1.0,))
        rows.append({"distance_m": 1.0, "axis": "x", "field_nt": 120.0})
        with self.assertRaises(ValueError):
            validate_rows(rows)


class TestTableGeometry(unittest.TestCase):
    def test_reported_distances_are_distinct_and_ordered(self):
        rows = validate_rows(table())
        self.assertEqual(reported_distances(rows), [1.0, 2.0, 4.0])

    def test_rows_at_a_distance_carry_the_axes_and_the_resultant(self):
        rows = validate_rows(table())
        self.assertEqual(len(rows_at_distance(rows, 2.0)), 4)

    def test_a_declared_distance_never_reported_is_listed(self):
        rows = validate_rows(table(distances=(1.0, 2.0)))
        self.assertEqual(missing_distances(rows, list(DISTANCES)), [4.0])

    def test_a_fully_reported_table_misses_no_distance(self):
        rows = validate_rows(table())
        self.assertEqual(missing_distances(rows, list(DISTANCES)), [])

    def test_an_empty_declared_distance_list_is_rejected(self):
        rows = validate_rows(table())
        with self.assertRaises(ValueError):
            missing_distances(rows, [])

    def test_a_missing_axis_at_one_distance_is_listed(self):
        rows = validate_rows(table(axes=("x", "y")))
        self.assertEqual(missing_axes(rows, 1.0), ["z"])

    def test_a_complete_distance_misses_no_axis(self):
        rows = validate_rows(table())
        self.assertEqual(missing_axes(rows, 4.0), [])


class TestDerivedQuantities(unittest.TestCase):
    def test_resultant_is_the_vector_sum_of_the_components(self):
        self.assertAlmostEqual(resultant_nt(120.0, 160.0, 0.0), 200.0, places=9)

    def test_resultant_ignores_component_sign(self):
        self.assertAlmostEqual(resultant_nt(-15.0, 0.0, -20.0), 25.0, places=9)

    def test_implied_moment_at_one_metre_is_the_field_over_the_coefficient(self):
        self.assertAlmostEqual(implied_dipole_moment_am2(200.0, 1.0), 1.0, places=9)

    def test_implied_moment_absorbs_the_cube_of_the_distance(self):
        self.assertAlmostEqual(implied_dipole_moment_am2(25.0, 2.0), 1.0, places=9)

    def test_implied_moment_rejects_a_zero_distance(self):
        with self.assertRaises(ValueError):
            implied_dipole_moment_am2(200.0, 0.0)

    def test_reported_resultant_is_used_when_present(self):
        rows = validate_rows(table())
        self.assertAlmostEqual(resultant_at_distance(rows, 2.0), 25.0, places=9)

    def test_resultant_is_rebuilt_from_the_axes_when_absent(self):
        rows = validate_rows(table(with_resultant=False))
        self.assertAlmostEqual(resultant_at_distance(rows, 4.0), 3.125, places=9)

    def test_resultant_is_unavailable_when_an_axis_is_missing(self):
        rows = validate_rows(table(with_resultant=False, axes=("x", "y")))
        self.assertIsNone(resultant_at_distance(rows, 1.0))

    def test_every_distance_implies_the_same_moment(self):
        rows = validate_rows(table())
        for _, moment in implied_moments(rows):
            self.assertAlmostEqual(moment, 1.0, places=9)


class TestConsistency(unittest.TestCase):
    def test_a_coherent_table_has_no_resultant_finding(self):
        rows = validate_rows(table())
        self.assertEqual(resultant_consistency_findings(rows), [])

    def test_a_resultant_that_contradicts_its_axes_is_reported(self):
        rows = table()
        for row in rows:
            if row["axis"] == AXIS_RESULTANT and row["distance_m"] == 1.0:
                row["field_nt"] = 150.0
        findings = resultant_consistency_findings(validate_rows(rows))
        self.assertEqual(len(findings), 1)
        self.assertIn("does not follow from the axis", findings[0])

    def test_a_resultant_check_rejects_a_zero_tolerance(self):
        rows = validate_rows(table())
        with self.assertRaises(ValueError):
            resultant_consistency_findings(rows, 0.0)

    def test_a_coherent_table_has_no_moment_finding(self):
        rows = validate_rows(table())
        self.assertEqual(moment_consistency_findings(rows), [])

    def test_a_row_filed_at_the_wrong_distance_breaks_the_moment_agreement(self):
        rows = table()
        for row in rows:
            if row["distance_m"] == 2.0:
                row["field_nt"] = row["field_nt"] * 4.0
        findings = moment_consistency_findings(validate_rows(rows))
        self.assertEqual(len(findings), 1)
        self.assertIn("implied moments run from", findings[0])

    def test_a_single_distance_cannot_disagree_with_itself(self):
        rows = validate_rows(table(distances=(1.0,)))
        self.assertEqual(moment_consistency_findings(rows), [])


class TestPresentationForm(unittest.TestCase):
    def test_the_table_form_raises_no_finding(self):
        self.assertEqual(presentation_form_findings(FORM_TABLE), [])

    def test_a_spectrum_plot_is_reported_as_the_wrong_form(self):
        findings = presentation_form_findings(FORM_PLOT)
        self.assertEqual(len(findings), 1)
        self.assertIn("no spectrum", findings[0])

    def test_a_single_summary_figure_is_reported_as_the_wrong_form(self):
        findings = presentation_form_findings(FORM_SUMMARY)
        self.assertEqual(len(findings), 1)
        self.assertIn("per distance and per axis", findings[0])


class TestFullAssessment(unittest.TestCase):
    def test_a_complete_table_passes(self):
        report = assess_magnetic_moment_data_presentation(good_report())
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["verdict"], PRESENTATION_COMPLETE)
        self.assertEqual(report["reported_distances_m"], [1.0, 2.0, 4.0])

    def test_a_plot_instead_of_a_table_is_deficient(self):
        report = assess_magnetic_moment_data_presentation(
            good_report(presented_as=FORM_PLOT)
        )
        self.assertEqual(report["verdict"], PRESENTATION_DEFICIENT)

    def test_a_declared_distance_left_out_is_a_finding(self):
        report = assess_magnetic_moment_data_presentation(
            good_report(rows=table(distances=(1.0, 2.0)))
        )
        self.assertEqual(report["missing_distances_m"], [4.0])
        self.assertTrue(any("declared distance" in f for f in report["findings"]))

    def test_a_missing_axis_is_a_finding(self):
        report = assess_magnetic_moment_data_presentation(
            good_report(rows=table(axes=("x", "y")), required_distances_m=[1.0])
        )
        self.assertTrue(any("missing the z axis" in f for f in report["findings"]))

    def test_missing_uncertainty_is_a_limitation_not_a_finding(self):
        report = assess_magnetic_moment_data_presentation(
            good_report(uncertainty_stated=False)
        )
        self.assertEqual(report["findings"], [])
        self.assertTrue(any("uncertainty" in m for m in report["limitations"]))
        self.assertEqual(report["verdict"], PRESENTATION_COMPLETE)

    def test_a_single_distance_table_is_complete_but_limited(self):
        report = assess_magnetic_moment_data_presentation(
            good_report(rows=table(distances=(1.0,)), required_distances_m=[1.0])
        )
        self.assertEqual(report["findings"], [])
        self.assertTrue(any("only one distance" in m for m in report["limitations"]))

    def test_report_carries_the_implied_moment_per_distance(self):
        report = assess_magnetic_moment_data_presentation(good_report())
        self.assertEqual(len(report["implied_moments_am2"]), 3)
        self.assertAlmostEqual(report["implied_moments_am2"][0][1], 1.0, places=9)

    def test_a_report_without_rows_is_rejected(self):
        record = good_report()
        del record["rows"]
        with self.assertRaises(ValueError):
            assess_magnetic_moment_data_presentation(record)

    def test_a_report_without_an_uncertainty_flag_is_rejected(self):
        record = good_report()
        del record["uncertainty_stated"]
        with self.assertRaises(ValueError):
            assess_magnetic_moment_data_presentation(record)

    def test_a_non_mapping_report_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_magnetic_moment_data_presentation(["rows"])


if __name__ == "__main__":
    unittest.main()
