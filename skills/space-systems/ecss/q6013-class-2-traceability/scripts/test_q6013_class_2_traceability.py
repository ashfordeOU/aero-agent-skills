"""Contract tests for the clause 5.5.4 class 2 lot traceability assessment.

Every workflow step the SKILL.md sets out is exercised here, together with the
stop conditions the gate 3 contract reviews: no record speaking for the lot, a
record naming another lot with no cross-reference, a record held by another
party with no access undertaking, a step nobody recorded, a retention period
below the floor, and records dated against the order of their handling steps.
"""

import unittest

from q6013_class_2_traceability_logic import (
    ACCESS_UNDERTAKING_MISSING,
    CHAIN_NOT_ESTABLISHED,
    COVERAGE_TOLERANCE,
    DEFAULT_TRACEABILITY_POLICY,
    HANDLING_STEP_ORDER,
    HELD_BY_PROJECT,
    HELD_EXTERNALLY,
    LOT_IDENTITY_BROKEN,
    RECORDS_OUT_OF_ORDER,
    RETENTION_BELOW_FLOOR,
    STEP_COVERAGE_SHORT,
    TRACEABILITY_MEETS_CLASS_TWO,
    assess_lot_traceability,
    dispose_steps,
    order_breaks,
    resolve_identity,
    retention_shortfalls,
    step_coverage,
    step_rank,
    validate_record,
    validate_records,
    validate_traceability_policy,
)

LOT = "LOT-4417"


def _record(step, day, identifier=None, lot=LOT, holder=HELD_BY_PROJECT,
            retention=12, cross_reference="", undertaking=""):
    entry = {
        "id": identifier or ("rec-%s" % step),
        "step": step,
        "lot_code": lot,
        "holder": holder,
        "retention_years": retention,
        "recorded_day": day,
        "cross_reference": cross_reference,
    }
    if holder == HELD_EXTERNALLY:
        entry["access_undertaking"] = undertaking
    return entry


def _full_chain():
    return [
        _record(step, day)
        for day, step in enumerate(HANDLING_STEP_ORDER, start=1)
    ]


def _case(**overrides):
    case = {"lot_code": LOT, "records": _full_chain()}
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        settings = validate_traceability_policy(None)
        self.assertEqual(settings["min_retention_years"], 10)
        self.assertEqual(len(settings["required_steps"]), 6)

    def test_unknown_policy_key_rejected(self):
        with self.assertRaises(ValueError):
            validate_traceability_policy({"min_retention_months": 24})

    def test_credited_floor_above_plain_floor_rejected(self):
        with self.assertRaises(ValueError):
            validate_traceability_policy(
                {"min_step_coverage": 0.6, "min_credited_step_coverage": 0.9}
            )

    def test_required_steps_without_receipt_rejected(self):
        with self.assertRaises(ValueError):
            validate_traceability_policy({"required_steps": ["storage", "assembly"]})

    def test_unrecognised_required_step_rejected(self):
        with self.assertRaises(ValueError):
            validate_traceability_policy({"required_steps": ["receipt", "painting"]})

    def test_required_steps_are_returned_in_handling_order(self):
        settings = validate_traceability_policy(
            {"required_steps": ["assembly", "receipt", "storage"]}
        )
        self.assertEqual(settings["required_steps"], ["receipt", "storage", "assembly"])

    def test_zero_retention_floor_rejected(self):
        with self.assertRaises(ValueError):
            validate_traceability_policy({"min_retention_years": 0})

    def test_defaults_are_not_shared_between_calls(self):
        first = validate_traceability_policy(None)
        first["required_steps"].append("receipt")
        second = validate_traceability_policy(None)
        self.assertEqual(len(second["required_steps"]),
                         len(DEFAULT_TRACEABILITY_POLICY["required_steps"]))


class StepOrderTests(unittest.TestCase):
    def test_receipt_ranks_first(self):
        self.assertEqual(step_rank("receipt"), 0)

    def test_delivery_ranks_last(self):
        self.assertEqual(step_rank("delivery"), len(HANDLING_STEP_ORDER) - 1)

    def test_unrecognised_step_rejected(self):
        with self.assertRaises(ValueError):
            step_rank("painting")


