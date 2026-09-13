#!/usr/bin/env python3
"""Contract test for the composite antenna surface finish leaf.

Offline, deterministic, python3 standard library only.
Run: python3 test_e20_composite_antenna_surface_finish.py
"""

import math
import unittest

import e20_composite_antenna_surface_finish_logic as logic


def _reflecting_case(**overrides):
    case = {
        "finish_type": "metallized-face",
        "frequency_hz": 20.0e9,
        "rms_surface_error_m": 1.0e-4,
        "allocated_degradation_db": 0.20,
        "sheet_resistance_ohm_per_square": 0.05,
    }
    case.update(overrides)
    return case


def _coated_case(**overrides):
    case = {
        "finish_type": "coated-metallized-face",
        "frequency_hz": 20.0e9,
        "rms_surface_error_m": 1.0e-4,
        "allocated_degradation_db": 0.20,
        "sheet_resistance_ohm_per_square": 0.05,
        "coating_thickness_m": 1.5e-4,
        "coating_relative_permittivity": 3.0,
        "coating_loss_tangent": 0.01,
    }
    case.update(overrides)
    return case


class Wavelength(unittest.TestCase):
    def test_three_hundred_megahertz_is_about_one_metre(self):
        self.assertAlmostEqual(logic.wavelength_m(3.0e8), 0.99930819, places=6)

    def test_twenty_gigahertz_is_about_fifteen_millimetres(self):
        self.assertAlmostEqual(logic.wavelength_m(20.0e9), 0.01498962, places=8)

    def test_zero_frequency_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.wavelength_m(0.0)

    def test_negative_frequency_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.wavelength_m(-1.0e9)

    def test_non_numeric_frequency_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.wavelength_m("20 GHz")


class FinishCategorization(unittest.TestCase):
    def test_metallized_face_reflects_and_owes_no_layer(self):
        finish = logic.categorize_surface_finish("metallized-face")
        self.assertTrue(finish["rf_reflective"])
        self.assertFalse(finish["metallization_required"])

    def test_bare_woven_face_owes_a_metallization_layer(self):
        finish = logic.categorize_surface_finish("bare-woven-carbon-face")
        self.assertFalse(finish["rf_reflective"])
        self.assertTrue(finish["metallization_required"])

    def test_bare_woven_face_is_flagged_as_depolarising(self):
        self.assertTrue(
            logic.categorize_surface_finish("bare-woven-carbon-face")["depolarising_weave"]
        )

    def test_resin_rich_face_owes_a_layer_but_does_not_depolarise(self):
        finish = logic.categorize_surface_finish("resin-rich-face")
        self.assertTrue(finish["metallization_required"])
        self.assertFalse(finish["depolarising_weave"])

    def test_coated_metallized_face_carries_a_coating(self):
        self.assertTrue(
            logic.categorize_surface_finish("coated-metallized-face")["carries_coating"]
        )

    def test_case_and_whitespace_are_normalised(self):
        self.assertEqual(
            logic.categorize_surface_finish("  Metallized-Face ")["finish_type"],
            "metallized-face",
        )

    def test_uncategorized_finish_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.categorize_surface_finish("hand-waxed-face")

    def test_empty_finish_type_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.categorize_surface_finish("  ")

    def test_non_string_finish_type_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.categorize_surface_finish(None)


class SurfaceErrorLoss(unittest.TestCase):
    def test_a_perfect_face_costs_nothing(self):
        self.assertAlmostEqual(logic.ruze_gain_loss_db(0.0, 0.015), 0.0, places=12)

    def test_a_known_finish_matches_the_closed_form(self):
        loss = logic.ruze_gain_loss_db(1.0e-4, logic.wavelength_m(20.0e9))
        self.assertAlmostEqual(loss, 0.03052268, places=7)

    def test_doubling_the_surface_error_quadruples_the_loss(self):
        single = logic.ruze_gain_loss_db(1.0e-4, 0.015)
        double = logic.ruze_gain_loss_db(2.0e-4, 0.015)
        self.assertAlmostEqual(double / single, 4.0, places=9)

    def test_halving_the_wavelength_quadruples_the_loss(self):
        low = logic.ruze_gain_loss_db(1.0e-4, 0.030)
        high = logic.ruze_gain_loss_db(1.0e-4, 0.015)
        self.assertAlmostEqual(high / low, 4.0, places=9)

    def test_the_error_ratio_is_reported_directly(self):
        self.assertAlmostEqual(
            logic.surface_error_ratio(1.5e-4, 0.015), 0.01, places=12
        )

    def test_negative_surface_error_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.ruze_gain_loss_db(-1.0e-4, 0.015)

    def test_zero_wavelength_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.ruze_gain_loss_db(1.0e-4, 0.0)

    def test_surface_error_beyond_the_wavelength_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.ruze_gain_loss_db(0.020, 0.015)

    def test_negative_error_ratio_input_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.surface_error_ratio(-1.0e-4, 0.015)


