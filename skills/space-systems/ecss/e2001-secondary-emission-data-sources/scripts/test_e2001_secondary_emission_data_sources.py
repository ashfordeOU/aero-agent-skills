#!/usr/bin/env python3
"""Contract test for the clause 5.3.3.3 secondary emission data source logic."""

import unittest

from e2001_secondary_emission_data_sources_logic import (
    assess_part_data,
    assess_part_set,
    categorize_data_source,
    conservatism_key,
    interpolate_yield,
    is_representative,
    more_conservative,
    representativeness_findings,
    select_yield_dataset,
    validate_yield_dataset,
    yield_above_unity_window,
)

CURVE = [(20.0, 0.4), (50.0, 1.0), (200.0, 2.1), (600.0, 1.4), (2000.0, 0.8)]


def dataset(**over):
    entry = {
        "source": "representative-coupon-measurement",
        "base_material": "aluminium-alloy",
        "surface_treatment": "silver-plated",
        "surface_condition": "vacuum-baked",
        "delta_max": 2.1,
        "first_crossover_ev": 50.0,
        "second_crossover_ev": 900.0,
        "curve": list(CURVE),
    }
    entry.update(over)
    return entry


def part(**over):
    entry = {
        "name": "output-filter-iris",
        "base_material": "aluminium-alloy",
        "surface_treatment": "silver-plated",
        "surface_condition": "vacuum-baked",
        "energy_min_ev": 20.0,
        "energy_max_ev": 1500.0,
    }
    entry.update(over)
    return entry


STANDARD = dataset(
    source="standard-tabulated-dataset",
    surface_treatment="silver-plated",
    surface_condition="as-received",
    delta_max=2.6,
    first_crossover_ev=30.0,
    second_crossover_ev=1600.0,
    curve=[(10.0, 0.5), (30.0, 1.0), (250.0, 2.6), (900.0, 1.6), (2000.0, 0.9)],
)


class DataSourceCategoryTests(unittest.TestCase):
    def test_flight_lot_measurement_is_measured_and_top_tier(self):
        result = categorize_data_source("flight-lot-sample-measurement")
        self.assertEqual(result["family"], "measured")
        self.assertEqual(result["tier"], 1)

    def test_standard_tabulated_dataset_is_its_own_family(self):
        self.assertEqual(
            categorize_data_source("standard-tabulated-dataset")["family"], "standard"
        )

    def test_supplier_datasheet_is_a_declared_source(self):
        self.assertEqual(
            categorize_data_source("supplier-datasheet")["family"], "declared"
        )

    def test_source_lookup_normalizes_case_and_spacing(self):
        self.assertEqual(
            categorize_data_source(" Open-Literature ")["tier"],
            categorize_data_source("open-literature")["tier"],
        )

    def test_unknown_source_is_rejected(self):
        with self.assertRaises(ValueError):
            categorize_data_source("hearsay")

    def test_empty_source_is_rejected(self):
        with self.assertRaises(ValueError):
            categorize_data_source("")


class DatasetValidationTests(unittest.TestCase):
    def test_valid_dataset_is_normalized_with_span(self):
        entry = validate_yield_dataset(dataset())
        self.assertAlmostEqual(entry["energy_min_ev"], 20.0)
        self.assertAlmostEqual(entry["energy_max_ev"], 2000.0)

    def test_non_mapping_dataset_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_yield_dataset(["aluminium-alloy"])

    def test_missing_base_material_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_yield_dataset(dataset(base_material=""))

    def test_non_positive_peak_yield_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_yield_dataset(dataset(delta_max=0.0))

    def test_peak_yield_at_or_below_unity_contradicts_the_crossovers(self):
        with self.assertRaises(ValueError):
            validate_yield_dataset(dataset(delta_max=0.9))

    def test_second_crossover_below_first_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_yield_dataset(dataset(second_crossover_ev=40.0))

    def test_non_positive_first_crossover_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_yield_dataset(dataset(first_crossover_ev=-5.0))

    def test_single_point_curve_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_yield_dataset(dataset(curve=[(20.0, 0.4)]))

    def test_malformed_curve_point_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_yield_dataset(dataset(curve=[(20.0, 0.4), (50.0,)]))

    def test_non_monotonic_curve_energies_are_rejected(self):
        with self.assertRaises(ValueError):
            validate_yield_dataset(
                dataset(curve=[(20.0, 0.4), (200.0, 2.1), (50.0, 1.0)])
            )

    def test_negative_yield_point_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_yield_dataset(dataset(curve=[(20.0, -0.1), (50.0, 1.0)]))

    def test_non_positive_curve_energy_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_yield_dataset(dataset(curve=[(0.0, 0.4), (50.0, 1.0)]))


