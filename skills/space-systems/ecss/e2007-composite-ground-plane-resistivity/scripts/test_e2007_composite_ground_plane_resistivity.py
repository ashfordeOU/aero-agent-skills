"""Gate 3 contract test for e2007-composite-ground-plane-resistivity.

Offline, deterministic, stdlib unittest only.
"""

import math
import unittest

import e2007_composite_ground_plane_resistivity_logic as logic


def flight_panel(**overrides):
    spec = {
        "surface_resistivity_ohm_per_square": 1.0e3,
        "directional_ohm_per_square": [1.0e3, 2.0e3],
    }
    spec.update(overrides)
    return spec


def test_panel(**overrides):
    spec = {
        "surface_resistivity_ohm_per_square": 1.2e3,
        "directional_ohm_per_square": [1.2e3, 2.4e3],
        "bond_resistance_mohm": 3.0,
    }
    spec.update(overrides)
    return spec


class TestMeasurementReduction(unittest.TestCase):
    def test_two_probe_square_sample_returns_the_measured_resistance(self):
        self.assertAlmostEqual(
            logic.surface_resistivity_two_probe(500.0, 100.0, 100.0), 500.0, places=9
        )

    def test_two_probe_scales_with_the_width_to_spacing_ratio(self):
        self.assertAlmostEqual(
            logic.surface_resistivity_two_probe(500.0, 200.0, 100.0), 1000.0, places=9
        )

    def test_two_probe_rejects_zero_spacing(self):
        with self.assertRaises(ValueError):
            logic.surface_resistivity_two_probe(500.0, 100.0, 0.0)

    def test_two_probe_rejects_negative_resistance(self):
        with self.assertRaises(ValueError):
            logic.surface_resistivity_two_probe(-500.0, 100.0, 100.0)

    def test_four_point_uses_the_thin_sheet_geometry_factor(self):
        self.assertAlmostEqual(
            logic.surface_resistivity_four_point(1.0, 1.0),
            math.pi / math.log(2.0),
            places=9,
        )

    def test_four_point_scales_linearly_with_voltage(self):
        single = logic.surface_resistivity_four_point(0.5, 0.01)
        double = logic.surface_resistivity_four_point(1.0, 0.01)
        self.assertAlmostEqual(double, 2.0 * single, places=9)

    def test_four_point_rejects_zero_current(self):
        with self.assertRaises(ValueError):
            logic.surface_resistivity_four_point(1.0, 0.0)

    def test_four_point_accepts_zero_voltage_as_a_reading(self):
        self.assertAlmostEqual(logic.surface_resistivity_four_point(0.0, 0.01), 0.0, places=12)

    def test_volume_reduction_divides_by_thickness(self):
        self.assertAlmostEqual(
            logic.surface_resistivity_from_volume(1.0e-2, 2.0), 5.0, places=9
        )

    def test_volume_reduction_rejects_zero_thickness(self):
        with self.assertRaises(ValueError):
            logic.surface_resistivity_from_volume(1.0e-2, 0.0)

    def test_dispatch_reduces_a_two_probe_record(self):
        record = {
            "method": "two-probe",
            "resistance_ohm": 500.0,
            "bar_width_mm": 200.0,
            "electrode_spacing_mm": 100.0,
        }
        self.assertAlmostEqual(logic.surface_resistivity(record), 1000.0, places=9)

    def test_dispatch_reduces_a_four_point_record(self):
        record = {"method": "Four-Point", "voltage_v": 1.0, "current_a": 1.0}
        self.assertAlmostEqual(
            logic.surface_resistivity(record), math.pi / math.log(2.0), places=9
        )

    def test_dispatch_reduces_a_volume_record(self):
        record = {"method": "volume", "volume_resistivity_ohm_m": 1.0e-2, "thickness_mm": 2.0}
        self.assertAlmostEqual(logic.surface_resistivity(record), 5.0, places=9)

    def test_dispatch_rejects_an_unknown_method(self):
        with self.assertRaises(ValueError):
            logic.surface_resistivity({"method": "eddy-current"})

    def test_dispatch_rejects_a_missing_method(self):
        with self.assertRaises(ValueError):
            logic.surface_resistivity({"resistance_ohm": 500.0})

    def test_dispatch_rejects_a_non_mapping_record(self):
        with self.assertRaises(ValueError):
            logic.surface_resistivity("four-point")


