"""Contract tests for the clause 6.4.3.17.3 cell assembly flatness criteria logic."""

import math
import unittest

from e2008_sca_flatness_criteria_logic import (
    DEFAULT_FLATNESS_CRITERIA_POLICY,
    LOT_ACCEPTED,
    LOT_REFERRED,
    LOT_REJECTED,
    LOT_UNDERSIZED,
    PROVENANCE_DERIVED,
    PROVENANCE_DRAWING,
    SAMPLE_ACCEPTED,
    SAMPLE_MARGINAL,
    SAMPLE_REJECTED,
    assess_flatness_criteria,
    characteristic_span,
    derive_flatness_limit,
    resolve_governing_limit,
    sentence_sample,
    validate_geometry,
    validate_policy,
)

# A representative assembly: the span term binds, well clear of floor and
# ceiling.
GEOMETRY = {"length_mm": 80.0, "width_mm": 40.0}
# A small assembly whose derived limit is held up by the floor, so the limit
# is exactly 50 um and boundary behaviour can be asserted without rounding.
SMALL_GEOMETRY = {"length_mm": 20.0, "width_mm": 20.0}
# A large assembly whose derived limit is held down by the ceiling.
LARGE_GEOMETRY = {"length_mm": 300.0, "width_mm": 300.0}

FLOOR_LIMIT = DEFAULT_FLATNESS_CRITERIA_POLICY["floor_um"]
CEILING_LIMIT = DEFAULT_FLATNESS_CRITERIA_POLICY["ceiling_um"]


def _sample(sample_id, deflection, uncertainty=1.0):
    return {
        "sample_id": sample_id,
        "max_deflection_um": deflection,
        "uncertainty_um": uncertainty,
    }


def _spec(**overrides):
    spec = {
        "geometry": dict(SMALL_GEOMETRY),
        "samples": [
            _sample("sca-01", 20.0),
            _sample("sca-02", 24.0),
            _sample("sca-03", 22.0),
            _sample("sca-04", 26.0),
        ],
    }
    spec.update(overrides)
    return spec


class PolicyValidationTests(unittest.TestCase):
    def test_default_policy_is_returned(self):
        policy = validate_policy()
        self.assertAlmostEqual(policy["floor_um"], 50.0, places=9)
        self.assertEqual(policy["min_subgroup_samples"], 4)

    def test_unrecognised_policy_key_rejected(self):
        with self.assertRaises(ValueError):
            validate_policy({"slope_um_per_metre": 1.0})

    def test_non_positive_slope_rejected(self):
        with self.assertRaises(ValueError):
            validate_policy({"slope_um_per_mm": 0.0})

    def test_ceiling_below_floor_rejected(self):
        with self.assertRaises(ValueError):
            validate_policy({"floor_um": 200.0, "ceiling_um": 100.0})

    def test_non_integer_sample_floor_rejected(self):
        with self.assertRaises(ValueError):
            validate_policy({"min_subgroup_samples": 2.5})

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_policy(["floor_um"])


class GeometryTests(unittest.TestCase):
    def test_geometry_is_normalized(self):
        geometry = validate_geometry(GEOMETRY)
        self.assertAlmostEqual(geometry["width_mm"], 40.0, places=9)

    def test_zero_width_geometry_rejected(self):
        with self.assertRaises(ValueError):
            validate_geometry({"length_mm": 80.0, "width_mm": 0.0})

    def test_missing_geometry_key_rejected(self):
        with self.assertRaises(ValueError):
            validate_geometry({"length_mm": 80.0})

    def test_span_is_the_diagonal(self):
        self.assertAlmostEqual(characteristic_span(GEOMETRY), math.sqrt(8000.0), places=9)

    def test_a_square_assembly_spans_root_two_sides(self):
        span = characteristic_span({"length_mm": 10.0, "width_mm": 10.0})
        self.assertAlmostEqual(span, 10.0 * math.sqrt(2.0), places=9)


