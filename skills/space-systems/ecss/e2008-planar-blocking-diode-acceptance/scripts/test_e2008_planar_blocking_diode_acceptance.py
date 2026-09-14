#!/usr/bin/env python3
"""Contract test for the planar blocking diode acceptance programme.

Walks the clause workflow step by step: the table the programme is graded
against, the construction the table covers, the proposed programme read
in its run order, the tabulated tests omitted and the tests added, the
run order against the tabulated order, the electrical readout every
stress owes, the basis and unit count each test runs at, the
completeness share against its floor, and the single programme verdict.
This is the gate 3 review evidence for the leaf.
"""

import copy
import unittest

from e2008_planar_blocking_diode_acceptance_logic import (
    AP_ACCEPTED,
    AP_INCOMPLETE,
    AP_OUT_OF_SCOPE,
    AP_RANK,
    TABULATED_BASIS,
    TABULATED_SEQUENCE,
    assess_planar_blocking_diode_acceptance,
    basis_and_sample,
    construction_scope,
    post_stress_readout,
    programme_completeness,
    programme_coverage,
    read_programme,
    resolve_policy,
    sequence_order,
)

LOT_SIZE = 40
SAMPLE_UNITS = 6


def _entries(names=None, **overrides):
    rows = []
    for name in TABULATED_SEQUENCE if names is None else names:
        basis = TABULATED_BASIS[name]
        row = {
            "test": name,
            "basis": basis,
            "units": LOT_SIZE if basis == "every-unit" else SAMPLE_UNITS,
        }
        if name in overrides:
            row.update(overrides[name])
        rows.append(row)
    return rows


SOUND_CASE = {
    "programme_id": "AP-PLANAR-BD-03",
    "construction": "planar-blocking-diode",
    "lot_size": LOT_SIZE,
    "entries": _entries(),
}


def _case(**overrides):
    record = copy.deepcopy(SOUND_CASE)
    record.update(overrides)
    return record


class PolicyTests(unittest.TestCase):
    def test_the_default_policy_carries_the_whole_table(self):
        settings = resolve_policy()
        self.assertEqual(settings["tabulated_sequence"], TABULATED_SEQUENCE)

    def test_an_empty_table_is_refused(self):
        with self.assertRaises(ValueError):
            resolve_policy({"tabulated_sequence": ()})

    def test_a_table_listing_a_test_twice_is_refused(self):
        with self.assertRaises(ValueError):
            resolve_policy(
                {"tabulated_sequence": ("thermal-shock", "thermal-shock")}
            )

    def test_a_table_entry_outside_the_tabulated_set_is_refused(self):
        with self.assertRaises(ValueError):
            resolve_policy({"tabulated_sequence": ("bend-test",)})

    def test_a_sampling_floor_outside_zero_to_one_is_refused(self):
        with self.assertRaises(ValueError):
            resolve_policy({"min_sample_share": -0.2})


class ConstructionScopeTests(unittest.TestCase):
    def test_a_planar_part_is_the_one_the_table_covers(self):
        result = construction_scope("planar-blocking-diode")
        self.assertTrue(result["in_scope"])
        self.assertEqual(result["findings"], [])

    def test_a_mesa_part_carries_its_own_list(self):
        result = construction_scope("mesa-blocking-diode")
        self.assertFalse(result["in_scope"])
        self.assertTrue(result["findings"])

    def test_an_integrated_part_is_accepted_through_its_assembly(self):
        result = construction_scope("integrated-blocking-diode")
        self.assertFalse(result["in_scope"])

    def test_an_unknown_construction_is_refused(self):
        with self.assertRaises(ValueError):
            construction_scope("wire-bonded-blocking-diode")


class ProgrammeReadingTests(unittest.TestCase):
    def test_a_sound_programme_reads_back_in_run_order(self):
        ordered = read_programme(_entries())
        self.assertEqual(
            [row["test"] for row in ordered], list(TABULATED_SEQUENCE)
        )

    def test_a_test_proposed_twice_is_refused(self):
        with self.assertRaises(ValueError):
            read_programme(_entries() + _entries(["thermal-shock"]))

    def test_an_unknown_basis_is_refused(self):
        rows = _entries(**{"seal-leak-test": {"basis": "as-required"}})
        with self.assertRaises(ValueError):
            read_programme(rows)

    def test_a_negative_unit_count_is_refused(self):
        rows = _entries(**{"thermal-shock": {"units": -4}})
        with self.assertRaises(ValueError):
            read_programme(rows)

    def test_an_empty_programme_is_refused(self):
        with self.assertRaises(ValueError):
            read_programme([])

    def test_a_non_mapping_entry_is_refused(self):
        with self.assertRaises(ValueError):
            read_programme(["thermal-shock"])