class OhmicAndCoverage(unittest.TestCase):
    def test_a_perfect_conductor_costs_nothing(self):
        self.assertAlmostEqual(logic.ohmic_reflection_loss_db(0.0), 0.0, places=12)

    def test_a_known_sheet_resistance_matches_the_surface_impedance_result(self):
        self.assertAlmostEqual(logic.ohmic_reflection_loss_db(1.0), 0.04611208, places=7)

    def test_loss_climbs_with_sheet_resistance(self):
        self.assertGreater(
            logic.ohmic_reflection_loss_db(2.0), logic.ohmic_reflection_loss_db(1.0)
        )

    def test_negative_sheet_resistance_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.ohmic_reflection_loss_db(-0.1)

    def test_sheet_resistance_at_the_free_space_impedance_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.ohmic_reflection_loss_db(logic.FREE_SPACE_IMPEDANCE_OHM)

    def test_sheet_resistance_above_the_free_space_impedance_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.ohmic_reflection_loss_db(5.0e3)

    def test_full_coverage_costs_nothing(self):
        self.assertAlmostEqual(logic.coverage_loss_db(1.0), 0.0, places=12)

    def test_half_coverage_costs_three_decibels(self):
        self.assertAlmostEqual(logic.coverage_loss_db(0.5), 3.0103, places=4)

    def test_zero_coverage_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.coverage_loss_db(0.0)

    def test_coverage_above_unity_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.coverage_loss_db(1.2)

    def test_negative_coverage_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.coverage_loss_db(-0.5)


class CoatingAbsorption(unittest.TestCase):
    def test_a_face_with_no_coating_costs_nothing(self):
        self.assertAlmostEqual(
            logic.coating_absorption_loss_db(0.0, 3.0, 0.01, 0.015), 0.0, places=12
        )

    def test_a_known_coating_matches_the_two_way_absorption(self):
        loss = logic.coating_absorption_loss_db(
            1.5e-4, 3.0, 0.01, logic.wavelength_m(20.0e9)
        )
        self.assertAlmostEqual(loss, 0.00945922, places=8)

    def test_doubling_the_thickness_doubles_the_loss(self):
        thin = logic.coating_absorption_loss_db(1.0e-4, 3.0, 0.01, 0.015)
        thick = logic.coating_absorption_loss_db(2.0e-4, 3.0, 0.01, 0.015)
        self.assertAlmostEqual(thick / thin, 2.0, places=9)

    def test_a_lossless_coating_costs_nothing(self):
        self.assertAlmostEqual(
            logic.coating_absorption_loss_db(1.5e-4, 3.0, 0.0, 0.015), 0.0, places=12
        )

    def test_oblique_incidence_stretches_the_path(self):
        normal = logic.coating_absorption_loss_db(1.5e-4, 3.0, 0.01, 0.015, 0.0)
        oblique = logic.coating_absorption_loss_db(1.5e-4, 3.0, 0.01, 0.015, 60.0)
        self.assertGreater(oblique, normal)

    def test_permittivity_below_unity_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.coating_absorption_loss_db(1.5e-4, 0.5, 0.01, 0.015)

    def test_negative_loss_tangent_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.coating_absorption_loss_db(1.5e-4, 3.0, -0.01, 0.015)

    def test_loss_tangent_at_unity_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.coating_absorption_loss_db(1.5e-4, 3.0, 1.0, 0.015)

    def test_grazing_incidence_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.coating_absorption_loss_db(1.5e-4, 3.0, 0.01, 0.015, 90.0)

    def test_negative_incidence_angle_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.coating_absorption_loss_db(1.5e-4, 3.0, 0.01, 0.015, -10.0)

    def test_negative_thickness_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.coating_absorption_loss_db(-1.0e-4, 3.0, 0.01, 0.015)


class LossSummation(unittest.TestCase):
    def test_terms_add(self):
        total = logic.total_gain_degradation_db({"a": 0.1, "b": 0.2})
        self.assertAlmostEqual(total, 0.3, places=12)

    def test_absent_terms_are_skipped(self):
        total = logic.total_gain_degradation_db({"a": 0.1, "b": None})
        self.assertAlmostEqual(total, 0.1, places=12)

    def test_a_negative_term_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.total_gain_degradation_db({"a": 0.1, "b": -0.2})

    def test_an_empty_mapping_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.total_gain_degradation_db({})

    def test_a_mapping_of_only_absent_terms_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.total_gain_degradation_db({"a": None})

    def test_a_non_mapping_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.total_gain_degradation_db([0.1, 0.2])


