#!/usr/bin/env python3
"""Gate 3 contract test for e2006-plasma-instrument-spacecraft-provisions."""

import unittest

from e2006_plasma_instrument_spacecraft_provisions_logic import (
    INSTRUMENT_CATALOGUE,
    MIN_CONDUCTIVE_COVERAGE,
    UNIFORMITY_FRACTION,
    assess_mission_provisions,
    categorize_instrument,
    emitter_sizing,
    evaluate_instrument,
    measurement_distortion,
    normalize_instrument,
    required_boom_length_m,
    surface_findings,
    tolerable_body_potential_v,
)


def surface(**over):
    rec = {
        "exposed-area-m2": 20.0,
        "conductive-area-m2": 19.5,
        "unbonded-conductive-areas": 0,
        "potential-spread-v": 0.05,
    }
    rec.update(over)
    return rec


def design(**over):
    rec = {
        "body-potential-v": -0.2,
        "debye-length-m": 0.2,
        "photoelectron-cloud-m": 1.0,
        "surface": surface(),
        "net-collected-current-a": 1.0e-4,
    }
    rec.update(over)
    return rec


def probe(**over):
    rec = {
        "id": "LP-1",
        "kind": "langmuir-probe",
        "min-energy-ev": 5.0,
        "boom-length-m": 2.0,
    }
    rec.update(over)
    return rec


def spectrometer(**over):
    rec = {"id": "ESA-1", "kind": "electron-spectrometer", "min-energy-ev": 1000.0}
    rec.update(over)
    return rec


class TestInstrumentCatalogue(unittest.TestCase):
    def test_known_kind_resolves(self):
        entry = categorize_instrument("langmuir-probe")
        self.assertTrue(entry["plasma-sensitive"])
        self.assertTrue(entry["needs-boom"])

    def test_kind_is_case_and_separator_insensitive(self):
        self.assertEqual(
            categorize_instrument("Electric_Field Double Probe")["kind"],
            "electric-field-double-probe",
        )

    def test_non_plasma_instrument_carries_no_provision(self):
        self.assertFalse(categorize_instrument("star-tracker")["plasma-sensitive"])

    def test_every_catalogue_entry_is_self_consistent(self):
        for key, entry in INSTRUMENT_CATALOGUE.items():
            self.assertEqual(categorize_instrument(key)["kind"], key)
            if entry["needs-boom"]:
                self.assertGreater(entry["debye-multiple"], 0.0)

    def test_unknown_kind_raises(self):
        with self.assertRaises(ValueError):
            categorize_instrument("dust-detector")

    def test_blank_kind_raises(self):
        with self.assertRaises(ValueError):
            categorize_instrument("  ")


class TestPotentialLimits(unittest.TestCase):
    def test_tolerable_potential_is_energy_times_allowance(self):
        self.assertAlmostEqual(tolerable_body_potential_v(5.0, 0.05), 0.25)

    def test_full_allowance_is_permitted(self):
        self.assertAlmostEqual(tolerable_body_potential_v(10.0, 1.0), 10.0)

    def test_zero_energy_raises(self):
        with self.assertRaises(ValueError):
            tolerable_body_potential_v(0.0, 0.1)

    def test_zero_allowance_raises(self):
        with self.assertRaises(ValueError):
            tolerable_body_potential_v(5.0, 0.0)

    def test_allowance_above_unity_raises(self):
        with self.assertRaises(ValueError):
            tolerable_body_potential_v(5.0, 1.2)

    def test_distortion_is_potential_over_energy(self):
        self.assertAlmostEqual(measurement_distortion(-2.0, 4.0), 0.5)

    def test_distortion_uses_magnitude(self):
        self.assertAlmostEqual(measurement_distortion(2.0, 4.0), measurement_distortion(-2.0, 4.0))

    def test_distortion_on_zero_energy_raises(self):
        with self.assertRaises(ValueError):
            measurement_distortion(1.0, 0.0)

    def test_distortion_on_non_numeric_potential_raises(self):
        with self.assertRaises(ValueError):
            measurement_distortion("1.0", 4.0)


class TestInstrumentNormalization(unittest.TestCase):
    def test_limits_are_derived_from_energy(self):
        rec = normalize_instrument(probe())
        self.assertAlmostEqual(rec["tolerable-body-potential-v"], 0.25)
        self.assertAlmostEqual(rec["uniformity-limit-v"], 0.25 * UNIFORMITY_FRACTION)

    def test_custom_allowance_overrides_the_catalogue(self):
        rec = normalize_instrument(probe(**{"distortion-allowance": 0.02}))
        self.assertAlmostEqual(rec["tolerable-body-potential-v"], 0.1)

    def test_non_plasma_instrument_has_no_limits(self):
        rec = normalize_instrument({"id": "ST-1", "kind": "star-tracker"})
        self.assertIsNone(rec["tolerable-body-potential-v"])
        self.assertIsNone(rec["boom-length-m"])

    def test_missing_boom_on_a_boom_instrument_raises(self):
        rec = probe()
        del rec["boom-length-m"]
        with self.assertRaises(ValueError):
            normalize_instrument(rec)

    def test_negative_boom_raises(self):
        with self.assertRaises(ValueError):
            normalize_instrument(probe(**{"boom-length-m": -0.5}))

    def test_missing_id_raises(self):
        rec = probe()
        del rec["id"]
        with self.assertRaises(ValueError):
            normalize_instrument(rec)

    def test_non_mapping_instrument_raises(self):
        with self.assertRaises(ValueError):
            normalize_instrument(["LP-1"])


