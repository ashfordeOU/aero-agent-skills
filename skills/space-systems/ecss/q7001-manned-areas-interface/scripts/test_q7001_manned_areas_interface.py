"""Contract tests for the crewed-area molecular and particulate interface."""

import unittest

from q7001_manned_areas_interface_logic import (
    DEFAULT_ALLOWABLE_TOTAL_INDEX,
    INDEX_TOLERANCE,
    assess_crewed_area_interface,
    driving_species,
    hazard_index,
    particulate_margin_mg_m3,
    species_rate_mg_per_day,
    steady_state_concentration_mg_m3,
    total_hazard_index,
    validate_compartment,
    validate_species,
)


def compartment(**overrides):
    base = {
        "volume_m3": 100.0,
        "scrubbing_flow_m3_per_day": 200.0,
        "removal_efficiency": 0.9,
        "allowable_total_index": 0.5,
        "particulate_mg_m3": 0.05,
        "particulate_limit_mg_m3": 0.2,
    }
    base.update(overrides)
    return base


SPECIES = [
    {
        "name": "aliphatic-hydrocarbon-blend",
        "rate_mg_per_day": 9.0,
        "max_allowable_concentration_mg_m3": 5.0,
    },
    {
        "name": "aldehyde-fraction",
        "rate_mg_per_day": 18.0,
        "max_allowable_concentration_mg_m3": 1.0,
    },
    {
        "name": "siloxane-fraction",
        "rate_mg_per_day": 36.0,
        "max_allowable_concentration_mg_m3": 2.0,
    },
]


def spec(**overrides):
    base = {"compartment": compartment(), "species": [dict(s) for s in SPECIES]}
    base.update(overrides)
    return base


class SpeciesRateTests(unittest.TestCase):
    def test_measured_rate_is_returned(self):
        self.assertAlmostEqual(
            species_rate_mg_per_day({"rate_mg_per_day": 9.0}), 9.0
        )

    def test_specific_rate_scales_with_installed_mass(self):
        value = species_rate_mg_per_day(
            {"specific_rate_mg_per_kg_day": 1.5, "installed_mass_kg": 4.0}
        )
        self.assertAlmostEqual(value, 6.0, places=12)

    def test_declaring_both_routes_is_refused(self):
        with self.assertRaises(ValueError):
            species_rate_mg_per_day(
                {
                    "rate_mg_per_day": 9.0,
                    "specific_rate_mg_per_kg_day": 1.5,
                    "installed_mass_kg": 4.0,
                }
            )

    def test_specific_rate_without_mass_is_refused(self):
        with self.assertRaises(ValueError):
            species_rate_mg_per_day({"specific_rate_mg_per_kg_day": 1.5})

    def test_no_rate_information_is_refused(self):
        with self.assertRaises(ValueError):
            species_rate_mg_per_day({"name": "unknown"})

    def test_negative_rate_rejected(self):
        with self.assertRaises(ValueError):
            species_rate_mg_per_day({"rate_mg_per_day": -1.0})

    def test_zero_installed_mass_rejected(self):
        with self.assertRaises(ValueError):
            species_rate_mg_per_day(
                {"specific_rate_mg_per_kg_day": 1.5, "installed_mass_kg": 0.0}
            )

    def test_non_mapping_species_rejected(self):
        with self.assertRaises(ValueError):
            species_rate_mg_per_day(["rate_mg_per_day"])


