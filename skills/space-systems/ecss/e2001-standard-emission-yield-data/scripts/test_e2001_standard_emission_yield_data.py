#!/usr/bin/env python3
"""Gate 3 contract test for e2001-standard-emission-yield-data.

stdlib unittest, offline, deterministic. Exercises alias resolution,
tabulated lookup and refusal, the universal yield-curve, crossover
bisection, disposition reporting, representativeness assessment, source
selection and the aggregate clause 9.6 evaluation, including every
ValueError path.
"""

import unittest

import e2001_standard_emission_yield_data_logic as logic


def measured_record(**overrides):
    record = {
        "material": "aluminium",
        "surface_condition": "as-received",
        "energy_min_ev": 10.0,
        "energy_max_ev": 3000.0,
        "specimen_count": 3,
        "delta_max": 2.15,
        "e_max_ev": 310.0,
    }
    record.update(overrides)
    return record


REQUIRED_SPAN = (20.0, 2000.0)


class TestNormalizeToken(unittest.TestCase):
    def test_folds_case_and_spaces(self):
        self.assertEqual(
            logic.normalize_token(" Stainless Steel ", "material"), "stainless-steel"
        )

    def test_folds_underscores(self):
        self.assertEqual(
            logic.normalize_token("sputter_cleaned", "surface condition"),
            "sputter-cleaned",
        )

    def test_non_string_raises(self):
        with self.assertRaises(ValueError):
            logic.normalize_token(None, "material")

    def test_blank_raises(self):
        with self.assertRaises(ValueError):
            logic.normalize_token("  ", "material")


class TestResolveMaterial(unittest.TestCase):
    def test_american_spelling_resolves(self):
        self.assertEqual(logic.resolve_material("Aluminum"), "aluminium")

    def test_symbol_resolves(self):
        self.assertEqual(logic.resolve_material("Au"), "gold")

    def test_cres_resolves_to_stainless_steel(self):
        self.assertEqual(logic.resolve_material("CRES"), "stainless-steel")

    def test_canonical_name_passes_through(self):
        self.assertEqual(logic.resolve_material("copper"), "copper")

    def test_unknown_material_passes_through_for_the_lookup_to_refuse(self):
        self.assertEqual(logic.resolve_material("kapton"), "kapton")


class TestResolveSurfaceCondition(unittest.TestCase):
    def test_oxidized_resolves_to_as_received(self):
        self.assertEqual(logic.resolve_surface_condition("oxidised"), logic.AS_RECEIVED)

    def test_ion_cleaned_resolves_to_sputter_cleaned(self):
        self.assertEqual(
            logic.resolve_surface_condition("ion cleaned"), logic.SPUTTER_CLEANED
        )

    def test_unrecognized_condition_raises(self):
        with self.assertRaises(ValueError):
            logic.resolve_surface_condition("gold-plated")

    def test_non_string_condition_raises(self):
        with self.assertRaises(ValueError):
            logic.resolve_surface_condition(7)


class TestTabulatedLookup(unittest.TestCase):
    def test_table_covers_the_expected_metals(self):
        self.assertEqual(
            logic.tabulated_materials(),
            [
                "aluminium",
                "copper",
                "gold",
                "magnesium",
                "nickel",
                "silver",
                "stainless-steel",
                "titanium",
            ],
        )

    def test_lookup_returns_the_tabulated_parameters(self):
        entry = logic.lookup_tabulated_yield("aluminium", "as-received")
        self.assertAlmostEqual(entry["delta_max"], 2.40, places=9)
        self.assertAlmostEqual(entry["e_max_ev"], 300.0, places=9)

    def test_lookup_resolves_aliases(self):
        entry = logic.lookup_tabulated_yield("Aluminum", "oxidized")
        self.assertAlmostEqual(entry["delta_max"], 2.40, places=9)

    def test_cleaning_lowers_the_peak_for_every_metal(self):
        for material in logic.tabulated_materials():
            raw = logic.lookup_tabulated_yield(material, logic.AS_RECEIVED)
            clean = logic.lookup_tabulated_yield(material, logic.SPUTTER_CLEANED)
            self.assertLess(clean["delta_max"], raw["delta_max"])

    def test_returned_entry_is_a_copy(self):
        entry = logic.lookup_tabulated_yield("gold", "as-received")
        entry["delta_max"] = 99.0
        self.assertAlmostEqual(
            logic.lookup_tabulated_yield("gold", "as-received")["delta_max"],
            1.75,
            places=9,
        )

    def test_material_outside_the_table_is_refused(self):
        with self.assertRaises(ValueError):
            logic.lookup_tabulated_yield("kapton", "as-received")


