"""Contract tests for the clause 5.3.3 screening assessment logic.

The cases walk the workflow one step at a time: the hundred-percent coverage
refusal, the package-family screen set, the sequence order check, the removal
arithmetic, the cumulative and burn-in allowances, and the disposition that
rejects a lot rather than only its removed units. Each limit is exercised on
both sides, so a review of the record shows what was judged and not only the
verdict.
"""

import unittest

from q6013_class_2_screening_requirements_logic import (
    BURN_IN_SCREENS,
    MARGINAL_FRACTION,
    PACKAGE_SCREENS,
    SCREENING_TOLERANCE,
    assess_screening,
    cumulative_percent_defective,
    missing_screens,
    package_screens,
    screen_removals,
    sequence_order_findings,
)

HERMETIC = list(PACKAGE_SCREENS["hermetic-cavity"])
PLASTIC = list(PACKAGE_SCREENS["solid-encapsulated"])


def _spec(**overrides):
    spec = {
        "lot_size": 400,
        "package_family": "solid-encapsulated",
        "performed_screens": list(PLASTIC),
        "removals": [
            {"screen": "burn-in", "rejects": 2},
            {"screen": "final-electrical", "rejects": 1},
        ],
        "allowable_percent": 5.0,
    }
    spec.update(overrides)
    return spec


class ScreenSetTests(unittest.TestCase):
    def test_cavity_family_carries_seal_screens(self):
        screens = package_screens("hermetic-cavity")
        self.assertIn("seal-fine-leak", screens)
        self.assertIn("particle-impact-noise-detection", screens)

    def test_solid_family_carries_no_seal_screen(self):
        screens = package_screens("solid-encapsulated")
        self.assertNotIn("seal-fine-leak", screens)
        self.assertIn("moisture-preconditioning", screens)

    def test_family_name_normalised(self):
        self.assertEqual(package_screens("Hermetic_Cavity"), PACKAGE_SCREENS["hermetic-cavity"])

    def test_unknown_family_rejected(self):
        with self.assertRaises(ValueError):
            package_screens("glass-bead")

    def test_empty_family_rejected(self):
        with self.assertRaises(ValueError):
            package_screens("   ")

    def test_external_visual_closes_every_family(self):
        for screens in PACKAGE_SCREENS.values():
            self.assertEqual(screens[-1], "external-visual")

    def test_burn_in_screens_belong_to_every_family(self):
        for screens in PACKAGE_SCREENS.values():
            for name in BURN_IN_SCREENS:
                self.assertIn(name, screens)


class MissingScreenTests(unittest.TestCase):
    def test_complete_sequence_has_nothing_missing(self):
        self.assertEqual(missing_screens("solid-encapsulated", PLASTIC), [])

    def test_dropped_screen_named(self):
        performed = [s for s in PLASTIC if s != "moisture-preconditioning"]
        self.assertEqual(
            missing_screens("solid-encapsulated", performed), ["moisture-preconditioning"]
        )

    def test_repeated_screen_rejected(self):
        with self.assertRaises(ValueError):
            missing_screens("solid-encapsulated", PLASTIC + ["burn-in"])

    def test_non_sequence_performed_rejected(self):
        with self.assertRaises(ValueError):
            missing_screens("solid-encapsulated", "burn-in")


class SequenceOrderTests(unittest.TestCase):
    def test_declared_order_has_no_findings(self):
        self.assertEqual(sequence_order_findings("hermetic-cavity", HERMETIC), [])

    def test_end_points_before_burn_in_reported(self):
        performed = list(PLASTIC)
        i, j = performed.index("burn-in"), performed.index("burn-in-electrical-end-points")
        performed[i], performed[j] = performed[j], performed[i]
        findings = sequence_order_findings("solid-encapsulated", performed)
        self.assertTrue(any("inverts the required order" in f for f in findings))

    def test_external_visual_not_last_reported(self):
        performed = [s for s in PLASTIC if s != "external-visual"]
        performed.insert(0, "external-visual")
        findings = sequence_order_findings("solid-encapsulated", performed)
        self.assertTrue(any("does not close the sequence" in f for f in findings))

    def test_extra_unknown_screen_does_not_disturb_order(self):
        performed = list(PLASTIC)
        performed.insert(2, "customer-witness-hold-point")
        self.assertEqual(sequence_order_findings("solid-encapsulated", performed), [])


