"""Contract tests for the clause 6.4.3.6.3 thermo optical acceptance limits."""

import unittest

from e2008_sca_thermo_optical_criteria_logic import (
    ADMISSIBLE_PROVENANCE,
    DISPOSITION_ORDER,
    LIMIT_SENSES,
    absorptance_emittance_ratio,
    assess_thermo_optical_criteria,
    categorize_limit_provenance,
    evaluate_sample_limits,
    guard_banded_disposition,
    validate_drawing,
    validate_limit,
    worst_disposition,
)

DRAWING = {
    "number": "SCA-CD-4471",
    "revision": "C",
    "lot_built_to_revision": "C",
}

LIMITS = {
    "solar_absorptance": {"value": 0.92, "source": "drawing"},
    "hemispherical_emittance": {"value": 0.80, "source": "drawing"},
    "absorptance_emittance_ratio": {"value": 1.20, "source": "drawing"},
}


def _limit_records(limits=None):
    records = {}
    for name, limit in (limits or LIMITS).items():
        record, _ = validate_limit(name, limit)
        records[name] = record
    return records


def _sample(sample_id="SCA-01", absorptance=0.90, emittance=0.85, uncertainty=None):
    sample = {
        "id": sample_id,
        "solar_absorptance": absorptance,
        "hemispherical_emittance": emittance,
    }
    if uncertainty is not None:
        sample["uncertainty"] = uncertainty
    return sample


def _spec(**overrides):
    spec = {
        "drawing": dict(DRAWING),
        "limits": {name: dict(limit) for name, limit in LIMITS.items()},
        "samples": [_sample("SCA-01"), _sample("SCA-02", 0.89, 0.86)],
    }
    spec.update(overrides)
    return spec


class ProvenanceTests(unittest.TestCase):
    def test_drawing_source_is_drawing_stated(self):
        self.assertEqual(
            categorize_limit_provenance({"source": "control-drawing"}), "drawing-stated"
        )

    def test_invoked_specification_is_drawing_invoked(self):
        self.assertEqual(
            categorize_limit_provenance({"source": "invoked-specification"}),
            "drawing-invoked",
        )

    def test_anything_else_is_a_house_default(self):
        self.assertEqual(
            categorize_limit_provenance({"source": "laboratory practice"}),
            "house-default",
        )

    def test_both_admissible_categories_are_drawing_backed(self):
        for category in ADMISSIBLE_PROVENANCE:
            self.assertIn("drawing", category)

    def test_house_default_limit_is_a_finding(self):
        record, findings = validate_limit(
            "solar_absorptance", {"value": 0.92, "source": "house"}
        )
        self.assertFalse(record["admissible"])
        self.assertEqual(len(findings), 1)

    def test_invoked_limit_without_a_named_document_is_a_finding(self):
        _, findings = validate_limit(
            "hemispherical_emittance", {"value": 0.80, "source": "drawing-invoked"}
        )
        self.assertTrue(any("not named" in item for item in findings))

    def test_invoked_limit_naming_its_document_is_clean(self):
        record, findings = validate_limit(
            "hemispherical_emittance",
            {"value": 0.80, "source": "drawing-invoked", "document": "SPEC-118"},
        )
        self.assertEqual(findings, [])
        self.assertEqual(record["document"], "SPEC-118")

    def test_ungoverned_property_name_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_limit("mass_g", {"value": 1.0, "source": "drawing"})

    def test_each_governed_property_carries_a_sense(self):
        self.assertEqual(LIMIT_SENSES["solar_absorptance"], "max")
        self.assertEqual(LIMIT_SENSES["hemispherical_emittance"], "min")


class DrawingRevisionTests(unittest.TestCase):
    def test_aligned_revision_is_clean(self):
        record, findings = validate_drawing(DRAWING)
        self.assertTrue(record["revision_aligned"])
        self.assertEqual(findings, [])

    def test_superseded_revision_is_a_finding(self):
        record, findings = validate_drawing(
            dict(DRAWING, revision="B", lot_built_to_revision="C")
        )
        self.assertFalse(record["revision_aligned"])
        self.assertEqual(len(findings), 1)

    def test_missing_revision_key_is_rejected(self):
        drawing = dict(DRAWING)
        del drawing["revision"]
        with self.assertRaises(ValueError):
            validate_drawing(drawing)

    def test_blank_drawing_number_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_drawing(dict(DRAWING, number="  "))


class GuardBandTests(unittest.TestCase):
    def test_clearly_inside_a_ceiling_passes(self):
        self.assertEqual(guard_banded_disposition(0.90, 0.92, "max", 0.01), "pass")

    def test_uncertainty_straddling_a_ceiling_is_marginal(self):
        self.assertEqual(guard_banded_disposition(0.915, 0.92, "max", 0.01), "marginal")

    def test_clearly_outside_a_ceiling_fails(self):
        self.assertEqual(guard_banded_disposition(0.95, 0.92, "max", 0.01), "fail")

    def test_clearly_inside_a_floor_passes(self):
        self.assertEqual(guard_banded_disposition(0.85, 0.80, "min", 0.01), "pass")

    def test_uncertainty_straddling_a_floor_is_marginal(self):
        self.assertEqual(guard_banded_disposition(0.805, 0.80, "min", 0.01), "marginal")

    def test_clearly_outside_a_floor_fails(self):
        self.assertEqual(guard_banded_disposition(0.75, 0.80, "min", 0.01), "fail")

    def test_value_exactly_on_a_ceiling_with_no_uncertainty_passes(self):
        self.assertEqual(guard_banded_disposition(0.92, 0.92, "max", 0.0), "pass")

    def test_value_exactly_on_a_floor_with_no_uncertainty_passes(self):
        self.assertEqual(guard_banded_disposition(0.80, 0.80, "min", 0.0), "pass")

    def test_unknown_sense_is_rejected(self):
        with self.assertRaises(ValueError):
            guard_banded_disposition(0.9, 0.92, "between", 0.01)

    def test_negative_uncertainty_is_rejected(self):
        with self.assertRaises(ValueError):
            guard_banded_disposition(0.9, 0.92, "max", -0.01)