class CoverageTests(unittest.TestCase):
    def test_a_complete_programme_holds_the_whole_table(self):
        result = programme_coverage(read_programme(_entries()), TABULATED_SEQUENCE)
        self.assertEqual(result["missing"], [])
        self.assertEqual(result["untabulated"], [])
        self.assertAlmostEqual(result["presence_share"], 1.0, places=9)

    def test_a_tabulated_test_left_out_is_named(self):
        names = [n for n in TABULATED_SEQUENCE if n != "seal-leak-test"]
        result = programme_coverage(
            read_programme(_entries(names)), TABULATED_SEQUENCE
        )
        self.assertEqual(result["missing"], ["seal-leak-test"])

    def test_a_test_added_to_the_table_is_named(self):
        rows = read_programme(
            _entries()
            + [{"test": "salt-fog", "basis": "sampled", "units": SAMPLE_UNITS}]
        )
        result = programme_coverage(rows, TABULATED_SEQUENCE)
        self.assertEqual(result["untabulated"], ["salt-fog"])


class SequenceTests(unittest.TestCase):
    def test_the_tabulated_order_reports_no_inversion(self):
        result = sequence_order(read_programme(_entries()), TABULATED_SEQUENCE)
        self.assertTrue(result["ordered"])
        self.assertEqual(result["inversions"], [])

    def test_a_final_measurement_run_before_a_stress_is_an_inversion(self):
        names = [
            "initial-visual-inspection",
            "initial-electrical-measurement",
            "final-electrical-measurement",
            "thermal-shock",
        ]
        result = sequence_order(read_programme(_entries(names)), TABULATED_SEQUENCE)
        self.assertFalse(result["ordered"])
        self.assertIn(
            ("final-electrical-measurement", "thermal-shock"), result["inversions"]
        )

    def test_an_untabulated_test_takes_no_part_in_the_order(self):
        rows = read_programme(
            [{"test": "salt-fog", "basis": "sampled", "units": SAMPLE_UNITS}]
            + _entries()
        )
        result = sequence_order(rows, TABULATED_SEQUENCE)
        self.assertTrue(result["ordered"])


class PostStressReadoutTests(unittest.TestCase):
    def test_every_stress_is_read_in_the_tabulated_order(self):
        result = post_stress_readout(
            read_programme(_entries()), TABULATED_SEQUENCE
        )
        self.assertTrue(result["every_stress_read"])
        self.assertEqual(result["unread"], [])

    def test_a_stress_run_last_is_never_read(self):
        names = [
            "initial-visual-inspection",
            "initial-electrical-measurement",
            "final-electrical-measurement",
            "thermal-shock",
        ]
        result = post_stress_readout(
            read_programme(_entries(names)), TABULATED_SEQUENCE
        )
        self.assertEqual(result["unread"], ["thermal-shock"])

    def test_a_visual_inspection_after_a_stress_is_not_a_readout(self):
        names = [
            "initial-electrical-measurement",
            "mechanical-shock",
            "final-visual-inspection",
        ]
        result = post_stress_readout(
            read_programme(_entries(names)), TABULATED_SEQUENCE
        )
        self.assertEqual(result["unread"], ["mechanical-shock"])

    def test_a_programme_with_no_stress_has_nothing_unread(self):
        names = ["initial-visual-inspection", "initial-electrical-measurement"]
        result = post_stress_readout(
            read_programme(_entries(names)), TABULATED_SEQUENCE
        )
        self.assertEqual(result["stresses"], [])
        self.assertTrue(result["every_stress_read"])


