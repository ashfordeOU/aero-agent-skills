"""Contract test for the active-chip-general-provisions leaf (stdlib unittest)."""

import unittest

from q6005_active_chip_general_provisions_logic import (
    COMPLIANT,
    COVERAGE_TOLERANCE,
    DEFICIENT,
    SCOPE_ALL_ACTIVE_DICE,
    SCOPE_FUNCTION,
    SCOPE_TECHNOLOGY,
    WAIVER_EXPIRED,
    WAIVER_NOT_WAIVABLE,
    WAIVER_UNAUTHORIZED,
    WAIVER_VALID,
    applicable_provisions,
    assess_general_provisions,
    assess_purchase_set,
    baseline_coverage_fraction,
    baseline_gaps,
    baseline_provision_ids,
    conditioned_gaps,
    conditioned_provisions_for,
    is_baseline,
    provision_is_waivable,
    substitution_findings,
    validate_declaration,
    validate_provision,
    validate_waiver,
    waived_provision_ids,
    waiver_findings,
    waiver_status,
)


def declaration(decl_id="P-1", **kw):
    record = {
        "id": decl_id,
        "technology": "silicon-cmos",
        "device_function": "digital",
        "declared_provisions": list(baseline_provision_ids()),
        "waivers": [],
        "substitutions": {},
        "assessment_date": "2026-06-01",
    }
    record.update(kw)
    return record


def waiver(provision="die-storage-under-controlled-atmosphere", **kw):
    record = {
        "provision": provision,
        "authority": "customer-product-assurance",
        "valid_until": "2026-12-31",
    }
    record.update(kw)
    return record


class TestProvisionScope(unittest.TestCase):
    def test_an_unconditioned_provision_is_baseline(self):
        self.assertTrue(
            is_baseline({"id": "x", "scope": SCOPE_ALL_ACTIVE_DICE})
        )

    def test_a_technology_conditioned_provision_is_not_baseline(self):
        self.assertFalse(
            is_baseline(
                {
                    "id": "x",
                    "scope": SCOPE_TECHNOLOGY,
                    "condition": "gallium-nitride-hemt",
                }
            )
        )

    def test_a_function_conditioned_provision_is_not_baseline(self):
        self.assertFalse(
            is_baseline({"id": "x", "scope": SCOPE_FUNCTION, "condition": "memory"})
        )

    def test_universal_scope_with_a_condition_raises(self):
        with self.assertRaises(ValueError):
            validate_provision(
                {
                    "id": "x",
                    "scope": SCOPE_ALL_ACTIVE_DICE,
                    "condition": "silicon-cmos",
                }
            )

    def test_conditioned_scope_without_a_condition_raises(self):
        with self.assertRaises(ValueError):
            validate_provision({"id": "x", "scope": SCOPE_TECHNOLOGY})

    def test_unknown_technology_condition_raises(self):
        with self.assertRaises(ValueError):
            validate_provision(
                {"id": "x", "scope": SCOPE_TECHNOLOGY, "condition": "clockwork"}
            )

    def test_unknown_function_condition_raises(self):
        with self.assertRaises(ValueError):
            validate_provision(
                {"id": "x", "scope": SCOPE_FUNCTION, "condition": "telepathy"}
            )

    def test_unknown_scope_raises(self):
        with self.assertRaises(ValueError):
            validate_provision({"id": "x", "scope": "sometimes"})

    def test_non_mapping_provision_raises(self):
        with self.assertRaises(ValueError):
            validate_provision("wafer-lot-traceability-to-diffusion-lot")


class TestApplicability(unittest.TestCase):
    def test_baseline_applies_to_a_plain_purchase(self):
        owed = applicable_provisions("silicon-cmos", "digital")
        self.assertEqual(set(owed), set(baseline_provision_ids()))

    def test_a_compound_technology_conditions_a_provision_in(self):
        owed = conditioned_provisions_for("gallium-arsenide-mmic", "digital")
        self.assertIn("compound-semiconductor-backside-metal-inspection", owed)

    def test_a_function_conditions_a_provision_in(self):
        owed = conditioned_provisions_for("silicon-cmos", "memory")
        self.assertIn("memory-device-pattern-sensitivity-screen", owed)

    def test_conditioned_provisions_add_to_the_baseline(self):
        owed = applicable_provisions("gallium-nitride-hemt", "linear")
        self.assertTrue(set(baseline_provision_ids()) <= set(owed))
        self.assertGreater(len(owed), len(baseline_provision_ids()))

    def test_unknown_technology_raises(self):
        with self.assertRaises(ValueError):
            conditioned_provisions_for("clockwork", "digital")

    def test_unknown_device_function_raises(self):
        with self.assertRaises(ValueError):
            conditioned_provisions_for("silicon-cmos", "telepathy")


