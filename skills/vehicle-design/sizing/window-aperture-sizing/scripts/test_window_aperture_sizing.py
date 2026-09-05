#!/usr/bin/env python3
"""Contract test for scripts/window_aperture_sizing_logic.py.

Exercises the window-aperture-sizing SKILL.md workflow end to end,
offline and deterministic (stdlib unittest, no network, no RNG). The
docstrings name the SKILL.md workflow steps they exercise: step 2 the
design pressure differential traverse (ISA cabin and ambient
pressures, limit differential, certification pressure factor), step 3
the clamped-circular-plate stress traverse, step 4 the pane thickness
inversion, step 5 the pane margin check, step 6 the window weight
rollup, step 7 the gauge verification pass at the limit differential.

Anchors come from the spec worked example (cabin altitude 2438.40 m,
flight altitude 12000 m, pane radius 0.15 m, acrylic density 1190
kg/m^3, designer allowable 50 MPa); module outputs must sit inside the
spec magnitude bounds. ValueErrors reject non-physical inputs.
"""

import math
import unittest

from window_aperture_sizing_logic import (
    CERT_PRESSURE_FACTOR,
    CLAMPED_PLATE_STRESS_COEF,
    design_pressure_differential,
    isa_pressure_pa,
    pane_margin,
    pane_thickness,
    plate_max_stress_clamped_circular,
    window_weight,
)

CABIN_ALT = 2438.40  # 8000 ft cabin altitude (m)
FLIGHT_ALT = 12000.0  # flight altitude (m)
RADIUS_M = 0.15  # pane radius (m)
ALLOWABLE_PA = 50.0e6  # designer-supplied allowable stress (Pa)
DENSITY = 1190.0  # acrylic pane density (kg/m^3)
T6 = 0.006  # 6 mm candidate gauge (m)
T5 = 0.005  # 5 mm candidate gauge (m)


def design_p():
    """Design differential (Pa) of the step 2 worked example traverse."""
    return design_pressure_differential(CABIN_ALT, FLIGHT_ALT)["design_differential_pa"]


class IsaPressureTests(unittest.TestCase):
    """Step 2 of the SKILL.md workflow, the ISA pressure traverse."""

    def test_isa_sea_level_and_tropopause_anchors(self):
        """Step 2 ISA anchors: sea level P0 = 101325 Pa; 11000 m = 22631.700910 Pa."""
        self.assertAlmostEqual(isa_pressure_pa(0.0), 101325.0, places=6)
        self.assertAlmostEqual(isa_pressure_pa(11000.0), 22631.700910, delta=0.5)

    def test_isa_stratosphere_12km_anchor(self):
        """Step 2 ISA anchor: 12000 m gives 19330.062329 Pa within 0.5 Pa."""
        self.assertAlmostEqual(isa_pressure_pa(12000.0), 19330.062329, delta=0.5)

    def test_isa_monotonic_and_continuous(self):
        """Step 2 traverse: pressure falls with altitude and is continuous at the tropopause."""
        low = isa_pressure_pa(500.0)
        mid = isa_pressure_pa(6000.0)
        tropo = isa_pressure_pa(11000.0)
        high = isa_pressure_pa(15000.0)
        self.assertGreater(low, mid)
        self.assertGreater(mid, tropo)
        self.assertGreater(tropo, high)
        self.assertAlmostEqual(
            isa_pressure_pa(11000.0), isa_pressure_pa(10999.999), delta=0.01
        )


