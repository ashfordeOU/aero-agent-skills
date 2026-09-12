#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-20C clause 6.3.3 electromagnetic
radiation hazard control.

Exercises scripts/e20_electromagnetic_radiation_hazard_control_logic.py
(stdlib unittest, offline). Contract: a receptor kind maps to exactly
one hazard family and an unrecognized kind raises; the far-field
boundary is twice the squared aperture over the wavelength and the
region selection at exactly that range resolves to the far field; the
far-field density is radiated power over the sphere while the
near-field density is the aperture plateau; the personnel limit is
piecewise in frequency and continuous at both break points, and a
frequency outside the band raises; a coupling-limited category refuses
to yield an incident-density limit; coupled power is density times
pickup area times efficiency with the efficiency confined to the unit
interval; the decibel margin is ten times the base-ten logarithm of the
threshold over the coupled power and a margin exactly on the
requirement passes; a density exactly on the limit passes; and the
aggregated review is safe only when the finding list is empty.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e20_electromagnetic_radiation_hazard_control_logic as rh  # noqa: E402


def _clean_emitter():
    """X-band dish: 100 W into 30 dBi, one metre aperture."""
    return {
        "emitter_id": "TT-C-XBAND-01",
        "transmit_power_w": 100.0,
        "gain_dbi": 30.0,
        "feed_loss_db": 0.0,
        "aperture_diameter_m": 1.0,
        "frequency_hz": 8.0e9,
    }


def _small_aperture_emitter():
    """Same power and gain behind a 0.1 m aperture, so the far field
    starts well inside a metre."""
    emitter = _clean_emitter()
    emitter["emitter_id"] = "TT-C-XBAND-02"
    emitter["aperture_diameter_m"] = 0.1
    return emitter


def _personnel_receptor():
    return {
        "receptor_id": "PAD-CREW-A",
        "receptor_kind": "pad_crew",
        "distance_m": 300.0,
    }


def _ordnance_receptor():
    return {
        "receptor_id": "SEP-NUT-03",
        "receptor_kind": "pyrotechnic_separation_nut",
        "distance_m": 300.0,
        "pickup_area_m2": 0.01,
        "coupling_efficiency": 0.1,
        "threshold_power_w": 0.1,
    }


def _thruster_receptor():
    return {
        "receptor_id": "RCS-VALVE-2B",
        "receptor_kind": "monopropellant_thruster_valve",
        "distance_m": 300.0,
        "pickup_area_m2": 0.004,
        "coupling_efficiency": 0.05,
        "threshold_power_w": 0.05,
    }


class CategorizeReceptorTest(unittest.TestCase):
    def test_pad_crew_is_personnel(self):
        self.assertEqual(
            rh.categorize_radiation_receptor("pad_crew"), "personnel"
        )

    def test_eva_crew_is_personnel(self):
        self.assertEqual(
            rh.categorize_radiation_receptor("eva_crew"), "personnel"
        )

    def test_transfer_line_is_fuel(self):
        self.assertEqual(
            rh.categorize_radiation_receptor("propellant_transfer_line"),
            "fuel",
        )

    def test_initiator_is_ordnance(self):
        self.assertEqual(
            rh.categorize_radiation_receptor("electro_explosive_initiator"),
            "ordnance",
        )

    def test_latch_valve_is_thruster_actuation(self):
        self.assertEqual(
            rh.categorize_radiation_receptor("latch_valve_actuator"),
            "thruster_actuation",
        )

    def test_every_kind_lands_in_a_known_family(self):
        families = set(rh.RECEPTOR_CATEGORIES.values())
        self.assertEqual(
            families,
            rh.DENSITY_LIMITED_CATEGORIES | rh.COUPLING_LIMITED_CATEGORIES,
        )

    def test_unknown_receptor_kind_raises(self):
        with self.assertRaises(ValueError):
            rh.categorize_radiation_receptor("solar_array_string")


class EmitterTermsTest(unittest.TestCase):
    def test_wavelength_at_x_band(self):
        self.assertAlmostEqual(rh.wavelength_m(8.0e9), 0.0374740, places=6)

    def test_zero_frequency_raises(self):
        with self.assertRaises(ValueError):
            rh.wavelength_m(0.0)

    def test_eirp_applies_gain(self):
        self.assertAlmostEqual(
            rh.effective_radiated_power_w(100.0, 30.0), 100000.0, places=3
        )

    def test_eirp_applies_feed_loss(self):
        self.assertAlmostEqual(
            rh.effective_radiated_power_w(100.0, 30.0, 3.0),
            100000.0 * 10.0 ** (-0.3),
            places=3,
        )

    def test_zero_transmit_power_raises(self):
        with self.assertRaises(ValueError):
            rh.effective_radiated_power_w(0.0, 30.0)

    def test_negative_feed_loss_raises(self):
        with self.assertRaises(ValueError):
            rh.effective_radiated_power_w(100.0, 30.0, -1.0)

    def test_far_field_boundary_value(self):
        self.assertAlmostEqual(
            rh.far_field_boundary_m(1.0, 8.0e9),
            2.0 / rh.wavelength_m(8.0e9),
            places=6,
        )

    def test_boundary_scales_with_squared_aperture(self):
        single = rh.far_field_boundary_m(1.0, 8.0e9)
        double = rh.far_field_boundary_m(2.0, 8.0e9)
        self.assertAlmostEqual(double / single, 4.0, places=9)

    def test_zero_aperture_raises(self):
        with self.assertRaises(ValueError):
            rh.far_field_boundary_m(0.0, 8.0e9)