class TestWaivers(unittest.TestCase):
    def test_a_sound_waiver_is_valid(self):
        self.assertEqual(waiver_status(waiver(), "2026-06-01"), WAIVER_VALID)

    def test_a_waiver_past_its_date_is_expired(self):
        self.assertEqual(waiver_status(waiver(), "2027-01-02"), WAIVER_EXPIRED)

    def test_a_waiver_on_its_last_day_is_still_valid(self):
        self.assertEqual(waiver_status(waiver(), "2026-12-31"), WAIVER_VALID)

    def test_a_supplier_cannot_grant_its_own_waiver(self):
        status = waiver_status(waiver(authority="die-supplier"), "2026-06-01")
        self.assertEqual(status, WAIVER_UNAUTHORIZED)

    def test_an_unwaivable_provision_refuses_the_waiver(self):
        status = waiver_status(
            waiver(provision="wafer-lot-traceability-to-diffusion-lot"),
            "2026-06-01",
        )
        self.assertEqual(status, WAIVER_NOT_WAIVABLE)

    def test_identity_provisions_may_not_be_waived(self):
        self.assertFalse(
            provision_is_waivable("die-visual-inspection-before-encapsulation")
        )
        self.assertTrue(provision_is_waivable("die-deliverable-documentation-set"))

    def test_unknown_provision_in_a_waiver_raises(self):
        with self.assertRaises(ValueError):
            validate_waiver(waiver(provision="free-lunch"))

    def test_malformed_waiver_date_raises(self):
        with self.assertRaises(ValueError):
            validate_waiver(waiver(valid_until="next-spring"))

    def test_empty_waiver_authority_raises(self):
        with self.assertRaises(ValueError):
            validate_waiver(waiver(authority="  "))

    def test_unwaivable_provision_is_not_relieved(self):
        decl = declaration(
            "P-1",
            declared_provisions=[
                p
                for p in baseline_provision_ids()
                if p != "wafer-lot-traceability-to-diffusion-lot"
            ],
            waivers=[waiver(provision="wafer-lot-traceability-to-diffusion-lot")],
        )
        self.assertIn("wafer-lot-traceability-to-diffusion-lot", baseline_gaps(decl))
        self.assertIn(
            "%s:wafer-lot-traceability-to-diffusion-lot" % WAIVER_NOT_WAIVABLE,
            waiver_findings(decl),
        )


class TestDeclarationValidation(unittest.TestCase):
    def test_defaults_are_filled_in(self):
        norm = validate_declaration(
            {
                "id": "P-9",
                "technology": "silicon-bipolar",
                "device_function": "discrete",
            }
        )
        self.assertEqual(norm["declared_provisions"], [])
        self.assertEqual(norm["waivers"], [])
        self.assertEqual(norm["substitutions"], {})

    def test_non_mapping_declaration_raises(self):
        with self.assertRaises(ValueError):
            validate_declaration(["P-1"])

    def test_empty_id_raises(self):
        with self.assertRaises(ValueError):
            validate_declaration(declaration(""))

    def test_unknown_declared_provision_raises(self):
        with self.assertRaises(ValueError):
            validate_declaration(
                declaration("P-1", declared_provisions=["free-lunch"])
            )

    def test_non_sequence_declared_provisions_raises(self):
        with self.assertRaises(ValueError):
            validate_declaration(
                declaration("P-1", declared_provisions="everything")
            )

    def test_non_mapping_substitutions_raises(self):
        with self.assertRaises(ValueError):
            validate_declaration(declaration("P-1", substitutions=["a", "b"]))

    def test_substitution_for_an_unknown_baseline_raises(self):
        with self.assertRaises(ValueError):
            validate_declaration(
                declaration(
                    "P-1",
                    substitutions={
                        "free-lunch": "memory-device-pattern-sensitivity-screen"
                    },
                )
            )


