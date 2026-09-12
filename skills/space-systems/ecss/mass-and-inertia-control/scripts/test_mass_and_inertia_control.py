import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from mass_and_inertia_control_logic import (
    validate_mass_entry,
    compute_mass_budget,
    compute_center_of_mass,
    compute_moments_of_inertia,
    check_mass_margin,
    roll_up_subsystems,
    generate_sms_drd_fields,
    PHASE_MARGIN_REQUIREMENTS,
)


def _entry(name='item', cbe=10.0, allocated=12.0, pos=(0.0, 0.0, 0.0)):
    return {
        'name': name,
        'mass_cbe_kg': cbe,
        'mass_allocated_kg': allocated,
        'position': pos,
    }


class TestValidateMassEntry(unittest.TestCase):

    def test_valid_entry_returns_same_object(self):
        e = _entry()
        self.assertIs(validate_mass_entry(e), e)

    def test_missing_name_field_raises(self):
        e = {'mass_cbe_kg': 5.0, 'mass_allocated_kg': 6.0, 'position': (0, 0, 0)}
        with self.assertRaises(ValueError):
            validate_mass_entry(e)

    def test_negative_cbe_raises(self):
        with self.assertRaises(ValueError):
            validate_mass_entry(_entry(cbe=-1.0))

    def test_zero_allocated_raises(self):
        with self.assertRaises(ValueError):
            validate_mass_entry(_entry(allocated=0.0))

    def test_negative_allocated_raises(self):
        with self.assertRaises(ValueError):
            validate_mass_entry(_entry(allocated=-5.0))

    def test_position_wrong_length_raises(self):
        with self.assertRaises(ValueError):
            validate_mass_entry(_entry(pos=(0.0, 0.0)))

    def test_empty_name_raises(self):
        with self.assertRaises(ValueError):
            validate_mass_entry(_entry(name='   '))

    def test_non_numeric_position_raises(self):
        with self.assertRaises(ValueError):
            validate_mass_entry(_entry(pos=(0.0, 'a', 0.0)))

    def test_zero_cbe_is_valid(self):
        e = _entry(cbe=0.0)
        self.assertIs(validate_mass_entry(e), e)


class TestComputeMassBudget(unittest.TestCase):

    def test_single_entry_totals(self):
        result = compute_mass_budget([_entry(cbe=10.0, allocated=12.0)])
        self.assertAlmostEqual(result['total_cbe_kg'], 10.0)
        self.assertAlmostEqual(result['total_allocated_kg'], 12.0)
        self.assertAlmostEqual(result['margin_kg'], 2.0)
        self.assertAlmostEqual(result['margin_pct'], 100.0 * 2.0 / 12.0)

    def test_multiple_entries_sum_correctly(self):
        entries = [_entry('a', 10.0, 12.0), _entry('b', 5.0, 8.0)]
        result = compute_mass_budget(entries)
        self.assertAlmostEqual(result['total_cbe_kg'], 15.0)
        self.assertAlmostEqual(result['total_allocated_kg'], 20.0)
        self.assertAlmostEqual(result['margin_kg'], 5.0)

    def test_exceedance_gives_negative_margin(self):
        result = compute_mass_budget([_entry(cbe=15.0, allocated=10.0)])
        self.assertLess(result['margin_kg'], 0.0)
        self.assertLess(result['margin_pct'], 0.0)

    def test_empty_entries_raises(self):
        with self.assertRaises(ValueError):
            compute_mass_budget([])

    def test_margin_pct_exact_zero_for_tight_budget(self):
        result = compute_mass_budget([_entry(cbe=10.0, allocated=10.0)])
        self.assertAlmostEqual(result['margin_pct'], 0.0)