class DesignDifferentialTests(unittest.TestCase):
    """Step 2 of the SKILL.md workflow, the design pressure differential."""

    def test_design_differential_worked_example_anchors(self):
        """Step 2 anchors for 2438.40 m / 12000 m, each within 1 Pa, about 0.744 bar."""
        r = design_pressure_differential(CABIN_ALT, FLIGHT_ALT)
        self.assertAlmostEqual(r["cabin_pressure_pa"], 75262.136558, delta=1.0)
        self.assertAlmostEqual(r["ambient_pressure_pa"], 19330.062329, delta=1.0)
        self.assertAlmostEqual(r["limit_differential_pa"], 55932.074230, delta=1.0)
        self.assertAlmostEqual(r["design_differential_pa"], 74389.658725, delta=1.0)
        self.assertAlmostEqual(r["design_differential_pa"] / 1e5, 0.743897, delta=1e-3)

    def test_design_differential_dict_keys(self):
        """Step 2 output dict carries exactly the documented keys."""
        r = design_pressure_differential(CABIN_ALT, FLIGHT_ALT)
        self.assertEqual(
            list(r.keys()),
            [
                "cabin_pressure_pa",
                "ambient_pressure_pa",
                "limit_differential_pa",
                "design_differential_pa",
            ],
        )

    def test_certification_pressure_factor_applied(self):
        """Step 2: design differential is the limit times the 1.33 certification factor."""
        r = design_pressure_differential(CABIN_ALT, FLIGHT_ALT)
        self.assertAlmostEqual(
            r["design_differential_pa"],
            r["limit_differential_pa"] * CERT_PRESSURE_FACTOR,
            places=9,
        )

    def test_custom_certification_factor(self):
        """Step 2: a designer certification factor scales the design differential."""
        r = design_pressure_differential(CABIN_ALT, FLIGHT_ALT, certification_factor=1.5)
        self.assertAlmostEqual(
            r["design_differential_pa"],
            r["limit_differential_pa"] * 1.5,
            places=9,
        )

    def test_higher_flight_altitude_raises_differential(self):
        """Step 2: a higher flight altitude lowers ambient pressure and lifts the limit."""
        base = design_pressure_differential(CABIN_ALT, 12000.0)
        higher = design_pressure_differential(CABIN_ALT, 15000.0)
        self.assertGreater(higher["limit_differential_pa"], base["limit_differential_pa"])

    def test_valueerror_flight_altitude_not_above_cabin(self):
        """Step 2 rejects a flight altitude below or equal to the cabin altitude."""
        with self.assertRaises(ValueError):
            design_pressure_differential(5000.0, 3000.0)
        with self.assertRaises(ValueError):
            design_pressure_differential(8000.0, 8000.0)

    def test_valueerror_altitude_out_of_isa_range(self):
        """Step 2 rejects negative and above-20000 m altitudes in the ISA traverse."""
        with self.assertRaises(ValueError):
            design_pressure_differential(-100.0, 12000.0)
        with self.assertRaises(ValueError):
            design_pressure_differential(CABIN_ALT, 21000.0)

    def test_valueerror_nonpositive_certification_factor(self):
        """Step 2 rejects a non-positive certification factor."""
        with self.assertRaises(ValueError):
            design_pressure_differential(CABIN_ALT, FLIGHT_ALT, certification_factor=0.0)