class InterpolationTests(unittest.TestCase):
    def test_yield_at_a_tabulated_point_is_that_point(self):
        self.assertAlmostEqual(interpolate_yield(dataset(), 200.0), 2.1)

    def test_yield_between_points_is_linear(self):
        self.assertAlmostEqual(interpolate_yield(dataset(), 35.0), 0.7)

    def test_yield_at_the_lower_endpoint_is_returned(self):
        self.assertAlmostEqual(interpolate_yield(dataset(), 20.0), 0.4)

    def test_yield_at_the_upper_endpoint_is_returned(self):
        self.assertAlmostEqual(interpolate_yield(dataset(), 2000.0), 0.8)

    def test_energy_below_the_span_is_rejected(self):
        with self.assertRaises(ValueError):
            interpolate_yield(dataset(), 5.0)

    def test_energy_above_the_span_is_rejected(self):
        with self.assertRaises(ValueError):
            interpolate_yield(dataset(), 5000.0)

    def test_non_numeric_energy_is_rejected(self):
        with self.assertRaises(ValueError):
            interpolate_yield(dataset(), "200")

    def test_multiplying_window_is_the_crossover_pair(self):
        low, high = yield_above_unity_window(dataset())
        self.assertAlmostEqual(low, 50.0)
        self.assertAlmostEqual(high, 900.0)


class RepresentativenessTests(unittest.TestCase):
    def test_matching_surface_has_no_findings(self):
        self.assertEqual(representativeness_findings(part(), dataset()), [])
        self.assertTrue(is_representative(part(), dataset()))

    def test_base_material_mismatch_is_found(self):
        findings = representativeness_findings(part(), dataset(base_material="copper"))
        self.assertIn("base-material-mismatch", findings)

    def test_surface_treatment_mismatch_is_found(self):
        findings = representativeness_findings(
            part(), dataset(surface_treatment="gold-plated")
        )
        self.assertIn("surface-treatment-mismatch", findings)

    def test_surface_condition_mismatch_is_found(self):
        findings = representativeness_findings(
            part(), dataset(surface_condition="as-received")
        )
        self.assertIn("surface-condition-mismatch", findings)

    def test_short_energy_coverage_is_found(self):
        findings = representativeness_findings(part(energy_max_ev=3000.0), dataset())
        self.assertIn("energy-coverage-short", findings)

    def test_energy_bound_exactly_on_the_span_survives_float_error(self):
        required_high = (0.1 + 0.2) * 1000.0
        self.assertGreater(required_high, 300.0)
        narrow = dataset(curve=[(20.0, 0.4), (50.0, 1.0), (300.0, 2.1)])
        findings = representativeness_findings(
            part(energy_max_ev=required_high), narrow
        )
        self.assertEqual(findings, [])

    def test_inverted_required_energy_range_is_rejected(self):
        with self.assertRaises(ValueError):
            representativeness_findings(
                part(energy_min_ev=900.0, energy_max_ev=100.0), dataset()
            )

    def test_non_mapping_part_is_rejected(self):
        with self.assertRaises(ValueError):
            representativeness_findings(["output-filter-iris"], dataset())


class ConservatismTests(unittest.TestCase):
    def test_higher_peak_yield_is_more_conservative(self):
        harsh = dataset(delta_max=3.0, curve=[(20.0, 0.4), (200.0, 3.0), (2000.0, 0.8)])
        self.assertIs(more_conservative(harsh, dataset()), harsh)

    def test_lower_first_crossover_breaks_an_equal_peak_tie(self):
        early = dataset(first_crossover_ev=30.0)
        self.assertIs(more_conservative(dataset(), early), early)

    def test_conservatism_key_orders_peak_yield_descending(self):
        harsh = dataset(delta_max=3.0, curve=[(20.0, 0.4), (200.0, 3.0), (2000.0, 0.8)])
        self.assertLess(conservatism_key(harsh), conservatism_key(dataset()))


