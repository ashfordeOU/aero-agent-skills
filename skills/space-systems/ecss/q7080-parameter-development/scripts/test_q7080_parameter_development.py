"""Contract tests for the per-material parameter-development logic."""

import unittest

from q7080_parameter_development_logic import (
    MIN_DISTINCT_ENERGY_POINTS,
    MIN_TRIALS,
    bracketing_findings,
    categorize_regime,
    develop_parameters,
    evaluate_campaign,
    evaluate_trial,
    linear_energy_density,
    porosity_pct,
    relative_density_pct,
    select_parameter_set,
    validate_energy_band,
    validate_parameters,
    volumetric_energy_density,
)

REFERENCE = 4430.0          # kg/m^3, wrought titanium alloy reference
BAND = (45.0, 110.0)        # J/mm^3 stable band declared for the material


def params(power, speed, hatch=0.10, layer=0.03):
    return {
        "beam_power_w": power,
        "scan_speed_mm_s": speed,
        "hatch_spacing_mm": hatch,
        "layer_thickness_mm": layer,
    }


TRIALS = [
    {"id": "t1", "material": "TiAl6V4", "parameters": params(170, 1200), "measured_density": 4340.0},
    {"id": "t2", "material": "TiAl6V4", "parameters": params(200, 1000), "measured_density": 4420.0},
    {"id": "t3", "material": "TiAl6V4", "parameters": params(250, 900), "measured_density": 4425.0},
    {"id": "t4", "material": "TiAl6V4", "parameters": params(300, 700), "measured_density": 4415.0},
    {"id": "t5", "material": "TiAl6V4", "parameters": params(140, 1400), "measured_density": 4200.0},
]


def spec(trials=None, target=99.5):
    return {
        "material": "TiAl6V4",
        "reference_density": REFERENCE,
        "energy_band": BAND,
        "trials": list(TRIALS if trials is None else trials),
        "target_relative_density_pct": target,
    }


class ParameterValidationTests(unittest.TestCase):
    def test_returns_floats_for_all_four_parameters(self):
        values = validate_parameters(params(200, 1000))
        self.assertAlmostEqual(values["beam_power_w"], 200.0, places=9)
        self.assertAlmostEqual(values["layer_thickness_mm"], 0.03, places=9)

    def test_missing_parameter_rejected(self):
        broken = params(200, 1000)
        del broken["hatch_spacing_mm"]
        with self.assertRaises(ValueError):
            validate_parameters(broken)

    def test_zero_scan_speed_rejected(self):
        with self.assertRaises(ValueError):
            validate_parameters(params(200, 0.0))

    def test_negative_power_rejected(self):
        with self.assertRaises(ValueError):
            validate_parameters(params(-200, 1000))

    def test_boolean_layer_thickness_rejected(self):
        with self.assertRaises(ValueError):
            validate_parameters(params(200, 1000, layer=True))

    def test_non_mapping_rejected(self):
        with self.assertRaises(ValueError):
            validate_parameters([200, 1000, 0.1, 0.03])


class EnergyDensityTests(unittest.TestCase):
    def test_volumetric_energy_density_closed_form(self):
        self.assertAlmostEqual(
            volumetric_energy_density(params(200, 1000)), 200.0 / 3.0, places=9
        )

    def test_linear_energy_density_closed_form(self):
        self.assertAlmostEqual(linear_energy_density(params(200, 1000)), 0.2, places=9)

    def test_thicker_layer_lowers_volumetric_energy(self):
        thin = volumetric_energy_density(params(200, 1000, layer=0.03))
        thick = volumetric_energy_density(params(200, 1000, layer=0.06))
        self.assertAlmostEqual(thick, thin / 2.0, places=9)

    def test_non_finite_speed_rejected(self):
        with self.assertRaises(ValueError):
            volumetric_energy_density(params(200, float("inf")))


