#!/usr/bin/env python3
"""Contract test for the clause 6.8.2 material-parameter evidence logic."""

import unittest

from e2006_material_parameter_selection_evidence_logic import (
    DECAY_DRIVING_FRACTION,
    VACUUM_PERMITTIVITY_F_PER_M,
    assess_material_evidence,
    categorize_evidence_source,
    charge_decay_time_constant,
    environment_coverage,
    normalize_parameter,
    parameter_spec,
    required_parameters_for_role,
    required_provenance,
    summarize_material_set,
    validate_parameter_record,
)


def record(parameter, value, source="selection-campaign-measurement", **extra):
    entry = {
        "parameter": parameter,
        "value": value,
        "source": source,
        "method": "vacuum-chamber-sample-measurement",
    }
    entry.update(extra)
    return entry


def dielectric_records():
    return [
        record("bulk-resistivity", 1.0e13),
        record("surface-resistivity", 1.0e14),
        record("relative-permittivity", 3.2),
        record("secondary-emission-yield-peak", 2.1),
        record("photoemission-yield", 2.0e-5),
        record("dielectric-thickness", 1.25e-4),
    ]


def dielectric_material(**overrides):
    material = {
        "id": "MAT-KAPTON-A",
        "role": "exposed-dielectric-surface",
        "records": dielectric_records(),
        "measured_range_c": (-150.0, 120.0),
        "mission_range_c": (-100.0, 90.0),
        "charging_timescale_s": 1.0e3,
    }
    material.update(overrides)
    return material


class TestNormalizeParameter(unittest.TestCase):
    def test_canonical_name_round_trips(self):
        self.assertEqual(normalize_parameter("bulk-resistivity"), "bulk-resistivity")

    def test_alias_maps_to_canonical(self):
        self.assertEqual(normalize_parameter("dielectric-constant"), "relative-permittivity")

    def test_case_and_underscore_normalized(self):
        self.assertEqual(normalize_parameter(" Sheet_Resistivity "), "surface-resistivity")

    def test_unknown_parameter_raises(self):
        with self.assertRaises(ValueError):
            normalize_parameter("thermal-conductivity")

    def test_blank_parameter_raises(self):
        with self.assertRaises(ValueError):
            normalize_parameter("  ")

    def test_non_string_parameter_raises(self):
        with self.assertRaises(ValueError):
            normalize_parameter(None)


class TestParameterSpec(unittest.TestCase):
    def test_permittivity_lower_bound_is_unity(self):
        self.assertAlmostEqual(parameter_spec("relative-permittivity")["lower"], 1.0)

    def test_spec_carries_the_working_unit(self):
        self.assertEqual(parameter_spec("bulk-resistivity")["unit"], "ohm-m")

    def test_spec_resolves_through_an_alias(self):
        self.assertEqual(parameter_spec("layer-thickness")["parameter"], "dielectric-thickness")


class TestCategorizeEvidenceSource(unittest.TestCase):
    def test_selection_campaign_is_measured_provenance(self):
        self.assertEqual(
            categorize_evidence_source("selection-campaign-measurement"), "selection-measured"
        )

    def test_manufacturer_datasheet_is_maker_declared(self):
        self.assertEqual(categorize_evidence_source("manufacturer-datasheet"), "maker-declared")

    def test_handbook_value_is_generic_reference(self):
        self.assertEqual(categorize_evidence_source("handbook-generic-value"), "generic-reference")

    def test_estimate_is_unsubstantiated(self):
        self.assertEqual(categorize_evidence_source("engineering-estimate"), "unsubstantiated")

    def test_canonical_category_is_accepted_directly(self):
        self.assertEqual(categorize_evidence_source("maker-declared"), "maker-declared")

    def test_unknown_source_raises(self):
        with self.assertRaises(ValueError):
            categorize_evidence_source("heard-it-in-a-review")

    def test_non_string_source_raises(self):
        with self.assertRaises(ValueError):
            categorize_evidence_source(42)