class SelectionTests(unittest.TestCase):
    def test_representative_measurement_is_selected(self):
        result = select_yield_dataset(part(), [dataset()], fallback=STANDARD)
        self.assertEqual(result["basis"], "representative-measured")
        self.assertEqual(result["findings"], [])

    def test_best_provenance_tier_wins_among_representative_candidates(self):
        flight = dataset(source="flight-lot-sample-measurement")
        result = select_yield_dataset(part(), [dataset(), flight], fallback=STANDARD)
        self.assertEqual(result["dataset"]["source"], "flight-lot-sample-measurement")

    def test_conservatism_breaks_a_tier_tie(self):
        harsh = dataset(delta_max=3.0, curve=[(20.0, 0.4), (200.0, 3.0), (2000.0, 0.8)])
        result = select_yield_dataset(part(), [dataset(), harsh], fallback=STANDARD)
        self.assertAlmostEqual(result["dataset"]["delta_max"], 3.0)

    def test_non_representative_candidates_fall_back_to_the_standard_curve(self):
        result = select_yield_dataset(
            part(), [dataset(base_material="copper")], fallback=STANDARD
        )
        self.assertEqual(result["basis"], "standard-fallback")
        self.assertIn("standard-fallback-applied", result["findings"])

    def test_fallback_surface_mismatch_is_carried_as_a_finding(self):
        result = select_yield_dataset(
            part(), [dataset(base_material="copper")], fallback=STANDARD
        )
        self.assertIn("fallback-surface-condition-mismatch", result["findings"])

    def test_no_representative_data_and_no_fallback_is_rejected(self):
        with self.assertRaises(ValueError):
            select_yield_dataset(part(), [dataset(base_material="copper")])

    def test_a_measured_curve_cannot_serve_as_the_fallback(self):
        with self.assertRaises(ValueError):
            select_yield_dataset(
                part(), [dataset(base_material="copper")], fallback=dataset()
            )

    def test_non_list_candidates_are_rejected(self):
        with self.assertRaises(ValueError):
            select_yield_dataset(part(), dataset(), fallback=STANDARD)


class PartAssessmentTests(unittest.TestCase):
    def test_representative_data_is_accepted(self):
        result = assess_part_data(part(), [dataset()], fallback=STANDARD)
        self.assertTrue(result["data_accepted"])
        self.assertEqual(result["basis"], "representative-measured")

    def test_declared_provenance_is_flagged(self):
        declared = dataset(source="supplier-datasheet")
        result = assess_part_data(part(), [declared], fallback=STANDARD)
        self.assertIn("provenance-not-measured-or-standard", result["findings"])
        self.assertFalse(result["data_accepted"])

    def test_curve_peak_above_the_declared_value_is_flagged(self):
        inconsistent = dataset(
            delta_max=1.5, curve=[(20.0, 0.4), (200.0, 2.1), (2000.0, 0.8)]
        )
        result = assess_part_data(part(), [inconsistent], fallback=STANDARD)
        self.assertIn("curve-peak-exceeds-declared-delta-max", result["findings"])

    def test_multiplying_window_is_reported(self):
        result = assess_part_data(part(), [dataset()], fallback=STANDARD)
        self.assertAlmostEqual(result["multiplying_window_ev"][0], 50.0)

    def test_unnamed_part_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_part_data(part(name="  "), [dataset()], fallback=STANDARD)

    def test_set_is_accepted_when_every_part_has_representative_data(self):
        first = part()
        first["candidates"] = [dataset()]
        second = part(name="input-manifold-step")
        second["candidates"] = [dataset()]
        summary = assess_part_set([first, second], fallback=STANDARD)
        self.assertTrue(summary["set_accepted"])
        self.assertEqual(summary["fallback_parts"], [])

    def test_set_records_the_parts_on_the_standard_fallback(self):
        first = part()
        first["candidates"] = [dataset()]
        second = part(name="input-manifold-step")
        second["candidates"] = [dataset(base_material="copper")]
        summary = assess_part_set([first, second], fallback=STANDARD)
        self.assertEqual(summary["fallback_parts"], ["input-manifold-step"])
        self.assertFalse(summary["set_accepted"])
        self.assertIn(
            "input-manifold-step:standard-fallback-applied", summary["open_findings"]
        )

    def test_duplicate_part_names_are_rejected(self):
        first = part()
        first["candidates"] = [dataset()]
        second = part()
        second["candidates"] = [dataset()]
        with self.assertRaises(ValueError):
            assess_part_set([first, second], fallback=STANDARD)

    def test_empty_part_set_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_part_set([], fallback=STANDARD)

    def test_non_mapping_part_entry_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_part_set(["output-filter-iris"], fallback=STANDARD)


if __name__ == "__main__":
    unittest.main()