class TestRegimeCategorization(unittest.TestCase):
    def test_low_resistivity_panel_is_conductive(self):
        self.assertEqual(logic.categorize_resistivity_regime(50.0), "conductive")

    def test_panel_just_under_the_boundary_is_conductive(self):
        self.assertEqual(logic.categorize_resistivity_regime(9.999e3), "conductive")

    def test_panel_exactly_on_the_boundary_is_dissipative(self):
        self.assertEqual(logic.categorize_resistivity_regime(1.0e4), "static-dissipative")

    def test_mid_band_panel_is_dissipative(self):
        self.assertEqual(logic.categorize_resistivity_regime(1.0e8), "static-dissipative")

    def test_panel_on_the_upper_boundary_is_insulating(self):
        self.assertEqual(logic.categorize_resistivity_regime(1.0e11), "insulating")

    def test_very_high_resistivity_panel_is_insulating(self):
        self.assertEqual(logic.categorize_resistivity_regime(1.0e14), "insulating")

    def test_zero_resistivity_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.categorize_resistivity_regime(0.0)

    def test_non_numeric_resistivity_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.categorize_resistivity_regime("1e4")


class TestDeviationPrimitives(unittest.TestCase):
    def test_identical_panels_have_no_decade_deviation(self):
        self.assertAlmostEqual(logic.decade_deviation(1.0e3, 1.0e3), 0.0, places=12)

    def test_one_decade_apart(self):
        self.assertAlmostEqual(logic.decade_deviation(1.0e4, 1.0e3), 1.0, places=12)

    def test_deviation_is_symmetric(self):
        self.assertAlmostEqual(
            logic.decade_deviation(1.0e3, 1.0e4), logic.decade_deviation(1.0e4, 1.0e3), places=12
        )

    def test_decade_deviation_rejects_zero(self):
        with self.assertRaises(ValueError):
            logic.decade_deviation(0.0, 1.0e3)

    def test_anisotropy_ratio_is_orientation_independent(self):
        self.assertAlmostEqual(logic.anisotropy_ratio(1.0e3, 2.0e3), 2.0, places=9)
        self.assertAlmostEqual(logic.anisotropy_ratio(2.0e3, 1.0e3), 2.0, places=9)

    def test_isotropic_laminate_has_unit_ratio(self):
        self.assertAlmostEqual(logic.anisotropy_ratio(1.5e3, 1.5e3), 1.0, places=9)

    def test_anisotropy_ratio_rejects_a_negative_direction(self):
        with self.assertRaises(ValueError):
            logic.anisotropy_ratio(-1.0e3, 2.0e3)


