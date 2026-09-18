"""Contract test for the contamination-budget-use leaf (stdlib unittest)."""

import unittest

from q7002_use_in_cleanliness_engineering_logic import (
    BASIS_SCREENING_BOUND,
    MAX_BAKEOUT_CREDIT,
    MICROGRAM_PER_GRAM,
    assess_contamination_budget,
    contributor_deposit,
    deposited_ug_per_cm2,
    source_term_g,
    validate_contributor,
)


def contributor(cid="HARNESS-POTTING", **kw):
    record = {
        "id": cid,
        "basis": BASIS_SCREENING_BOUND,
        "cvcm_pct": 0.04,
        "exposed_mass_g": 250.0,
        "transport_fraction": 0.01,
    }
    record.update(kw)
    return record


def receiver(**kw):
    record = {"area_cm2": 1000.0, "allocation_ug_per_cm2": 2.0}
    record.update(kw)
    return record


class TestValidateContributor(unittest.TestCase):
    def test_a_valid_contributor_is_normalized(self):
        norm = validate_contributor(contributor())
        self.assertEqual(norm["id"], "HARNESS-POTTING")
        self.assertAlmostEqual(norm["transport_fraction"], 0.01, places=12)

    def test_a_rate_basis_is_refused(self):
        with self.assertRaises(ValueError):
            validate_contributor(contributor(basis="outgassing-rate-g-per-s"))

    def test_a_blank_id_raises(self):
        with self.assertRaises(ValueError):
            validate_contributor(contributor("  "))

    def test_a_negative_condensable_figure_raises(self):
        with self.assertRaises(ValueError):
            validate_contributor(contributor(cvcm_pct=-0.01))

    def test_a_condensable_figure_above_a_hundred_percent_raises(self):
        with self.assertRaises(ValueError):
            validate_contributor(contributor(cvcm_pct=140.0))

    def test_a_transport_fraction_above_one_raises(self):
        with self.assertRaises(ValueError):
            validate_contributor(contributor(transport_fraction=1.4))

    def test_a_negative_transport_fraction_raises(self):
        with self.assertRaises(ValueError):
            validate_contributor(contributor(transport_fraction=-0.2))

    def test_a_full_transport_fraction_is_allowed(self):
        norm = validate_contributor(contributor(transport_fraction=1.0))
        self.assertAlmostEqual(norm["transport_fraction"], 1.0, places=12)

    def test_a_bakeout_credit_above_the_ceiling_raises(self):
        with self.assertRaises(ValueError):
            validate_contributor(
                contributor(
                    bakeout_credit_fraction=MAX_BAKEOUT_CREDIT + 0.05,
                    bakeout_reference="BKO-3",
                )
            )

    def test_a_non_boolean_comparability_flag_raises(self):
        with self.assertRaises(ValueError):
            validate_contributor(contributor(screening_comparable="yes"))

    def test_a_non_mapping_contributor_raises(self):
        with self.assertRaises(ValueError):
            validate_contributor("HARNESS-POTTING")


class TestSourceTerm(unittest.TestCase):
    def test_the_source_term_is_the_condensable_fraction_of_the_mass(self):
        self.assertAlmostEqual(source_term_g(0.04, 250.0), 0.1, places=9)

    def test_no_exposed_mass_gives_no_source(self):
        self.assertAlmostEqual(source_term_g(0.04, 0.0), 0.0, places=12)

    def test_the_source_term_scales_with_the_mass(self):
        self.assertAlmostEqual(
            source_term_g(0.04, 500.0), 2.0 * source_term_g(0.04, 250.0), places=9
        )

    def test_a_negative_mass_raises(self):
        with self.assertRaises(ValueError):
            source_term_g(0.04, -1.0)


class TestDeposit(unittest.TestCase):
    def test_the_deposit_is_the_transported_source_over_the_area(self):
        value = deposited_ug_per_cm2(0.1, 0.01, 1000.0)
        self.assertAlmostEqual(value, 0.1 * MICROGRAM_PER_GRAM * 0.01 / 1000.0, places=9)

    def test_no_transport_deposits_nothing(self):
        self.assertAlmostEqual(deposited_ug_per_cm2(0.1, 0.0, 1000.0), 0.0, places=12)

    def test_halving_the_area_doubles_the_areal_deposit(self):
        one = deposited_ug_per_cm2(0.1, 0.01, 1000.0)
        two = deposited_ug_per_cm2(0.1, 0.01, 500.0)
        self.assertAlmostEqual(two, 2.0 * one, places=9)

    def test_a_zero_receiver_area_raises(self):
        with self.assertRaises(ValueError):
            deposited_ug_per_cm2(0.1, 0.01, 0.0)