class PlateStressTests(unittest.TestCase):
    """Step 3 of the SKILL.md workflow, the clamped-circular-plate stress."""

    def test_stress_worked_example_6mm_gauge(self):
        """Step 3 anchor: 34.870153 MPa at the 6 mm gauge, within 1e-3 MPa."""
        s = plate_max_stress_clamped_circular(design_p(), RADIUS_M, T6)
        self.assertAlmostEqual(s / 1e6, 34.870153, delta=1e-3)

    def test_stress_worked_example_5mm_gauge(self):
        """Step 3 anchor: 50.213020 MPa at the 5 mm gauge, within 1e-3 MPa."""
        s = plate_max_stress_clamped_circular(design_p(), RADIUS_M, T5)
        self.assertAlmostEqual(s / 1e6, 50.213020, delta=1e-3)

    def test_stress_scaling_identities(self):
        """Step 3 identities: stress scales as p, as r squared, as 1 over t squared."""
        s = plate_max_stress_clamped_circular(74389.658725, RADIUS_M, T6)
        self.assertAlmostEqual(
            plate_max_stress_clamped_circular(2.0 * 74389.658725, RADIUS_M, T6) / s,
            2.0,
            places=12,
        )
        self.assertAlmostEqual(
            plate_max_stress_clamped_circular(74389.658725, 2.0 * RADIUS_M, T6) / s,
            4.0,
            places=12,
        )
        self.assertAlmostEqual(
            plate_max_stress_clamped_circular(74389.658725, RADIUS_M, 0.5 * T6) / s,
            4.0,
            places=12,
        )

    def test_stress_closed_form_constant(self):
        """Step 3: the closed form carries the 3/4 constant, independent of Poisson ratio."""
        s = plate_max_stress_clamped_circular(74389.658725, RADIUS_M, T6)
        expected = CLAMPED_PLATE_STRESS_COEF * 74389.658725 * (RADIUS_M / T6) ** 2
        self.assertAlmostEqual(s, expected, places=6)

    def test_clamped_edge_governs_over_center(self):
        """Step 3: at nu 0.33 the clamped edge stress exceeds the center stress."""
        p = design_p()
        edge = plate_max_stress_clamped_circular(p, RADIUS_M, T6)
        center = 3.0 * (1.0 + 0.33) * p * (RADIUS_M / T6) ** 2 / 8.0
        self.assertGreater(edge, center)

    def test_valueerror_nonpositive_stress_inputs(self):
        """Step 3 rejects non-positive pressure, radius, and gauge thickness."""
        with self.assertRaises(ValueError):
            plate_max_stress_clamped_circular(0.0, RADIUS_M, T6)
        with self.assertRaises(ValueError):
            plate_max_stress_clamped_circular(74389.658725, 0.0, T6)
        with self.assertRaises(ValueError):
            plate_max_stress_clamped_circular(74389.658725, RADIUS_M, 0.0)


class PaneThicknessTests(unittest.TestCase):
    """Step 4 of the SKILL.md workflow, the pane thickness inversion."""

    def test_pane_thickness_worked_example(self):
        """Step 4 anchor: 5.010640 mm required, within 1e-5 m, so 6 mm is the first gauge."""
        t = pane_thickness(design_p(), RADIUS_M, ALLOWABLE_PA)
        self.assertAlmostEqual(t, 0.005010640, delta=1e-5)
        self.assertLess(t, T6)

    def test_pane_thickness_round_trip(self):
        """Step 4 inversion identity: stress at the required gauge returns the allowable."""
        t = pane_thickness(design_p(), RADIUS_M, ALLOWABLE_PA)
        stress = plate_max_stress_clamped_circular(design_p(), RADIUS_M, t)
        self.assertAlmostEqual(stress / ALLOWABLE_PA, 1.0, delta=1e-6)

    def test_pane_thickness_scaling_identities(self):
        """Step 4 identities: required thickness scales as sqrt(p) and linearly with r."""
        t1 = pane_thickness(74389.658725, RADIUS_M, ALLOWABLE_PA)
        self.assertAlmostEqual(
            pane_thickness(4.0 * 74389.658725, RADIUS_M, ALLOWABLE_PA) / t1,
            2.0,
            places=12,
        )
        self.assertAlmostEqual(
            pane_thickness(74389.658725, 0.30, ALLOWABLE_PA) / t1, 2.0, places=12
        )

    def test_pane_thickness_small_radius_sweep_anchor(self):
        """Step 4 sweep anchor: a 0.10 m radius pane needs 3.340426 mm, within 1e-5 m."""
        t = pane_thickness(design_p(), 0.10, ALLOWABLE_PA)
        self.assertAlmostEqual(t, 0.003340426, delta=1e-5)

    def test_doubling_certification_factor_scales_sqrt2(self):
        """Step 4 identity: doubling the certification factor scales the gauge by sqrt(2)."""
        base = design_pressure_differential(CABIN_ALT, FLIGHT_ALT)
        doubled = design_pressure_differential(
            CABIN_ALT, FLIGHT_ALT, certification_factor=2.0 * CERT_PRESSURE_FACTOR
        )
        t_base = pane_thickness(base["design_differential_pa"], RADIUS_M, ALLOWABLE_PA)
        t_doubled = pane_thickness(
            doubled["design_differential_pa"], RADIUS_M, ALLOWABLE_PA
        )
        self.assertAlmostEqual(t_doubled / t_base, math.sqrt(2.0), places=10)

    def test_valueerror_nonpositive_thickness_inputs(self):
        """Step 4 rejects non-positive pressure, radius, and allowable inputs."""
        with self.assertRaises(ValueError):
            pane_thickness(0.0, RADIUS_M, ALLOWABLE_PA)
        with self.assertRaises(ValueError):
            pane_thickness(74389.658725, -0.15, ALLOWABLE_PA)
        with self.assertRaises(ValueError):
            pane_thickness(74389.658725, RADIUS_M, 0.0)


