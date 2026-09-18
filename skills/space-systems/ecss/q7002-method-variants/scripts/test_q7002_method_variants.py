"""Contract test for the outgassing method-variants leaf (stdlib unittest)."""

import unittest

from q7002_method_variants_logic import (
    DIRECTLY_COMPARABLE,
    EXTENDED_BAKE_DURATION,
    EXTENDED_PRECONDITIONING,
    MIN_BAKE_TEMPERATURE_C,
    NOT_DIRECTLY_COMPARABLE,
    REDUCED_BAKE_TEMPERATURE,
    STANDARD_BAKE_DURATION_H,
    STANDARD_BAKE_TEMPERATURE_C,
    STANDARD_PRECONDITIONING_DURATION_H,
    VALID_VARIANTS,
    WATER_VAPOUR_REGAINED,
    assess_method_variants,
    check_variant_settings,
    comparability,
    indicated_variants,
    recovered_mass_loss_pct,
    validate_request,
    variant_record,
    water_vapour_regained_pct,
)


def hygroscopic():
    return {"moisture_uptake_pct": 0.90}


def request(**kw):
    record = {
        "applied_variants": [WATER_VAPOUR_REGAINED, EXTENDED_PRECONDITIONING],
        "preconditioning_duration_h": 48.0,
        "reconditioning_duration_h": 24.0,
        "material": hygroscopic(),
    }
    record.update(kw)
    return record


class TestVariantRegistry(unittest.TestCase):
    def test_every_variant_declares_what_it_alters(self):
        for name in VALID_VARIANTS:
            self.assertIn("alters", variant_record(name))

    def test_the_water_variant_keeps_results_comparable(self):
        self.assertTrue(variant_record(WATER_VAPOUR_REGAINED)["comparable"])

    def test_a_reduced_bake_does_not(self):
        self.assertFalse(variant_record(REDUCED_BAKE_TEMPERATURE)["comparable"])

    def test_an_unknown_variant_raises(self):
        with self.assertRaises(ValueError):
            variant_record("bake-it-until-it-passes")

    def test_the_returned_record_is_a_copy(self):
        record = variant_record(WATER_VAPOUR_REGAINED)
        record["comparable"] = False
        self.assertTrue(variant_record(WATER_VAPOUR_REGAINED)["comparable"])


class TestIndication(unittest.TestCase):
    def test_a_hygroscopic_material_indicates_two_variants(self):
        indicated = indicated_variants(hygroscopic())
        self.assertIn(WATER_VAPOUR_REGAINED, indicated)
        self.assertIn(EXTENDED_PRECONDITIONING, indicated)

    def test_a_dry_material_indicates_nothing(self):
        self.assertEqual(indicated_variants({"moisture_uptake_pct": 0.05}), [])

    def test_a_low_use_temperature_indicates_a_reduced_bake(self):
        self.assertIn(
            REDUCED_BAKE_TEMPERATURE,
            indicated_variants({"maximum_use_temperature_c": 80.0}),
        )

    def test_a_use_temperature_at_the_screening_temperature_does_not(self):
        self.assertEqual(
            indicated_variants(
                {"maximum_use_temperature_c": STANDARD_BAKE_TEMPERATURE_C}
            ),
            [],
        )

    def test_a_thick_specimen_indicates_a_longer_bake(self):
        self.assertIn(
            EXTENDED_BAKE_DURATION, indicated_variants({"specimen_thickness_mm": 8.0})
        )

    def test_an_empty_material_indicates_nothing(self):
        self.assertEqual(indicated_variants({}), [])

    def test_a_non_mapping_material_raises(self):
        with self.assertRaises(ValueError):
            indicated_variants("epoxy")


