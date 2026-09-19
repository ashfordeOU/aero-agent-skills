"""Contract tests for the life-cycle contamination threat identification."""

import unittest

from q7001_contamination_threat_identification_logic import (
    DOMINANCE_FRACTION,
    LIFE_CYCLE_PHASES,
    SPECIES,
    dominant_source,
    identify_threats,
    phase_coverage,
    rank_sources,
    source_arrival,
    totals_by_phase,
    totals_by_species,
    validate_fraction,
    validate_non_negative,
    validate_phase,
    validate_source,
    validate_species,
)

SOURCES = [
    {
        "name": "machining-swarf",
        "phase": "manufacture",
        "species": "particulate",
        "release_rate": 2.0,
        "exposure_duration": 1.0,
        "transport_fraction": 0.5,
        "barrier": "bagged-enclosure",
    },
    {
        "name": "operator-shedding",
        "phase": "assembly",
        "species": "particulate",
        "release_rate": 2.0,
        "exposure_duration": 1.0,
        "transport_fraction": 0.5,
        "barrier": "garment-and-flow",
    },
    {
        "name": "adhesive-outgassing",
        "phase": "integration",
        "species": "molecular",
        "release_rate": 1.0,
        "exposure_duration": 2.0,
        "transport_fraction": 0.5,
        "barrier": "purge-and-cover",
    },
    {
        "name": "thruster-plume-backflow",
        "phase": "in-orbit",
        "species": "molecular",
        "release_rate": 0.5,
        "exposure_duration": 4.0,
        "transport_fraction": 0.5,
        "barrier": "canted-nozzle",
    },
]

DECLARED = ["manufacture", "assembly", "integration", "in-orbit"]


def nominal_spec(**overrides):
    spec = {
        "sources": [dict(source) for source in SOURCES],
        "declared_phases": list(DECLARED),
    }
    spec.update(overrides)
    return spec


class ValidationTests(unittest.TestCase):
    def test_non_negative_accepts_zero(self):
        self.assertEqual(validate_non_negative(0, "rate"), 0.0)

    def test_non_negative_rejects_a_negative_rate(self):
        with self.assertRaises(ValueError):
            validate_non_negative(-1.0, "release_rate")

    def test_fraction_accepts_the_closed_unit_interval(self):
        self.assertAlmostEqual(validate_fraction(1.0, "transport_fraction"), 1.0)
        self.assertAlmostEqual(validate_fraction(0.0, "transport_fraction"), 0.0)

    def test_fraction_above_unity_rejected(self):
        with self.assertRaises(ValueError):
            validate_fraction(1.2, "transport_fraction")

    def test_known_phase_is_normalised(self):
        self.assertEqual(validate_phase("  In-Orbit "), "in-orbit")

    def test_unknown_phase_rejected(self):
        with self.assertRaises(ValueError):
            validate_phase("on-the-pad")

    def test_known_species_is_normalised(self):
        self.assertEqual(validate_species("Molecular"), "molecular")

    def test_unknown_species_rejected(self):
        with self.assertRaises(ValueError):
            validate_species("biological")

    def test_missing_source_key_rejected(self):
        with self.assertRaises(ValueError):
            validate_source({"name": "x", "phase": "test", "species": "particulate"})

    def test_unnamed_source_rejected(self):
        source = dict(SOURCES[0], name="  ")
        with self.assertRaises(ValueError):
            validate_source(source)

    def test_release_with_zero_duration_rejected(self):
        source = dict(SOURCES[0], exposure_duration=0.0)
        with self.assertRaises(ValueError):
            validate_source(source)

    def test_transport_fraction_defaults_to_unity(self):
        source = dict(SOURCES[0])
        del source["transport_fraction"]
        self.assertAlmostEqual(validate_source(source)["transport_fraction"], 1.0)


class ArrivalTests(unittest.TestCase):
    def test_arrival_is_rate_times_duration_times_transport(self):
        self.assertAlmostEqual(source_arrival(SOURCES[0]), 1.0, places=12)

    def test_a_blocked_path_delivers_nothing(self):
        blocked = dict(SOURCES[0], transport_fraction=0.0)
        self.assertAlmostEqual(source_arrival(blocked), 0.0, places=12)

    def test_species_totals_split_the_register(self):
        totals = totals_by_species(SOURCES)
        self.assertAlmostEqual(totals["particulate"], 2.0, places=12)
        self.assertAlmostEqual(totals["molecular"], 2.0, places=12)

    def test_phase_totals_are_keyed_by_phase(self):
        totals = totals_by_phase(SOURCES)
        self.assertAlmostEqual(totals["manufacture"], 1.0, places=12)
        self.assertEqual(len(totals), 4)

    def test_ranking_puts_the_largest_arrival_first(self):
        heavy = dict(SOURCES[0], name="grit-blast-residue", release_rate=20.0)
        ranked = rank_sources([heavy] + SOURCES[1:])
        self.assertEqual(ranked[0]["name"], "grit-blast-residue")

    def test_ranking_can_be_filtered_by_species(self):
        ranked = rank_sources(SOURCES, "molecular")
        self.assertEqual(len(ranked), 2)
        for record in ranked:
            self.assertEqual(record["species"], "molecular")

    def test_duplicate_source_name_rejected(self):
        with self.assertRaises(ValueError):
            rank_sources(SOURCES + [dict(SOURCES[0])])

    def test_empty_register_rejected(self):
        with self.assertRaises(ValueError):
            totals_by_species([])


