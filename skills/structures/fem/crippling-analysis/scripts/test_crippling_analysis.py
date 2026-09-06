"""Contract test for the crippling-analysis leaf (structures/fem).

Exercises the SKILL.md workflow end to end: step 1 material resolution,
step 2 formed-shape expansion into flat elements, step 3 element crippling
stress by the shape-constant power law, step 4 area-weighted section
crippling averaging, step 5 the inter-rivet buckling allowable of the
fastener-attached flat, step 6 the Johnson-Euler stiffener column
interaction anchored on the local crippling stress, and step 7 the
stiffener compression allowable with its margin of safety and verdict.
All asserts are tolerance-based (order-safe across interpreters); exact
equality is used only for literal constants, exact yield-cap returns and
bit-identical repeat runs.
"""

import math
import os
import re
import unittest

_MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
_SYS_PATH = os.path.dirname(_MODULE_DIR)
if _SYS_PATH not in __import__("sys").path:
    __import__("sys").path.insert(0, _SYS_PATH)

from crippling_analysis_logic import (  # noqa: E402
    CRIPPLING_EXPONENT,
    C_OEF,
    C_SEF,
    K_INTER_RIVET,
    MATERIALS,
    material,
    element_crippling_stress,
    section_crippling_stress,
    inter_rivet_allowable,
    column_interaction_allowable,
    compression_margin,
    formed_shape_elements,
    stiffener_compression_check,
)

AL = material("2024-T3")
T6 = material("7075-T6")

# Worked-example geometry (spec section "Worked example", SI units).
Z_ELEMENTS = [
    {"label": "web", "b": 32e-3, "t": 1.6e-3, "cls": "sef"},
    {"label": "flange-a", "b": 19e-3, "t": 1.6e-3, "cls": "oef"},
    {"label": "flange-b", "b": 19e-3, "t": 1.6e-3, "cls": "oef"},
]
ANGLE_ELEMENTS = formed_shape_elements("angle", b1=25e-3, b2=25e-3, t=1.6e-3)
HAT_ELEMENTS = formed_shape_elements("hat", bc=25e-3, bl=12e-3, t=0.7e-3)


def assert_rel(test, actual, expected, rel):
    """Fail unless actual and expected agree within the relative tolerance."""
    test.assertTrue(
        math.isclose(actual, expected, rel_tol=rel, abs_tol=0.0),
        "expected %.12g within %.3g relative of %.12g, got %.12g"
        % (expected, rel, expected, actual),
    )


class MaterialResolutionTests(unittest.TestCase):
    """Step 1 of the SKILL.md workflow, the material constant resolution."""

    def test_material_resolves_both_registry_constants(self):
        self.assertEqual(AL, {"E": 72.4e9, "fcy": 290.0e6, "nu": 0.33})
        self.assertEqual(T6, {"E": 71.7e9, "fcy": 462.0e6, "nu": 0.33})
        self.assertEqual(sorted(MATERIALS), ["2024-T3", "7075-T6"])

    def test_material_case_and_whitespace_insensitive(self):
        # "2024-T3", " 2024-t3 ", "2024 t3" and "2024-t3" all resolve, the
        # hyphen reads as optional spacing
        for name in ("2024-T3", " 2024-t3 ", "2024 t3", "2024-t3"):
            self.assertEqual(material(name), AL)
        for name in ("7075-T6", "7075-t6", " 7075 T6"):
            self.assertEqual(material(name), T6)

    def test_unknown_material_raises_valueerror(self):
        for bad in ("steel", "6061-T6", "", None, 7):
            with self.assertRaises(ValueError):
                material(bad)