class TestSecondaryYield(unittest.TestCase):
    def test_peak_is_reached_near_the_tabulated_peak_energy(self):
        self.assertAlmostEqual(logic.peak_yield(2.4, 300.0), 2.4, places=3)

    def test_yield_rises_towards_the_peak(self):
        low = logic.secondary_yield(50.0, 2.4, 300.0)
        mid = logic.secondary_yield(150.0, 2.4, 300.0)
        self.assertLess(low, mid)
        self.assertLess(mid, logic.peak_yield(2.4, 300.0))

    def test_yield_decays_above_the_peak(self):
        near = logic.secondary_yield(1000.0, 2.4, 300.0)
        far = logic.secondary_yield(5000.0, 2.4, 300.0)
        self.assertLess(far, near)

    def test_yield_scales_linearly_with_the_peak_parameter(self):
        one = logic.secondary_yield(200.0, 1.0, 300.0)
        two = logic.secondary_yield(200.0, 2.0, 300.0)
        self.assertAlmostEqual(two, 2.0 * one, places=12)

    def test_zero_energy_raises(self):
        with self.assertRaises(ValueError):
            logic.secondary_yield(0.0, 2.4, 300.0)

    def test_negative_energy_raises(self):
        with self.assertRaises(ValueError):
            logic.secondary_yield(-10.0, 2.4, 300.0)

    def test_non_positive_peak_parameter_raises(self):
        with self.assertRaises(ValueError):
            logic.secondary_yield(100.0, 0.0, 300.0)

    def test_non_numeric_peak_energy_raises(self):
        with self.assertRaises(ValueError):
            logic.secondary_yield(100.0, 2.4, "300")


class TestCrossoverEnergies(unittest.TestCase):
    def test_high_yield_surface_has_a_crossover(self):
        self.assertTrue(logic.has_crossover(2.4, 300.0))

    def test_low_yield_surface_has_no_crossover(self):
        self.assertFalse(logic.has_crossover(0.95, 300.0))

    def test_first_crossover_sits_below_the_peak_energy(self):
        first = logic.first_crossover_energy(2.4, 300.0)
        self.assertLess(first, 300.0)
        self.assertGreater(first, 0.0)

    def test_second_crossover_sits_above_the_peak_energy(self):
        second = logic.second_crossover_energy(2.4, 300.0)
        self.assertGreater(second, 300.0)

    def test_yield_is_unity_at_the_first_crossover(self):
        first = logic.first_crossover_energy(2.4, 300.0)
        self.assertAlmostEqual(logic.secondary_yield(first, 2.4, 300.0), 1.0, places=9)

    def test_yield_is_unity_at_the_second_crossover(self):
        second = logic.second_crossover_energy(2.4, 300.0)
        self.assertAlmostEqual(logic.secondary_yield(second, 2.4, 300.0), 1.0, places=9)

    def test_yield_exceeds_unity_between_the_crossovers(self):
        first = logic.first_crossover_energy(2.4, 300.0)
        second = logic.second_crossover_energy(2.4, 300.0)
        middle = 0.5 * (first + second)
        self.assertGreater(logic.secondary_yield(middle, 2.4, 300.0), 1.0)

    def test_a_higher_peak_widens_the_crossover_window(self):
        narrow = logic.second_crossover_energy(
            1.3, 600.0
        ) - logic.first_crossover_energy(1.3, 600.0)
        wide = logic.second_crossover_energy(
            1.9, 600.0
        ) - logic.first_crossover_energy(1.9, 600.0)
        self.assertGreater(wide, narrow)

    def test_first_crossover_raises_without_a_crossing(self):
        with self.assertRaises(ValueError):
            logic.first_crossover_energy(0.9, 280.0)

    def test_second_crossover_raises_without_a_crossing(self):
        with self.assertRaises(ValueError):
            logic.second_crossover_energy(0.9, 280.0)