class TestIndividualChecks(unittest.TestCase):
    def test_characterized_flight_panel_is_clean(self):
        self.assertEqual(logic.check_flight_characterization(flight_panel()), [])

    def test_uncharacterized_flight_panel_is_major(self):
        findings = logic.check_flight_characterization({"note": "panel not measured"})
        self.assertEqual([f["code"] for f in findings], ["CP-FLIGHT-VALUE-MISSING"])
        self.assertEqual(findings[0]["severity"], "major")

    def test_matching_regime_is_clean(self):
        self.assertEqual(logic.check_regime_match(flight_panel(), test_panel()), [])

    def test_regime_mismatch_is_major(self):
        findings = logic.check_regime_match(
            flight_panel(), test_panel(surface_resistivity_ohm_per_square=1.0e12)
        )
        self.assertEqual([f["code"] for f in findings], ["CP-REGIME-MISMATCH"])
        self.assertEqual(findings[0]["severity"], "major")

    def test_panel_resistivity_can_come_from_a_measurement(self):
        panel = {
            "measurement": {
                "method": "two-probe",
                "resistance_ohm": 1000.0,
                "bar_width_mm": 100.0,
                "electrode_spacing_mm": 100.0,
            },
            "bond_resistance_mohm": 1.0,
        }
        self.assertEqual(logic.check_regime_match(flight_panel(), panel), [])

    def test_panel_without_value_or_measurement_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.check_regime_match(flight_panel(), {"bond_resistance_mohm": 1.0})

    def test_decade_match_within_tolerance_is_clean(self):
        self.assertEqual(logic.check_decade_match(flight_panel(), test_panel()), [])

    def test_decade_match_beyond_tolerance_is_major(self):
        findings = logic.check_decade_match(
            flight_panel(), test_panel(surface_resistivity_ohm_per_square=5.0e3)
        )
        self.assertEqual([f["code"] for f in findings], ["CP-DECADE-DEVIATION"])

    def test_decade_match_at_exactly_a_factor_of_two_passes(self):
        # log10(2000) - log10(1000) evaluates a few units in the last place
        # above log10(2) in binary floating point. A test panel exactly at
        # twice the flight panel sits on the tolerance and has to read as
        # compliant, so the comparison absorbs the representation error
        # rather than the tolerance being widened.
        deviation = logic.decade_deviation(2.0e3, 1.0e3)
        self.assertGreater(deviation, logic.MAX_DECADE_DEVIATION)
        self.assertEqual(
            logic.check_decade_match(
                flight_panel(), test_panel(surface_resistivity_ohm_per_square=2.0e3)
            ),
            [],
        )

    def test_decade_match_accepts_a_tighter_programme_tolerance(self):
        findings = logic.check_decade_match(
            flight_panel(),
            test_panel(surface_resistivity_ohm_per_square=1.9e3),
            max_decades=0.05,
        )
        self.assertEqual([f["code"] for f in findings], ["CP-DECADE-DEVIATION"])

    def test_decade_match_rejects_a_non_positive_tolerance(self):
        with self.assertRaises(ValueError):
            logic.check_decade_match(flight_panel(), test_panel(), max_decades=0.0)

    def test_matching_anisotropy_is_clean(self):
        self.assertEqual(logic.check_anisotropy_match(flight_panel(), test_panel()), [])

    def test_anisotropy_far_from_flight_is_minor(self):
        findings = logic.check_anisotropy_match(
            flight_panel(), test_panel(directional_ohm_per_square=[1.2e3, 6.0e3])
        )
        self.assertEqual([f["code"] for f in findings], ["CP-ANISOTROPY"])
        self.assertEqual(findings[0]["severity"], "minor")

    def test_one_sided_directional_data_is_minor(self):
        panel = test_panel()
        del panel["directional_ohm_per_square"]
        findings = logic.check_anisotropy_match(flight_panel(), panel)
        self.assertEqual([f["code"] for f in findings], ["CP-ANISOTROPY-UNCHARACTERIZED"])

    def test_no_directional_data_anywhere_is_clean(self):
        flight = flight_panel()
        del flight["directional_ohm_per_square"]
        panel = test_panel()
        del panel["directional_ohm_per_square"]
        self.assertEqual(logic.check_anisotropy_match(flight, panel), [])

    def test_malformed_directional_data_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.check_anisotropy_match(
                flight_panel(), test_panel(directional_ohm_per_square=[1.2e3])
            )

    def test_low_panel_bond_is_clean(self):
        self.assertEqual(logic.check_panel_bonding(test_panel()), [])

    def test_high_panel_bond_is_major(self):
        findings = logic.check_panel_bonding(test_panel(bond_resistance_mohm=25.0))
        self.assertEqual([f["code"] for f in findings], ["CP-BOND-RESISTANCE"])

    def test_panel_bond_exactly_at_the_cap_passes(self):
        self.assertEqual(
            logic.check_panel_bonding(
                test_panel(bond_resistance_mohm=logic.MAX_PANEL_BOND_RESISTANCE_MOHM)
            ),
            [],
        )

    def test_unrecorded_panel_bond_is_minor(self):
        panel = test_panel()
        del panel["bond_resistance_mohm"]
        findings = logic.check_panel_bonding(panel)
        self.assertEqual([f["code"] for f in findings], ["CP-BOND-UNRECORDED"])

    def test_negative_panel_bond_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.check_panel_bonding(test_panel(bond_resistance_mohm=-1.0))

    def test_differing_probe_methods_are_minor(self):
        flight = {
            "measurement": {
                "method": "four-point",
                "voltage_v": 1.0,
                "current_a": 0.0045323601418272,
            }
        }
        panel = {
            "measurement": {
                "method": "two-probe",
                "resistance_ohm": 1000.0,
                "bar_width_mm": 100.0,
                "electrode_spacing_mm": 100.0,
            },
            "bond_resistance_mohm": 1.0,
        }
        findings = logic.check_measurement_method(flight, panel)
        self.assertEqual([f["code"] for f in findings], ["CP-METHOD-DEVIATION"])

    def test_same_probe_method_is_clean(self):
        record = {
            "method": "two-probe",
            "resistance_ohm": 1000.0,
            "bar_width_mm": 100.0,
            "electrode_spacing_mm": 100.0,
        }
        self.assertEqual(
            logic.check_measurement_method({"measurement": record}, {"measurement": record}), []
        )


