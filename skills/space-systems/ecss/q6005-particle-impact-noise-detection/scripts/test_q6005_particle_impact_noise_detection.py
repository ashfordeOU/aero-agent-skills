"""Contract test for the particle-impact-noise-detection leaf (stdlib unittest)."""

import math
import unittest

from q6005_particle_impact_noise_detection_logic import (
    FAIL,
    FREQUENCY_BAND_HZ,
    G0,
    MAX_TEST_RUNS,
    PARTICLE_DENSITY_G_CM3,
    PASS,
    PIND_CONDITIONS,
    REQUIRED_CYCLES,
    assess_detection_lot,
    assess_unit,
    block_withdrawal,
    bridging_particle_mass_ug,
    check_applicability,
    check_excitation,
    check_indications,
    check_sensitivity,
    condition_levels,
    package_has_cavity,
    stroke_demand_ratio,
    validate_unit,
    vibration_displacement_mm,
)


def unit(unit_id="U-1", **kw):
    record = {
        "id": unit_id,
        "package_style": "metal-lid-flatpack-cavity",
        "condition": "A",
        "particle_material": "gold-wire-offcut",
        "vibration_peak_g": 20.0,
        "frequency_hz": 60.0,
        "shock_peak_g": 1000.0,
        "cycles_run": 5,
        "conductor_spacing_mm": 0.15,
        "system_threshold_ug": 0.5,
        "test_runs": 1,
        "sensitivity_verified_before": True,
        "indication_recorded": False,
    }
    record.update(kw)
    return record


class TestApplicability(unittest.TestCase):
    def test_a_sealed_cavity_can_be_listened_into(self):
        self.assertTrue(package_has_cavity("ceramic-sealed-cavity"))
        self.assertEqual(check_applicability(unit()), [])

    def test_a_solid_body_has_nothing_to_hear(self):
        self.assertFalse(package_has_cavity("solid-encapsulated-body"))
        self.assertIn(
            "package-style-has-no-cavity-to-listen-into",
            check_applicability(unit("U-1", package_style="solid-encapsulated-body")),
        )

    def test_conformal_coated_assembly_is_not_eligible(self):
        self.assertFalse(package_has_cavity("conformal-coated-open-assembly"))

    def test_unknown_package_style_raises(self):
        with self.assertRaises(ValueError):
            package_has_cavity("mystery-box")


class TestConditions(unittest.TestCase):
    def test_condition_carries_a_vibration_and_a_shock_peak(self):
        vib, shock = condition_levels("A")
        self.assertAlmostEqual(vib, 20.0, places=9)
        self.assertAlmostEqual(shock, 1000.0, places=9)

    def test_the_gentler_condition_is_lower_on_both_axes(self):
        vib_a, shock_a = condition_levels("A")
        vib_b, shock_b = condition_levels("B")
        self.assertLess(vib_b, vib_a)
        self.assertLess(shock_b, shock_a)

    def test_every_condition_is_tabulated(self):
        for name in PIND_CONDITIONS:
            vib, shock = condition_levels(name)
            self.assertGreater(vib, 0.0)
            self.assertGreater(shock, 0.0)

    def test_unknown_condition_raises(self):
        with self.assertRaises(ValueError):
            condition_levels("Z")


class TestStroke(unittest.TestCase):
    def test_stroke_follows_the_sinusoidal_relation(self):
        omega = 2.0 * math.pi * 60.0
        self.assertAlmostEqual(
            vibration_displacement_mm(20.0, 60.0),
            (20.0 * G0 / (omega * omega)) * 1000.0,
            places=12,
        )

    def test_the_same_peak_needs_more_stroke_lower_down(self):
        self.assertGreater(
            vibration_displacement_mm(20.0, 40.0),
            vibration_displacement_mm(20.0, 250.0),
        )

    def test_stroke_demand_scales_with_the_frequency_ratio_squared(self):
        ratio = stroke_demand_ratio(20.0, 40.0, 250.0)
        self.assertAlmostEqual(ratio, (250.0 / 40.0) ** 2, places=9)

    def test_zero_frequency_raises(self):
        with self.assertRaises(ValueError):
            vibration_displacement_mm(20.0, 0.0)

    def test_boolean_peak_raises(self):
        with self.assertRaises(ValueError):
            vibration_displacement_mm(True, 60.0)