class ElementCripplingTests(unittest.TestCase):
    """Step 3 of the SKILL.md workflow, shape-constant element crippling."""

    def test_z_stringer_element_anchors_step3(self):
        # web (no-edge-free, b/t = 20) at 266.4762 MPa and each flange
        # (one-edge-free, b/t = 11.9) at 222.0520 MPa
        assert_rel(self, element_crippling_stress(32e-3, 1.6e-3, "sef", AL),
                   266.4762e6, 1e-5)
        assert_rel(self, element_crippling_stress(19e-3, 1.6e-3, "oef", AL),
                   222.0520e6, 1e-5)

    def test_angle_and_hat_element_anchors_step3(self):
        # angle leg (oef, b/t = 15.6) 180.7444 MPa; hat crown (sef,
        # b/t = 35.7) 172.5041 MPa and hat leg (oef, b/t = 17.1)
        # 168.6039 MPa
        assert_rel(self, element_crippling_stress(25e-3, 1.6e-3, "oef", AL),
                   180.7444e6, 1e-5)
        assert_rel(self, element_crippling_stress(25e-3, 0.7e-3, "sef", AL),
                   172.5041e6, 1e-5)
        assert_rel(self, element_crippling_stress(12e-3, 0.7e-3, "oef", AL),
                   168.6039e6, 1e-5)

    def test_yield_cap_stubby_element_returns_fcy_exactly(self):
        # one-edge-free 2024-T3 at b/t = 5: the raw power law sits above
        # yield (it crosses fcy near b/t = 8.3), so min() returns the fcy
        # literal unchanged
        self.assertEqual(element_crippling_stress(5 * 1.6e-3, 1.6e-3, "oef", AL),
                         AL["fcy"])
        self.assertEqual(element_crippling_stress(5 * 1.6e-3, 1.6e-3, "sef", AL),
                         AL["fcy"])

    def test_class_ranking_and_yield_bounds(self):
        # at equal b/t the no-edge-free allowance sits at or above the
        # one-edge-free allowance and both sit at or below fcy
        b, t = 32e-3, 1.6e-3
        oef = element_crippling_stress(b, t, "oef", AL)
        sef = element_crippling_stress(b, t, "sef", AL)
        self.assertGreaterEqual(sef, oef)
        self.assertLessEqual(oef, AL["fcy"])
        self.assertLessEqual(sef, AL["fcy"])

    def test_crippling_power_law_quarter_identity(self):
        # at fixed t, quadrupling b multiplies the raw element stress by
        # (1/4)**0.75 = 0.353553390593 (spec identity, module constants
        # pinned: exponent 0.75, C_OEF 0.31, C_SEF 0.55)
        base = element_crippling_stress(19e-3, 1.6e-3, "oef", AL)
        wide = element_crippling_stress(4 * 19e-3, 1.6e-3, "oef", AL)
        assert_rel(self, wide / base, 0.25 ** CRIPPLING_EXPONENT, 1e-9)
        self.assertEqual((CRIPPLING_EXPONENT, C_OEF, C_SEF), (0.75, 0.31, 0.55))

    def test_element_nonpositive_geometry_raises(self):
        with self.assertRaises(ValueError):
            element_crippling_stress(0.0, 1.6e-3, "oef", AL)
        with self.assertRaises(ValueError):
            element_crippling_stress(-1e-3, 1.6e-3, "oef", AL)
        with self.assertRaises(ValueError):
            element_crippling_stress(19e-3, 0.0, "oef", AL)
        with self.assertRaises(ValueError):
            element_crippling_stress(19e-3, -1e-3, "sef", AL)

    def test_element_unknown_edge_class_raises(self):
        for cls in ("bulb", "free", "SEF", ""):
            with self.assertRaises(ValueError):
                element_crippling_stress(19e-3, 1.6e-3, cls, AL)


