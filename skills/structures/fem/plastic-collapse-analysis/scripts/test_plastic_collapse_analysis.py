"""Contract test for the plastic-collapse-analysis leaf (structures/fem).

Exercises the full SKILL.md workflow of rigid-perfectly-plastic
collapse analysis: step 1 (section reserves: plastic section modulus,
elastic section modulus, shape factor), step 2 (yield capacity: fully
plastic moment and first-yield moment), step 3 (plastic hinge
mechanisms and collapse loads of single-span beams by the kinematic
theorem), step 4 (static theorem cross-check on the collapse-state
moment diagram), step 5 (elastic first-yield context loads and the
collapse-to-yield ratios), step 6 (portal sway mechanism collapse
loads) and step 7 (collapse load factor and ultimate margin verdicts
in the FAR 25.303 context). All numeric asserts are tolerance-based
(math.isclose, rel_tol) with no exact equality on computed aggregates;
the worked-example values are the real outputs of the module. Offline,
deterministic, stdlib unittest only, under 20 seconds.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import plastic_collapse_analysis_logic as pc

# Worked-example constants (spec): sigma_y = 250 MPa, sections 50x100 mm
# rectangle, 100 mm circle, 400x200x12x8 mm I-beam.
SIGMA_Y = 250e6
RECT = (0.05, 0.1)
CIRC = (0.1,)
IBEAM = (0.4, 0.2, 0.012, 0.008)
MP_RECT = 31250.0        # N m, fully plastic moment of the rectangle
MP_IBEAM = 303488.0      # N m, fully plastic moment of the I-beam
L_BEAM = 3.0             # m span, one central point load
H_PORTAL = 4.0           # m column height, top lateral load


def _assert_rel(test, actual, expected, rel_tol, msg=None):
    """Order-safe relative assert: math.isclose with rel_tol only."""
    ok = math.isclose(actual, expected, rel_tol=rel_tol, abs_tol=0.0)
    test.assertTrue(
        ok, "%r vs expected %r (rel %g)%s"
        % (actual, expected, rel_tol, (" | " + msg) if msg else ""))


def _rectangular_moment(x, load, span, left_fraction, end_moment=0.0):
    """Equilibrium bending moment M(x) of a central-loaded beam.

    left_fraction is the share of the load carried by the left support
    reaction in the collapse state (1/2 for the simply supported and
    fixed-fixed beams, 2/3 for the propped cantilever whose fixed end
    reaction is 4*Mp/L against 2*Mp/L at the pin); end_moment is the
    hogging moment carried at x = 0 (zero for the pinned end of the
    simply supported beam, Mp at the fixed ends).
    """
    half = span / 2.0
    r_left = left_fraction * load
    if x <= half:
        return -end_moment + r_left * x
    return -end_moment + r_left * x - load * (x - half)


class PlasticCollapseAnalysisTest(unittest.TestCase):

    # --- step 1 of the SKILL.md workflow: the section-reserve pass,
    # plastic section modulus Zp about the equal-area axis ----------

    def test_rectangle_plastic_section_modulus_closed_form(self):
        """Rectangle Zp = b*h**2/4 = 0.000125 m^3 (125 cm^3)."""
        zp = pc.plastic_section_modulus("rectangle", *RECT)
        _assert_rel(self, zp, 0.000125, 1e-9)
        _assert_rel(self, zp, RECT[0] * RECT[1] ** 2 / 4.0, 1e-15)

    def test_circle_plastic_section_modulus_closed_form(self):
        """Circle Zp = d**3/6 = 0.000166666666667 m^3 (166.7 cm^3)."""
        zp = pc.plastic_section_modulus("circle", *CIRC)
        _assert_rel(self, zp, 0.000166666666667, 1e-9)
        _assert_rel(self, zp, CIRC[0] ** 3 / 6.0, 1e-15)

    def test_ibeam_plastic_section_modulus_closed_form(self):
        """I-beam Zp = b*t_f*(d - t_f) + t_w*(d - 2*t_f)**2/4 (PNA web)."""
        d, b, tf, tw = IBEAM
        expect = b * tf * (d - tf) + tw * (d - 2 * tf) ** 2 / 4.0
        zp = pc.plastic_section_modulus("i-beam", *IBEAM)
        _assert_rel(self, zp, 0.001213952, 1e-9)
        _assert_rel(self, zp, expect, 1e-15)

    def test_rectangle_elastic_section_modulus_closed_form(self):
        """Rectangle Z = b*h**2/6 = 8.33333333333e-05 m^3."""
        z = pc.elastic_section_modulus("rectangle", *RECT)
        _assert_rel(self, z, 8.33333333333e-05, 1e-9)

    def test_circle_elastic_section_modulus_closed_form(self):
        """Circle Z = pi*d**3/32 = 9.81747704247e-05 m^3."""
        z = pc.elastic_section_modulus("circle", *CIRC)
        _assert_rel(self, z, 9.81747704247e-05, 1e-9)
        _assert_rel(self, z, math.pi * CIRC[0] ** 3 / 32.0, 1e-15)

    def test_ibeam_elastic_section_modulus_closed_form(self):
        """I-beam Z = 2*I/d from the doubly symmetric inertia."""
        d, b, tf, tw = IBEAM
        inertia = (b * d ** 3 - (b - tw) * (d - 2 * tf) ** 3) / 12.0
        z = pc.elastic_section_modulus("i-beam", *IBEAM)
        _assert_rel(self, z, 0.00108074325333, 1e-9)
        _assert_rel(self, z, 2.0 * inertia / d, 1e-15)

    # --- step 1 continued: the shape factor nu = Zp/Z, the reserve
    # between first yield and full plasticity -----------------------

    def test_rectangle_shape_factor_exact_one_and_a_half(self):
        """Rectangle shape factor nu = 1.5 (anchor residual 0.0)."""
        nu = pc.shape_factor("rectangle", *RECT)
        _assert_rel(self, nu, 1.5, 1e-12)

    def test_circle_shape_factor_16_over_3pi(self):
        """Circle nu = 16/(3*pi) = 1.69765272631."""
        nu = pc.shape_factor("circle", *CIRC)
        _assert_rel(self, nu, 16.0 / (3.0 * math.pi), 1e-12)
        _assert_rel(self, nu, 1.69765272631, 1e-6)

    def test_ibeam_shape_factor_rolled_section_value(self):
        """I-beam nu = 1.12325660721: flanges cut the reserve."""
        nu = pc.shape_factor("i-beam", *IBEAM)
        _assert_rel(self, nu, 1.12325660721, 1e-6)

    def test_shape_factor_reserve_ordering(self):
        """nu circle 1.6977 > nu rectangle 1.5 > nu I-beam 1.1233."""
        nu_c = pc.shape_factor("circle", *CIRC)
        nu_r = pc.shape_factor("rectangle", *RECT)
        nu_i = pc.shape_factor("i-beam", *IBEAM)
        self.assertGreater(nu_c, nu_r)
        self.assertGreater(nu_r, nu_i)
        _assert_rel(self, nu_c, 1.6977, 1e-3)
        _assert_rel(self, nu_i, 1.1233, 1e-3)

    def test_shape_factor_equals_mp_over_my_identity(self):
        """nu = Mp/My identity holds for every worked section."""
        for shape, dims in (("rectangle", RECT), ("circle", CIRC),
                            ("i-beam", IBEAM)):
            zp = pc.plastic_section_modulus(shape, *dims)
            mp = pc.fully_plastic_moment(SIGMA_Y, zp)
            my = mp / pc.shape_factor(shape, *dims)
            _assert_rel(self, pc.shape_factor(shape, *dims), mp / my, 1e-9)

    # --- step 2 of the SKILL.md workflow: yield capacity of the
    # member, fully plastic moment Mp = sigma_y*Zp and the first-yield
    # moment My = Mp/nu ----------------------------------------------

    def test_fully_plastic_moments_of_worked_sections(self):
        """Mp = 31250, 41666.6666667 and 303488 N m at sigma_y = 250 MPa."""
        mp_r = pc.fully_plastic_moment(SIGMA_Y,
                                       pc.plastic_section_modulus(
                                           "rectangle", *RECT))
        mp_c = pc.fully_plastic_moment(SIGMA_Y,
                                       pc.plastic_section_modulus(
                                           "circle", *CIRC))
        mp_i = pc.fully_plastic_moment(SIGMA_Y,
                                       pc.plastic_section_modulus(
                                           "i-beam", *IBEAM))
        _assert_rel(self, mp_r, 31250.0, 1e-9)
        _assert_rel(self, mp_c, 41666.6666667, 1e-9)
        _assert_rel(self, mp_i, 303488.0, 1e-9)
        _assert_rel(self, pc.fully_plastic_moment(250e6, 0.000125),
                    31250.0, 1e-9)

    def test_first_yield_moments_from_shape_factor(self):
        """My = Mp/nu: 20833.3333333, 24543.6926062, 270185.813333 N m."""
        my_r = MP_RECT / pc.shape_factor("rectangle", *RECT)
        my_c = (pc.fully_plastic_moment(
            SIGMA_Y, pc.plastic_section_modulus("circle", *CIRC))
            / pc.shape_factor("circle", *CIRC))
        my_i = MP_IBEAM / pc.shape_factor("i-beam", *IBEAM)
        _assert_rel(self, my_r, 20833.3333333, 1e-6)
        _assert_rel(self, my_c, 24543.6926062, 1e-6)
        _assert_rel(self, my_i, 270185.813333, 1e-6)

    # --- step 3 of the SKILL.md workflow: plastic hinge mechanisms of
    # the single-span beams and the collapse loads by the kinematic
    # (virtual work) theorem, r + 1 hinges for r-fold indeterminacy ---

    def test_simply_supported_central_collapse_load(self):
        """Wc = 4*Mp/L = 41666.6666667 N, one hinge at midspan."""
        out = pc.collapse_load_beam("simply-supported-central", L_BEAM,
                                    MP_RECT)
        self.assertEqual(out["case"], "simply-supported-central")
        _assert_rel(self, out["collapse_load"], 41666.6666667, 1e-9)
        self.assertEqual(out["plastic_hinges"], 1)
        self.assertIn("x = L/2", out["hinge_locations"])

    def test_propped_cantilever_central_collapse_load(self):
        """Wc = 6*Mp/L = 62500 N, hinges at the fixed end and load."""
        out = pc.collapse_load_beam("propped-cantilever-central", L_BEAM,
                                    MP_RECT)
        self.assertEqual(out["case"], "propped-cantilever-central")
        _assert_rel(self, out["collapse_load"], 62500.0, 1e-9)
        self.assertEqual(out["plastic_hinges"], 2)
        self.assertIn("x = 0", out["hinge_locations"])
        self.assertIn("x = L/2", out["hinge_locations"])

    def test_fixed_fixed_central_collapse_load(self):
        """Wc = 8*Mp/L = 83333.3333333 N, hinges at both ends and mid."""
        out = pc.collapse_load_beam("fixed-fixed-central", L_BEAM, MP_RECT)
        self.assertEqual(out["case"], "fixed-fixed-central")
        _assert_rel(self, out["collapse_load"], 83333.3333333, 1e-9)
        self.assertEqual(out["plastic_hinges"], 3)
        for station in ("x = 0", "x = L/2", "x = L"):
            self.assertIn(station, out["hinge_locations"])

    def test_beam_collapse_closed_form_identity(self):
        """Wc equals 4*Mp/L, 6*Mp/L and 8*Mp/L by construction."""
        for config, factor in (("simply-supported-central", 4.0),
                               ("propped-cantilever-central", 6.0),
                               ("fixed-fixed-central", 8.0)):
            out = pc.collapse_load_beam(config, L_BEAM, MP_RECT)
            _assert_rel(self, out["collapse_load"],
                        factor * MP_RECT / L_BEAM, 1e-9)
            self.assertIn("mechanism", out)
            self.assertTrue(out["mechanism"])

    # --- step 4 of the SKILL.md workflow: the static theorem
    # cross-check on the collapse-state equilibrium moment diagram ---

    def test_static_theorem_moment_bounded_by_mp(self):
        """Collapse-state |M(x)| never exceeds Mp = 31250 N m."""
        cases = {
            "simply-supported-central": (41666.6666667, 0.5, 0.0),
            "propped-cantilever-central": (62500.0, 2.0 / 3.0, MP_RECT),
            "fixed-fixed-central": (83333.3333333, 0.5, MP_RECT),
        }
        stations = 2001
        for config, (load, left_fraction, end_moment) in cases.items():
            max_mag = 0.0
            for i in range(stations):
                x = i * L_BEAM / (stations - 1)
                m = _rectangular_moment(x, load, L_BEAM, left_fraction,
                                        end_moment)
                max_mag = max(max_mag, abs(m))
            _assert_rel(self, max_mag, MP_RECT, 1e-6, config)
            overshoot = max_mag - MP_RECT
            self.assertLessEqual(overshoot / MP_RECT, 1e-9, config)

    def test_static_theorem_equality_only_at_hinge_stations(self):
        """|M| = Mp only where the collapse mechanism hinges."""
        cases = {
            "simply-supported-central": (41666.6666667, 0.5, 0.0,
                                         (L_BEAM / 2.0,)),
            "propped-cantilever-central": (62500.0, 2.0 / 3.0, MP_RECT,
                                           (0.0, L_BEAM / 2.0)),
            "fixed-fixed-central": (83333.3333333, 0.5, MP_RECT,
                                    (0.0, L_BEAM / 2.0, L_BEAM)),
        }
        stations = 2001
        for config, (load, left_fraction, end_moment, hinges) in \
                cases.items():
            for i in range(stations):
                x = i * L_BEAM / (stations - 1)
                m = _rectangular_moment(x, load, L_BEAM, left_fraction,
                                        end_moment)
                at_hinge = any(abs(x - hx) < 1e-9 for hx in hinges)
                if at_hinge:
                    _assert_rel(self, abs(m), MP_RECT, 1e-6,
                                "%s at x=%g" % (config, x))
                else:
                    self.assertLess(abs(m), MP_RECT * (1.0 + 1e-9),
                                    "%s at x=%g" % (config, x))

    # --- step 5 of the SKILL.md workflow: elastic first-yield context
    # loads and the collapse-to-yield ratios Wc/Wy -------------------

    def test_elastic_first_yield_context_loads(self):
        """W_y = 4*My/L, 16*My/(3*L), 8*My/L at My = 20833.3333333."""
        my = MP_RECT / pc.shape_factor("rectangle", *RECT)
        _assert_rel(self, my, 20833.3333333, 1e-6)
        wy_ss = 4.0 * my / L_BEAM
        wy_propped = 16.0 * my / (3.0 * L_BEAM)
        wy_ff = 8.0 * my / L_BEAM
        _assert_rel(self, wy_ss, 27777.7777778, 1e-6)
        _assert_rel(self, wy_propped, 37037.037037, 1e-6)
        _assert_rel(self, wy_ff, 55555.5555556, 1e-6)

    def test_collapse_to_yield_ratios(self):
        """Wc/Wy = nu, 9*nu/8 and nu: propped gains 12.5% over nu."""
        my = MP_RECT / pc.shape_factor("rectangle", *RECT)
        wc = {cfg: pc.collapse_load_beam(cfg, L_BEAM, MP_RECT)[
            "collapse_load"] for cfg in
            ("simply-supported-central", "propped-cantilever-central",
             "fixed-fixed-central")}
        _assert_rel(self, wc["simply-supported-central"]
                    / (4.0 * my / L_BEAM), 1.5, 1e-9)
        _assert_rel(self, wc["propped-cantilever-central"]
                    / (16.0 * my / (3.0 * L_BEAM)), 1.6875, 1e-9)
        _assert_rel(self, wc["fixed-fixed-central"]
                    / (8.0 * my / L_BEAM), 1.5, 1e-9)

    # --- step 6 of the SKILL.md workflow: sway mechanisms of the
    # portal frame under a top lateral load --------------------------

    def test_portal_sway_pinned_bases(self):
        """Pinned-base sway Hc = 2*Mp/h = 151744 N, 2 top-corner hinges."""
        out = pc.portal_sway_collapse_load(H_PORTAL, MP_IBEAM, "pinned")
        self.assertEqual(out["case"], "portal-sway-pinned")
        _assert_rel(self, out["collapse_load"], 151744.0, 1e-9)
        self.assertEqual(out["plastic_hinges"], 2)
        self.assertEqual(len(out["hinge_locations"]), 2)
        _assert_rel(self, out["collapse_load"],
                    2.0 * MP_IBEAM / H_PORTAL, 1e-12)

    def test_portal_sway_fixed_bases(self):
        """Fixed-base sway Hc = 4*Mp/h = 303488 N, 4 corner hinges."""
        out = pc.portal_sway_collapse_load(H_PORTAL, MP_IBEAM, "fixed")
        self.assertEqual(out["case"], "portal-sway-fixed")
        _assert_rel(self, out["collapse_load"], 303488.0, 1e-9)
        self.assertEqual(out["plastic_hinges"], 4)
        self.assertEqual(len(out["hinge_locations"]), 4)

    def test_fixed_base_sway_doubles_pinned_base(self):
        """Fixing the feet doubles the hinge dissipation to 4*Mp/h."""
        pinned = pc.portal_sway_collapse_load(H_PORTAL, MP_IBEAM,
                                              "pinned")["collapse_load"]
        fixed = pc.portal_sway_collapse_load(H_PORTAL, MP_IBEAM,
                                             "fixed")["collapse_load"]
        _assert_rel(self, fixed / pinned, 2.0, 1e-12)
        _assert_rel(self, pc.portal_sway_collapse_load(H_PORTAL, MP_IBEAM)[
            "collapse_load"], pinned, 1e-12,
            msg="pinned is the default base")

    # --- step 7 of the SKILL.md workflow: collapse load factor and
    # the FAR 25.303 ultimate margin verdict -------------------------

    def test_collapse_load_factor_ratio(self):
        """lambda = collapse load / limit load = 2.08333333333 at 40 kN."""
        lam = pc.collapse_load_factor(40000.0, 83333.3333333)
        _assert_rel(self, lam, 2.08333333333, 1e-9)
        _assert_rel(self, lam, 83333.3333333 / 40000.0, 1e-12)

    def test_ultimate_margin_adequate_beam(self):
        """40 kN limit: margin 1.38888888889, verdict adequate."""
        out = pc.ultimate_margin(40000.0, 83333.3333333)
        _assert_rel(self, out["collapse_load_factor"], 2.08333333333, 1e-6)
        _assert_rel(self, out["ultimate_load_required"], 60000.0, 1e-9)
        _assert_rel(self, out["ultimate_margin"], 1.38888888889, 1e-6)
        self.assertEqual(out["verdict"], "adequate")

    def test_ultimate_margin_inadequate_beam(self):
        """60 kN limit: margin 0.925925925926, verdict inadequate."""
        out = pc.ultimate_margin(60000.0, 83333.3333333)
        _assert_rel(self, out["collapse_load_factor"], 1.38888888889, 1e-6)
        _assert_rel(self, out["ultimate_margin"], 0.925925925926, 1e-6)
        self.assertEqual(out["verdict"], "inadequate")

    def test_ultimate_margin_portal_adequate(self):
        """Pinned portal at 60 kN: 2.52906666667, margin 1.68604444444."""
        pinned = pc.portal_sway_collapse_load(H_PORTAL, MP_IBEAM,
                                              "pinned")["collapse_load"]
        fixed = pc.portal_sway_collapse_load(H_PORTAL, MP_IBEAM,
                                             "fixed")["collapse_load"]
        out_p = pc.ultimate_margin(60000.0, pinned)
        _assert_rel(self, out_p["collapse_load_factor"], 2.52906666667, 1e-6)
        _assert_rel(self, out_p["ultimate_margin"], 1.68604444444, 1e-6)
        self.assertEqual(out_p["verdict"], "adequate")
        out_f = pc.ultimate_margin(60000.0, fixed)
        _assert_rel(self, out_f["collapse_load_factor"], 5.05813333333, 1e-6)
        _assert_rel(self, out_f["ultimate_margin"], 3.37208888889, 1e-6)
        self.assertEqual(out_f["verdict"], "adequate")

    def test_verdict_flip_at_collapse_over_ultimate_factor(self):
        """Verdict flips where collapse load crosses 1.5*limit load."""
        pinned = pc.portal_sway_collapse_load(H_PORTAL, MP_IBEAM,
                                              "pinned")["collapse_load"]
        threshold = pinned / 1.5
        _assert_rel(self, threshold, 101162.666667, 1e-6)
        below = pc.ultimate_margin(threshold * (1.0 - 1e-9), pinned)
        above = pc.ultimate_margin(threshold * (1.0 + 1e-9), pinned)
        self.assertEqual(below["verdict"], "adequate")
        self.assertEqual(above["verdict"], "inadequate")

    # --- ValueError rejection of non-physical inputs (13 anchor
    # cases) and determinism -----------------------------------------

    def test_valueerror_section_validation(self):
        """Unknown shapes, nonpositive dims, bad I-beam proportions."""
        with self.assertRaises(ValueError):
            pc.plastic_section_modulus("triangle", 0.05, 0.1)
        with self.assertRaises(ValueError):
            pc.plastic_section_modulus("rectangle", 0.0, 0.1)
        with self.assertRaises(ValueError):
            pc.plastic_section_modulus("circle", 0.0)
        with self.assertRaises(ValueError):
            pc.plastic_section_modulus("i-beam", 0.2, 0.2, 0.12, 0.008)
        with self.assertRaises(ValueError):
            pc.plastic_section_modulus("i-beam", 0.4, 0.2, 0.012)
        for fn in (pc.elastic_section_modulus, pc.shape_factor):
            with self.assertRaises(ValueError):
                fn("rectangle", 0.05, -0.1)
            with self.assertRaises(ValueError):
                fn("i-beam", 0.4, 0.2, 0.2, 0.008)  # t_w >= b

    def test_valueerror_yield_stress_and_section_modulus(self):
        """fully_plastic_moment rejects sigma_y <= 0 and zp <= 0."""
        with self.assertRaises(ValueError):
            pc.fully_plastic_moment(0.0, 0.000125)
        with self.assertRaises(ValueError):
            pc.fully_plastic_moment(250e6, -1.0)

    def test_valueerror_beam_and_frame_configs(self):
        """Unknown cases, zero spans and heights, nonpositive Mp."""
        with self.assertRaises(ValueError):
            pc.collapse_load_beam("cantilever-central", L_BEAM, MP_RECT)
        with self.assertRaises(ValueError):
            pc.collapse_load_beam("fixed-fixed-central", 0.0, MP_RECT)
        with self.assertRaises(ValueError):
            pc.collapse_load_beam("fixed-fixed-central", L_BEAM, 0.0)
        with self.assertRaises(ValueError):
            pc.portal_sway_collapse_load(H_PORTAL, MP_IBEAM, "propped")
        with self.assertRaises(ValueError):
            pc.portal_sway_collapse_load(0.0, MP_IBEAM)
        with self.assertRaises(ValueError):
            pc.portal_sway_collapse_load(H_PORTAL, -1.0)

    def test_valueerror_margin_arguments(self):
        """Load factors and margins reject nonpositive arguments."""
        with self.assertRaises(ValueError):
            pc.collapse_load_factor(0.0, 83333.3333333)
        with self.assertRaises(ValueError):
            pc.collapse_load_factor(40000.0, -5.0)
        with self.assertRaises(ValueError):
            pc.ultimate_margin(40000.0, 83333.3333333, 0.0)
        with self.assertRaises(ValueError):
            pc.ultimate_margin(-1.0, 83333.3333333)

    def test_deterministic_repeat_and_key_schema(self):
        """Two identical runs return identical dicts with all keys."""
        first = pc.collapse_load_beam("fixed-fixed-central", L_BEAM,
                                      MP_RECT)
        second = pc.collapse_load_beam("fixed-fixed-central", L_BEAM,
                                       MP_RECT)
        self.assertEqual(first, second)
        self.assertEqual(
            sorted(first.keys()),
            ["case", "collapse_load", "hinge_locations", "mechanism",
             "plastic_hinges"])
        frame = pc.portal_sway_collapse_load(H_PORTAL, MP_IBEAM)
        self.assertEqual(
            sorted(frame.keys()),
            ["case", "collapse_load", "hinge_locations", "mechanism",
             "plastic_hinges"])
        margin = pc.ultimate_margin(40000.0, 83333.3333333)
        self.assertEqual(
            sorted(margin.keys()),
            ["collapse_load_factor", "ultimate_load_required",
             "ultimate_margin", "verdict"])


if __name__ == "__main__":
    unittest.main()