class TestChargingDisposition(unittest.TestCase):
    def test_inside_the_window_the_surface_emits_net_electrons(self):
        self.assertEqual(
            logic.charging_disposition(300.0, 2.4, 300.0),
            "net-secondary-emission-positive-drift",
        )

    def test_below_the_first_crossover_the_surface_absorbs(self):
        self.assertEqual(
            logic.charging_disposition(5.0, 2.4, 300.0),
            "net-electron-absorption-negative-drift",
        )

    def test_above_the_second_crossover_the_surface_absorbs(self):
        self.assertEqual(
            logic.charging_disposition(20000.0, 2.4, 300.0),
            "net-electron-absorption-negative-drift",
        )

    def test_at_the_crossover_the_surface_is_balanced(self):
        first = logic.first_crossover_energy(2.4, 300.0)
        self.assertEqual(
            logic.charging_disposition(first, 2.4, 300.0), "unity-yield-balance"
        )

    def test_invalid_energy_raises(self):
        with self.assertRaises(ValueError):
            logic.charging_disposition(0.0, 2.4, 300.0)


class TestValidateMeasuredRecord(unittest.TestCase):
    def test_good_record_normalizes(self):
        normalized = logic.validate_measured_record(
            measured_record(material="Aluminum", surface_condition="oxidized")
        )
        self.assertEqual(normalized["material"], "aluminium")
        self.assertEqual(normalized["surface_condition"], logic.AS_RECEIVED)

    def test_non_mapping_raises(self):
        with self.assertRaises(ValueError):
            logic.validate_measured_record("aluminium")

    def test_inverted_energy_span_raises(self):
        with self.assertRaises(ValueError):
            logic.validate_measured_record(
                measured_record(energy_min_ev=3000.0, energy_max_ev=10.0)
            )

    def test_non_positive_energy_raises(self):
        with self.assertRaises(ValueError):
            logic.validate_measured_record(measured_record(energy_min_ev=0.0))

    def test_zero_specimen_count_raises(self):
        with self.assertRaises(ValueError):
            logic.validate_measured_record(measured_record(specimen_count=0))

    def test_non_integer_specimen_count_raises(self):
        with self.assertRaises(ValueError):
            logic.validate_measured_record(measured_record(specimen_count=2.5))

    def test_non_positive_peak_parameter_raises(self):
        with self.assertRaises(ValueError):
            logic.validate_measured_record(measured_record(delta_max=0.0))


class TestAssessRepresentativeness(unittest.TestCase):
    def test_matching_record_is_representative(self):
        ok, reasons = logic.assess_representativeness(
            measured_record(), "aluminium", "as-received", REQUIRED_SPAN
        )
        self.assertTrue(ok)
        self.assertEqual(reasons, [])

    def test_span_endpoint_exactly_met_is_still_covered(self):
        # The required upper endpoint evaluates a few ULPs above 300.0; a
        # record that genuinely reaches 300 eV must not be rejected by that.
        required_hi = (0.1 + 0.2) * 1000.0
        self.assertGreater(required_hi, 300.0)
        ok, reasons = logic.assess_representativeness(
            measured_record(energy_max_ev=300.0),
            "aluminium",
            "as-received",
            (10.0, required_hi),
        )
        self.assertTrue(ok)
        self.assertEqual(reasons, [])

    def test_material_mismatch_is_a_reason(self):
        ok, reasons = logic.assess_representativeness(
            measured_record(material="copper"), "aluminium", "as-received", REQUIRED_SPAN
        )
        self.assertFalse(ok)
        self.assertTrue(any("flight material" in r for r in reasons))

    def test_surface_condition_mismatch_is_a_reason(self):
        ok, reasons = logic.assess_representativeness(
            measured_record(surface_condition="sputter-cleaned"),
            "aluminium",
            "as-received",
            REQUIRED_SPAN,
        )
        self.assertFalse(ok)
        self.assertTrue(any("surface condition" in r for r in reasons))

    def test_energy_span_shortfall_is_a_reason(self):
        ok, reasons = logic.assess_representativeness(
            measured_record(energy_max_ev=500.0),
            "aluminium",
            "as-received",
            REQUIRED_SPAN,
        )
        self.assertFalse(ok)
        self.assertTrue(any("energy span" in r for r in reasons))

    def test_single_specimen_is_a_reason(self):
        ok, reasons = logic.assess_representativeness(
            measured_record(specimen_count=1),
            "aluminium",
            "as-received",
            REQUIRED_SPAN,
        )
        self.assertFalse(ok)
        self.assertTrue(any("specimen" in r for r in reasons))

    def test_several_failures_are_all_reported(self):
        ok, reasons = logic.assess_representativeness(
            measured_record(material="copper", specimen_count=1),
            "aluminium",
            "as-received",
            REQUIRED_SPAN,
        )
        self.assertFalse(ok)
        self.assertEqual(len(reasons), 2)

    def test_malformed_span_raises(self):
        with self.assertRaises(ValueError):
            logic.assess_representativeness(
                measured_record(), "aluminium", "as-received", (2000.0, 20.0)
            )

    def test_span_of_wrong_length_raises(self):
        with self.assertRaises(ValueError):
            logic.assess_representativeness(
                measured_record(), "aluminium", "as-received", (20.0,)
            )


