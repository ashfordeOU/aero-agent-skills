#!/usr/bin/env python3
"""Contract test for the ECSS-Q-ST-60-05 clause 6.3.2 teardown leaf.

Offline, deterministic, stdlib unittest.
Run: python3 test_q6005_construction_analysis_of_sample_units.py
"""

import unittest

from q6005_construction_analysis_of_sample_units_logic import (
    ACCEPTANCE_INDEX,
    ADMISSIBLE_UNIT_SOURCES,
    DEVIATION_CATEGORIES,
    FAMILY_MINIMUM_UNITS,
    INADMISSIBLE_UNIT_SOURCES,
    MANDATORY_TEARDOWN_STEPS,
    SET_WIDE_UNIT_FRACTION,
    STEP_OUTCOME_CREDIT,
    TEARDOWN_STEP_WEIGHTS,
    TEARDOWN_TOLERANCE,
    VERDICTS,
    assess_construction_analysis,
    assess_step,
    build_conformity_index,
    categorize_deviation,
    family_minimum_units,
    inadmissible_units,
    normalize_step,
    normalize_units,
    outcome_credit,
    required_unit_count,
    step_weight,
    unit_coverage,
    unit_source_is_admissible,
)

FAMILY = "thick-film-hybrid"
SPARE_STEP = "marking-and-identification-check"

DECLARED = {
    "production_lots": ["L-1", "L-2"],
    "design_variants": ["V-A"],
    "build_standards": ["BS-3"],
}


def unit(unit_id, lot="L-1", variant="V-A", build="BS-3", source="serial-production-run"):
    """One unit torn down and the build it speaks for."""
    return {
        "unit_id": unit_id,
        "production_lot": lot,
        "design_variant": variant,
        "build_standard": build,
        "source": source,
    }


def representative_units():
    """A unit set that meets the family floor and spans every declaration."""
    return [unit("U-1", lot="L-1"), unit("U-2", lot="L-2"), unit("U-3", lot="L-1")]


def performed_steps(**outcomes):
    """Every teardown step matching the declared build, with named exceptions."""
    steps = []
    for name in sorted(TEARDOWN_STEP_WEIGHTS):
        entry = {"step": name, "outcome": "matches-declared-build"}
        if name in outcomes:
            entry["outcome"] = outcomes[name]
        steps.append(entry)
    return steps


def deviation(**overrides):
    """A cosmetic observation on a single unit."""
    item = {
        "deviation_id": "DV-1",
        "outside_declared_build_standard": False,
        "affects_attach_or_bond_integrity": False,
        "dimensional_or_cosmetic_only": True,
        "observed_on_units": 1,
    }
    item.update(overrides)
    return item


def run(**overrides):
    """Grade one teardown case."""
    case = {
        "product_id": "HYB-01",
        "family": FAMILY,
        "declared": DECLARED,
        "units": representative_units(),
        "steps": performed_steps(),
        "deviations": (),
    }
    case.update(overrides)
    return assess_construction_analysis(**case)


class UnitSizingTests(unittest.TestCase):
    def test_every_family_carries_a_published_floor(self):
        for family in FAMILY_MINIMUM_UNITS:
            self.assertGreaterEqual(family_minimum_units(family), 1)

    def test_an_unknown_product_family_is_rejected(self):
        with self.assertRaises(ValueError):
            family_minimum_units("printed-circuit-assembly")

    def test_the_family_floor_governs_when_few_lots_are_declared(self):
        self.assertEqual(required_unit_count(FAMILY, 1, 1), FAMILY_MINIMUM_UNITS[FAMILY])

    def test_declared_lots_beyond_the_floor_raise_the_required_count(self):
        self.assertEqual(required_unit_count(FAMILY, 5, 1), 5)

    def test_declared_variants_beyond_the_floor_raise_the_required_count(self):
        self.assertEqual(required_unit_count(FAMILY, 1, 6), 6)

    def test_a_zero_lot_count_is_rejected(self):
        with self.assertRaises(ValueError):
            required_unit_count(FAMILY, 0, 1)


class UnitSourceTests(unittest.TestCase):
    def test_a_production_run_source_can_carry_the_analysis(self):
        for source in ADMISSIBLE_UNIT_SOURCES:
            self.assertTrue(unit_source_is_admissible(source))

    def test_a_bench_build_source_cannot_carry_the_analysis(self):
        for source in INADMISSIBLE_UNIT_SOURCES:
            self.assertFalse(unit_source_is_admissible(source))

    def test_an_unknown_source_is_an_input_error_not_a_silent_pass(self):
        with self.assertRaises(ValueError):
            unit_source_is_admissible("somewhere-on-the-shelf")

    def test_an_engineering_build_unit_is_named_in_the_rejected_set(self):
        units = representative_units() + [unit("U-4", source="engineering-build")]
        self.assertEqual(inadmissible_units(units), ["U-4"])