class PaneMarginTests(unittest.TestCase):
    """Step 5 of the SKILL.md workflow, the pane margin check."""

    def test_margin_positive_at_6mm_gauge(self):
        """Step 5 anchor: the 6 mm gauge margin is 0.433891 against 50 MPa, within 1e-4."""
        m = pane_margin(design_p(), RADIUS_M, T6, ALLOWABLE_PA)
        self.assertAlmostEqual(m, 0.433891, delta=1e-4)

    def test_margin_negative_at_5mm_gauge(self):
        """Step 5 anchor: the 5 mm gauge margin is -0.004242, the pane fails."""
        m = pane_margin(design_p(), RADIUS_M, T5, ALLOWABLE_PA)
        self.assertAlmostEqual(m, -0.004242, delta=1e-4)
        self.assertLess(m, 0.0)

    def test_first_standard_gauge_selection(self):
        """Step 5: 6 mm is the first standard gauge whose margin passes at the design differential."""
        self.assertLess(pane_margin(design_p(), RADIUS_M, T5, ALLOWABLE_PA), 0.0)
        self.assertGreater(pane_margin(design_p(), RADIUS_M, T6, ALLOWABLE_PA), 0.0)

    def test_margin_zero_at_required_thickness_and_rising(self):
        """Step 5: margin is zero at the required thickness and rises with the gauge."""
        m = pane_margin(design_p(), RADIUS_M, pane_thickness(design_p(), RADIUS_M, ALLOWABLE_PA), ALLOWABLE_PA)
        self.assertAlmostEqual(m, 0.0, places=9)
        self.assertLess(
            pane_margin(design_p(), RADIUS_M, 0.005, ALLOWABLE_PA),
            pane_margin(design_p(), RADIUS_M, 0.006, ALLOWABLE_PA),
        )

    def test_valueerror_nonpositive_margin_inputs(self):
        """Step 5 rejects non-positive pressure, radius, thickness, and allowable."""
        with self.assertRaises(ValueError):
            pane_margin(design_p(), RADIUS_M, T6, 0.0)
        with self.assertRaises(ValueError):
            pane_margin(design_p(), RADIUS_M, 0.0, ALLOWABLE_PA)
        with self.assertRaises(ValueError):
            pane_margin(0.0, RADIUS_M, T6, ALLOWABLE_PA)
        with self.assertRaises(ValueError):
            pane_margin(design_p(), 0.0, T6, ALLOWABLE_PA)


