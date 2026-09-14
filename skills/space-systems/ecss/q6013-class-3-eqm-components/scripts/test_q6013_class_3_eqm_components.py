"""Contract tests for the clause 6.1.6 lowest-class model part choice logic."""

import unittest

from q6013_class_3_eqm_components_logic import (
    DEFAULT_SOFT_WEIGHTS,
    DELTA_RECORD,
    HARD_ATTRIBUTES,
    MATCH_TOLERANCE,
    REJECTION_REASONS,
    SLOT_VERDICTS,
    choose_eqm_part,
    delta_records,
    hard_mismatches,
    match_fraction,
    screen_candidate,
    soft_deltas,
    validate_identifier,
    validate_soft_weights,
)

INTENDED = {
    "function": "low-dropout-regulator",
    "pinout": "SOT223-3-standard",
    "package": "SOT223",
    "supply_range": "3v0-to-16v0",
    "manufacturer": "alpha-semi",
    "screening_level": "commercial",
    "mounting_technology": "surface-mount",
}


def candidate(**overrides):
    """Return a candidate identical to the intended part, with overrides."""
    base = dict(INTENDED)
    base["reference"] = "CAND-A"
    base["lead_days"] = 10
    base.update(overrides)
    return base


class ValidateIdentifierTests(unittest.TestCase):
    def test_strips_surrounding_space(self):
        self.assertEqual(validate_identifier(" CAND-A ", "reference"), "CAND-A")

    def test_blank_rejected(self):
        with self.assertRaises(ValueError):
            validate_identifier("\t", "reference")

    def test_non_string_rejected(self):
        with self.assertRaises(ValueError):
            validate_identifier(None, "reference")


class ValidateSoftWeightsTests(unittest.TestCase):
    def test_default_weights_sum_to_unity(self):
        total = sum(validate_soft_weights().values())
        self.assertAlmostEqual(total, 1.0, places=9)

    def test_default_set_is_returned_when_omitted(self):
        self.assertEqual(
            sorted(validate_soft_weights()), sorted(DEFAULT_SOFT_WEIGHTS)
        )

    def test_weights_not_summing_to_unity_rejected(self):
        with self.assertRaises(ValueError):
            validate_soft_weights({"package": 0.5, "supply_range": 0.2})

    def test_hard_attribute_may_not_be_weighted(self):
        with self.assertRaises(ValueError):
            validate_soft_weights({"function": 1.0})

    def test_attribute_without_a_record_obligation_rejected(self):
        with self.assertRaises(ValueError):
            validate_soft_weights({"colour": 1.0})

    def test_negative_weight_rejected(self):
        with self.assertRaises(ValueError):
            validate_soft_weights({"package": -1.0, "supply_range": 2.0})

    def test_empty_mapping_rejected(self):
        with self.assertRaises(ValueError):
            validate_soft_weights({})


class HardMismatchTests(unittest.TestCase):
    def test_identical_part_has_no_hard_mismatch(self):
        self.assertEqual(hard_mismatches(candidate(), INTENDED), ())

    def test_different_function_is_a_hard_mismatch(self):
        self.assertEqual(
            hard_mismatches(candidate(function="switching-regulator"), INTENDED),
            ("function",),
        )

    def test_different_pinout_is_a_hard_mismatch(self):
        self.assertIn(
            "pinout", hard_mismatches(candidate(pinout="SOT223-3-mirrored"), INTENDED)
        )

    def test_comparison_is_case_insensitive(self):
        self.assertEqual(
            hard_mismatches(candidate(function="Low-Dropout-Regulator"), INTENDED), ()
        )

    def test_missing_hard_attribute_rejected(self):
        broken = candidate()
        del broken["pinout"]
        with self.assertRaises(ValueError):
            hard_mismatches(broken, INTENDED)

    def test_hard_attributes_are_the_published_set(self):
        self.assertEqual(len(HARD_ATTRIBUTES), 2)


