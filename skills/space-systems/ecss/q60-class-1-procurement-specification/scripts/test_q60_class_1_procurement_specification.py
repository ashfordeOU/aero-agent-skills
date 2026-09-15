"""Contract tests for the clause 4.3.2 Class 1 purchasing-specification logic.

The cases walk the workflow one step at a time: document identity, the
one-to-one mapping of ordered component types onto specifications, the
content each specification has to declare, the issue-currency comparison
against the order date, deviation approval, and the controlled fraction the
verdict reports. Each limit is exercised on both sides, so a review of the
record shows what was judged and not only the verdict.
"""

import datetime
import unittest

from q60_class_1_procurement_specification_logic import (
    FRACTION_TOLERANCE,
    MINIMUM_TRACEABILITY,
    REQUIRED_QUALITY_LEVEL,
    TRACEABILITY_RANK,
    assess_procurement_baseline,
    controlled_fraction,
    map_types_to_specifications,
    normalize_token,
    parse_iso_date,
    specification_findings,
    traceability_rank,
    validate_specification,
)


def _spec(**overrides):
    spec = {
        "identifier": "PS-4401",
        "issue": "C",
        "approved_by": "product-assurance-manager",
        "effective_date": "2026-01-10",
        "component_types": ["hermetic-microcircuit"],
        "quality_level": "class-1",
        "manufacturer": "approved-foundry",
        "manufacturing_line": "line-2-hermetic",
        "test_programme": "TP-60C-MICROCIRCUIT",
        "traceability": "wafer-lot",
        "deviations": [],
    }
    spec.update(overrides)
    return spec


def _baseline(**overrides):
    baseline = {
        "order_reference": "PO-2026-118",
        "order_date": "2026-03-02",
        "ordered_types": ["hermetic-microcircuit", "tantalum-capacitor"],
        "specifications": [
            _spec(),
            _spec(
                identifier="PS-4402",
                component_types=["tantalum-capacitor"],
                test_programme="TP-60C-CAPACITOR",
                traceability="lot-date-code",
            ),
        ],
    }
    baseline.update(overrides)
    return baseline


class TokenAndDateTests(unittest.TestCase):
    def test_token_normalised_to_lower_hyphen(self):
        self.assertEqual(
            normalize_token("Hermetic_Microcircuit", "type"), "hermetic-microcircuit"
        )

    def test_blank_token_refused(self):
        with self.assertRaises(ValueError):
            normalize_token("   ", "type")

    def test_non_string_token_refused(self):
        with self.assertRaises(ValueError):
            normalize_token(7, "type")

    def test_iso_date_parsed(self):
        self.assertEqual(
            parse_iso_date("2026-03-02", "order_date"), datetime.date(2026, 3, 2)
        )

    def test_date_object_passes_through(self):
        day = datetime.date(2026, 3, 2)
        self.assertEqual(parse_iso_date(day, "order_date"), day)

    def test_non_calendar_date_refused(self):
        with self.assertRaises(ValueError):
            parse_iso_date("02/03/2026", "order_date")


class TraceabilityTests(unittest.TestCase):
    def test_ranks_are_ordered_weakest_first(self):
        self.assertLess(TRACEABILITY_RANK["none"], TRACEABILITY_RANK["lot-date-code"])
        self.assertLess(
            TRACEABILITY_RANK["lot-date-code"], TRACEABILITY_RANK["serial-number"]
        )

    def test_minimum_level_is_recognised(self):
        self.assertIn(MINIMUM_TRACEABILITY, TRACEABILITY_RANK)

    def test_unknown_level_refused(self):
        with self.assertRaises(ValueError):
            traceability_rank("handshake")

    def test_stronger_level_outranks_the_minimum(self):
        self.assertGreater(
            traceability_rank("serial-number"), traceability_rank(MINIMUM_TRACEABILITY)
        )