class RecordValidationTests(unittest.TestCase):
    def test_record_without_id_rejected(self):
        bad = _record("receipt", 1)
        del bad["id"]
        with self.assertRaises(ValueError):
            validate_record(bad)

    def test_record_without_lot_code_rejected(self):
        with self.assertRaises(ValueError):
            validate_record(_record("receipt", 1, lot="   "))

    def test_unknown_holder_rejected(self):
        bad = _record("receipt", 1)
        bad["holder"] = "somebody"
        with self.assertRaises(ValueError):
            validate_record(bad)

    def test_negative_retention_rejected(self):
        with self.assertRaises(ValueError):
            validate_record(_record("receipt", 1, retention=-1))

    def test_project_held_record_with_an_undertaking_rejected(self):
        bad = _record("receipt", 1)
        bad["access_undertaking"] = "AU-1"
        with self.assertRaises(ValueError):
            validate_record(bad)

    def test_duplicate_record_id_rejected(self):
        with self.assertRaises(ValueError):
            validate_records([_record("receipt", 1, identifier="r-1"),
                              _record("storage", 2, identifier="r-1")])

    def test_record_day_must_be_an_integer(self):
        with self.assertRaises(ValueError):
            validate_record(_record("receipt", 1.0))


class IdentityTests(unittest.TestCase):
    def test_matching_lot_codes_stay_on_the_chain(self):
        split = resolve_identity(validate_records(_full_chain()), LOT)
        self.assertEqual(len(split["on_chain"]), len(HANDLING_STEP_ORDER))
        self.assertEqual(split["identity_breaks"], [])

    def test_another_lot_with_no_cross_reference_is_a_break(self):
        records = _full_chain()
        records[2]["lot_code"] = "LOT-9999"
        split = resolve_identity(validate_records(records), LOT)
        self.assertEqual(split["identity_breaks"], ["rec-storage"])

    def test_a_cross_reference_bridges_a_relotted_record(self):
        records = _full_chain()
        records[2]["lot_code"] = "LOT-9999"
        records[2]["cross_reference"] = LOT
        split = resolve_identity(validate_records(records), LOT)
        self.assertEqual(split["bridged"], ["rec-storage"])
        self.assertEqual(split["identity_breaks"], [])

    def test_a_bridge_is_refused_when_the_policy_forbids_it(self):
        records = _full_chain()
        records[2]["lot_code"] = "LOT-9999"
        records[2]["cross_reference"] = LOT
        settings = validate_traceability_policy({"allow_cross_reference_bridge": False})
        split = resolve_identity(validate_records(records), LOT, settings)
        self.assertEqual(split["identity_breaks"], ["rec-storage"])

    def test_blank_lot_under_investigation_rejected(self):
        with self.assertRaises(ValueError):
            resolve_identity(validate_records(_full_chain()), "  ")


class DispositionTests(unittest.TestCase):
    def test_every_step_held_here_gives_full_coverage(self):
        disposition = dispose_steps(validate_records(_full_chain()))
        coverage = step_coverage(disposition["steps"])
        self.assertAlmostEqual(coverage["plain"], 1.0, places=9)
        self.assertAlmostEqual(coverage["credited"], 1.0, places=9)

    def test_an_external_record_is_credited_below_one(self):
        records = _full_chain()
        records[3]["holder"] = HELD_EXTERNALLY
        records[3]["access_undertaking"] = "AU-7"
        disposition = dispose_steps(validate_records(records))
        coverage = step_coverage(disposition["steps"])
        self.assertAlmostEqual(coverage["plain"], 1.0, places=9)
        self.assertAlmostEqual(coverage["credited"], 11.0 / 12.0, places=9)

    def test_an_external_record_without_an_undertaking_covers_nothing(self):
        records = _full_chain()
        records[3]["holder"] = HELD_EXTERNALLY
        records[3]["access_undertaking"] = ""
        disposition = dispose_steps(validate_records(records))
        self.assertEqual(disposition["unprotected_records"], ["rec-kitting"])
        self.assertEqual(disposition["steps"]["kitting"]["state"], "unprotected")

    def test_a_missing_step_is_named(self):
        records = [r for r in _full_chain() if r["step"] != "delivery"]
        disposition = dispose_steps(validate_records(records))
        coverage = step_coverage(disposition["steps"])
        self.assertEqual(coverage["uncovered_steps"], ["delivery"])

    def test_a_record_held_here_outranks_an_external_duplicate(self):
        records = _full_chain()
        records.append(_record("storage", 3, identifier="rec-storage-ext",
                               holder=HELD_EXTERNALLY, undertaking="AU-2"))
        disposition = dispose_steps(validate_records(records))
        self.assertEqual(disposition["steps"]["storage"]["state"], "held-here")

    def test_coverage_tolerance_is_small_but_nonzero(self):
        self.assertGreater(COVERAGE_TOLERANCE, 0.0)
        self.assertLess(COVERAGE_TOLERANCE, 1e-6)


