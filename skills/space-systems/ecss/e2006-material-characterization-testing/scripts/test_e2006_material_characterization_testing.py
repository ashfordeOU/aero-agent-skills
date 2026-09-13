#!/usr/bin/env python3
"""Gate 3 contract test for e2006-material-characterization-testing."""

import unittest

from e2006_material_characterization_testing_logic import (
    CAMPAIGN_LEVELS,
    PARAMETER_INSTRUMENTATION,
    assess_characterization_programme,
    configuration_findings,
    envelope_findings,
    envelope_margins,
    evaluate_material_waiver,
    normalize_campaign,
    normalize_environment,
    normalize_material,
    normalize_parameter,
    parameter_coverage,
)


def flight_env(**over):
    env = {
        "electron-energy-kev": 20.0,
        "particle-flux-a-per-m2": 1.0e-6,
        "exposure-duration-h": 100.0,
        "applied-bias-v": 500.0,
        "temperature-min-c": -40.0,
        "temperature-max-c": 60.0,
    }
    env.update(over)
    return env


def campaign_env(**over):
    env = {
        "electron-energy-kev": 25.0,
        "particle-flux-a-per-m2": 2.0e-6,
        "exposure-duration-h": 150.0,
        "applied-bias-v": 600.0,
        "temperature-min-c": -55.0,
        "temperature-max-c": 80.0,
    }
    env.update(over)
    return env


def campaign(**over):
    rec = {
        "id": "AQ-01",
        "level": "qualification",
        "environment": campaign_env(),
        "instrumentation": [
            "through-thickness-current-monitor",
            "surface-current-monitor",
            "electron-beam-current-monitor",
        ],
    }
    rec.update(over)
    return rec


def material(**over):
    rec = {
        "id": "kapton-outer",
        "parameters": ["bulk-resistivity", "surface-resistivity"],
        "thickness-mm": 0.125,
        "assembly-thickness-mm": 0.125,
        "thickness-tolerance-frac": 0.05,
        "surface-treatment": "ITO-coated",
        "assembly-surface-treatment": "ito-coated",
        "flight-environment": flight_env(),
        "exposed-outside-assembly": False,
    }
    rec.update(over)
    return rec


class TestParameterNormalization(unittest.TestCase):
    def test_canonical_token_passes_through(self):
        self.assertEqual(normalize_parameter("bulk-resistivity"), "bulk-resistivity")

    def test_token_is_case_and_separator_insensitive(self):
        self.assertEqual(normalize_parameter("Secondary_Electron Yield"), "secondary-electron-yield")

    def test_every_catalogued_parameter_has_a_channel(self):
        for key, channel in PARAMETER_INSTRUMENTATION.items():
            self.assertEqual(normalize_parameter(key), key)
            self.assertTrue(channel)

    def test_unknown_parameter_raises(self):
        with self.assertRaises(ValueError):
            normalize_parameter("thermal-emittance")

    def test_empty_parameter_raises(self):
        with self.assertRaises(ValueError):
            normalize_parameter("   ")


class TestEnvironmentNormalization(unittest.TestCase):
    def test_valid_environment_returns_floats(self):
        env = normalize_environment(flight_env(), "flight")
        self.assertAlmostEqual(env["electron-energy-kev"], 20.0)
        self.assertAlmostEqual(env["temperature-max-c"], 60.0)

    def test_missing_axis_raises(self):
        env = flight_env()
        del env["applied-bias-v"]
        with self.assertRaises(ValueError):
            normalize_environment(env, "flight")

    def test_missing_temperature_axis_raises(self):
        env = flight_env()
        del env["temperature-min-c"]
        with self.assertRaises(ValueError):
            normalize_environment(env, "flight")

    def test_negative_magnitude_raises(self):
        with self.assertRaises(ValueError):
            normalize_environment(flight_env(**{"exposure-duration-h": -1.0}), "flight")

    def test_inverted_temperature_band_raises(self):
        with self.assertRaises(ValueError):
            normalize_environment(
                flight_env(**{"temperature-min-c": 80.0, "temperature-max-c": -10.0}), "flight"
            )

    def test_non_numeric_axis_raises(self):
        with self.assertRaises(ValueError):
            normalize_environment(flight_env(**{"applied-bias-v": "500"}), "flight")

    def test_non_mapping_environment_raises(self):
        with self.assertRaises(ValueError):
            normalize_environment(["electron-energy-kev"], "flight")