class PowerDensityTest(unittest.TestCase):
    def test_far_field_density_at_range(self):
        self.assertAlmostEqual(
            rh.far_field_power_density_w_per_m2(1.0e5, 300.0),
            1.0e5 / (4.0 * math.pi * 9.0e4),
            places=9,
        )

    def test_density_falls_with_the_square_of_range(self):
        near = rh.far_field_power_density_w_per_m2(1.0e5, 100.0)
        far = rh.far_field_power_density_w_per_m2(1.0e5, 200.0)
        self.assertAlmostEqual(near / far, 4.0, places=9)

    def test_zero_range_raises(self):
        with self.assertRaises(ValueError):
            rh.far_field_power_density_w_per_m2(1.0e5, 0.0)

    def test_zero_eirp_raises(self):
        with self.assertRaises(ValueError):
            rh.far_field_power_density_w_per_m2(0.0, 300.0)

    def test_near_field_plateau_value(self):
        self.assertAlmostEqual(
            rh.near_field_power_density_w_per_m2(100.0, 1.0),
            16.0 * 100.0 / math.pi,
            places=6,
        )

    def test_near_field_zero_aperture_raises(self):
        with self.assertRaises(ValueError):
            rh.near_field_power_density_w_per_m2(100.0, 0.0)


class RegionSelectionTest(unittest.TestCase):
    def test_far_range_uses_far_field(self):
        field = rh.power_density_at_range(_clean_emitter(), 300.0)
        self.assertEqual(field["region"], "far_field")

    def test_close_range_uses_near_field_plateau(self):
        field = rh.power_density_at_range(_clean_emitter(), 5.0)
        self.assertEqual(field["region"], "near_field")
        self.assertAlmostEqual(
            field["power_density_w_per_m2"],
            16.0 * 100.0 / math.pi,
            places=6,
        )

    def test_exactly_at_boundary_is_far_field(self):
        emitter = _clean_emitter()
        boundary = rh.far_field_boundary_m(
            emitter["aperture_diameter_m"], emitter["frequency_hz"]
        )
        field = rh.power_density_at_range(emitter, boundary)
        self.assertEqual(field["region"], "far_field")

    def test_boundary_is_reported_back(self):
        field = rh.power_density_at_range(_clean_emitter(), 300.0)
        self.assertAlmostEqual(
            field["far_field_boundary_m"], 2.0 / rh.wavelength_m(8.0e9),
            places=6,
        )

    def test_zero_range_raises_in_region_selection(self):
        with self.assertRaises(ValueError):
            rh.power_density_at_range(_clean_emitter(), 0.0)


class PersonnelLimitTest(unittest.TestCase):
    def test_low_band_is_flat(self):
        self.assertAlmostEqual(rh.personnel_limit_w_per_m2(1.0e8), 10.0,
                               places=9)

    def test_limit_is_continuous_at_the_lower_break(self):
        self.assertAlmostEqual(
            rh.personnel_limit_w_per_m2(400.0e6), 10.0, places=9
        )

    def test_resonance_band_rises_with_frequency(self):
        self.assertAlmostEqual(
            rh.personnel_limit_w_per_m2(1.0e9), 25.0, places=9
        )

    def test_limit_is_continuous_at_the_upper_break(self):
        self.assertAlmostEqual(
            rh.personnel_limit_w_per_m2(2.0e9), 50.0, places=9
        )

    def test_high_band_is_flat(self):
        self.assertAlmostEqual(
            rh.personnel_limit_w_per_m2(8.0e9), 50.0, places=9
        )

    def test_below_band_raises(self):
        with self.assertRaises(ValueError):
            rh.personnel_limit_w_per_m2(1.0e6)

    def test_above_band_raises(self):
        with self.assertRaises(ValueError):
            rh.personnel_limit_w_per_m2(1.0e12)