class ValidationTests(unittest.TestCase):
    def test_species_record_is_normalised(self):
        record = validate_species(dict(SPECIES[0]))
        self.assertEqual(record["name"], "aliphatic-hydrocarbon-blend")
        self.assertAlmostEqual(record["rate_mg_per_day"], 9.0)

    def test_species_without_a_limit_rejected(self):
        with self.assertRaises(ValueError):
            validate_species({"name": "x", "rate_mg_per_day": 1.0})

    def test_blank_species_name_rejected(self):
        bad = dict(SPECIES[0])
        bad["name"] = "  "
        with self.assertRaises(ValueError):
            validate_species(bad)

    def test_zero_allowable_concentration_rejected(self):
        bad = dict(SPECIES[0])
        bad["max_allowable_concentration_mg_m3"] = 0.0
        with self.assertRaises(ValueError):
            validate_species(bad)

    def test_compartment_defaults_are_applied(self):
        record = validate_compartment(
            {"volume_m3": 100.0, "scrubbing_flow_m3_per_day": 200.0}
        )
        self.assertAlmostEqual(record["removal_efficiency"], 1.0)
        self.assertAlmostEqual(
            record["allowable_total_index"], DEFAULT_ALLOWABLE_TOTAL_INDEX
        )

    def test_compartment_missing_key_rejected(self):
        with self.assertRaises(ValueError):
            validate_compartment({"volume_m3": 100.0})

    def test_zero_removal_efficiency_rejected(self):
        with self.assertRaises(ValueError):
            validate_compartment(compartment(removal_efficiency=0.0))

    def test_efficiency_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_compartment(compartment(removal_efficiency=1.5))

    def test_implausible_scrubbing_flow_rejected(self):
        with self.assertRaises(ValueError):
            validate_compartment(
                compartment(volume_m3=10.0, scrubbing_flow_m3_per_day=1.0e7)
            )

    def test_non_mapping_compartment_rejected(self):
        with self.assertRaises(ValueError):
            validate_compartment(["volume_m3"])


class ConcentrationTests(unittest.TestCase):
    def test_steady_state_is_rate_over_effective_flow(self):
        self.assertAlmostEqual(
            steady_state_concentration_mg_m3(9.0, 200.0, 0.9), 0.05, places=12
        )

    def test_a_better_scrubber_lowers_the_concentration(self):
        poor = steady_state_concentration_mg_m3(9.0, 200.0, 0.5)
        good = steady_state_concentration_mg_m3(9.0, 200.0, 1.0)
        self.assertGreater(poor, good)

    def test_more_flow_lowers_the_concentration(self):
        low = steady_state_concentration_mg_m3(9.0, 100.0, 0.9)
        high = steady_state_concentration_mg_m3(9.0, 400.0, 0.9)
        self.assertGreater(low, high)

    def test_no_offgassing_is_no_concentration(self):
        self.assertAlmostEqual(steady_state_concentration_mg_m3(0.0, 200.0, 0.9), 0.0)

    def test_zero_removal_efficiency_refused(self):
        with self.assertRaises(ValueError):
            steady_state_concentration_mg_m3(9.0, 200.0, 0.0)

    def test_zero_flow_refused(self):
        with self.assertRaises(ValueError):
            steady_state_concentration_mg_m3(9.0, 0.0, 0.9)


class IndexTests(unittest.TestCase):
    def test_index_is_the_quotient(self):
        self.assertAlmostEqual(hazard_index(0.1, 1.0), 0.1, places=12)

    def test_index_at_the_limit_is_unity(self):
        self.assertAlmostEqual(hazard_index(2.0, 2.0), 1.0)

    def test_zero_limit_rejected(self):
        with self.assertRaises(ValueError):
            hazard_index(0.1, 0.0)

    def test_total_is_the_sum(self):
        self.assertAlmostEqual(total_hazard_index([0.01, 0.1, 0.1]), 0.21, places=12)

    def test_empty_total_rejected(self):
        with self.assertRaises(ValueError):
            total_hazard_index([])

    def test_negative_index_rejected(self):
        with self.assertRaises(ValueError):
            total_hazard_index([0.1, -0.1])

    def test_driving_species_is_the_largest(self):
        records = [
            {"name": "a", "hazard_index": 0.01},
            {"name": "b", "hazard_index": 0.3},
            {"name": "c", "hazard_index": 0.1},
        ]
        self.assertEqual(driving_species(records)["name"], "b")

    def test_driving_species_rejects_a_malformed_record(self):
        with self.assertRaises(ValueError):
            driving_species([{"name": "a"}])

    def test_driving_species_rejects_an_empty_set(self):
        with self.assertRaises(ValueError):
            driving_species([])

    def test_particulate_margin_is_the_headroom(self):
        self.assertAlmostEqual(particulate_margin_mg_m3(0.05, 0.2), 0.15, places=12)

    def test_particulate_over_limit_is_negative(self):
        self.assertLess(particulate_margin_mg_m3(0.3, 0.2), 0.0)

    def test_zero_particulate_limit_rejected(self):
        with self.assertRaises(ValueError):
            particulate_margin_mg_m3(0.05, 0.0)