class EnergyBandTests(unittest.TestCase):
    def test_band_returned_as_floats(self):
        self.assertEqual(validate_energy_band((45, 110)), (45.0, 110.0))

    def test_inverted_band_rejected(self):
        with self.assertRaises(ValueError):
            validate_energy_band((110.0, 45.0))

    def test_degenerate_band_rejected(self):
        with self.assertRaises(ValueError):
            validate_energy_band((60.0, 60.0))

    def test_malformed_band_rejected(self):
        with self.assertRaises(ValueError):
            validate_energy_band((45.0,))

    def test_below_band_is_lack_of_fusion(self):
        self.assertEqual(categorize_regime(33.0, BAND), "lack-of-fusion")

    def test_above_band_is_keyhole(self):
        self.assertEqual(categorize_regime(142.0, BAND), "keyhole")

    def test_inside_band_is_stable(self):
        self.assertEqual(categorize_regime(70.0, BAND), "stable")

    def test_exact_lower_edge_counts_as_stable(self):
        self.assertEqual(categorize_regime(45.0, BAND), "stable")

    def test_exact_upper_edge_counts_as_stable(self):
        self.assertEqual(categorize_regime(110.0, BAND), "stable")


class DensityTests(unittest.TestCase):
    def test_relative_density_is_a_percentage(self):
        self.assertAlmostEqual(relative_density_pct(4425.0, REFERENCE), 99.887133, places=6)

    def test_full_density_is_one_hundred(self):
        self.assertAlmostEqual(relative_density_pct(REFERENCE, REFERENCE), 100.0, places=9)

    def test_porosity_complements_relative_density(self):
        self.assertAlmostEqual(porosity_pct(99.75), 0.25, places=9)

    def test_density_above_reference_rejected(self):
        with self.assertRaises(ValueError):
            relative_density_pct(4800.0, REFERENCE)

    def test_zero_reference_rejected(self):
        with self.assertRaises(ValueError):
            relative_density_pct(4425.0, 0.0)

    def test_implausible_relative_density_rejected(self):
        with self.assertRaises(ValueError):
            porosity_pct(140.0)


class TrialEvaluationTests(unittest.TestCase):
    def test_record_carries_energy_and_regime(self):
        record = evaluate_trial(TRIALS[1], REFERENCE, BAND)
        self.assertEqual(record["regime"], "stable")
        self.assertAlmostEqual(record["volumetric_energy_density"], 200.0 / 3.0, places=9)

    def test_lack_of_fusion_trial_grouped(self):
        record = evaluate_trial(TRIALS[4], REFERENCE, BAND)
        self.assertEqual(record["regime"], "lack-of-fusion")

    def test_keyhole_trial_grouped(self):
        record = evaluate_trial(TRIALS[3], REFERENCE, BAND)
        self.assertEqual(record["regime"], "keyhole")

    def test_trial_without_id_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_trial({"parameters": params(200, 1000), "measured_density": 4400.0},
                           REFERENCE, BAND)

    def test_duplicate_trial_id_rejected(self):
        doubled = list(TRIALS) + [dict(TRIALS[0])]
        with self.assertRaises(ValueError):
            evaluate_campaign(doubled, REFERENCE, BAND, material="TiAl6V4")

    def test_foreign_material_trial_rejected(self):
        foreign = list(TRIALS[:3]) + [
            {"id": "x1", "material": "AlSi10Mg", "parameters": params(200, 1000),
             "measured_density": 4400.0}
        ]
        with self.assertRaises(ValueError):
            evaluate_campaign(foreign, REFERENCE, BAND, material="TiAl6V4")

    def test_empty_campaign_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_campaign([], REFERENCE, BAND)


