"""Contract tests for the clause 5.5.1.3.3 cycling-coupon definition logic."""

import unittest

from e2008_thermal_cycling_qualification_coupon_logic import (
    COVERAGE_TOLERANCE,
    RECORD_MEDIA,
    REQUIRED_FEATURES,
    assess_coupon_definition,
    build_register,
    coverage_fraction,
    extraneous_features,
    missing_required,
    normalize_feature,
    reference_kind,
    unrepresented_flight_features,
    validate_entry,
)

FULL_FEATURES = [
    {"name": "solar-cell", "reference": "SA-104275"},
    {"name": "interconnect", "reference": "SA-104276 rev B"},
    {"name": "coverglass", "reference": "MTX-7:R1C2"},
    {"name": "adhesive", "reference": "MTX-7:R1C3"},
    {"name": "substrate", "reference": "SA-104280-A"},
    {"name": "wiring termination", "reference": "MTX-7:R2C1"},
]


class NormalizationTests(unittest.TestCase):
    def test_spaces_become_hyphens(self):
        self.assertEqual(normalize_feature(" Wiring Termination "), "wiring-termination")

    def test_underscores_become_hyphens(self):
        self.assertEqual(normalize_feature("solar_cell"), "solar-cell")

    def test_existing_hyphens_survive(self):
        self.assertEqual(normalize_feature("cover-glass"), "cover-glass")

    def test_blank_name_rejected(self):
        with self.assertRaises(ValueError):
            normalize_feature("   ")

    def test_non_string_name_rejected(self):
        with self.assertRaises(ValueError):
            normalize_feature(12)

    def test_required_families_are_six(self):
        self.assertEqual(len(REQUIRED_FEATURES), 6)

    def test_record_media_are_drawing_and_matrix(self):
        self.assertEqual(RECORD_MEDIA, ("drawing", "matrix"))


class ReferenceTests(unittest.TestCase):
    def test_plain_drawing_number(self):
        self.assertEqual(reference_kind("SA-104275"), "drawing")

    def test_drawing_with_revision(self):
        self.assertEqual(reference_kind("PVA-2210-B rev C"), "drawing")

    def test_matrix_cell(self):
        self.assertEqual(reference_kind("MTX-7:R3C4"), "matrix")

    def test_matrix_cell_is_not_read_as_a_drawing(self):
        self.assertNotEqual(reference_kind("MTX-12:R10C2"), "drawing")

    def test_free_text_note_refused(self):
        with self.assertRaises(ValueError):
            reference_kind("as built on the bench last week")

    def test_bare_number_refused(self):
        with self.assertRaises(ValueError):
            reference_kind("104275")

    def test_empty_reference_refused(self):
        with self.assertRaises(ValueError):
            reference_kind("   ")

    def test_non_string_reference_refused(self):
        with self.assertRaises(ValueError):
            reference_kind(104275)


class EntryTests(unittest.TestCase):
    def test_entry_is_normalised(self):
        entry = validate_entry({"name": "Wiring Termination", "reference": "SA-104281"})
        self.assertEqual(entry["name"], "wiring-termination")
        self.assertEqual(entry["record"], "drawing")

    def test_process_is_normalised_when_given(self):
        entry = validate_entry(
            {"name": "interconnect", "reference": "SA-104276",
             "process": "Parallel Gap Weld"}
        )
        self.assertEqual(entry["process"], "parallel-gap-weld")

    def test_process_is_optional(self):
        entry = validate_entry({"name": "adhesive", "reference": "MTX-7:R1C3"})
        self.assertIsNone(entry["process"])

    def test_missing_reference_rejected(self):
        with self.assertRaises(ValueError):
            validate_entry({"name": "adhesive"})

    def test_non_mapping_entry_rejected(self):
        with self.assertRaises(ValueError):
            validate_entry(["adhesive", "MTX-7:R1C3"])


class RegisterTests(unittest.TestCase):
    def test_register_keeps_one_record_per_feature(self):
        register = build_register(FULL_FEATURES)
        self.assertEqual(len(register), 6)

    def test_duplicate_feature_rejected(self):
        doubled = FULL_FEATURES + [{"name": "Solar Cell", "reference": "SA-104999"}]
        with self.assertRaises(ValueError):
            build_register(doubled)

    def test_empty_register_rejected(self):
        with self.assertRaises(ValueError):
            build_register([])

    def test_non_sequence_rejected(self):
        with self.assertRaises(ValueError):
            build_register({"name": "adhesive", "reference": "MTX-7:R1C3"})


class CoverageTests(unittest.TestCase):
    def test_full_register_covers_everything(self):
        names = [entry["name"] for entry in build_register(FULL_FEATURES)]
        self.assertAlmostEqual(coverage_fraction(names), 1.0, places=9)

    def test_half_register_covers_half(self):
        names = ["solar-cell", "interconnect", "coverglass"]
        self.assertAlmostEqual(coverage_fraction(names), 0.5, places=9)

    def test_unknown_name_does_not_raise_the_coverage(self):
        names = ["solar-cell", "thermocouple-tab"]
        self.assertAlmostEqual(coverage_fraction(names), 1.0 / 6.0, places=9)

    def test_missing_families_are_named(self):
        self.assertEqual(
            missing_required(["solar-cell", "interconnect", "coverglass"]),
            ["adhesive", "substrate", "wiring-termination"],
        )

    def test_empty_required_set_rejected(self):
        with self.assertRaises(ValueError):
            coverage_fraction(["solar-cell"], [])

    def test_non_sequence_names_rejected(self):
        with self.assertRaises(ValueError):
            coverage_fraction("solar-cell")


