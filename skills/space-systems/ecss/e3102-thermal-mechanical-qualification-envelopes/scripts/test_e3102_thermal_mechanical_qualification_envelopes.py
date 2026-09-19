#!/usr/bin/env python3
"""Contract test for the two-phase qualification envelopes (offline)."""

import copy
import unittest

from e3102_thermal_mechanical_qualification_envelopes_logic import (
    ENVELOPE_ADMITTED,
    ENVELOPE_REJECTED,
    acceptance_temperature_envelope,
    assess_fluid_against_envelope,
    audit_survival_envelope,
    define_qualification_envelopes,
    merit_number,
    qualification_temperature_envelope,
    qualification_vibration_duration,
    qualification_vibration_level,
    select_working_fluid,
    validate_fluid,
    worst_end_merit,
)

AMMONIA = {
    "name": "ammonia",
    "surface_tension_n_per_m": 0.0214,
    "liquid_density_kg_per_m3": 600.0,
    "latent_heat_j_per_kg": 1.16e6,
    "liquid_viscosity_pa_s": 1.3e-4,
    "freezing_point_k": 195.0,
    "critical_point_k": 405.0,
    "cold_scaling": 1.0,
    "hot_scaling": 0.8,
}

PROPYLENE = {
    "name": "propylene",
    "surface_tension_n_per_m": 0.0075,
    "liquid_density_kg_per_m3": 520.0,
    "latent_heat_j_per_kg": 3.7e5,
    "liquid_viscosity_pa_s": 1.0e-4,
    "freezing_point_k": 88.0,
    "critical_point_k": 364.0,
    "cold_scaling": 1.0,
    "hot_scaling": 0.9,
}

WATER = {
    "name": "water",
    "surface_tension_n_per_m": 0.0589,
    "liquid_density_kg_per_m3": 958.0,
    "latent_heat_j_per_kg": 2.26e6,
    "liquid_viscosity_pa_s": 2.8e-4,
    "freezing_point_k": 273.15,
    "critical_point_k": 647.0,
    "cold_scaling": 1.0,
    "hot_scaling": 1.0,
}

BASE_CASE = {
    "predicted_min_k": 263.0,
    "predicted_max_k": 323.0,
    "acceptance_margin_k": 5.0,
    "qualification_margin_k": 10.0,
    "survival_min_k": 240.0,
    "survival_max_k": 350.0,
    "acceptance_asd_g2_per_hz": 0.04,
    "vibration_uplift_db": 3.0,
    "acceptance_duration_s": 60.0,
    "duration_factor": 2.0,
    "candidate_fluids": (AMMONIA, PROPYLENE, WATER),
}


def _case(base, **overrides):
    case = copy.deepcopy(base)
    case.update(overrides)
    return case


def _fluid(base, **overrides):
    fluid = copy.deepcopy(base)
    fluid.update(overrides)
    return fluid


class TemperatureEnvelopeTests(unittest.TestCase):
    def test_acceptance_envelope_widens_both_ends(self):
        envelope = acceptance_temperature_envelope(263.0, 323.0, 5.0)
        self.assertAlmostEqual(envelope["min_k"], 258.0, places=9)
        self.assertAlmostEqual(envelope["max_k"], 328.0, places=9)

    def test_qualification_envelope_widens_the_acceptance_one(self):
        envelope = qualification_temperature_envelope(263.0, 323.0, 5.0, 10.0)
        self.assertAlmostEqual(envelope["acceptance_min_k"], 258.0, places=9)
        self.assertAlmostEqual(envelope["min_k"], 248.0, places=9)
        self.assertAlmostEqual(envelope["max_k"], 338.0, places=9)

    def test_a_zero_qualification_margin_leaves_the_acceptance_envelope(self):
        envelope = qualification_temperature_envelope(263.0, 323.0, 5.0, 0.0)
        self.assertAlmostEqual(envelope["min_k"], envelope["acceptance_min_k"], places=9)
        self.assertAlmostEqual(envelope["max_k"], envelope["acceptance_max_k"], places=9)

    def test_an_inverted_prediction_rejected(self):
        with self.assertRaises(ValueError):
            acceptance_temperature_envelope(323.0, 263.0, 5.0)

    def test_a_margin_below_absolute_zero_rejected(self):
        with self.assertRaises(ValueError):
            acceptance_temperature_envelope(263.0, 323.0, 300.0)

    def test_a_negative_acceptance_margin_rejected(self):
        with self.assertRaises(ValueError):
            acceptance_temperature_envelope(263.0, 323.0, -5.0)

    def test_a_non_numeric_prediction_rejected(self):
        with self.assertRaises(ValueError):
            acceptance_temperature_envelope("263 K", 323.0, 5.0)


