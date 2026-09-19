"""Contract tests for the clause 5.3/5.4 qualification-path logic."""

import unittest

from e3102_qualification_process_selection_logic import (
    FULL_PROGRAMME_INDEX,
    MODIFICATION_CATEGORIES,
    assess_qualification_process,
    categorize_modification,
    delta_test_scope,
    determine_qualification_path,
    envelope_exceedances,
    fundamental_modifications,
    modification_extent_index,
    validate_envelope,
    validate_heritage,
)

QUALIFIED_ENVELOPE = {
    "operating-temperature-c": (-40.0, 60.0),
    "transport-power-w": (0.0, 150.0),
    "adverse-tilt-mm": (0.0, 5.0),
}

HERITAGE = {
    "qualified": True,
    "evidence_complete": True,
    "envelope": QUALIFIED_ENVELOPE,
}


def heritage(**overrides):
    record = {
        "qualified": True,
        "evidence_complete": True,
        "envelope": dict(QUALIFIED_ENVELOPE),
    }
    record.update(overrides)
    return record


class ValidateEnvelopeTests(unittest.TestCase):
    def test_returns_float_pairs(self):
        out = validate_envelope({"operating-temperature-c": (-40, 60)})
        self.assertEqual(out, {"operating-temperature-c": (-40.0, 60.0)})

    def test_empty_envelope_rejected(self):
        with self.assertRaises(ValueError):
            validate_envelope({})

    def test_inverted_span_rejected(self):
        with self.assertRaises(ValueError):
            validate_envelope({"transport-power-w": (150.0, 10.0)})

    def test_malformed_span_rejected(self):
        with self.assertRaises(ValueError):
            validate_envelope({"transport-power-w": (150.0,)})

    def test_non_numeric_bound_rejected(self):
        with self.assertRaises(ValueError):
            validate_envelope({"transport-power-w": ("0", 150.0)})


class ValidateHeritageTests(unittest.TestCase):
    def test_accepts_a_complete_record(self):
        record = validate_heritage(HERITAGE)
        self.assertTrue(record["qualified"])
        self.assertEqual(record["envelope"]["adverse-tilt-mm"], (0.0, 5.0))

    def test_missing_key_rejected(self):
        with self.assertRaises(ValueError):
            validate_heritage({"qualified": True, "envelope": QUALIFIED_ENVELOPE})

    def test_non_boolean_flag_rejected(self):
        with self.assertRaises(ValueError):
            validate_heritage(heritage(qualified="yes"))

    def test_non_mapping_rejected(self):
        with self.assertRaises(ValueError):
            validate_heritage(["qualified"])


class EnvelopeExceedanceTests(unittest.TestCase):
    def test_inside_envelope_is_clean(self):
        self.assertEqual(
            envelope_exceedances(QUALIFIED_ENVELOPE, {"transport-power-w": (0.0, 120.0)}),
            [],
        )

    def test_equal_to_the_bound_is_inside(self):
        self.assertEqual(
            envelope_exceedances(QUALIFIED_ENVELOPE, {"transport-power-w": (0.0, 150.0)}),
            [],
        )

    def test_above_the_bound_is_reported(self):
        out = envelope_exceedances(QUALIFIED_ENVELOPE, {"transport-power-w": (0.0, 180.0)})
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["parameter"], "transport-power-w")

    def test_below_the_bound_is_reported(self):
        out = envelope_exceedances(
            QUALIFIED_ENVELOPE, {"operating-temperature-c": (-60.0, 20.0)}
        )
        self.assertEqual(len(out), 1)

    def test_uncovered_parameter_is_an_exceedance(self):
        out = envelope_exceedances(QUALIFIED_ENVELOPE, {"radiation-dose-krad": (0.0, 10.0)})
        self.assertEqual(len(out), 1)
        self.assertIsNone(out[0]["qualified"])

    def test_several_parameters_all_reported(self):
        out = envelope_exceedances(
            QUALIFIED_ENVELOPE,
            {"transport-power-w": (0.0, 200.0), "adverse-tilt-mm": (0.0, 9.0)},
        )
        self.assertEqual(len(out), 2)


class ModificationCategoryTests(unittest.TestCase):
    def test_known_category_resolves(self):
        entry = categorize_modification("groove-geometry")
        self.assertEqual(entry["weight"], MODIFICATION_CATEGORIES["groove-geometry"]["weight"])
        self.assertFalse(entry["fundamental"])

    def test_category_name_is_case_insensitive(self):
        self.assertEqual(categorize_modification("Working-Fluid")["category"], "working-fluid")

    def test_unknown_category_rejected(self):
        with self.assertRaises(ValueError):
            categorize_modification("repaint-the-saddle")

    def test_empty_category_rejected(self):
        with self.assertRaises(ValueError):
            categorize_modification("   ")

    def test_working_fluid_is_fundamental(self):
        self.assertEqual(fundamental_modifications(["working-fluid"]), ["working-fluid"])

    def test_dimension_change_is_not_fundamental(self):
        self.assertEqual(fundamental_modifications(["length-increase"]), [])

    def test_extent_index_sums_the_weights(self):
        expected = (
            MODIFICATION_CATEGORIES["length-increase"]["weight"]
            + MODIFICATION_CATEGORIES["interface-saddle"]["weight"]
        )
        self.assertEqual(
            modification_extent_index(["length-increase", "interface-saddle"]), expected
        )

    def test_repeated_category_counts_once(self):
        single = modification_extent_index(["length-increase"])
        self.assertEqual(modification_extent_index(["length-increase"] * 3), single)

    def test_no_modifications_scores_zero(self):
        self.assertEqual(modification_extent_index(None), 0)

    def test_scope_is_the_union(self):
        scope = delta_test_scope(["length-increase", "interface-saddle"])
        self.assertIn("tilt-sensitivity", scope)
        self.assertIn("thermal-interface", scope)
        self.assertEqual(scope, sorted(set(scope)))

    def test_non_sequence_modifications_rejected(self):
        with self.assertRaises(ValueError):
            modification_extent_index("length-increase")


