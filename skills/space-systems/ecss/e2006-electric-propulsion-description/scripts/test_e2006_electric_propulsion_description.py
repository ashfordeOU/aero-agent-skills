#!/usr/bin/env python3
"""Contract test for the ECSS-E-ST-20-06C clause 11.1.1 description leaf."""

import unittest

from e2006_electric_propulsion_description_logic import (
    ELEMENTARY_CHARGE_C,
    STANDARD_GRAVITY_M_S2,
    acceleration_mechanism,
    beam_current,
    charging_interactions,
    describe_thruster,
    emits_charged_beam,
    exhaust_velocity,
    mass_flow_rate,
    neutralizer_required,
    specific_charge,
    survey_propulsion_set,
    thruster_family,
    validate_power_split,
)


def ion_unit(**over):
    record = {
        "id": "EPT-A",
        "kind": "gridded-ion",
        "thrust_n": 0.090,
        "specific_impulse_s": 1600.0,
        "propellant": "xenon",
    }
    record.update(over)
    return record


class ThrusterFamilyTests(unittest.TestCase):
    def test_gridded_ion_is_electrostatic(self):
        self.assertEqual(thruster_family("gridded-ion"), "electrostatic")

    def test_hall_effect_is_electromagnetic(self):
        self.assertEqual(thruster_family("hall-effect"), "electromagnetic")

    def test_resistojet_is_electrothermal(self):
        self.assertEqual(thruster_family("resistojet"), "electrothermal")

    def test_designation_is_case_and_space_insensitive(self):
        self.assertEqual(thruster_family("  Gridded-Ion "), "electrostatic")

    def test_every_designation_has_a_mechanism_paraphrase(self):
        for kind in ("gridded-ion", "hall-effect", "colloid", "arcjet",
                     "pulsed-plasma", "magnetoplasmadynamic", "resistojet",
                     "field-emission-electric-propulsion"):
            self.assertTrue(acceleration_mechanism(kind))

    def test_uncategorized_designation_rejected(self):
        with self.assertRaises(ValueError):
            thruster_family("warp-coil")

    def test_empty_designation_rejected(self):
        with self.assertRaises(ValueError):
            thruster_family("   ")

    def test_non_string_designation_rejected(self):
        with self.assertRaises(ValueError):
            thruster_family(7)

    def test_mechanism_rejects_unknown_designation(self):
        with self.assertRaises(ValueError):
            acceleration_mechanism("solar-sail")


class ChargeEjectionTests(unittest.TestCase):
    def test_ion_thruster_ejects_net_charge(self):
        self.assertTrue(emits_charged_beam("gridded-ion"))

    def test_hall_effect_ejects_net_charge(self):
        self.assertTrue(emits_charged_beam("hall-effect"))

    def test_quasi_neutral_plasma_unit_ejects_no_net_charge(self):
        self.assertFalse(emits_charged_beam("pulsed-plasma"))
        self.assertFalse(emits_charged_beam("magnetoplasmadynamic"))

    def test_electrothermal_unit_ejects_no_net_charge(self):
        self.assertFalse(emits_charged_beam("arcjet"))

    def test_neutralizer_requirement_tracks_net_charge(self):
        self.assertTrue(neutralizer_required("colloid"))
        self.assertFalse(neutralizer_required("resistojet"))

    def test_charge_ejection_rejects_unknown_designation(self):
        with self.assertRaises(ValueError):
            emits_charged_beam("photon-drive")


class KinematicsTests(unittest.TestCase):
    def test_exhaust_velocity_uses_standard_gravity(self):
        self.assertAlmostEqual(exhaust_velocity(1600.0),
                               1600.0 * STANDARD_GRAVITY_M_S2, places=6)

    def test_mass_flow_from_thrust_and_impulse(self):
        expected = 0.090 / (1600.0 * STANDARD_GRAVITY_M_S2)
        self.assertAlmostEqual(mass_flow_rate(0.090, 1600.0), expected, places=12)

    def test_zero_impulse_rejected(self):
        with self.assertRaises(ValueError):
            exhaust_velocity(0.0)

    def test_negative_impulse_rejected(self):
        with self.assertRaises(ValueError):
            exhaust_velocity(-250.0)

    def test_zero_thrust_rejected(self):
        with self.assertRaises(ValueError):
            mass_flow_rate(0.0, 1600.0)

    def test_negative_thrust_rejected(self):
        with self.assertRaises(ValueError):
            mass_flow_rate(-0.01, 1600.0)