class TestCoverage(unittest.TestCase):
    def test_a_full_declaration_covers_the_baseline(self):
        self.assertAlmostEqual(
            baseline_coverage_fraction(declaration()), 1.0, places=9
        )
        self.assertEqual(baseline_gaps(declaration()), [])

    def test_a_dropped_provision_opens_a_gap(self):
        held = [
            p
            for p in baseline_provision_ids()
            if p != "supplier-change-notification-agreement"
        ]
        decl = declaration("P-1", declared_provisions=held)
        self.assertEqual(
            baseline_gaps(decl), ["supplier-change-notification-agreement"]
        )
        total = len(baseline_provision_ids())
        self.assertAlmostEqual(
            baseline_coverage_fraction(decl), (total - 1) / total, places=12
        )

    def test_an_empty_declaration_covers_nothing(self):
        decl = declaration("P-1", declared_provisions=[])
        self.assertAlmostEqual(baseline_coverage_fraction(decl), 0.0, places=12)

    def test_a_valid_waiver_closes_the_gap_it_covers(self):
        held = [
            p
            for p in baseline_provision_ids()
            if p != "die-storage-under-controlled-atmosphere"
        ]
        decl = declaration("P-1", declared_provisions=held, waivers=[waiver()])
        self.assertEqual(baseline_gaps(decl), [])
        self.assertEqual(
            waived_provision_ids(decl),
            ["die-storage-under-controlled-atmosphere"],
        )

    def test_an_expired_waiver_leaves_the_gap_open(self):
        held = [
            p
            for p in baseline_provision_ids()
            if p != "die-storage-under-controlled-atmosphere"
        ]
        decl = declaration(
            "P-1",
            declared_provisions=held,
            waivers=[waiver(valid_until="2026-01-31")],
        )
        self.assertEqual(
            baseline_gaps(decl), ["die-storage-under-controlled-atmosphere"]
        )

    def test_coverage_tolerance_is_far_below_one_provision(self):
        self.assertAlmostEqual(COVERAGE_TOLERANCE, 1.0e-12, places=18)


class TestSubstitution(unittest.TestCase):
    def test_a_substitution_is_reported(self):
        decl = declaration(
            "P-1",
            substitutions={
                "die-deliverable-documentation-set": (
                    "memory-device-pattern-sensitivity-screen"
                )
            },
        )
        self.assertIn(
            "device-specific-provision-offered-for-baseline:"
            "die-deliverable-documentation-set",
            substitution_findings(decl),
        )

    def test_no_substitution_produces_no_finding(self):
        self.assertEqual(substitution_findings(declaration()), [])


class TestAssessment(unittest.TestCase):
    def test_a_complete_declaration_is_acceptable(self):
        result = assess_general_provisions(declaration())
        self.assertEqual(result["status"], COMPLIANT)
        self.assertTrue(result["acceptable"])
        self.assertEqual(result["findings"], [])

    def test_a_gap_makes_the_declaration_deficient(self):
        decl = declaration("P-1", declared_provisions=[])
        result = assess_general_provisions(decl)
        self.assertEqual(result["status"], DEFICIENT)
        self.assertFalse(result["acceptable"])

    def test_a_conditioned_gap_is_reported_separately(self):
        decl = declaration("P-1", technology="gallium-arsenide-mmic")
        result = assess_general_provisions(decl)
        self.assertEqual(result["status"], COMPLIANT)
        self.assertEqual(
            result["conditioned_gaps"],
            ["compound-semiconductor-backside-metal-inspection"],
        )
        self.assertFalse(result["acceptable"])

    def test_report_lists_what_the_purchase_owes(self):
        result = assess_general_provisions(
            declaration("P-1", device_function="linear")
        )
        self.assertIn(
            "linear-device-parametric-drift-screen", result["applicable_provisions"]
        )


class TestPurchaseSet(unittest.TestCase):
    def test_a_clean_set_is_acceptable(self):
        report = assess_purchase_set([declaration("P-1"), declaration("P-2")])
        self.assertTrue(report["set_acceptable"])
        self.assertEqual(report["open_ids"], [])
        self.assertAlmostEqual(report["weakest_coverage"], 1.0, places=9)

    def test_one_open_declaration_fails_the_set(self):
        report = assess_purchase_set(
            [declaration("P-1"), declaration("P-2", declared_provisions=[])]
        )
        self.assertFalse(report["set_acceptable"])
        self.assertEqual(report["open_ids"], ["P-2"])
        self.assertEqual(report["acceptable_ids"], ["P-1"])
        self.assertEqual(report["weakest_declaration"], "P-2")

    def test_duplicate_declaration_id_raises(self):
        with self.assertRaises(ValueError):
            assess_purchase_set([declaration("P-1"), declaration("P-1")])

    def test_empty_set_raises(self):
        with self.assertRaises(ValueError):
            assess_purchase_set([])

    def test_non_list_set_raises(self):
        with self.assertRaises(ValueError):
            assess_purchase_set(declaration())


if __name__ == "__main__":
    unittest.main()