class RemovalTests(unittest.TestCase):
    def test_removal_percent_of_lot(self):
        records = screen_removals(200, [{"screen": "burn-in", "rejects": 4}])
        self.assertAlmostEqual(records[0]["percent_of_lot"], 2.0, places=9)
        self.assertTrue(records[0]["burn_in"])

    def test_non_burn_in_screen_flagged_as_such(self):
        records = screen_removals(200, [{"screen": "external-visual", "rejects": 1}])
        self.assertFalse(records[0]["burn_in"])

    def test_removals_exceeding_the_lot_rejected(self):
        with self.assertRaises(ValueError):
            screen_removals(10, [{"screen": "burn-in", "rejects": 7}, {"screen": "final-electrical", "rejects": 5}])

    def test_negative_rejects_refused(self):
        with self.assertRaises(ValueError):
            screen_removals(100, [{"screen": "burn-in", "rejects": -1}])

    def test_removal_missing_screen_key_refused(self):
        with self.assertRaises(ValueError):
            screen_removals(100, [{"rejects": 1}])

    def test_zero_lot_size_refused(self):
        with self.assertRaises(ValueError):
            screen_removals(0, [])

    def test_cumulative_splits_burn_in_from_the_rest(self):
        records = screen_removals(
            100,
            [
                {"screen": "burn-in", "rejects": 3},
                {"screen": "burn-in-electrical-end-points", "rejects": 1},
                {"screen": "external-visual", "rejects": 2},
            ],
        )
        totals = cumulative_percent_defective(100, records)
        self.assertEqual(totals["removed"], 6)
        self.assertEqual(totals["survivors"], 94)
        self.assertAlmostEqual(totals["percent_defective"], 6.0, places=9)
        self.assertAlmostEqual(totals["burn_in_percent_defective"], 4.0, places=9)


class AssessmentTests(unittest.TestCase):
    def test_clean_lot_released(self):
        result = assess_screening(_spec())
        self.assertTrue(result["accepted"])
        self.assertEqual(result["disposition"], "release-screened-lot")
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["survivors"], 397)

    def test_sampled_screening_refused(self):
        with self.assertRaises(ValueError):
            assess_screening(_spec(units_screened=40))

    def test_screened_count_above_lot_refused(self):
        with self.assertRaises(ValueError):
            assess_screening(_spec(units_screened=401))

    def test_missing_screen_holds_the_lot(self):
        performed = [s for s in PLASTIC if s != "temperature-cycling"]
        result = assess_screening(_spec(performed_screens=performed))
        self.assertFalse(result["accepted"])
        self.assertEqual(result["disposition"], "reject-lot")
        self.assertEqual(result["missing_screens"], ["temperature-cycling"])

    def test_percent_defective_equal_to_allowance_accepts(self):
        result = assess_screening(
            _spec(
                lot_size=100,
                removals=[{"screen": "burn-in", "rejects": 5}],
                allowable_percent=5.0,
                burn_in_allowable_percent=100.0,
            )
        )
        self.assertAlmostEqual(result["percent_defective"], 5.0, places=9)
        self.assertTrue(result["within_allowance"])
        self.assertTrue(result["accepted"])

    def test_percent_defective_over_allowance_rejects_the_whole_lot(self):
        result = assess_screening(
            _spec(lot_size=100, removals=[{"screen": "burn-in", "rejects": 6}], allowable_percent=5.0)
        )
        self.assertFalse(result["accepted"])
        self.assertTrue(any("rejected, not only its removed units" in f for f in result["findings"]))

    def test_burn_in_subtotal_is_a_separate_gate(self):
        result = assess_screening(
            _spec(
                lot_size=100,
                removals=[{"screen": "burn-in", "rejects": 4}],
                allowable_percent=20.0,
                burn_in_allowable_percent=2.0,
            )
        )
        self.assertTrue(result["within_allowance"])
        self.assertFalse(result["within_burn_in_allowance"])
        self.assertFalse(result["accepted"])

    def test_replacement_units_reject_the_lot(self):
        result = assess_screening(_spec(replacement_units=6))
        self.assertFalse(result["accepted"])
        self.assertTrue(any("is not topped up" in f for f in result["findings"]))

    def test_removal_naming_a_screen_outside_the_family_refused(self):
        with self.assertRaises(ValueError):
            assess_screening(_spec(removals=[{"screen": "seal-fine-leak", "rejects": 1}]))

    def test_marginal_lot_released_with_an_advisory(self):
        result = assess_screening(
            _spec(
                lot_size=100,
                removals=[{"screen": "final-electrical", "rejects": 4}],
                allowable_percent=5.0,
            )
        )
        self.assertTrue(result["accepted"])
        self.assertTrue(result["marginal"])
        self.assertGreaterEqual(result["percent_defective"], MARGINAL_FRACTION * 5.0)

    def test_allowance_outside_percentage_range_refused(self):
        with self.assertRaises(ValueError):
            assess_screening(_spec(allowable_percent=140.0))

    def test_missing_required_key_refused(self):
        spec = _spec()
        del spec["removals"]
        with self.assertRaises(ValueError):
            assess_screening(spec)

    def test_non_mapping_spec_refused(self):
        with self.assertRaises(ValueError):
            assess_screening(["not", "a", "mapping"])

    def test_tolerance_is_representation_sized_only(self):
        self.assertLess(SCREENING_TOLERANCE, 1e-6)


if __name__ == "__main__":
    unittest.main()