class TestSelectYieldSource(unittest.TestCase):
    def test_representative_record_is_used_as_measured(self):
        source = logic.select_yield_source(
            measured_record(), "aluminium", "as-received", REQUIRED_SPAN
        )
        self.assertEqual(source["provenance"], logic.MEASURED)
        self.assertAlmostEqual(source["delta_max"], 2.15, places=9)
        self.assertEqual(source["fallback_reasons"], [])

    def test_non_representative_record_falls_back_with_reasons(self):
        source = logic.select_yield_source(
            measured_record(specimen_count=1), "aluminium", "as-received", REQUIRED_SPAN
        )
        self.assertEqual(source["provenance"], logic.TABULATED_FALLBACK)
        self.assertAlmostEqual(source["delta_max"], 2.40, places=9)
        self.assertTrue(source["fallback_reasons"])

    def test_absent_record_falls_back_and_says_so(self):
        source = logic.select_yield_source(
            None, "gold", "sputter-cleaned", REQUIRED_SPAN
        )
        self.assertEqual(source["provenance"], logic.TABULATED_FALLBACK)
        self.assertAlmostEqual(source["delta_max"], 1.45, places=9)
        self.assertTrue(any("no measured record" in r for r in source["fallback_reasons"]))

    def test_fallback_declaration_names_the_clause(self):
        source = logic.select_yield_source(
            None, "copper", "as-received", REQUIRED_SPAN
        )
        self.assertIn("9.6", source["declaration"])

    def test_material_outside_the_table_is_refused(self):
        with self.assertRaises(ValueError):
            logic.select_yield_source(None, "kapton", "as-received", REQUIRED_SPAN)

    def test_non_representative_record_for_an_untabulated_material_is_refused(self):
        with self.assertRaises(ValueError):
            logic.select_yield_source(
                measured_record(material="copper"), "kapton", "as-received", REQUIRED_SPAN
            )


class TestEvaluateSurface(unittest.TestCase):
    def test_measured_path_reports_points_and_crossovers(self):
        result = logic.evaluate_surface(
            measured_record(), "aluminium", "as-received", REQUIRED_SPAN, [100.0, 310.0]
        )
        self.assertEqual(result["provenance"], logic.MEASURED)
        self.assertEqual(len(result["points"]), 2)
        self.assertIsNotNone(result["crossovers"])
        self.assertLess(
            result["crossovers"]["first_ev"], result["crossovers"]["second_ev"]
        )

    def test_fallback_path_uses_the_tabulated_parameters(self):
        result = logic.evaluate_surface(
            None, "stainless-steel", "as-received", REQUIRED_SPAN, [300.0]
        )
        self.assertEqual(result["provenance"], logic.TABULATED_FALLBACK)
        self.assertAlmostEqual(result["delta_max"], 2.10, places=9)
        self.assertAlmostEqual(result["e_max_ev"], 350.0, places=9)

    def test_low_yield_surface_reports_no_crossover_window(self):
        result = logic.evaluate_surface(
            None, "titanium", "sputter-cleaned", REQUIRED_SPAN, [280.0]
        )
        self.assertIsNone(result["crossovers"])
        self.assertEqual(
            result["points"][0]["disposition"],
            "net-electron-absorption-negative-drift",
        )

    def test_each_point_carries_a_yield_and_a_disposition(self):
        result = logic.evaluate_surface(
            None, "silver", "as-received", REQUIRED_SPAN, [50.0, 800.0, 30000.0]
        )
        dispositions = [p["disposition"] for p in result["points"]]
        self.assertEqual(dispositions[1], "net-secondary-emission-positive-drift")
        self.assertEqual(dispositions[0], "net-electron-absorption-negative-drift")
        self.assertEqual(dispositions[2], "net-electron-absorption-negative-drift")

    def test_empty_energy_list_raises(self):
        with self.assertRaises(ValueError):
            logic.evaluate_surface(
                None, "gold", "as-received", REQUIRED_SPAN, []
            )

    def test_non_sequence_energy_list_raises(self):
        with self.assertRaises(ValueError):
            logic.evaluate_surface(
                None, "gold", "as-received", REQUIRED_SPAN, 300.0
            )


if __name__ == "__main__":
    unittest.main()
