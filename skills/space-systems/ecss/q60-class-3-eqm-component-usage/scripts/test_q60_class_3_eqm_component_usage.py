"""Contract tests for the clause 6.1.6 Class 3 model part-handling logic."""

import unittest

from q60_class_3_eqm_component_usage_logic import (
    ALLOWED_RELAXATION_DEPTH,
    LIFE_STRESSES,
    QUALITY_LEVEL_LADDER,
    RETENTION_THRESHOLD,
    TOLERANCE,
    assess_class_3_eqm_part_usage,
    consumed_life,
    flight_build_position,
    governing_stress,
    part_disposition,
    quality_level_rank,
    relaxation_depth,
    usage_completeness,
    validate_part_id,
)

LIMITS = {"thermal_cycles": 200, "rework_operations": 5, "powered_hours": 1000}


def spent(**overrides):
    """Return what the model has spent on one part, with overrides."""
    base = {"thermal_cycles": 20, "rework_operations": 1, "powered_hours": 100}
    base.update(overrides)
    return base


def fitted(**overrides):
    """Return one fitted part record with optional overrides."""
    base = {
        "part_id": "U17",
        "fitted_quality_level": "military-level",
        "flight_intended_quality_level": "military-level",
        "spent": spent(),
    }
    base.update(overrides)
    return base


class PartIdTests(unittest.TestCase):
    def test_surrounding_space_is_stripped(self):
        self.assertEqual(validate_part_id("  U17 "), "U17")

    def test_blank_part_id_rejected(self):
        with self.assertRaises(ValueError):
            validate_part_id("   ")

    def test_non_string_part_id_rejected(self):
        with self.assertRaises(ValueError):
            validate_part_id(17)


class QualityLadderTests(unittest.TestCase):
    def test_top_rung_ranks_zero(self):
        self.assertEqual(quality_level_rank(QUALITY_LEVEL_LADDER[0]), 0)

    def test_ladder_is_ordered_downwards(self):
        ranks = [quality_level_rank(level) for level in QUALITY_LEVEL_LADDER]
        self.assertEqual(ranks, sorted(ranks))

    def test_lookup_ignores_case(self):
        self.assertEqual(quality_level_rank("SPACE-LEVEL"), 0)

    def test_unknown_level_rejected(self):
        with self.assertRaises(ValueError):
            quality_level_rank("shelf-level")

    def test_matching_levels_carry_no_relaxation(self):
        self.assertEqual(relaxation_depth("military-level", "military-level"), 0)

    def test_one_rung_down_is_depth_one(self):
        self.assertEqual(relaxation_depth("automotive-level", "military-level"), 1)

    def test_better_than_intended_is_a_negative_depth(self):
        self.assertEqual(relaxation_depth("space-level", "military-level"), -1)


class CompletenessTests(unittest.TestCase):
    def test_complete_record_scores_one(self):
        missing, fraction = usage_completeness(fitted())
        self.assertEqual(missing, ())
        self.assertAlmostEqual(fraction, 1.0, places=9)

    def test_absent_field_is_named(self):
        record = fitted()
        del record["fitted_quality_level"]
        missing, _ = usage_completeness(record)
        self.assertEqual(missing, ("fitted_quality_level",))

    def test_blank_string_counts_as_missing(self):
        missing, _ = usage_completeness(fitted(part_id="  "))
        self.assertEqual(missing, ("part_id",))

    def test_non_mapping_spent_counts_as_missing(self):
        missing, _ = usage_completeness(fitted(spent=[20, 1, 100]))
        self.assertEqual(missing, ("spent",))

    def test_non_mapping_record_rejected(self):
        with self.assertRaises(ValueError):
            usage_completeness(["U17"])