class UnitSetTests(unittest.TestCase):
    def test_a_repeated_unit_identifier_is_rejected(self):
        units = representative_units() + [unit("U-1")]
        with self.assertRaises(ValueError):
            normalize_units(units)

    def test_a_unit_that_names_no_build_standard_is_rejected(self):
        bad = unit("U-4")
        del bad["build_standard"]
        with self.assertRaises(ValueError):
            normalize_units([bad])

    def test_a_unit_record_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            normalize_units(["U-1"])

    def test_a_representative_set_leaves_nothing_uncovered(self):
        self.assertEqual(unit_coverage(representative_units(), DECLARED), [])

    def test_a_declared_lot_no_unit_came_from_is_reported(self):
        units = [unit("U-1"), unit("U-2"), unit("U-3")]
        self.assertEqual(unit_coverage(units, DECLARED), ["production-lot:L-2"])

    def test_a_lot_represented_only_by_a_bench_unit_stays_uncovered(self):
        units = [unit("U-1"), unit("U-2"), unit("U-3", lot="L-2", source="engineering-build")]
        self.assertIn("production-lot:L-2", unit_coverage(units, DECLARED))

    def test_an_empty_declared_list_is_rejected(self):
        declared = dict(DECLARED, build_standards=[])
        with self.assertRaises(ValueError):
            unit_coverage(representative_units(), declared)


class TeardownStepTests(unittest.TestCase):
    def test_every_mandatory_step_carries_a_published_weight(self):
        for name in MANDATORY_TEARDOWN_STEPS:
            self.assertIn(name, TEARDOWN_STEP_WEIGHTS)

    def test_an_unknown_step_name_is_rejected(self):
        with self.assertRaises(ValueError):
            step_weight("shake-it-and-listen")

    def test_an_unknown_step_outcome_is_rejected(self):
        with self.assertRaises(ValueError):
            outcome_credit("looked-fine")

    def test_a_step_defaults_to_not_performed_when_nobody_named_an_outcome(self):
        self.assertEqual(normalize_step({"step": SPARE_STEP})["outcome"], "step-not-performed")

    def test_a_matching_step_earns_its_full_weight(self):
        record = assess_step({"step": SPARE_STEP, "outcome": "matches-declared-build"})
        self.assertAlmostEqual(
            record["weighted_credit"], TEARDOWN_STEP_WEIGHTS[SPARE_STEP], places=9
        )
        self.assertEqual(record["findings"], [])

    def test_a_skipped_mandatory_step_is_marked_missing(self):
        record = assess_step(
            {"step": "cross-section-preparation-and-review", "outcome": "step-not-performed"}
        )
        self.assertTrue(record["mandatory_missing"])
        self.assertIn("mandatory-teardown-step-not-performed", record["findings"])

    def test_a_skipped_optional_step_is_a_finding_but_not_a_missing_mandatory(self):
        record = assess_step({"step": SPARE_STEP, "outcome": "step-not-performed"})
        self.assertFalse(record["mandatory_missing"])
        self.assertIn("step-not-performed", record["findings"])

    def test_a_full_teardown_reaches_a_full_index(self):
        records = [assess_step(entry) for entry in performed_steps()]
        self.assertAlmostEqual(build_conformity_index(records), 1.0, places=9)

    def test_an_empty_step_set_is_rejected(self):
        with self.assertRaises(ValueError):
            build_conformity_index([])


class DeviationSeverityTests(unittest.TestCase):
    def test_every_returned_category_is_published(self):
        self.assertIn(categorize_deviation(deviation(), 3), DEVIATION_CATEGORIES)

    def test_construction_outside_the_declared_build_is_critical_on_one_unit(self):
        severity = categorize_deviation(
            deviation(outside_declared_build_standard=True, dimensional_or_cosmetic_only=False),
            4,
        )
        self.assertEqual(severity, "critical-build-deviation")

    def test_an_attach_deviation_spanning_the_set_is_critical(self):
        severity = categorize_deviation(
            deviation(
                affects_attach_or_bond_integrity=True,
                dimensional_or_cosmetic_only=False,
                observed_on_units=2,
            ),
            4,
        )
        self.assertEqual(severity, "critical-build-deviation")

    def test_an_attach_deviation_on_a_minority_is_major_not_critical(self):
        severity = categorize_deviation(
            deviation(
                affects_attach_or_bond_integrity=True,
                dimensional_or_cosmetic_only=False,
                observed_on_units=1,
            ),
            4,
        )
        self.assertEqual(severity, "major-build-deviation")

    def test_cosmetic_workmanship_on_a_minority_is_minor(self):
        self.assertEqual(categorize_deviation(deviation(), 4), "minor-build-deviation")

    def test_cosmetic_workmanship_across_the_set_is_no_longer_minor(self):
        severity = categorize_deviation(deviation(observed_on_units=3), 4)
        self.assertEqual(severity, "major-build-deviation")

    def test_the_set_wide_bound_is_met_exactly_at_half_the_units(self):
        self.assertAlmostEqual(SET_WIDE_UNIT_FRACTION, 0.5, places=9)
        self.assertEqual(
            categorize_deviation(deviation(observed_on_units=2), 4), "major-build-deviation"
        )

    def test_a_deviation_seen_on_more_units_than_exist_is_rejected(self):
        with self.assertRaises(ValueError):
            categorize_deviation(deviation(observed_on_units=5), 4)

    def test_a_deviation_missing_a_required_flag_is_rejected(self):
        bad = deviation()
        del bad["affects_attach_or_bond_integrity"]
        with self.assertRaises(ValueError):
            categorize_deviation(bad, 4)