class TestValidateRequest(unittest.TestCase):
    def test_a_valid_request_is_normalized(self):
        norm = validate_request(request())
        self.assertEqual(
            norm["applied_variants"],
            sorted([WATER_VAPOUR_REGAINED, EXTENDED_PRECONDITIONING]),
        )
        self.assertAlmostEqual(
            norm["bake_temperature_c"], STANDARD_BAKE_TEMPERATURE_C, places=9
        )

    def test_a_bake_above_the_screening_temperature_raises(self):
        with self.assertRaises(ValueError):
            validate_request(request(bake_temperature_c=200.0))

    def test_a_bake_below_the_method_floor_raises(self):
        with self.assertRaises(ValueError):
            validate_request(request(bake_temperature_c=MIN_BAKE_TEMPERATURE_C - 10.0))

    def test_a_bake_exactly_at_the_method_floor_is_accepted(self):
        norm = validate_request(
            request(
                applied_variants=[
                    WATER_VAPOUR_REGAINED,
                    EXTENDED_PRECONDITIONING,
                    REDUCED_BAKE_TEMPERATURE,
                ],
                bake_temperature_c=MIN_BAKE_TEMPERATURE_C,
            )
        )
        self.assertAlmostEqual(
            norm["bake_temperature_c"], MIN_BAKE_TEMPERATURE_C, places=9
        )

    def test_a_short_preconditioning_raises(self):
        with self.assertRaises(ValueError):
            validate_request(request(preconditioning_duration_h=6.0))

    def test_a_short_bake_raises(self):
        with self.assertRaises(ValueError):
            validate_request(request(bake_duration_h=4.0))

    def test_a_duplicated_variant_raises(self):
        with self.assertRaises(ValueError):
            validate_request(
                request(applied_variants=[WATER_VAPOUR_REGAINED, WATER_VAPOUR_REGAINED])
            )

    def test_a_non_sequence_variant_list_raises(self):
        with self.assertRaises(ValueError):
            validate_request(request(applied_variants=WATER_VAPOUR_REGAINED))

    def test_a_non_mapping_request_raises(self):
        with self.assertRaises(ValueError):
            validate_request("water-vapour-regained")


class TestVariantSettings(unittest.TestCase):
    def test_a_consistent_request_has_no_settings_findings(self):
        self.assertEqual(check_variant_settings(request()), [])

    def test_declaring_extended_preconditioning_at_the_baseline_is_a_finding(self):
        findings = check_variant_settings(
            request(preconditioning_duration_h=STANDARD_PRECONDITIONING_DURATION_H)
        )
        self.assertIn(
            "extended-preconditioning-declared-at-the-baseline-period", findings
        )

    def test_lengthening_preconditioning_undeclared_is_a_finding(self):
        findings = check_variant_settings(
            request(applied_variants=[WATER_VAPOUR_REGAINED])
        )
        self.assertIn(
            "preconditioning-lengthened-without-declaring-the-variant", findings
        )

    def test_lowering_the_bake_undeclared_is_a_finding(self):
        findings = check_variant_settings(request(bake_temperature_c=90.0))
        self.assertIn(
            "bake-temperature-lowered-without-declaring-the-variant", findings
        )

    def test_lengthening_the_bake_undeclared_is_a_finding(self):
        findings = check_variant_settings(
            request(bake_duration_h=STANDARD_BAKE_DURATION_H * 2.0)
        )
        self.assertIn("bake-lengthened-without-declaring-the-variant", findings)

    def test_the_water_variant_without_reconditioning_is_a_finding(self):
        findings = check_variant_settings(request(reconditioning_duration_h=None))
        self.assertIn(
            "water-vapour-variant-without-a-reconditioning-period", findings
        )

    def test_a_short_reconditioning_period_is_a_finding(self):
        findings = check_variant_settings(request(reconditioning_duration_h=2.0))
        self.assertIn(
            "reconditioning-period-shorter-than-the-method-requires", findings
        )

    def test_reconditioning_without_the_variant_is_a_finding(self):
        findings = check_variant_settings(
            request(applied_variants=[EXTENDED_PRECONDITIONING])
        )
        self.assertIn(
            "reconditioning-recorded-without-declaring-the-variant", findings
        )


class TestWaterVapourArithmetic(unittest.TestCase):
    def test_regained_mass_is_normalized_by_the_initial_mass(self):
        value = water_vapour_regained_pct(0.19880, 0.19960, 0.20000)
        self.assertAlmostEqual(value, 0.40, places=9)

    def test_no_regain_gives_zero(self):
        self.assertAlmostEqual(
            water_vapour_regained_pct(0.1988, 0.1988, 0.2), 0.0, places=12
        )

    def test_a_lighter_reconditioned_specimen_raises(self):
        with self.assertRaises(ValueError):
            water_vapour_regained_pct(0.1988, 0.1900, 0.2)

    def test_regaining_past_the_initial_mass_raises(self):
        with self.assertRaises(ValueError):
            water_vapour_regained_pct(0.1988, 0.2500, 0.2)

    def test_zero_initial_mass_raises(self):
        with self.assertRaises(ValueError):
            water_vapour_regained_pct(0.1988, 0.1996, 0.0)

    def test_recovered_loss_removes_the_regained_water(self):
        self.assertAlmostEqual(recovered_mass_loss_pct(1.20, 0.40), 0.80, places=9)

    def test_recovering_everything_leaves_zero(self):
        self.assertAlmostEqual(recovered_mass_loss_pct(0.60, 0.60), 0.0, places=12)

    def test_regaining_more_than_was_lost_raises(self):
        with self.assertRaises(ValueError):
            recovered_mass_loss_pct(0.40, 0.90)