class TestCampaignNormalization(unittest.TestCase):
    def test_qualification_campaign_is_waiver_capable(self):
        camp = normalize_campaign(campaign())
        self.assertTrue(camp["waiver-capable-level"])
        self.assertIn("surface-current-monitor", camp["instrumentation"])

    def test_development_campaign_is_not_waiver_capable(self):
        camp = normalize_campaign(campaign(level="development"))
        self.assertFalse(camp["waiver-capable-level"])

    def test_level_table_covers_protoflight_and_acceptance(self):
        self.assertTrue(CAMPAIGN_LEVELS["protoflight"])
        self.assertFalse(CAMPAIGN_LEVELS["acceptance"])

    def test_unknown_level_raises(self):
        with self.assertRaises(ValueError):
            normalize_campaign(campaign(level="flight-spare"))

    def test_empty_instrumentation_raises(self):
        with self.assertRaises(ValueError):
            normalize_campaign(campaign(instrumentation=[]))

    def test_blank_channel_raises(self):
        with self.assertRaises(ValueError):
            normalize_campaign(campaign(instrumentation=["  "]))

    def test_missing_id_raises(self):
        rec = campaign()
        del rec["id"]
        with self.assertRaises(ValueError):
            normalize_campaign(rec)


class TestMaterialNormalization(unittest.TestCase):
    def test_parameters_are_deduplicated_and_sorted(self):
        mat = normalize_material(
            material(parameters=["surface-resistivity", "bulk-resistivity", "bulk_resistivity"])
        )
        self.assertEqual(mat["parameters"], ["bulk-resistivity", "surface-resistivity"])

    def test_surface_treatment_is_case_folded(self):
        mat = normalize_material(material())
        self.assertEqual(mat["surface-treatment"], mat["assembly-surface-treatment"])

    def test_empty_parameter_list_raises(self):
        with self.assertRaises(ValueError):
            normalize_material(material(parameters=[]))

    def test_zero_thickness_raises(self):
        with self.assertRaises(ValueError):
            normalize_material(material(**{"thickness-mm": 0.0}))

    def test_tolerance_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            normalize_material(material(**{"thickness-tolerance-frac": 1.0}))

    def test_non_boolean_exposure_flag_raises(self):
        with self.assertRaises(ValueError):
            normalize_material(material(**{"exposed-outside-assembly": "yes"}))

    def test_blank_surface_treatment_raises(self):
        with self.assertRaises(ValueError):
            normalize_material(material(**{"surface-treatment": ""}))


class TestConfigurationFindings(unittest.TestCase):
    def test_identical_configuration_has_no_findings(self):
        self.assertEqual(configuration_findings(normalize_material(material())), [])

    def test_thickness_at_exact_tolerance_is_compliant(self):
        mat = normalize_material(
            material(**{"thickness-mm": 0.1, "assembly-thickness-mm": 0.105,
                        "thickness-tolerance-frac": 0.05})
        )
        self.assertEqual(configuration_findings(mat), [])

    def test_thickness_beyond_tolerance_is_flagged(self):
        mat = normalize_material(
            material(**{"thickness-mm": 0.1, "assembly-thickness-mm": 0.2})
        )
        self.assertEqual(len(configuration_findings(mat)), 1)

    def test_surface_treatment_mismatch_is_flagged(self):
        mat = normalize_material(material(**{"assembly-surface-treatment": "bare"}))
        self.assertTrue(any("surface-treatment" in f for f in configuration_findings(mat)))


class TestEnvelopeCoverage(unittest.TestCase):
    def test_bounding_campaign_has_no_findings(self):
        self.assertEqual(envelope_findings(normalize_environment(campaign_env(), "c"),
                                           normalize_environment(flight_env(), "f")), [])

    def test_exact_axis_match_is_covered(self):
        camp = normalize_environment(campaign_env(**{"electron-energy-kev": 20.0}), "c")
        flight = normalize_environment(flight_env(), "f")
        self.assertEqual(envelope_findings(camp, flight), [])

    def test_float_representation_edge_is_absorbed(self):
        # The flight value is the sum of two stored decimals and lands a few
        # ULPs above the physically identical campaign value; an exact match
        # is compliant, so the logic absorbs the representation error.
        camp = normalize_environment(campaign_env(**{"applied-bias-v": 0.3}), "c")
        flight = normalize_environment(flight_env(**{"applied-bias-v": 0.1 + 0.2}), "f")
        self.assertGreater(flight["applied-bias-v"], camp["applied-bias-v"])
        self.assertEqual(envelope_findings(camp, flight), [])

    def test_energy_shortfall_is_flagged(self):
        camp = normalize_environment(campaign_env(**{"electron-energy-kev": 5.0}), "c")
        flight = normalize_environment(flight_env(), "f")
        findings = envelope_findings(camp, flight)
        self.assertTrue(any("electron-energy-kev" in f for f in findings))

    def test_cold_end_shortfall_is_flagged(self):
        camp = normalize_environment(campaign_env(**{"temperature-min-c": -10.0}), "c")
        flight = normalize_environment(flight_env(), "f")
        self.assertTrue(any("cold-end" in f for f in envelope_findings(camp, flight)))

    def test_hot_end_shortfall_is_flagged(self):
        camp = normalize_environment(campaign_env(**{"temperature-max-c": 40.0}), "c")
        flight = normalize_environment(flight_env(), "f")
        self.assertTrue(any("hot-end" in f for f in envelope_findings(camp, flight)))

    def test_margins_are_reported_per_axis(self):
        margins = envelope_margins(normalize_environment(campaign_env(), "c"),
                                   normalize_environment(flight_env(), "f"))
        self.assertAlmostEqual(margins["electron-energy-kev"], 5.0)
        self.assertAlmostEqual(margins["temperature-cold-margin-c"], 15.0)
        self.assertAlmostEqual(margins["temperature-hot-margin-c"], 20.0)


