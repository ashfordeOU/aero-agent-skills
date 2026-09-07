"""Contract test for mangler-axisymmetric-transform (aerodynamics boundary-layer).

Step 8 of the SKILL.md workflow, the momentum-integral closure and the
input-rejection traverse, is exercised by test_momentum_integral_closure_
worked_station and the test_valueerror_* methods. The Mangler-transformation
geometry traverse of step 1 (cone radius and the equivalent 2-D running
length xi) is exercised by the cone_radius and mangler_xi tests; the
coordinate-mapping traverse of step 2 (transformed normal coordinate and
the power-law body xi for the cylinder and the cone) by the
transformed_normal_coordinate and powerlaw tests; the flat-plate baseline
consumption of step 3 (skin friction, wall shear, 99-percent, displacement
and momentum thickness inputs at the same running length) by
test_flat_plate_baseline_values_consumed; the cone skin-friction and
wall-shear scaling of step 4 (the sqrt-3 cone factor) by the
cone_skin_friction and cone_wall_shear tests; the cone thickness scaling of
step 5 (the inverse sqrt-3 factor) by the cone_boundary_layer_thickness,
cone_displacement_thickness and cone_momentum_thickness tests; the shape
factor check of step 6 by test_shape_factor_preserved_by_transform; and the
Blasius station-scaling evaluation of the equivalent 2-D layer of step 7 by
the pipeline and helper tests. Deterministic and offline, stdlib unittest,
passes under /usr/bin/python3 3.9.6 and the pyenv 3.13.12 interpreter.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import mangler_axisymmetric_transform_logic as m  # noqa: E402

_SOURCE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "mangler_axisymmetric_transform_logic.py",
)

# Worked-example state (slender cone, 5 deg half angle, standard air).
X_RUN = 2.0            # m, running length
HALF_ANGLE = 5.0       # deg, cone semi-vertex angle
REF_LENGTH = 1.0       # m, Mangler reference length
NU_AIR = 1.5e-5        # m2/s
RHO_AIR = 1.225        # kg/m3
U_E = 30.0             # m/s, constant cone edge velocity

# Worked-example flat-plate baseline inputs at x = 2.0 m (consumed from the
# sibling boundary-layer-theory Blasius correlations, Re_x = 4.0e6).
CF_FLAT = 3.32e-4
TAU_FLAT = 0.183015        # Pa
DELTA_FLAT = 5.0e-3        # m
DELTA_STAR_FLAT = 1.7208e-3  # m
THETA_FLAT = 6.64e-4       # m


def _rel(a, b):
    """Relative difference |a/b - 1|, guarding the zero division."""
    return abs(a / b - 1.0)


class ManglerAxisymmetricTransformContractTest(unittest.TestCase):
    """Worked-example anchors, closed-form identities and rejection paths."""

    # Step 1: geometry traverse of the Mangler transformation on the cone.
    def test_cone_radius_anchor_value(self):
        """Step 1 geometry traverse: cone_radius(2.0, 5.0) returns the cone
        surface radius 1.749773271e-01 m at the worked running length, equal
        to x*tan(alpha) with the degrees-to-radians conversion internal."""
        r0 = m.cone_radius(X_RUN, HALF_ANGLE)
        self.assertAlmostEqual(_rel(r0, 1.749773271e-01), 0.0, delta=1e-6)
        self.assertAlmostEqual(
            _rel(r0, X_RUN * math.tan(math.radians(HALF_ANGLE))),
            0.0, delta=1e-12)

    def test_mangler_xi_anchor_value(self):
        """Step 1 geometry traverse: mangler_xi(2.0, 5.0, 1.0) returns the
        equivalent 2-D running length 2.041137665e-02 m (the 2 m cone maps
        to a 2 cm plate), equal to cone_radius**2*x/(3*L**2)."""
        xi = m.mangler_xi(X_RUN, HALF_ANGLE, REF_LENGTH)
        self.assertAlmostEqual(_rel(xi, 2.041137665e-02), 0.0, delta=1e-6)
        r0 = m.cone_radius(X_RUN, HALF_ANGLE)
        self.assertAlmostEqual(
            _rel(xi, r0 * r0 * X_RUN / 3.0), 0.0, delta=1e-12)

    def test_mangler_xi_cubic_scaling_along_cone(self):
        """Step 1 geometry traverse: the transformed running length xi of the
        Mangler transformation scales as x**3 along the cone, so the
        half-length station carries one eighth of the full-station xi, and
        doubling the reference length quarters xi (L-invariance of the
        physical mapping)."""
        xi_full = m.mangler_xi(X_RUN, HALF_ANGLE, REF_LENGTH)
        xi_half = m.mangler_xi(X_RUN / 2.0, HALF_ANGLE, REF_LENGTH)
        self.assertAlmostEqual(_rel(xi_half, xi_full / 8.0), 0.0, delta=1e-9)
        xi_2l = m.mangler_xi(X_RUN, HALF_ANGLE, 2.0 * REF_LENGTH)
        self.assertAlmostEqual(_rel(xi_2l, xi_full / 4.0), 0.0, delta=1e-12)

    # Step 2: coordinate mapping traverse.
    def test_transformed_normal_coordinate_anchor_and_inverse(self):
        """Step 2 coordinate mapping: transformed_normal_coordinate(2.0,
        5.0e-3, 5.0, 1.0) returns ybar = 8.748866353e-04 m at the flat-plate
        layer top, the inverse map y = ybar*L/r0 round trips within float
        noise, and the wall y = 0 maps to ybar = 0 exactly."""
        ybar = m.transformed_normal_coordinate(
            X_RUN, 5.0e-3, HALF_ANGLE, REF_LENGTH)
        self.assertAlmostEqual(_rel(ybar, 8.748866353e-04), 0.0, delta=1e-6)
        r0 = m.cone_radius(X_RUN, HALF_ANGLE)
        y_back = ybar * REF_LENGTH / r0
        self.assertAlmostEqual(_rel(y_back, 5.0e-3), 0.0, delta=1e-12)
        self.assertEqual(
            m.transformed_normal_coordinate(X_RUN, 0.0, HALF_ANGLE,
                                            REF_LENGTH),
            0.0)

    def test_powerlaw_mangler_xi_cylinder_closed_form(self):
        """Step 2 coordinate mapping: the slender power-law body r0 = 0.1 m
        at exponent 0 is the cylinder and its Mangler xi is the closed form
        amplitude**2*x/(L**2) = 2.00000000e-02 m at the worked station."""
        xi = m.powerlaw_mangler_xi(X_RUN, 0.1, 0.0, REF_LENGTH)
        self.assertAlmostEqual(_rel(xi, 2.00000000e-02), 0.0, delta=1e-12)

    def test_powerlaw_mangler_xi_half_power_body(self):
        """Step 2 coordinate mapping: the slender body r0 = 0.05*x**0.5 has
        Mangler xi = 5.00000000e-03 m at x = 2.0 m from the power-law
        closed form amplitude**2*x**(2n+1)/((2n+1)*L**2)."""
        xi = m.powerlaw_mangler_xi(X_RUN, 0.05, 0.5, REF_LENGTH)
        self.assertAlmostEqual(_rel(xi, 5.00000000e-03), 0.0, delta=1e-12)

    def test_powerlaw_mangler_xi_cone_identity(self):
        """Step 2 coordinate mapping: the cone is the exponent-1 power-law
        body with amplitude tan(alpha), so powerlaw_mangler_xi(x,
        tan(5 deg), 1.0, L) reproduces mangler_xi(x, 5.0, L) exactly."""
        xi_cone = m.mangler_xi(X_RUN, HALF_ANGLE, REF_LENGTH)
        xi_power = m.powerlaw_mangler_xi(
            X_RUN, math.tan(math.radians(HALF_ANGLE)), 1.0, REF_LENGTH)
        self.assertAlmostEqual(_rel(xi_power, xi_cone), 0.0, delta=1e-12)

    # Step 3: flat-plate baseline consumption.
    def test_flat_plate_baseline_values_consumed(self):
        """Step 3 baseline consumption: the worked example takes the sibling
        boundary-layer-theory flat-plate values at Re_x = 4.0e6 (cf 3.32e-4,
        wall shear 0.183015 Pa, 99-percent 5.0e-3 m, displacement 1.7208e-3
        m, momentum 6.64e-4 m) as inputs; the cone functions never derive
        them, they are passed in as arguments."""
        re_x = U_E * X_RUN / NU_AIR
        self.assertAlmostEqual(_rel(re_x, 4.0e6), 0.0, delta=1e-12)
        self.assertAlmostEqual(
            _rel(m.BLASIUS_CF_COEFF / math.sqrt(re_x), CF_FLAT),
            0.0, delta=1e-12)
        self.assertAlmostEqual(
            _rel(m.BLASIUS_TAU_COEFF * RHO_AIR * U_E ** 2 / math.sqrt(re_x),
                 TAU_FLAT),
            0.0, delta=1e-12)
        self.assertAlmostEqual(
            _rel(m.BLASIUS_DELTA_COEFF * X_RUN / math.sqrt(re_x),
                 DELTA_FLAT),
            0.0, delta=1e-12)
        self.assertAlmostEqual(
            _rel(m.BLASIUS_DSTAR_COEFF * X_RUN / math.sqrt(re_x),
                 DELTA_STAR_FLAT),
            0.0, delta=1e-12)
        self.assertAlmostEqual(
            _rel(m.BLASIUS_THETA_COEFF * X_RUN / math.sqrt(re_x),
                 THETA_FLAT),
            0.0, delta=1e-12)

    # Step 4: cone skin friction and wall shear (sqrt-3 cone factor).
    def test_cone_skin_friction_anchor_value(self):
        """Step 4 cone skin friction: cone_skin_friction(3.32e-4) returns
        5.750408681e-04 at the worked station, inside the 4.0e-4 to 8.0e-4
        magnitude band of the laminar cone signature."""
        cf_cone = m.cone_skin_friction(CF_FLAT)
        self.assertAlmostEqual(_rel(cf_cone, 5.750408681e-04), 0.0,
                               delta=1e-9)
        self.assertGreater(cf_cone, 4.0e-4)
        self.assertLess(cf_cone, 8.0e-4)

    def test_cone_skin_friction_sqrt3_ratio(self):
        """Step 4 cone skin friction: the cone-to-plate skin-friction ratio
        at the same running length is the sqrt-3 cone factor, exactly
        SQRT3 = 1.7320508075688772, the laminar Mangler closed form."""
        cf_cone = m.cone_skin_friction(CF_FLAT)
        self.assertAlmostEqual(_rel(cf_cone / CF_FLAT, m.SQRT3), 0.0,
                               delta=1e-12)
        self.assertAlmostEqual(_rel(cf_cone / CF_FLAT, math.sqrt(3.0)),
                               0.0, delta=1e-12)

    def test_cone_wall_shear_anchor_value(self):
        """Step 4 cone wall shear: cone_wall_shear(0.183015) returns the
        3.169912785e-01 Pa cone wall shear at the worked station, the
        sqrt-3 cone factor on the flat-plate wall shear at the same running
        length and edge velocity."""
        tau_cone = m.cone_wall_shear(TAU_FLAT)
        self.assertAlmostEqual(_rel(tau_cone, 3.169912785e-01), 0.0,
                               delta=1e-6)
        self.assertAlmostEqual(_rel(tau_cone / TAU_FLAT, m.SQRT3), 0.0,
                               delta=1e-12)

    def test_wall_shear_and_cf_ratio_consistency(self):
        """Step 4 cone wall shear: the wall-shear ratio equals the
        skin-friction ratio (both the sqrt-3 cone factor) because the shear
        and the coefficient share the 0.5*rho*u_e**2 normalization."""
        tau_ratio = m.cone_wall_shear(TAU_FLAT) / TAU_FLAT
        cf_ratio = m.cone_skin_friction(CF_FLAT) / CF_FLAT
        self.assertAlmostEqual(_rel(tau_ratio, cf_ratio), 0.0, delta=1e-9)
        self.assertAlmostEqual(_rel(tau_ratio, m.SQRT3), 0.0, delta=1e-9)

    # Step 5: cone thicknesses (inverse sqrt-3 factor).
    def test_cone_boundary_layer_thickness_anchor(self):
        """Step 5 cone thickness: cone_boundary_layer_thickness(5.0e-3)
        returns 2.886751346e-03 m, between 2.0e-3 and 3.5e-3 m and strictly
        below the 5.0e-3 m flat-plate layer at the same running length: the
        thinner higher-shear cone layer."""
        delta_cone = m.cone_boundary_layer_thickness(DELTA_FLAT)
        self.assertAlmostEqual(_rel(delta_cone, 2.886751346e-03), 0.0,
                               delta=1e-9)
        self.assertGreater(delta_cone, 2.0e-3)
        self.assertLess(delta_cone, 3.5e-3)
        self.assertLess(delta_cone, DELTA_FLAT)

    def test_cone_thickness_inverse_sqrt3_ratio(self):
        """Step 5 cone thickness: the cone-to-plate 99-percent thickness
        ratio at the same running length is 1/sqrt(3), the INV_SQRT3 =
        0.5773502691896258 laminar cone factor."""
        ratio = (m.cone_boundary_layer_thickness(DELTA_FLAT)
                 / DELTA_FLAT)
        self.assertAlmostEqual(_rel(ratio, m.INV_SQRT3), 0.0, delta=1e-12)

    def test_cone_displacement_thickness_anchor(self):
        """Step 5 cone thickness: cone_displacement_thickness(1.7208e-3)
        returns 9.935043432e-04 m, the inverse sqrt-3 factor on the
        flat-plate displacement thickness at the same running length."""
        dstar_cone = m.cone_displacement_thickness(DELTA_STAR_FLAT)
        self.assertAlmostEqual(_rel(dstar_cone, 9.935043432e-04), 0.0,
                               delta=1e-9)
        self.assertAlmostEqual(
            _rel(dstar_cone / DELTA_STAR_FLAT, m.INV_SQRT3), 0.0,
            delta=1e-12)

    def test_cone_momentum_thickness_anchor(self):
        """Step 5 cone thickness: cone_momentum_thickness(6.64e-4) returns
        3.833605787e-04 m, the inverse sqrt-3 factor on the flat-plate
        momentum thickness at the same running length."""
        theta_cone = m.cone_momentum_thickness(THETA_FLAT)
        self.assertAlmostEqual(_rel(theta_cone, 3.833605787e-04), 0.0,
                               delta=1e-9)
        self.assertAlmostEqual(
            _rel(theta_cone / THETA_FLAT, m.INV_SQRT3), 0.0, delta=1e-12)

    # Step 6: shape factor preservation.
    def test_shape_factor_preserved_by_transform(self):
        """Step 6 shape factor: the Mangler transformation scales the cone
        layer but does not reshape it, so H_cone = delta*_cone/theta_cone =
        2.591566265 equals H_flat = 1.7208/0.664 on the Blasius baseline."""
        h_cone = (m.cone_displacement_thickness(DELTA_STAR_FLAT)
                  / m.cone_momentum_thickness(THETA_FLAT))
        self.assertAlmostEqual(_rel(h_cone, 2.591566265), 0.0, delta=1e-9)
        self.assertAlmostEqual(_rel(h_cone, 1.7208 / 0.664), 0.0,
                               delta=1e-9)

    # Step 7: Blasius station scaling of the equivalent 2-D layer.
    def test_mangler_shear_pipeline_closes_on_closed_form(self):
        """Step 7 station scaling: with the equivalent 2-D length xi and the
        plane-to-physical shear scaling r0/L, the composed pipeline
        (r0/L)*blasius_cf_at_station(cf_flat, x, xi) equals the direct
        cone_skin_friction(cf_flat) closed form within float noise: the
        sqrt-3 cone factor is the composition of the Blasius 1/sqrt(xi)
        decay and the Mangler radius ratio."""
        xi = m.mangler_xi(X_RUN, HALF_ANGLE, REF_LENGTH)
        r0 = m.cone_radius(X_RUN, HALF_ANGLE)
        cf_2d = m.blasius_cf_at_station(CF_FLAT, X_RUN, xi)
        pipeline = (r0 / REF_LENGTH) * cf_2d
        direct = m.cone_skin_friction(CF_FLAT)
        self.assertAlmostEqual(_rel(pipeline, direct), 0.0, delta=1e-9)
        self.assertAlmostEqual(_rel(pipeline, 5.750408681e-04), 0.0,
                               delta=1e-9)

    def test_mangler_thickness_pipeline_closes_on_closed_form(self):
        """Step 7 station scaling: with the plane-to-physical thickness
        scaling L/r0, the composed pipeline (L/r0)*blasius_delta_at_station
        (delta_flat, x, xi) equals the direct
        cone_boundary_layer_thickness(delta_flat) closed form within float
        noise."""
        xi = m.mangler_xi(X_RUN, HALF_ANGLE, REF_LENGTH)
        r0 = m.cone_radius(X_RUN, HALF_ANGLE)
        delta_2d = m.blasius_delta_at_station(DELTA_FLAT, X_RUN, xi)
        pipeline = (REF_LENGTH / r0) * delta_2d
        direct = m.cone_boundary_layer_thickness(DELTA_FLAT)
        self.assertAlmostEqual(_rel(pipeline, direct), 0.0, delta=1e-9)
        self.assertAlmostEqual(_rel(pipeline, 2.886751346e-03), 0.0,
                               delta=1e-9)

    def test_blasius_cf_station_scaling_helper(self):
        """Step 7 station scaling: blasius_cf_at_station(3.32e-4, 2.0, 4.0)
        returns 2.3475945135e-04 (local Cf decays as 1/sqrt(x), so the
        doubled station carries cf/sqrt(2)) with no Blasius constant inside
        the helper."""
        cf_4 = m.blasius_cf_at_station(CF_FLAT, X_RUN, 2.0 * X_RUN)
        self.assertAlmostEqual(_rel(cf_4, 2.3475945135e-04), 0.0,
                               delta=1e-9)
        self.assertAlmostEqual(_rel(cf_4, CF_FLAT / math.sqrt(2.0)), 0.0,
                               delta=1e-12)

    def test_blasius_delta_station_scaling_helper(self):
        """Step 7 station scaling: blasius_delta_at_station(5.0e-3, 2.0,
        4.0) returns delta*sqrt(2) (the 99-percent thickness grows as
        sqrt(x)) with no Blasius constant inside the helper."""
        delta_4 = m.blasius_delta_at_station(DELTA_FLAT, X_RUN,
                                             2.0 * X_RUN)
        self.assertAlmostEqual(_rel(delta_4, DELTA_FLAT * math.sqrt(2.0)),
                               0.0, delta=1e-12)

    def test_station_helpers_round_trip(self):
        """Step 7 station scaling: both Blasius station helpers round trip
        over (x1, x2) and back to the starting value within float noise."""
        cf_rt = m.blasius_cf_at_station(
            m.blasius_cf_at_station(CF_FLAT, X_RUN, 4.0), 4.0, X_RUN)
        self.assertAlmostEqual(_rel(cf_rt, CF_FLAT), 0.0, delta=1e-12)
        delta_rt = m.blasius_delta_at_station(
            m.blasius_delta_at_station(DELTA_FLAT, X_RUN, 4.0), 4.0,
            X_RUN)
        self.assertAlmostEqual(_rel(delta_rt, DELTA_FLAT), 0.0,
                               delta=1e-12)

    # Step 8: momentum-integral closure and determinism.
    def test_momentum_integral_closure_worked_station(self):
        """Step 8 momentum-integral closure: the axisymmetric zero-pressure-
        gradient balance d(theta_cone*r0)/dx = r0*Cf,cone/2 is satisfied
        identically by the sqrt-3 (shear and Cf) and inverse sqrt-3
        (thickness) cone factor pair; the closed-form ratio is 1 at the
        worked station. The reversed pair (both factors sqrt-3) would fail
        this integral by a factor of 3."""
        tana = math.tan(math.radians(HALF_ANGLE))
        nu = NU_AIR
        ue = U_E
        x = X_RUN
        lhs = ((0.664 / m.SQRT3) * tana * math.sqrt(nu / ue) * 1.5
               * math.sqrt(x))
        rhs = (x * tana * (m.SQRT3 * 0.664
                           * math.sqrt(nu / (ue * x))) / 2.0)
        self.assertAlmostEqual(_rel(lhs, rhs), 0.0, delta=1e-9)
        # The reversed pair fails by a factor of 3: thickness ratio must be
        # the inverse sqrt-3 factor, not sqrt-3, for the balance to close.
        lhs_bad = (0.664 * m.SQRT3) * tana * math.sqrt(nu / ue) * 1.5 \
            * math.sqrt(x)
        self.assertAlmostEqual(_rel(lhs_bad, 3.0 * rhs), 0.0, delta=1e-9)

    def test_deterministic_repeat_calls(self):
        """Step 8 determinism: two identical calls return bitwise-equal
        floats; the closed-form module has no iteration, no random state
        and no ODE or quadrature call, so the Mangler values never vary
        between runs or interpreters."""
        a1 = m.cone_skin_friction(CF_FLAT)
        a2 = m.cone_skin_friction(CF_FLAT)
        self.assertEqual(a1, a2)
        self.assertEqual(m.mangler_xi(X_RUN, HALF_ANGLE, REF_LENGTH),
                         m.mangler_xi(X_RUN, HALF_ANGLE, REF_LENGTH))

    def test_module_imports_math_only(self):
        """Step 8 module hygiene: the logic source imports math only, with
        no numpy, scipy, random or loop body, keeping the contract test
        offline and deterministic."""
        with open(_SOURCE, "r", encoding="utf-8") as fh:
            src = fh.read()
        self.assertIn("import math", src)
        self.assertNotIn("numpy", src)
        self.assertNotIn("scipy", src)
        self.assertNotIn("import random", src)
        self.assertNotIn("while ", src)

    # Input-rejection traverse (ValueErrors).
    def test_valueerror_cone_radius_running_length(self):
        """Input rejection: cone_radius rejects the non-physical running
        lengths x = 0 and x = -1.0 (no surface upstream of the apex)."""
        for bad_x in (0.0, -1.0):
            with self.assertRaises(ValueError):
                m.cone_radius(bad_x, HALF_ANGLE)

    def test_valueerror_cone_radius_and_xi_half_angle(self):
        """Input rejection: the geometry traverse rejects half_angle_deg at
        0 and 90 on cone_radius, mangler_xi and the transformed normal
        coordinate (a degenerate or inverted cone)."""
        for bad_angle in (0.0, 90.0):
            with self.assertRaises(ValueError):
                m.cone_radius(X_RUN, bad_angle)
            with self.assertRaises(ValueError):
                m.mangler_xi(X_RUN, bad_angle, REF_LENGTH)
            with self.assertRaises(ValueError):
                m.transformed_normal_coordinate(X_RUN, 1.0e-3, bad_angle,
                                                REF_LENGTH)

    def test_valueerror_mangler_xi_and_ybar_reference_length(self):
        """Input rejection: mangler_xi and the transformed normal coordinate
        reject ref_length at 0 and -1.0 (a zero or negative Mangler
        reference length inverts the mapping)."""
        for bad_l in (0.0, -1.0):
            with self.assertRaises(ValueError):
                m.mangler_xi(X_RUN, HALF_ANGLE, bad_l)
            with self.assertRaises(ValueError):
                m.transformed_normal_coordinate(X_RUN, 1.0e-3, HALF_ANGLE,
                                                bad_l)

    def test_valueerror_transformed_normal_coordinate_negative_y(self):
        """Input rejection: the coordinate mapping rejects the negative
        normal distance y = -1e-6 (the layer lives above the surface)."""
        with self.assertRaises(ValueError):
            m.transformed_normal_coordinate(X_RUN, -1.0e-6, HALF_ANGLE,
                                            REF_LENGTH)

    def test_valueerror_powerlaw_mangler_xi_inputs(self):
        """Input rejection: powerlaw_mangler_xi rejects amplitude 0,
        exponent -0.5, x at 0 and ref_length at 0 and -1.0 on the slender
        power-law body family."""
        with self.assertRaises(ValueError):
            m.powerlaw_mangler_xi(X_RUN, 0.0, 0.5, REF_LENGTH)
        with self.assertRaises(ValueError):
            m.powerlaw_mangler_xi(X_RUN, 0.1, -0.5, REF_LENGTH)
        with self.assertRaises(ValueError):
            m.powerlaw_mangler_xi(0.0, 0.1, 0.5, REF_LENGTH)
        for bad_l in (0.0, -1.0):
            with self.assertRaises(ValueError):
                m.powerlaw_mangler_xi(X_RUN, 0.1, 0.5, bad_l)

    def test_valueerror_blasius_station_helpers(self):
        """Input rejection: both Blasius station-scaling helpers reject a
        zero baseline value and zero stations x1 or x2 (no layer at a
        degenerate station)."""
        for bad in (0.0,):
            with self.assertRaises(ValueError):
                m.blasius_cf_at_station(bad, X_RUN, 4.0)
            with self.assertRaises(ValueError):
                m.blasius_cf_at_station(CF_FLAT, bad, 4.0)
            with self.assertRaises(ValueError):
                m.blasius_cf_at_station(CF_FLAT, X_RUN, bad)
            with self.assertRaises(ValueError):
                m.blasius_delta_at_station(bad, X_RUN, 4.0)
            with self.assertRaises(ValueError):
                m.blasius_delta_at_station(DELTA_FLAT, bad, 4.0)
            with self.assertRaises(ValueError):
                m.blasius_delta_at_station(DELTA_FLAT, X_RUN, bad)

    def test_valueerror_cone_skin_friction_inputs(self):
        """Input rejection: cone_skin_friction rejects the flat-plate
        baseline skin friction at 0 and -1e-4 (no negative or zero drag
        coefficient on the plate baseline)."""
        for bad_cf in (0.0, -1.0e-4):
            with self.assertRaises(ValueError):
                m.cone_skin_friction(bad_cf)

    def test_valueerror_cone_wall_shear_input(self):
        """Input rejection: cone_wall_shear rejects the flat-plate wall
        shear at 0 (a zero-shear plate baseline gives no cone shear)."""
        with self.assertRaises(ValueError):
            m.cone_wall_shear(0.0)

    def test_valueerror_cone_thickness_functions(self):
        """Input rejection: the cone thickness functions reject the
        non-physical flat-plate baselines delta_flat at -1e-3,
        delta_star_flat at 0 and theta_flat at -1e-5."""
        with self.assertRaises(ValueError):
            m.cone_boundary_layer_thickness(-1.0e-3)
        with self.assertRaises(ValueError):
            m.cone_displacement_thickness(0.0)
        with self.assertRaises(ValueError):
            m.cone_momentum_thickness(-1.0e-5)


if __name__ == "__main__":
    unittest.main()
