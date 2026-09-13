"""Contract tests for the clause 5.5.1.4.3 humidity-test sample logic."""

import unittest

from e2008_humidity_test_sample_logic import (
    DEFAULT_THICKNESS_TOLERANCE_REL,
    assess_test_sample,
    compare_stackups,
    normalize_equivalents,
    process_findings,
    representativeness_fraction,
    thickness_within_band,
    validate_iso_date,
    validate_layer,
    validate_stackup,
)

# Representative rigid-panel photovoltaic assembly stack-up, coverglass down to
# the substrate bond line.
FLIGHT = [
    {"layer": "coverglass", "material_spec": "CMG-100",
     "thickness_mm": 0.100, "process": "coverglass-bonding"},
    {"layer": "coverglass-adhesive", "material_spec": "ADH-93500",
     "thickness_mm": 0.050, "process": "adhesive-dispense"},
    {"layer": "solar-cell", "material_spec": "GAAS-3J-80",
     "thickness_mm": 0.080, "process": "cell-singulation"},
    {"layer": "interconnect", "material_spec": "AG-MESH-25",
     "thickness_mm": 0.025, "process": "parallel-gap-welding"},
    {"layer": "substrate-adhesive", "material_spec": "ADH-2568",
     "thickness_mm": 0.150, "process": "adhesive-dispense"},
]

QUALIFIED = {
    "coverglass-bonding": {"valid_from": "2025-01-01", "valid_to": "2027-12-31"},
    "adhesive-dispense": {"valid_from": "2025-01-01", "valid_to": "2027-12-31"},
    "cell-singulation": {"valid_from": "2025-01-01", "valid_to": "2027-12-31"},
    "parallel-gap-welding": {"valid_from": "2025-01-01", "valid_to": "2027-12-31"},
}

BUILD_DATE = "2026-02-10"


def _specimen(**layer_overrides):
    """Copy the flight stack-up, applying per-layer overrides."""
    layers = []
    for layer in FLIGHT:
        copy = dict(layer)
        copy.update(layer_overrides.get(layer["layer"], {}))
        layers.append(copy)
    return layers


def _spec(**overrides):
    spec = {
        "flight_stackup": FLIGHT,
        "specimen_stackup": _specimen(),
        "qualified_processes": QUALIFIED,
        "build_date": BUILD_DATE,
        "specimen_count": 4,
    }
    spec.update(overrides)
    return spec


class LayerValidationTests(unittest.TestCase):
    def test_identifiers_are_trimmed(self):
        layer = validate_layer(dict(FLIGHT[0], layer="  coverglass  "), 0, "flight")
        self.assertEqual(layer["layer"], "coverglass")

    def test_missing_key_rejected(self):
        broken = dict(FLIGHT[0])
        del broken["process"]
        with self.assertRaises(ValueError):
            validate_layer(broken, 0, "flight")

    def test_blank_material_spec_rejected(self):
        with self.assertRaises(ValueError):
            validate_layer(dict(FLIGHT[0], material_spec="   "), 0, "flight")

    def test_zero_thickness_rejected(self):
        with self.assertRaises(ValueError):
            validate_layer(dict(FLIGHT[0], thickness_mm=0.0), 0, "flight")

    def test_non_numeric_thickness_rejected(self):
        with self.assertRaises(ValueError):
            validate_layer(dict(FLIGHT[0], thickness_mm="0.1"), 0, "flight")

    def test_non_mapping_layer_rejected(self):
        with self.assertRaises(ValueError):
            validate_layer(["coverglass"], 0, "flight")

    def test_iso_build_date_parsed(self):
        self.assertEqual(validate_iso_date(BUILD_DATE, "build_date").year, 2026)

    def test_malformed_build_date_rejected(self):
        with self.assertRaises(ValueError):
            validate_iso_date("2026-02-32", "build_date")


class StackupValidationTests(unittest.TestCase):
    def test_layers_keep_their_build_order(self):
        stack = validate_stackup(FLIGHT, "flight")
        self.assertEqual([item["index"] for item in stack], [0, 1, 2, 3, 4])

    def test_empty_stackup_rejected(self):
        with self.assertRaises(ValueError):
            validate_stackup([], "flight")

    def test_duplicate_layer_names_rejected(self):
        with self.assertRaises(ValueError):
            validate_stackup([FLIGHT[0], dict(FLIGHT[1], layer="coverglass")], "flight")


class EquivalentsTests(unittest.TestCase):
    def test_absent_table_is_empty(self):
        self.assertEqual(normalize_equivalents(None), {})

    def test_single_string_alternative_is_wrapped(self):
        table = normalize_equivalents({"ADH-93500": "ADH-93500-LOTB"})
        self.assertEqual(table["ADH-93500"], set(["ADH-93500-LOTB"]))

    def test_non_mapping_table_rejected(self):
        with self.assertRaises(ValueError):
            normalize_equivalents(["ADH-93500"])

    def test_empty_alternative_list_rejected(self):
        with self.assertRaises(ValueError):
            normalize_equivalents({"ADH-93500": []})

    def test_non_string_alternative_rejected(self):
        with self.assertRaises(ValueError):
            normalize_equivalents({"ADH-93500": [93500]})