class RetentionAndOrderTests(unittest.TestCase):
    def test_a_short_retention_is_named(self):
        records = _full_chain()
        records[1]["retention_years"] = 3
        shortfalls = retention_shortfalls(validate_records(records))
        self.assertEqual(shortfalls, ["rec-incoming-inspection"])

    def test_retention_exactly_on_the_floor_is_accepted(self):
        records = _full_chain()
        for record in records:
            record["retention_years"] = 10
        self.assertEqual(retention_shortfalls(validate_records(records)), [])

    def test_an_ordered_chain_has_no_order_breaks(self):
        self.assertEqual(order_breaks(validate_records(_full_chain())), [])

    def test_same_day_records_are_not_an_order_break(self):
        records = [_record(step, 5) for step in HANDLING_STEP_ORDER]
        self.assertEqual(order_breaks(validate_records(records)), [])

    def test_an_assembly_record_dated_before_receipt_is_an_order_break(self):
        records = _full_chain()
        records[4]["recorded_day"] = 1
        self.assertTrue(order_breaks(validate_records(records)))


class AssessmentTests(unittest.TestCase):
    def test_a_complete_chain_meets_the_class(self):
        result = assess_lot_traceability(_case())
        self.assertEqual(result["verdict"], TRACEABILITY_MEETS_CLASS_TWO)
        self.assertTrue(result["traceable"])
        self.assertEqual(result["findings"], [])

    def test_no_records_closes_on_chain_not_established(self):
        result = assess_lot_traceability(_case(records=[]))
        self.assertEqual(result["verdict"], CHAIN_NOT_ESTABLISHED)
        self.assertFalse(result["chain_established"])

    def test_no_receipt_record_closes_on_chain_not_established(self):
        records = [r for r in _full_chain() if r["step"] != "receipt"]
        result = assess_lot_traceability(_case(records=records))
        self.assertEqual(result["verdict"], CHAIN_NOT_ESTABLISHED)

    def test_an_identity_break_outranks_a_coverage_shortfall(self):
        records = _full_chain()
        records[2]["lot_code"] = "LOT-9999"
        result = assess_lot_traceability(_case(records=records))
        self.assertEqual(result["verdict"], LOT_IDENTITY_BROKEN)
        self.assertEqual(result["identity_breaks"], ["rec-storage"])

    def test_a_missing_undertaking_outranks_the_coverage_it_causes(self):
        records = _full_chain()
        records[3]["holder"] = HELD_EXTERNALLY
        records[3]["access_undertaking"] = ""
        result = assess_lot_traceability(_case(records=records))
        self.assertEqual(result["verdict"], ACCESS_UNDERTAKING_MISSING)

    def test_a_missing_step_is_coverage_short(self):
        records = [r for r in _full_chain() if r["step"] != "delivery"]
        result = assess_lot_traceability(_case(records=records))
        self.assertEqual(result["verdict"], STEP_COVERAGE_SHORT)
        self.assertEqual(result["uncovered_steps"], ["delivery"])

    def test_a_short_retention_closes_on_retention_below_floor(self):
        records = _full_chain()
        records[1]["retention_years"] = 2
        result = assess_lot_traceability(_case(records=records))
        self.assertEqual(result["verdict"], RETENTION_BELOW_FLOOR)

    def test_records_out_of_order_are_the_last_verdict_before_a_pass(self):
        records = _full_chain()
        records[4]["recorded_day"] = 1
        result = assess_lot_traceability(_case(records=records))
        self.assertEqual(result["verdict"], RECORDS_OUT_OF_ORDER)

    def test_a_bridged_record_is_reported_rather_than_hidden(self):
        records = _full_chain()
        records[2]["lot_code"] = "LOT-9999"
        records[2]["cross_reference"] = LOT
        result = assess_lot_traceability(_case(records=records))
        self.assertEqual(result["verdict"], TRACEABILITY_MEETS_CLASS_TWO)
        self.assertEqual(result["bridged_records"], ["rec-storage"])

    def test_external_records_everywhere_go_credited_coverage_short(self):
        records = _full_chain()
        for record in records:
            record["holder"] = HELD_EXTERNALLY
            record["access_undertaking"] = "AU-1"
        result = assess_lot_traceability(_case(records=records))
        self.assertEqual(result["verdict"], STEP_COVERAGE_SHORT)
        self.assertAlmostEqual(result["plain_step_coverage"], 1.0, places=9)
        self.assertAlmostEqual(result["credited_step_coverage"], 0.5, places=9)

    def test_case_without_lot_code_rejected(self):
        with self.assertRaises(ValueError):
            assess_lot_traceability({"records": _full_chain()})

    def test_case_without_records_rejected(self):
        with self.assertRaises(ValueError):
            assess_lot_traceability({"lot_code": LOT})

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_lot_traceability([LOT])

    def test_the_report_names_each_step_disposition(self):
        result = assess_lot_traceability(_case())
        self.assertEqual(len(result["step_disposition"]), len(HANDLING_STEP_ORDER))
        self.assertEqual(result["step_disposition"]["receipt"], "held-here")


if __name__ == "__main__":
    unittest.main(verbosity=0)
