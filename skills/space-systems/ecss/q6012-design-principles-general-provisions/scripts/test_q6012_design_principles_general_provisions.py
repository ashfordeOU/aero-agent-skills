"""Contract tests for the clause 7.1.2 baseline design-provision logic."""

import unittest

from q6012_design_principles_general_provisions_logic import (
    BAND_TOLERANCE_GHZ,
    CANONICAL_STAGES,
    MANDATORY_PROVISIONS,
    STATE_HELD,
    STATE_NOT_APPLICABLE,
    STATE_NOT_HELD,
    STATE_UNDECLARED,
    assess_general_provisions,
    band_coverage,
    derating_margin_c,
    first_lapse,
    missing_mandatory_provisions,
    normalise_stage,
    provision_coverage,
    validate_provision,
    validate_stage_sequence,
)

FULL_EFFORT = list(CANONICAL_STAGES)


def held_everywhere(ident, stages=None):
    """A provision held at every stage it applies from."""
    entry = MANDATORY_PROVISIONS[ident]
    stages = stages or FULL_EFFORT
    start = CANONICAL_STAGES.index(entry)
    return {
        "id": ident,
        "applies_from": entry,
        "mandatory": True,
        "evidence": "DDR-%s-01" % ident[:4],
        "stage_status": {
            s: True for s in stages if CANONICAL_STAGES.index(s) >= start
        },
    }


def clean_spec(**overrides):
    spec = {
        "stages": list(FULL_EFFORT),
        "provisions": [held_everywhere(i) for i in sorted(MANDATORY_PROVISIONS)],
        "operating_band_ghz": (27.5, 31.0),
        "model_band_ghz": (18.0, 40.0),
        "junction_temperature_c": 105.0,
        "derating_limit_c": 125.0,
    }
    spec.update(overrides)
    return spec


class NormaliseStageTests(unittest.TestCase):
    def test_canonical_name_passes_through(self):
        self.assertEqual(normalise_stage("layout"), "layout")

    def test_case_and_separators_normalised(self):
        self.assertEqual(normalise_stage("  Schematic_Design "), "schematic-design")

    def test_spaces_become_hyphens(self):
        self.assertEqual(normalise_stage("design freeze"), "design-freeze")

    def test_unknown_stage_rejected(self):
        with self.assertRaises(ValueError):
            normalise_stage("tape-out")

    def test_empty_stage_rejected(self):
        with self.assertRaises(ValueError):
            normalise_stage("   ")

    def test_non_string_stage_rejected(self):
        with self.assertRaises(ValueError):
            normalise_stage(3)


class StageSequenceTests(unittest.TestCase):
    def test_full_effort_accepted(self):
        self.assertEqual(validate_stage_sequence(FULL_EFFORT), CANONICAL_STAGES)

    def test_subset_in_order_accepted(self):
        self.assertEqual(
            validate_stage_sequence(["specification", "layout", "design-freeze"]),
            ("specification", "layout", "design-freeze"),
        )

    def test_out_of_order_sequence_rejected(self):
        with self.assertRaises(ValueError):
            validate_stage_sequence(["layout", "architecture"])

    def test_duplicate_stage_rejected(self):
        with self.assertRaises(ValueError):
            validate_stage_sequence(["layout", "layout"])

    def test_empty_sequence_rejected(self):
        with self.assertRaises(ValueError):
            validate_stage_sequence([])

    def test_non_sequence_rejected(self):
        with self.assertRaises(ValueError):
            validate_stage_sequence("specification")


class ValidateProvisionTests(unittest.TestCase):
    def test_known_provision_infers_entry_stage(self):
        record = validate_provision({"id": "layout-rule-compliance"})
        self.assertEqual(record["applies_from"], "layout")
        self.assertTrue(record["mandatory"])

    def test_identifier_normalised(self):
        record = validate_provision({"id": " Lifetime_Baseline "})
        self.assertEqual(record["id"], "lifetime-baseline")

    def test_unknown_provision_needs_explicit_entry_stage(self):
        with self.assertRaises(ValueError):
            validate_provision({"id": "esd-handling-baseline"})

    def test_unknown_provision_accepted_with_entry_stage(self):
        record = validate_provision(
            {"id": "esd-handling-baseline", "applies_from": "layout"}
        )
        self.assertEqual(record["applies_from"], "layout")
        self.assertFalse(record["mandatory"])

    def test_non_boolean_status_rejected(self):
        with self.assertRaises(ValueError):
            validate_provision(
                {"id": "lifetime-baseline", "stage_status": {"layout": "yes"}}
            )

    def test_empty_identifier_rejected(self):
        with self.assertRaises(ValueError):
            validate_provision({"id": "  "})

    def test_non_mapping_provision_rejected(self):
        with self.assertRaises(ValueError):
            validate_provision(["lifetime-baseline"])