class ThicknessBandTests(unittest.TestCase):
    def test_identical_thickness_is_inside_the_band(self):
        self.assertTrue(thickness_within_band(0.150, 0.150))

    def test_thickness_exactly_on_the_band_edge_is_accepted(self):
        limit = 0.150 * DEFAULT_THICKNESS_TOLERANCE_REL
        self.assertAlmostEqual(abs((0.150 + limit) - 0.150), limit, places=9)
        self.assertTrue(thickness_within_band(0.150 + limit, 0.150))

    def test_thickness_beyond_the_band_is_refused(self):
        self.assertFalse(thickness_within_band(0.200, 0.150))

    def test_zero_tolerance_admits_only_an_identical_thickness(self):
        self.assertTrue(thickness_within_band(0.150, 0.150, 0.0))
        self.assertFalse(thickness_within_band(0.151, 0.150, 0.0))

    def test_negative_tolerance_rejected(self):
        with self.assertRaises(ValueError):
            thickness_within_band(0.150, 0.150, -0.05)

    def test_zero_flight_thickness_rejected(self):
        with self.assertRaises(ValueError):
            thickness_within_band(0.150, 0.0)


class StackupComparisonTests(unittest.TestCase):
    def test_identical_builds_have_no_deviations(self):
        walk = compare_stackups(FLIGHT, _specimen())
        self.assertEqual(walk["deviations"], [])
        self.assertEqual(walk["representative_layer_count"], 5)

    def test_omitted_layer_is_recorded(self):
        specimen = [layer for layer in _specimen() if layer["layer"] != "interconnect"]
        walk = compare_stackups(FLIGHT, specimen)
        kinds = [d["kind"] for d in walk["deviations"]]
        self.assertIn("missing-layer", kinds)

    def test_added_layer_is_recorded(self):
        specimen = _specimen() + [
            {"layer": "witness-tab", "material_spec": "AL-6061",
             "thickness_mm": 0.500, "process": "adhesive-dispense"}
        ]
        walk = compare_stackups(FLIGHT, specimen)
        kinds = [d["kind"] for d in walk["deviations"]]
        self.assertIn("extra-layer", kinds)

    def test_unapproved_material_swap_is_a_deviation(self):
        specimen = _specimen(**{"coverglass-adhesive": {"material_spec": "ADH-OTHER"}})
        walk = compare_stackups(FLIGHT, specimen)
        self.assertEqual(walk["deviations"][0]["kind"], "material-substitution")
        self.assertEqual(walk["representative_layer_count"], 4)

    def test_approved_equivalent_stays_representative(self):
        specimen = _specimen(**{"coverglass-adhesive": {"material_spec": "ADH-93500-LOTB"}})
        walk = compare_stackups(
            FLIGHT, specimen, {"ADH-93500": ["ADH-93500-LOTB"]}
        )
        self.assertEqual(walk["deviations"], [])
        self.assertEqual(len(walk["substitutions"]), 1)
        self.assertEqual(walk["representative_layer_count"], 5)

    def test_thickness_deviation_is_recorded(self):
        specimen = _specimen(**{"substrate-adhesive": {"thickness_mm": 0.250}})
        walk = compare_stackups(FLIGHT, specimen)
        self.assertEqual(walk["deviations"][0]["kind"], "thickness-deviation")

    def test_out_of_sequence_layer_is_recorded(self):
        specimen = _specimen()
        specimen[1], specimen[2] = specimen[2], specimen[1]
        walk = compare_stackups(FLIGHT, specimen)
        kinds = [d["kind"] for d in walk["deviations"]]
        self.assertEqual(kinds.count("sequence-deviation"), 2)


class RepresentativenessTests(unittest.TestCase):
    def test_full_reproduction_is_unity(self):
        self.assertAlmostEqual(representativeness_fraction(5, 5), 1.0, places=9)

    def test_partial_reproduction(self):
        self.assertAlmostEqual(representativeness_fraction(3, 5), 0.6, places=9)

    def test_zero_flight_layers_rejected(self):
        with self.assertRaises(ValueError):
            representativeness_fraction(0, 0)

    def test_more_representative_than_flight_layers_rejected(self):
        with self.assertRaises(ValueError):
            representativeness_fraction(6, 5)

    def test_non_integer_count_rejected(self):
        with self.assertRaises(ValueError):
            representativeness_fraction(3.0, 5)

    def test_negative_count_rejected(self):
        with self.assertRaises(ValueError):
            representativeness_fraction(-1, 5)