class SelectionTests(unittest.TestCase):
    def test_highest_stable_density_selected(self):
        records = evaluate_campaign(TRIALS, REFERENCE, BAND, material="TiAl6V4")
        best = select_parameter_set(records, 99.5)
        self.assertEqual(best["id"], "t3")

    def test_keyhole_trial_never_selected(self):
        hot = [dict(TRIALS[3], measured_density=4429.0)] + list(TRIALS[:3])
        records = evaluate_campaign(hot, REFERENCE, BAND, material="TiAl6V4")
        best = select_parameter_set(records, 99.5)
        self.assertEqual(best["id"], "t3")

    def test_no_trial_meets_target_returns_none(self):
        records = evaluate_campaign(TRIALS, REFERENCE, BAND, material="TiAl6V4")
        self.assertIsNone(select_parameter_set(records, 99.99))

    def test_tie_breaks_towards_lower_energy(self):
        tied = [
            {"id": "a", "regime": "stable", "relative_density_pct": 99.8,
             "volumetric_energy_density": 95.0},
            {"id": "b", "regime": "stable", "relative_density_pct": 99.8,
             "volumetric_energy_density": 62.0},
        ]
        self.assertEqual(select_parameter_set(tied, 99.5)["id"], "b")

    def test_target_equality_is_eligible(self):
        exact = [
            {"id": "e", "regime": "stable", "relative_density_pct": 99.5,
             "volumetric_energy_density": 70.0},
        ]
        self.assertEqual(select_parameter_set(exact, 99.5)["id"], "e")

    def test_target_above_one_hundred_rejected(self):
        records = evaluate_campaign(TRIALS, REFERENCE, BAND, material="TiAl6V4")
        with self.assertRaises(ValueError):
            select_parameter_set(records, 101.0)


class CampaignFindingTests(unittest.TestCase):
    def test_clean_campaign_releases_a_parameter_set(self):
        result = develop_parameters(spec())
        self.assertTrue(result["released"])
        self.assertEqual(result["selected"]["id"], "t3")
        self.assertEqual(result["findings"], [])

    def test_optimum_on_the_span_edge_is_a_finding(self):
        result = develop_parameters(spec(trials=TRIALS[:3] + [TRIALS[4]]))
        self.assertFalse(result["released"])
        self.assertTrue(any("edge of the explored energy span" in f for f in result["findings"]))

    def test_too_few_trials_is_a_finding(self):
        result = develop_parameters(spec(trials=TRIALS[1:4]))
        self.assertTrue(any("development matrix needs at least %d" % MIN_TRIALS in f
                            for f in result["findings"]))

    def test_too_few_distinct_energy_points_is_a_finding(self):
        repeated = [
            dict(TRIALS[1], id="r1"),
            dict(TRIALS[1], id="r2"),
            dict(TRIALS[1], id="r3"),
            dict(TRIALS[1], id="r4"),
        ]
        result = develop_parameters(spec(trials=repeated))
        self.assertTrue(any("at least %d are" % MIN_DISTINCT_ENERGY_POINTS in f
                            for f in result["findings"]))

    def test_unmet_target_is_reported_first(self):
        result = develop_parameters(spec(target=99.99))
        self.assertIsNone(result["selected"])
        self.assertIn("relative-density target", result["findings"][0])

    def test_achieved_density_reported(self):
        result = develop_parameters(spec())
        self.assertAlmostEqual(result["achieved_relative_density_pct"], 99.887133, places=6)

    def test_missing_spec_key_rejected(self):
        broken = spec()
        del broken["energy_band"]
        with self.assertRaises(ValueError):
            develop_parameters(broken)

    def test_blank_material_rejected(self):
        with self.assertRaises(ValueError):
            develop_parameters(dict(spec(), material="  "))

    def test_bracketing_findings_tolerate_a_single_point(self):
        records = evaluate_campaign([TRIALS[1]], REFERENCE, BAND, material="TiAl6V4")
        found = bracketing_findings(records, records[0])
        self.assertTrue(any("development matrix" in f for f in found))


if __name__ == "__main__":
    unittest.main(verbosity=1)