class TestParameterCoverage(unittest.TestCase):
    def test_all_parameters_observed(self):
        observed, unobserved = parameter_coverage(
            ["bulk-resistivity", "surface-resistivity"],
            normalize_campaign(campaign())["instrumentation"],
        )
        self.assertEqual(observed, ["bulk-resistivity", "surface-resistivity"])
        self.assertEqual(unobserved, [])

    def test_unobserved_parameter_is_split_out(self):
        observed, unobserved = parameter_coverage(
            ["bulk-resistivity", "photoemission-yield"],
            normalize_campaign(campaign())["instrumentation"],
        )
        self.assertEqual(observed, ["bulk-resistivity"])
        self.assertEqual(unobserved, ["photoemission-yield"])

    def test_unknown_parameter_in_coverage_raises(self):
        with self.assertRaises(ValueError):
            parameter_coverage(["solar-absorptance"], {"surface-current-monitor"})


class TestWaiverDecision(unittest.TestCase):
    def test_fully_covered_material_is_waived(self):
        result = evaluate_material_waiver(material(), campaign())
        self.assertEqual(result["waiver"], "granted")
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["residual-parameters"], [])

    def test_development_campaign_refuses_the_waiver(self):
        result = evaluate_material_waiver(material(), campaign(level="development"))
        self.assertEqual(result["waiver"], "refused")
        self.assertTrue(any("cannot carry a waiver" in f for f in result["findings"]))

    def test_material_exposed_outside_assembly_is_refused(self):
        result = evaluate_material_waiver(
            material(**{"exposed-outside-assembly": True}), campaign()
        )
        self.assertEqual(result["waiver"], "refused")
        self.assertEqual(result["residual-parameters"], ["bulk-resistivity", "surface-resistivity"])

    def test_missing_channel_refuses_and_names_the_parameter(self):
        result = evaluate_material_waiver(
            material(parameters=["photoemission-yield"]), campaign()
        )
        self.assertEqual(result["waiver"], "refused")
        self.assertTrue(any("photoemission-yield" in f for f in result["findings"]))

    def test_envelope_shortfall_refuses_the_waiver(self):
        result = evaluate_material_waiver(
            material(**{"flight-environment": flight_env(**{"exposure-duration-h": 5000.0})}),
            campaign(),
        )
        self.assertEqual(result["waiver"], "refused")

    def test_margins_are_returned_with_the_decision(self):
        result = evaluate_material_waiver(material(), campaign())
        self.assertAlmostEqual(result["margins"]["exposure-duration-h"], 50.0)


class TestProgrammeAggregation(unittest.TestCase):
    def test_all_materials_waived_completes_the_programme(self):
        report = assess_characterization_programme(
            campaign(), [material(), material(id="teflon-strip")]
        )
        self.assertTrue(report["complete"])
        self.assertEqual(report["residual-matrix"], {})
        self.assertEqual(report["waived"], ["kapton-outer", "teflon-strip"])

    def test_one_uncovered_material_leaves_a_residual_matrix(self):
        report = assess_characterization_programme(
            campaign(),
            [material(), material(id="ptfe-shim", parameters=["dielectric-strength"])],
        )
        self.assertFalse(report["complete"])
        self.assertIn("ptfe-shim", report["residual-matrix"])
        self.assertEqual(report["waived"], ["kapton-outer"])

    def test_duplicate_material_id_raises(self):
        with self.assertRaises(ValueError):
            assess_characterization_programme(campaign(), [material(), material()])

    def test_empty_material_list_raises(self):
        with self.assertRaises(ValueError):
            assess_characterization_programme(campaign(), [])

    def test_campaign_level_is_echoed(self):
        report = assess_characterization_programme(campaign(level="protoflight"), [material()])
        self.assertEqual(report["level"], "protoflight")


if __name__ == "__main__":
    unittest.main()