class TestChargeDecayTimeConstant(unittest.TestCase):
    def test_constant_matches_the_relaxation_product(self):
        tau = charge_decay_time_constant(1.0e13, 3.0)
        self.assertAlmostEqual(tau, VACUUM_PERMITTIVITY_F_PER_M * 3.0 * 1.0e13, places=6)

    def test_lower_resistivity_drains_faster(self):
        self.assertLess(
            charge_decay_time_constant(1.0e9, 3.0), charge_decay_time_constant(1.0e13, 3.0)
        )

    def test_zero_resistivity_raises(self):
        with self.assertRaises(ValueError):
            charge_decay_time_constant(0.0, 3.0)

    def test_permittivity_below_unity_raises(self):
        with self.assertRaises(ValueError):
            charge_decay_time_constant(1.0e13, 0.5)

    def test_non_finite_resistivity_raises(self):
        with self.assertRaises(ValueError):
            charge_decay_time_constant(float("nan"), 3.0)


class TestRequiredProvenance(unittest.TestCase):
    def test_fast_draining_material_accepts_maker_data(self):
        self.assertEqual(required_provenance(1.0, 1.0e3), "maker-declared")

    def test_slow_draining_material_demands_a_selection_measurement(self):
        self.assertEqual(required_provenance(5.0e3, 1.0e3), "selection-measured")

    def test_exact_driving_fraction_demands_a_selection_measurement(self):
        timescale = 1.0e3
        self.assertEqual(
            required_provenance(DECAY_DRIVING_FRACTION * timescale, timescale), "selection-measured"
        )

    def test_accumulated_tau_at_the_fraction_still_demands_a_measurement(self):
        # tau assembled from ten equal contributions lands a few ULPs under
        # the driving threshold; the tolerance must not let it slip a grade.
        timescale = 1.0e3
        tau = 0.0
        for _ in range(10):
            tau += DECAY_DRIVING_FRACTION * timescale / 10.0
        self.assertEqual(required_provenance(tau, timescale), "selection-measured")

    def test_zero_timescale_raises(self):
        with self.assertRaises(ValueError):
            required_provenance(1.0, 0.0)

    def test_negative_tau_raises(self):
        with self.assertRaises(ValueError):
            required_provenance(-1.0, 1.0e3)


class TestValidateParameterRecord(unittest.TestCase):
    def test_measured_record_is_acceptable(self):
        entry = validate_parameter_record(record("bulk-resistivity", 1.0e13))
        self.assertTrue(entry["acceptable"])
        self.assertEqual(entry["provenance"], "selection-measured")
        self.assertEqual(entry["findings"], [])

    def test_maker_record_with_a_method_is_acceptable(self):
        entry = validate_parameter_record(
            record("relative-permittivity", 3.4, source="manufacturer-datasheet")
        )
        self.assertTrue(entry["acceptable"])
        self.assertEqual(entry["rank"], 2)

    def test_maker_record_without_a_method_is_flagged(self):
        entry = validate_parameter_record(
            record("relative-permittivity", 3.4, source="manufacturer-datasheet", method="")
        )
        self.assertFalse(entry["acceptable"])
        self.assertIn("relative-permittivity measurement states no method", entry["findings"])

    def test_generic_reference_is_flagged_not_rejected(self):
        entry = validate_parameter_record(
            record("photoemission-yield", 2.0e-5, source="handbook-generic-value")
        )
        self.assertFalse(entry["acceptable"])
        self.assertEqual(entry["rank"], 1)

    def test_unsubstantiated_value_is_flagged(self):
        entry = validate_parameter_record(
            record("surface-resistivity", 1.0e12, source="engineering-estimate")
        )
        self.assertFalse(entry["acceptable"])
        self.assertTrue(any("unsubstantiated" in f for f in entry["findings"]))

    def test_matching_unit_is_accepted(self):
        entry = validate_parameter_record(record("bulk-resistivity", 1.0e13, unit="ohm-m"))
        self.assertTrue(entry["acceptable"])

    def test_permittivity_below_unity_raises(self):
        with self.assertRaises(ValueError):
            validate_parameter_record(record("relative-permittivity", 0.8))

    def test_value_above_the_admissible_range_raises(self):
        with self.assertRaises(ValueError):
            validate_parameter_record(record("photoemission-yield", 1.0))

    def test_unit_disagreement_raises(self):
        with self.assertRaises(ValueError):
            validate_parameter_record(record("bulk-resistivity", 1.0e13, unit="ohm-per-square"))

    def test_missing_value_raises(self):
        entry = record("bulk-resistivity", 1.0e13)
        del entry["value"]
        with self.assertRaises(ValueError):
            validate_parameter_record(entry)

    def test_non_mapping_record_raises(self):
        with self.assertRaises(ValueError):
            validate_parameter_record(["bulk-resistivity", 1.0e13])

    def test_admissible_lower_bound_value_is_accepted(self):
        spec = parameter_spec("relative-permittivity")
        entry = validate_parameter_record(record("relative-permittivity", spec["lower"]))
        self.assertAlmostEqual(entry["value"], 1.0)