class SpecificChargeTests(unittest.TestCase):
    def test_singly_charged_xenon_ratio(self):
        value = specific_charge("xenon")
        self.assertAlmostEqual(value, 7.349e5, delta=1.0e3)

    def test_doubly_charged_ion_doubles_the_ratio(self):
        self.assertAlmostEqual(specific_charge("xenon", 2),
                               2.0 * specific_charge("xenon"), places=3)

    def test_lighter_propellant_gives_a_larger_ratio(self):
        self.assertGreater(specific_charge("argon"), specific_charge("xenon"))

    def test_elementary_charge_constant_is_codata(self):
        self.assertAlmostEqual(ELEMENTARY_CHARGE_C, 1.602176634e-19, places=28)

    def test_undeclared_propellant_rejected(self):
        with self.assertRaises(ValueError):
            specific_charge("helium")

    def test_empty_propellant_rejected(self):
        with self.assertRaises(ValueError):
            specific_charge("")

    def test_zero_charge_state_rejected(self):
        with self.assertRaises(ValueError):
            specific_charge("xenon", 0)

    def test_non_integer_charge_state_rejected(self):
        with self.assertRaises(ValueError):
            specific_charge("xenon", 1.5)


class BeamCurrentTests(unittest.TestCase):
    def test_beam_current_matches_flow_times_specific_charge(self):
        expected = mass_flow_rate(0.090, 1600.0) * specific_charge("xenon")
        self.assertAlmostEqual(beam_current(0.090, 1600.0, "xenon"),
                               expected, places=9)

    def test_partial_ionisation_scales_the_current(self):
        full = beam_current(0.090, 1600.0, "xenon")
        half = beam_current(0.090, 1600.0, "xenon", 1, 0.5)
        self.assertAlmostEqual(half, 0.5 * full, places=9)

    def test_unit_beam_fraction_is_accepted_at_the_boundary(self):
        self.assertAlmostEqual(beam_current(0.090, 1600.0, "xenon", 1, 1.0),
                               beam_current(0.090, 1600.0, "xenon"), places=12)

    def test_zero_beam_fraction_rejected(self):
        with self.assertRaises(ValueError):
            beam_current(0.090, 1600.0, "xenon", 1, 0.0)

    def test_beam_fraction_above_unity_rejected(self):
        with self.assertRaises(ValueError):
            beam_current(0.090, 1600.0, "xenon", 1, 1.2)


class PowerSplitTests(unittest.TestCase):
    def test_residual_is_the_unallocated_share(self):
        residual = validate_power_split({"beam": 0.60, "discharge": 0.25})
        self.assertAlmostEqual(residual, 0.15, places=9)

    def test_exact_unity_split_is_compliant(self):
        residual = validate_power_split({"beam": 0.7, "discharge": 0.1,
                                         "cathode": 0.1, "neutralizer": 0.1})
        self.assertAlmostEqual(residual, 0.0, places=9)

    def test_float_representation_overshoot_is_absorbed(self):
        # 0.1 + 0.1 + 0.1 + 0.7 evaluates a few ULPs above unity.
        residual = validate_power_split({"a": 0.1, "b": 0.1, "c": 0.1, "d": 0.7})
        self.assertAlmostEqual(residual, 0.0, places=9)

    def test_real_overshoot_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_power_split({"beam": 0.8, "discharge": 0.3})

    def test_empty_split_rejected(self):
        with self.assertRaises(ValueError):
            validate_power_split({})

    def test_non_positive_share_rejected(self):
        with self.assertRaises(ValueError):
            validate_power_split({"beam": 0.0})

    def test_blank_label_rejected(self):
        with self.assertRaises(ValueError):
            validate_power_split({"  ": 0.4})


class InteractionTests(unittest.TestCase):
    def test_ion_thruster_interactions(self):
        found = charging_interactions("gridded-ion", True)
        self.assertIn("beam-space-charge", found)
        self.assertIn("charge-exchange-plasma-backflow", found)
        self.assertIn("neutralizer-coupling-voltage", found)

    def test_missing_neutralizer_swaps_the_interaction(self):
        found = charging_interactions("gridded-ion", False)
        self.assertIn("unneutralized-beam-charging", found)
        self.assertNotIn("neutralizer-coupling-voltage", found)

    def test_electromagnetic_unit_adds_pulsed_emission(self):
        self.assertIn("pulsed-electromagnetic-emission",
                      charging_interactions("pulsed-plasma", False))

    def test_electrothermal_unit_drives_only_neutral_gas_rise(self):
        self.assertEqual(charging_interactions("resistojet", False),
                         ("neutral-gas-pressure-rise",))

    def test_interactions_are_sorted_and_unique(self):
        found = charging_interactions("hall-effect", True)
        self.assertEqual(list(found), sorted(set(found)))

    def test_non_boolean_neutralizer_flag_rejected(self):
        with self.assertRaises(ValueError):
            charging_interactions("gridded-ion", "yes")