class SurvivalEnvelopeTests(unittest.TestCase):
    def test_a_containing_survival_range_passes(self):
        envelope = qualification_temperature_envelope(263.0, 323.0, 5.0, 10.0)
        audit = audit_survival_envelope(envelope, 240.0, 350.0)
        self.assertTrue(audit["contains_envelope"])
        self.assertEqual(audit["findings"], [])

    def test_a_survival_range_exactly_on_the_envelope_passes(self):
        envelope = qualification_temperature_envelope(263.0, 323.0, 5.0, 10.0)
        audit = audit_survival_envelope(
            envelope, envelope["min_k"], envelope["max_k"]
        )
        self.assertTrue(audit["contains_envelope"])

    def test_a_warm_survival_cold_limit_is_a_finding(self):
        envelope = qualification_temperature_envelope(263.0, 323.0, 5.0, 10.0)
        audit = audit_survival_envelope(envelope, 255.0, 350.0)
        self.assertFalse(audit["contains_envelope"])
        self.assertTrue(any("cold limit" in f for f in audit["findings"]))

    def test_a_low_survival_hot_limit_is_a_finding(self):
        envelope = qualification_temperature_envelope(263.0, 323.0, 5.0, 10.0)
        audit = audit_survival_envelope(envelope, 240.0, 330.0)
        self.assertTrue(any("hot limit" in f for f in audit["findings"]))

    def test_an_inverted_survival_range_rejected(self):
        envelope = qualification_temperature_envelope(263.0, 323.0, 5.0, 10.0)
        with self.assertRaises(ValueError):
            audit_survival_envelope(envelope, 350.0, 240.0)

    def test_a_non_mapping_envelope_rejected(self):
        with self.assertRaises(ValueError):
            audit_survival_envelope("248 to 338", 240.0, 350.0)


class MechanicalEnvelopeTests(unittest.TestCase):
    def test_a_three_decibel_uplift_roughly_doubles_the_density(self):
        self.assertAlmostEqual(
            qualification_vibration_level(0.04, 3.0), 0.04 * (10.0 ** 0.3), places=12
        )

    def test_a_zero_uplift_leaves_the_acceptance_level(self):
        self.assertAlmostEqual(qualification_vibration_level(0.04, 0.0), 0.04, places=12)

    def test_six_decibel_is_the_square_of_three_decibel_in_ratio(self):
        three = qualification_vibration_level(0.04, 3.0) / 0.04
        six = qualification_vibration_level(0.04, 6.0) / 0.04
        self.assertAlmostEqual(six, three * three, places=9)

    def test_the_duration_factor_multiplies_the_acceptance_duration(self):
        self.assertAlmostEqual(qualification_vibration_duration(60.0, 2.0), 120.0, places=9)

    def test_a_unit_duration_factor_is_allowed(self):
        self.assertAlmostEqual(qualification_vibration_duration(60.0, 1.0), 60.0, places=9)

    def test_a_shortening_duration_factor_rejected(self):
        with self.assertRaises(ValueError):
            qualification_vibration_duration(60.0, 0.5)

    def test_a_negative_uplift_rejected(self):
        with self.assertRaises(ValueError):
            qualification_vibration_level(0.04, -3.0)

    def test_a_zero_acceptance_density_rejected(self):
        with self.assertRaises(ValueError):
            qualification_vibration_level(0.0, 3.0)