class TestEnvironmentCoverage(unittest.TestCase):
    def test_enveloping_measurement_covers_the_mission(self):
        self.assertTrue(environment_coverage((-150.0, 150.0), (-100.0, 90.0))["covered"])

    def test_cold_shortfall_is_reported(self):
        result = environment_coverage((-50.0, 150.0), (-100.0, 90.0))
        self.assertFalse(result["covered"])
        self.assertTrue(any("cold side" in f for f in result["findings"]))

    def test_hot_shortfall_is_reported(self):
        result = environment_coverage((-150.0, 40.0), (-100.0, 90.0))
        self.assertFalse(result["covered"])
        self.assertTrue(any("hot side" in f for f in result["findings"]))

    def test_both_shortfalls_reported_together(self):
        result = environment_coverage((-50.0, 40.0), (-100.0, 90.0))
        self.assertEqual(len(result["findings"]), 2)

    def test_exactly_coincident_limits_are_covered(self):
        self.assertTrue(environment_coverage((-100.0, 90.0), (-100.0, 90.0))["covered"])

    def test_accumulated_mission_limit_at_the_measured_limit_is_covered(self):
        # The mission cold limit assembled from two contributions lands a few
        # ULPs below the measured limit; that is representation error, not an
        # uncovered environment.
        mission_low = -0.1 + -0.2
        self.assertLess(mission_low, -0.3)
        self.assertTrue(environment_coverage((-0.3, 90.0), (mission_low, 90.0))["covered"])

    def test_inverted_measured_range_raises(self):
        with self.assertRaises(ValueError):
            environment_coverage((120.0, -150.0), (-100.0, 90.0))

    def test_malformed_range_raises(self):
        with self.assertRaises(ValueError):
            environment_coverage((-150.0,), (-100.0, 90.0))

    def test_non_numeric_range_raises(self):
        with self.assertRaises(ValueError):
            environment_coverage((-150.0, "hot"), (-100.0, 90.0))


class TestRequiredParametersForRole(unittest.TestCase):
    def test_exposed_dielectric_needs_the_full_set(self):
        self.assertEqual(len(required_parameters_for_role("exposed-dielectric-surface")), 6)

    def test_conductive_coating_does_not_need_thickness(self):
        self.assertNotIn("dielectric-thickness", required_parameters_for_role("conductive-external-coating"))

    def test_internal_dielectric_does_not_need_photoemission(self):
        self.assertNotIn("photoemission-yield", required_parameters_for_role("internal-dielectric"))

    def test_unknown_role_raises(self):
        with self.assertRaises(ValueError):
            required_parameters_for_role("radiator-coating")

    def test_non_string_role_raises(self):
        with self.assertRaises(ValueError):
            required_parameters_for_role(None)