class WholeAnalysisTests(unittest.TestCase):
    def test_a_clean_teardown_confirms_the_declared_build(self):
        result = run()
        self.assertEqual(result["verdict"], "construction-confirms-declared-build")
        self.assertTrue(result["build_confirmed"])
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["build_conformity_index"], 1.0, places=9)

    def test_every_verdict_returned_is_one_of_the_published_verdicts(self):
        self.assertIn(run()["verdict"], VERDICTS)

    def test_a_bench_built_unit_makes_the_analysis_incomplete(self):
        units = representative_units()
        units[2]["source"] = "engineering-build"
        result = run(units=units)
        self.assertEqual(result["verdict"], "construction-analysis-incomplete")
        self.assertEqual(result["rejected_units"], ["U-3"])

    def test_a_short_unit_set_makes_the_analysis_incomplete(self):
        result = run(units=[unit("U-1"), unit("U-2", lot="L-2")])
        self.assertEqual(result["verdict"], "construction-analysis-incomplete")
        self.assertIn(
            "unit-count-below-minimum", [f["finding"] for f in result["findings"]]
        )

    def test_a_skipped_cross_section_makes_the_analysis_incomplete(self):
        steps = performed_steps(**{"cross-section-preparation-and-review": "step-not-performed"})
        result = run(steps=steps)
        self.assertEqual(result["verdict"], "construction-analysis-incomplete")

    def test_a_critical_deviation_denies_the_build_on_a_complete_teardown(self):
        result = run(
            deviations=[
                deviation(
                    outside_declared_build_standard=True, dimensional_or_cosmetic_only=False
                )
            ]
        )
        self.assertEqual(result["verdict"], "construction-does-not-confirm-declared-build")
        self.assertFalse(result["build_confirmed"])

    def test_a_minor_deviation_leaves_the_build_confirmed_with_open_actions(self):
        result = run(deviations=[deviation()])
        self.assertEqual(result["verdict"], "construction-confirms-build-with-open-actions")
        self.assertTrue(result["build_confirmed"])

    def test_a_low_index_denies_the_build_even_with_no_deviation_listed(self):
        steps = performed_steps(
            **{
                "external-visual-and-dimensional-check": "major-deviation",
                "materials-and-finish-verification": "major-deviation",
                "internal-dimension-measurement": "major-deviation",
            }
        )
        result = run(steps=steps)
        self.assertLess(result["build_conformity_index"], ACCEPTANCE_INDEX)
        self.assertEqual(result["verdict"], "construction-does-not-confirm-declared-build")

    def test_a_step_nobody_mentioned_is_graded_as_not_performed(self):
        result = run(steps=[{"step": SPARE_STEP, "outcome": "matches-declared-build"}])
        outcomes = {r["step"]: r["outcome"] for r in result["step_records"]}
        self.assertEqual(outcomes["internal-visual-examination"], "step-not-performed")
        self.assertEqual(len(result["step_records"]), len(TEARDOWN_STEP_WEIGHTS))

    def test_a_repeated_teardown_step_is_rejected(self):
        steps = performed_steps() + [{"step": SPARE_STEP, "outcome": "matches-declared-build"}]
        with self.assertRaises(ValueError):
            run(steps=steps)

    def test_a_non_sequence_step_argument_is_rejected(self):
        with self.assertRaises(ValueError):
            run(steps={"step": SPARE_STEP})

    def test_a_blank_product_identifier_is_rejected(self):
        with self.assertRaises(ValueError):
            run(product_id="   ")


class ConstantsTests(unittest.TestCase):
    def test_the_tolerance_is_small_enough_to_separate_the_bounds(self):
        self.assertLess(TEARDOWN_TOLERANCE, 1e-6)

    def test_the_step_credits_span_the_published_scale(self):
        self.assertAlmostEqual(max(STEP_OUTCOME_CREDIT.values()), 1.0, places=9)
        self.assertAlmostEqual(min(STEP_OUTCOME_CREDIT.values()), 0.0, places=9)

    def test_the_acceptance_index_sits_under_a_full_teardown(self):
        self.assertLess(ACCEPTANCE_INDEX, 1.0)


if __name__ == "__main__":
    unittest.main()