class PathDecisionTests(unittest.TestCase):
    def test_unchanged_item_inside_envelope_needs_nothing(self):
        out = determine_qualification_path(HERITAGE, {"transport-power-w": (0.0, 100.0)})
        self.assertEqual(out["path"], "none")
        self.assertEqual(out["reasons"], [])

    def test_minor_modification_goes_delta(self):
        out = determine_qualification_path(
            HERITAGE, {"transport-power-w": (0.0, 100.0)}, ["interface-saddle"]
        )
        self.assertEqual(out["path"], "delta")

    def test_fundamental_modification_goes_full(self):
        out = determine_qualification_path(
            HERITAGE, {"transport-power-w": (0.0, 100.0)}, ["wick-type"]
        )
        self.assertEqual(out["path"], "full")
        self.assertIn("wick-type", out["fundamental_modifications"])

    def test_envelope_exceedance_goes_full(self):
        out = determine_qualification_path(
            HERITAGE, {"transport-power-w": (0.0, 400.0)}, ["interface-saddle"]
        )
        self.assertEqual(out["path"], "full")

    def test_missing_predecessor_goes_full(self):
        out = determine_qualification_path(
            heritage(qualified=False), {"transport-power-w": (0.0, 10.0)}
        )
        self.assertEqual(out["path"], "full")

    def test_incomplete_evidence_goes_full(self):
        out = determine_qualification_path(
            heritage(evidence_complete=False), {"transport-power-w": (0.0, 10.0)}
        )
        self.assertEqual(out["path"], "full")

    def test_accumulated_minor_changes_reach_the_threshold(self):
        mods = ["envelope-diameter", "fluid-charge-mass", "reservoir-volume"]
        self.assertGreaterEqual(modification_extent_index(mods), FULL_PROGRAMME_INDEX)
        out = determine_qualification_path(HERITAGE, {"transport-power-w": (0.0, 100.0)}, mods)
        self.assertEqual(out["path"], "full")

    def test_just_below_the_threshold_stays_delta(self):
        mods = ["groove-geometry", "length-increase"]
        self.assertLess(modification_extent_index(mods), FULL_PROGRAMME_INDEX)
        out = determine_qualification_path(HERITAGE, {"transport-power-w": (0.0, 100.0)}, mods)
        self.assertEqual(out["path"], "delta")


class AssessmentTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "heritage": heritage(),
            "application_envelope": {"transport-power-w": (0.0, 100.0)},
            "modifications": ["groove-geometry"],
        }
        spec.update(overrides)
        return spec

    def test_delta_scope_is_the_modification_scope(self):
        out = assess_qualification_process(self._spec())
        self.assertEqual(out["path"], "delta")
        self.assertEqual(out["test_scope"], delta_test_scope(["groove-geometry"]))

    def test_full_scope_covers_the_baseline_items(self):
        out = assess_qualification_process(self._spec(modifications=["working-fluid"]))
        self.assertEqual(out["path"], "full")
        for item in ("proof-pressure", "burst-pressure", "leak-rate", "life-test"):
            self.assertIn(item, out["test_scope"])

    def test_no_change_gives_an_empty_scope(self):
        out = assess_qualification_process(self._spec(modifications=[]))
        self.assertEqual(out["path"], "none")
        self.assertEqual(out["test_scope"], [])

    def test_heritage_usable_flag_tracks_the_path(self):
        self.assertTrue(assess_qualification_process(self._spec())["heritage_usable"])
        self.assertFalse(
            assess_qualification_process(self._spec(modifications=["envelope-material"]))[
                "heritage_usable"
            ]
        )

    def test_missing_key_rejected(self):
        spec = self._spec()
        del spec["application_envelope"]
        with self.assertRaises(ValueError):
            assess_qualification_process(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_qualification_process(["heritage"])

    def test_reasons_name_every_driver(self):
        out = assess_qualification_process(
            self._spec(
                application_envelope={"transport-power-w": (0.0, 900.0)},
                modifications=["working-fluid"],
            )
        )
        joined = " ".join(out["reasons"])
        self.assertIn("working-fluid", joined)
        self.assertIn("transport-power-w", joined)


if __name__ == "__main__":
    unittest.main()
