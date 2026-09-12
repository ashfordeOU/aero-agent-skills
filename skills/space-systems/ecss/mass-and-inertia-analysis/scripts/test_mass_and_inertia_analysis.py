import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from mass_and_inertia_analysis_logic import (
    compute_total_mass,
    compute_center_of_mass,
    compute_inertia_tensor,
    check_mass_budget,
    mass_fraction,
    MassInertiaError,
)


def _zero_inertia():
    return [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]]


def _diag_inertia(ixx, iyy, izz):
    return [
        [ixx, 0.0, 0.0],
        [0.0, iyy, 0.0],
        [0.0, 0.0, izz],
    ]


def _make(name, mass, centroid, inertia=None):
    return {"name": name, "mass": mass, "centroid": centroid,
            "inertia": inertia if inertia is not None else _zero_inertia()}


# ---------------------------------------------------------------------------
# Total mass
# ---------------------------------------------------------------------------

class TestComputeTotalMass(unittest.TestCase):
    def test_single_component(self):
        self.assertAlmostEqual(compute_total_mass([_make("A", 5.0, [0, 0, 0])]), 5.0)

    def test_multiple_components_sum(self):
        cs = [_make("A", 3.0, [0, 0, 0]), _make("B", 7.0, [1, 0, 0])]
        self.assertAlmostEqual(compute_total_mass(cs), 10.0)

    def test_empty_list_raises(self):
        with self.assertRaises(MassInertiaError):
            compute_total_mass([])

    def test_zero_mass_raises(self):
        with self.assertRaises(MassInertiaError):
            compute_total_mass([_make("bad", 0.0, [0, 0, 0])])

    def test_negative_mass_raises(self):
        with self.assertRaises(MassInertiaError):
            compute_total_mass([_make("neg", -1.0, [0, 0, 0])])


# ---------------------------------------------------------------------------
# Center of mass
# ---------------------------------------------------------------------------

class TestComputeCenterOfMass(unittest.TestCase):
    def test_single_component_returns_its_centroid(self):
        cm = compute_center_of_mass([_make("X", 2.0, [1.0, 2.0, 3.0])])
        self.assertAlmostEqual(cm[0], 1.0)
        self.assertAlmostEqual(cm[1], 2.0)
        self.assertAlmostEqual(cm[2], 3.0)

    def test_two_equal_masses_midpoint(self):
        cs = [_make("A", 1.0, [0.0, 0.0, 0.0]), _make("B", 1.0, [2.0, 0.0, 0.0])]
        cm = compute_center_of_mass(cs)
        self.assertAlmostEqual(cm[0], 1.0)
        self.assertAlmostEqual(cm[1], 0.0)
        self.assertAlmostEqual(cm[2], 0.0)

    def test_weighted_center_of_mass(self):
        # mass 3 at x=0, mass 1 at x=4 → CoM at x=1
        cs = [_make("A", 3.0, [0.0, 0.0, 0.0]), _make("B", 1.0, [4.0, 0.0, 0.0])]
        cm = compute_center_of_mass(cs)
        self.assertAlmostEqual(cm[0], 1.0)

    def test_center_of_mass_at_origin(self):
        cs = [_make("A", 2.0, [-1.0, 0.0, 0.0]), _make("B", 2.0, [1.0, 0.0, 0.0])]
        cm = compute_center_of_mass(cs)
        self.assertAlmostEqual(cm[0], 0.0)


# ---------------------------------------------------------------------------
# Inertia tensor
# ---------------------------------------------------------------------------