class SpecificationValidationTests(unittest.TestCase):
    def test_complete_specification_validates(self):
        record = validate_specification(_spec())
        self.assertEqual(record["identifier"], "PS-4401")
        self.assertEqual(record["component_types"], ["hermetic-microcircuit"])

    def test_missing_issue_refused(self):
        spec = _spec()
        del spec["issue"]
        with self.assertRaises(ValueError):
            validate_specification(spec)

    def test_blank_approving_authority_refused(self):
        with self.assertRaises(ValueError):
            validate_specification(_spec(approved_by="  "))

    def test_empty_type_list_refused(self):
        with self.assertRaises(ValueError):
            validate_specification(_spec(component_types=[]))

    def test_repeated_type_on_one_specification_refused(self):
        with self.assertRaises(ValueError):
            validate_specification(
                _spec(component_types=["hermetic-microcircuit", "Hermetic Microcircuit"])
            )

    def test_deviation_without_subject_refused(self):
        with self.assertRaises(ValueError):
            validate_specification(_spec(deviations=[{"approval_reference": "RFD-9"}]))

    def test_non_mapping_specification_refused(self):
        with self.assertRaises(ValueError):
            validate_specification(["PS-4401"])


class SpecificationFindingTests(unittest.TestCase):
    def test_complete_specification_raises_nothing(self):
        record = validate_specification(_spec())
        self.assertEqual(specification_findings(record, "2026-03-02"), [])

    def test_wrong_quality_level_reported(self):
        record = validate_specification(_spec(quality_level="class-2"))
        findings = specification_findings(record, "2026-03-02")
        self.assertTrue(any(REQUIRED_QUALITY_LEVEL in f for f in findings))

    def test_missing_manufacturing_line_reported(self):
        record = validate_specification(_spec(manufacturing_line=""))
        findings = specification_findings(record, "2026-03-02")
        self.assertTrue(any("manufacturing line" in f for f in findings))

    def test_missing_test_programme_reported(self):
        record = validate_specification(_spec(test_programme=""))
        findings = specification_findings(record, "2026-03-02")
        self.assertTrue(any("test programme" in f for f in findings))

    def test_weak_traceability_reported(self):
        record = validate_specification(_spec(traceability="delivery-batch"))
        findings = specification_findings(record, "2026-03-02")
        self.assertTrue(any("weaker than" in f for f in findings))

    def test_minimum_traceability_accepted(self):
        record = validate_specification(_spec(traceability=MINIMUM_TRACEABILITY))
        self.assertEqual(specification_findings(record, "2026-03-02"), [])

    def test_issue_effective_after_the_order_reported(self):
        record = validate_specification(_spec(effective_date="2026-04-01"))
        findings = specification_findings(record, "2026-03-02")
        self.assertTrue(any("after the order date" in f for f in findings))

    def test_issue_effective_on_the_order_date_accepted(self):
        record = validate_specification(_spec(effective_date="2026-03-02"))
        self.assertEqual(specification_findings(record, "2026-03-02"), [])

    def test_unapproved_deviation_reported(self):
        record = validate_specification(
            _spec(deviations=[{"subject": "burn-in duration", "approval_reference": ""}])
        )
        findings = specification_findings(record, "2026-03-02")
        self.assertTrue(any("no approval reference" in f for f in findings))

    def test_approved_deviation_accepted(self):
        record = validate_specification(
            _spec(deviations=[{"subject": "burn-in duration", "approval_reference": "RFD-9"}])
        )
        self.assertEqual(specification_findings(record, "2026-03-02"), [])


class CoverageMappingTests(unittest.TestCase):
    def test_one_to_one_mapping_has_no_findings(self):
        records = [validate_specification(s) for s in _baseline()["specifications"]]
        coverage = map_types_to_specifications(
            ["hermetic-microcircuit", "tantalum-capacitor"], records
        )
        self.assertEqual(coverage["findings"], [])

    def test_uncovered_type_reported(self):
        records = [validate_specification(_spec())]
        coverage = map_types_to_specifications(
            ["hermetic-microcircuit", "tantalum-capacitor"], records
        )
        self.assertEqual(coverage["uncovered_types"], ["tantalum-capacitor"])

    def test_type_carried_by_two_specifications_reported(self):
        records = [
            validate_specification(_spec()),
            validate_specification(_spec(identifier="PS-4405")),
        ]
        coverage = map_types_to_specifications(["hermetic-microcircuit"], records)
        self.assertEqual(coverage["ambiguous_types"], ["hermetic-microcircuit"])

    def test_surplus_type_reported(self):
        records = [validate_specification(_spec(component_types=["relay"]))]
        coverage = map_types_to_specifications(["hermetic-microcircuit"], records)
        self.assertIn("relay", coverage["surplus_types"])

    def test_type_ordered_twice_refused(self):
        records = [validate_specification(_spec())]
        with self.assertRaises(ValueError):
            map_types_to_specifications(
                ["hermetic-microcircuit", "Hermetic-Microcircuit"], records
            )

    def test_empty_order_refused(self):
        with self.assertRaises(ValueError):
            map_types_to_specifications([], [])