class ProcessQualificationTests(unittest.TestCase):
    def test_qualified_build_has_no_process_findings(self):
        self.assertEqual(process_findings(_specimen(), QUALIFIED, BUILD_DATE), [])

    def test_unknown_process_is_flagged(self):
        specimen = _specimen(**{"interconnect": {"process": "hand-soldering"}})
        findings = process_findings(specimen, QUALIFIED, BUILD_DATE)
        self.assertEqual(findings[0]["kind"], "unqualified-process")

    def test_lapsed_qualification_is_flagged(self):
        lapsed = dict(QUALIFIED)
        lapsed["cell-singulation"] = {"valid_from": "2024-01-01", "valid_to": "2025-06-30"}
        findings = process_findings(_specimen(), lapsed, BUILD_DATE)
        self.assertEqual(findings[0]["kind"], "lapsed-qualification")

    def test_build_before_the_qualification_opens_is_flagged(self):
        early = dict(QUALIFIED)
        early["cell-singulation"] = {"valid_from": "2026-09-01", "valid_to": "2028-01-01"}
        findings = process_findings(_specimen(), early, BUILD_DATE)
        self.assertEqual(findings[0]["kind"], "premature-qualification")

    def test_each_process_is_reported_once(self):
        broken = dict(QUALIFIED)
        del broken["adhesive-dispense"]
        findings = process_findings(_specimen(), broken, BUILD_DATE)
        self.assertEqual(len(findings), 1)

    def test_inverted_qualification_window_rejected(self):
        inverted = dict(QUALIFIED)
        inverted["adhesive-dispense"] = {"valid_from": "2027-01-01", "valid_to": "2025-01-01"}
        with self.assertRaises(ValueError):
            process_findings(_specimen(), inverted, BUILD_DATE)

    def test_malformed_qualification_record_rejected(self):
        malformed = dict(QUALIFIED)
        malformed["adhesive-dispense"] = {"valid_from": "2025-01-01"}
        with self.assertRaises(ValueError):
            process_findings(_specimen(), malformed, BUILD_DATE)

    def test_empty_qualification_list_rejected(self):
        with self.assertRaises(ValueError):
            process_findings(_specimen(), {}, BUILD_DATE)


class AssessmentTests(unittest.TestCase):
    def test_flight_equivalent_specimen_passes(self):
        result = assess_test_sample(_spec())
        self.assertTrue(result["flight_representative"])
        self.assertEqual(result["findings"], [])

    def test_representativeness_is_reported(self):
        result = assess_test_sample(_spec())
        self.assertAlmostEqual(result["representativeness"], 1.0, places=9)

    def test_material_deviation_becomes_a_finding(self):
        specimen = _specimen(**{"solar-cell": {"material_spec": "SI-BSF-200"}})
        result = assess_test_sample(_spec(specimen_stackup=specimen))
        self.assertFalse(result["flight_representative"])
        self.assertIn("material-substitution", result["findings"][0])

    def test_threshold_exactly_met_adds_no_fraction_finding(self):
        specimen = _specimen(**{"substrate-adhesive": {"thickness_mm": 0.250}})
        result = assess_test_sample(
            _spec(specimen_stackup=specimen, required_representativeness=0.8)
        )
        self.assertAlmostEqual(result["representativeness"], 0.8, places=9)
        self.assertEqual(
            [f for f in result["findings"] if "against a required" in f], []
        )

    def test_threshold_missed_adds_a_fraction_finding(self):
        specimen = _specimen(
            **{"substrate-adhesive": {"thickness_mm": 0.250},
               "coverglass": {"thickness_mm": 0.200}}
        )
        result = assess_test_sample(
            _spec(specimen_stackup=specimen, required_representativeness=0.8)
        )
        self.assertAlmostEqual(result["representativeness"], 0.6, places=9)
        self.assertEqual(
            len([f for f in result["findings"] if "against a required" in f]), 1
        )

    def test_short_specimen_population_is_flagged(self):
        result = assess_test_sample(_spec(specimen_count=1))
        self.assertFalse(result["flight_representative"])
        self.assertIn("below the agreed minimum", result["findings"][-1])

    def test_lowered_minimum_accepts_a_small_population(self):
        result = assess_test_sample(_spec(specimen_count=1, minimum_specimens=1))
        self.assertTrue(result["flight_representative"])

    def test_threshold_outside_the_unit_interval_rejected(self):
        with self.assertRaises(ValueError):
            assess_test_sample(_spec(required_representativeness=1.4))

    def test_non_integer_specimen_count_rejected(self):
        with self.assertRaises(ValueError):
            assess_test_sample(_spec(specimen_count=4.0))

    def test_zero_specimen_count_rejected(self):
        with self.assertRaises(ValueError):
            assess_test_sample(_spec(specimen_count=0))

    def test_non_positive_minimum_rejected(self):
        with self.assertRaises(ValueError):
            assess_test_sample(_spec(minimum_specimens=0))

    def test_missing_spec_key_rejected(self):
        spec = _spec()
        del spec["build_date"]
        with self.assertRaises(ValueError):
            assess_test_sample(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_test_sample(["flight_stackup"])

    def test_approved_substitution_is_reported_but_not_a_finding(self):
        specimen = _specimen(**{"coverglass-adhesive": {"material_spec": "ADH-93500-LOTB"}})
        result = assess_test_sample(
            _spec(specimen_stackup=specimen,
                  approved_equivalents={"ADH-93500": ["ADH-93500-LOTB"]})
        )
        self.assertTrue(result["flight_representative"])
        self.assertEqual(len(result["substitutions"]), 1)


if __name__ == "__main__":
    unittest.main()
