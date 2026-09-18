"""Contract tests for the ECSS-Q-ST-70-31C paint application-method logic."""

import unittest

from q7031_application_methods_logic import (
    APPLICATION_TOLERANCE,
    APPROVED_METHODS,
    DEFAULT_APPLICATION_TEMPERATURE_C,
    DEFAULT_MAX_RELATIVE_HUMIDITY_PCT,
    DISPOSITIONS,
    METHODS_FOR_THIN_UNIFORM_FILMS,
    METHOD_PER_PASS_DFT_UM,
    METHOD_TRANSFER_EFFICIENCY,
    assess_application,
    environment_findings,
    method_findings,
    method_per_pass_dft_um,
    normalize_key,
    paint_volume_required_l,
    passes_required,
    recoat_findings,
    theoretical_coverage_m2_per_l,
    wet_film_thickness_um,
)


def record(**overrides):
    base = {
        "method": "hvlp-spray",
        "target_dft_um": 50.0,
        "volume_solids_fraction": 0.50,
        "area_m2": 12.0,
        "temperature_c": 22.0,
        "relative_humidity_pct": 45.0,
        "elapsed_since_previous_coat_h": 8.0,
    }
    base.update(overrides)
    return base


class MethodTableTests(unittest.TestCase):
    def test_per_pass_build_looked_up(self):
        self.assertAlmostEqual(method_per_pass_dft_um("hvlp-spray"),
                               METHOD_PER_PASS_DFT_UM["hvlp-spray"])

    def test_method_name_folded(self):
        self.assertAlmostEqual(method_per_pass_dft_um(" HVLP-Spray "),
                               METHOD_PER_PASS_DFT_UM["hvlp-spray"])

    def test_unknown_method_rejected(self):
        with self.assertRaises(ValueError):
            method_per_pass_dft_um("thrown-from-a-bucket")

    def test_every_method_has_a_transfer_efficiency(self):
        for method in APPROVED_METHODS:
            self.assertIn(method, METHOD_TRANSFER_EFFICIENCY)

    def test_thin_film_methods_are_a_subset_of_approved_methods(self):
        for method in METHODS_FOR_THIN_UNIFORM_FILMS:
            self.assertIn(method, APPROVED_METHODS)

    def test_key_helper_rejects_blank(self):
        with self.assertRaises(ValueError):
            normalize_key("   ", "application method")


class FilmArithmeticTests(unittest.TestCase):
    def test_wet_film_is_dry_film_over_volume_solids(self):
        self.assertAlmostEqual(wet_film_thickness_um(50.0, 0.5), 100.0, places=9)

    def test_high_solids_needs_less_wet_film(self):
        self.assertLess(wet_film_thickness_um(50.0, 0.8),
                        wet_film_thickness_um(50.0, 0.4))

    def test_volume_solids_above_unity_rejected(self):
        with self.assertRaises(ValueError):
            wet_film_thickness_um(50.0, 1.4)

    def test_zero_volume_solids_rejected(self):
        with self.assertRaises(ValueError):
            wet_film_thickness_um(50.0, 0.0)

    def test_exact_multiple_needs_no_extra_pass(self):
        self.assertEqual(passes_required(50.0, 25.0), 2)

    def test_partial_pass_rounds_up(self):
        self.assertEqual(passes_required(60.0, 25.0), 3)

    def test_thin_target_still_needs_one_pass(self):
        self.assertEqual(passes_required(5.0, 25.0), 1)

    def test_representation_error_does_not_add_a_pass(self):
        target = 75.0 + APPLICATION_TOLERANCE / 2.0
        self.assertEqual(passes_required(target, 25.0), 3)

    def test_negative_target_rejected(self):
        with self.assertRaises(ValueError):
            passes_required(-10.0, 25.0)

    def test_coverage_falls_as_the_film_thickens(self):
        self.assertAlmostEqual(theoretical_coverage_m2_per_l(50.0, 0.5), 10.0, places=9)
        self.assertAlmostEqual(theoretical_coverage_m2_per_l(100.0, 0.5), 5.0, places=9)

    def test_volume_includes_transfer_losses(self):
        got = paint_volume_required_l(10.0, 50.0, 0.5, 0.5)
        self.assertAlmostEqual(got, 2.0, places=9)

    def test_perfect_transfer_needs_only_the_theoretical_volume(self):
        got = paint_volume_required_l(10.0, 50.0, 0.5, 1.0)
        self.assertAlmostEqual(got, 1.0, places=9)

    def test_transfer_efficiency_above_unity_rejected(self):
        with self.assertRaises(ValueError):
            paint_volume_required_l(10.0, 50.0, 0.5, 1.2)


