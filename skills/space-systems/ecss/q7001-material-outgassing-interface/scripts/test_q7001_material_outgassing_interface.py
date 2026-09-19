"""Contract tests for the sensitive-surface outgassing screening logic."""

import unittest

from q7001_material_outgassing_interface_logic import (
    BUDGET_TOLERANCE_NG_CM2,
    CVCM_LIMIT_PCT,
    SURFACE_GRADES,
    TML_LIMIT_PCT,
    areal_deposit_ng_cm2,
    assess_material_interface,
    budget_findings,
    condensation_fraction,
    disposition,
    effective_mass_loss_pct,
    normalise_identifier,
    screening_findings,
    screening_limits,
    surface_grade,
    validate_outgassing_record,
)

CLEAN = {"material": "Epoxy-Adhesive-A", "tml_pct": 0.42, "cvcm_pct": 0.01}
WET = {"material": "polyimide-film", "tml_pct": 1.40, "cvcm_pct": 0.02,
       "water_vapour_regain_pct": 0.90}
TACKY = {"material": "silicone-potting", "tml_pct": 0.80, "cvcm_pct": 0.22}


def _spec(**overrides):
    spec = {
        "record": dict(CLEAN),
        "surface": "optical-window",
        "exposed_mass_g": 20.0,
        "view_factor": 0.2,
        "surface_area_cm2": 100.0,
        "source_temp_c": 60.0,
        "surface_temp_c": 0.0,
    }
    spec.update(overrides)
    return spec


class NormaliseIdentifierTests(unittest.TestCase):
    def test_trims_and_lowercases(self):
        self.assertEqual(normalise_identifier("  Silicone-A  ", "material"),
                         "silicone-a")

    def test_empty_rejected(self):
        with self.assertRaises(ValueError):
            normalise_identifier("   ", "material")

    def test_non_string_rejected(self):
        with self.assertRaises(ValueError):
            normalise_identifier(7, "material")


class ValidateRecordTests(unittest.TestCase):
    def test_minimal_record_normalised(self):
        record = validate_outgassing_record(CLEAN)
        self.assertEqual(record["material"], "epoxy-adhesive-a")
        self.assertAlmostEqual(record["tml_pct"], 0.42, places=9)
        self.assertIsNone(record["rml_pct"])

    def test_regain_derives_recovered_mass_loss(self):
        record = validate_outgassing_record(WET)
        self.assertAlmostEqual(record["rml_pct"], 0.50, places=9)

    def test_inconsistent_triple_rejected(self):
        bad = dict(WET)
        bad["rml_pct"] = 0.20
        with self.assertRaises(ValueError):
            validate_outgassing_record(bad)

    def test_consistent_triple_accepted(self):
        good = dict(WET)
        good["rml_pct"] = 0.50
        self.assertAlmostEqual(
            validate_outgassing_record(good)["rml_pct"], 0.50, places=9
        )

    def test_condensable_above_total_rejected(self):
        with self.assertRaises(ValueError):
            validate_outgassing_record(
                {"material": "x", "tml_pct": 0.10, "cvcm_pct": 0.40}
            )

    def test_recovered_above_total_rejected(self):
        with self.assertRaises(ValueError):
            validate_outgassing_record(
                {"material": "x", "tml_pct": 0.50, "cvcm_pct": 0.01, "rml_pct": 0.90}
            )

    def test_regain_above_total_rejected(self):
        with self.assertRaises(ValueError):
            validate_outgassing_record(
                {"material": "x", "tml_pct": 0.50, "cvcm_pct": 0.01,
                 "water_vapour_regain_pct": 0.90}
            )

    def test_negative_percentage_rejected(self):
        with self.assertRaises(ValueError):
            validate_outgassing_record(
                {"material": "x", "tml_pct": -0.10, "cvcm_pct": 0.01}
            )

    def test_percentage_above_hundred_rejected(self):
        with self.assertRaises(ValueError):
            validate_outgassing_record(
                {"material": "x", "tml_pct": 140.0, "cvcm_pct": 0.01}
            )

    def test_missing_key_rejected(self):
        with self.assertRaises(ValueError):
            validate_outgassing_record({"material": "x", "tml_pct": 0.5})

    def test_non_mapping_rejected(self):
        with self.assertRaises(ValueError):
            validate_outgassing_record(["material", "x"])

    def test_boolean_percentage_rejected(self):
        with self.assertRaises(ValueError):
            validate_outgassing_record(
                {"material": "x", "tml_pct": True, "cvcm_pct": 0.01}
            )