class HazardLimitDispatchTest(unittest.TestCase):
    def test_personnel_limit_is_frequency_dependent(self):
        self.assertAlmostEqual(
            rh.hazard_limit_w_per_m2("personnel", 1.0e9), 25.0, places=9
        )

    def test_fuel_limit_is_fixed(self):
        self.assertAlmostEqual(
            rh.hazard_limit_w_per_m2("fuel", 1.0e9),
            rh.FUEL_HAZARD_LIMIT_W_PER_M2,
            places=9,
        )

    def test_ordnance_refuses_a_density_limit(self):
        with self.assertRaises(ValueError):
            rh.hazard_limit_w_per_m2("ordnance", 1.0e9)

    def test_thruster_actuation_refuses_a_density_limit(self):
        with self.assertRaises(ValueError):
            rh.hazard_limit_w_per_m2("thruster_actuation", 1.0e9)

    def test_unknown_category_raises(self):
        with self.assertRaises(ValueError):
            rh.hazard_limit_w_per_m2("avionics", 1.0e9)


class SeparationDistanceTest(unittest.TestCase):
    def test_separation_reproduces_the_limit_density(self):
        distance = rh.minimum_safe_separation_m(1.0e5, 50.0)
        self.assertAlmostEqual(
            rh.far_field_power_density_w_per_m2(1.0e5, distance),
            50.0,
            places=9,
        )

    def test_tighter_limit_pushes_the_distance_out(self):
        self.assertGreater(
            rh.minimum_safe_separation_m(1.0e5, 10.0),
            rh.minimum_safe_separation_m(1.0e5, 50.0),
        )

    def test_zero_eirp_raises(self):
        with self.assertRaises(ValueError):
            rh.minimum_safe_separation_m(0.0, 50.0)

    def test_zero_limit_raises(self):
        with self.assertRaises(ValueError):
            rh.minimum_safe_separation_m(1.0e5, 0.0)


class CoupledPowerTest(unittest.TestCase):
    def test_coupled_power_is_the_product(self):
        self.assertAlmostEqual(
            rh.coupled_power_w(100.0, 0.01, 0.1), 0.1, places=9
        )

    def test_zero_efficiency_couples_nothing(self):
        self.assertAlmostEqual(
            rh.coupled_power_w(100.0, 0.01, 0.0), 0.0, places=9
        )

    def test_unit_efficiency_is_accepted(self):
        self.assertAlmostEqual(
            rh.coupled_power_w(100.0, 0.01, 1.0), 1.0, places=9
        )

    def test_efficiency_above_one_raises(self):
        with self.assertRaises(ValueError):
            rh.coupled_power_w(100.0, 0.01, 1.1)

    def test_negative_efficiency_raises(self):
        with self.assertRaises(ValueError):
            rh.coupled_power_w(100.0, 0.01, -0.1)

    def test_negative_pickup_area_raises(self):
        with self.assertRaises(ValueError):
            rh.coupled_power_w(100.0, -0.01, 0.1)

    def test_negative_density_raises(self):
        with self.assertRaises(ValueError):
            rh.coupled_power_w(-1.0, 0.01, 0.1)


class CouplingMarginTest(unittest.TestCase):
    def test_decade_ratio_is_ten_decibels(self):
        self.assertAlmostEqual(
            rh.coupling_margin_db(1.0, 0.1), 10.0, places=9
        )

    def test_equal_powers_give_zero_margin(self):
        self.assertAlmostEqual(
            rh.coupling_margin_db(0.1, 0.1), 0.0, places=9
        )

    def test_coupled_above_threshold_is_negative(self):
        self.assertLess(rh.coupling_margin_db(0.1, 1.0), 0.0)

    def test_zero_threshold_raises(self):
        with self.assertRaises(ValueError):
            rh.coupling_margin_db(0.0, 0.1)

    def test_zero_coupled_power_raises(self):
        with self.assertRaises(ValueError):
            rh.coupling_margin_db(0.1, 0.0)