class SectionCripplingTests(unittest.TestCase):
    """Step 4 of the SKILL.md workflow, area-weighted section averaging."""

    def test_z_stringer_section_allowable_step4(self):
        # anchor: section F_cc = 242.3602 MPa, 0.8357 of F_cy, total flat
        # area 1.12e-4 m^2 over the web plus two flanges
        result = section_crippling_stress(Z_ELEMENTS, AL)
        assert_rel(self, result["fcc"], 242.3602e6, 1e-5)
        assert_rel(self, result["fcc"] / AL["fcy"], 0.8357, 1e-4)
        assert_rel(self, result["area_total"], 1.12e-4, 1e-9)
        rows = {row["label"]: row for row in result["elements"]}
        self.assertEqual(len(rows), 3)
        assert_rel(self, rows["web"]["area"], 32e-3 * 1.6e-3, 1e-12)
        assert_rel(self, rows["flange-a"]["fcc"], 222.0520e6, 1e-5)

    def test_section_average_properties(self):
        # the area-weighted section allowable of the mixed Z section lies
        # strictly between its element extremes, while a uniform section
        # (angle) averages back to the common element value
        mixed = section_crippling_stress(Z_ELEMENTS, AL)
        fccs = [row["fcc"] for row in mixed["elements"]]
        self.assertGreater(mixed["fcc"], min(fccs))
        self.assertLess(mixed["fcc"], max(fccs))
        uniform = section_crippling_stress(ANGLE_ELEMENTS, AL)
        leg = element_crippling_stress(25e-3, 1.6e-3, "oef", AL)
        assert_rel(self, uniform["fcc"], leg, 1e-12)

    def test_bulb_element_carries_at_yield(self):
        # a solid bulb does not cripple locally: it carries at fcy with
        # area pi*d**2/4
        result = section_crippling_stress(
            [{"label": "bulb", "d": 5e-3, "cls": "bulb"}], AL)
        self.assertEqual(result["fcc"], AL["fcy"])
        assert_rel(self, result["area_total"],
                   math.pi * (5e-3) ** 2 / 4.0, 1e-12)

    def test_section_structural_valueerrors(self):
        with self.assertRaises(ValueError):
            section_crippling_stress([], AL)
        # unknown element class, missing geometry keys, missing label
        with self.assertRaises(ValueError):
            section_crippling_stress(
                [{"label": "x", "b": 1e-3, "t": 1e-3, "cls": "cantilever"}], AL)
        with self.assertRaises(ValueError):
            section_crippling_stress(
                [{"label": "x", "t": 1e-3, "cls": "oef"}], AL)
        with self.assertRaises(ValueError):
            section_crippling_stress(
                [{"label": "x", "cls": "bulb"}], AL)
        with self.assertRaises(ValueError):
            section_crippling_stress([{"cls": "sef"}], AL)


class InterRivetTests(unittest.TestCase):
    """Step 5 of the SKILL.md workflow, inter-rivet buckling allowable."""

    def test_z_and_hat_inter_rivet_anchors_step5(self):
        # 1.6 mm flat at 25 mm pitch: raw 1094.84 MPa, capped at 290.00 MPa
        # yield; 0.7 mm flat at 25 mm pitch: genuine sub-yield inter-rivet
        # regime with raw and allowable both 209.56 MPa
        z_result = inter_rivet_allowable(1.6e-3, 25e-3, AL)
        assert_rel(self, z_result["stress_raw"], 1094.84e6, 1e-5)
        self.assertEqual(z_result["allowable"], AL["fcy"])
        hat_result = inter_rivet_allowable(0.7e-3, 25e-3, AL)
        assert_rel(self, hat_result["stress_raw"], 209.56e6, 1e-5)
        assert_rel(self, hat_result["allowable"], 209.56e6, 1e-5)
        self.assertLess(hat_result["allowable"], AL["fcy"])

    def test_double_thickness_quadruples_stress_identity(self):
        # sigma_ir is quadratic in t_attach/pitch with rivet lines as
        # simple supports; doubling t_attach at fixed pitch quadruples the
        # stress, and the long-plate coefficient at nu = 0.33 reads about
        # 3.69 (K_INTER_RIVET * pi**2 / (12*(1-nu**2)))
        base = inter_rivet_allowable(1.6e-3, 25e-3, AL)
        doubled = inter_rivet_allowable(3.2e-3, 25e-3, AL)
        assert_rel(self, doubled["stress_raw"] / base["stress_raw"], 4.0, 1e-12)
        self.assertEqual(K_INTER_RIVET, 4.0)
        coeff = K_INTER_RIVET * math.pi ** 2 / (12.0 * (1.0 - AL["nu"] ** 2))
        assert_rel(self, coeff, 3.69, 1e-2)

    def test_inter_rivet_nonpositive_inputs_raise(self):
        with self.assertRaises(ValueError):
            inter_rivet_allowable(0.0, 25e-3, AL)
        with self.assertRaises(ValueError):
            inter_rivet_allowable(-1e-3, 25e-3, AL)
        with self.assertRaises(ValueError):
            inter_rivet_allowable(1.6e-3, 0.0, AL)
        with self.assertRaises(ValueError):
            inter_rivet_allowable(1.6e-3, -25e-3, AL)