class SoftDeltaTests(unittest.TestCase):
    def test_identical_part_has_no_soft_delta(self):
        self.assertEqual(soft_deltas(candidate(), INTENDED), ())

    def test_package_difference_is_reported(self):
        self.assertEqual(
            soft_deltas(candidate(package="SOIC8"), INTENDED), ("package",)
        )

    def test_deltas_are_sorted(self):
        deltas = soft_deltas(
            candidate(package="SOIC8", manufacturer="beta-semi"), INTENDED
        )
        self.assertEqual(list(deltas), sorted(deltas))

    def test_missing_soft_attribute_rejected(self):
        broken = candidate()
        del broken["package"]
        with self.assertRaises(ValueError):
            soft_deltas(broken, INTENDED)

    def test_non_mapping_candidate_rejected(self):
        with self.assertRaises(ValueError):
            soft_deltas(["CAND-A"], INTENDED)


class MatchFractionTests(unittest.TestCase):
    def test_no_delta_is_unity(self):
        self.assertAlmostEqual(match_fraction(()), 1.0, places=9)

    def test_package_delta_costs_its_weight(self):
        self.assertAlmostEqual(match_fraction(("package",)), 0.70, places=9)

    def test_every_delta_is_zero(self):
        self.assertAlmostEqual(
            match_fraction(tuple(sorted(DEFAULT_SOFT_WEIGHTS))), 0.0, places=9
        )

    def test_repeated_delta_rejected(self):
        with self.assertRaises(ValueError):
            match_fraction(("package", "package"))

    def test_unweighted_delta_rejected(self):
        with self.assertRaises(ValueError):
            match_fraction(("function",))

    def test_non_sequence_rejected(self):
        with self.assertRaises(ValueError):
            match_fraction("package")


class DeltaRecordTests(unittest.TestCase):
    def test_package_delta_maps_to_a_mechanical_record(self):
        self.assertEqual(delta_records(("package",)), ("mechanical-interface-delta",))

    def test_records_are_deduplicated_and_sorted(self):
        records = delta_records(("supply_range", "package"))
        self.assertEqual(list(records), sorted(records))
        self.assertEqual(len(records), 2)

    def test_every_weighted_attribute_has_a_record(self):
        for attribute in DEFAULT_SOFT_WEIGHTS:
            self.assertIn(attribute, DELTA_RECORD)

    def test_unknown_delta_rejected(self):
        with self.assertRaises(ValueError):
            delta_records(("colour",))


class ScreenCandidateTests(unittest.TestCase):
    def test_identical_in_window_candidate_is_admissible(self):
        record = screen_candidate(candidate(), INTENDED, 30)
        self.assertTrue(record["admissible"])
        self.assertIsNone(record["rejection_reason"])
        self.assertAlmostEqual(record["match_fraction"], 1.0, places=9)

    def test_function_change_is_ruled_out(self):
        record = screen_candidate(
            candidate(function="switching-regulator"), INTENDED, 30
        )
        self.assertFalse(record["admissible"])
        self.assertEqual(record["rejection_reason"], "hard-attribute-mismatch")

    def test_late_candidate_is_ruled_out(self):
        record = screen_candidate(candidate(lead_days=60), INTENDED, 30)
        self.assertEqual(record["rejection_reason"], "outside-build-window")

    def test_lead_time_exactly_at_the_window_is_admissible(self):
        record = screen_candidate(candidate(lead_days=30), INTENDED, 30)
        self.assertTrue(record["admissible"])

    def test_hard_mismatch_outranks_a_window_problem(self):
        record = screen_candidate(
            candidate(function="switching-regulator", lead_days=90), INTENDED, 30
        )
        self.assertEqual(record["rejection_reason"], "hard-attribute-mismatch")

    def test_negative_lead_days_rejected(self):
        with self.assertRaises(ValueError):
            screen_candidate(candidate(lead_days=-1), INTENDED, 30)

    def test_missing_reference_rejected(self):
        broken = candidate()
        del broken["reference"]
        with self.assertRaises(ValueError):
            screen_candidate(broken, INTENDED, 30)

    def test_rejection_reasons_are_the_published_set(self):
        self.assertEqual(len(REJECTION_REASONS), 2)