class ConsumedLifeTests(unittest.TestCase):
    def test_every_declared_stress_is_answered(self):
        fractions = consumed_life(spent(), LIMITS)
        self.assertEqual(sorted(fractions), sorted(LIFE_STRESSES))

    def test_fraction_is_amount_over_limit(self):
        fractions = consumed_life(spent(thermal_cycles=100), LIMITS)
        self.assertAlmostEqual(fractions["thermal_cycles"], 0.5, places=9)

    def test_unspent_stress_reads_as_zero(self):
        fractions = consumed_life({"thermal_cycles": 0}, LIMITS)
        self.assertAlmostEqual(fractions["powered_hours"], 0.0, places=9)

    def test_missing_limit_rejected(self):
        with self.assertRaises(ValueError):
            consumed_life(spent(), {"thermal_cycles": 200})

    def test_zero_limit_rejected(self):
        broken = dict(LIMITS, rework_operations=0)
        with self.assertRaises(ValueError):
            consumed_life(spent(), broken)

    def test_negative_amount_rejected(self):
        with self.assertRaises(ValueError):
            consumed_life(spent(powered_hours=-5), LIMITS)

    def test_unknown_stress_rejected(self):
        with self.assertRaises(ValueError):
            consumed_life(dict(spent(), vibration_minutes=4), LIMITS)

    def test_non_mapping_spent_rejected(self):
        with self.assertRaises(ValueError):
            consumed_life([20, 1, 100], LIMITS)


class GoverningStressTests(unittest.TestCase):
    def test_stress_nearest_its_limit_governs(self):
        fractions = consumed_life(spent(rework_operations=4), LIMITS)
        stress, fraction = governing_stress(fractions)
        self.assertEqual(stress, "rework_operations")
        self.assertAlmostEqual(fraction, 0.8, places=9)

    def test_tie_keeps_the_declared_stress_order(self):
        fractions = {name: 0.25 for name in LIFE_STRESSES}
        stress, _ = governing_stress(fractions)
        self.assertEqual(stress, LIFE_STRESSES[0])

    def test_incomplete_fraction_map_rejected(self):
        with self.assertRaises(ValueError):
            governing_stress({"thermal_cycles": 0.1})

    def test_empty_fraction_map_rejected(self):
        with self.assertRaises(ValueError):
            governing_stress({})


class DispositionTests(unittest.TestCase):
    def test_clean_part_stays_available_to_the_model(self):
        record = part_disposition(fitted(), LIMITS)
        self.assertEqual(record["disposition"], "eligible-for-continued-model-use")
        self.assertTrue(record["clean"])

    def test_incomplete_record_is_not_reported_as_a_life_finding(self):
        broken = fitted()
        del broken["spent"]
        record = part_disposition(broken, LIMITS)
        self.assertEqual(record["disposition"], "usage-record-incomplete")
        self.assertIsNone(record["governing_stress"])

    def test_relaxation_deeper_than_allowed_is_refused(self):
        record = part_disposition(
            fitted(fitted_quality_level="commercial-level"), LIMITS
        )
        self.assertEqual(record["disposition"], "relaxation-beyond-allowance")

    def test_allowed_relaxation_without_a_note_is_refused(self):
        record = part_disposition(
            fitted(fitted_quality_level="automotive-level"), LIMITS
        )
        self.assertEqual(record["disposition"], "substitution-note-missing")

    def test_allowed_relaxation_with_a_note_passes(self):
        record = part_disposition(
            fitted(
                fitted_quality_level="automotive-level",
                substitution_note="agreed at the model build review",
            ),
            LIMITS,
        )
        self.assertEqual(record["disposition"], "eligible-for-continued-model-use")

    def test_blank_substitution_note_does_not_count(self):
        record = part_disposition(
            fitted(fitted_quality_level="automotive-level", substitution_note="   "),
            LIMITS,
        )
        self.assertEqual(record["disposition"], "substitution-note-missing")

    def test_part_better_than_intended_needs_no_note(self):
        record = part_disposition(fitted(fitted_quality_level="space-level"), LIMITS)
        self.assertEqual(record["disposition"], "eligible-for-continued-model-use")

    def test_spent_past_a_limit_is_a_life_finding(self):
        record = part_disposition(fitted(spent=spent(rework_operations=7)), LIMITS)
        self.assertEqual(record["disposition"], "life-limit-exceeded")

    def test_part_near_a_limit_is_retained_by_the_model(self):
        record = part_disposition(fitted(spent=spent(powered_hours=950)), LIMITS)
        self.assertEqual(record["disposition"], "retain-for-model-use-only")

    def test_part_exactly_on_the_threshold_is_not_retained(self):
        record = part_disposition(fitted(spent=spent(powered_hours=800)), LIMITS)
        self.assertAlmostEqual(record["governing_fraction"], RETENTION_THRESHOLD, places=9)
        self.assertEqual(record["disposition"], "eligible-for-continued-model-use")

    def test_part_exactly_on_a_limit_is_not_reported_as_exceeded(self):
        record = part_disposition(fitted(spent=spent(powered_hours=1000)), LIMITS)
        self.assertAlmostEqual(record["governing_fraction"], 1.0, places=9)
        self.assertEqual(record["disposition"], "retain-for-model-use-only")

    def test_negative_allowed_depth_rejected(self):
        with self.assertRaises(ValueError):
            part_disposition(fitted(), LIMITS, allowed_depth=-1)

    def test_boolean_allowed_depth_rejected(self):
        with self.assertRaises(ValueError):
            part_disposition(fitted(), LIMITS, allowed_depth=True)

    def test_threshold_above_one_rejected(self):
        with self.assertRaises(ValueError):
            part_disposition(fitted(), LIMITS, retention_threshold=1.5)

    def test_default_allowance_is_one_rung(self):
        self.assertEqual(ALLOWED_RELAXATION_DEPTH, 1)