class TestAssessment(unittest.TestCase):
    def test_representative_panel_is_clean(self):
        report = logic.assess_composite_ground_plane(flight_panel(), test_panel())
        self.assertTrue(report["compliant"])
        self.assertTrue(report["clean"])
        self.assertEqual(report["codes"], [])
        self.assertEqual(report["flight_regime"], "conductive")
        self.assertEqual(report["test_regime"], "conductive")
        self.assertAlmostEqual(report["decade_deviation"], math.log10(1.2), places=12)

    def test_uncharacterized_flight_panel_short_circuits_the_assessment(self):
        report = logic.assess_composite_ground_plane({"note": "not measured"}, test_panel())
        self.assertEqual(report["codes"], ["CP-FLIGHT-VALUE-MISSING"])
        self.assertFalse(report["compliant"])
        self.assertIsNone(report["flight_ohm_per_square"])
        self.assertIsNone(report["decade_deviation"])
        self.assertAlmostEqual(report["test_ohm_per_square"], 1.2e3, places=9)

    def test_insulating_test_panel_fails_regime_and_decades(self):
        report = logic.assess_composite_ground_plane(
            flight_panel(), test_panel(surface_resistivity_ohm_per_square=1.0e12)
        )
        self.assertIn("CP-REGIME-MISMATCH", report["codes"])
        self.assertIn("CP-DECADE-DEVIATION", report["codes"])
        self.assertFalse(report["compliant"])
        self.assertEqual(report["test_regime"], "insulating")

    def test_minor_only_panel_is_compliant_but_not_clean(self):
        report = logic.assess_composite_ground_plane(
            flight_panel(), test_panel(directional_ohm_per_square=[1.2e3, 6.0e3])
        )
        self.assertTrue(report["compliant"])
        self.assertFalse(report["clean"])
        self.assertEqual(report["counts"], {"major": 0, "minor": 1})

    def test_counts_match_the_finding_list(self):
        panel = test_panel(
            surface_resistivity_ohm_per_square=4.0e11,
            directional_ohm_per_square=[4.0e11, 4.0e12],
            bond_resistance_mohm=40.0,
        )
        report = logic.assess_composite_ground_plane(flight_panel(), panel)
        self.assertEqual(
            report["counts"]["major"] + report["counts"]["minor"], len(report["findings"])
        )
        for code in ("CP-REGIME-MISMATCH", "CP-DECADE-DEVIATION", "CP-BOND-RESISTANCE"):
            self.assertIn(code, report["codes"])
        self.assertFalse(report["compliant"])

    def test_assessment_rejects_a_non_mapping_panel(self):
        with self.assertRaises(ValueError):
            logic.assess_composite_ground_plane(flight_panel(), "1.2e3")

    def test_assessment_is_deterministic(self):
        self.assertEqual(
            logic.assess_composite_ground_plane(flight_panel(), test_panel()),
            logic.assess_composite_ground_plane(flight_panel(), test_panel()),
        )


if __name__ == "__main__":
    unittest.main()