class WholeAssessment(unittest.TestCase):
    def test_a_well_finished_metallized_face_is_compliant(self):
        result = logic.assess_composite_surface_finish(**_reflecting_case())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_the_total_is_the_sum_of_the_reported_terms(self):
        result = logic.assess_composite_surface_finish(**_coated_case())
        terms = [v for v in result["components_db"].values() if v is not None]
        self.assertAlmostEqual(result["total_degradation_db"], math.fsum(terms), places=12)

    def test_a_coated_face_costs_more_than_a_bare_metallized_one(self):
        plain = logic.assess_composite_surface_finish(**_reflecting_case())
        coated = logic.assess_composite_surface_finish(**_coated_case())
        self.assertGreater(
            coated["total_degradation_db"], plain["total_degradation_db"]
        )

    def test_a_bare_woven_face_owes_a_metallization_layer(self):
        result = logic.assess_composite_surface_finish(
            finish_type="bare-woven-carbon-face",
            frequency_hz=20.0e9,
            rms_surface_error_m=1.0e-4,
            allocated_degradation_db=0.20,
        )
        self.assertFalse(result["compliant"])
        self.assertTrue(any("metallization layer is owed" in f for f in result["findings"]))

    def test_a_bare_woven_face_also_raises_the_cross_polarisation_finding(self):
        result = logic.assess_composite_surface_finish(
            finish_type="bare-woven-carbon-face",
            frequency_hz=20.0e9,
            rms_surface_error_m=1.0e-4,
            allocated_degradation_db=0.20,
        )
        self.assertTrue(any("cross-polarisation" in f for f in result["findings"]))

    def test_incomplete_coverage_is_a_finding(self):
        result = logic.assess_composite_surface_finish(
            **_reflecting_case(metallization_coverage_fraction=0.95)
        )
        self.assertTrue(any("metallization covers" in f for f in result["findings"]))

    def test_a_coarse_face_trips_the_small_error_validity_limit(self):
        result = logic.assess_composite_surface_finish(
            **_reflecting_case(rms_surface_error_m=2.0e-3, allocated_degradation_db=100.0)
        )
        self.assertTrue(any("small-error validity" in f for f in result["findings"]))

    def test_an_exceeded_allocation_is_a_finding(self):
        result = logic.assess_composite_surface_finish(
            **_reflecting_case(allocated_degradation_db=0.001)
        )
        self.assertFalse(result["within_allocation"])
        self.assertTrue(any("against an allocation" in f for f in result["findings"]))

    def test_an_allocation_equal_to_the_computed_total_passes(self):
        baseline = logic.assess_composite_surface_finish(**_coated_case())
        total = baseline["total_degradation_db"]
        tight = logic.assess_composite_surface_finish(
            **_coated_case(allocated_degradation_db=total)
        )
        self.assertTrue(tight["within_allocation"])

    def test_an_allocation_a_hair_under_the_total_still_passes(self):
        baseline = logic.assess_composite_surface_finish(**_coated_case())
        total = baseline["total_degradation_db"]
        tight = logic.assess_composite_surface_finish(
            **_coated_case(allocated_degradation_db=total - 1e-12)
        )
        self.assertTrue(tight["within_allocation"])

    def test_an_allocation_five_thousandths_under_the_total_fails(self):
        baseline = logic.assess_composite_surface_finish(**_coated_case())
        total = baseline["total_degradation_db"]
        tight = logic.assess_composite_surface_finish(
            **_coated_case(allocated_degradation_db=total - 0.005)
        )
        self.assertFalse(tight["within_allocation"])

    def test_a_reflecting_face_without_a_sheet_resistance_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.assess_composite_surface_finish(
                **_reflecting_case(sheet_resistance_ohm_per_square=None)
            )

    def test_a_coated_face_without_a_thickness_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.assess_composite_surface_finish(**_coated_case(coating_thickness_m=0.0))

    def test_a_non_positive_allocation_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.assess_composite_surface_finish(**_reflecting_case(allocated_degradation_db=0.0))

    def test_an_uncategorized_finish_is_rejected_by_the_assessment(self):
        with self.assertRaises(ValueError):
            logic.assess_composite_surface_finish(**_reflecting_case(finish_type="anodised-face"))

    def test_the_wavelength_is_reported_back(self):
        result = logic.assess_composite_surface_finish(**_reflecting_case())
        self.assertAlmostEqual(result["wavelength_m"], 0.01498962, places=8)


if __name__ == "__main__":
    unittest.main()