class TestComparability(unittest.TestCase):
    def test_water_and_preconditioning_variants_stay_comparable(self):
        status, breaking = comparability(
            [WATER_VAPOUR_REGAINED, EXTENDED_PRECONDITIONING]
        )
        self.assertEqual(status, DIRECTLY_COMPARABLE)
        self.assertEqual(breaking, [])

    def test_a_reduced_bake_breaks_comparability(self):
        status, breaking = comparability([REDUCED_BAKE_TEMPERATURE])
        self.assertEqual(status, NOT_DIRECTLY_COMPARABLE)
        self.assertEqual(breaking, [REDUCED_BAKE_TEMPERATURE])

    def test_a_baseline_run_is_comparable(self):
        self.assertEqual(comparability([])[0], DIRECTLY_COMPARABLE)

    def test_a_non_sequence_variant_list_raises(self):
        with self.assertRaises(ValueError):
            comparability(REDUCED_BAKE_TEMPERATURE)


class TestAssessMethodVariants(unittest.TestCase):
    def test_a_matched_request_is_acceptable(self):
        report = assess_method_variants(request())
        self.assertTrue(report["acceptable"])
        self.assertEqual(report["comparability"], DIRECTLY_COMPARABLE)

    def test_an_indicated_variant_left_out_is_a_finding(self):
        report = assess_method_variants(
            request(
                applied_variants=[EXTENDED_PRECONDITIONING],
                reconditioning_duration_h=None,
            )
        )
        self.assertIn("indicated-variant-not-applied", report["findings"])
        self.assertIn(WATER_VAPOUR_REGAINED, report["missing_variants"])

    def test_a_variant_with_no_indicating_property_is_a_finding(self):
        report = assess_method_variants(
            request(
                material={"moisture_uptake_pct": 0.02},
                applied_variants=[
                    WATER_VAPOUR_REGAINED,
                    EXTENDED_PRECONDITIONING,
                    EXTENDED_BAKE_DURATION,
                ],
                bake_duration_h=48.0,
            )
        )
        self.assertIn(
            "variant-applied-without-an-indicating-material-property",
            report["findings"],
        )

    def test_a_reduced_bake_run_is_reported_as_not_comparable(self):
        report = assess_method_variants(
            request(
                material={"maximum_use_temperature_c": 90.0},
                applied_variants=[REDUCED_BAKE_TEMPERATURE],
                preconditioning_duration_h=STANDARD_PRECONDITIONING_DURATION_H,
                reconditioning_duration_h=None,
                bake_temperature_c=85.0,
            )
        )
        self.assertEqual(report["comparability"], NOT_DIRECTLY_COMPARABLE)
        self.assertEqual(
            report["comparability_breaking_variants"], [REDUCED_BAKE_TEMPERATURE]
        )

    def test_weighings_produce_the_regained_and_recovered_figures(self):
        report = assess_method_variants(
            request(
                weighings={
                    "initial_mass_g": 0.20000,
                    "mass_after_bake_g": 0.19880,
                    "mass_after_reconditioning_g": 0.19960,
                    "total_mass_loss_pct": 0.60,
                }
            )
        )
        self.assertAlmostEqual(report["water_vapour_regained_pct"], 0.40, places=9)
        self.assertAlmostEqual(report["recovered_mass_loss_pct"], 0.20, places=9)

    def test_without_weighings_no_figures_are_derived(self):
        report = assess_method_variants(request())
        self.assertIsNone(report["water_vapour_regained_pct"])
        self.assertIsNone(report["recovered_mass_loss_pct"])

    def test_a_non_mapping_material_raises(self):
        with self.assertRaises(ValueError):
            assess_method_variants(request(material="epoxy"))


if __name__ == "__main__":
    unittest.main()