class LimitDerivationTests(unittest.TestCase):
    def test_span_term_binds_for_a_representative_assembly(self):
        derived = derive_flatness_limit(GEOMETRY)
        self.assertEqual(derived["binding_term"], "span")
        self.assertAlmostEqual(derived["limit_um"], math.sqrt(8000.0), places=9)

    def test_floor_binds_for_a_small_assembly(self):
        derived = derive_flatness_limit(SMALL_GEOMETRY)
        self.assertEqual(derived["binding_term"], "floor")
        self.assertAlmostEqual(derived["limit_um"], FLOOR_LIMIT, places=9)

    def test_ceiling_binds_for_a_large_assembly(self):
        derived = derive_flatness_limit(LARGE_GEOMETRY)
        self.assertEqual(derived["binding_term"], "ceiling")
        self.assertAlmostEqual(derived["limit_um"], CEILING_LIMIT, places=9)

    def test_a_longer_assembly_earns_no_less_allowance(self):
        short = derive_flatness_limit({"length_mm": 60.0, "width_mm": 40.0})
        long = derive_flatness_limit({"length_mm": 120.0, "width_mm": 40.0})
        self.assertAlmostEqual(
            max(short["limit_um"], long["limit_um"]), long["limit_um"], places=9
        )

    def test_declared_slope_changes_the_derived_limit(self):
        derived = derive_flatness_limit(GEOMETRY, {"slope_um_per_mm": 2.0})
        self.assertAlmostEqual(derived["limit_um"], 2.0 * math.sqrt(8000.0), places=9)

    def test_raw_limit_is_reported_alongside_the_held_one(self):
        derived = derive_flatness_limit(SMALL_GEOMETRY)
        self.assertAlmostEqual(derived["raw_limit_um"], math.sqrt(800.0), places=9)


class GoverningLimitTests(unittest.TestCase):
    def test_derived_limit_governs_when_no_drawing_states_one(self):
        resolved = resolve_governing_limit(GEOMETRY)
        self.assertEqual(resolved["provenance"], PROVENANCE_DERIVED)
        self.assertEqual(resolved["findings"], [])

    def test_drawing_limit_governs_when_stated(self):
        resolved = resolve_governing_limit(GEOMETRY, 60.0)
        self.assertEqual(resolved["provenance"], PROVENANCE_DRAWING)
        self.assertAlmostEqual(resolved["governing_limit_um"], 60.0, places=9)

    def test_a_tighter_drawing_limit_raises_no_finding(self):
        resolved = resolve_governing_limit(GEOMETRY, 40.0)
        self.assertEqual(resolved["findings"], [])

    def test_a_drawing_limit_above_the_envelope_is_a_finding(self):
        resolved = resolve_governing_limit(GEOMETRY, 400.0)
        self.assertEqual(len(resolved["findings"]), 1)

    def test_a_drawing_limit_on_the_envelope_raises_no_finding(self):
        derived = derive_flatness_limit(SMALL_GEOMETRY)
        self.assertAlmostEqual(derived["limit_um"], FLOOR_LIMIT, places=9)
        resolved = resolve_governing_limit(SMALL_GEOMETRY, FLOOR_LIMIT)
        self.assertEqual(resolved["findings"], [])

    def test_non_positive_drawing_limit_rejected(self):
        with self.assertRaises(ValueError):
            resolve_governing_limit(GEOMETRY, 0.0)


class SampleSentenceTests(unittest.TestCase):
    def test_a_clear_deflection_is_accepted(self):
        result = sentence_sample(20.0, 2.0, FLOOR_LIMIT)
        self.assertEqual(result["disposition"], SAMPLE_ACCEPTED)

    def test_a_deflection_landing_on_the_limit_is_accepted(self):
        result = sentence_sample(FLOOR_LIMIT, 0.0, FLOOR_LIMIT)
        self.assertAlmostEqual(result["guard_banded_um"], FLOOR_LIMIT, places=9)
        self.assertEqual(result["disposition"], SAMPLE_ACCEPTED)

    def test_a_guard_band_landing_on_the_limit_is_accepted(self):
        result = sentence_sample(48.0, 2.0, FLOOR_LIMIT)
        self.assertAlmostEqual(result["guard_banded_um"], FLOOR_LIMIT, places=9)
        self.assertEqual(result["disposition"], SAMPLE_ACCEPTED)

    def test_a_guard_band_crossing_the_limit_is_marginal(self):
        result = sentence_sample(48.0, 5.0, FLOOR_LIMIT)
        self.assertEqual(result["disposition"], SAMPLE_MARGINAL)

    def test_a_deflection_over_the_limit_is_rejected(self):
        result = sentence_sample(55.0, 0.0, FLOOR_LIMIT)
        self.assertEqual(result["disposition"], SAMPLE_REJECTED)

    def test_margin_is_reported_against_the_bare_deflection(self):
        result = sentence_sample(30.0, 4.0, FLOOR_LIMIT)
        self.assertAlmostEqual(result["margin_um"], 20.0, places=9)

    def test_negative_deflection_rejected(self):
        with self.assertRaises(ValueError):
            sentence_sample(-1.0, 1.0, FLOOR_LIMIT)

    def test_negative_uncertainty_rejected(self):
        with self.assertRaises(ValueError):
            sentence_sample(10.0, -1.0, FLOOR_LIMIT)

    def test_non_positive_limit_rejected(self):
        with self.assertRaises(ValueError):
            sentence_sample(10.0, 1.0, 0.0)

    def test_non_numeric_deflection_rejected(self):
        with self.assertRaises(ValueError):
            sentence_sample("twenty", 1.0, FLOOR_LIMIT)