class ColumnInteractionTests(unittest.TestCase):
    """Step 6 of the SKILL.md workflow, Johnson-Euler interaction."""

    def test_z_stringer_column_interaction_step6(self):
        # fcc = 242.3602 MPa anchors the parabola: lam_t = 76.790 and
        # F_col = 209.4793 MPa at lambda 40 (johnson arm)
        fcc = section_crippling_stress(Z_ELEMENTS, AL)["fcc"]
        result = column_interaction_allowable(fcc, 40.0, AL)
        assert_rel(self, result["lam_t"], 76.790, 1e-4)
        assert_rel(self, result["allowable"], 209.4793e6, 1e-5)
        self.assertEqual(result["regime"], "johnson")

    def test_interaction_curve_arm_values(self):
        # johnson arm at 20 and 60, euler arm at 100 and 150 for the Z;
        # the euler arm matches pi**2*E/lam**2 exactly
        fcc = section_crippling_stress(Z_ELEMENTS, AL)["fcc"]
        cases = [(20.0, 234.1400e6, "johnson"), (60.0, 168.3781e6, "johnson"),
                 (100.0, 71.4559e6, "euler"), (150.0, 31.7582e6, "euler")]
        for lam, expected, regime in cases:
            result = column_interaction_allowable(fcc, lam, AL)
            assert_rel(self, result["allowable"], expected, 1e-5)
            self.assertEqual(result["regime"], regime)
        euler = column_interaction_allowable(fcc, 150.0, AL)
        assert_rel(self, euler["allowable"],
                   math.pi ** 2 * AL["E"] / 150.0 ** 2, 1e-12)

    def test_tangency_both_arms_equal_fcc_over_two_at_lam_t(self):
        # at lam_t the Johnson arm and the Euler arm both return fcc/2 by
        # construction (spec anchor relative difference 2.46e-16), with the
        # regime switching from johnson at lam_t to euler just above it
        fcc = section_crippling_stress(Z_ELEMENTS, AL)["fcc"]
        lam_t = column_interaction_allowable(fcc, 40.0, AL)["lam_t"]
        at_t = column_interaction_allowable(fcc, lam_t, AL)
        assert_rel(self, at_t["allowable"], fcc / 2.0, 1e-9)
        self.assertEqual(at_t["regime"], "johnson")
        above = column_interaction_allowable(fcc, lam_t * (1.0 + 1e-12), AL)
        assert_rel(self, above["allowable"], fcc / 2.0, 1e-9)
        self.assertEqual(above["regime"], "euler")

    def test_column_interaction_nonpositive_inputs_raise(self):
        with self.assertRaises(ValueError):
            column_interaction_allowable(0.0, 40.0, AL)
        with self.assertRaises(ValueError):
            column_interaction_allowable(-1e6, 40.0, AL)
        with self.assertRaises(ValueError):
            column_interaction_allowable(242.3602e6, 0.0, AL)
        with self.assertRaises(ValueError):
            column_interaction_allowable(242.3602e6, -40.0, AL)


