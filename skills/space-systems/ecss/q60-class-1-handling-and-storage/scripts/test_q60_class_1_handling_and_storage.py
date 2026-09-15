"""Contract tests for the clause 4.4 handling, packaging and storage logic."""

import unittest

from q60_class_1_handling_and_storage_logic import (
    BASE_PACKAGING_LAYERS,
    BOUND_TOLERANCE,
    DOUBLING_INTERVAL_C,
    FRAGILITY_LAYERS,
    HANDLING_AUTHORIZATIONS,
    MOISTURE_BARRIER_LAYERS,
    REFERENCE_TEMPERATURE_C,
    assess_class_1_handling,
    container_findings,
    degradation_allowance_exceeded,
    handling_verdict,
    missing_authorizations,
    missing_packaging_layers,
    required_packaging_layers,
    shock_exposure_ratio,
    thermal_degradation_index,
)


def _pack(**over):
    base = {
        "fragility": "standard",
        "moisture_barrier_required": False,
        "layers_present": list(BASE_PACKAGING_LAYERS),
        "seal_intact": True,
        "indicator_percent": 8.0,
        "indicator_threshold_percent": 10.0,
        "peak_shock_g": 24.0,
        "allowable_shock_g": 60.0,
        "storage_days": 180.0,
        "mean_temperature_c": REFERENCE_TEMPERATURE_C,
        "degradation_allowance_days": 730.0,
        "authorizations_held": list(HANDLING_AUTHORIZATIONS),
    }
    base.update(over)
    return base


class PackagingLayerTests(unittest.TestCase):
    def test_base_layers_apply_to_every_part(self):
        for category in FRAGILITY_LAYERS:
            owed = required_packaging_layers(category)
            self.assertTrue(set(BASE_PACKAGING_LAYERS) <= set(owed))

    def test_a_fragile_part_owes_a_cushioned_tray(self):
        self.assertIn("cushioned-inner-tray", required_packaging_layers("fragile"))

    def test_a_standard_part_does_not_owe_foam_suspension(self):
        self.assertNotIn("foam-suspension-insert", required_packaging_layers("standard"))

    def test_a_moisture_barrier_adds_its_three_layers(self):
        owed = required_packaging_layers("standard", True)
        self.assertTrue(set(MOISTURE_BARRIER_LAYERS) <= set(owed))

    def test_unknown_fragility_rejected(self):
        with self.assertRaises(ValueError):
            required_packaging_layers("delicate")

    def test_non_boolean_moisture_flag_rejected(self):
        with self.assertRaises(ValueError):
            required_packaging_layers("standard", "yes")

    def test_a_complete_pack_reports_nothing_missing(self):
        owed = required_packaging_layers("very-fragile", True)
        self.assertEqual(missing_packaging_layers("very-fragile", True, owed), [])

    def test_missing_layers_are_named(self):
        gaps = missing_packaging_layers("standard", True, BASE_PACKAGING_LAYERS)
        self.assertEqual(sorted(gaps), sorted(MOISTURE_BARRIER_LAYERS))

    def test_layer_names_compare_case_insensitively(self):
        upper = [layer.upper() for layer in BASE_PACKAGING_LAYERS]
        self.assertEqual(missing_packaging_layers("standard", False, upper), [])

    def test_blank_layer_name_rejected(self):
        with self.assertRaises(ValueError):
            missing_packaging_layers("standard", False, ["  "])


class ContainerTests(unittest.TestCase):
    def test_a_sound_container_carries_no_defect(self):
        self.assertEqual(container_findings(True, 8.0, 10.0), [])

    def test_a_breached_seal_is_flagged(self):
        self.assertIn("container-seal-breached", container_findings(False, 8.0, 10.0))

    def test_an_indicator_over_threshold_is_flagged(self):
        self.assertIn("humidity-indicator-over-threshold",
                      container_findings(True, 22.0, 10.0))

    def test_an_indicator_exactly_on_threshold_is_inside(self):
        self.assertEqual(container_findings(True, 10.0, 10.0), [])

    def test_an_impossible_percentage_rejected(self):
        with self.assertRaises(ValueError):
            container_findings(True, 140.0, 10.0)

    def test_a_non_positive_threshold_rejected(self):
        with self.assertRaises(ValueError):
            container_findings(True, 5.0, 0.0)


