"""Contract test for the rotorcraft-range-endurance SKILL.md workflow.

Deterministic, offline, stdlib unittest for
skills/flight-mechanics/performance/rotorcraft-range-endurance. Run from
the repo root:

    python3 skills/flight-mechanics/performance/rotorcraft-range-endurance/scripts/test_rotorcraft_range_endurance.py

The methods exercise the numbered SKILL.md workflow steps: step 2 (rotor
disk area from the radius), step 3 (hover power constant and hover power
at the takeoff weight), step 4 (the hover endurance fuel closure from
the weight-decay power integration), step 5 (fuel flow at the operating
weights), step 6 (cruise speed selection through the specific range and
the best range and best endurance speeds over the power-required curve),
step 7 (the cruise range and cruise endurance fuel closures with the
average-weight power scaling), and step 8 (the deterministic checks run
here). Covers the six-tonne worked example against the spec anchors, the
validation-list ValueErrors, the scaling identities, and run-to-run
determinism.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rotorcraft_range_endurance_logic as rre

# Worked example inputs (six-tonne class helicopter, sea level).
W0 = 60000.0            # takeoff weight, N
FUEL = 1500.0           # fuel mass, kg
RADIUS = 8.0            # rotor radius, m
RHO = 1.225             # sea-level density, kg/m^3
FM = 0.75               # figure of merit
C_SPEC = 1.0e-7         # specific fuel consumption, kg/(s W)
POWER_CURVE = [
    (40.0, 620000.0),
    (50.0, 560000.0),
    (60.0, 540000.0),
    (70.0, 555000.0),
    (80.0, 600000.0),
]                       # power-required curve at the reference weight, W


class RotorcraftRangeEnduranceContractTests(unittest.TestCase):
    """Assert the worked example, identities and ValueErrors of the module."""

    # --- Step 2: disk area from the rotor radius -------------------------

    def test_disk_area_worked_value(self):
        """Step 2 of the SKILL.md workflow, the rotor disk area traverse,
        is exercised: disk_area(8.0) returns 201.062 m2 within 0.01."""
        self.assertAlmostEqual(rre.disk_area(RADIUS), 201.062, delta=0.01)

    def test_disk_area_rejects_nonpositive_radius(self):
        """Step 2 input guard: a zero or negative rotor radius is
        non-physical and must raise ValueError."""
        for bad in (0.0, -1.0):
            with self.assertRaises(ValueError):
                rre.disk_area(bad)

    # --- Step 3: hover power constant and hover power --------------------

    def test_hover_power_constant_worked_value(self):
        """Step 3 of the SKILL.md workflow, the hover power constant k_h
        from the disk area, density and figure of merit, is exercised:
        hover_power_constant(8.0) returns 0.0600746 within 1e-5."""
        self.assertAlmostEqual(rre.hover_power_constant(RADIUS),
                               0.0600746, delta=1e-5)

    def test_hover_power_constant_rejects_bad_inputs(self):
        """Step 3 guard: non-positive density or a figure of merit outside
        (0, 1] must raise ValueError in the hover power constant."""
        with self.assertRaises(ValueError):
            rre.hover_power_constant(RADIUS, rho=0.0)
        for bad_fm in (0.0, 1.5, -0.2):
            with self.assertRaises(ValueError):
                rre.hover_power_constant(RADIUS, figure_of_merit=bad_fm)

    def test_hover_power_worked_value(self):
        """Step 3 of the SKILL.md workflow, the hover power from the
        takeoff weight through the W^1.5 power law, is exercised:
        hover_power(60000, 8.0) returns 882912 W within 10."""
        self.assertAlmostEqual(rre.hover_power(W0, RADIUS), 882912.0,
                               delta=10.0)

    def test_hover_power_rejects_nonpositive_weight(self):
        """Step 3 guard: a zero or negative rotorcraft weight cannot close
        the hover power check and must raise ValueError."""
        for bad in (0.0, -100.0):
            with self.assertRaises(ValueError):
                rre.hover_power(bad, RADIUS)

    def test_hover_power_rejects_bad_figure_of_merit(self):
        """Step 3 guard: the figure of merit input of the hover power must
        sit in (0, 1]; 0 and 1.5 both raise ValueError."""
        for bad_fm in (0.0, 1.5):
            with self.assertRaises(ValueError):
                rre.hover_power(W0, RADIUS, figure_of_merit=bad_fm)

    # --- Step 4: hover endurance fuel closure ----------------------------

    def test_hover_endurance_worked_value(self):
        """Step 4 of the SKILL.md workflow, the hover endurance weight-
        decay fuel closure over the fuel mass, is exercised:
        hover_endurance(60000, 1500, 8.0) returns 20927.3 s within 1.0
        (the spec anchor sits in the 5.5-6.1 h band)."""
        self.assertAlmostEqual(
            rre.hover_endurance(W0, FUEL, RADIUS), 20927.3, delta=1.0)

    def test_hover_endurance_zero_fuel_returns_zero(self):
        """Step 4 boundary: with no fuel mass the hover endurance fuel
        closure must return exactly 0.0 s."""
        self.assertEqual(rre.hover_endurance(W0, 0.0, RADIUS), 0.0)

    def test_hover_endurance_grows_with_fuel_mass(self):
        """Step 4 monotonicity: the hover endurance fuel closure must grow
        as the fuel mass grows at a fixed figure of merit."""
        low = rre.hover_endurance(W0, 500.0, RADIUS)
        high = rre.hover_endurance(W0, 1500.0, RADIUS)
        self.assertGreater(high, low)

    def test_hover_endurance_grows_with_figure_of_merit(self):
        """Step 4 monotonicity: the hover endurance fuel closure must grow
        as the figure of merit grows at a fixed fuel mass (a better rotor
        burns the fuel slower)."""
        low = rre.hover_endurance(W0, FUEL, RADIUS, figure_of_merit=0.60)
        high = rre.hover_endurance(W0, FUEL, RADIUS, figure_of_merit=0.85)
        self.assertGreater(high, low)

    def test_hover_endurance_rejects_zeroing_fuel_mass(self):
        """Step 4 guard: fuel mass that burns the rotorcraft to zero or
        negative weight (W1 <= 0) must raise ValueError in the hover
        endurance closure."""
        with self.assertRaises(ValueError):
            rre.hover_endurance(W0, W0 / rre.G0 + 1.0, RADIUS)

    def test_hover_endurance_rejects_negative_fuel(self):
        """Step 4 guard: a negative fuel mass is non-physical for the
        hover endurance fuel closure and must raise ValueError."""
        with self.assertRaises(ValueError):
            rre.hover_endurance(W0, -1.0, RADIUS)

    def test_hover_endurance_rejects_nonpositive_sfc(self):
        """Step 4 guard: a zero specific fuel consumption would freeze the
        weight decay and must raise ValueError in hover_endurance."""
        with self.assertRaises(ValueError):
            rre.hover_endurance(W0, FUEL, RADIUS, c_specific=0.0)

    # --- Step 5: fuel flow at the operating weights ----------------------

    def test_fuel_flow_worked_value(self):
        """Step 5 of the SKILL.md workflow, the fuel flow at the takeoff
        weight, is exercised: fuel_flow(60000, 8.0) returns
        0.0882912 kg/s within 1e-5."""
        self.assertAlmostEqual(rre.fuel_flow(W0, RADIUS), 0.0882912,
                               delta=1e-5)

    def test_fuel_flow_identity_sfc_times_hover_power(self):
        """Step 5 identity: the fuel flow must equal the specific fuel
        consumption times the step-3 hover power at the same weight."""
        self.assertAlmostEqual(rre.fuel_flow(W0, RADIUS),
                               C_SPEC * rre.hover_power(W0, RADIUS),
                               delta=1e-12)

    # --- Step 6: cruise speed selection ----------------------------------

    def test_specific_range_worked_value(self):
        """Step 6 of the SKILL.md workflow, the specific range at a cruise
        point on the power-required curve, is exercised:
        specific_range(60, 540000) returns 113.302 m per kg within 0.01."""
        self.assertAlmostEqual(rre.specific_range(60.0, 540000.0),
                               113.302, delta=0.01)

    def test_specific_range_rejects_nonphysical_inputs(self):
        """Step 6 guard: a zero cruise speed or zero power cannot define
        the specific range fuel closure and must raise ValueError."""
        with self.assertRaises(ValueError):
            rre.specific_range(0.0, 540000.0)
        with self.assertRaises(ValueError):
            rre.specific_range(60.0, 0.0)

    def test_specific_range_monotone_in_speed(self):
        """Step 6 monotonicity: at a fixed power the specific range fuel
        closure must grow with the cruise speed."""
        slow = rre.specific_range(50.0, 540000.0)
        fast = rre.specific_range(80.0, 540000.0)
        self.assertGreater(fast, slow)

    def test_best_range_speed_worked_value(self):
        """Step 6 of the SKILL.md workflow, the best range speed pick over
        the power-required curve, is exercised: the worked curve gives
        best_range_speed = 80.0 m/s."""
        self.assertEqual(rre.best_range_speed(POWER_CURVE), 80.0)

    def test_best_endurance_speed_worked_value(self):
        """Step 6 of the SKILL.md workflow, the best endurance speed pick
        over the power-required curve, is exercised: the worked curve
        gives best_endurance_speed = 60.0 m/s."""
        self.assertEqual(rre.best_endurance_speed(POWER_CURVE), 60.0)

    def test_best_speeds_reject_empty_curve(self):
        """Step 6 guard: an empty power-required curve has no speed to
        pick and must raise ValueError in both best-speed scans."""
        with self.assertRaises(ValueError):
            rre.best_range_speed([])
        with self.assertRaises(ValueError):
            rre.best_endurance_speed([])

    def test_best_speeds_reject_nonpositive_pairs(self):
        """Step 6 guard: a power-required curve pair with non-positive
        speed or power is non-physical and must raise ValueError in both
        best-speed scans."""
        for curve in ([(0.0, 540000.0)], [(60.0, 0.0)], [(-5.0, 540000.0)]):
            with self.assertRaises(ValueError):
                rre.best_range_speed(curve)
            with self.assertRaises(ValueError):
                rre.best_endurance_speed(curve)

    def test_best_range_speed_is_specific_range_argmax(self):
        """Step 6 identity: the best range speed over the power-required
        curve must equal the argmax of the step-6 specific range."""
        expected = max(POWER_CURVE,
                       key=lambda pair: rre.specific_range(pair[0], pair[1]))[0]
        self.assertEqual(rre.best_range_speed(POWER_CURVE), expected)

    def test_best_endurance_speed_is_power_argmin(self):
        """Step 6 identity: the best endurance speed over the power-
        required curve must equal the argmin of the power values."""
        expected = min(POWER_CURVE, key=lambda pair: pair[1])[0]
        self.assertEqual(rre.best_endurance_speed(POWER_CURVE), expected)

    # --- Step 7: cruise range and endurance fuel closures ----------------

    def test_cruise_range_worked_value(self):
        """Step 7 of the SKILL.md workflow, the cruise range fuel closure
        at the best range speed with the average-weight power scaling, is
        exercised: cruise_range(80, 60000, 1500, 600000, 60000) returns
        2433442 m within 100 (the 2400-2500 km band)."""
        self.assertAlmostEqual(
            rre.cruise_range(80.0, W0, FUEL, 600000.0, W0),
            2433442.0, delta=100.0)

    def test_cruise_endurance_worked_value(self):
        """Step 7 of the SKILL.md workflow, the cruise endurance fuel
        closure at the best endurance speed with the average-weight power
        scaling, is exercised: cruise_endurance(60, 60000, 1500, 540000,
        60000) returns 33797.8 s within 10 (the 9-10 h band)."""
        self.assertAlmostEqual(
            rre.cruise_endurance(60.0, W0, FUEL, 540000.0, W0),
            33797.8, delta=10.0)

    def test_cruise_range_linear_in_speed_at_fixed_power(self):
        """Step 7 scaling: at a fixed average-weight-scaled power the
        cruise range fuel closure must scale linearly with the chosen
        cruise speed."""
        base = rre.cruise_range(80.0, W0, FUEL, 600000.0, W0)
        double = rre.cruise_range(160.0, W0, FUEL, 600000.0, W0)
        self.assertAlmostEqual(double, 2.0 * base, delta=1e-6)

    def test_cruise_weight_scaling_identity_no_decay(self):
        """Step 7 identity: with no weight decay the average weight equals
        the reference weight, the (W_avg/W_ref)^1.5 factor is exactly 1,
        and the cruise range fuel closure returns the no-scaling value."""
        p_avg = 600000.0 * ((W0 + (W0 - rre.G0 * 0.0)) / 2.0 / W0) ** 1.5
        self.assertEqual(p_avg, 600000.0)
        self.assertEqual(rre.cruise_range(80.0, W0, 0.0, 600000.0, W0), 0.0)

    def test_cruise_weight_scaling_lengthens_range(self):
        """Step 7 scaling identity: the average-weight power scaling is a
        strict reduction below the reference weight, so the cruise range
        fuel closure is longer than the no-scaling estimate at the same
        reference power."""
        scaled = rre.cruise_range(80.0, W0, FUEL, 600000.0, W0)
        w1 = W0 - rre.G0 * FUEL
        no_scaling = 80.0 * (W0 - w1) / (rre.G0 * C_SPEC * 600000.0)
        self.assertGreater(scaled, no_scaling)

    def test_cruise_lower_power_point_shorter_range(self):
        """Step 7 ordering: the lower-power lower-speed cruise point
        (60 m/s, 540000 W) must close a shorter cruise range than the
        best-range point (80 m/s, 600000 W), the worked-example
        ordering behind the spec statement that the range at the lower
        reference power point is shorter."""
        best_range_closure = rre.cruise_range(80.0, W0, FUEL, 600000.0, W0)
        lower_power_closure = rre.cruise_range(60.0, W0, FUEL, 540000.0, W0)
        self.assertLess(lower_power_closure, best_range_closure)

    def test_cruise_range_falls_as_reference_power_rises(self):
        """Step 7 behaviour at a fixed cruise speed: the reference power
        sits in the denominator of the fuel closure, so raising it burns
        the fuel load faster and must shorten the cruise range."""
        low_p = rre.cruise_range(60.0, W0, FUEL, 540000.0, W0)
        high_p = rre.cruise_range(60.0, W0, FUEL, 600000.0, W0)
        self.assertGreater(low_p, high_p)

    def test_cruise_closures_reject_nonphysical_inputs(self):
        """Step 7 guards: the cruise range and cruise endurance fuel
        closures must raise ValueError for a zero cruise speed, negative
        fuel, fuel that zeroes the final weight, a zero reference power
        and a zero reference weight."""
        for fn in (rre.cruise_range, rre.cruise_endurance):
            with self.assertRaises(ValueError):
                fn(0.0, W0, FUEL, 600000.0, W0)
            with self.assertRaises(ValueError):
                fn(80.0, W0, -1.0, 600000.0, W0)
            with self.assertRaises(ValueError):
                fn(80.0, W0, W0 / rre.G0 + 1.0, 600000.0, W0)
            with self.assertRaises(ValueError):
                fn(80.0, W0, FUEL, 0.0, W0)
            with self.assertRaises(ValueError):
                fn(80.0, W0, FUEL, 600000.0, 0.0)

    # --- Step 8: determinism and module constants ------------------------

    def test_determinism_repeated_calls(self):
        """Step 8 of the SKILL.md workflow, the deterministic re-run
        check, is exercised: repeated hover endurance and cruise range
        fuel closures must return identical floats."""
        h1 = rre.hover_endurance(W0, FUEL, RADIUS)
        r1 = rre.cruise_range(80.0, W0, FUEL, 600000.0, W0)
        for _ in range(3):
            self.assertEqual(rre.hover_endurance(W0, FUEL, RADIUS), h1)
            self.assertEqual(rre.cruise_range(80.0, W0, FUEL, 600000.0, W0),
                             r1)

    def test_module_constants(self):
        """Step 8 anchor: the module constants must match the SI values
        the SKILL.md domain quick reference states."""
        self.assertEqual(rre.G0, 9.80665)
        self.assertEqual(rre.RHO_SL, 1.225)
        self.assertEqual(rre.C_SPEC_DEFAULT, 1.0e-7)
        self.assertEqual(rre.FM_DEFAULT, 0.75)


if __name__ == "__main__":
    unittest.main()