class FormedShapeTests(unittest.TestCase):
    """Step 2 of the SKILL.md workflow, formed-shape element expansion."""

    def test_angle_and_hat_expansion_step2(self):
        # an angle is two one-edge-free legs; a hat is a no-edge-free
        # crown plus two one-edge-free legs
        angle = formed_shape_elements("angle", b1=25e-3, b2=25e-3, t=1.6e-3)
        self.assertEqual(len(angle), 2)
        self.assertTrue(all(e["cls"] == "oef" for e in angle))
        self.assertTrue(all(e["b"] == 25e-3 and e["t"] == 1.6e-3
                            for e in angle))
        hat = formed_shape_elements("hat", bc=25e-3, bl=12e-3, t=0.7e-3)
        self.assertEqual(len(hat), 3)
        self.assertEqual(hat[0]["cls"], "sef")
        self.assertEqual(hat[0]["b"], 25e-3)
        self.assertTrue(all(e["cls"] == "oef" for e in hat[1:]))

    def test_channel_and_z_share_element_classes(self):
        # channel and Z share the no-edge-free web plus two one-edge-free
        # flanges, so they give the same section crippling allowable
        # 242.3602 MPa
        channel = formed_shape_elements("channel", bw=32e-3, bf=19e-3, t=1.6e-3)
        zed = formed_shape_elements("z", bw=32e-3, bf=19e-3, t=1.6e-3)
        self.assertEqual([e["cls"] for e in channel], ["sef", "oef", "oef"])
        self.assertEqual([e["cls"] for e in zed], ["sef", "oef", "oef"])
        fcc_ch = section_crippling_stress(channel, AL)["fcc"]
        fcc_z = section_crippling_stress(zed, AL)["fcc"]
        assert_rel(self, fcc_ch, 242.3602e6, 1e-5)
        assert_rel(self, fcc_z, fcc_ch, 1e-12)

    def test_bulb_angle_expansion_and_section_elevation(self):
        # plain leg and stem are one-edge-free flats, the bulb is a solid
        # element: bulb-angle 218.5184 MPa (0.7535 of F_cy) sits above the
        # plain angle 180.7444 MPa
        elements = formed_shape_elements(
            "bulb-angle", b1=25e-3, bs=19e-3, d=5e-3, t=1.6e-3)
        self.assertEqual(len(elements), 3)
        self.assertEqual([e["cls"] for e in elements],
                         ["oef", "oef", "bulb"])
        fcc_ba = section_crippling_stress(elements, AL)["fcc"]
        fcc_angle = section_crippling_stress(ANGLE_ELEMENTS, AL)["fcc"]
        assert_rel(self, fcc_ba, 218.5184e6, 1e-5)
        assert_rel(self, fcc_ba / AL["fcy"], 0.7535, 1e-4)
        self.assertGreater(fcc_ba, fcc_angle)

    def test_formed_shape_valueerrors(self):
        # unknown shape, missing dims, non-positive and non-numeric dims
        with self.assertRaises(ValueError):
            formed_shape_elements("tee", b1=1e-3, b2=1e-3, t=1e-3)
        with self.assertRaises(ValueError):
            formed_shape_elements("angle", b1=25e-3, t=1.6e-3)
        with self.assertRaises(ValueError):
            formed_shape_elements("angle", b1=-25e-3, b2=25e-3, t=1.6e-3)
        with self.assertRaises(ValueError):
            formed_shape_elements("hat", bc=0.0, bl=12e-3, t=0.7e-3)
        with self.assertRaises(ValueError):
            formed_shape_elements("channel", bw=32e-3, bf=19e-3, t="thin")
        with self.assertRaises(ValueError):
            formed_shape_elements("bulb-angle", b1=25e-3, bs=19e-3, d=0.0,
                                  t=1.6e-3)