class TestComputeCenterOfMass(unittest.TestCase):

    def test_single_entry_at_origin(self):
        cx, cy, cz = compute_center_of_mass([_entry(cbe=5.0, pos=(0.0, 0.0, 0.0))])
        self.assertAlmostEqual(cx, 0.0)
        self.assertAlmostEqual(cy, 0.0)
        self.assertAlmostEqual(cz, 0.0)

    def test_two_equal_masses_symmetric_about_origin(self):
        entries = [
            _entry('L', 5.0, 6.0, pos=(-1.0, 0.0, 0.0)),
            _entry('R', 5.0, 6.0, pos=(1.0, 0.0, 0.0)),
        ]
        cx, cy, cz = compute_center_of_mass(entries)
        self.assertAlmostEqual(cx, 0.0)
        self.assertAlmostEqual(cy, 0.0)
        self.assertAlmostEqual(cz, 0.0)

    def test_weighted_com_calculation(self):
        # 1 kg at x=0, 3 kg at x=4 → weighted CoM at x=3
        entries = [
            _entry('a', 1.0, 2.0, pos=(0.0, 0.0, 0.0)),
            _entry('b', 3.0, 4.0, pos=(4.0, 0.0, 0.0)),
        ]
        cx, cy, cz = compute_center_of_mass(entries)
        self.assertAlmostEqual(cx, 3.0)
        self.assertAlmostEqual(cy, 0.0)
        self.assertAlmostEqual(cz, 0.0)

    def test_zero_total_mass_raises(self):
        with self.assertRaises(ValueError):
            compute_center_of_mass([_entry(cbe=0.0)])

    def test_com_uses_cbe_not_allocated(self):
        # Asymmetric CBE masses but symmetric allocations
        entries = [
            _entry('a', 2.0, 5.0, pos=(0.0, 0.0, 0.0)),
            _entry('b', 8.0, 5.0, pos=(5.0, 0.0, 0.0)),
        ]
        cx, _, _ = compute_center_of_mass(entries)
        self.assertAlmostEqual(cx, 4.0)  # 2*0 + 8*5 / 10 = 4.0


class TestComputeMomentsOfInertia(unittest.TestCase):

    def test_mass_at_origin_gives_zero_moi(self):
        Ixx, Iyy, Izz = compute_moments_of_inertia(
            [_entry(cbe=5.0, pos=(0.0, 0.0, 0.0))]
        )
        self.assertAlmostEqual(Ixx, 0.0)
        self.assertAlmostEqual(Iyy, 0.0)
        self.assertAlmostEqual(Izz, 0.0)

    def test_point_mass_on_y_axis(self):
        # 2 kg at (0, 1, 0): Ixx=2*(1²+0²)=2, Iyy=2*(0+0)=0, Izz=2*(0+1²)=2
        Ixx, Iyy, Izz = compute_moments_of_inertia(
            [_entry(cbe=2.0, pos=(0.0, 1.0, 0.0))]
        )
        self.assertAlmostEqual(Ixx, 2.0)
        self.assertAlmostEqual(Iyy, 0.0)
        self.assertAlmostEqual(Izz, 2.0)

    def test_point_mass_on_z_axis(self):
        # 3 kg at (0, 0, 2): Ixx=3*4=12, Iyy=3*4=12, Izz=0
        Ixx, Iyy, Izz = compute_moments_of_inertia(
            [_entry(cbe=3.0, pos=(0.0, 0.0, 2.0))]
        )
        self.assertAlmostEqual(Ixx, 12.0)
        self.assertAlmostEqual(Iyy, 12.0)
        self.assertAlmostEqual(Izz, 0.0)

    def test_custom_reference_point_collocated_gives_zero(self):
        # Mass at (1, 2, 3), reference at (1, 2, 3) → all MoI zero
        Ixx, Iyy, Izz = compute_moments_of_inertia(
            [_entry(cbe=4.0, pos=(1.0, 2.0, 3.0))],
            reference_point=(1.0, 2.0, 3.0),
        )
        self.assertAlmostEqual(Ixx, 0.0)
        self.assertAlmostEqual(Iyy, 0.0)
        self.assertAlmostEqual(Izz, 0.0)

    def test_two_masses_additive(self):
        # 1 kg at (0,1,0) and 1 kg at (0,-1,0): each gives Ixx=1, total Ixx=2
        entries = [
            _entry('a', 1.0, 2.0, pos=(0.0, 1.0, 0.0)),
            _entry('b', 1.0, 2.0, pos=(0.0, -1.0, 0.0)),
        ]
        Ixx, _, _ = compute_moments_of_inertia(entries)
        self.assertAlmostEqual(Ixx, 2.0)

    def test_empty_entries_raises(self):
        with self.assertRaises(ValueError):
            compute_moments_of_inertia([])