class BasisAndSampleTests(unittest.TestCase):
    def test_a_sound_programme_runs_every_test_at_its_tabulated_basis(self):
        result = basis_and_sample(
            read_programme(_entries()), LOT_SIZE, 0.1, TABULATED_SEQUENCE
        )
        self.assertEqual(result["substituted"], [])
        self.assertEqual(result["short_units"], [])
        self.assertEqual(result["short_samples"], [])

    def test_an_every_unit_test_drawn_on_a_sample_is_a_substitution(self):
        rows = _entries(
            **{"final-visual-inspection": {"basis": "sampled", "units": 8}}
        )
        result = basis_and_sample(
            read_programme(rows), LOT_SIZE, 0.1, TABULATED_SEQUENCE
        )
        self.assertEqual(result["substituted"], ["final-visual-inspection"])

    def test_an_every_unit_test_short_of_the_lot_is_named(self):
        rows = _entries(**{"seal-leak-test": {"units": 38}})
        result = basis_and_sample(
            read_programme(rows), LOT_SIZE, 0.1, TABULATED_SEQUENCE
        )
        self.assertEqual(result["short_units"], ["seal-leak-test"])

    def test_a_sample_landing_exactly_on_the_floor_is_accepted(self):
        rows = _entries(**{"thermal-shock": {"units": 4}})
        result = basis_and_sample(
            read_programme(rows), LOT_SIZE, 0.1, TABULATED_SEQUENCE
        )
        row = [r for r in result["rows"] if r["test"] == "thermal-shock"][0]
        self.assertAlmostEqual(row["drawn_share"], 0.1, places=9)
        self.assertEqual(result["short_samples"], [])

    def test_a_sample_under_the_floor_is_named(self):
        rows = _entries(**{"mechanical-shock": {"units": 3}})
        result = basis_and_sample(
            read_programme(rows), LOT_SIZE, 0.1, TABULATED_SEQUENCE
        )
        self.assertEqual(result["short_samples"], ["mechanical-shock"])

    def test_a_sampled_test_run_on_every_unit_is_stricter_than_the_table(self):
        rows = _entries(
            **{"thermal-shock": {"basis": "every-unit", "units": LOT_SIZE}}
        )
        result = basis_and_sample(
            read_programme(rows), LOT_SIZE, 0.1, TABULATED_SEQUENCE
        )
        self.assertEqual(result["stricter_than_table"], ["thermal-shock"])
        self.assertEqual(result["short_units"], [])

    def test_more_units_than_the_lot_holds_is_refused(self):
        rows = _entries(**{"thermal-shock": {"units": LOT_SIZE + 1}})
        with self.assertRaises(ValueError):
            basis_and_sample(
                read_programme(rows), LOT_SIZE, 0.1, TABULATED_SEQUENCE
            )

    def test_an_empty_lot_is_refused(self):
        with self.assertRaises(ValueError):
            basis_and_sample(read_programme(_entries()), 0, 0.1, TABULATED_SEQUENCE)


class CompletenessTests(unittest.TestCase):
    def test_a_sound_programme_is_wholly_complete(self):
        ordered = read_programme(_entries())
        coverage = programme_coverage(ordered, TABULATED_SEQUENCE)
        basis = basis_and_sample(ordered, LOT_SIZE, 0.1, TABULATED_SEQUENCE)
        result = programme_completeness(coverage, basis, TABULATED_SEQUENCE)
        self.assertEqual(result["short"], [])
        self.assertAlmostEqual(result["completeness_share"], 1.0, places=9)

    def test_a_substituted_test_does_not_count_as_sound(self):
        rows = _entries(
            **{"final-visual-inspection": {"basis": "sampled", "units": 8}}
        )
        ordered = read_programme(rows)
        coverage = programme_coverage(ordered, TABULATED_SEQUENCE)
        basis = basis_and_sample(ordered, LOT_SIZE, 0.1, TABULATED_SEQUENCE)
        result = programme_completeness(coverage, basis, TABULATED_SEQUENCE)
        self.assertEqual(result["short"], ["final-visual-inspection"])
        self.assertAlmostEqual(
            result["completeness_share"],
            (len(TABULATED_SEQUENCE) - 1) / len(TABULATED_SEQUENCE),
            places=9,
        )