class TestBridgingParticle(unittest.TestCase):
    def test_mass_follows_the_sphere_volume(self):
        diameter_cm = 0.15 / 10.0
        expected = (
            (math.pi / 6.0)
            * diameter_cm ** 3
            * PARTICLE_DENSITY_G_CM3["gold-wire-offcut"]
            * 1.0e6
        )
        self.assertAlmostEqual(
            bridging_particle_mass_ug(0.15, "gold-wire-offcut"), expected, places=12
        )

    def test_a_denser_particle_is_heavier_at_the_same_size(self):
        self.assertGreater(
            bridging_particle_mass_ug(0.15, "gold-wire-offcut"),
            bridging_particle_mass_ug(0.15, "epoxy-flake"),
        )

    def test_a_tighter_spacing_lowers_the_mass_that_matters(self):
        self.assertLess(
            bridging_particle_mass_ug(0.05, "solder-ball"),
            bridging_particle_mass_ug(0.15, "solder-ball"),
        )

    def test_unknown_material_raises(self):
        with self.assertRaises(ValueError):
            bridging_particle_mass_ug(0.15, "unobtainium-dust")

    def test_zero_spacing_raises(self):
        with self.assertRaises(ValueError):
            bridging_particle_mass_ug(0.0, "solder-ball")


class TestValidation(unittest.TestCase):
    def test_non_mapping_raises(self):
        with self.assertRaises(ValueError):
            validate_unit(["U-1"])

    def test_empty_id_raises(self):
        with self.assertRaises(ValueError):
            validate_unit(unit(""))

    def test_zero_cycles_raises(self):
        with self.assertRaises(ValueError):
            validate_unit(unit("U-1", cycles_run=0))

    def test_non_integer_cycles_raises(self):
        with self.assertRaises(ValueError):
            validate_unit(unit("U-1", cycles_run=5.0))

    def test_non_boolean_indication_flag_raises(self):
        with self.assertRaises(ValueError):
            validate_unit(unit("U-1", indication_recorded="quiet"))

    def test_defaults_fill_the_optional_fields(self):
        norm = validate_unit(
            {
                "id": "U-9",
                "package_style": "metal-can-sealed-cavity",
                "condition": "B",
                "vibration_peak_g": 10.0,
                "frequency_hz": 60.0,
                "shock_peak_g": 500.0,
                "cycles_run": 5,
                "conductor_spacing_mm": 0.2,
                "system_threshold_ug": 0.5,
            }
        )
        self.assertEqual(norm["test_runs"], 1)
        self.assertFalse(norm["indication_recorded"])
        self.assertEqual(norm["particle_material"], "gold-wire-offcut")


class TestExcitationFindings(unittest.TestCase):
    def test_low_vibration_peak_is_a_finding(self):
        self.assertIn(
            "vibration-peak-below-the-condition",
            check_excitation(unit("U-1", vibration_peak_g=5.0)),
        )

    def test_frequency_outside_the_band_is_a_finding(self):
        self.assertIn(
            "vibration-frequency-outside-the-band",
            check_excitation(unit("U-1", frequency_hz=12.0)),
        )

    def test_frequency_exactly_on_the_band_edge_is_accepted(self):
        low, high = FREQUENCY_BAND_HZ
        self.assertNotIn(
            "vibration-frequency-outside-the-band",
            check_excitation(unit("U-1", frequency_hz=low)),
        )
        self.assertNotIn(
            "vibration-frequency-outside-the-band",
            check_excitation(unit("U-1", frequency_hz=high)),
        )

    def test_low_shock_pulse_is_a_finding(self):
        self.assertIn(
            "shock-pulse-below-the-condition",
            check_excitation(unit("U-1", shock_peak_g=200.0)),
        )

    def test_too_few_cycles_is_a_finding(self):
        self.assertIn(
            "fewer-cycles-than-the-method-requires",
            check_excitation(unit("U-1", cycles_run=REQUIRED_CYCLES - 1)),
        )

    def test_a_correct_excitation_carries_no_finding(self):
        self.assertEqual(check_excitation(unit()), [])


class TestSensitivityFindings(unittest.TestCase):
    def test_unverified_system_is_a_finding(self):
        self.assertIn(
            "system-sensitivity-not-verified-before-the-run",
            check_sensitivity(unit("U-1", sensitivity_verified_before=False)),
        )

    def test_a_coarse_threshold_is_a_finding(self):
        findings = check_sensitivity(unit("U-1", system_threshold_ug=500.0))
        self.assertIn("threshold-coarser-than-the-bridging-particle", findings)

    def test_threshold_exactly_on_the_bridging_mass_is_absorbed(self):
        mass = bridging_particle_mass_ug(0.15, "gold-wire-offcut")
        findings = check_sensitivity(unit("U-1", system_threshold_ug=mass))
        self.assertNotIn("threshold-coarser-than-the-bridging-particle", findings)

    def test_a_fine_threshold_carries_no_finding(self):
        self.assertEqual(check_sensitivity(unit()), [])