class AssessmentTests(unittest.TestCase):
    def test_baseline_is_compliant(self):
        result = assess_crewed_area_interface(spec())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_total_index_is_the_sum_of_shares(self):
        result = assess_crewed_area_interface(spec())
        self.assertAlmostEqual(result["total_hazard_index"], 0.21, places=12)

    def test_driving_species_is_named(self):
        result = assess_crewed_area_interface(spec())
        self.assertIn(
            result["driving_species"], ("aldehyde-fraction", "siloxane-fraction")
        )

    def test_total_over_the_allowable_is_flagged(self):
        result = assess_crewed_area_interface(
            spec(compartment=compartment(allowable_total_index=0.1))
        )
        self.assertFalse(result["compliant"])
        self.assertTrue(any("total hazard index" in f for f in result["findings"]))

    def test_exact_total_boundary_is_accepted(self):
        probe = assess_crewed_area_interface(spec())
        limit = probe["total_hazard_index"]
        result = assess_crewed_area_interface(
            spec(compartment=compartment(allowable_total_index=limit))
        )
        self.assertAlmostEqual(result["total_hazard_index"], limit, places=12)
        self.assertLessEqual(
            abs(result["total_hazard_index"] - limit), INDEX_TOLERANCE
        )
        self.assertTrue(result["compliant"])

    def test_a_single_species_over_its_own_limit_is_named(self):
        loaded = [dict(s) for s in SPECIES]
        loaded[1]["rate_mg_per_day"] = 900.0
        result = assess_crewed_area_interface(spec(species=loaded))
        self.assertIn("aldehyde-fraction", result["species_over_own_limit"])
        self.assertFalse(result["compliant"])

    def test_a_weaker_scrubber_raises_every_index(self):
        good = assess_crewed_area_interface(spec())
        poor = assess_crewed_area_interface(
            spec(compartment=compartment(removal_efficiency=0.3))
        )
        self.assertGreater(
            poor["total_hazard_index"], good["total_hazard_index"]
        )

    def test_particulate_over_limit_is_flagged(self):
        result = assess_crewed_area_interface(
            spec(compartment=compartment(particulate_mg_m3=0.4))
        )
        self.assertFalse(result["compliant"])
        self.assertTrue(any("particulate" in f for f in result["findings"]))

    def test_particulate_headroom_is_reported(self):
        result = assess_crewed_area_interface(spec())
        self.assertAlmostEqual(
            result["particulate_headroom_mg_m3"], 0.15, places=12
        )

    def test_mass_driven_species_are_accepted(self):
        by_mass = [
            {
                "name": "adhesive-volatiles",
                "specific_rate_mg_per_kg_day": 0.5,
                "installed_mass_kg": 18.0,
                "max_allowable_concentration_mg_m3": 1.0,
            }
        ]
        result = assess_crewed_area_interface(spec(species=by_mass))
        self.assertAlmostEqual(result["species"][0]["rate_mg_per_day"], 9.0, places=12)

    def test_duplicate_species_names_rejected(self):
        doubled = [dict(SPECIES[0]), dict(SPECIES[0])]
        with self.assertRaises(ValueError):
            assess_crewed_area_interface(spec(species=doubled))

    def test_empty_species_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_crewed_area_interface(spec(species=[]))

    def test_missing_spec_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_crewed_area_interface({"compartment": compartment()})

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_crewed_area_interface(["compartment"])


if __name__ == "__main__":
    unittest.main()
