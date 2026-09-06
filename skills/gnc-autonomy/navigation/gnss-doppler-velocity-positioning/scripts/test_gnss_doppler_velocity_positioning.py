"""Contract test for gnss-doppler-velocity-positioning (gnc-autonomy/navigation).

Exercises the full SKILL.md workflow of the wave-43 leaf: step 1 (fix the
measurement set: broadcast-ephemeris element records, per-satellite carrier
delta-range-rate doppler observables in m/s and the receiver ECEF position,
supplied or seeded), step 2 (the pseudorange_position iterated least-squares
geometry seed), step 3 (Kepler propagation of satellite ECEF states to the
light-time-corrected transmit epoch through mean_to_eccentric,
kepler_state_eci and ecef_state under the linear GMST model), step 4 (the
line-of-sight unit vector and geometric range of line_of_sight), step 5 (the
range-rate prediction of predicted_range_rate, rho_dot = (v_sat - v_rec) dot
u + c*(dtr_dot - dts_dot)), step 6 (the 4x4 normal-equation solve of
solve_normal4 with the clock column carrying the minus sign of the
rearranged equation), step 7 (the iterated velocity fix of
velocity_least_squares over the per-satellite doppler residuals with the
per-axis 1-sigma precision from the covariance diagonal) and step 8 (the
read-off of the velocity fix, the recovered clock drift in m/s and s/s, the
post-fit residual RMS and the convergence state that gate the navigation
velocity output).

Facts exercised (fact terms): carrier delta range rate doppler observable,
broadcast ephemeris Kepler elements, eccentric anomaly, line of sight,
geometric range, light-time-corrected transmit epoch, receiver clock drift,
ECEF velocity, earth rotation rate, residual RMS. Procedures exercised
(procedure terms): velocity fix by iterated least squares, normal equations,
Gaussian elimination, Kepler propagation, per-axis precision from the
doppler covariance, deterministic offline checks and ValueError rejection of
non-physical inputs. Deterministic: the doppler measurements and the
pseudorange list are fixed constants of this file, no RNG anywhere.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gnss_doppler_velocity_positioning_logic as gd

DEG = math.pi / 180.0

# Worked example (wave-43 spec): demo receiver on the equator at the prime
# meridian moving due north at 250 m/s. Broadcast-ephemeris style element
# records (a in m, angles in deg here, converted below; toe 0 s; dts0 in s;
# dts_dot in s/s). Seven MEO satellites, 55.5 deg inclination, argp 0.
_SAT_SPECS = [
    ("A", 26560000.0, 0.0080, -33.5573, 56.6777, -4.200e-09, -1.700e-10),
    ("B", 26558000.0, 0.0120, 44.6470, 36.5232, 2.800e-09, 9.000e-11),
    ("C", 26562000.0, 0.0060, 104.6252, 14.4399, -1.900e-09, 2.100e-10),
    ("D", 26559000.0, 0.0150, 98.5683, -9.4352, 3.600e-09, -6.000e-11),
    ("E", 26561000.0, 0.0100, 141.4038, -36.6604, -2.500e-09, 1.300e-10),
    ("F", 26560000.0, 0.0180, 91.2561, -52.6231, 1.400e-09, -2.400e-10),
    ("G", 26557000.0, 0.0090, 17.4134, 17.9818, -3.100e-09, 5.000e-11),
]
_INC_DEG = 55.5
# Simulated carrier delta-range-rate observables y_i (m/s), column y of the
# spec worked example: geometric (v_sat - v_rec) dot u + c*(dtr_dot_true -
# dts_dot) plus the documented deterministic noise offsets.
_Y_DOPPLER = [-270.264366, 342.286009, 143.629913, -29.518775,
              84.049775, -417.444778, 56.378270]
_PR_NOISE = [-1.8, 2.3, -1.2, 3.1, 1.6, -2.7, 0.9]
REC_POS = (gd.R_EARTH, 0.0, 0.0)          # lat 0, lon 0, sea level (spherical)
V_TRUE = (0.0, 0.0, 250.0)                # 250 m/s due north at the equator
DTR0_TRUE = 1.2e-7                        # s, receiver clock bias (feeder)
DTRDOT_TRUE = 1.2e-9                      # s/s, receiver clock drift


def demo_satellites():
    """The seven element records of the worked example (angles in rad)."""
    return [{"id": sid, "a": a, "e": e, "inc": _INC_DEG * DEG,
             "raan": raan * DEG, "argp": 0.0, "m0": m0 * DEG, "toe": 0.0,
             "dts0": dts0, "dts_dot": dtsdot}
            for (sid, a, e, raan, m0, dts0, dtsdot) in _SAT_SPECS]


def transmit_states(sats, rec_pos, epoch=0.0):
    """Satellite ECEF states at the light-time-corrected transmit epoch,
    the converged geometry reference used to build the measurement lists
    (deterministic fixed-point iteration, no RNG)."""
    states = []
    for sat in sats:
        t_tx = epoch
        for _ in range(10):
            r_eci, v_eci = gd.kepler_state_eci(sat, t_tx)
            r_ecef, v_ecef = gd.ecef_state(r_eci, v_eci, t_tx)
            _, rho = gd.line_of_sight(r_ecef, rec_pos)
            t_tx = epoch - rho / gd.C_LIGHT
        r_eci, v_eci = gd.kepler_state_eci(sat, t_tx)
        r_ecef, v_ecef = gd.ecef_state(r_eci, v_eci, t_tx)
        u, rho = gd.line_of_sight(r_ecef, rec_pos)
        states.append((r_ecef, v_ecef, u, rho, t_tx))
    return states


class TestModuleConstants(unittest.TestCase):
    """Step 1 of the SKILL.md workflow, the fixed measurement and model
    context, starts from the pinned module constants."""

    def test_wgs84_constants(self):
        """The WGS-84 model constants that fix the range-rate equations."""
        self.assertEqual(gd.MU_EARTH, 3.986004418e14)
        self.assertEqual(gd.OMEGA_EARTH, 7.2921150e-5)
        self.assertEqual(gd.C_LIGHT, 299792458.0)
        self.assertEqual(gd.R_EARTH, 6378137.0)

    def test_model_parameters(self):
        """The deterministic model parameters: GMST reference, ephemeris
        window and Kepler solver controls."""
        self.assertEqual(gd.THETA_G0, 1.1)
        self.assertEqual(gd.EPHEMERIS_WINDOW, 7200.0)
        self.assertEqual(gd.NEWTON_TOL, 1e-14)
        self.assertEqual(gd.NEWTON_MAX, 60)


class TestKeplerSolvers(unittest.TestCase):
    """Step 3 of the SKILL.md workflow, the Kepler propagation to the
    light-time-corrected transmit epoch, is exercised here."""

    def test_mean_to_eccentric_kepler_identity(self):
        """E - e sin E == M for the recovered eccentric anomaly across the
        eccentricity range of the broadcast records."""
        for M in (0.0, 0.3, 1.0, 2.5, 3.141592653589793, 4.2, 5.9):
            for e in (0.0, 0.006, 0.012, 0.018, 0.25, 0.6, 0.9):
                E = gd.mean_to_eccentric(M, e)
                self.assertTrue(abs(E - e * math.sin(E) - M) < 1e-12)

    def test_mean_to_eccentric_circular_limit(self):
        """e = 0 makes the eccentric anomaly equal the mean anomaly."""
        for M in (0.0, 0.7, 1.9, 4.4):
            self.assertEqual(gd.mean_to_eccentric(M, 0.0), M)

    def test_mean_to_eccentric_value_errors(self):
        """e = 1.0, negative e and non-finite arguments raise ValueError."""
        for e in (1.0, -0.1, 1.5):
            with self.assertRaises(ValueError):
                gd.mean_to_eccentric(0.5, e)
        with self.assertRaises(ValueError):
            gd.mean_to_eccentric(float("nan"), 0.1)
        with self.assertRaises(ValueError):
            gd.mean_to_eccentric(0.5, float("inf"))

    def test_kepler_state_eci_circular_orbit_sanity(self):
        """A circular record returns an ECI radius equal to a and an ECI
        speed equal to the two-body circular speed sqrt(MU/a)."""
        sat = {"id": "X", "a": 2.656e7, "e": 0.0, "inc": 0.5, "raan": 0.3,
               "argp": 0.1, "m0": 1.2, "toe": 0.0, "dts0": 0.0, "dts_dot": 0.0}
        pos, vel = gd.kepler_state_eci(sat, 100.0)
        r_mag = math.sqrt(sum(x * x for x in pos))
        v_mag = math.sqrt(sum(x * x for x in vel))
        self.assertTrue(abs(r_mag - 2.656e7) < 1e-3)
        self.assertTrue(abs(v_mag - math.sqrt(gd.MU_EARTH / 2.656e7)) < 1e-6)

    def test_kepler_state_eci_time_advance(self):
        """Advancing the epoch by the orbital period returns a state whose
        mean anomaly closes the full circle of the element record."""
        # Low orbit keeps the full period inside the 7200 s ephemeris window
        sat = {"id": "L", "a": 7.5e6, "e": 0.005, "inc": 0.9, "raan": 1.2,
               "argp": 0.4, "m0": 0.7, "toe": 0.0, "dts0": 0.0, "dts_dot": 0.0}
        n = math.sqrt(gd.MU_EARTH / sat["a"] ** 3)
        period = 2.0 * math.pi / n
        self.assertTrue(period < gd.EPHEMERIS_WINDOW)
        p0, v0 = gd.kepler_state_eci(sat, 0.0)
        p1, v1 = gd.kepler_state_eci(sat, period)
        for k in range(3):
            self.assertTrue(abs(p0[k] - p1[k]) < 1e-3)
            self.assertTrue(abs(v0[k] - v1[k]) < 1e-6)

    def test_kepler_state_eci_rejects_bad_elements(self):
        """ValueError rejection of every non-physical element input of the
        spec validation list (e outside [0,1), a <= 0, missing keys)."""
        sats = demo_satellites()
        bad_e1 = dict(sats[0], e=1.0)
        with self.assertRaises(ValueError):
            gd.kepler_state_eci(bad_e1, 0.0)
        bad_e2 = dict(sats[0], e=-0.05)
        with self.assertRaises(ValueError):
            gd.kepler_state_eci(bad_e2, 0.0)
        bad_a = dict(sats[0], a=-1.0)
        with self.assertRaises(ValueError):
            gd.kepler_state_eci(bad_a, 0.0)
        with self.assertRaises(ValueError):
            gd.kepler_state_eci({}, 0.0)
        bad_key = dict(sats[0])
        del bad_key["m0"]
        with self.assertRaises(ValueError):
            gd.kepler_state_eci(bad_key, 0.0)

    def test_kepler_state_eci_rejects_epoch(self):
        """Non-finite epochs and epochs outside the 7200 s broadcast window
        raise ValueError."""
        sat = demo_satellites()[0]
        with self.assertRaises(ValueError):
            gd.kepler_state_eci(sat, 8000.0)
        with self.assertRaises(ValueError):
            gd.kepler_state_eci(sat, -8000.0)
        with self.assertRaises(ValueError):
            gd.kepler_state_eci(sat, float("nan"))
        with self.assertRaises(ValueError):
            gd.kepler_state_eci(dict(sat, a=float("inf")), 0.0)


class TestFrameAndGeometry(unittest.TestCase):
    """Steps 3 and 4 of the SKILL.md workflow, the ECEF frame rotation and
    the line-of-sight geometry of the doppler residuals."""

    def test_ecef_state_rotation_preserves_length(self):
        """The linear GMST rotation preserves the ECI radius while the ECEF
        velocity subtracts the omega x r earth-rotation term."""
        sat = demo_satellites()[3]
        r_eci, v_eci = gd.kepler_state_eci(sat, 123.4)
        r_ecef, v_ecef = gd.ecef_state(r_eci, v_eci, 123.4)
        r_eci_mag = math.sqrt(sum(x * x for x in r_eci))
        r_ecef_mag = math.sqrt(sum(x * x for x in r_ecef))
        self.assertTrue(abs(r_eci_mag - r_ecef_mag) < 1e-6)
        v_eci_mag = math.sqrt(sum(x * x for x in v_eci))
        v_ecef_mag = math.sqrt(sum(x * x for x in v_ecef))
        # ECEF speed lies below the ECI speed by the projected earth rotation
        self.assertTrue(v_ecef_mag < v_eci_mag)

    def test_ecef_state_earth_rotation_rate(self):
        """A stationary ECI state picks up the full omega x r ECEF speed,
        the earth-rotation subtraction of step 3 (v_ecef = -omega x r)."""
        r = (gd.R_EARTH, 0.0, 0.0)
        r_ecef, v_ecef = gd.ecef_state(r, (0.0, 0.0, 0.0), 0.0)
        theta = gd.THETA_G0
        # R3(-theta) on the +x ECI axis
        self.assertTrue(abs(r_ecef[0] - gd.R_EARTH * math.cos(theta)) < 1e-3)
        self.assertTrue(abs(r_ecef[1] + gd.R_EARTH * math.sin(theta)) < 1e-3)
        spin = gd.OMEGA_EARTH * gd.R_EARTH
        v_mag = math.sqrt(sum(x * x for x in v_ecef))
        self.assertTrue(abs(v_mag - spin) < 1e-6)
        self.assertTrue(abs(v_ecef[2]) < 1e-6)
        # v_ecef = -(omega x r_ecef): opposite the eastward rotation term
        wxr = (-gd.OMEGA_EARTH * r_ecef[1], gd.OMEGA_EARTH * r_ecef[0], 0.0)
        for k in range(3):
            self.assertTrue(abs(v_ecef[k] + wxr[k]) < 1e-6)

    def test_ecef_state_value_errors(self):
        """Malformed or non-finite ECI states raise ValueError."""
        with self.assertRaises(ValueError):
            gd.ecef_state((1.0, 2.0), (0.0, 0.0, 0.0), 0.0)
        with self.assertRaises(ValueError):
            gd.ecef_state((1.0, float("nan"), 3.0), (0.0, 0.0, 0.0), 0.0)
        with self.assertRaises(ValueError):
            gd.ecef_state((1.0, 2.0, 3.0), (0.0, 0.0, float("inf")), 0.0)

    def test_line_of_sight_unit_and_range(self):
        """line_of_sight returns a unit vector and a range equal to the
        geometric distance, the step-4 geometry of the residual rows."""
        sat_pos = (2.0e7, 1.0e7, 5.0e6)
        u, rho = gd.line_of_sight(sat_pos, REC_POS)
        u_mag = math.sqrt(sum(x * x for x in u))
        self.assertTrue(abs(u_mag - 1.0) < 1e-15)
        r_true = math.sqrt(sum((sat_pos[k] - REC_POS[k]) ** 2 for k in range(3)))
        self.assertTrue(abs(rho - r_true) < 1e-6)
        self.assertTrue(u[0] > 0.0)

    def test_line_of_sight_rejects_coincident(self):
        """A satellite coincident with the receiver (range below 1 m) raises
        ValueError."""
        with self.assertRaises(ValueError):
            gd.line_of_sight(REC_POS, REC_POS)
        with self.assertRaises(ValueError):
            gd.line_of_sight((REC_POS[0] + 0.5, REC_POS[1], REC_POS[2]), REC_POS)


class TestRangeRateModel(unittest.TestCase):
    """Step 5 of the SKILL.md workflow, the range-rate prediction
    rho_dot = (v_sat - v_rec) dot u + c*(dtr_dot - dts_dot)."""

    def test_predicted_range_rate_formula(self):
        """The predicted range rate matches the manual evaluation of the
        claim-form equation, including the c-scaled net clock drift."""
        sat_vel = (100.0, -200.0, 3000.0)
        rec_vel = (0.0, 0.0, 250.0)
        u = (0.5, 0.3, math.sqrt(1.0 - 0.25 - 0.09))
        dts_dot, dtr_dot = -1.7e-10, 1.2e-9
        pred = gd.predicted_range_rate(sat_vel, rec_vel, u, dts_dot, dtr_dot)
        manual = sum((sat_vel[k] - rec_vel[k]) * u[k] for k in range(3))
        manual += gd.C_LIGHT * (dtr_dot - dts_dot)
        self.assertEqual(pred, manual)

    def test_predicted_range_rate_clock_scaling(self):
        """The clock terms enter through c*(dtr_dot - dts_dot): a zero
        relative velocity leaves exactly the scaled drift difference."""
        u = (1.0, 0.0, 0.0)
        pred = gd.predicted_range_rate((10.0, 0.0, 0.0), (10.0, 0.0, 0.0),
                                       u, 1.0e-10, 3.0e-10)
        self.assertTrue(abs(pred - gd.C_LIGHT * 2.0e-10) < 1e-12)

    def test_predicted_range_rate_value_errors(self):
        """Non-finite velocities, line-of-sight or drift inputs raise
        ValueError."""
        u = (1.0, 0.0, 0.0)
        with self.assertRaises(ValueError):
            gd.predicted_range_rate((float("nan"), 0.0, 0.0), (0.0, 0.0, 0.0),
                                    u, 0.0, 0.0)
        with self.assertRaises(ValueError):
            gd.predicted_range_rate((1.0, 0.0, 0.0), (0.0, 0.0, 0.0),
                                    u, float("inf"), 0.0)


class TestNormalSolver(unittest.TestCase):
    """Step 6 of the SKILL.md workflow, the 4x4 normal-equation solve with
    the clock column carrying the minus sign of the rearranged equation."""

    def test_solve_normal4_known_system(self):
        """A known 4x4 system solves to its exact right answer."""
        rows = ((2.0, 1.0, 0.0, 0.0), (1.0, 3.0, 1.0, 0.0),
                (0.0, 1.0, 4.0, 1.0), (0.0, 0.0, 1.0, 5.0))
        rhs = (5.0, 10.0, 15.0, 20.0)
        x = gd.solve_normal4(rows, rhs)
        for r in range(4):
            back = sum(rows[r][c] * x[c] for c in range(4))
            self.assertTrue(abs(back - rhs[r]) < 1e-9)

    def test_solve_normal4_row_identity(self):
        """Row identity of the rearranged equation: with the geometry row
        [u, -1.0] and state (vx, vy, vz, c*dtr_dot), row dot x =
        u dot v_rec - c*dtr_dot by construction, so the clock column carries
        the minus sign."""
        u = (0.6, 0.4, math.sqrt(1.0 - 0.36 - 0.16))
        v = (1.5, -2.5, 3.5)
        cdtr = 0.3455
        row = (u[0], u[1], u[2], -1.0)
        state = (v[0], v[1], v[2], cdtr)
        row_dot = sum(row[k] * state[k] for k in range(4))
        manual = sum(u[k] * v[k] for k in range(3)) - cdtr
        self.assertEqual(row_dot, manual)

    def test_solve_normal4_singular_value_error(self):
        """A singular 4x4 normal matrix raises ValueError."""
        sing = ((1.0, 2.0, 3.0, 4.0), (2.0, 4.0, 6.0, 8.0),
                (1.0, 1.0, 1.0, 1.0), (1.0, 0.0, 0.0, 1.0))
        with self.assertRaises(ValueError):
            gd.solve_normal4(sing, (1.0, 1.0, 1.0, 1.0))

    def test_solve_normal4_shape_and_finite_value_errors(self):
        """Wrong shapes and non-finite systems raise ValueError."""
        with self.assertRaises(ValueError):
            gd.solve_normal4(((1.0, 0.0, 0.0, 0.0), (0.0, 1.0, 0.0, 0.0),
                              (0.0, 0.0, 1.0, 0.0)), (1.0, 1.0, 1.0, 1.0))
        with self.assertRaises(ValueError):
            gd.solve_normal4(((1.0, 0.0, 0.0, 0.0), (0.0, 1.0, 0.0, 0.0),
                              (0.0, 0.0, 1.0, 0.0), (0.0, 0.0, 0.0, 1.0)),
                             (1.0, 1.0, 1.0))
        bad = ((1.0, 0.0, 0.0, 0.0), (0.0, float("nan"), 0.0, 0.0),
               (0.0, 0.0, 1.0, 0.0), (0.0, 0.0, 0.0, 1.0))
        with self.assertRaises(ValueError):
            gd.solve_normal4(bad, (1.0, 1.0, 1.0, 1.0))


class TestVelocityFixWorkedExample(unittest.TestCase):
    """Step 7 of the SKILL.md workflow, the iterated least-squares velocity
    fix on the worked example, receiver position supplied."""

    def setUp(self):
        self.sats = demo_satellites()
        self.fix = gd.velocity_least_squares(self.sats, list(_Y_DOPPLER),
                                             REC_POS, epoch=0.0)

    def test_recovered_velocity_bounds(self):
        """The 250 m/s north motion is recovered within 0.10 m/s on every
        axis (anchor -0.023031, -0.027232, -0.029766 per-axis error)."""
        err = [self.fix["velocity"][k] - V_TRUE[k] for k in range(3)]
        for k in range(3):
            self.assertTrue(abs(err[k]) < 0.10, "axis %d error %.6f" % (k, err[k]))
        err3 = math.sqrt(sum(e * e for e in err))
        self.assertTrue(err3 < 0.15)
        self.assertTrue(abs(err3 - 0.046455) < 1e-3)

    def test_recovered_velocity_close_to_anchor(self):
        """The recovered velocity sits within 1e-3 m/s of the spec anchor
        (-0.023031, -0.027232, 249.970234) m/s."""
        anchor = (-0.023031, -0.027232, 249.970234)
        for k in range(3):
            self.assertTrue(abs(self.fix["velocity"][k] - anchor[k]) < 1e-3)

    def test_clock_drift_recovery(self):
        """The recovered clock drift lies within 0.05 m/s of the true
        0.359751 m/s (anchor error -0.014250 m/s), the broadcast dts_dot
        terms absorbed by the 4th unknown."""
        self.assertTrue(abs(self.fix["clock_drift_mps"] - gd.C_LIGHT * DTRDOT_TRUE) < 0.05)
        self.assertTrue(abs(self.fix["clock_drift_mps"] - 0.359751) < 0.05)

    def test_clock_drift_scaling_identity(self):
        """clock_drift_mps = C_LIGHT * clock_drift_sps: the m/s value is the
        same float divided by C_LIGHT, so sps == mps/C exactly."""
        self.assertEqual(self.fix["clock_drift_sps"],
                         self.fix["clock_drift_mps"] / gd.C_LIGHT)
        self.assertTrue(abs(self.fix["clock_drift_mps"] -
                            gd.C_LIGHT * self.fix["clock_drift_sps"]) < 1e-9)

    def test_residual_rms_and_sigma0(self):
        """Post-fit residual RMS below 0.05 m/s (anchor 0.023142) and sigma0
        from n - 4 = 3 degrees of freedom (anchor 0.035350)."""
        self.assertTrue(self.fix["residual_rms"] < 0.05)
        self.assertTrue(abs(self.fix["residual_rms"] - 0.023142) < 1e-3)
        self.assertTrue(abs(self.fix["sigma0"] - 0.035350) < 1e-3)
        self.assertEqual(self.fix["num_satellites"], 7)

    def test_convergence_state(self):
        """The fix converges in at most 8 passes with converged True
        (anchor: 4 iterations)."""
        self.assertTrue(self.fix["converged"])
        self.assertTrue(self.fix["iterations"] <= 8)
        self.assertEqual(self.fix["iterations"], 4)

    def test_residual_consistency(self):
        """The returned residuals sit in the measurement-noise band and their
        RMS is consistent with the reported residual RMS (step-8 read-off:
        residual_rms = sqrt(mean(residuals^2)))."""
        resid = self.fix["residuals"]
        self.assertEqual(len(resid), 7)
        for r in resid:
            self.assertTrue(math.isfinite(r))
            self.assertTrue(abs(r) < 0.1, "residual %.6f m/s" % r)
        n = len(resid)
        rms = math.sqrt(sum(r * r for r in resid) / n)
        self.assertAlmostEqual(rms, self.fix["residual_rms"], delta=1e-12)


class TestPrecisionOutputs(unittest.TestCase):
    """Step 8 of the SKILL.md workflow, the per-axis 1-sigma precision from
    the doppler covariance and the clock drift sigma."""

    def setUp(self):
        self.sats = demo_satellites()
        self.fix = gd.velocity_least_squares(self.sats, list(_Y_DOPPLER),
                                             REC_POS, epoch=0.0)

    def test_precision_identity(self):
        """per_axis_sigma_mps = sigma0 * sqrt(covariance_diag) on the three
        velocity axes and for the clock term; covariance_diag is the diagonal
        of the converged (H^T H)^-1 normal matrix."""
        cd = self.fix["covariance_diag"]
        self.assertEqual(len(cd), 4)
        for k in range(3):
            expect = self.fix["sigma0"] * math.sqrt(cd[k])
            self.assertTrue(abs(self.fix["per_axis_sigma_mps"][k] - expect) < 1e-12)
        expect_c = self.fix["sigma0"] * math.sqrt(cd[3])
        self.assertTrue(abs(self.fix["clock_drift_sigma_mps"] - expect_c) < 1e-12)

    def test_per_axis_precision_anchor(self):
        """The per-axis 1-sigma precision holds the anchor values
        (0.061974, 0.024222, 0.026807) m/s within 1e-3; the radial (x)
        axis is the weakest, as expected for a horizon-confined geometry."""
        anchor = (0.061974, 0.024222, 0.026807)
        for k in range(3):
            self.assertTrue(abs(self.fix["per_axis_sigma_mps"][k] - anchor[k]) < 1e-3)
        self.assertTrue(abs(self.fix["clock_drift_sigma_mps"] - 0.035651) < 1e-3)
        self.assertTrue(self.fix["per_axis_sigma_mps"][0] >
                        self.fix["per_axis_sigma_mps"][1])

    def test_covariance_diag_positive(self):
        """The converged covariance diagonal is strictly positive on every
        axis."""
        for k in range(4):
            self.assertTrue(self.fix["covariance_diag"][k] > 0.0)


class TestNoiselessIdentity(unittest.TestCase):
    """The noiseless exact-recovery identity of the linearized system:
    with zero doppler noise the LS recovers the true velocity to float
    noise (step 7 of the SKILL.md workflow, closed-form cross-check)."""

    def _noiseless_measurements(self):
        sats = demo_satellites()
        states = transmit_states(sats, REC_POS)
        out = []
        for i, sat in enumerate(sats):
            _, v_ecef, u, _, _ = states[i]
            geo = sum((v_ecef[k] - V_TRUE[k]) * u[k] for k in range(3))
            clk = gd.C_LIGHT * (DTRDOT_TRUE - sat["dts_dot"])
            out.append(geo + clk)
        return out

    def test_noiseless_exact_recovery(self):
        """Zero-noise doppler observables recover (0, 0, 250) m/s with a
        3-D error below 1e-6 m/s per axis (anchor 1.649e-13)."""
        fix = gd.velocity_least_squares(demo_satellites(),
                                        self._noiseless_measurements(),
                                        REC_POS, epoch=0.0)
        for k in range(3):
            self.assertTrue(abs(fix["velocity"][k] - V_TRUE[k]) < 1e-6)
        err3 = math.sqrt(sum((fix["velocity"][k] - V_TRUE[k]) ** 2 for k in range(3)))
        self.assertTrue(err3 < 1e-6)
        self.assertTrue(fix["residual_rms"] < 1e-6)
        self.assertTrue(fix["converged"])
        self.assertTrue(fix["iterations"] <= 8)


class TestPseudorangeFeederArm(unittest.TestCase):
    """Step 2 of the SKILL.md workflow, the internal pseudorange_position
    geometry seed that supplies the receiver position when none is provided
    (never a reported output of this leaf)."""

    def setUp(self):
        self.sats = demo_satellites()
        states = transmit_states(self.sats, REC_POS)
        self.pseudo = []
        for i, sat in enumerate(self.sats):
            _, _, _, rho, _ = states[i]
            self.pseudo.append(rho + gd.C_LIGHT * (DTR0_TRUE - sat["dts0"])
                               + _PR_NOISE[i])
        self.sat_positions = [states[i][0] for i in range(7)]
        self.feed = gd.pseudorange_position(self.sat_positions, self.pseudo)

    def test_feeder_position_within_bounds(self):
        """The feeder converges to a position within 5 m of the truth
        (anchor 3-D error 2.532 m) and reports a plausible residual RMS."""
        perr = [self.feed["position"][k] - REC_POS[k] for k in range(3)]
        err3 = math.sqrt(sum(e * e for e in perr))
        self.assertTrue(err3 < 5.0)
        self.assertTrue(abs(err3 - 2.532) < 0.5)
        self.assertTrue(1.0 < self.feed["residual_rms"] < 2.5)
        self.assertTrue(self.feed["converged"])
        self.assertTrue(self.feed["iterations"] <= 8)

    def test_feeder_position_velocity_insensitivity(self):
        """The velocity fix fed with the pseudorange-seed position differs
        from the supplied-truth-position run by less than 1e-3 m/s per axis
        (anchor 1.537e-04): the fix is insensitive to the position-seed
        error at the sub-mm/s level."""
        fix_supplied = gd.velocity_least_squares(self.sats, list(_Y_DOPPLER),
                                                 REC_POS, epoch=0.0)
        fix_seeded = gd.velocity_least_squares(self.sats, list(_Y_DOPPLER),
                                               self.feed["position"], epoch=0.0)
        for k in range(3):
            dv = abs(fix_seeded["velocity"][k] - fix_supplied["velocity"][k])
            self.assertTrue(dv < 1e-3, "axis %d dv %.3e" % (k, dv))

    def test_feeder_value_errors(self):
        """Fewer than 4 satellites, length mismatch and non-finite inputs
        raise ValueError in the position feeder."""
        with self.assertRaises(ValueError):
            gd.pseudorange_position(self.sat_positions[:3], self.pseudo[:3])
        with self.assertRaises(ValueError):
            gd.pseudorange_position(self.sat_positions, self.pseudo[:-1])
        bad = [(float("nan"), 0.0, 0.0)] + self.sat_positions[1:]
        with self.assertRaises(ValueError):
            gd.pseudorange_position(bad, self.pseudo)


class TestConstellationSanity(unittest.TestCase):
    """Step 3 of the SKILL.md workflow, the propagated demo constellation:
    ECEF speeds, elevations and the light-time correction scale."""

    def setUp(self):
        self.sats = demo_satellites()
        self.states = transmit_states(self.sats, REC_POS)

    def test_ecef_speed_band(self):
        """Each satellite ECEF speed lies between 2500 and 3500 m/s (anchor
        range 2926-3245), below the ECI two-body speed of the record."""
        for i, sat in enumerate(self.sats):
            v_ecef = self.states[i][1]
            v_mag = math.sqrt(sum(x * x for x in v_ecef))
            self.assertTrue(2500.0 < v_mag < 3500.0)
            _, v_eci = gd.kepler_state_eci(sat, self.states[i][4])
            v_eci_mag = math.sqrt(sum(x * x for x in v_eci))
            self.assertTrue(v_mag < v_eci_mag)

    def test_elevation_above_horizon(self):
        """Every satellite sits above the local horizon (elevation above 5
        deg; anchor 10.7 to 50.8 deg)."""
        up = (1.0, 0.0, 0.0)  # local vertical at lat 0 lon 0
        for i in range(7):
            u = self.states[i][2]
            el = math.degrees(math.asin(max(-1.0, min(1.0,
                                                      sum(u[k] * up[k] for k in range(3))))))
            self.assertTrue(el > 5.0, "satellite %s elevation %.3f" % (self.sats[i]["id"], el))

    def test_light_time_correction_scale(self):
        """The light-time transmit-epoch offset stays below 0.1 s (about
        0.07-0.08 s for the MEO constellation), the scale of the about
        300 m along-track propagation."""
        for i, sat in enumerate(self.sats):
            self.assertTrue(abs(self.states[i][4]) < 0.1)
            self.assertTrue(abs(self.states[i][4]) > 0.05)


class TestValueErrorsAndDeterminism(unittest.TestCase):
    """Step 7 of the SKILL.md workflow: ValueError rejection of every
    non-physical input in the spec validation list, and module determinism."""

    def setUp(self):
        self.sats = demo_satellites()
        self.dopp = list(_Y_DOPPLER)

    def test_velocity_ls_rejects_few_satellites(self):
        """Fewer than 4 satellites cannot form the 4-unknown system."""
        with self.assertRaises(ValueError):
            gd.velocity_least_squares(self.sats[:3], self.dopp[:3], REC_POS)

    def test_velocity_ls_rejects_length_mismatch(self):
        """A doppler list that does not match the satellite list raises."""
        with self.assertRaises(ValueError):
            gd.velocity_least_squares(self.sats, self.dopp[:-1], REC_POS)

    def test_velocity_ls_rejects_non_finite(self):
        """Non-finite receiver position, doppler, epoch, clock seed and
        satellite elements raise ValueError."""
        with self.assertRaises(ValueError):
            gd.velocity_least_squares(self.sats, self.dopp,
                                      (float("nan"), 0.0, 0.0))
        with self.assertRaises(ValueError):
            gd.velocity_least_squares(self.sats, [float("inf")] + self.dopp[1:],
                                      REC_POS)
        with self.assertRaises(ValueError):
            gd.velocity_least_squares(self.sats, self.dopp, REC_POS,
                                      epoch=float("nan"))
        with self.assertRaises(ValueError):
            gd.velocity_least_squares(self.sats, self.dopp, REC_POS,
                                      dtr_dot_seed=float("inf"))

    def test_velocity_ls_rejects_control_parameters(self):
        """iters = 0 and non-positive tol raise ValueError."""
        with self.assertRaises(ValueError):
            gd.velocity_least_squares(self.sats, self.dopp, REC_POS, iters=0)
        with self.assertRaises(ValueError):
            gd.velocity_least_squares(self.sats, self.dopp, REC_POS, tol=0.0)
        with self.assertRaises(ValueError):
            gd.velocity_least_squares(self.sats, self.dopp, REC_POS, tol=-1e-9)

    def test_four_satellite_sigma0_fallback(self):
        """With exactly 4 satellites sigma0 falls back to the supplied
        doppler_sigma (n - 4 = 0 residual degrees of freedom)."""
        fix = gd.velocity_least_squares(self.sats[:4], self.dopp[:4], REC_POS,
                                        doppler_sigma=0.05)
        self.assertEqual(fix["num_satellites"], 4)
        self.assertEqual(fix["sigma0"], 0.05)
        self.assertTrue(fix["converged"])

    def test_bad_satellite_record_propagates(self):
        """A bad satellite record inside the velocity LS propagates the
        ValueError of the element validation."""
        bad = list(self.sats)
        bad[2] = dict(bad[2], e=1.0)
        with self.assertRaises(ValueError):
            gd.velocity_least_squares(bad, self.dopp, REC_POS)

    def test_determinism(self):
        """Two runs on the identical inputs return identical outputs (no RNG
        anywhere in the module)."""
        f1 = gd.velocity_least_squares(self.sats, self.dopp, REC_POS)
        f2 = gd.velocity_least_squares(self.sats, self.dopp, REC_POS)
        self.assertEqual(f1["velocity"], f2["velocity"])
        self.assertEqual(f1["clock_drift_mps"], f2["clock_drift_mps"])
        self.assertEqual(f1["per_axis_sigma_mps"], f2["per_axis_sigma_mps"])
        self.assertEqual(f1["residuals"], f2["residuals"])
        self.assertEqual(f1["iterations"], f2["iterations"])

    def test_module_pure_stdlib_no_rng(self):
        """The logic module imports nothing beyond math and contains no RNG
        calls, keeping the offline contract deterministic."""
        import ast
        src_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "gnss_doppler_velocity_positioning_logic.py")
        with open(src_path, "r") as fh:
            src = fh.read()
        tree = ast.parse(src)
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
        self.assertEqual(imports, ["math"], "imports: %s" % imports)
        for token in ("random", "numpy", "np.random", "secrets", "os.urandom"):
            self.assertNotIn(token, src)


if __name__ == "__main__":
    unittest.main()