class DominanceTests(unittest.TestCase):
    def test_even_split_is_not_dominance(self):
        driver = dominant_source(SOURCES, "particulate")
        self.assertAlmostEqual(driver["fraction"], 0.5, places=12)
        self.assertFalse(driver["dominant"])

    def test_one_large_source_is_dominance(self):
        heavy = dict(SOURCES[0], name="grit-blast-residue", release_rate=20.0)
        driver = dominant_source([heavy] + SOURCES[1:], "particulate")
        self.assertEqual(driver["name"], "grit-blast-residue")
        self.assertGreater(driver["fraction"], DOMINANCE_FRACTION)
        self.assertTrue(driver["dominant"])

    def test_species_with_no_source_returns_nothing(self):
        molecular_only = [s for s in SOURCES if s["species"] == "molecular"]
        self.assertIsNone(dominant_source(molecular_only, "particulate"))


class CoverageTests(unittest.TestCase):
    def test_declared_phases_are_all_covered(self):
        coverage = phase_coverage(SOURCES, DECLARED)
        self.assertEqual(coverage["uncovered"], [])

    def test_full_life_cycle_shows_the_gaps(self):
        coverage = phase_coverage(SOURCES)
        self.assertIn("storage", coverage["uncovered"])
        self.assertEqual(len(coverage["declared"]), len(LIFE_CYCLE_PHASES))

    def test_an_explicit_nil_statement_closes_a_phase(self):
        coverage = phase_coverage(
            SOURCES, DECLARED + ["storage"], phases_without_sources=["storage"]
        )
        self.assertEqual(coverage["uncovered"], [])
        self.assertEqual(coverage["stated_without_sources"], ["storage"])

    def test_nil_statement_contradicted_by_a_source_rejected(self):
        with self.assertRaises(ValueError):
            phase_coverage(SOURCES, DECLARED, phases_without_sources=["assembly"])

    def test_empty_declared_phase_list_rejected(self):
        with self.assertRaises(ValueError):
            phase_coverage(SOURCES, [])


class IdentificationTests(unittest.TestCase):
    def test_nominal_register_is_complete(self):
        result = identify_threats(nominal_spec())
        self.assertTrue(result["complete"])
        self.assertEqual(result["findings"], [])

    def test_both_species_are_reported(self):
        result = identify_threats(nominal_spec())
        self.assertEqual(sorted(result["species_totals"]), sorted(SPECIES))

    def test_driving_phase_is_the_largest_arrival_phase(self):
        spec = nominal_spec()
        spec["sources"][0]["release_rate"] = 20.0
        result = identify_threats(spec)
        self.assertEqual(result["driving_phase"], "manufacture")

    def test_uncovered_phase_is_a_finding(self):
        spec = nominal_spec()
        del spec["declared_phases"]
        result = identify_threats(spec)
        self.assertFalse(result["complete"])
        self.assertTrue(any("neither an identified source" in f for f in result["findings"]))

    def test_missing_species_is_a_finding(self):
        spec = nominal_spec(
            sources=[dict(s) for s in SOURCES if s["species"] == "molecular"],
            declared_phases=["integration", "in-orbit"],
        )
        result = identify_threats(spec)
        self.assertTrue(any("no particulate source" in f for f in result["findings"]))

    def test_uncredited_transport_barrier_is_a_finding(self):
        spec = nominal_spec()
        spec["sources"][0]["transport_fraction"] = 1.0
        spec["sources"][0]["barrier"] = None
        result = identify_threats(spec)
        self.assertTrue(any("no transport barrier" in f for f in result["findings"]))

    def test_dominant_source_is_a_finding(self):
        spec = nominal_spec()
        spec["sources"][0]["release_rate"] = 20.0
        result = identify_threats(spec)
        self.assertTrue(any("dominated by" in f for f in result["findings"]))

    def test_ranked_output_is_ordered_by_arrival(self):
        spec = nominal_spec()
        spec["sources"][0]["release_rate"] = 20.0
        result = identify_threats(spec)
        arrivals = [record["arrival"] for record in result["ranked"]]
        self.assertEqual(arrivals, sorted(arrivals, reverse=True))

    def test_missing_sources_key_rejected(self):
        with self.assertRaises(ValueError):
            identify_threats({"declared_phases": DECLARED})

    def test_non_mapping_specification_rejected(self):
        with self.assertRaises(ValueError):
            identify_threats(["sources"])


if __name__ == "__main__":
    unittest.main()