class LimitPressureGaugeTests(unittest.TestCase):
    """Step 7 of the SKILL.md workflow, the gauge verification at limit pressure."""

    def test_limit_pressure_stress_6mm_anchor(self):
        """Step 7 anchor: limit-pressure stress is 26.218160 MPa at the 6 mm gauge."""
        r = design_pressure_differential(CABIN_ALT, FLIGHT_ALT)
        s = plate_max_stress_clamped_circular(r["limit_differential_pa"], RADIUS_M, T6)
        self.assertAlmostEqual(s / 1e6, 26.218160, delta=1e-3)
        self.assertLess(s, plate_max_stress_clamped_circular(r["design_differential_pa"], RADIUS_M, T6))

    def test_limit_pressure_margin_6mm_anchor(self):
        """Step 7 anchor: limit-pressure margin is 0.907075 at the 6 mm gauge."""
        r = design_pressure_differential(CABIN_ALT, FLIGHT_ALT)
        m = pane_margin(r["limit_differential_pa"], RADIUS_M, T6, ALLOWABLE_PA)
        self.assertAlmostEqual(m, 0.907075, delta=1e-4)
        self.assertGreater(m, pane_margin(r["design_differential_pa"], RADIUS_M, T6, ALLOWABLE_PA))

    def test_thin_pane_sweep_10mm_anchor(self):
        """Step 7 sweep anchor: a 0.10 m radius pane at 10 mm runs 5.579224 MPa."""
        s = plate_max_stress_clamped_circular(design_p(), 0.10, 0.010)
        self.assertAlmostEqual(s / 1e6, 5.579224, delta=1e-3)


class WindowWeightTests(unittest.TestCase):
    """Step 6 of the SKILL.md workflow, the window weight rollup."""

    def test_window_weight_worked_example_anchors(self):
        """Step 6 anchors: 0.504697 kg per pane and 50.469686 kg over 100 windows."""
        w = window_weight(RADIUS_M, T6, DENSITY, 100)
        self.assertAlmostEqual(w["per_window_kg"], 0.504697, delta=1e-4)
        self.assertAlmostEqual(w["total_kg"], 50.469686, delta=1e-4)
        self.assertEqual(list(w.keys()), ["per_window_kg", "total_kg"])

    def test_window_weight_scaling_identities(self):
        """Step 6 identities: mass scales with count, density, and the radius squared."""
        self.assertAlmostEqual(
            window_weight(RADIUS_M, T6, DENSITY, 100)["total_kg"]
            / window_weight(RADIUS_M, T6, DENSITY, 25)["total_kg"],
            4.0,
            places=12,
        )
        self.assertAlmostEqual(
            window_weight(RADIUS_M, T6, 2380.0, 10)["total_kg"]
            / window_weight(RADIUS_M, T6, 1190.0, 10)["total_kg"],
            2.0,
            places=12,
        )
        self.assertAlmostEqual(
            window_weight(0.20, T6, DENSITY, 10)["total_kg"]
            / window_weight(0.10, T6, DENSITY, 10)["total_kg"],
            4.0,
            places=12,
        )
        w1 = window_weight(RADIUS_M, T6, DENSITY, 1)
        w100 = window_weight(RADIUS_M, T6, DENSITY, 100)
        self.assertAlmostEqual(w1["per_window_kg"], w100["per_window_kg"], places=12)

    def test_valueerror_window_weight_nonpositive_inputs(self):
        """Step 6 rejects non-positive radius, thickness, density, and a count below 1."""
        with self.assertRaises(ValueError):
            window_weight(0.0, T6, DENSITY, 10)
        with self.assertRaises(ValueError):
            window_weight(RADIUS_M, 0.0, DENSITY, 10)
        with self.assertRaises(ValueError):
            window_weight(RADIUS_M, T6, 0.0, 10)
        with self.assertRaises(ValueError):
            window_weight(RADIUS_M, T6, DENSITY, 0)
        with self.assertRaises(ValueError):
            window_weight(RADIUS_M, T6, DENSITY, -3)


class DeterminismTests(unittest.TestCase):
    """Workflow-wide check: the module is deterministic and offline."""

    def test_repeated_calls_deterministic(self):
        """Steps 2 and 3: repeated calls return identical results."""
        a = design_pressure_differential(CABIN_ALT, FLIGHT_ALT)
        b = design_pressure_differential(CABIN_ALT, FLIGHT_ALT)
        self.assertEqual(a, b)
        self.assertEqual(
            plate_max_stress_clamped_circular(design_p(), RADIUS_M, T6),
            plate_max_stress_clamped_circular(design_p(), RADIUS_M, T6),
        )


if __name__ == "__main__":
    unittest.main()
