"""Contract test for the diagonal-tension-field-webs leaf (structures/fem).

Exercises the post-buckled diagonal tension field workflow of SKILL.md on
the rectangular shear web worked example (500 mm between end posts x 300 mm
deep x 1.2 mm thick, applied shear tau = 40 MPa, buckling stress input
tau_cr = 18 MPa). Step 1 of the SKILL.md workflow collects the web state;
step 2 runs the regime check with tension_field_ratio; step 3 takes the
tension field angle; step 4 computes the diagonal web tension stress; step 5
computes the flange and end post axial loads; step 6 computes the rivet
shear flows on the flange and end post attachments; step 7 gates the reserve
with the margin against buckling; step 8 confirms every check with this
contract test. All checks are offline and deterministic; the worked-example
anchor values are the real module outputs and lie inside the spec magnitude
bounds.
"""

import math
import unittest

import diagonal_tension_field_webs_logic as dtf

TAU = 40e6          # applied shear stress, Pa (worked example)
TAU_CR = 18e6       # elastic shear-buckling stress input, Pa
DEPTH = 0.3         # web depth between flanges, m
THICKNESS = 0.0012  # web thickness, m
ALPHA = 45.0        # classical plane-web tension field angle, degrees


class DiagonalTensionFieldWebsContractTest(unittest.TestCase):
    """Contract asserts for the diagonal-tension-field-webs leaf."""

    def test_tension_field_ratio_worked_example(self):
        """Step 2 regime check: the tension field ratio at 40 MPa over
        18 MPa is (40 - 18) / 40 = 0.55 exactly."""
        self.assertAlmostEqual(0.55, dtf.tension_field_ratio(TAU, TAU_CR),
                               delta=1e-9)

    def test_tension_field_ratio_zero_at_buckling(self):
        """Step 2 regime check: the tension field ratio is 0 at tau = tau_cr
        where the diagonal-tension reserve has not yet formed."""
        self.assertEqual(0.0, dtf.tension_field_ratio(TAU_CR, TAU_CR))

    def test_tension_field_ratio_zero_in_elastic_regime(self):
        """Step 2 regime check: below tau_cr the shear web is elastic and the
        tension field ratio stays 0.0."""
        self.assertEqual(0.0, dtf.tension_field_ratio(10e6, TAU_CR))
        self.assertEqual(0.0, dtf.tension_field_ratio(0.0, TAU_CR))

    def test_tension_field_ratio_approaches_one(self):
        """Step 2 regime check: as tau grows the tension field ratio
        approaches 1, matching (tau - tau_cr) / tau at large applied
        shear."""
        ratio_high = dtf.tension_field_ratio(1e12, TAU_CR)
        self.assertAlmostEqual((1e12 - TAU_CR) / 1e12, ratio_high,
                               delta=1e-12)
        self.assertGreater(ratio_high, dtf.tension_field_ratio(TAU, TAU_CR))
        self.assertLess(ratio_high, 1.0)

    def test_tension_field_angle_worked_example(self):
        """Step 3 of the SKILL.md workflow, the tension field angle take,
        returns the classical 45 degree plane-web value at the worked
        example."""
        self.assertEqual(ALPHA, dtf.tension_field_angle(TAU, TAU_CR))

    def test_tension_field_angle_continuity(self):
        """Step 3 tension field angle take: the classical angle is constant
        and continuous above tau_cr, from 1.01 * tau_cr to 1e6 * tau_cr."""
        self.assertEqual(ALPHA, dtf.tension_field_angle(1.01 * TAU_CR,
                                                        TAU_CR))
        self.assertEqual(ALPHA, dtf.tension_field_angle(1e6 * TAU_CR,
                                                        TAU_CR))

    def test_web_tension_stress_worked_example(self):
        """Step 4 diagonal web tension stress computation: at 45 degrees
        sigma_d = 2 * (40 - 18) MPa = 44.0 MPa at the worked example."""
        self.assertAlmostEqual(44.0e6,
                               dtf.web_tension_stress(TAU, TAU_CR, ALPHA),
                               delta=1.0)

    def test_web_tension_stress_at_38_degrees(self):
        """Step 4 diagonal web tension stress computation: the same web at a
        38 degree field gives sigma_d = 45.347 MPa, inside the spec bound of
        the anchor."""
        self.assertAlmostEqual(45.347e6,
                               dtf.web_tension_stress(TAU, TAU_CR, 38.0),
                               delta=1.0)

    def test_web_tension_stress_ideal_angle_identity(self):
        """Step 4 diagonal web tension stress computation: at the ideal
        angle the stress reduces to the closed form 2 * (tau - tau_cr)."""
        self.assertAlmostEqual(2.0 * (TAU - TAU_CR),
                               dtf.web_tension_stress(TAU, TAU_CR, ALPHA),
                               delta=1e-6)

    def test_web_tension_stress_elastic_regime_zero(self):
        """Step 4 diagonal web tension stress computation: below tau_cr the
        elastic web carries no diagonal tension, so sigma_d is 0.0."""
        self.assertEqual(0.0, dtf.web_tension_stress(10e6, TAU_CR, ALPHA))
        self.assertEqual(0.0, dtf.web_tension_stress(TAU_CR, TAU_CR, ALPHA))

    def test_web_tension_stress_angle_symmetry_identity(self):
        """Step 4 diagonal web tension stress computation: cot + tan is
        symmetric about 45 degrees, so the 30 and 60 degree fields give the
        same diagonal web tension stress."""
        self.assertAlmostEqual(
            dtf.web_tension_stress(TAU, TAU_CR, 30.0),
            dtf.web_tension_stress(TAU, TAU_CR, 60.0),
            delta=1e-3)
        self.assertGreater(
            dtf.web_tension_stress(TAU, TAU_CR, 30.0),
            dtf.web_tension_stress(TAU, TAU_CR, ALPHA))

    def test_flange_axial_load_worked_example(self):
        """Step 5 attachment axial load computation: the flange axial load at
        the worked example is 7920 N."""
        self.assertAlmostEqual(7920.0,
                               dtf.flange_axial_load(TAU, TAU_CR, ALPHA,
                                                     DEPTH, THICKNESS),
                               delta=0.01)

    def test_end_post_load_worked_example(self):
        """Step 5 attachment axial load computation: the end post axial load
        at the worked example is 7920 N."""
        self.assertAlmostEqual(7920.0,
                               dtf.end_post_load(TAU, TAU_CR, ALPHA,
                                                 DEPTH, THICKNESS),
                               delta=0.01)

    def test_attachment_loads_equal_at_ideal_angle(self):
        """Step 5 attachment axial load computation: the 45 degree symmetry
        identity holds, the flange and end post loads are equal at alpha =
        45."""
        self.assertAlmostEqual(
            dtf.flange_axial_load(TAU, TAU_CR, ALPHA, DEPTH, THICKNESS),
            dtf.end_post_load(TAU, TAU_CR, ALPHA, DEPTH, THICKNESS),
            delta=1e-6)

    def test_flange_axial_load_at_38_degrees(self):
        """Step 5 attachment axial load computation: at a 38 degree field the
        flange load grows to 10137.1 N, the spec anchor bound."""
        self.assertAlmostEqual(10137.1,
                               dtf.flange_axial_load(TAU, TAU_CR, 38.0,
                                                     DEPTH, THICKNESS),
                               delta=1.0)

    def test_end_post_load_at_38_degrees(self):
        """Step 5 attachment axial load computation: at a 38 degree field the
        end post load drops to 6187.8 N, the spec anchor bound."""
        self.assertAlmostEqual(6187.8,
                               dtf.end_post_load(TAU, TAU_CR, 38.0,
                                                 DEPTH, THICKNESS),
                               delta=1.0)

    def test_attachment_loads_elastic_regime_zero(self):
        """Step 5 attachment axial load computation: below tau_cr no diagonal
        tension is pulled into the flange or end post, both loads are
        0.0."""
        self.assertEqual(0.0, dtf.flange_axial_load(10e6, TAU_CR, ALPHA,
                                                    DEPTH, THICKNESS))
        self.assertEqual(0.0, dtf.end_post_load(10e6, TAU_CR, ALPHA,
                                                DEPTH, THICKNESS))

    def test_flange_load_monotone_in_tau(self):
        """Step 5 attachment axial load computation: the flange load at 30
        MPa is 4320 N, at 60 MPa 15120 N, and the load is monotone
        increasing in the applied shear."""
        p30 = dtf.flange_axial_load(30e6, TAU_CR, ALPHA, DEPTH, THICKNESS)
        p60 = dtf.flange_axial_load(60e6, TAU_CR, ALPHA, DEPTH, THICKNESS)
        self.assertAlmostEqual(4320.0, p30, delta=0.01)
        self.assertAlmostEqual(15120.0, p60, delta=0.01)
        self.assertLess(p30, dtf.flange_axial_load(TAU, TAU_CR, ALPHA,
                                                   DEPTH, THICKNESS))
        self.assertLess(dtf.flange_axial_load(TAU, TAU_CR, ALPHA, DEPTH,
                                              THICKNESS), p60)

    def test_rivet_shear_flow_flange_worked_example(self):
        """Step 6 rivet shear flow computation: the flange attachment flow at
        the worked example is 48000 N/m (48 N/mm)."""
        self.assertAlmostEqual(48000.0,
                               dtf.rivet_shear_flow(TAU, TAU_CR, ALPHA,
                                                    THICKNESS, "flange"),
                               delta=0.01)

    def test_rivet_shear_flow_end_post_worked_example(self):
        """Step 6 rivet shear flow computation: the end post attachment flow
        at the worked example is 48000 N/m (48 N/mm)."""
        self.assertAlmostEqual(48000.0,
                               dtf.rivet_shear_flow(TAU, TAU_CR, ALPHA,
                                                    THICKNESS, "end_post"),
                               delta=0.01)

    def test_rivet_shear_flows_equal_at_ideal_angle(self):
        """Step 6 rivet shear flow computation: at 45 degrees the flange and
        end post rivet flows coincide, the worked-example identity."""
        q_flange = dtf.rivet_shear_flow(TAU, TAU_CR, ALPHA, THICKNESS,
                                        "flange")
        q_post = dtf.rivet_shear_flow(TAU, TAU_CR, ALPHA, THICKNESS,
                                      "end_post")
        self.assertAlmostEqual(q_post, q_flange, delta=1e-6)

    def test_rivet_shear_flow_flange_elastic_regime(self):
        """Step 6 rivet shear flow computation: below tau_cr the flange flow
        is the elastic tau * t, here 10 MPa * 1.2 mm = 12000 N/m."""
        self.assertAlmostEqual(10e6 * THICKNESS,
                               dtf.rivet_shear_flow(10e6, TAU_CR, ALPHA,
                                                    THICKNESS, "flange"),
                               delta=1e-6)

    def test_rivet_shear_flow_end_post_full_applied_shear(self):
        """Step 6 rivet shear flow computation: the end post carries the full
        applied shear q = tau * t in both regimes, 48000 N/m at 40 MPa and
        12000 N/m at 10 MPa."""
        self.assertAlmostEqual(TAU * THICKNESS,
                               dtf.rivet_shear_flow(TAU, TAU_CR, ALPHA,
                                                    THICKNESS, "end_post"),
                               delta=1e-6)
        self.assertAlmostEqual(10e6 * THICKNESS,
                               dtf.rivet_shear_flow(10e6, TAU_CR, ALPHA,
                                                    THICKNESS, "end_post"),
                               delta=1e-6)

    def test_rivet_shear_flow_flange_non_ideal_angle(self):
        """Step 6 rivet shear flow computation: at a 38 degree field the
        flange flow is t * (tau_cr + (tau - tau_cr) * tan(38)), recomputed
        here from the raw formula."""
        expected = THICKNESS * (TAU_CR + (TAU - TAU_CR)
                                * math.tan(math.radians(38.0)))
        actual = dtf.rivet_shear_flow(TAU, TAU_CR, 38.0, THICKNESS, "flange")
        self.assertAlmostEqual(expected, actual, delta=1e-3)
        self.assertLess(actual, TAU * THICKNESS)

    def test_margin_against_buckling_worked_example(self):
        """Step 7 buckling margin gate: the margin against buckling at the
        worked example is tau_cr / tau = 0.45."""
        self.assertAlmostEqual(0.45, dtf.margin_against_buckling(TAU,
                                                                 TAU_CR),
                               delta=1e-9)

    def test_margin_against_buckling_at_buckling(self):
        """Step 7 buckling margin gate: the margin is 1.0 exactly at
        tau = tau_cr, the onset of the diagonal-tension regime."""
        self.assertEqual(1.0, dtf.margin_against_buckling(TAU_CR, TAU_CR))

    def test_margin_against_buckling_zero_shear(self):
        """Step 7 buckling margin gate: at zero applied shear the margin is
        defined as 0.0."""
        self.assertEqual(0.0, dtf.margin_against_buckling(0.0, TAU_CR))

    def test_margin_against_buckling_inverse_relation(self):
        """Step 7 buckling margin gate: margin * tau reconstructs tau_cr,
        with margin 0.3 at 60 MPa applied shear."""
        margin = dtf.margin_against_buckling(60e6, TAU_CR)
        self.assertAlmostEqual(0.3, margin, delta=1e-9)
        self.assertAlmostEqual(TAU_CR, margin * 60e6, delta=1e-3)

    def test_force_levels_reconstruct_excess_shear(self):
        """Step 5 attachment axial load computation: the applied shear force
        V = tau * t * d is 14400 N, the buckling shear force Vcr is 6480 N,
        and the 7920 N excess equals the flange axial load at 45 degrees."""
        v_total = TAU * THICKNESS * DEPTH
        v_cr = TAU_CR * THICKNESS * DEPTH
        self.assertAlmostEqual(14400.0, v_total, delta=0.01)
        self.assertAlmostEqual(6480.0, v_cr, delta=0.01)
        self.assertAlmostEqual(v_total - v_cr,
                               dtf.flange_axial_load(TAU, TAU_CR, ALPHA,
                                                     DEPTH, THICKNESS),
                               delta=0.01)

    def test_valueerror_negative_tau_rejected(self):
        """Steps 2 to 7 of the SKILL.md workflow reject a negative applied
        shear stress across the tension field ratio, the tension field angle
        take, the diagonal web tension stress computation, the attachment
        load computation, the rivet shear flow computation and the buckling
        margin gate."""
        for fn in (dtf.tension_field_ratio, dtf.tension_field_angle,
                   dtf.margin_against_buckling):
            with self.assertRaises(ValueError):
                fn(-1.0, TAU_CR)
        with self.assertRaises(ValueError):
            dtf.web_tension_stress(-1.0, TAU_CR, ALPHA)
        with self.assertRaises(ValueError):
            dtf.flange_axial_load(-1.0, TAU_CR, ALPHA, DEPTH, THICKNESS)
        with self.assertRaises(ValueError):
            dtf.end_post_load(-1.0, TAU_CR, ALPHA, DEPTH, THICKNESS)
        with self.assertRaises(ValueError):
            dtf.rivet_shear_flow(-1.0, TAU_CR, ALPHA, THICKNESS, "flange")

    def test_valueerror_zero_tau_cr_rejected(self):
        """Steps 2 to 7 of the workflow reject a non-positive buckling stress
        input tau_cr, which every diagonal-tension quantity divides on."""
        for fn in (dtf.tension_field_ratio, dtf.tension_field_angle,
                   dtf.margin_against_buckling):
            with self.assertRaises(ValueError):
                fn(TAU, 0.0)
        with self.assertRaises(ValueError):
            dtf.web_tension_stress(TAU, 0.0, ALPHA)
        with self.assertRaises(ValueError):
            dtf.flange_axial_load(TAU, 0.0, ALPHA, DEPTH, THICKNESS)
        with self.assertRaises(ValueError):
            dtf.rivet_shear_flow(TAU, 0.0, ALPHA, THICKNESS, "end_post")

    def test_valueerror_bad_angle_rejected(self):
        """Steps 4 to 6 of the workflow reject tension field angles outside
        the open interval (0, 90) degrees, including 0, 90, negative and
        out-of-range values."""
        for alpha in (0.0, 90.0, -10.0, 180.0, 450.0):
            with self.assertRaises(ValueError):
                dtf.web_tension_stress(TAU, TAU_CR, alpha)
            with self.assertRaises(ValueError):
                dtf.flange_axial_load(TAU, TAU_CR, alpha, DEPTH, THICKNESS)
            with self.assertRaises(ValueError):
                dtf.rivet_shear_flow(TAU, TAU_CR, alpha, THICKNESS, "flange")

    def test_valueerror_bad_geometry_rejected(self):
        """Step 5 and 6 of the workflow reject non-positive web geometry in
        the flange and end post load and rivet shear flow computations."""
        for depth in (0.0, -0.3):
            with self.assertRaises(ValueError):
                dtf.flange_axial_load(TAU, TAU_CR, ALPHA, depth, THICKNESS)
            with self.assertRaises(ValueError):
                dtf.end_post_load(TAU, TAU_CR, ALPHA, depth, THICKNESS)
        for thickness in (0.0, -0.0012):
            with self.assertRaises(ValueError):
                dtf.flange_axial_load(TAU, TAU_CR, ALPHA, DEPTH, thickness)
            with self.assertRaises(ValueError):
                dtf.rivet_shear_flow(TAU, TAU_CR, ALPHA, thickness, "flange")
            with self.assertRaises(ValueError):
                dtf.rivet_shear_flow(TAU, TAU_CR, ALPHA, thickness,
                                     "end_post")

    def test_valueerror_bad_member_rejected(self):
        """Step 6 rivet shear flow computation rejects any attachment member
        other than flange or end_post, such as a web panel member."""
        for member in ("web", "", "FLANGE", "end-post"):
            with self.assertRaises(ValueError):
                dtf.rivet_shear_flow(TAU, TAU_CR, ALPHA, THICKNESS, member)

    def test_determinism_repeated_calls_identical(self):
        """Step 8 contract test confirmation: repeated calls of every
        workflow function on the worked example are bit-for-bit identical
        (no RNG, no state)."""
        first = (dtf.tension_field_ratio(TAU, TAU_CR),
                 dtf.tension_field_angle(TAU, TAU_CR),
                 dtf.web_tension_stress(TAU, TAU_CR, ALPHA),
                 dtf.flange_axial_load(TAU, TAU_CR, ALPHA, DEPTH,
                                       THICKNESS),
                 dtf.end_post_load(TAU, TAU_CR, ALPHA, DEPTH, THICKNESS),
                 dtf.rivet_shear_flow(TAU, TAU_CR, ALPHA, THICKNESS,
                                      "flange"),
                 dtf.rivet_shear_flow(TAU, TAU_CR, ALPHA, THICKNESS,
                                      "end_post"),
                 dtf.margin_against_buckling(TAU, TAU_CR))
        for _ in range(3):
            second = (dtf.tension_field_ratio(TAU, TAU_CR),
                      dtf.tension_field_angle(TAU, TAU_CR),
                      dtf.web_tension_stress(TAU, TAU_CR, ALPHA),
                      dtf.flange_axial_load(TAU, TAU_CR, ALPHA, DEPTH,
                                            THICKNESS),
                      dtf.end_post_load(TAU, TAU_CR, ALPHA, DEPTH,
                                        THICKNESS),
                      dtf.rivet_shear_flow(TAU, TAU_CR, ALPHA, THICKNESS,
                                           "flange"),
                      dtf.rivet_shear_flow(TAU, TAU_CR, ALPHA, THICKNESS,
                                           "end_post"),
                      dtf.margin_against_buckling(TAU, TAU_CR))
            self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