class FluidPropertyTests(unittest.TestCase):
    def test_a_complete_fluid_validates(self):
        self.assertIs(validate_fluid(AMMONIA), AMMONIA)

    def test_a_fluid_missing_a_property_rejected(self):
        broken = _fluid(AMMONIA)
        del broken["latent_heat_j_per_kg"]
        with self.assertRaises(ValueError):
            validate_fluid(broken)

    def test_a_fluid_with_zero_viscosity_rejected(self):
        with self.assertRaises(ValueError):
            validate_fluid(_fluid(AMMONIA, liquid_viscosity_pa_s=0.0))

    def test_a_critical_point_below_the_freezing_point_rejected(self):
        with self.assertRaises(ValueError):
            validate_fluid(_fluid(AMMONIA, critical_point_k=100.0))

    def test_the_merit_number_follows_the_grouped_properties(self):
        expected = (
            AMMONIA["surface_tension_n_per_m"]
            * AMMONIA["liquid_density_kg_per_m3"]
            * AMMONIA["latent_heat_j_per_kg"]
            / AMMONIA["liquid_viscosity_pa_s"]
        )
        self.assertAlmostEqual(merit_number(AMMONIA), expected, places=3)

    def test_a_higher_viscosity_lowers_the_merit_number(self):
        thick = _fluid(AMMONIA, name="thick", liquid_viscosity_pa_s=2.6e-4)
        self.assertLess(merit_number(thick), merit_number(AMMONIA))

    def test_the_scaling_factor_scales_the_merit_number(self):
        self.assertAlmostEqual(
            merit_number(AMMONIA, 0.5), merit_number(AMMONIA) * 0.5, places=3
        )

    def test_a_zero_scaling_factor_rejected(self):
        with self.assertRaises(ValueError):
            merit_number(AMMONIA, 0.0)

    def test_the_worst_end_is_the_weaker_of_the_two_ends(self):
        worst = worst_end_merit(AMMONIA, 1.0, 0.8)
        self.assertAlmostEqual(worst, merit_number(AMMONIA, 0.8), places=3)


class FluidAdmissionTests(unittest.TestCase):
    def test_a_fluid_liquid_across_the_envelope_is_admitted(self):
        verdict = assess_fluid_against_envelope(
            AMMONIA, {"min_k": 248.0, "max_k": 338.0}
        )
        self.assertEqual(verdict["status"], ENVELOPE_ADMITTED)
        self.assertEqual(verdict["reasons"], [])

    def test_a_fluid_that_freezes_inside_the_envelope_is_rejected(self):
        verdict = assess_fluid_against_envelope(
            WATER, {"min_k": 248.0, "max_k": 338.0}
        )
        self.assertEqual(verdict["status"], ENVELOPE_REJECTED)
        self.assertTrue(any("freezes" in r for r in verdict["reasons"]))

    def test_a_fluid_past_its_critical_point_is_rejected(self):
        verdict = assess_fluid_against_envelope(
            PROPYLENE, {"min_k": 248.0, "max_k": 380.0}
        )
        self.assertTrue(any("critical point" in r for r in verdict["reasons"]))

    def test_a_freezing_point_exactly_on_the_cold_end_is_admitted(self):
        verdict = assess_fluid_against_envelope(
            AMMONIA, {"min_k": AMMONIA["freezing_point_k"], "max_k": 338.0}
        )
        self.assertEqual(verdict["status"], ENVELOPE_ADMITTED)

    def test_a_clearance_can_reject_a_fluid_that_just_fits(self):
        verdict = assess_fluid_against_envelope(
            AMMONIA,
            {"min_k": AMMONIA["freezing_point_k"], "max_k": 338.0},
            clearance_k=5.0,
        )
        self.assertEqual(verdict["status"], ENVELOPE_REJECTED)

    def test_a_negative_clearance_rejected(self):
        with self.assertRaises(ValueError):
            assess_fluid_against_envelope(
                AMMONIA, {"min_k": 248.0, "max_k": 338.0}, clearance_k=-1.0
            )