class ShockTests(unittest.TestCase):
    def test_a_quiet_transport_reads_below_one(self):
        self.assertAlmostEqual(shock_exposure_ratio(30.0, 60.0), 0.5, places=9)

    def test_a_peak_on_the_allowable_reads_one(self):
        self.assertAlmostEqual(shock_exposure_ratio(60.0, 60.0), 1.0, places=9)

    def test_an_exceeded_allowable_reads_above_one(self):
        self.assertAlmostEqual(shock_exposure_ratio(150.0, 60.0), 2.5, places=9)

    def test_a_non_positive_allowable_rejected(self):
        with self.assertRaises(ValueError):
            shock_exposure_ratio(30.0, 0.0)

    def test_a_negative_peak_rejected(self):
        with self.assertRaises(ValueError):
            shock_exposure_ratio(-5.0, 60.0)


class DegradationTests(unittest.TestCase):
    def test_storage_at_the_reference_returns_the_duration(self):
        value = thermal_degradation_index(180.0, REFERENCE_TEMPERATURE_C)
        self.assertAlmostEqual(value, 180.0, places=9)

    def test_one_doubling_interval_doubles_the_index(self):
        warm = REFERENCE_TEMPERATURE_C + DOUBLING_INTERVAL_C
        self.assertAlmostEqual(thermal_degradation_index(100.0, warm), 200.0, places=9)

    def test_one_interval_below_the_reference_halves_the_index(self):
        cool = REFERENCE_TEMPERATURE_C - DOUBLING_INTERVAL_C
        self.assertAlmostEqual(thermal_degradation_index(100.0, cool), 50.0, places=9)

    def test_zero_duration_accumulates_nothing(self):
        self.assertAlmostEqual(thermal_degradation_index(0.0, 45.0), 0.0, places=9)

    def test_a_temperature_below_absolute_zero_rejected(self):
        with self.assertRaises(ValueError):
            thermal_degradation_index(10.0, -400.0)

    def test_a_non_positive_doubling_interval_rejected(self):
        with self.assertRaises(ValueError):
            thermal_degradation_index(10.0, 30.0, doubling_interval_c=0.0)

    def test_an_index_inside_its_allowance_is_not_exceeded(self):
        self.assertFalse(degradation_allowance_exceeded(400.0, 730.0))

    def test_an_index_exactly_on_its_allowance_is_not_exceeded(self):
        self.assertFalse(degradation_allowance_exceeded(730.0, 730.0))

    def test_an_index_past_its_allowance_is_exceeded(self):
        self.assertTrue(degradation_allowance_exceeded(900.0, 730.0))

    def test_a_non_positive_allowance_rejected(self):
        with self.assertRaises(ValueError):
            degradation_allowance_exceeded(400.0, 0.0)

    def test_tolerance_is_the_documented_size(self):
        self.assertAlmostEqual(BOUND_TOLERANCE, 1e-9, places=12)


class AuthorizationTests(unittest.TestCase):
    def test_a_fully_authorized_movement_reports_no_gap(self):
        self.assertEqual(missing_authorizations(HANDLING_AUTHORIZATIONS), [])

    def test_gaps_are_named(self):
        gaps = missing_authorizations(["open-work-order"])
        self.assertEqual(gaps, ["trained-handler-certification", "protected-area-release"])

    def test_unknown_authorization_rejected(self):
        with self.assertRaises(ValueError):
            missing_authorizations(["line-manager-nod"])

    def test_authorizations_must_be_a_sequence(self):
        with self.assertRaises(ValueError):
            missing_authorizations("open-work-order")