class FlightPositionTests(unittest.TestCase):
    def test_clean_unrelaxed_part_is_only_a_candidate(self):
        record = part_disposition(fitted(), LIMITS)
        self.assertEqual(
            flight_build_position(record), "flight-build-candidate-subject-to-review"
        )

    def test_relaxed_part_is_never_a_flight_candidate(self):
        record = part_disposition(
            fitted(
                fitted_quality_level="automotive-level",
                substitution_note="agreed at the model build review",
            ),
            LIMITS,
        )
        self.assertEqual(flight_build_position(record), "not-eligible-for-flight-build")

    def test_retained_part_is_not_a_flight_candidate(self):
        record = part_disposition(fitted(spent=spent(powered_hours=950)), LIMITS)
        self.assertEqual(flight_build_position(record), "not-eligible-for-flight-build")

    def test_record_without_a_disposition_rejected(self):
        with self.assertRaises(ValueError):
            flight_build_position({"part_id": "U17"})


class AssessmentTests(unittest.TestCase):
    def _spec(self, **overrides):
        base = {"parts": [fitted()], "limits": LIMITS}
        base.update(overrides)
        return base

    def test_clean_model_is_accepted(self):
        result = assess_class_3_eqm_part_usage(self._spec())
        self.assertTrue(result["model_usage_accepted"])
        self.assertEqual(result["verdict"], "model-usage-accepted")

    def test_clean_fraction_counts_the_parts(self):
        spec = self._spec(
            parts=[fitted(), fitted(part_id="U18", spent=spent(rework_operations=9))]
        )
        result = assess_class_3_eqm_part_usage(spec)
        self.assertAlmostEqual(result["clean_fraction"], 0.5, places=9)

    def test_findings_are_ranked_worst_first(self):
        broken = fitted(part_id="U20")
        del broken["spent"]
        spec = self._spec(
            parts=[
                fitted(part_id="U18", spent=spent(rework_operations=9)),
                broken,
            ]
        )
        result = assess_class_3_eqm_part_usage(spec)
        severities = [entry["severity"] for entry in result["findings"]]
        self.assertEqual(severities, sorted(severities))

    def test_flight_candidates_are_listed(self):
        spec = self._spec(
            parts=[fitted(), fitted(part_id="U18", spent=spent(powered_hours=950))]
        )
        result = assess_class_3_eqm_part_usage(spec)
        self.assertEqual(result["flight_build_candidates"], ("U17",))

    def test_repeated_part_identifier_rejected(self):
        with self.assertRaises(ValueError):
            assess_class_3_eqm_part_usage(self._spec(parts=[fitted(), fitted()]))

    def test_stricter_allowance_refuses_a_relaxed_part(self):
        spec = self._spec(
            parts=[
                fitted(
                    fitted_quality_level="automotive-level",
                    substitution_note="agreed at the model build review",
                )
            ],
            allowed_relaxation_depth=0,
        )
        result = assess_class_3_eqm_part_usage(spec)
        self.assertEqual(
            result["records"][0]["disposition"], "relaxation-beyond-allowance"
        )

    def test_missing_limits_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_class_3_eqm_part_usage({"parts": [fitted()]})

    def test_empty_part_set_rejected(self):
        with self.assertRaises(ValueError):
            assess_class_3_eqm_part_usage(self._spec(parts=[]))

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_class_3_eqm_part_usage(["parts"])

    def test_tolerance_is_representation_sized_only(self):
        self.assertLess(TOLERANCE, 1e-6)


if __name__ == "__main__":
    unittest.main()