class ChooseEqmPartTests(unittest.TestCase):
    def _spec(self, **overrides):
        base = {
            "intended": INTENDED,
            "candidates": [candidate()],
            "build_window_days": 30,
        }
        base.update(overrides)
        return base

    def test_intended_part_available_is_fitted(self):
        result = choose_eqm_part(self._spec())
        self.assertEqual(result["verdict"], "intended-part-fitted")
        self.assertEqual(result["chosen"]["reference"], "CAND-A")
        self.assertEqual(result["build_standard_deltas"], ())

    def test_best_admissible_substitution_is_chosen(self):
        spec = self._spec(
            candidates=[
                candidate(reference="CAND-A", lead_days=90),
                candidate(reference="CAND-B", manufacturer="beta-semi"),
                candidate(reference="CAND-C", package="SOIC8", manufacturer="beta-semi"),
            ]
        )
        result = choose_eqm_part(spec)
        self.assertEqual(result["chosen"]["reference"], "CAND-B")
        self.assertEqual(result["verdict"], "substitution-recorded")
        self.assertAlmostEqual(result["match_fraction"], 0.80, places=9)

    def test_substitution_names_the_flight_build_records(self):
        spec = self._spec(
            candidates=[candidate(reference="CAND-B", package="SOIC8")]
        )
        result = choose_eqm_part(spec)
        self.assertEqual(
            result["flight_build_records"], ("mechanical-interface-delta",)
        )

    def test_tie_breaks_on_lead_time_then_reference(self):
        spec = self._spec(
            candidates=[
                candidate(reference="CAND-Z", manufacturer="beta-semi", lead_days=5),
                candidate(reference="CAND-B", manufacturer="gamma-semi", lead_days=5),
                candidate(reference="CAND-C", manufacturer="beta-semi", lead_days=20),
            ]
        )
        result = choose_eqm_part(spec)
        self.assertEqual(result["chosen"]["reference"], "CAND-B")
        self.assertEqual(result["ranked"][0], "CAND-B")

    def test_no_admissible_candidate_escalates(self):
        spec = self._spec(
            candidates=[candidate(reference="CAND-D", function="switching-regulator")]
        )
        result = choose_eqm_part(spec)
        self.assertIsNone(result["chosen"])
        self.assertEqual(result["verdict"], "escalate")
        self.assertFalse(result["meets_floor"])

    def test_match_below_the_floor_escalates(self):
        spec = self._spec(
            candidates=[
                candidate(
                    reference="CAND-E",
                    package="SOIC8",
                    supply_range="5v0-to-12v0",
                    manufacturer="beta-semi",
                )
            ]
        )
        result = choose_eqm_part(spec)
        self.assertAlmostEqual(result["match_fraction"], 0.25, places=9)
        self.assertEqual(result["verdict"], "escalate")

    def test_exactly_met_floor_counts_as_met(self):
        spec = self._spec(
            candidates=[candidate(reference="CAND-F", supply_range="5v0-to-12v0")],
            floor=0.75,
        )
        result = choose_eqm_part(spec)
        self.assertAlmostEqual(result["match_fraction"], 0.75, places=9)
        self.assertTrue(result["meets_floor"])
        self.assertEqual(result["verdict"], "substitution-recorded")

    def test_ruled_out_candidates_appear_in_the_findings(self):
        spec = self._spec(
            candidates=[
                candidate(reference="CAND-A"),
                candidate(reference="CAND-G", function="switching-regulator"),
            ]
        )
        result = choose_eqm_part(spec)
        self.assertEqual(result["findings"][0]["reference"], "CAND-G")
        self.assertEqual(result["findings"][0]["severity"], 0)

    def test_duplicate_candidate_reference_rejected(self):
        with self.assertRaises(ValueError):
            choose_eqm_part(self._spec(candidates=[candidate(), candidate()]))

    def test_empty_candidate_list_rejected(self):
        with self.assertRaises(ValueError):
            choose_eqm_part(self._spec(candidates=[]))

    def test_missing_build_window_rejected(self):
        with self.assertRaises(ValueError):
            choose_eqm_part({"intended": INTENDED, "candidates": [candidate()]})

    def test_floor_above_one_rejected(self):
        with self.assertRaises(ValueError):
            choose_eqm_part(self._spec(floor=1.2))

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            choose_eqm_part(["candidates"])

    def test_verdicts_are_the_published_set(self):
        self.assertEqual(len(SLOT_VERDICTS), 3)

    def test_tolerance_is_representation_sized(self):
        self.assertLess(MATCH_TOLERANCE, 1e-6)


if __name__ == "__main__":
    unittest.main()