class TestComputeInertiaTensor(unittest.TestCase):
    def test_component_at_reference_no_shift(self):
        I_self = _diag_inertia(10.0, 20.0, 30.0)
        c = [_make("X", 5.0, [0.0, 0.0, 0.0], inertia=I_self)]
        I = compute_inertia_tensor(c, ref_point=[0.0, 0.0, 0.0])
        self.assertAlmostEqual(I[0][0], 10.0)
        self.assertAlmostEqual(I[1][1], 20.0)
        self.assertAlmostEqual(I[2][2], 30.0)
        self.assertAlmostEqual(I[0][1], 0.0)

    def test_parallel_axis_x_displacement(self):
        # Point mass m=2 at x=d=3: Iyy = Izz = m*d^2; Ixx = 0
        m, d = 2.0, 3.0
        c = [_make("pt", m, [d, 0.0, 0.0])]
        I = compute_inertia_tensor(c, ref_point=[0.0, 0.0, 0.0])
        self.assertAlmostEqual(I[0][0], 0.0)
        self.assertAlmostEqual(I[1][1], m * d * d)
        self.assertAlmostEqual(I[2][2], m * d * d)

    def test_parallel_axis_y_displacement(self):
        # Point mass m=1 at y=d=4: Ixx = Izz = m*d^2; Iyy = 0
        m, d = 1.0, 4.0
        c = [_make("pt", m, [0.0, d, 0.0])]
        I = compute_inertia_tensor(c, ref_point=[0.0, 0.0, 0.0])
        self.assertAlmostEqual(I[0][0], m * d * d)
        self.assertAlmostEqual(I[1][1], 0.0)
        self.assertAlmostEqual(I[2][2], m * d * d)

    def test_product_of_inertia_sign(self):
        # Point mass at [a, b, 0]: Ixy_correction = -m*a*b
        m, a, b = 1.0, 2.0, 3.0
        c = [_make("pt", m, [a, b, 0.0])]
        I = compute_inertia_tensor(c, ref_point=[0.0, 0.0, 0.0])
        self.assertAlmostEqual(I[0][1], -m * a * b)
        self.assertAlmostEqual(I[1][0], -m * a * b)

    def test_tensor_symmetry(self):
        cs = [
            _make("A", 2.0, [1.0, 2.0, 3.0], inertia=_diag_inertia(5.0, 6.0, 7.0)),
            _make("B", 3.0, [-1.0, 0.5, 1.0], inertia=_diag_inertia(1.0, 2.0, 3.0)),
        ]
        I = compute_inertia_tensor(cs, ref_point=[0.0, 0.0, 0.0])
        for i in range(3):
            for j in range(3):
                self.assertAlmostEqual(I[i][j], I[j][i], places=10)

    def test_default_ref_point_equals_center_of_mass(self):
        # Two equal masses symmetric about origin: CoM == origin
        cs = [_make("A", 1.0, [1.0, 0.0, 0.0]), _make("B", 1.0, [-1.0, 0.0, 0.0])]
        I_default = compute_inertia_tensor(cs)
        I_at_origin = compute_inertia_tensor(cs, ref_point=[0.0, 0.0, 0.0])
        for i in range(3):
            for j in range(3):
                self.assertAlmostEqual(I_default[i][j], I_at_origin[i][j])

    def test_two_components_additive(self):
        # Each component contributes independently; sum must equal individual sum
        c1 = _make("A", 1.0, [1.0, 0.0, 0.0], inertia=_diag_inertia(2.0, 3.0, 4.0))
        c2 = _make("B", 1.0, [0.0, 1.0, 0.0], inertia=_diag_inertia(5.0, 6.0, 7.0))
        I_both = compute_inertia_tensor([c1, c2], ref_point=[0.0, 0.0, 0.0])
        I_c1 = compute_inertia_tensor([c1], ref_point=[0.0, 0.0, 0.0])
        I_c2 = compute_inertia_tensor([c2], ref_point=[0.0, 0.0, 0.0])
        for i in range(3):
            for j in range(3):
                self.assertAlmostEqual(I_both[i][j], I_c1[i][j] + I_c2[i][j])


# ---------------------------------------------------------------------------
# Mass budget
# ---------------------------------------------------------------------------

class TestCheckMassBudget(unittest.TestCase):
    def test_under_budget_compliant(self):
        r = check_mass_budget(80.0, 100.0)
        self.assertTrue(r["compliant"])
        self.assertAlmostEqual(r["margin"], 20.0)

    def test_exactly_at_budget_compliant(self):
        r = check_mass_budget(100.0, 100.0)
        self.assertTrue(r["compliant"])
        self.assertAlmostEqual(r["margin"], 0.0)

    def test_over_budget_not_compliant(self):
        r = check_mass_budget(110.0, 100.0)
        self.assertFalse(r["compliant"])
        self.assertAlmostEqual(r["margin"], -10.0)

    def test_zero_budget_raises(self):
        with self.assertRaises(MassInertiaError):
            check_mass_budget(5.0, 0.0)

    def test_negative_budget_raises(self):
        with self.assertRaises(MassInertiaError):
            check_mass_budget(5.0, -1.0)


# ---------------------------------------------------------------------------
# Mass fraction
# ---------------------------------------------------------------------------

class TestMassFraction(unittest.TestCase):
    def test_fraction_value(self):
        self.assertAlmostEqual(mass_fraction(30.0, 100.0), 0.3)

    def test_full_mass_gives_one(self):
        self.assertAlmostEqual(mass_fraction(50.0, 50.0), 1.0)

    def test_zero_total_raises(self):
        with self.assertRaises(MassInertiaError):
            mass_fraction(5.0, 0.0)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

class TestValidation(unittest.TestCase):
    def test_missing_inertia_field_raises(self):
        c = [{"name": "X", "mass": 1.0, "centroid": [0, 0, 0]}]
        with self.assertRaises(MassInertiaError):
            compute_total_mass(c)

    def test_missing_centroid_field_raises(self):
        c = [{"name": "X", "mass": 1.0, "inertia": _zero_inertia()}]
        with self.assertRaises(MassInertiaError):
            compute_total_mass(c)

    def test_bad_centroid_length_raises(self):
        c = [_make("X", 1.0, [0, 0])]  # only 2 elements
        with self.assertRaises(MassInertiaError):
            compute_center_of_mass(c)

    def test_bad_inertia_shape_raises(self):
        c = [{"name": "X", "mass": 1.0, "centroid": [0, 0, 0],
              "inertia": [[1, 0], [0, 1]]}]
        with self.assertRaises(MassInertiaError):
            compute_inertia_tensor(c, ref_point=[0, 0, 0])


if __name__ == "__main__":
    unittest.main()