class TestBoomSizing(unittest.TestCase):
    def test_required_length_adds_cloud_to_debye_multiple(self):
        self.assertAlmostEqual(required_boom_length_m(3.0, 0.2, 1.0), 1.6)

    def test_zero_multiple_leaves_the_cloud_extent(self):
        self.assertAlmostEqual(required_boom_length_m(0.0, 0.2, 1.0), 1.0)

    def test_zero_debye_length_raises(self):
        with self.assertRaises(ValueError):
            required_boom_length_m(3.0, 0.0, 1.0)

    def test_negative_multiple_raises(self):
        with self.assertRaises(ValueError):
            required_boom_length_m(-1.0, 0.2, 1.0)

    def test_negative_cloud_extent_raises(self):
        with self.assertRaises(ValueError):
            required_boom_length_m(3.0, 0.2, -0.1)


class TestSurfaceCleanliness(unittest.TestCase):
    def test_clean_surface_has_no_findings(self):
        report = surface_findings(surface())
        self.assertEqual(report["findings"], [])
        self.assertAlmostEqual(report["coverage"], 0.975)

    def test_coverage_shortfall_is_flagged(self):
        report = surface_findings(surface(**{"conductive-area-m2": 15.0}))
        self.assertTrue(any("coverage" in f for f in report["findings"]))

    def test_coverage_float_edge_is_absorbed(self):
        # The conductive area is exactly 95% of the exposed area, but the
        # stored product divides back a few ULPs low; an exactly-compliant
        # surface must not read as short.
        total = 3.0
        rec = surface(
            **{"exposed-area-m2": total, "conductive-area-m2": MIN_CONDUCTIVE_COVERAGE * total}
        )
        report = surface_findings(rec)
        self.assertLess(report["coverage"], MIN_CONDUCTIVE_COVERAGE)
        self.assertEqual(report["findings"], [])

    def test_unbonded_conductive_area_is_flagged(self):
        report = surface_findings(surface(**{"unbonded-conductive-areas": 2}))
        self.assertTrue(any("bonded" in f for f in report["findings"]))

    def test_conductive_area_above_total_raises(self):
        with self.assertRaises(ValueError):
            surface_findings(surface(**{"conductive-area-m2": 25.0}))

    def test_zero_exposed_area_raises(self):
        with self.assertRaises(ValueError):
            surface_findings(surface(**{"exposed-area-m2": 0.0}))

    def test_negative_spread_raises(self):
        with self.assertRaises(ValueError):
            surface_findings(surface(**{"potential-spread-v": -0.1}))

    def test_boolean_unbonded_count_raises(self):
        with self.assertRaises(ValueError):
            surface_findings(surface(**{"unbonded-conductive-areas": True}))

    def test_non_mapping_surface_raises(self):
        with self.assertRaises(ValueError):
            surface_findings("conductive")


class TestEmitterSizing(unittest.TestCase):
    def test_adequate_device_reports_positive_margin(self):
        report = emitter_sizing(1.0e-4, 5.0e-4)
        self.assertTrue(report["adequate"])
        self.assertAlmostEqual(report["required-current-a"], 1.5e-4)
        self.assertGreater(report["margin-a"], 0.0)

    def test_undersized_device_is_inadequate(self):
        self.assertFalse(emitter_sizing(1.0e-4, 1.0e-4)["adequate"])

    def test_exact_capability_is_adequate(self):
        self.assertTrue(emitter_sizing(1.0e-4, 1.5e-4)["adequate"])

    def test_margin_below_unity_raises(self):
        with self.assertRaises(ValueError):
            emitter_sizing(1.0e-4, 5.0e-4, 0.8)

    def test_zero_net_current_raises(self):
        with self.assertRaises(ValueError):
            emitter_sizing(0.0, 5.0e-4)

    def test_negative_capability_raises(self):
        with self.assertRaises(ValueError):
            emitter_sizing(1.0e-4, -1.0e-4)