class TestCheckMassMargin(unittest.TestCase):

    def test_phase_a_compliant_at_exactly_20pct(self):
        result = check_mass_margin(80.0, 100.0, 'A')
        self.assertTrue(result['compliant'])
        self.assertAlmostEqual(result['margin_pct'], 20.0)
        self.assertAlmostEqual(result['min_required_pct'], 20.0)

    def test_phase_b_non_compliant_at_10pct(self):
        result = check_mass_margin(90.0, 100.0, 'B')
        self.assertFalse(result['compliant'])

    def test_phase_c_compliant_above_threshold(self):
        result = check_mass_margin(85.0, 100.0, 'C')
        self.assertTrue(result['compliant'])

    def test_phase_d_exactly_at_limit_compliant(self):
        result = check_mass_margin(95.0, 100.0, 'D')
        self.assertTrue(result['compliant'])
        self.assertAlmostEqual(result['margin_pct'], 5.0)

    def test_phase_d_below_limit_non_compliant(self):
        result = check_mass_margin(96.0, 100.0, 'D')
        self.assertFalse(result['compliant'])

    def test_unknown_phase_raises(self):
        with self.assertRaises(ValueError):
            check_mass_margin(80.0, 100.0, 'Z')

    def test_lowercase_phase_accepted(self):
        result = check_mass_margin(75.0, 100.0, 'a')
        self.assertAlmostEqual(result['min_required_pct'], 20.0)

    def test_non_positive_allocated_raises(self):
        with self.assertRaises(ValueError):
            check_mass_margin(10.0, 0.0, 'B')

    def test_negative_cbe_raises(self):
        with self.assertRaises(ValueError):
            check_mass_margin(-1.0, 100.0, 'C')

    def test_all_phase_thresholds_present(self):
        self.assertEqual(PHASE_MARGIN_REQUIREMENTS['A'], 20.0)
        self.assertEqual(PHASE_MARGIN_REQUIREMENTS['B'], 15.0)
        self.assertEqual(PHASE_MARGIN_REQUIREMENTS['C'], 10.0)
        self.assertEqual(PHASE_MARGIN_REQUIREMENTS['D'], 5.0)


class TestRollUpSubsystems(unittest.TestCase):

    def test_two_subsystems_roll_up_correctly(self):
        subs = [
            {'name': 'structure', 'cbe_kg': 50.0, 'allocated_kg': 60.0},
            {'name': 'propulsion', 'cbe_kg': 30.0, 'allocated_kg': 40.0},
        ]
        result = roll_up_subsystems(subs)
        self.assertAlmostEqual(result['total_cbe_kg'], 80.0)
        self.assertAlmostEqual(result['total_allocated_kg'], 100.0)
        self.assertAlmostEqual(result['margin_kg'], 20.0)
        self.assertEqual(result['subsystem_count'], 2)

    def test_empty_list_raises(self):
        with self.assertRaises(ValueError):
            roll_up_subsystems([])

    def test_missing_field_raises(self):
        with self.assertRaises(ValueError):
            roll_up_subsystems([{'name': 'x', 'cbe_kg': 10.0}])

    def test_negative_subsystem_cbe_raises(self):
        with self.assertRaises(ValueError):
            roll_up_subsystems(
                [{'name': 'x', 'cbe_kg': -1.0, 'allocated_kg': 5.0}]
            )


class TestGenerateSmsDrdFields(unittest.TestCase):

    def test_full_sms_drd_output_keys_present(self):
        entries = [
            _entry('panel', 20.0, 25.0, pos=(0.5, 0.0, 0.0)),
            _entry('tank', 30.0, 35.0, pos=(-0.5, 0.0, 0.0)),
        ]
        result = generate_sms_drd_fields(entries, 'C')
        for key in [
            'total_cbe_kg', 'total_allocated_kg', 'margin_kg', 'margin_pct',
            'phase', 'phase_margin_required_pct', 'mass_margin_compliant',
            'center_of_mass_m', 'Ixx_kg_m2', 'Iyy_kg_m2', 'Izz_kg_m2',
            'reference_point_m',
        ]:
            self.assertIn(key, result, f"Missing key: {key}")

    def test_sms_drd_phase_and_threshold(self):
        entries = [_entry(cbe=80.0, allocated=100.0, pos=(0.0, 0.0, 0.0))]
        result = generate_sms_drd_fields(entries, 'A')
        self.assertEqual(result['phase'], 'A')
        self.assertAlmostEqual(result['phase_margin_required_pct'], 20.0)
        self.assertTrue(result['mass_margin_compliant'])

    def test_sms_drd_reference_point_carried_through(self):
        entries = [_entry(cbe=10.0, allocated=12.0, pos=(1.0, 2.0, 3.0))]
        ref = (1.0, 2.0, 3.0)
        result = generate_sms_drd_fields(entries, 'D', reference_point=ref)
        self.assertEqual(result['reference_point_m'], ref)
        self.assertAlmostEqual(result['Ixx_kg_m2'], 0.0)


if __name__ == '__main__':
    unittest.main()