class RolledUpProgrammeTests(unittest.TestCase):
    def test_a_sound_programme_matches_the_table(self):
        result = assess_planar_blocking_diode_acceptance(_case())
        self.assertEqual(result["verdict"], AP_ACCEPTED)
        self.assertEqual(result["findings"], [])
        self.assertTrue(result["completeness_floor_met"])

    def test_a_mesa_part_falls_outside_the_table(self):
        result = assess_planar_blocking_diode_acceptance(
            _case(construction="mesa-blocking-diode")
        )
        self.assertEqual(result["verdict"], AP_OUT_OF_SCOPE)

    def test_a_missing_tabulated_test_leaves_the_programme_short(self):
        names = [n for n in TABULATED_SEQUENCE if n != "high-temperature-reverse-bias"]
        result = assess_planar_blocking_diode_acceptance(
            _case(entries=_entries(names))
        )
        self.assertEqual(result["verdict"], AP_INCOMPLETE)
        self.assertTrue(
            any("high-temperature-reverse-bias" in f for f in result["findings"])
        )

    def test_a_test_added_to_the_table_is_carried_on_project_authority(self):
        rows = _entries() + [
            {"test": "salt-fog", "basis": "sampled", "units": SAMPLE_UNITS}
        ]
        result = assess_planar_blocking_diode_acceptance(_case(entries=rows))
        self.assertEqual(result["verdict"], AP_INCOMPLETE)
        self.assertTrue(any("salt-fog" in f for f in result["findings"]))

    def test_a_stress_run_after_the_last_measurement_is_reported_unread(self):
        names = [
            "initial-visual-inspection",
            "initial-electrical-measurement",
            "intermediate-electrical-measurement",
            "seal-leak-test",
            "final-electrical-measurement",
            "final-visual-inspection",
            "thermal-shock",
            "high-temperature-reverse-bias",
            "mechanical-shock",
        ]
        result = assess_planar_blocking_diode_acceptance(
            _case(entries=_entries(names))
        )
        self.assertEqual(result["verdict"], AP_INCOMPLETE)
        self.assertTrue(
            any("without being read" in f for f in result["findings"])
        )

    def test_a_short_sample_leaves_the_programme_incomplete(self):
        rows = _entries(**{"mechanical-shock": {"units": 2}})
        result = assess_planar_blocking_diode_acceptance(_case(entries=rows))
        self.assertEqual(result["verdict"], AP_INCOMPLETE)
        self.assertFalse(result["completeness_floor_met"])

    def test_a_substituted_basis_leaves_the_programme_incomplete(self):
        rows = _entries(
            **{"initial-electrical-measurement": {"basis": "sampled", "units": 8}}
        )
        result = assess_planar_blocking_diode_acceptance(_case(entries=rows))
        self.assertEqual(result["verdict"], AP_INCOMPLETE)

    def test_a_stricter_basis_is_reported_and_still_accepted(self):
        rows = _entries(
            **{
                "high-temperature-reverse-bias": {
                    "basis": "every-unit",
                    "units": LOT_SIZE,
                }
            }
        )
        result = assess_planar_blocking_diode_acceptance(_case(entries=rows))
        self.assertEqual(result["verdict"], AP_ACCEPTED)
        self.assertTrue(any("stricter" in f for f in result["findings"]))

    def test_a_reduced_table_can_be_matched_by_a_shorter_programme(self):
        table = (
            "initial-visual-inspection",
            "initial-electrical-measurement",
            "thermal-shock",
            "final-electrical-measurement",
        )
        result = assess_planar_blocking_diode_acceptance(
            _case(entries=_entries(table), policy={"tabulated_sequence": table})
        )
        self.assertEqual(result["verdict"], AP_ACCEPTED)

    def test_the_verdict_rank_orders_the_three_outcomes(self):
        self.assertLess(AP_RANK[AP_OUT_OF_SCOPE], AP_RANK[AP_INCOMPLETE])
        self.assertLess(AP_RANK[AP_INCOMPLETE], AP_RANK[AP_ACCEPTED])

    def test_a_non_mapping_case_is_refused(self):
        with self.assertRaises(ValueError):
            assess_planar_blocking_diode_acceptance("run the tabulated tests")

    def test_a_programme_without_an_identifier_is_refused(self):
        with self.assertRaises(ValueError):
            assess_planar_blocking_diode_acceptance(_case(programme_id=""))


if __name__ == "__main__":
    unittest.main()