class ReceptorFindingsTest(unittest.TestCase):
    def test_distant_crew_has_no_findings(self):
        self.assertEqual(
            rh.receptor_findings(_personnel_receptor(), _clean_emitter()), []
        )

    def test_crew_inside_the_near_field_is_reported_twice(self):
        receptor = _personnel_receptor()
        receptor["distance_m"] = 5.0
        issues = [
            f["issue"]
            for f in rh.receptor_findings(receptor, _clean_emitter())
        ]
        self.assertIn("receptor_inside_far_field_boundary", issues)
        self.assertIn("incident_density_above_limit", issues)

    def test_density_exactly_on_the_personnel_limit_passes(self):
        emitter = _small_aperture_emitter()
        eirp = rh.effective_radiated_power_w(
            emitter["transmit_power_w"], emitter["gain_dbi"],
            emitter["feed_loss_db"],
        )
        receptor = _personnel_receptor()
        receptor["distance_m"] = rh.minimum_safe_separation_m(eirp, 50.0)
        self.assertEqual(rh.receptor_findings(receptor, emitter), [])

    def test_fuel_line_uses_the_propellant_limit(self):
        receptor = {
            "receptor_id": "MMH-LINE-1",
            "receptor_kind": "propellant_transfer_line",
            "distance_m": 300.0,
        }
        self.assertEqual(rh.receptor_findings(receptor, _clean_emitter()), [])

    def test_distant_ordnance_has_no_findings(self):
        self.assertEqual(
            rh.receptor_findings(_ordnance_receptor(), _clean_emitter()), []
        )

    def test_thin_ordnance_margin_is_reported(self):
        receptor = _ordnance_receptor()
        receptor["threshold_power_w"] = 1.0e-4
        findings = rh.receptor_findings(receptor, _clean_emitter())
        self.assertEqual(len(findings), 1)
        self.assertEqual(
            findings[0]["issue"], "coupling_margin_below_requirement"
        )

    def test_ordnance_margin_exactly_on_requirement_passes(self):
        emitter = _clean_emitter()
        receptor = _ordnance_receptor()
        field = rh.power_density_at_range(emitter, receptor["distance_m"])
        coupled = rh.coupled_power_w(
            field["power_density_w_per_m2"],
            receptor["pickup_area_m2"],
            receptor["coupling_efficiency"],
        )
        receptor["threshold_power_w"] = coupled * 10.0 ** (16.5 / 10.0)
        self.assertEqual(rh.receptor_findings(receptor, emitter), [])

    def test_thruster_uses_a_stricter_default_margin(self):
        emitter = _clean_emitter()
        receptor = _thruster_receptor()
        field = rh.power_density_at_range(emitter, receptor["distance_m"])
        coupled = rh.coupled_power_w(
            field["power_density_w_per_m2"],
            receptor["pickup_area_m2"],
            receptor["coupling_efficiency"],
        )
        receptor["threshold_power_w"] = coupled * 10.0 ** (18.0 / 10.0)
        findings = rh.receptor_findings(receptor, emitter)
        self.assertEqual(len(findings), 1)
        self.assertAlmostEqual(
            findings[0]["required_margin_db"], 20.0, places=9
        )

    def test_zero_coupling_efficiency_yields_no_margin_finding(self):
        receptor = _ordnance_receptor()
        receptor["coupling_efficiency"] = 0.0
        receptor["threshold_power_w"] = 1.0e-9
        self.assertEqual(rh.receptor_findings(receptor, _clean_emitter()), [])

    def test_explicit_required_margin_overrides_the_default(self):
        receptor = _ordnance_receptor()
        self.assertEqual(
            rh.receptor_findings(receptor, _clean_emitter(), 16.5), []
        )
        self.assertEqual(
            len(rh.receptor_findings(receptor, _clean_emitter(), 60.0)), 1
        )

    def test_negative_required_margin_raises(self):
        with self.assertRaises(ValueError):
            rh.receptor_findings(
                _ordnance_receptor(), _clean_emitter(), -1.0
            )

    def test_unknown_receptor_kind_raises_in_findings(self):
        receptor = _personnel_receptor()
        receptor["receptor_kind"] = "star_tracker_baffle"
        with self.assertRaises(ValueError):
            rh.receptor_findings(receptor, _clean_emitter())


class AssessRadiationHazardTest(unittest.TestCase):
    def test_clean_scenario_is_safe(self):
        result = rh.assess_radiation_hazard(
            {
                "emitter": _clean_emitter(),
                "receptors": [
                    _personnel_receptor(),
                    _ordnance_receptor(),
                    _thruster_receptor(),
                ],
            }
        )
        self.assertTrue(result["safe"])
        self.assertEqual(result["emitter_id"], "TT-C-XBAND-01")

    def test_one_close_receptor_breaks_safety(self):
        receptor = _ordnance_receptor()
        receptor["distance_m"] = 2.0
        result = rh.assess_radiation_hazard(
            {"emitter": _clean_emitter(), "receptors": [receptor]}
        )
        self.assertFalse(result["safe"])
        self.assertGreaterEqual(len(result["findings"]), 1)

    def test_empty_receptor_list_is_vacuously_safe(self):
        result = rh.assess_radiation_hazard(
            {"emitter": _clean_emitter(), "receptors": []}
        )
        self.assertTrue(result["safe"])

    def test_per_receptor_margin_flows_through_aggregate(self):
        receptor = _ordnance_receptor()
        receptor["required_margin_db"] = 60.0
        result = rh.assess_radiation_hazard(
            {"emitter": _clean_emitter(), "receptors": [receptor]}
        )
        self.assertFalse(result["safe"])
        self.assertAlmostEqual(
            result["findings"][0]["required_margin_db"], 60.0, places=9
        )


if __name__ == "__main__":
    unittest.main()