class TestInstrumentEvaluation(unittest.TestCase):
    def test_compliant_design_has_no_findings(self):
        result = evaluate_instrument(probe(), design())
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["distortion"], 0.04)

    def test_exact_potential_limit_is_compliant(self):
        result = evaluate_instrument(probe(), design(**{"body-potential-v": -0.25}))
        self.assertTrue(result["compliant"])

    def test_body_potential_exceedance_is_flagged(self):
        result = evaluate_instrument(probe(), design(**{"body-potential-v": -3.0}))
        self.assertTrue(any("body potential" in f for f in result["findings"]))

    def test_uniformity_exceedance_is_flagged(self):
        rec = design(surface=surface(**{"potential-spread-v": 0.4}))
        result = evaluate_instrument(probe(), rec)
        self.assertTrue(any("spread" in f for f in result["findings"]))

    def test_short_boom_is_flagged(self):
        result = evaluate_instrument(probe(**{"boom-length-m": 0.5}), design())
        self.assertTrue(any("boom" in f for f in result["findings"]))

    def test_boom_length_float_edge_is_absorbed(self):
        # 3 x 0.2 + 1.0 stores a few ULPs above 1.6; a 1.6 m boom is the
        # exactly-compliant case and must not read as short.
        self.assertGreater(required_boom_length_m(3.0, 0.2, 1.0), 1.5999999999)
        result = evaluate_instrument(probe(**{"boom-length-m": 1.6}), design())
        self.assertTrue(result["compliant"])

    def test_high_energy_spectrometer_tolerates_the_same_potential(self):
        result = evaluate_instrument(spectrometer(), design(**{"body-potential-v": -3.0}))
        self.assertTrue(result["compliant"])

    def test_non_plasma_instrument_is_not_applicable(self):
        result = evaluate_instrument({"id": "ST-1", "kind": "star-tracker"}, design())
        self.assertFalse(result["applicable"])
        self.assertEqual(result["findings"], [])

    def test_non_mapping_design_raises(self):
        with self.assertRaises(ValueError):
            evaluate_instrument(probe(), "clean")


class TestMissionProvisions(unittest.TestCase):
    def test_driving_instrument_is_the_tightest(self):
        report = assess_mission_provisions([spectrometer(), probe()], design())
        self.assertEqual(report["driving-instrument"], "LP-1")
        self.assertAlmostEqual(report["body-potential-limit-v"], 0.25)
        self.assertTrue(report["compliant"])

    def test_no_plasma_instrument_makes_the_clause_inapplicable(self):
        report = assess_mission_provisions(
            [{"id": "ST-1", "kind": "star-tracker"}], design(**{"body-potential-v": -50.0})
        )
        self.assertFalse(report["applicable"])
        self.assertTrue(report["compliant"])
        self.assertIsNone(report["driving-instrument"])

    def test_active_control_required_and_adequately_sized(self):
        rec = design(
            **{
                "body-potential-v": -4.0,
                "emitter-capability-a": 5.0e-4,
                "controlled-body-potential-v": -0.1,
            }
        )
        report = assess_mission_provisions([probe()], rec)
        self.assertTrue(report["active-control-required"])
        self.assertTrue(report["emitter"]["adequate"])
        self.assertAlmostEqual(report["effective-body-potential-v"], 0.1)
        self.assertTrue(report["compliant"])

    def test_active_control_required_but_no_emitter_on_record(self):
        report = assess_mission_provisions([probe()], design(**{"body-potential-v": -4.0}))
        self.assertTrue(report["active-control-required"])
        self.assertTrue(any("no emitter" in f for f in report["findings"]))
        self.assertFalse(report["compliant"])

    def test_undersized_emitter_leaves_the_passive_potential(self):
        rec = design(
            **{
                "body-potential-v": -4.0,
                "emitter-capability-a": 1.0e-5,
                "controlled-body-potential-v": -0.1,
            }
        )
        report = assess_mission_provisions([probe()], rec)
        self.assertFalse(report["emitter"]["adequate"])
        self.assertAlmostEqual(report["effective-body-potential-v"], 4.0)
        self.assertFalse(report["compliant"])

    def test_adequate_emitter_without_a_predicted_potential_is_flagged(self):
        rec = design(**{"body-potential-v": -4.0, "emitter-capability-a": 5.0e-4})
        report = assess_mission_provisions([probe()], rec)
        self.assertTrue(any("not predicted" in f for f in report["findings"]))

    def test_surface_finding_reaches_the_mission_verdict(self):
        rec = design(surface=surface(**{"conductive-area-m2": 10.0}))
        report = assess_mission_provisions([probe()], rec)
        self.assertFalse(report["compliant"])
        self.assertTrue(any("coverage" in f for f in report["findings"]))

    def test_duplicate_instrument_id_raises(self):
        with self.assertRaises(ValueError):
            assess_mission_provisions([probe(), probe()], design())

    def test_empty_instrument_list_raises(self):
        with self.assertRaises(ValueError):
            assess_mission_provisions([], design())

    def test_results_cover_every_instrument(self):
        report = assess_mission_provisions(
            [spectrometer(), probe(), {"id": "ST-1", "kind": "star-tracker"}], design()
        )
        self.assertEqual(len(report["results"]), 3)
        self.assertEqual(
            sorted(r["instrument"] for r in report["results"]), ["ESA-1", "LP-1", "ST-1"]
        )


if __name__ == "__main__":
    unittest.main()