class FluidSelectionTests(unittest.TestCase):
    def test_the_strongest_admitted_worst_end_is_selected(self):
        result = select_working_fluid(
            (AMMONIA, PROPYLENE), {"min_k": 248.0, "max_k": 338.0}
        )
        self.assertEqual(result["selected"]["name"], "ammonia")

    def test_a_fluid_rejected_on_the_envelope_cannot_be_selected(self):
        result = select_working_fluid(
            (WATER, PROPYLENE), {"min_k": 248.0, "max_k": 338.0}
        )
        self.assertEqual(result["selected"]["name"], "propylene")
        self.assertEqual(len(result["rejected"]), 1)

    def test_a_headline_merit_does_not_beat_a_stronger_worst_end(self):
        peaky = _fluid(AMMONIA, name="peaky", hot_scaling=0.05)
        result = select_working_fluid(
            (peaky, PROPYLENE), {"min_k": 248.0, "max_k": 338.0}
        )
        self.assertEqual(result["selected"]["name"], "propylene")

    def test_no_admitted_fluid_gives_a_finding_and_no_choice(self):
        result = select_working_fluid((WATER,), {"min_k": 248.0, "max_k": 338.0})
        self.assertIsNone(result["selected"])
        self.assertTrue(result["findings"])

    def test_an_empty_candidate_set_rejected(self):
        with self.assertRaises(ValueError):
            select_working_fluid((), {"min_k": 248.0, "max_k": 338.0})

    def test_a_duplicate_candidate_rejected(self):
        with self.assertRaises(ValueError):
            select_working_fluid(
                (AMMONIA, _fluid(AMMONIA)), {"min_k": 248.0, "max_k": 338.0}
            )

    def test_a_non_sequence_candidate_set_rejected(self):
        with self.assertRaises(ValueError):
            select_working_fluid("ammonia", {"min_k": 248.0, "max_k": 338.0})


class DefineEnvelopesTests(unittest.TestCase):
    def test_a_sound_case_defines_every_envelope(self):
        result = define_qualification_envelopes(BASE_CASE)
        self.assertEqual(result["verdict"], "envelopes-defined")
        self.assertAlmostEqual(result["temperature"]["min_k"], 248.0, places=9)
        self.assertAlmostEqual(result["temperature"]["max_k"], 338.0, places=9)
        self.assertEqual(result["fluid"]["name"], "ammonia")

    def test_the_mechanical_levels_carry_the_uplift_and_the_factor(self):
        result = define_qualification_envelopes(BASE_CASE)
        self.assertAlmostEqual(
            result["mechanical"]["qualification_asd_g2_per_hz"],
            0.04 * (10.0 ** 0.3),
            places=12,
        )
        self.assertAlmostEqual(
            result["mechanical"]["qualification_duration_s"], 120.0, places=9
        )

    def test_water_is_reported_as_rejected_on_this_envelope(self):
        result = define_qualification_envelopes(BASE_CASE)
        self.assertIn("water", [item["name"] for item in result["fluids_rejected"]])

    def test_a_short_survival_range_opens_the_envelope(self):
        result = define_qualification_envelopes(_case(BASE_CASE, survival_max_k=330.0))
        self.assertEqual(result["verdict"], "envelopes-open")
        self.assertTrue(result["findings"])

    def test_a_wider_qualification_margin_widens_the_envelope(self):
        narrow = define_qualification_envelopes(BASE_CASE)["temperature"]
        wide = define_qualification_envelopes(
            _case(BASE_CASE, qualification_margin_k=20.0, survival_min_k=230.0,
                  survival_max_k=360.0)
        )["temperature"]
        self.assertLess(wide["min_k"], narrow["min_k"])
        self.assertGreater(wide["max_k"], narrow["max_k"])

    def test_a_case_with_no_candidate_fluid_rejected(self):
        case = _case(BASE_CASE)
        case["candidate_fluids"] = ()
        with self.assertRaises(ValueError):
            define_qualification_envelopes(case)

    def test_a_missing_acceptance_density_rejected(self):
        case = _case(BASE_CASE)
        del case["acceptance_asd_g2_per_hz"]
        with self.assertRaises(ValueError):
            define_qualification_envelopes(case)

    def test_a_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            define_qualification_envelopes("263 to 323 K")


if __name__ == "__main__":
    unittest.main()