class EffectiveMassLossTests(unittest.TestCase):
    def test_total_used_when_no_regain_measured(self):
        record = validate_outgassing_record(CLEAN)
        self.assertAlmostEqual(effective_mass_loss_pct(record), 0.42, places=9)

    def test_recovered_used_when_regain_measured(self):
        record = validate_outgassing_record(WET)
        self.assertAlmostEqual(effective_mass_loss_pct(record), 0.50, places=9)

    def test_non_record_rejected(self):
        with self.assertRaises(ValueError):
            effective_mass_loss_pct("0.42")


class SurfaceGradeTests(unittest.TestCase):
    def test_known_grade_returned(self):
        grade = surface_grade("Optical-Window")
        self.assertEqual(grade["surface"], "optical-window")
        self.assertAlmostEqual(grade["budget_ng_cm2"], 40.0, places=9)

    def test_unknown_grade_rejected(self):
        with self.assertRaises(ValueError):
            surface_grade("gold-plated-nothing")

    def test_every_grade_has_a_positive_budget(self):
        for name, entry in SURFACE_GRADES.items():
            self.assertGreater(entry["budget_ng_cm2"], 0.0, name)

    def test_detector_limit_is_tighter_than_structure(self):
        detector = screening_limits("cryogenic-detector")["cvcm_limit_pct"]
        structure = screening_limits("structure")["cvcm_limit_pct"]
        self.assertLess(detector, structure)

    def test_structure_limit_is_the_baseline(self):
        self.assertAlmostEqual(
            screening_limits("structure")["cvcm_limit_pct"], CVCM_LIMIT_PCT, places=9
        )

    def test_mass_loss_limit_is_grade_independent(self):
        self.assertAlmostEqual(
            screening_limits("cryogenic-detector")["mass_loss_limit_pct"],
            TML_LIMIT_PCT,
            places=9,
        )


class ScreeningFindingTests(unittest.TestCase):
    def test_clean_material_has_no_findings(self):
        result = screening_findings(validate_outgassing_record(CLEAN), "optical-window")
        self.assertEqual(result["findings"], [])

    def test_condensable_exceedance_named(self):
        result = screening_findings(validate_outgassing_record(TACKY), "structure")
        self.assertTrue(result["cvcm_exceeded"])
        self.assertFalse(result["mass_loss_exceeded"])

    def test_regain_rescues_a_wet_material(self):
        result = screening_findings(validate_outgassing_record(WET), "structure")
        self.assertFalse(result["mass_loss_exceeded"])

    def test_total_alone_would_have_failed_the_wet_material(self):
        dry = {"material": "polyimide-film", "tml_pct": 1.40, "cvcm_pct": 0.02}
        result = screening_findings(validate_outgassing_record(dry), "structure")
        self.assertTrue(result["mass_loss_exceeded"])

    def test_material_exactly_on_the_limit_passes(self):
        record = validate_outgassing_record(
            {"material": "x", "tml_pct": TML_LIMIT_PCT, "cvcm_pct": CVCM_LIMIT_PCT}
        )
        result = screening_findings(record, "structure")
        self.assertFalse(result["mass_loss_exceeded"])
        self.assertFalse(result["cvcm_exceeded"])

    def test_grade_tightening_can_fail_a_baseline_pass(self):
        record = validate_outgassing_record(
            {"material": "x", "tml_pct": 0.5, "cvcm_pct": 0.08}
        )
        self.assertFalse(screening_findings(record, "structure")["cvcm_exceeded"])
        self.assertTrue(
            screening_findings(record, "cryogenic-detector")["cvcm_exceeded"]
        )


