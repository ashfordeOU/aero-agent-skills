"""Contract test for the vmu-determination leaf
(flight-test-operations/envelope).

Exercises the SKILL.md workflow end to end: step 1 fixes the
reference conditions (rotation limit angle, reference takeoff weight
and flap), step 2 fixes the test-day atmosphere with the ISA density
ratio, step 3 corrects each takeoff-rotation-run liftoff speed to the
reference conditions, step 4 classifies each rotation run against the
certified rotation-limit-speed, step 5 reduces the corrected runs to
the minimum-unstick-speed Vmu verdict with the no-unstick and
premature-unstick bracket consistency check, step 6 checks the
certification margins against the 1.08 Vmu liftoff constraint and the
1.10 Vs1 stall floor, and step 7 gates the V1/VR schedule. The
unstick-certification verdict and the FAR/CS 25.107(b) summary method
anchors below are the real prep outputs of the spec anchor script.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from vmu_determination_logic import (
    KT2MS, EXP, corrected_run_speed, flap_normalized_speed,
    isa_sigma, liftoff_margin_108, rotation_run_class,
    scheduling_gate, tas_to_cas, vmu_verdict,
    weight_corrected_speed,
)

# Worked example reference conditions (step 1 of the SKILL.md workflow).
W_REF = 79000.0          # kg, reference takeoff weight
THETA_LIM = 11.0         # deg, certified tail-strike rotation limit
FLAP_REF = 15.0          # deg, reference takeoff flap
CL_0 = 1.10              # rotation-limit lift coefficient intercept
CL_PER_DEG = 0.020       # rotation-limit lift coefficient slope


def worked_runs():
    """The five worked takeoff-rotation runs from the spec (steps 2-5
    of the SKILL.md workflow: warm-day 600 m test, +12 K deviation)."""
    return [
        {"id": "1", "speed": 60.8, "weight": 77500.0, "flap": 15.0,
         "theta": 11.4, "unstuck": True, "h_p": 600.0, "dt_isa": 12.0},
        {"id": "2", "speed": 62.9, "weight": 79000.0, "flap": 15.0,
         "theta": 9.8, "unstuck": True, "h_p": 600.0, "dt_isa": 12.0},
        {"id": "3", "speed": 59.6, "weight": 79000.0, "flap": 15.0,
         "theta": 11.0, "unstuck": False, "h_p": 600.0, "dt_isa": 12.0},
        {"id": "4", "speed": 64.8, "weight": 78500.0, "flap": 15.0,
         "theta": 11.2, "unstuck": True, "h_p": 600.0, "dt_isa": 12.0,
         "tas_input": True},
        {"id": "5", "speed": 60.2, "weight": 76500.0, "flap": 15.0,
         "theta": 11.3, "unstuck": True, "h_p": 600.0, "dt_isa": 12.0},
    ]


class TestIsaSigma(unittest.TestCase):
    """Step 2 of the SKILL.md workflow, the test-day atmosphere
    reduction, is exercised by these methods."""

    def test_standard_day_anchors(self):
        """Step 2 standard-day anchors: isa_sigma(0, 0) is 1.0 exactly
        at sea level and the 600 m standard-day ratio is 0.943654, the
        sigma reference every speed correction scales from."""
        self.assertAlmostEqual(isa_sigma(0.0, 0.0), 1.0, delta=1e-12)
        self.assertAlmostEqual(isa_sigma(600.0, 0.0), 0.943654, delta=1e-5)

    def test_warm_day_600m_anchor(self):
        """Step 2 warm-day anchor: sigma at 600 m with +12 K is
        0.905430, its square root 0.951541 (the TAS to CAS factor),
        and the warm-day value sits below the standard-day value and
        below 1, about 5% less dense than sea level standard."""
        self.assertAlmostEqual(isa_sigma(600.0, 12.0), 0.905430, delta=1e-5)
        self.assertAlmostEqual(
            math.sqrt(isa_sigma(600.0, 12.0)), 0.951541, delta=1e-5)
        self.assertLess(isa_sigma(600.0, 12.0), isa_sigma(600.0, 0.0))
        self.assertLess(isa_sigma(600.0, 0.0), 1.0)

    def test_out_of_band_altitude_raises(self):
        """Step 2 rejection coverage: isa_sigma raises ValueError for
        pressure altitudes outside the single-layer band and for a
        non-positive ambient temperature."""
        with self.assertRaises(ValueError):
            isa_sigma(-1.0, 0.0)
        with self.assertRaises(ValueError):
            isa_sigma(12000.0, 0.0)
        with self.assertRaises(ValueError):
            isa_sigma(11000.0, -400.0)


class TestTasToCas(unittest.TestCase):
    """Step 2 of the SKILL.md workflow, the true to calibrated
    airspeed leg of the standard-condition corrections, is exercised
    by these methods."""

    def test_warm_day_tas_anchor(self):
        """Step 2 anchor: tas_to_cas(64.8, 600, 12) is 61.659846 m/s on
        the warm-day 600 m test point, and the same call at sea level
        standard conditions returns the input unchanged."""
        self.assertAlmostEqual(
            tas_to_cas(64.8, 600.0, 12.0), 61.659846, delta=1e-3)
        for v in (40.0, 61.659846, 100.0):
            self.assertAlmostEqual(
                tas_to_cas(v, 0.0, 0.0), v, delta=1e-12)

    def test_nonpositive_tas_raises(self):
        """Step 2 rejection: a zero true airspeed is non-physical and
        raises ValueError."""
        with self.assertRaises(ValueError):
            tas_to_cas(0.0, 600.0, 12.0)


class TestWeightCorrection(unittest.TestCase):
    """Step 3 of the SKILL.md workflow, the weight correction of each
    takeoff-rotation-run liftoff speed, is exercised by these
    methods."""

    def test_weight_correction_anchors(self):
        """Step 3 weight correction anchors: the 77500 kg run at
        60.8 m/s corrects to 61.385567 m/s and the 76500 kg run at
        60.2 m/s to 61.175752 m/s at the 79000 kg reference takeoff
        weight, the sqrt(w_ref/w_test) factor pulling the heavy-run
        speeds up about 1%."""
        self.assertAlmostEqual(
            weight_corrected_speed(60.8, 77500.0, W_REF),
            61.385567, delta=1e-3)
        self.assertAlmostEqual(
            weight_corrected_speed(60.2, 76500.0, W_REF),
            61.175752, delta=1e-3)

    def test_sqrt_scaling_and_degeneracy(self):
        """Step 3 closed-form identity: weight_corrected_speed(v, w,
        4*w) is exactly 2*v (real anchor 120.000000 from 60.0), and a
        same-weight call returns the input unchanged."""
        self.assertAlmostEqual(
            weight_corrected_speed(60.0, 1234.0, 4.0 * 1234.0),
            120.0, delta=1e-9)
        self.assertAlmostEqual(
            weight_corrected_speed(61.4, W_REF, W_REF), 61.4, delta=1e-12)

    def test_zero_weight_raises(self):
        """Step 3 rejection: non-positive test or reference weights are
        non-physical and raise ValueError."""
        with self.assertRaises(ValueError):
            weight_corrected_speed(60.8, 0.0, W_REF)
        with self.assertRaises(ValueError):
            weight_corrected_speed(60.8, 77500.0, 0.0)


class TestFlapNormalization(unittest.TestCase):
    """Step 3 of the SKILL.md workflow, the flap configuration
    normalization through the rotation-limit lift coefficient
    CL(f) = cl_0 + cl_per_deg*f, is exercised by these methods."""

    def test_ten_to_fifteen_anchor(self):
        """Step 3 flap normalization anchor: a speed of 62.9 m/s at
        10 deg flap normalizes to 60.611957 m/s at the 15 deg
        reference takeoff flap (CL 1.300 to 1.400), the extra flap
        lift lowering the unstick speed by about 3.6%, and a
        same-flap call returns the input unchanged."""
        v = flap_normalized_speed(62.9, 10.0, FLAP_REF, CL_0, CL_PER_DEG)
        self.assertAlmostEqual(v, 60.611957, delta=1e-3)
        self.assertLess(v, 62.9)
        self.assertAlmostEqual(
            flap_normalized_speed(61.4, 15.0, 15.0, CL_0, CL_PER_DEG),
            61.4, delta=1e-12)

    def test_round_trip_exact(self):
        """Step 3 round trip: normalizing 10 to 15 deg and back
        recovers the input 62.9 within 1e-9."""
        v = flap_normalized_speed(
            flap_normalized_speed(62.9, 10.0, 15.0, CL_0, CL_PER_DEG),
            15.0, 10.0, CL_0, CL_PER_DEG)
        self.assertAlmostEqual(v, 62.9, delta=1e-9)

    def test_nonphysical_inputs_raise(self):
        """Step 3 rejection: a negative flap setting, a zero cl_0 and
        a negative cl_per_deg are non-physical and raise ValueError."""
        with self.assertRaises(ValueError):
            flap_normalized_speed(62.9, -1.0, 15.0, CL_0, CL_PER_DEG)
        with self.assertRaises(ValueError):
            flap_normalized_speed(62.9, 10.0, 15.0, 0.0, CL_PER_DEG)
        with self.assertRaises(ValueError):
            flap_normalized_speed(62.9, 10.0, 15.0, CL_0, -0.01)


class TestCorrectedRunSpeed(unittest.TestCase):
    """Step 3 of the SKILL.md workflow, the full reduction chain of one
    measured takeoff-rotation-run liftoff speed, is exercised by these
    methods."""

    def test_tas_run_anchor(self):
        """Step 3 anchor: the 78500 kg run 4 at 64.8 m/s true airspeed
        on the warm-day 600 m point corrects to 61.855904 m/s at the
        reference conditions, equal to the manual chain
        weight_corrected_speed(tas_to_cas(v, h, dt), w, w_ref) within
        1e-9 when the flap factor is 1.0."""
        v = corrected_run_speed(64.8, 78500.0, W_REF, 15.0, FLAP_REF,
                                CL_0, CL_PER_DEG, 600.0, 12.0,
                                tas_input=True)
        self.assertAlmostEqual(v, 61.855904, delta=1e-3)
        manual = weight_corrected_speed(
            tas_to_cas(64.8, 600.0, 12.0), 78500.0, W_REF)
        self.assertAlmostEqual(v, manual, delta=1e-9)

    def test_cas_noop_identity(self):
        """Step 3 degeneracy: a CAS run at the reference weight and
        flap passes through the reduction chain unchanged."""
        v = corrected_run_speed(61.4, W_REF, W_REF, 15.0, FLAP_REF,
                                CL_0, CL_PER_DEG, 600.0, 12.0,
                                tas_input=False)
        self.assertAlmostEqual(v, 61.4, delta=1e-12)

    def test_zero_measured_speed_raises(self):
        """Step 3 rejection: a zero measured liftoff speed on the CAS
        path is non-physical and raises ValueError."""
        with self.assertRaises(ValueError):
            corrected_run_speed(0.0, 77500.0, W_REF, 15.0, FLAP_REF,
                                CL_0, CL_PER_DEG, 600.0, 12.0)


class TestRotationRunClass(unittest.TestCase):
    """Step 4 of the SKILL.md workflow, the geometric classification of
    each rotation run against the certified rotation-limit-speed
    boundary, is exercised by these methods."""

    def test_class_strings_and_boundary(self):
        """Step 4 class strings: a run unstuck at or beyond the 11.0
        deg rotation limit is the Vmu-qualifying 'limit-unstick' class
        (boundary included: 11.0 vs 11.0), an unstuck run below the
        limit is 'premature-unstick', and a run that reached the limit
        without liftoff is 'no-unstick' at any theta."""
        self.assertEqual(rotation_run_class(11.4, True, THETA_LIM),
                         "limit-unstick")
        self.assertEqual(rotation_run_class(THETA_LIM, True, THETA_LIM),
                         "limit-unstick")
        self.assertEqual(rotation_run_class(9.8, True, THETA_LIM),
                         "premature-unstick")
        self.assertEqual(rotation_run_class(11.0, False, THETA_LIM),
                         "no-unstick")
        self.assertEqual(rotation_run_class(5.0, False, THETA_LIM),
                         "no-unstick")

    def test_nonphysical_angles_raise(self):
        """Step 4 rejection: a non-positive rotation limit angle and a
        negative unstick pitch angle are non-physical and raise
        ValueError."""
        with self.assertRaises(ValueError):
            rotation_run_class(11.4, True, 0.0)
        with self.assertRaises(ValueError):
            rotation_run_class(-1.0, True, THETA_LIM)


class TestVmuVerdict(unittest.TestCase):
    """Step 5 of the SKILL.md workflow, the reduction of the corrected
    takeoff rotation runs to the minimum-unstick-speed Vmu verdict with
    the bracket consistency check, is exercised by these methods."""

    def test_worked_data_verdict(self):
        """Step 5 verdict anchor: the worked five-run set gives
        vmu_cas 61.175752 m/s (run 5 exactly, the minimum of the three
        limit-unstick corrected speeds 61.385567, 61.855904,
        61.175752) and vmu_knots 118.916149 KCAS with
        n_qualifying 3."""
        ver = vmu_verdict(worked_runs(), THETA_LIM, W_REF, FLAP_REF,
                          CL_0, CL_PER_DEG)
        self.assertAlmostEqual(ver["vmu_cas"], 61.175752, delta=1e-3)
        self.assertAlmostEqual(ver["vmu_knots"], 118.916149, delta=0.01)
        self.assertEqual(ver["n_qualifying"], 3)
        run5 = [r for r in ver["runs"] if r["id"] == "5"][0]
        self.assertAlmostEqual(ver["vmu_cas"], run5["corrected"], delta=1e-9)

    def test_corrected_run_table(self):
        """Step 5 corrected run table anchor: the per-run corrected
        speeds match the spec table within 1e-3 and carry the classes
        assigned by the step 4 rotation-limit classification."""
        ver = vmu_verdict(worked_runs(), THETA_LIM, W_REF, FLAP_REF,
                          CL_0, CL_PER_DEG)
        expected = {"1": (61.385567, "limit-unstick"),
                    "2": (62.900000, "premature-unstick"),
                    "3": (59.600000, "no-unstick"),
                    "4": (61.855904, "limit-unstick"),
                    "5": (61.175752, "limit-unstick")}
        self.assertEqual(len(ver["runs"]), 5)
        for r in ver["runs"]:
            self.assertAlmostEqual(r["corrected"], expected[r["id"]][0],
                                   delta=1e-3)
            self.assertEqual(r["class"], expected[r["id"]][1])

    def test_bracket_consistency_ok(self):
        """Step 5 bracket consistency check anchor: bracket_ok is True
        with v_no_unstick_max 59.6 below the verdict and
        v_premature_min 62.9 at or above it, so the
        unstick-certification is bracketed by real run evidence: the
        airplane failed to unstick at 59.6 m/s and had unstuck
        prematurely by 62.9 m/s."""
        ver = vmu_verdict(worked_runs(), THETA_LIM, W_REF, FLAP_REF,
                          CL_0, CL_PER_DEG)
        self.assertTrue(ver["bracket_ok"])
        self.assertAlmostEqual(ver["v_no_unstick_max"], 59.6, delta=1e-9)
        self.assertAlmostEqual(ver["v_premature_min"], 62.9, delta=1e-9)
        self.assertLess(ver["v_no_unstick_max"], ver["vmu_cas"])
        self.assertLessEqual(ver["vmu_cas"], ver["v_premature_min"])

    def test_single_sided_brackets_allowed(self):
        """Step 5 bracket logic: removing the premature-unstick run
        keeps bracket_ok True, and removing the no-unstick run also
        keeps it True (single-sided brackets are allowed)."""
        runs = worked_runs()
        self.assertTrue(vmu_verdict(
            [r for r in runs if r["id"] != "2"], THETA_LIM, W_REF,
            FLAP_REF, CL_0, CL_PER_DEG)["bracket_ok"])
        self.assertTrue(vmu_verdict(
            [r for r in runs if r["id"] != "3"], THETA_LIM, W_REF,
            FLAP_REF, CL_0, CL_PER_DEG)["bracket_ok"])

    def test_knots_relation_and_determinism(self):
        """Step 5 unit conversion and determinism: vmu_knots times
        KT2MS recovers vmu_cas within 1e-6 (KT2MS = 1852/3600 appears
        only to quote the verdict in knots), and two reductions of the
        same run set give identical verdict values."""
        a = vmu_verdict(worked_runs(), THETA_LIM, W_REF, FLAP_REF,
                        CL_0, CL_PER_DEG)
        b = vmu_verdict(worked_runs(), THETA_LIM, W_REF, FLAP_REF,
                        CL_0, CL_PER_DEG)
        self.assertAlmostEqual(a["vmu_knots"] * KT2MS, a["vmu_cas"],
                               delta=1e-6)
        self.assertEqual(a["vmu_cas"], b["vmu_cas"])
        self.assertEqual(a["bracket_ok"], b["bracket_ok"])

    def test_undefined_verdict_raises(self):
        """Step 5 rejection: an empty run list and a run list whose
        only run is premature-unstick (no limit-unstick run) cannot
        define a minimum-unstick-speed and raise ValueError."""
        with self.assertRaises(ValueError):
            vmu_verdict([], THETA_LIM, W_REF, FLAP_REF, CL_0, CL_PER_DEG)
        only_premature = [{"id": "2", "speed": 62.9, "weight": 79000.0,
                           "flap": 15.0, "theta": 9.8, "unstuck": True,
                           "h_p": 600.0, "dt_isa": 12.0}]
        with self.assertRaises(ValueError):
            vmu_verdict(only_premature, THETA_LIM, W_REF, FLAP_REF,
                        CL_0, CL_PER_DEG)


class TestCertificationMargins(unittest.TestCase):
    """Step 6 of the SKILL.md workflow, the certification margins
    against the 1.08 Vmu liftoff constraint and the 1.10 Vs1 rotation
    stall floor, is exercised by these methods."""

    def test_liftoff_margin_anchor(self):
        """Step 6 liftoff margin anchor: on vmu 61.175752 and the
        scheduled liftoff 66.4 m/s, required_108 is 66.069813 m/s
        (exactly 1.08*Vmu), the margin 0.330187 m/s and the ratio
        1.085397, met True; the met flag flips to False when the
        liftoff speed drops to 66.0 m/s below the constraint."""
        lm = liftoff_margin_108(61.175752, 66.4)
        self.assertAlmostEqual(lm["required_108"], 66.069813, delta=1e-3)
        self.assertAlmostEqual(lm["required_108"], 1.08 * 61.175752,
                               delta=1e-9)
        self.assertAlmostEqual(lm["margin_mps"], 0.330187, delta=1e-3)
        self.assertAlmostEqual(lm["ratio_vlof_over_vmu"], 1.085397,
                               delta=1e-5)
        self.assertTrue(lm["met"])
        self.assertFalse(liftoff_margin_108(61.175752, 66.0)["met"])

    def test_stall_proximity(self):
        """Step 6 stall proximity: the worked vmu/vs1 ratio 1.054754
        sits below the 1.10 threshold that keeps the stall guard
        relevant for the V1/VR scheduling."""
        self.assertAlmostEqual(61.175752 / 58.0, 1.054754, delta=1e-5)
        self.assertLess(61.175752 / 58.0, 1.10)

    def test_zero_speed_raises(self):
        """Step 6 rejection: a zero Vmu or liftoff speed raises
        ValueError."""
        with self.assertRaises(ValueError):
            liftoff_margin_108(0.0, 66.4)
        with self.assertRaises(ValueError):
            liftoff_margin_108(61.175752, 0.0)


class TestSchedulingGate(unittest.TestCase):
    """Step 7 of the SKILL.md workflow, the V1/VR scheduling gate
    against the Vmu verdict and the stall floor, is exercised by these
    methods."""

    def test_vmu_gated_verdict(self):
        """Step 7 verdict anchor: with vr 63.9 the stall floor
        (63.8 m/s) is met but the 1.08 Vmu gate (66.069813 m/s) is
        not, so the verdict is 'vmu-gated' and vr_required equals
        1.08*Vmu, forcing the rotation speed up 2.17 m/s."""
        sg = scheduling_gate(61.175752, 63.9, 58.0)
        self.assertFalse(sg["vmu_gate_met"])
        self.assertTrue(sg["stall_floor_met"])
        self.assertAlmostEqual(sg["req_vr_vmu_108"], 66.069813, delta=1e-3)
        self.assertAlmostEqual(sg["req_vr_stall_110"], 63.8, delta=1e-9)
        self.assertAlmostEqual(sg["vr_required"], 66.069813, delta=1e-3)
        self.assertEqual(sg["verdict"], "vmu-gated")

    def test_ok_and_dual_verdicts(self):
        """Step 7 verdict transitions: with vr 67.0 both the 1.08 Vmu
        gate and the 1.10 Vs1 stall floor are cleared and the verdict
        is 'ok'; with vr 63.0 and vs1 58.0 neither floor is met and
        the verdict is 'dual-gated' with vr_required 1.08*Vmu."""
        ok = scheduling_gate(61.175752, 67.0, 58.0)
        self.assertTrue(ok["vmu_gate_met"])
        self.assertTrue(ok["stall_floor_met"])
        self.assertEqual(ok["verdict"], "ok")
        dual = scheduling_gate(61.175752, 63.0, 58.0)
        self.assertFalse(dual["vmu_gate_met"])
        self.assertFalse(dual["stall_floor_met"])
        self.assertEqual(dual["verdict"], "dual-gated")
        self.assertAlmostEqual(dual["vr_required"], 66.069813, delta=1e-3)

    def test_remaining_verdict_branches(self):
        """Step 7 remaining branches: when the Vmu gate clears but the
        stall floor does not the verdict is 'stall-gated' with
        vr_required 1.10*Vs1, and without a Vs1 input only the 1.08
        Vmu floor applies ('vmu-gated' at vr 65.0, 'ok' at vr 67.0)."""
        stall = scheduling_gate(61.175752, 66.5, 63.0)
        self.assertTrue(stall["vmu_gate_met"])
        self.assertFalse(stall["stall_floor_met"])
        self.assertEqual(stall["verdict"], "stall-gated")
        self.assertAlmostEqual(stall["vr_required"], 69.3, delta=1e-9)
        no_vs1 = scheduling_gate(61.175752, 65.0)
        self.assertFalse(no_vs1["vmu_gate_met"])
        self.assertIsNone(no_vs1["stall_floor_met"])
        self.assertIsNone(no_vs1["req_vr_stall_110"])
        self.assertAlmostEqual(no_vs1["vr_required"], 66.069813, delta=1e-3)
        self.assertEqual(no_vs1["verdict"], "vmu-gated")
        self.assertEqual(scheduling_gate(61.175752, 67.0)["verdict"], "ok")

    def test_zero_speed_raises(self):
        """Step 7 rejection: zero scheduled speeds and a zero Vs1 input
        raise ValueError (this leaf only checks a supplied schedule,
        never deriving Vr from Vs1)."""
        with self.assertRaises(ValueError):
            scheduling_gate(0.0, 63.9, 58.0)
        with self.assertRaises(ValueError):
            scheduling_gate(61.175752, 0.0, 58.0)
        with self.assertRaises(ValueError):
            scheduling_gate(61.175752, 63.9, 0.0)


class TestModuleDiscipline(unittest.TestCase):
    """Module-level discipline checks for the vmu-determination
    logic."""

    def test_module_constants(self):
        """Discipline: the ISA pressure exponent is about 5.2559 and
        KT2MS is exactly 1852/3600 (0.514444444444 m/s per knot)."""
        self.assertAlmostEqual(EXP, 5.2559, delta=1e-3)
        self.assertAlmostEqual(KT2MS, 0.514444444444, delta=1e-12)

    def test_no_heavy_imports(self):
        """Discipline: the logic module imports only the stdlib math
        module (no numpy, no scipy, no pandas in the process)."""
        import sys as _sys
        import vmu_determination_logic as mod
        heavy = [n for n in ("numpy", "scipy", "pandas")
                 if n in _sys.modules]
        self.assertEqual(heavy, [])
        self.assertTrue(hasattr(mod, "math"))


if __name__ == "__main__":
    unittest.main()
