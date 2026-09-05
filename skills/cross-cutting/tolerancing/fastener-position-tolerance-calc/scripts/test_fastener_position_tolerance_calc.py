"""Contract test for the fastener-position-tolerance-calc leaf
(cross-cutting/tolerancing), ASME Y14.5 fixed and floating fastener
sizing of positional tolerances and clearance holes for mating fastener
patterns.

Each method docstring names the SKILL.md workflow step it exercises: the
step 1 joint input traverse, the step 2 budget traverse for the total
positional tolerance budget from the clearance hole MMC diameter and the
fastener maximum diameter, the step 3 split traverse of the tolerance
split between the two mating members, the step 4 projected zone traverse
for the projected tolerance zone height over the mating thickness, the
step 5 minimum hole traverse for the minimum clearance hole MMC diameter,
the step 6 report bookkeeping of the fastener_report sizing record, and
the step 7 contract test confirmation. Runs offline, deterministic.

python3 scripts/test_fastener_position_tolerance_calc.py
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastener_position_tolerance_calc_logic import (
    floating_fastener_total_tolerance,
    fixed_fastener_total_tolerance,
    split_tolerance,
    minimum_clearance_hole_mmc,
    projected_zone_height,
    fastener_report,
    report_keys,
)

FASTENER_MM = 6.35
HOLE_MM = 6.75
TOTAL_BUDGET = 0.40
MATING_THICKNESS = 12.0


class FastenerBudgetTests(unittest.TestCase):
    """Step 2 budget traverse of the SKILL.md workflow."""

    def test_step2_budget_floating_worked_example(self):
        """Step 2 budget traverse for the floating fastener formula:
        floating_fastener_total_tolerance(6.75, 6.35) must give the total
        positional tolerance budget of 0.40 mm."""
        self.assertAlmostEqual(
            floating_fastener_total_tolerance(HOLE_MM, FASTENER_MM),
            TOTAL_BUDGET, places=6)

    def test_step2_budget_fixed_equals_floating(self):
        """Step 2 budget traverse with the fixed fastener formula must
        return the same total positional tolerance budget as the floating
        case at the same clearance hole MMC diameter and fastener maximum
        diameter."""
        self.assertAlmostEqual(
            fixed_fastener_total_tolerance(HOLE_MM, FASTENER_MM),
            floating_fastener_total_tolerance(HOLE_MM, FASTENER_MM),
            places=6)

    def test_step2_budget_larger_fastener_smaller_budget(self):
        """Step 2 budget traverse scaling: a larger fastener maximum
        diameter at a fixed clearance hole MMC diameter must leave a
        smaller total positional tolerance budget."""
        self.assertLess(
            floating_fastener_total_tolerance(6.75, 6.50),
            floating_fastener_total_tolerance(6.75, 6.35))

    def test_step2_budget_ten_millimeter_joint(self):
        """Step 2 budget traverse on a second joint: hole MMC 8.50 mm
        with a 8.00 mm fastener leaves a 0.50 mm total budget."""
        self.assertAlmostEqual(
            floating_fastener_total_tolerance(8.50, 8.00), 0.50, places=6)


class SplitToleranceTests(unittest.TestCase):
    """Step 3 split traverse of the SKILL.md workflow."""

    def test_step3_split_equal_worked_example(self):
        """Step 3 split traverse, tolerance split of the 0.40 mm total
        into equal shares between the two mating members:
        split_tolerance(0.40) = (0.20, 0.20)."""
        t1, t2 = split_tolerance(TOTAL_BUDGET)
        self.assertAlmostEqual(t1, 0.20, places=6)
        self.assertAlmostEqual(t2, 0.20, places=6)

    def test_step3_split_pair_sums_to_total(self):
        """Step 3 split traverse sum property: the tolerance split pair
        must sum back to the total positional tolerance budget within
        0.01 mm."""
        t1, t2 = split_tolerance(TOTAL_BUDGET)
        self.assertAlmostEqual(t1 + t2, TOTAL_BUDGET, delta=0.01)

    def test_step3_split_unequal_keeps_total(self):
        """Step 3 split traverse with first_share 0.75: the tolerance
        split (0.30, 0.10) keeps the same 0.40 mm total, showing the
        total budget is independent of the split."""
        t1, t2 = split_tolerance(TOTAL_BUDGET, 0.75)
        self.assertAlmostEqual(t1, 0.30, places=6)
        self.assertAlmostEqual(t2, 0.10, places=6)
        self.assertAlmostEqual(t1 + t2, TOTAL_BUDGET, delta=0.01)

    def test_step3_split_unequal_reverse_keeps_total(self):
        """Step 3 split traverse with first_share 0.25: the reversed
        tolerance split (0.10, 0.30) still sums to the total, the
        budget independence of the split on the other side."""
        t1, t2 = split_tolerance(TOTAL_BUDGET, 0.25)
        self.assertAlmostEqual(t1, 0.10, places=6)
        self.assertAlmostEqual(t2, 0.30, places=6)
        self.assertAlmostEqual(t1 + t2, TOTAL_BUDGET, delta=0.01)

    def test_step3_split_three_quarters_budget(self):
        """Step 3 split traverse on a 0.60 mm total with a 0.40 first
        share gives (0.24, 0.36) at two decimals, still summing back."""
        t1, t2 = split_tolerance(0.60, 0.40)
        self.assertAlmostEqual(t1, 0.24, places=6)
        self.assertAlmostEqual(t2, 0.36, places=6)


class ProjectedZoneTests(unittest.TestCase):
    """Step 4 projected zone traverse of the SKILL.md workflow."""

    def test_step4_projected_zone_default_full_thickness(self):
        """Step 4 projected zone traverse: the projected tolerance zone
        height defaults to the full mating thickness,
        projected_zone_height(12.0) = 12.0 mm for the fixed fastener
        case."""
        self.assertAlmostEqual(
            projected_zone_height(MATING_THICKNESS), 12.0, places=6)

    def test_step4_projected_zone_multiplier_variant(self):
        """Step 4 projected zone traverse multiplier variant: a 0.75
        multiplier shortens the zone over the same mating thickness to
        9.0 mm."""
        self.assertAlmostEqual(
            projected_zone_height(MATING_THICKNESS, 0.75), 9.0, places=6)

    def test_step4_projected_zone_larger_stack(self):
        """Step 4 projected zone traverse over a 20 mm mating thickness
        gives a 20.0 mm zone height."""
        self.assertAlmostEqual(
            projected_zone_height(20.0), 20.0, places=6)


class MinimumHoleTests(unittest.TestCase):
    """Step 5 minimum hole traverse of the SKILL.md workflow."""

    def test_step5_minimum_hole_worked_example(self):
        """Step 5 minimum hole traverse: minimum_clearance_hole_mmc(6.35,
        0.25, 0.15) = 6.75 mm, the minimum clearance hole MMC diameter
        for the worked-example fastener and tolerance split."""
        self.assertAlmostEqual(
            minimum_clearance_hole_mmc(FASTENER_MM, 0.25, 0.15),
            HOLE_MM, places=6)

    def test_step5_minimum_hole_equal_split(self):
        """Step 5 minimum hole traverse with the equal tolerance split:
        minimum_clearance_hole_mmc(6.35, 0.20, 0.20) = 6.75 mm, the same
        hole as the worked example."""
        self.assertAlmostEqual(
            minimum_clearance_hole_mmc(FASTENER_MM, 0.20, 0.20),
            HOLE_MM, places=6)

    def test_step5_minimum_hole_inverts_budget_round_trip(self):
        """Step 5 minimum hole traverse round trip: the sized minimum
        clearance hole MMC diameter fed back to the step 2 budget
        traverse must recover the original total positional tolerance
        budget of 0.40 mm, the inverse identity."""
        sized = minimum_clearance_hole_mmc(FASTENER_MM, 0.20, 0.20)
        self.assertAlmostEqual(sized, HOLE_MM, places=6)
        self.assertAlmostEqual(
            floating_fastener_total_tolerance(sized, FASTENER_MM),
            TOTAL_BUDGET, places=6)

    def test_step5_minimum_hole_zero_tolerance_member_allowed(self):
        """Step 5 minimum hole traverse: a zero tolerance on one mating
        member is allowed and leaves the hole at the fastener plus the
        other member tolerance."""
        self.assertAlmostEqual(
            minimum_clearance_hole_mmc(6.35, 0.20, 0.0), 6.55, places=6)


class FastenerReportTests(unittest.TestCase):
    """Step 6 report bookkeeping of the SKILL.md workflow."""

    def test_step6_report_floating_direct_record(self):
        """Step 6 report bookkeeping for the floating fastener case:
        fastener_report("floating", 6.35, 6.75) must carry the 0.40 mm
        total tolerance, the 0.20 and 0.20 tolerance split and the
        6.75 mm clearance hole MMC diameter."""
        rec = fastener_report("floating", fastener_max=FASTENER_MM,
                              hole_mmc=HOLE_MM)
        self.assertEqual(rec["case"], "floating")
        self.assertAlmostEqual(rec["total_tolerance"], 0.40, places=6)
        self.assertAlmostEqual(rec["tol_clearance_member"], 0.20, places=6)
        self.assertAlmostEqual(rec["tol_other_member"], 0.20, places=6)
        self.assertAlmostEqual(rec["hole_mmc"], 6.75, places=6)

    def test_step6_report_fixed_solving_record(self):
        """Step 6 report bookkeeping solving the fixed fastener case:
        the record for 0.25 and 0.15 member tolerances on a 12 mm stack
        carries the minimum hole 6.75 mm and the 12.0 mm projected
        tolerance zone height."""
        rec = fastener_report("fixed", fastener_max=FASTENER_MM,
                              tol_clearance_member=0.25,
                              tol_other_member=0.15,
                              mating_thickness=MATING_THICKNESS)
        self.assertEqual(rec["case"], "fixed")
        self.assertAlmostEqual(rec["total_tolerance"], 0.40, places=6)
        self.assertAlmostEqual(rec["minimum_hole_mmc"], 6.75, places=6)
        self.assertAlmostEqual(rec["hole_mmc"], 6.75, places=6)
        self.assertAlmostEqual(rec["projected_zone_height"], 12.0, places=6)

    def test_step6_report_keys_exact_documented_sets(self):
        """Step 6 report bookkeeping key contract: the floating direct
        record exposes the five base keys and the fixed solving record
        with a mating thickness adds minimum_hole_mmc and
        projected_zone_height, matching the documented key sets."""
        float_rec = fastener_report("floating", fastener_max=FASTENER_MM,
                                    hole_mmc=HOLE_MM)
        fixed_rec = fastener_report("fixed", fastener_max=FASTENER_MM,
                                    tol_clearance_member=0.25,
                                    tol_other_member=0.15,
                                    mating_thickness=MATING_THICKNESS)
        self.assertEqual(set(float_rec.keys()),
                         set(report_keys(case="floating")))
        self.assertEqual(
            set(fixed_rec.keys()),
            set(report_keys(case="fixed", solving=True, fixed_zone=True)))

    def test_step6_report_fixed_without_thickness_no_zone_key(self):
        """Step 6 report bookkeeping: a fixed case without a mating
        thickness carries no projected_zone_height key."""
        rec = fastener_report("fixed", fastener_max=FASTENER_MM,
                              hole_mmc=HOLE_MM)
        self.assertNotIn("projected_zone_height", rec)
        self.assertIn("case", rec)

    def test_step6_report_invalid_case_rejected(self):
        """Step 6 report bookkeeping rejects a case outside floating and
        fixed with ValueError."""
        with self.assertRaises(ValueError):
            fastener_report("tapped", fastener_max=FASTENER_MM,
                            hole_mmc=HOLE_MM)

    def test_step6_report_solving_requires_both_tolerances(self):
        """Step 6 report bookkeeping solving mode needs both member
        tolerances of the tolerance split before it can size the hole."""
        with self.assertRaises(ValueError):
            fastener_report("fixed", fastener_max=FASTENER_MM,
                            tol_clearance_member=0.25)

    def test_step6_report_assigned_tolerances_preserved(self):
        """Step 6 report bookkeeping with assigned member tolerances and
        a set hole keeps the assigned 0.25 and 0.15 values instead of
        re-splitting the total tolerance."""
        rec = fastener_report("fixed", fastener_max=FASTENER_MM,
                              hole_mmc=HOLE_MM, tol_clearance_member=0.25,
                              tol_other_member=0.15)
        self.assertAlmostEqual(rec["tol_clearance_member"], 0.25, places=6)
        self.assertAlmostEqual(rec["tol_other_member"], 0.15, places=6)


class ValueErrorRejectionTests(unittest.TestCase):
    """Non-physical inputs must raise ValueError (Verification list)."""

    def test_error_hole_equal_to_fastener_rejected(self):
        """A clearance hole MMC diameter equal to the fastener maximum
        diameter leaves no clearance and must be rejected in the step 2
        budget traverse."""
        with self.assertRaises(ValueError):
            floating_fastener_total_tolerance(6.35, 6.35)
        with self.assertRaises(ValueError):
            fixed_fastener_total_tolerance(6.35, 6.35)

    def test_error_hole_below_fastener_rejected(self):
        """A clearance hole MMC diameter below the fastener maximum
        diameter is non-physical and must raise ValueError."""
        with self.assertRaises(ValueError):
            floating_fastener_total_tolerance(6.30, 6.35)

    def test_error_zero_fastener_rejected(self):
        """A zero fastener maximum diameter must be rejected by both the
        step 2 budget traverse and the step 5 minimum hole traverse."""
        with self.assertRaises(ValueError):
            floating_fastener_total_tolerance(6.75, 0.0)
        with self.assertRaises(ValueError):
            minimum_clearance_hole_mmc(0.0, 0.20, 0.20)

    def test_error_negative_fastener_rejected(self):
        """A negative fastener maximum diameter must raise ValueError."""
        with self.assertRaises(ValueError):
            fixed_fastener_total_tolerance(6.75, -1.0)

    def test_error_zero_total_budget_rejected(self):
        """A zero or negative total positional tolerance budget cannot be
        split in the step 3 split traverse."""
        with self.assertRaises(ValueError):
            split_tolerance(0.0)

    def test_error_negative_total_budget_rejected(self):
        """A negative total in the step 3 split traverse must raise
        ValueError."""
        with self.assertRaises(ValueError):
            split_tolerance(-0.1)

    def test_error_first_share_zero_rejected(self):
        """A first share of 0 in the step 3 split traverse would give one
        mating member nothing and must raise ValueError."""
        with self.assertRaises(ValueError):
            split_tolerance(0.40, 0.0)

    def test_error_first_share_one_rejected(self):
        """A first share of 1 in the step 3 split traverse would leave the
        other mating member with no tolerance and must raise ValueError."""
        with self.assertRaises(ValueError):
            split_tolerance(0.40, 1.0)

    def test_error_first_share_outside_range_rejected(self):
        """A first share outside (0, 1) in the step 3 split traverse must
        raise ValueError."""
        with self.assertRaises(ValueError):
            split_tolerance(0.40, 1.5)

    def test_error_negative_member_tolerance_rejected(self):
        """A negative member tolerance in the step 5 minimum hole traverse
        must raise ValueError."""
        with self.assertRaises(ValueError):
            minimum_clearance_hole_mmc(6.35, -0.05, 0.15)
        with self.assertRaises(ValueError):
            minimum_clearance_hole_mmc(6.35, 0.25, -0.05)

    def test_error_zero_mating_thickness_rejected(self):
        """A zero mating thickness in the step 4 projected zone traverse
        must raise ValueError."""
        with self.assertRaises(ValueError):
            projected_zone_height(0.0)

    def test_error_negative_mating_thickness_rejected(self):
        """A negative mating thickness in the step 4 projected zone
        traverse must raise ValueError."""
        with self.assertRaises(ValueError):
            projected_zone_height(-2.0)

    def test_error_zero_projected_multiplier_rejected(self):
        """A zero projected zone multiplier must raise ValueError."""
        with self.assertRaises(ValueError):
            projected_zone_height(12.0, 0.0)


class DeterminismAndBoundsTests(unittest.TestCase):
    """Step 7 contract test confirmation checks."""

    def test_determinism_repeated_calls_identical(self):
        """Repeated budget and split calls must be deterministic: the
        total positional tolerance budget and the tolerance split are
        identical across runs."""
        first = (floating_fastener_total_tolerance(6.75, 6.35),
                 split_tolerance(0.40))
        second = (floating_fastener_total_tolerance(6.75, 6.35),
                  split_tolerance(0.40))
        self.assertEqual(first, second)
        self.assertEqual(fastener_report("floating", fastener_max=6.35,
                                         hole_mmc=6.75),
                         fastener_report("floating", fastener_max=6.35,
                                         hole_mmc=6.75))

    def test_worked_example_magnitude_bounds(self):
        """The worked-example outputs sit inside the spec magnitude
        bounds: total 0.40 mm within 0.35 to 0.45, the equal split
        shares within 0.15 to 0.25, the minimum hole 6.75 mm within
        6.70 to 6.80, and the projected zone 12.0 mm."""
        total = floating_fastener_total_tolerance(6.75, 6.35)
        self.assertGreaterEqual(total, 0.35)
        self.assertLessEqual(total, 0.45)
        t1, t2 = split_tolerance(total)
        for share in (t1, t2):
            self.assertGreaterEqual(share, 0.15)
            self.assertLessEqual(share, 0.25)
        hole = minimum_clearance_hole_mmc(6.35, 0.25, 0.15)
        self.assertGreaterEqual(hole, 6.70)
        self.assertLessEqual(hole, 6.80)
        zone = projected_zone_height(12.0)
        self.assertGreaterEqual(zone, 11.9)
        self.assertLessEqual(zone, 12.1)


if __name__ == "__main__":
    unittest.main()