class LotAssessmentTests(unittest.TestCase):
    def test_nominal_lot_is_accepted(self):
        result = assess_flatness_criteria(_spec())
        self.assertEqual(result["verdict"], LOT_ACCEPTED)
        self.assertEqual(result["findings"], [])

    def test_one_over_limit_sample_rejects_the_lot(self):
        samples = _spec()["samples"] + [_sample("sca-05", 62.0)]
        result = assess_flatness_criteria(_spec(samples=samples))
        self.assertEqual(result["verdict"], LOT_REJECTED)
        self.assertEqual(result["rejected_ids"], ["sca-05"])

    def test_a_marginal_sample_refers_the_lot(self):
        samples = _spec()["samples"] + [_sample("sca-05", 49.0, 4.0)]
        result = assess_flatness_criteria(_spec(samples=samples))
        self.assertEqual(result["verdict"], LOT_REFERRED)
        self.assertEqual(result["marginal_ids"], ["sca-05"])

    def test_rejection_outranks_referral(self):
        samples = _spec()["samples"] + [
            _sample("sca-05", 49.0, 4.0),
            _sample("sca-06", 80.0, 1.0),
        ]
        result = assess_flatness_criteria(_spec(samples=samples))
        self.assertEqual(result["verdict"], LOT_REJECTED)

    def test_undersized_lot_outranks_a_rejection(self):
        result = assess_flatness_criteria(_spec(samples=[_sample("sca-01", 400.0)]))
        self.assertEqual(result["verdict"], LOT_UNDERSIZED)

    def test_drawing_limit_can_accept_a_lot_the_envelope_would_refuse(self):
        samples = [_sample("sca-0%d" % i, 60.0) for i in range(1, 5)]
        tight = assess_flatness_criteria(_spec(samples=samples))
        loose = assess_flatness_criteria(_spec(samples=samples, drawing_limit_um=120.0))
        self.assertEqual(tight["verdict"], LOT_REJECTED)
        self.assertEqual(loose["verdict"], LOT_ACCEPTED)

    def test_a_permissive_drawing_limit_is_still_reported(self):
        result = assess_flatness_criteria(_spec(drawing_limit_um=120.0))
        self.assertEqual(result["provenance"], PROVENANCE_DRAWING)
        self.assertEqual(len(result["findings"]), 1)

    def test_binding_term_and_span_are_echoed(self):
        result = assess_flatness_criteria(_spec())
        self.assertEqual(result["binding_term"], "floor")
        self.assertAlmostEqual(result["span_mm"], math.sqrt(800.0), places=9)

    def test_worst_sample_is_reported_on_the_guard_banded_value(self):
        result = assess_flatness_criteria(_spec())
        self.assertEqual(result["worst_sample_id"], "sca-04")
        self.assertAlmostEqual(result["worst_guard_banded_um"], 27.0, places=9)

    def test_repeated_sample_identifier_rejected(self):
        samples = _spec()["samples"] + [_sample("sca-01", 30.0)]
        with self.assertRaises(ValueError):
            assess_flatness_criteria(_spec(samples=samples))

    def test_blank_sample_identifier_rejected(self):
        with self.assertRaises(ValueError):
            assess_flatness_criteria(_spec(samples=[_sample("  ", 20.0)]))

    def test_missing_sample_field_rejected(self):
        bad = dict(_sample("sca-01", 20.0))
        del bad["uncertainty_um"]
        with self.assertRaises(ValueError):
            assess_flatness_criteria(_spec(samples=[bad]))

    def test_empty_sample_set_rejected(self):
        with self.assertRaises(ValueError):
            assess_flatness_criteria(_spec(samples=[]))

    def test_missing_spec_key_rejected(self):
        spec = _spec()
        del spec["geometry"]
        with self.assertRaises(ValueError):
            assess_flatness_criteria(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_flatness_criteria(["geometry"])


if __name__ == "__main__":
    unittest.main()
