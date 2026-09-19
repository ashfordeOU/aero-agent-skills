"""Contract tests for the ECSS-Q-ST-70-09C applicability and properties logic."""

import unittest

from q7009_applicability_and_properties_logic import (
    BALANCE_TOLERANCE,
    INFRARED_EMITTANCE,
    MIN_PATTERN_PERIODS,
    PORT_OVERFILL_MARGIN,
    SOLAR_ABSORPTANCE,
    SURFACE_CATEGORIES,
    TRANSMITTANCE_FLOOR,
    absorptance_from_reflectance_transmittance,
    assess_campaign,
    assess_specimen,
    measurable_properties,
    opacity_state,
    overfills_port,
    pattern_periods_across_port,
    port_overfill_ratio,
    validate_surface_category,
)


def white_paint(**overrides):
    """Return a nominal opaque diffuse coating specimen record."""
    specimen = {
        "id": "SP-01",
        "category": "diffuse-opaque-coating",
        "transmittance": 0.0,
        "specimen_size_mm": 50.0,
        "port_size_mm": 25.0,
    }
    specimen.update(overrides)
    return specimen


class SurfaceCategoryTests(unittest.TestCase):
    def test_every_covered_family_is_accepted(self):
        for category in SURFACE_CATEGORIES:
            self.assertEqual(validate_surface_category(category), category)

    def test_unknown_family_rejected(self):
        with self.assertRaises(ValueError):
            validate_surface_category("solar-cell-cover-glass-stack")

    def test_empty_family_rejected(self):
        with self.assertRaises(ValueError):
            validate_surface_category("")

    def test_non_string_family_rejected(self):
        with self.assertRaises(ValueError):
            validate_surface_category(3)


class OpacityTests(unittest.TestCase):
    def test_zero_transmittance_is_opaque(self):
        self.assertEqual(opacity_state(0.0), "opaque")

    def test_value_on_the_floor_is_opaque(self):
        self.assertEqual(opacity_state(TRANSMITTANCE_FLOOR), "opaque")

    def test_value_above_the_floor_transmits(self):
        self.assertEqual(opacity_state(0.05), "transmitting")

    def test_transmittance_above_unity_rejected(self):
        with self.assertRaises(ValueError):
            opacity_state(1.4)

    def test_negative_transmittance_rejected(self):
        with self.assertRaises(ValueError):
            opacity_state(-0.01)

    def test_boolean_transmittance_rejected(self):
        with self.assertRaises(ValueError):
            opacity_state(True)

    def test_floor_above_unity_rejected(self):
        with self.assertRaises(ValueError):
            opacity_state(0.0, floor=1.5)


class PortGeometryTests(unittest.TestCase):
    def test_overfill_ratio_is_the_size_ratio(self):
        self.assertAlmostEqual(port_overfill_ratio(50.0, 25.0), 2.0)

    def test_generous_overfill_passes(self):
        self.assertTrue(overfills_port(50.0, 25.0))

    def test_exact_margin_ratio_passes(self):
        port = 25.0
        specimen = port * (1.0 + PORT_OVERFILL_MARGIN)
        self.assertAlmostEqual(port_overfill_ratio(specimen, port),
                               1.0 + PORT_OVERFILL_MARGIN, places=9)
        self.assertTrue(overfills_port(specimen, port))

    def test_specimen_smaller_than_the_port_fails(self):
        self.assertFalse(overfills_port(20.0, 25.0))

    def test_zero_port_rejected(self):
        with self.assertRaises(ValueError):
            port_overfill_ratio(50.0, 0.0)

    def test_negative_specimen_rejected(self):
        with self.assertRaises(ValueError):
            port_overfill_ratio(-50.0, 25.0)

    def test_pattern_periods_across_port(self):
        self.assertAlmostEqual(pattern_periods_across_port(2.0, 25.0), 12.5)

    def test_zero_pitch_rejected(self):
        with self.assertRaises(ValueError):
            pattern_periods_across_port(0.0, 25.0)


class EnergyBalanceTests(unittest.TestCase):
    def test_opaque_absorptance_is_one_minus_reflectance(self):
        self.assertAlmostEqual(absorptance_from_reflectance_transmittance(0.18), 0.82)

    def test_transmitting_absorptance_subtracts_both_terms(self):
        value = absorptance_from_reflectance_transmittance(0.30, 0.20)
        self.assertAlmostEqual(value, 0.50)

    def test_balance_exactly_closed_gives_zero_absorptance(self):
        value = absorptance_from_reflectance_transmittance(0.60, 0.40)
        self.assertAlmostEqual(value, 0.0, places=9)

    def test_over_unity_balance_refused(self):
        with self.assertRaises(ValueError):
            absorptance_from_reflectance_transmittance(0.70, 0.40)

    def test_reflectance_outside_unit_interval_refused(self):
        with self.assertRaises(ValueError):
            absorptance_from_reflectance_transmittance(1.2)