class CondensationFractionTests(unittest.TestCase):
    def test_no_transfer_to_a_warmer_collector(self):
        self.assertAlmostEqual(condensation_fraction(10.0, 40.0), 0.0, places=9)

    def test_no_transfer_at_equal_temperature(self):
        self.assertAlmostEqual(condensation_fraction(20.0, 20.0), 0.0, places=9)

    def test_full_transfer_beyond_the_span(self):
        self.assertAlmostEqual(condensation_fraction(80.0, 0.0), 1.0, places=9)

    def test_span_boundary_is_full_transfer(self):
        self.assertAlmostEqual(condensation_fraction(40.0, 0.0), 1.0, places=9)

    def test_half_span_is_half_transfer(self):
        self.assertAlmostEqual(condensation_fraction(20.0, 0.0), 0.5, places=9)

    def test_cryogenic_collector_accepts_negative_temperatures(self):
        self.assertAlmostEqual(condensation_fraction(-40.0, -80.0), 1.0, places=9)

    def test_non_finite_temperature_rejected(self):
        with self.assertRaises(ValueError):
            condensation_fraction(float("nan"), 0.0)

    def test_non_positive_span_rejected(self):
        with self.assertRaises(ValueError):
            condensation_fraction(60.0, 0.0, span_c=0.0)


class ArealDepositTests(unittest.TestCase):
    def test_deposit_is_the_transported_condensable_fraction(self):
        record = validate_outgassing_record(CLEAN)
        value = areal_deposit_ng_cm2(record, 20.0, 0.5, 100.0, 80.0, 0.0)
        self.assertAlmostEqual(value, 10000.0, places=6)

    def test_zero_view_factor_deposits_nothing(self):
        record = validate_outgassing_record(CLEAN)
        self.assertAlmostEqual(
            areal_deposit_ng_cm2(record, 20.0, 0.0, 100.0, 80.0, 0.0), 0.0, places=9
        )

    def test_cold_source_deposits_nothing(self):
        record = validate_outgassing_record(CLEAN)
        self.assertAlmostEqual(
            areal_deposit_ng_cm2(record, 20.0, 0.5, 100.0, -20.0, 0.0), 0.0, places=9
        )

    def test_deposit_halves_with_double_surface_area(self):
        record = validate_outgassing_record(CLEAN)
        small = areal_deposit_ng_cm2(record, 20.0, 0.5, 100.0, 80.0, 0.0)
        large = areal_deposit_ng_cm2(record, 20.0, 0.5, 200.0, 80.0, 0.0)
        self.assertAlmostEqual(large, small / 2.0, places=6)

    def test_view_factor_above_unity_rejected(self):
        record = validate_outgassing_record(CLEAN)
        with self.assertRaises(ValueError):
            areal_deposit_ng_cm2(record, 20.0, 1.4, 100.0, 80.0, 0.0)

    def test_zero_surface_area_rejected(self):
        record = validate_outgassing_record(CLEAN)
        with self.assertRaises(ValueError):
            areal_deposit_ng_cm2(record, 20.0, 0.5, 0.0, 80.0, 0.0)

    def test_zero_exposed_mass_rejected(self):
        record = validate_outgassing_record(CLEAN)
        with self.assertRaises(ValueError):
            areal_deposit_ng_cm2(record, 0.0, 0.5, 100.0, 80.0, 0.0)


class BudgetFindingTests(unittest.TestCase):
    def test_deposit_under_budget_is_silent(self):
        self.assertEqual(budget_findings(10.0, 40.0), [])

    def test_deposit_on_budget_is_silent(self):
        self.assertEqual(budget_findings(40.0, 40.0), [])

    def test_deposit_a_hair_over_budget_within_tolerance_is_silent(self):
        self.assertEqual(
            budget_findings(40.0 + BUDGET_TOLERANCE_NG_CM2 / 2.0, 40.0), []
        )

    def test_deposit_over_budget_reported(self):
        self.assertEqual(len(budget_findings(400.0, 40.0)), 1)

    def test_non_positive_budget_rejected(self):
        with self.assertRaises(ValueError):
            budget_findings(10.0, 0.0)