class TestContributorDeposit(unittest.TestCase):
    def test_a_plain_contributor_has_no_findings(self):
        row = contributor_deposit(contributor(), 1000.0)
        self.assertEqual(row["findings"], [])
        self.assertAlmostEqual(row["deposit_ug_per_cm2"], 1.0, places=9)

    def test_a_referenced_bakeout_credit_reduces_the_deposit(self):
        row = contributor_deposit(
            contributor(bakeout_credit_fraction=0.50, bakeout_reference="BKO-3"),
            1000.0,
        )
        self.assertAlmostEqual(row["deposit_ug_per_cm2"], 0.5, places=9)
        self.assertEqual(row["findings"], [])

    def test_an_uncited_bakeout_credit_is_not_applied(self):
        row = contributor_deposit(contributor(bakeout_credit_fraction=0.50), 1000.0)
        self.assertAlmostEqual(row["deposit_ug_per_cm2"], 1.0, places=9)
        self.assertIn(
            "bakeout-credit-claimed-without-a-bakeout-on-record", row["findings"]
        )

    def test_a_bakeout_on_record_with_no_credit_is_flagged(self):
        row = contributor_deposit(contributor(bakeout_reference="BKO-3"), 1000.0)
        self.assertIn("bakeout-on-record-with-no-credit-taken", row["findings"])

    def test_a_non_baseline_figure_without_a_note_is_flagged(self):
        row = contributor_deposit(contributor(screening_comparable=False), 1000.0)
        self.assertIn(
            "non-baseline-screening-figure-used-without-a-note", row["findings"]
        )

    def test_a_non_baseline_figure_with_a_note_is_accepted(self):
        row = contributor_deposit(
            contributor(
                screening_comparable=False,
                non_comparable_note="baked at 90 C, the maximum use temperature",
            ),
            1000.0,
        )
        self.assertEqual(row["findings"], [])


class TestBudget(unittest.TestCase):
    def test_a_budget_inside_its_allocation_is_clear(self):
        report = assess_contamination_budget([contributor()], receiver())
        self.assertTrue(report["clear"])
        self.assertAlmostEqual(report["total_deposit_ug_per_cm2"], 1.0, places=9)
        self.assertAlmostEqual(report["margin_ug_per_cm2"], 1.0, places=9)

    def test_contributions_add(self):
        report = assess_contamination_budget(
            [contributor("A"), contributor("B")], receiver()
        )
        self.assertAlmostEqual(report["total_deposit_ug_per_cm2"], 2.0, places=9)

    def test_a_budget_exactly_on_its_allocation_stays_within_it(self):
        report = assess_contamination_budget(
            [contributor("A"), contributor("B")], receiver()
        )
        self.assertAlmostEqual(
            report["total_deposit_ug_per_cm2"],
            report["allocation_ug_per_cm2"],
            places=9,
        )
        self.assertTrue(report["within_allocation"])

    def test_an_overrun_is_a_finding(self):
        report = assess_contamination_budget(
            [contributor("A", exposed_mass_g=2000.0)], receiver()
        )
        self.assertFalse(report["within_allocation"])
        self.assertIn(
            "molecular-deposition-budget-exceeds-its-allocation", report["findings"]
        )

    def test_the_dominant_contributor_is_named(self):
        report = assess_contamination_budget(
            [contributor("SMALL", exposed_mass_g=10.0), contributor("BIG")],
            receiver(),
        )
        self.assertEqual(report["dominant_contributor"], "BIG")
        self.assertEqual(report["ranked_contributor_ids"], ["BIG", "SMALL"])

    def test_utilization_is_the_total_over_the_allocation(self):
        report = assess_contamination_budget([contributor()], receiver())
        self.assertAlmostEqual(report["utilization_fraction"], 0.5, places=9)

    def test_contributor_findings_reach_the_budget(self):
        report = assess_contamination_budget(
            [contributor(bakeout_credit_fraction=0.5)], receiver()
        )
        self.assertFalse(report["clear"])
        self.assertIn(
            "bakeout-credit-claimed-without-a-bakeout-on-record", report["findings"]
        )

    def test_duplicate_contributor_ids_raise(self):
        with self.assertRaises(ValueError):
            assess_contamination_budget(
                [contributor("A"), contributor("A")], receiver()
            )

    def test_an_empty_contributor_list_raises(self):
        with self.assertRaises(ValueError):
            assess_contamination_budget([], receiver())

    def test_a_zero_allocation_raises(self):
        with self.assertRaises(ValueError):
            assess_contamination_budget(
                [contributor()], receiver(allocation_ug_per_cm2=0.0)
            )

    def test_a_non_mapping_receiver_raises(self):
        with self.assertRaises(ValueError):
            assess_contamination_budget([contributor()], 1000.0)

    def test_a_rate_basis_anywhere_in_the_list_raises(self):
        with self.assertRaises(ValueError):
            assess_contamination_budget(
                [contributor("A"), contributor("B", basis="rate")], receiver()
            )


if __name__ == "__main__":
    unittest.main()