class FlightComparisonTests(unittest.TestCase):
    def test_unrepresented_flight_feature_is_named(self):
        result = unrepresented_flight_features(
            ["solar-cell", "interconnect"],
            ["solar-cell", "interconnect", "blocking-diode"],
        )
        self.assertEqual(result, ["blocking-diode"])

    def test_nothing_unrepresented_when_the_coupon_matches(self):
        self.assertEqual(
            unrepresented_flight_features(["solar-cell"], ["Solar Cell"]), []
        )

    def test_extraneous_coupon_feature_is_named(self):
        result = extraneous_features(
            ["solar-cell", "handling-tab"], ["solar-cell", "interconnect"]
        )
        self.assertEqual(result, ["handling-tab"])

    def test_extraneous_list_is_empty_for_a_subset_coupon(self):
        self.assertEqual(extraneous_features(["solar-cell"], ["solar-cell"]), [])


class AssessmentTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "features": [dict(entry) for entry in FULL_FEATURES],
            "flight_features": [
                "solar-cell",
                "interconnect",
                "coverglass",
                "adhesive",
                "substrate",
                "wiring-termination",
            ],
            "minimum_coverage": 1.0,
        }
        spec.update(overrides)
        return spec

    def test_complete_definition_is_accepted(self):
        result = assess_coupon_definition(self._spec())
        self.assertTrue(result["defined"])
        self.assertEqual(result["findings"], [])

    def test_coverage_is_reported(self):
        result = assess_coupon_definition(self._spec())
        self.assertAlmostEqual(result["coverage"], 1.0, places=9)

    def test_register_is_grouped_by_record_medium(self):
        result = assess_coupon_definition(self._spec())
        self.assertEqual(result["record_grouping"]["drawing"], 3)
        self.assertEqual(result["record_grouping"]["matrix"], 3)

    def test_missing_family_is_flagged(self):
        features = [dict(entry) for entry in FULL_FEATURES[:4]]
        result = assess_coupon_definition(self._spec(features=features))
        self.assertFalse(result["defined"])
        self.assertEqual(len(result["missing_required"]), 2)

    def test_free_text_reference_is_refused(self):
        features = [dict(entry) for entry in FULL_FEATURES]
        features[0]["reference"] = "see the build notes"
        with self.assertRaises(ValueError):
            assess_coupon_definition(self._spec(features=features))

    def test_coverage_exactly_on_the_minimum_raises_no_coverage_finding(self):
        features = [dict(entry) for entry in FULL_FEATURES[:3]]
        result = assess_coupon_definition(
            self._spec(features=features, minimum_coverage=0.5, flight_features=None)
        )
        self.assertAlmostEqual(result["coverage"], 0.5, places=9)
        self.assertFalse(any("below the" in finding for finding in result["findings"]))

    def test_coverage_under_the_minimum_is_flagged(self):
        features = [dict(entry) for entry in FULL_FEATURES[:2]]
        result = assess_coupon_definition(
            self._spec(features=features, minimum_coverage=0.9, flight_features=None)
        )
        self.assertTrue(any("below the" in finding for finding in result["findings"]))

    def test_flight_feature_absent_from_the_coupon_is_flagged(self):
        spec = self._spec()
        spec["flight_features"] = spec["flight_features"] + ["blocking-diode"]
        result = assess_coupon_definition(spec)
        self.assertEqual(result["unrepresented_flight_features"], ["blocking-diode"])
        self.assertFalse(result["defined"])

    def test_coupon_feature_absent_from_flight_is_flagged(self):
        features = [dict(entry) for entry in FULL_FEATURES]
        features.append({"name": "handling-tab", "reference": "SA-104999"})
        result = assess_coupon_definition(self._spec(features=features))
        self.assertEqual(result["extraneous_features"], ["handling-tab"])

    def test_flight_comparison_is_skipped_when_not_declared(self):
        result = assess_coupon_definition(self._spec(flight_features=None))
        self.assertEqual(result["unrepresented_flight_features"], [])
        self.assertTrue(result["defined"])

    def test_missing_features_key_rejected(self):
        spec = self._spec()
        del spec["features"]
        with self.assertRaises(ValueError):
            assess_coupon_definition(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_coupon_definition(["features"])

    def test_minimum_coverage_above_one_rejected(self):
        with self.assertRaises(ValueError):
            assess_coupon_definition(self._spec(minimum_coverage=1.4))

    def test_boolean_minimum_coverage_rejected(self):
        with self.assertRaises(ValueError):
            assess_coupon_definition(self._spec(minimum_coverage=True))

    def test_coverage_tolerance_is_small(self):
        self.assertAlmostEqual(COVERAGE_TOLERANCE, 1e-9, places=12)


if __name__ == "__main__":
    unittest.main()