class MethodApprovalTests(unittest.TestCase):
    def test_listed_method_is_approved(self):
        got = method_findings("hvlp-spray", {"approved_methods": ["hvlp-spray", "brush"]})
        self.assertEqual(got, [])

    def test_unlisted_method_reported(self):
        got = method_findings("roller", {"approved_methods": ["hvlp-spray", "brush"]})
        self.assertIn("method-not-on-the-approved-list", got)

    def test_unrecognised_method_reported(self):
        got = method_findings("thrown-from-a-bucket", {})
        self.assertEqual(got, ["application-method-not-recognised"])

    def test_brush_cannot_hold_a_thermo_optical_film(self):
        got = method_findings("brush", {"thermo_optical_surface": True})
        self.assertIn("method-cannot-hold-a-thermo-optical-film", got)

    def test_spray_can_hold_a_thermo_optical_film(self):
        got = method_findings("conventional-spray", {"thermo_optical_surface": True})
        self.assertEqual(got, [])

    def test_dipping_cannot_respect_a_keep_out_area(self):
        got = method_findings("dip", {"keep_out_areas": ["connector-face"]})
        self.assertIn("dip-cannot-respect-a-keep-out-area", got)

    def test_approved_methods_must_be_a_sequence(self):
        with self.assertRaises(ValueError):
            method_findings("brush", {"approved_methods": "brush"})


class RecoatTests(unittest.TestCase):
    def test_inside_the_interval_is_clean(self):
        self.assertEqual(recoat_findings(8.0, 4.0, 72.0), [])

    def test_too_soon_reported(self):
        self.assertIn("recoated-before-the-minimum-interval",
                      recoat_findings(1.0, 4.0, 72.0))

    def test_too_late_reported(self):
        self.assertIn("recoated-after-the-maximum-interval",
                      recoat_findings(120.0, 4.0, 72.0))

    def test_exactly_at_the_minimum_is_clean(self):
        self.assertEqual(recoat_findings(4.0, 4.0, 72.0), [])

    def test_exactly_at_the_maximum_is_clean(self):
        self.assertEqual(recoat_findings(72.0, 4.0, 72.0), [])

    def test_inverted_interval_rejected(self):
        with self.assertRaises(ValueError):
            recoat_findings(8.0, 72.0, 4.0)


class EnvironmentTests(unittest.TestCase):
    def test_conditions_inside_the_window_are_clean(self):
        self.assertEqual(environment_findings(22.0, 45.0), [])

    def test_cold_room_reported(self):
        self.assertIn("application-temperature-below-window",
                      environment_findings(5.0, 45.0))

    def test_hot_room_reported(self):
        self.assertIn("application-temperature-above-window",
                      environment_findings(40.0, 45.0))

    def test_humid_room_reported(self):
        self.assertIn("application-humidity-over-ceiling",
                      environment_findings(22.0, 88.0))

    def test_exactly_at_the_window_edges_is_clean(self):
        low, high = DEFAULT_APPLICATION_TEMPERATURE_C
        self.assertEqual(environment_findings(low, DEFAULT_MAX_RELATIVE_HUMIDITY_PCT), [])
        self.assertEqual(environment_findings(high, 40.0), [])

    def test_window_may_be_overridden(self):
        self.assertEqual(environment_findings(5.0, 45.0, window=(0.0, 35.0)), [])

    def test_humidity_above_saturation_rejected(self):
        with self.assertRaises(ValueError):
            environment_findings(22.0, 140.0)


class DispositionTests(unittest.TestCase):
    def test_well_run_application_is_compliant(self):
        out = assess_application(record())
        self.assertEqual(out["disposition"], "compliant")
        self.assertAlmostEqual(out["wft_um"], 100.0, places=9)
        self.assertEqual(out["passes"], 2)

    def test_unapproved_method_short_circuits_the_sizing(self):
        out = assess_application(record(method="brush", thermo_optical_surface=True))
        self.assertEqual(out["disposition"], "method-not-approved")
        self.assertIsNone(out["passes"])

    def test_recoat_violation_is_rework(self):
        out = assess_application(record(elapsed_since_previous_coat_h=0.5))
        self.assertEqual(out["disposition"], "rework-required")
        self.assertIn("recoated-before-the-minimum-interval", out["findings"])

    def test_bad_conditions_are_rework(self):
        out = assess_application(record(relative_humidity_pct=90.0))
        self.assertEqual(out["disposition"], "rework-required")

    def test_volume_uses_the_method_transfer_efficiency(self):
        out = assess_application(record())
        expected = paint_volume_required_l(
            12.0, 50.0, 0.5, METHOD_TRANSFER_EFFICIENCY["hvlp-spray"]
        )
        self.assertAlmostEqual(out["volume_l"], expected, places=9)

    def test_per_pass_build_may_be_overridden(self):
        out = assess_application(record(per_pass_dft_um=10.0))
        self.assertEqual(out["passes"], 5)

    def test_missing_record_key_rejected(self):
        spec = record()
        del spec["area_m2"]
        with self.assertRaises(ValueError):
            assess_application(spec)

    def test_non_mapping_record_rejected(self):
        with self.assertRaises(ValueError):
            assess_application(["hvlp-spray"])

    def test_every_disposition_is_a_declared_one(self):
        for spec in (record(), record(relative_humidity_pct=95.0),
                     record(method="dip", keep_out_areas=["connector-face"])):
            self.assertIn(assess_application(spec)["disposition"], DISPOSITIONS)


if __name__ == "__main__":
    unittest.main()