class CoverageMatrixTests(unittest.TestCase):
    def test_stages_before_entry_are_not_applicable(self):
        row = provision_coverage(held_everywhere("layout-rule-compliance"), FULL_EFFORT)
        self.assertEqual(row["specification"], STATE_NOT_APPLICABLE)
        self.assertEqual(row["architecture"], STATE_NOT_APPLICABLE)

    def test_declared_true_reads_held(self):
        row = provision_coverage(held_everywhere("lifetime-baseline"), FULL_EFFORT)
        self.assertEqual(row["design-freeze"], STATE_HELD)

    def test_declared_false_reads_not_held(self):
        provision = held_everywhere("lifetime-baseline")
        provision["stage_status"]["verification"] = False
        row = provision_coverage(provision, FULL_EFFORT)
        self.assertEqual(row["verification"], STATE_NOT_HELD)

    def test_applicable_but_unassessed_reads_undeclared(self):
        provision = held_everywhere("lifetime-baseline")
        del provision["stage_status"]["layout"]
        row = provision_coverage(provision, FULL_EFFORT)
        self.assertEqual(row["layout"], STATE_UNDECLARED)

    def test_undeclared_is_distinct_from_not_held(self):
        provision = held_everywhere("lifetime-baseline")
        del provision["stage_status"]["layout"]
        provision["stage_status"]["verification"] = False
        row = provision_coverage(provision, FULL_EFFORT)
        self.assertNotEqual(row["layout"], row["verification"])


class FirstLapseTests(unittest.TestCase):
    def test_no_lapse_when_held_throughout(self):
        self.assertIsNone(first_lapse(held_everywhere("lifetime-baseline"), FULL_EFFORT))

    def test_earliest_failing_stage_reported_not_the_freeze(self):
        provision = held_everywhere("lifetime-baseline")
        provision["stage_status"]["architecture"] = False
        provision["stage_status"]["design-freeze"] = False
        self.assertEqual(first_lapse(provision, FULL_EFFORT), "architecture")

    def test_undeclared_stage_counts_as_a_lapse(self):
        provision = held_everywhere("thermal-derating-baseline")
        del provision["stage_status"]["schematic-design"]
        self.assertEqual(first_lapse(provision, FULL_EFFORT), "schematic-design")

    def test_lapse_before_entry_stage_is_not_possible(self):
        provision = held_everywhere("layout-rule-compliance")
        self.assertIsNone(first_lapse(provision, FULL_EFFORT))


class BandCoverageTests(unittest.TestCase):
    def test_band_inside_model_span(self):
        result = band_coverage((27.5, 31.0), (18.0, 40.0))
        self.assertTrue(result["inside"])
        self.assertAlmostEqual(result["low_margin_ghz"], 9.5, places=9)
        self.assertAlmostEqual(result["high_margin_ghz"], 9.0, places=9)

    def test_band_exactly_on_both_edges_is_inside(self):
        result = band_coverage((18.0, 40.0), (18.0, 40.0))
        self.assertTrue(result["inside"])
        self.assertAlmostEqual(result["low_margin_ghz"], 0.0, places=9)
        self.assertAlmostEqual(result["high_margin_ghz"], 0.0, places=9)

    def test_band_reaching_above_the_model_span_is_outside(self):
        result = band_coverage((30.0, 44.0), (18.0, 40.0))
        self.assertFalse(result["inside"])

    def test_band_below_the_model_span_is_outside(self):
        result = band_coverage((12.0, 30.0), (18.0, 40.0))
        self.assertFalse(result["inside"])

    def test_edge_overshoot_inside_the_tolerance_is_absorbed(self):
        result = band_coverage((18.0 - BAND_TOLERANCE_GHZ / 2.0, 40.0), (18.0, 40.0))
        self.assertTrue(result["inside"])

    def test_inverted_operating_band_rejected(self):
        with self.assertRaises(ValueError):
            band_coverage((31.0, 27.5), (18.0, 40.0))

    def test_degenerate_model_span_rejected(self):
        with self.assertRaises(ValueError):
            band_coverage((27.5, 31.0), (40.0, 40.0))

    def test_non_pair_band_rejected(self):
        with self.assertRaises(ValueError):
            band_coverage((27.5,), (18.0, 40.0))


class DeratingMarginTests(unittest.TestCase):
    def test_margin_is_limit_minus_junction(self):
        self.assertAlmostEqual(derating_margin_c(105.0, 125.0), 20.0, places=9)

    def test_exceedance_is_negative(self):
        self.assertAlmostEqual(derating_margin_c(140.0, 125.0), -15.0, places=9)

    def test_exactly_on_the_limit_is_zero(self):
        self.assertAlmostEqual(derating_margin_c(125.0, 125.0), 0.0, places=9)

    def test_sub_absolute_zero_rejected(self):
        with self.assertRaises(ValueError):
            derating_margin_c(-300.0, 125.0)

    def test_non_numeric_limit_rejected(self):
        with self.assertRaises(ValueError):
            derating_margin_c(105.0, "125")