class DispositionRollupTests(unittest.TestCase):
    def test_ordering_runs_pass_marginal_fail(self):
        self.assertEqual(DISPOSITION_ORDER, ("pass", "marginal", "fail"))

    def test_worst_of_a_clean_set_is_pass(self):
        self.assertEqual(worst_disposition(["pass", "pass"]), "pass")

    def test_one_marginal_carries_the_set(self):
        self.assertEqual(worst_disposition(["pass", "marginal", "pass"]), "marginal")

    def test_one_failure_outranks_a_marginal(self):
        self.assertEqual(worst_disposition(["marginal", "fail", "pass"]), "fail")

    def test_unknown_disposition_is_rejected(self):
        with self.assertRaises(ValueError):
            worst_disposition(["pass", "waived"])

    def test_empty_disposition_set_is_rejected(self):
        with self.assertRaises(ValueError):
            worst_disposition([])


class SampleLimitTests(unittest.TestCase):
    def test_ratio_is_derived_from_the_two_properties(self):
        self.assertAlmostEqual(
            absorptance_emittance_ratio(0.90, 0.85), 0.90 / 0.85, places=9
        )

    def test_compliant_sample_passes_every_check(self):
        record = evaluate_sample_limits(_sample(), _limit_records())
        self.assertEqual(record["disposition"], "pass")
        self.assertEqual(record["findings"], [])
        self.assertEqual(len(record["checks"]), 3)

    def test_absorptance_above_its_ceiling_fails(self):
        record = evaluate_sample_limits(_sample(absorptance=0.97), _limit_records())
        self.assertEqual(record["disposition"], "fail")

    def test_emittance_below_its_floor_fails(self):
        record = evaluate_sample_limits(_sample(emittance=0.60), _limit_records())
        self.assertEqual(record["disposition"], "fail")

    def test_result_inside_its_own_uncertainty_of_the_limit_is_marginal(self):
        record = evaluate_sample_limits(
            _sample(absorptance=0.915, uncertainty={"solar_absorptance": 0.01}),
            _limit_records(),
        )
        self.assertEqual(record["disposition"], "marginal")

    def test_ratio_uncertainty_is_propagated_when_not_declared(self):
        record = evaluate_sample_limits(
            _sample(
                uncertainty={
                    "solar_absorptance": 0.01,
                    "hemispherical_emittance": 0.01,
                }
            ),
            _limit_records(),
        )
        ratio_check = [
            check
            for check in record["checks"]
            if check["property"] == "absorptance_emittance_ratio"
        ][0]
        self.assertGreater(ratio_check["uncertainty"], 0.01)

    def test_declared_ratio_uncertainty_is_used_as_given(self):
        record = evaluate_sample_limits(
            _sample(uncertainty={"absorptance_emittance_ratio": 0.05}),
            _limit_records(),
        )
        ratio_check = [
            check
            for check in record["checks"]
            if check["property"] == "absorptance_emittance_ratio"
        ][0]
        self.assertAlmostEqual(ratio_check["uncertainty"], 0.05, places=9)

    def test_zero_emittance_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_sample_limits(_sample(emittance=0.0), _limit_records())

    def test_blank_sample_identifier_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_sample_limits(_sample(sample_id="  "), _limit_records())


class CriteriaAssessmentTests(unittest.TestCase):
    def test_drawing_backed_limits_and_compliant_lot_is_valid(self):
        result = assess_thermo_optical_criteria(_spec())
        self.assertTrue(result["valid"])
        self.assertEqual(result["lot_disposition"], "pass")
        self.assertEqual(result["disposition_counts"]["pass"], 2)

    def test_house_default_limit_invalidates_a_compliant_lot(self):
        limits = {name: dict(limit) for name, limit in LIMITS.items()}
        limits["solar_absorptance"]["source"] = "house"
        result = assess_thermo_optical_criteria(_spec(limits=limits))
        self.assertFalse(result["valid"])
        self.assertEqual(result["lot_disposition"], "pass")

    def test_superseded_drawing_revision_invalidates_the_lot(self):
        result = assess_thermo_optical_criteria(
            _spec(drawing=dict(DRAWING, revision="B"))
        )
        self.assertFalse(result["valid"])

    def test_one_failing_sample_carries_the_lot_disposition(self):
        result = assess_thermo_optical_criteria(
            _spec(samples=[_sample("SCA-01"), _sample("SCA-02", absorptance=0.99)])
        )
        self.assertEqual(result["lot_disposition"], "fail")
        self.assertEqual(result["disposition_counts"]["fail"], 1)

    def test_duplicate_sample_identifier_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_thermo_optical_criteria(
                _spec(samples=[_sample("SCA-01"), _sample("SCA-01")])
            )

    def test_empty_limit_set_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_thermo_optical_criteria(_spec(limits={}))

    def test_empty_sample_sequence_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_thermo_optical_criteria(_spec(samples=[]))

    def test_non_mapping_spec_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_thermo_optical_criteria(["drawing"])

    def test_a_subset_of_the_governed_limits_is_accepted(self):
        result = assess_thermo_optical_criteria(
            _spec(limits={"solar_absorptance": dict(LIMITS["solar_absorptance"])})
        )
        self.assertTrue(result["valid"])
        self.assertEqual(len(result["sample_records"][0]["checks"]), 1)


if __name__ == "__main__":
    unittest.main()