class ControlledFractionTests(unittest.TestCase):
    def test_all_types_controlled_is_one(self):
        value = controlled_fraction(["a", "b"], ["a", "b"])
        self.assertAlmostEqual(value, 1.0, places=9)

    def test_half_controlled(self):
        value = controlled_fraction(["a", "b"], ["a"])
        self.assertAlmostEqual(value, 0.5, places=9)

    def test_none_controlled_is_zero(self):
        self.assertAlmostEqual(controlled_fraction(["a", "b"], []), 0.0, places=9)

    def test_thirds_are_representation_sized(self):
        value = controlled_fraction(["a", "b", "c"], ["a"])
        self.assertAlmostEqual(value, 1.0 / 3.0, places=9)

    def test_unknown_controlled_type_refused(self):
        with self.assertRaises(ValueError):
            controlled_fraction(["a"], ["z"])

    def test_tolerance_is_representation_sized_only(self):
        self.assertLess(FRACTION_TOLERANCE, 1e-6)


class BaselineTests(unittest.TestCase):
    def test_clean_baseline_is_orderable(self):
        verdict = assess_procurement_baseline(_baseline())
        self.assertTrue(verdict["orderable"])
        self.assertEqual(verdict["findings"], [])
        self.assertAlmostEqual(verdict["controlled_fraction"], 1.0, places=9)

    def test_uncovered_type_blocks_the_order(self):
        baseline = _baseline(specifications=[_spec()])
        verdict = assess_procurement_baseline(baseline)
        self.assertFalse(verdict["orderable"])
        self.assertAlmostEqual(verdict["controlled_fraction"], 0.5, places=9)

    def test_every_finding_is_carried_not_only_the_first(self):
        baseline = _baseline(
            specifications=[
                _spec(quality_level="class-2", test_programme=""),
                _spec(
                    identifier="PS-4402",
                    component_types=["tantalum-capacitor"],
                    test_programme="TP-60C-CAPACITOR",
                    traceability="none",
                ),
            ]
        )
        verdict = assess_procurement_baseline(baseline)
        self.assertGreaterEqual(len(verdict["findings"]), 3)

    def test_type_record_names_its_specification_issue(self):
        verdict = assess_procurement_baseline(_baseline())
        record = verdict["types"][0]
        self.assertEqual(record["component_type"], "hermetic-microcircuit")
        self.assertEqual(record["issue"], "C")
        self.assertTrue(record["governed"])

    def test_ambiguous_type_is_not_governed(self):
        baseline = _baseline(
            ordered_types=["hermetic-microcircuit"],
            specifications=[_spec(), _spec(identifier="PS-4409")],
        )
        verdict = assess_procurement_baseline(baseline)
        self.assertFalse(verdict["types"][0]["governed"])
        self.assertAlmostEqual(verdict["controlled_fraction"], 0.0, places=9)

    def test_same_specification_issue_twice_refused(self):
        baseline = _baseline(
            ordered_types=["hermetic-microcircuit"], specifications=[_spec(), _spec()]
        )
        with self.assertRaises(ValueError):
            assess_procurement_baseline(baseline)

    def test_missing_required_key_refused(self):
        baseline = _baseline()
        del baseline["order_date"]
        with self.assertRaises(ValueError):
            assess_procurement_baseline(baseline)

    def test_non_mapping_baseline_refused(self):
        with self.assertRaises(ValueError):
            assess_procurement_baseline(["not", "a", "mapping"])

    def test_order_date_echoed_in_the_record(self):
        verdict = assess_procurement_baseline(_baseline())
        self.assertEqual(verdict["order_date"], "2026-03-02")


if __name__ == "__main__":
    unittest.main()