class DispositionTests(unittest.TestCase):
    def _screening(self, mass_loss=False, cvcm=False):
        return {"mass_loss_exceeded": mass_loss, "cvcm_exceeded": cvcm}

    def test_clean_material_accepted(self):
        self.assertEqual(disposition(self._screening(), False, False), "accepted")

    def test_mass_loss_exceedance_goes_to_bakeout(self):
        self.assertEqual(
            disposition(self._screening(mass_loss=True), False, False),
            "vacuum-bakeout-and-retest",
        )

    def test_condensable_exceedance_is_refused_in_view(self):
        self.assertEqual(
            disposition(self._screening(cvcm=True), False, False),
            "refused-in-view-of-surface",
        )

    def test_condensable_exceedance_dominates_mass_loss(self):
        self.assertEqual(
            disposition(self._screening(mass_loss=True, cvcm=True), True, False),
            "refused-in-view-of-surface",
        )

    def test_shielding_accepts_whatever_the_screening_said(self):
        self.assertEqual(
            disposition(self._screening(cvcm=True), True, True),
            "accepted-behind-shield",
        )

    def test_budget_exceedance_alone_relocates(self):
        self.assertEqual(
            disposition(self._screening(), True, False),
            "relocate-or-reduce-exposed-area",
        )

    def test_malformed_screening_rejected(self):
        with self.assertRaises(ValueError):
            disposition({"mass_loss_exceeded": False}, False, False)


class AssessMaterialInterfaceTests(unittest.TestCase):
    def test_clean_interface_accepted(self):
        result = assess_material_interface(_spec(exposed_mass_g=0.01))
        self.assertEqual(result["disposition"], "accepted")
        self.assertTrue(result["within_budget"])
        self.assertEqual(result["findings"], [])

    def test_large_exposed_mass_breaks_the_budget(self):
        result = assess_material_interface(_spec(exposed_mass_g=500.0))
        self.assertFalse(result["within_budget"])
        self.assertEqual(result["disposition"], "relocate-or-reduce-exposed-area")

    def test_tacky_material_refused_in_view_of_a_window(self):
        result = assess_material_interface(_spec(record=dict(TACKY)))
        self.assertEqual(result["disposition"], "refused-in-view-of-surface")

    def test_shielded_tacky_material_accepted_with_a_note(self):
        result = assess_material_interface(
            _spec(record=dict(TACKY), view_factor=0.0)
        )
        self.assertEqual(result["disposition"], "accepted-behind-shield")
        self.assertTrue(any("line of sight" in f for f in result["findings"]))

    def test_regain_reported_material_keeps_its_recovered_figure(self):
        result = assess_material_interface(
            _spec(record=dict(WET), exposed_mass_g=0.01)
        )
        self.assertAlmostEqual(result["mass_loss_pct"], 0.50, places=9)
        self.assertEqual(result["disposition"], "accepted")

    def test_surface_grade_carries_its_own_budget(self):
        window = assess_material_interface(_spec(surface="optical-window"))
        radiator = assess_material_interface(_spec(surface="thermal-radiator"))
        self.assertLess(window["budget_ng_cm2"], radiator["budget_ng_cm2"])

    def test_missing_spec_key_rejected(self):
        spec = _spec()
        del spec["view_factor"]
        with self.assertRaises(ValueError):
            assess_material_interface(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_material_interface(["record"])

    def test_material_name_is_normalised_in_the_report(self):
        result = assess_material_interface(_spec(exposed_mass_g=0.01))
        self.assertEqual(result["material"], "epoxy-adhesive-a")


if __name__ == "__main__":
    unittest.main()