class VerdictTests(unittest.TestCase):
    def test_no_findings_is_fit_for_issue(self):
        self.assertEqual(handling_verdict([]), "fit-for-issue")

    def test_a_major_finding_issues_with_actions(self):
        self.assertEqual(
            handling_verdict([{"severity": "major", "topic": "t", "message": "m"}]),
            "issue-with-actions",
        )

    def test_a_critical_finding_holds_for_reconditioning(self):
        self.assertEqual(
            handling_verdict([{"severity": "critical", "topic": "t", "message": "m"}]),
            "hold-for-reconditioning",
        )

    def test_unknown_severity_rejected(self):
        with self.assertRaises(ValueError):
            handling_verdict([{"severity": "blocking", "topic": "t", "message": "m"}])


class AssessmentTests(unittest.TestCase):
    def test_a_sound_pack_is_fit_for_issue(self):
        result = assess_class_1_handling(_pack())
        self.assertTrue(result["fit_for_issue"])
        self.assertEqual(result["findings"], [])

    def test_a_missing_moisture_barrier_holds_the_pack(self):
        result = assess_class_1_handling(_pack(moisture_barrier_required=True))
        self.assertEqual(result["verdict"], "hold-for-reconditioning")
        self.assertEqual(sorted(result["missing_layers"]), sorted(MOISTURE_BARRIER_LAYERS))

    def test_a_breached_seal_holds_the_pack(self):
        result = assess_class_1_handling(_pack(seal_intact=False))
        self.assertEqual(result["verdict"], "hold-for-reconditioning")
        self.assertIn("container-seal-breached", result["container_defects"])

    def test_a_small_shock_overshoot_issues_with_actions(self):
        result = assess_class_1_handling(_pack(peak_shock_g=72.0))
        self.assertEqual(result["verdict"], "issue-with-actions")
        self.assertAlmostEqual(result["shock_exposure_ratio"], 1.2, places=9)

    def test_a_shock_peak_on_the_allowable_stays_fit(self):
        result = assess_class_1_handling(_pack(peak_shock_g=60.0))
        self.assertAlmostEqual(result["shock_exposure_ratio"], 1.0, places=9)
        self.assertTrue(result["fit_for_issue"])

    def test_a_large_shock_overshoot_holds_the_pack(self):
        result = assess_class_1_handling(_pack(peak_shock_g=240.0))
        self.assertEqual(result["verdict"], "hold-for-reconditioning")

    def test_warm_storage_past_the_allowance_holds_the_pack(self):
        result = assess_class_1_handling(
            _pack(storage_days=600.0, mean_temperature_c=REFERENCE_TEMPERATURE_C + 20.0)
        )
        self.assertTrue(result["degradation_allowance_exceeded"])
        self.assertEqual(result["verdict"], "hold-for-reconditioning")

    def test_cool_storage_of_the_same_duration_stays_fit(self):
        result = assess_class_1_handling(
            _pack(storage_days=600.0, mean_temperature_c=REFERENCE_TEMPERATURE_C - 10.0)
        )
        self.assertFalse(result["degradation_allowance_exceeded"])
        self.assertAlmostEqual(result["thermal_degradation_index"], 300.0, places=9)

    def test_a_missing_authorization_issues_with_actions(self):
        result = assess_class_1_handling(_pack(authorizations_held=["open-work-order"]))
        self.assertEqual(result["verdict"], "issue-with-actions")
        self.assertEqual(len(result["missing_authorizations"]), 2)

    def test_findings_are_ranked_critical_first(self):
        result = assess_class_1_handling(
            _pack(seal_intact=False, authorizations_held=["open-work-order"])
        )
        self.assertEqual(result["findings"][0]["severity"], "critical")
        self.assertEqual(result["findings"][-1]["severity"], "major")

    def test_missing_pack_key_rejected(self):
        pack = _pack()
        del pack["allowable_shock_g"]
        with self.assertRaises(ValueError):
            assess_class_1_handling(pack)

    def test_pack_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            assess_class_1_handling([_pack()])


if __name__ == "__main__":
    unittest.main(verbosity=1)