class UmbrellaCheckTests(unittest.TestCase):
    """Step 7 of the SKILL.md workflow, compression allowable and margin."""

    def test_z_stringer_full_check_step7(self):
        # 2024-T3 Z-stringer at 150 MPa applied, lambda 40: F_comp =
        # min(209.4793, 290.00) = 209.4793 MPa, margin 0.396529, pass
        result = stiffener_compression_check(
            Z_ELEMENTS, AL, 1.6e-3, 25e-3, 40.0, 150e6)
        assert_rel(self, result["fcc_section"], 242.3602e6, 1e-5)
        assert_rel(self, result["area_total"], 1.12e-4, 1e-9)
        assert_rel(self, result["sigma_ir_raw"], 1094.84e6, 1e-5)
        self.assertEqual(result["f_ir_allowable"], AL["fcy"])
        assert_rel(self, result["f_col_allowable"], 209.4793e6, 1e-5)
        assert_rel(self, result["lam_t"], 76.790, 1e-4)
        self.assertEqual(result["column_regime"], "johnson")
        self.assertEqual(result["f_compression_allowable"],
                         result["f_col_allowable"])
        assert_rel(self, result["margin"], 0.396529, 1e-4)
        self.assertEqual(result["verdict"], "pass")

    def test_angle_and_hat_stringer_checks_step7(self):
        # angle 25x25 at 120 MPa applied, lambda 50: F_cc 180.7444 MPa,
        # F_col 152.1704 MPa, margin 0.268087; hat 25/12 thin gauge at
        # 100 MPa, lambda 60: inter-rivet 209.56 MPa sits below yield but
        # the column interaction binds at 133.9390 MPa, margin 0.339390
        angle = stiffener_compression_check(
            ANGLE_ELEMENTS, AL, 1.6e-3, 25e-3, 50.0, 120e6)
        assert_rel(self, angle["fcc_section"], 180.7444e6, 1e-5)
        assert_rel(self, angle["f_col_allowable"], 152.1704e6, 1e-5)
        assert_rel(self, angle["margin"], 0.268087, 1e-4)
        self.assertEqual(angle["verdict"], "pass")
        hat = stiffener_compression_check(
            HAT_ELEMENTS, AL, 0.7e-3, 25e-3, 60.0, 100e6)
        assert_rel(self, hat["fcc_section"], 170.5938e6, 1e-5)
        assert_rel(self, hat["sigma_ir_raw"], 209.56e6, 1e-5)
        assert_rel(self, hat["f_ir_allowable"], 209.56e6, 1e-5)
        assert_rel(self, hat["f_col_allowable"], 133.9390e6, 1e-5)
        self.assertEqual(hat["f_compression_allowable"],
                         hat["f_col_allowable"])
        assert_rel(self, hat["margin"], 0.339390, 1e-4)
        self.assertEqual(hat["verdict"], "pass")

    def test_7075_t6_material_normalization(self):
        # the same Z geometry in 7075-T6 gives 304.4203 MPa but only
        # 0.6589 of F_cy versus 0.8357 for 2024-T3, the lower normalized
        # crippling of the higher-strength alloy
        result = section_crippling_stress(Z_ELEMENTS, T6)
        assert_rel(self, result["fcc"], 304.4203e6, 1e-5)
        assert_rel(self, result["fcc"] / T6["fcy"], 0.6589, 1e-4)
        ratio_24 = section_crippling_stress(Z_ELEMENTS, AL)["fcc"] / AL["fcy"]
        self.assertGreater(ratio_24, result["fcc"] / T6["fcy"])

    def test_margin_reproduction_identity(self):
        # compression_margin reproduces the check margin exactly
        result = stiffener_compression_check(
            Z_ELEMENTS, AL, 1.6e-3, 25e-3, 40.0, 150e6)
        direct = compression_margin(result["f_compression_allowable"], 150e6)
        self.assertEqual(direct, result["margin"])

    def test_fail_verdict_when_applied_stress_exceeds_allowable(self):
        base = stiffener_compression_check(
            Z_ELEMENTS, AL, 1.6e-3, 25e-3, 40.0, 150e6)
        # applied set from the check's own allowable, so the margin is
        # -0.5 exactly by construction (round-trip halving)
        result = stiffener_compression_check(
            Z_ELEMENTS, AL, 1.6e-3, 25e-3, 40.0,
            2.0 * base["f_compression_allowable"])
        self.assertEqual(result["verdict"], "fail")
        assert_rel(self, result["margin"], -0.5, 1e-12)

    def test_umbrella_valueerror_inheritance(self):
        # the umbrella check inherits the callee ValueError set: empty
        # section, non-positive applied stress, non-positive t_attach, and
        # the standalone margin on a non-positive applied stress
        with self.assertRaises(ValueError):
            stiffener_compression_check([], AL, 1.6e-3, 25e-3, 40.0, 150e6)
        with self.assertRaises(ValueError):
            stiffener_compression_check(Z_ELEMENTS, AL, 1.6e-3, 25e-3, 40.0,
                                        0.0)
        with self.assertRaises(ValueError):
            stiffener_compression_check(Z_ELEMENTS, AL, 0.0, 25e-3, 40.0,
                                        150e6)
        with self.assertRaises(ValueError):
            compression_margin(209.4793e6, 0.0)
        with self.assertRaises(ValueError):
            compression_margin(209.4793e6, -150e6)


class ModuleHygieneTests(unittest.TestCase):
    """Determinism and stdlib-only constraints of the logic module."""

    def test_determinism_repeat_runs_bit_identical(self):
        first = stiffener_compression_check(
            Z_ELEMENTS, AL, 1.6e-3, 25e-3, 40.0, 150e6)
        second = stiffener_compression_check(
            Z_ELEMENTS, AL, 1.6e-3, 25e-3, 40.0, 150e6)
        self.assertEqual(first, second)

    def test_module_imports_math_only(self):
        # no imports beyond math anywhere in the logic source
        logic_path = os.path.join(_MODULE_DIR, "crippling_analysis_logic.py")
        with open(logic_path, "r") as handle:
            source = handle.read()
        imported = []
        for line in source.splitlines():
            match = re.match(r"^(?:import|from)\s+([A-Za-z0-9_.]+)",
                             line.strip())
            if match:
                imported.append(match.group(1).split(".")[0])
        self.assertEqual(imported, ["math"])


if __name__ == "__main__":
    unittest.main()