class MeasurablePropertyTests(unittest.TestCase):
    def test_opaque_coating_yields_both_properties(self):
        properties = measurable_properties("diffuse-opaque-coating", 0.0)
        self.assertIn(SOLAR_ABSORPTANCE, properties)
        self.assertIn(INFRARED_EMITTANCE, properties)

    def test_free_transmitting_film_yields_nothing(self):
        self.assertEqual(measurable_properties("semi-transparent-film", 0.4), ())

    def test_backed_transmitting_film_yields_both(self):
        properties = measurable_properties("semi-transparent-film", 0.4, True)
        self.assertEqual(len(properties), 2)

    def test_non_boolean_backing_rejected(self):
        with self.assertRaises(ValueError):
            measurable_properties("semi-transparent-film", 0.4, "yes")


class SpecimenAssessmentTests(unittest.TestCase):
    def test_nominal_coating_is_in_scope(self):
        record = assess_specimen(white_paint())
        self.assertTrue(record["in_scope"])
        self.assertEqual(record["findings"], [])

    def test_undersized_specimen_is_a_finding(self):
        record = assess_specimen(white_paint(specimen_size_mm=20.0))
        self.assertFalse(record["in_scope"])
        self.assertIn("port surround", record["findings"][0])

    def test_reflectance_only_on_a_transmitting_film_is_a_finding(self):
        record = assess_specimen(white_paint(
            category="semi-transparent-film",
            transmittance=0.35,
            substrate_backed=True,
            reflectance_only=True,
        ))
        self.assertFalse(record["in_scope"])
        self.assertTrue(any("transmitted term" in f for f in record["findings"]))

    def test_backed_film_without_reflectance_only_is_a_constraint_not_a_finding(self):
        record = assess_specimen(white_paint(
            category="semi-transparent-film",
            transmittance=0.35,
            substrate_backed=True,
        ))
        self.assertTrue(record["in_scope"])
        self.assertTrue(any("close the" in c for c in record["constraints"]))

    def test_declared_film_that_measures_opaque_is_a_finding(self):
        record = assess_specimen(white_paint(
            category="semi-transparent-film", transmittance=0.0))
        self.assertFalse(record["in_scope"])
        self.assertTrue(any("disagree" in f for f in record["findings"]))

    def test_coarse_pattern_across_the_port_is_a_finding(self):
        record = assess_specimen(white_paint(
            category="patterned-or-textured",
            pattern_pitch_mm=20.0,
        ))
        self.assertFalse(record["in_scope"])
        self.assertAlmostEqual(record["pattern_periods"], 1.25)

    def test_pattern_exactly_on_the_period_threshold_passes(self):
        pitch = 25.0 / MIN_PATTERN_PERIODS
        record = assess_specimen(white_paint(
            category="patterned-or-textured", pattern_pitch_mm=pitch))
        self.assertAlmostEqual(record["pattern_periods"], MIN_PATTERN_PERIODS, places=9)
        self.assertTrue(record["in_scope"])

    def test_patterned_surface_without_pitch_rejected(self):
        with self.assertRaises(ValueError):
            assess_specimen(white_paint(category="patterned-or-textured"))

    def test_specular_surface_carries_the_trap_constraint(self):
        record = assess_specimen(white_paint(category="specular-metallized"))
        self.assertTrue(any("specular component" in c for c in record["constraints"]))

    def test_contaminated_surface_is_reported_as_received(self):
        record = assess_specimen(white_paint(category="in-service-contaminated"))
        self.assertTrue(any("as-received" in c for c in record["constraints"]))

    def test_missing_key_rejected(self):
        specimen = white_paint()
        del specimen["port_size_mm"]
        with self.assertRaises(ValueError):
            assess_specimen(specimen)

    def test_blank_identifier_rejected(self):
        with self.assertRaises(ValueError):
            assess_specimen(white_paint(id="   "))

    def test_non_mapping_specimen_rejected(self):
        with self.assertRaises(ValueError):
            assess_specimen(["SP-01"])


class CampaignTests(unittest.TestCase):
    def test_campaign_counts_both_properties(self):
        result = assess_campaign([white_paint(), white_paint(id="SP-02")])
        self.assertEqual(result["specimen_count"], 2)
        self.assertEqual(result["solar_absorptance_count"], 2)
        self.assertEqual(result["infrared_emittance_count"], 2)
        self.assertTrue(result["campaign_in_scope"])

    def test_duplicate_identifier_is_a_campaign_finding(self):
        result = assess_campaign([white_paint(), white_paint()])
        self.assertFalse(result["campaign_in_scope"])
        self.assertTrue(any("more than once" in f for f in result["findings"]))

    def test_one_out_of_scope_specimen_sinks_the_campaign(self):
        result = assess_campaign([
            white_paint(),
            white_paint(id="SP-02", specimen_size_mm=10.0),
        ])
        self.assertEqual(result["in_scope_count"], 1)
        self.assertFalse(result["campaign_in_scope"])

    def test_empty_campaign_rejected(self):
        with self.assertRaises(ValueError):
            assess_campaign([])

    def test_balance_tolerance_is_small(self):
        self.assertAlmostEqual(BALANCE_TOLERANCE, 1.0e-9, places=12)


if __name__ == "__main__":
    unittest.main()