class MissingProvisionTests(unittest.TestCase):
    def test_full_set_leaves_nothing_missing(self):
        provisions = [held_everywhere(i) for i in sorted(MANDATORY_PROVISIONS)]
        self.assertEqual(missing_mandatory_provisions(provisions), [])

    def test_dropped_provision_is_reported(self):
        provisions = [
            held_everywhere(i)
            for i in sorted(MANDATORY_PROVISIONS)
            if i != "radiation-environment-baseline"
        ]
        self.assertEqual(
            missing_mandatory_provisions(provisions),
            ["radiation-environment-baseline"],
        )

    def test_non_sequence_rejected(self):
        with self.assertRaises(ValueError):
            missing_mandatory_provisions({"id": "lifetime-baseline"})


class AssessGeneralProvisionsTests(unittest.TestCase):
    def test_clean_effort_establishes_the_baseline(self):
        result = assess_general_provisions(clean_spec())
        self.assertTrue(result["baseline_established"])
        self.assertEqual(result["findings"], [])

    def test_missing_mandatory_provision_breaks_the_baseline(self):
        provisions = [
            held_everywhere(i)
            for i in sorted(MANDATORY_PROVISIONS)
            if i != "lifetime-baseline"
        ]
        result = assess_general_provisions(clean_spec(provisions=provisions))
        self.assertFalse(result["baseline_established"])
        self.assertIn("lifetime-baseline", result["missing_mandatory"])

    def test_mid_effort_lapse_names_the_stage_it_started_at(self):
        provisions = [held_everywhere(i) for i in sorted(MANDATORY_PROVISIONS)]
        for provision in provisions:
            if provision["id"] == "lifetime-baseline":
                provision["stage_status"]["schematic-design"] = False
        result = assess_general_provisions(clean_spec(provisions=provisions))
        self.assertFalse(result["baseline_established"])
        self.assertEqual(result["first_lapse"]["lifetime-baseline"], "schematic-design")

    def test_status_declared_before_the_entry_stage_is_not_a_lapse(self):
        provisions = [held_everywhere(i) for i in sorted(MANDATORY_PROVISIONS)]
        for provision in provisions:
            if provision["id"] == "layout-rule-compliance":
                provision["stage_status"]["architecture"] = False
        result = assess_general_provisions(clean_spec(provisions=provisions))
        self.assertEqual(
            result["coverage"]["layout-rule-compliance"]["architecture"],
            STATE_NOT_APPLICABLE,
        )
        self.assertTrue(result["baseline_established"])

    def test_optional_provision_lapse_does_not_break_the_baseline(self):
        provisions = [held_everywhere(i) for i in sorted(MANDATORY_PROVISIONS)]
        provisions.append(
            {
                "id": "esd-handling-baseline",
                "applies_from": "layout",
                "mandatory": False,
                "stage_status": {"layout": False},
            }
        )
        result = assess_general_provisions(clean_spec(provisions=provisions))
        self.assertTrue(result["baseline_established"])
        self.assertTrue(any("esd-handling-baseline" in f for f in result["findings"]))

    def test_band_outside_the_model_span_breaks_the_baseline(self):
        result = assess_general_provisions(
            clean_spec(operating_band_ghz=(27.5, 44.0))
        )
        self.assertFalse(result["baseline_established"])
        self.assertFalse(result["band"]["inside"])

    def test_junction_over_the_derating_limit_breaks_the_baseline(self):
        result = assess_general_provisions(clean_spec(junction_temperature_c=140.0))
        self.assertFalse(result["baseline_established"])
        self.assertFalse(result["thermal_baseline_held"])

    def test_junction_exactly_on_the_limit_still_holds(self):
        result = assess_general_provisions(clean_spec(junction_temperature_c=125.0))
        self.assertAlmostEqual(result["derating_margin_c"], 0.0, places=9)
        self.assertTrue(result["thermal_baseline_held"])
        self.assertTrue(result["baseline_established"])

    def test_missing_evidence_reference_is_a_finding(self):
        provisions = [held_everywhere(i) for i in sorted(MANDATORY_PROVISIONS)]
        provisions[2]["evidence"] = None
        result = assess_general_provisions(clean_spec(provisions=provisions))
        self.assertTrue(
            any("no evidence reference" in f for f in result["findings"])
        )

    def test_short_stage_list_only_grades_the_stages_declared(self):
        stages = ["specification", "architecture"]
        provisions = [held_everywhere(i, stages) for i in sorted(MANDATORY_PROVISIONS)]
        result = assess_general_provisions(
            clean_spec(stages=stages, provisions=provisions)
        )
        self.assertEqual(result["stages"], stages)
        self.assertNotIn("layout", result["coverage"]["lifetime-baseline"])
        self.assertTrue(result["baseline_established"])

    def test_duplicate_provision_rejected(self):
        provisions = [held_everywhere(i) for i in sorted(MANDATORY_PROVISIONS)]
        provisions.append(held_everywhere("lifetime-baseline"))
        with self.assertRaises(ValueError):
            assess_general_provisions(clean_spec(provisions=provisions))

    def test_empty_provision_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_general_provisions(clean_spec(provisions=[]))

    def test_missing_spec_key_rejected(self):
        spec = clean_spec()
        del spec["derating_limit_c"]
        with self.assertRaises(ValueError):
            assess_general_provisions(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_general_provisions(["stages"])


if __name__ == "__main__":
    unittest.main()