class TestAssessMaterialEvidence(unittest.TestCase):
    def test_complete_measured_dossier_is_sufficient(self):
        result = assess_material_evidence(dielectric_material())
        self.assertEqual(result["status"], "evidence-sufficient")
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["missing"], [])

    def test_decay_constant_is_reported(self):
        result = assess_material_evidence(dielectric_material())
        self.assertAlmostEqual(
            result["decay_time_constant_s"],
            VACUUM_PERMITTIVITY_F_PER_M * 3.2 * 1.0e13,
            places=6,
        )

    def test_missing_required_parameter_is_reported(self):
        records = [r for r in dielectric_records() if r["parameter"] != "dielectric-thickness"]
        result = assess_material_evidence(dielectric_material(records=records))
        self.assertEqual(result["missing"], ["dielectric-thickness"])
        self.assertEqual(result["status"], "evidence-insufficient")

    def test_maker_data_is_insufficient_for_a_slow_draining_dielectric(self):
        records = dielectric_records()
        records[0] = record("bulk-resistivity", 1.0e13, source="manufacturer-datasheet")
        result = assess_material_evidence(dielectric_material(records=records))
        self.assertEqual(result["status"], "evidence-insufficient")
        self.assertTrue(any("drives the decay behaviour" in f for f in result["findings"]))

    def test_maker_data_is_sufficient_for_a_fast_draining_dielectric(self):
        records = dielectric_records()
        records[0] = record("bulk-resistivity", 1.0e8, source="manufacturer-datasheet")
        result = assess_material_evidence(dielectric_material(records=records))
        self.assertEqual(result["status"], "evidence-sufficient")

    def test_environment_shortfall_reaches_the_material_verdict(self):
        result = assess_material_evidence(dielectric_material(measured_range_c=(-40.0, 120.0)))
        self.assertEqual(result["status"], "evidence-insufficient")
        self.assertTrue(any("cold side" in f for f in result["findings"]))

    def test_weakest_rank_tracks_the_poorest_record(self):
        records = dielectric_records()
        records[3] = record("secondary-emission-yield-peak", 2.1, source="handbook-generic-value")
        result = assess_material_evidence(dielectric_material(records=records))
        self.assertEqual(result["weakest_rank"], 1)

    def test_coating_role_ignores_absent_bulk_parameters(self):
        material = dielectric_material(
            id="MAT-ITO-COAT",
            role="conductive-external-coating",
            records=[
                record("surface-resistivity", 5.0e3),
                record("secondary-emission-yield-peak", 1.4),
                record("photoemission-yield", 3.0e-5),
            ],
        )
        result = assess_material_evidence(material)
        self.assertEqual(result["status"], "evidence-sufficient")
        self.assertIsNone(result["decay_time_constant_s"])

    def test_duplicate_parameter_record_raises(self):
        records = dielectric_records() + [record("relative-permittivity", 3.3)]
        with self.assertRaises(ValueError):
            assess_material_evidence(dielectric_material(records=records))

    def test_empty_record_list_raises(self):
        with self.assertRaises(ValueError):
            assess_material_evidence(dielectric_material(records=[]))

    def test_blank_material_id_raises(self):
        with self.assertRaises(ValueError):
            assess_material_evidence(dielectric_material(id="   "))

    def test_non_mapping_material_raises(self):
        with self.assertRaises(ValueError):
            assess_material_evidence("MAT-KAPTON-A")


class TestSummarizeMaterialSet(unittest.TestCase):
    def test_clean_campaign_closes(self):
        summary = summarize_material_set([dielectric_material()])
        self.assertTrue(summary["campaign_closed"])
        self.assertEqual(summary["sufficient_count"], 1)

    def test_one_weak_dossier_opens_the_campaign(self):
        weak = dielectric_material(id="MAT-WEAK", measured_range_c=(-20.0, 30.0))
        summary = summarize_material_set([dielectric_material(), weak])
        self.assertFalse(summary["campaign_closed"])
        self.assertEqual(summary["insufficient_ids"], ["MAT-WEAK"])

    def test_counts_add_up(self):
        summary = summarize_material_set([dielectric_material(), dielectric_material(id="MAT-B")])
        self.assertEqual(summary["sufficient_count"] + len(summary["insufficient_ids"]), 2)

    def test_empty_campaign_raises(self):
        with self.assertRaises(ValueError):
            summarize_material_set([])

    def test_non_list_campaign_raises(self):
        with self.assertRaises(ValueError):
            summarize_material_set(dielectric_material())


if __name__ == "__main__":
    unittest.main()