class TestIndications(unittest.TestCase):
    def test_an_indication_is_a_finding(self):
        self.assertIn(
            "noise-indication-recorded",
            check_indications(unit("U-1", indication_recorded=True)),
        )

    def test_too_many_runs_is_a_finding(self):
        self.assertIn(
            "more-test-runs-than-the-allowance",
            check_indications(unit("U-1", test_runs=MAX_TEST_RUNS + 1)),
        )

    def test_re_running_an_indicating_unit_is_its_own_finding(self):
        findings = check_indications(
            unit("U-1", indication_recorded=True, test_runs=2)
        )
        self.assertIn("indicating-unit-re-run-instead-of-rejected", findings)

    def test_a_quiet_unit_may_be_re_run_inside_the_allowance(self):
        self.assertEqual(check_indications(unit("U-1", test_runs=MAX_TEST_RUNS)), [])


class TestAssessUnit(unittest.TestCase):
    def test_a_sound_run_passes(self):
        result = assess_unit(unit())
        self.assertEqual(result["disposition"], PASS)
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["required_cycles"], REQUIRED_CYCLES)

    def test_any_finding_rejects_the_unit(self):
        self.assertEqual(assess_unit(unit("U-1", cycles_run=1))["disposition"], FAIL)

    def test_report_carries_the_stroke_and_the_bridging_mass(self):
        result = assess_unit(unit())
        self.assertAlmostEqual(
            result["stroke_mm"], vibration_displacement_mm(20.0, 60.0), places=12
        )
        self.assertAlmostEqual(
            result["bridging_particle_mass_ug"],
            bridging_particle_mass_ug(0.15, "gold-wire-offcut"),
            places=12,
        )


class TestBlockWithdrawal(unittest.TestCase):
    def test_a_passing_closing_check_withdraws_nothing(self):
        self.assertEqual(block_withdrawal([unit("U-1"), unit("U-2")], True), [])

    def test_a_failed_closing_check_withdraws_the_whole_block(self):
        self.assertEqual(
            block_withdrawal([unit("U-1"), unit("U-2"), unit("U-3")], False),
            ["U-1", "U-2", "U-3"],
        )

    def test_duplicate_id_in_a_block_raises(self):
        with self.assertRaises(ValueError):
            block_withdrawal([unit("U-1"), unit("U-1")], False)

    def test_non_boolean_closing_check_raises(self):
        with self.assertRaises(ValueError):
            block_withdrawal([unit("U-1")], "passed")

    def test_empty_block_raises(self):
        with self.assertRaises(ValueError):
            block_withdrawal([], True)


class TestLot(unittest.TestCase):
    def test_a_clean_lot_is_accepted(self):
        report = assess_detection_lot([unit("U-1"), unit("U-2")])
        self.assertTrue(report["lot_accepted"])
        self.assertEqual(report["rejected_ids"], [])
        self.assertAlmostEqual(report["indication_fraction"], 0.0, places=12)

    def test_an_indicating_unit_is_named_and_rejected(self):
        report = assess_detection_lot(
            [unit("U-1"), unit("U-2", indication_recorded=True)]
        )
        self.assertEqual(report["indicating_ids"], ["U-2"])
        self.assertEqual(report["rejected_ids"], ["U-2"])
        self.assertAlmostEqual(report["indication_fraction"], 0.5, places=12)
        self.assertFalse(report["lot_accepted"])

    def test_a_failed_closing_check_refuses_an_otherwise_clean_lot(self):
        report = assess_detection_lot([unit("U-1"), unit("U-2")], False)
        self.assertFalse(report["lot_accepted"])
        self.assertEqual(report["withdrawn_ids"], ["U-1", "U-2"])

    def test_duplicate_unit_id_raises(self):
        with self.assertRaises(ValueError):
            assess_detection_lot([unit("U-1"), unit("U-1")])

    def test_empty_lot_raises(self):
        with self.assertRaises(ValueError):
            assess_detection_lot([])

    def test_non_list_lot_raises(self):
        with self.assertRaises(ValueError):
            assess_detection_lot(unit())


if __name__ == "__main__":
    unittest.main()