class DescribeThrusterTests(unittest.TestCase):
    def test_description_record_fields(self):
        out = describe_thruster(ion_unit())
        self.assertEqual(out["family"], "electrostatic")
        self.assertTrue(out["neutralizer_required"])
        self.assertAlmostEqual(out["beam_current_a"],
                               beam_current(0.090, 1600.0, "xenon"), places=9)
        self.assertEqual(out["findings"], [])

    def test_missing_neutralizer_raises_a_finding(self):
        out = describe_thruster(ion_unit(neutralizer_present=False))
        self.assertEqual(len(out["findings"]), 1)
        self.assertIn("unneutralized-beam", out["findings"][0])

    def test_neutral_unit_carries_zero_beam_current(self):
        out = describe_thruster({"id": "RJ-1", "kind": "resistojet",
                                 "thrust_n": 0.3, "specific_impulse_s": 300.0})
        self.assertAlmostEqual(out["beam_current_a"], 0.0, places=12)
        self.assertFalse(out["neutralizer_required"])

    def test_neutralizer_declared_on_current_balanced_unit_is_a_finding(self):
        out = describe_thruster({"id": "PPT-1", "kind": "pulsed-plasma",
                                 "thrust_n": 0.0005, "specific_impulse_s": 1000.0,
                                 "neutralizer_present": True})
        self.assertEqual(len(out["findings"]), 1)
        self.assertIn("current-balanced", out["findings"][0])

    def test_power_split_is_carried_into_the_record(self):
        out = describe_thruster(ion_unit(power_split={"beam": 0.6,
                                                      "discharge": 0.25}))
        self.assertAlmostEqual(out["residual_thermal_fraction"], 0.15, places=9)

    def test_record_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            describe_thruster(["gridded-ion"])

    def test_missing_required_key_rejected(self):
        record = ion_unit()
        del record["thrust_n"]
        with self.assertRaises(ValueError):
            describe_thruster(record)

    def test_blank_unit_id_rejected(self):
        with self.assertRaises(ValueError):
            describe_thruster(ion_unit(id=" "))

    def test_charged_unit_without_propellant_rejected(self):
        record = ion_unit()
        del record["propellant"]
        with self.assertRaises(ValueError):
            describe_thruster(record)


class SurveyTests(unittest.TestCase):
    def test_survey_sums_beam_current_over_the_set(self):
        out = survey_propulsion_set([
            ion_unit(),
            ion_unit(id="EPT-B"),
        ])
        self.assertAlmostEqual(out["total_beam_current_a"],
                               2.0 * beam_current(0.090, 1600.0, "xenon"),
                               places=9)

    def test_survey_unions_interactions_across_families(self):
        out = survey_propulsion_set([
            ion_unit(),
            {"id": "RJ-1", "kind": "resistojet", "thrust_n": 0.3,
             "specific_impulse_s": 300.0},
        ])
        self.assertIn("neutral-gas-pressure-rise", out["interactions"])
        self.assertIn("beam-space-charge", out["interactions"])
        self.assertEqual(out["families"], ["electrostatic", "electrothermal"])

    def test_complete_survey_has_no_findings(self):
        out = survey_propulsion_set([ion_unit()])
        self.assertTrue(out["description_complete"])

    def test_survey_propagates_unit_findings(self):
        out = survey_propulsion_set([ion_unit(neutralizer_present=False)])
        self.assertFalse(out["description_complete"])
        self.assertEqual(len(out["findings"]), 1)

    def test_duplicate_unit_id_rejected(self):
        with self.assertRaises(ValueError):
            survey_propulsion_set([ion_unit(), ion_unit()])

    def test_empty_set_rejected(self):
        with self.assertRaises(ValueError):
            survey_propulsion_set([])

    def test_non_list_set_rejected(self):
        with self.assertRaises(ValueError):
            survey_propulsion_set(ion_unit())


if __name__ == "__main__":
    unittest.main()
