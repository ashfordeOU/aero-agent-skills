"""Contract tests for the clause 6.5.4 class 3 traceability depth assessment.

Every workflow step the SKILL.md sets out is exercised here, together with the
stop conditions the gate 3 contract reviews: a record with no date, a chain that
loops, a chain dying on a reference nobody supplies, a pooled batch claiming a
depth above the cap, a record dated after the installation it supplied, and a
population sitting exactly on the coverage floor.
"""

import unittest

from q6013_class_3_traceability_logic import (
    CHAIN_UNRESOLVED,
    COVERAGE_BELOW_FLOOR,
    DATE_ORDER_CONTRADICTED,
    DEFAULT_TRACEABILITY_POLICY,
    DEPTH_RANKS,
    POOLED_DEPTH_CEILING,
    TRACEABLE_TO_DEPTH,
    TRACEABLE_WITH_SHORTFALLS,
    assess_traceability_depth,
    chain_depth,
    coverage_meets_floor,
    depth_rank,
    effective_depth,
    index_records,
    resolve_chain,
    validate_installation,
    validate_record,
    validate_traceability_policy,
)


def _record(reference, depth="manufacturing-lot", day=10, parent=None,
            pooled=False, goods_in=None):
    record = {
        "reference": reference,
        "depth": depth,
        "day": day,
        "parent": parent,
        "pooled": pooled,
    }
    if goods_in is not None:
        record["goods_in"] = goods_in
    return record


def _records():
    return [
        _record("gi-1", day=10, parent=None),
        _record("kit-1", day=20, parent="gi-1"),
    ]


def _installations(count=10, record="kit-1", day=30):
    return [
        {"part_id": "p-%02d" % i, "assembly": "asm-1", "record": record, "day": day}
        for i in range(1, count + 1)
    ]


def _policy(**overrides):
    policy = dict(DEFAULT_TRACEABILITY_POLICY)
    policy.update(overrides)
    return policy


def _case(**overrides):
    case = {"records": _records(), "installations": _installations()}
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        settings = validate_traceability_policy(None)
        self.assertEqual(settings["required_depth"], "delivery-batch")
        self.assertTrue(settings["require_goods_in_root"])

    def test_unknown_policy_key_rejected(self):
        with self.assertRaises(ValueError):
            validate_traceability_policy({"coverage_percent": 90})

    def test_unknown_required_depth_rejected(self):
        with self.assertRaises(ValueError):
            validate_traceability_policy({"required_depth": "wafer-map"})

    def test_coverage_floor_above_the_whole_population_rejected(self):
        with self.assertRaises(ValueError):
            validate_traceability_policy(
                {"coverage_numerator": 11, "coverage_denominator": 10}
            )

    def test_zero_chain_hops_rejected(self):
        with self.assertRaises(ValueError):
            validate_traceability_policy({"max_chain_hops": 0})


class DepthTokenTests(unittest.TestCase):
    def test_depth_ranks_are_ordered_weakest_first(self):
        self.assertLess(DEPTH_RANKS["part-number-only"], DEPTH_RANKS["delivery-batch"])
        self.assertLess(DEPTH_RANKS["manufacturing-lot"], DEPTH_RANKS["unit-serial"])

    def test_unknown_depth_token_rejected(self):
        with self.assertRaises(ValueError):
            depth_rank("wafer-coordinate")

    def test_blank_depth_token_rejected(self):
        with self.assertRaises(ValueError):
            depth_rank("   ")

    def test_pooled_record_cannot_claim_above_the_ceiling(self):
        record = validate_record(_record("pool-1", depth="unit-serial", pooled=True))
        self.assertEqual(effective_depth(record), POOLED_DEPTH_CEILING)

    def test_unpooled_record_keeps_its_declared_depth(self):
        record = validate_record(_record("lot-1", depth="unit-serial"))
        self.assertEqual(effective_depth(record), DEPTH_RANKS["unit-serial"])


class RecordValidationTests(unittest.TestCase):
    def test_record_without_reference_rejected(self):
        with self.assertRaises(ValueError):
            validate_record(_record("  "))

    def test_record_without_day_rejected(self):
        record = _record("gi-1")
        del record["day"]
        with self.assertRaises(ValueError):
            validate_record(record)

    def test_record_with_float_day_rejected(self):
        with self.assertRaises(ValueError):
            validate_record(_record("gi-1", day=10.0))

    def test_record_with_blank_parent_rejected(self):
        with self.assertRaises(ValueError):
            validate_record(_record("kit-1", parent="   "))

    def test_duplicate_record_reference_rejected(self):
        with self.assertRaises(ValueError):
            index_records([_record("gi-1"), _record("gi-1")])

    def test_parentless_record_defaults_to_a_goods_in_root(self):
        self.assertTrue(validate_record(_record("gi-1"))["goods_in"])

    def test_installation_without_assembly_rejected(self):
        with self.assertRaises(ValueError):
            validate_installation({"part_id": "p-01", "record": "kit-1", "day": 30})


class ChainResolutionTests(unittest.TestCase):
    def test_chain_reaches_the_goods_in_root(self):
        walk = resolve_chain(index_records(_records()), "kit-1", 6)
        self.assertTrue(walk["resolved"])
        self.assertEqual(walk["chain"][-1]["reference"], "gi-1")

    def test_chain_dying_on_an_unknown_reference_is_unresolved(self):
        walk = resolve_chain(index_records(_records()), "kit-9", 6)
        self.assertFalse(walk["resolved"])
        self.assertEqual(walk["missing_reference"], "kit-9")

    def test_looping_chain_rejected(self):
        records = [
            _record("a", parent="b", goods_in=False),
            _record("b", parent="a", goods_in=False),
        ]
        with self.assertRaises(ValueError):
            resolve_chain(index_records(records), "a", 6)

    def test_chain_longer_than_the_hop_limit_is_truncated(self):
        records = [_record("r-8", parent=None)]
        for i in range(7, 0, -1):
            records.append(_record("r-%d" % i, parent="r-%d" % (i + 1)))
        walk = resolve_chain(index_records(records), "r-1", 6)
        self.assertTrue(walk["truncated"])
        self.assertFalse(walk["resolved"])

    def test_weakest_link_sets_the_chain_depth(self):
        records = [
            _record("gi-1", depth="part-number-only", parent=None),
            _record("kit-1", depth="unit-serial", parent="gi-1"),
        ]
        walk = resolve_chain(index_records(records), "kit-1", 6)
        weakest = chain_depth(walk["chain"])
        self.assertEqual(weakest["rank"], DEPTH_RANKS["part-number-only"])
        self.assertEqual(weakest["set_by"], "gi-1")

    def test_empty_chain_rejected(self):
        with self.assertRaises(ValueError):
            chain_depth([])


class CoverageArithmeticTests(unittest.TestCase):
    def test_population_exactly_on_the_floor_is_met(self):
        self.assertTrue(coverage_meets_floor(9, 10, 9, 10))

    def test_population_one_below_the_floor_is_not_met(self):
        self.assertFalse(coverage_meets_floor(8, 10, 9, 10))

    def test_met_above_the_total_rejected(self):
        with self.assertRaises(ValueError):
            coverage_meets_floor(11, 10, 9, 10)

    def test_zero_total_rejected(self):
        with self.assertRaises(ValueError):
            coverage_meets_floor(0, 0, 9, 10)

    def test_float_count_rejected(self):
        with self.assertRaises(ValueError):
            coverage_meets_floor(9.0, 10, 9, 10)


class AssessmentTests(unittest.TestCase):
    def test_full_depth_population_is_traceable(self):
        result = assess_traceability_depth(_case())
        self.assertEqual(result["verdict"], TRACEABLE_TO_DEPTH)
        self.assertTrue(result["traceable"])
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["coverage_fraction"], 1.0, places=9)

    def test_one_shortfall_still_meets_the_coverage_floor(self):
        records = _records()
        records.append(_record("kit-2", depth="part-number-only", day=20, parent="gi-1"))
        installations = _installations(9)
        installations.append(
            {"part_id": "p-10", "assembly": "asm-1", "record": "kit-2", "day": 30}
        )
        result = assess_traceability_depth(
            _case(records=records, installations=installations)
        )
        self.assertEqual(result["verdict"], TRACEABLE_WITH_SHORTFALLS)
        self.assertEqual(result["shortfall_parts"], ["p-10"])
        self.assertAlmostEqual(result["coverage_fraction"], 0.9, places=9)

    def test_two_shortfalls_drop_below_the_coverage_floor(self):
        records = _records()
        records.append(_record("kit-2", depth="part-number-only", day=20, parent="gi-1"))
        installations = _installations(8)
        for index in (9, 10):
            installations.append(
                {"part_id": "p-%02d" % index, "assembly": "asm-1",
                 "record": "kit-2", "day": 30}
            )
        result = assess_traceability_depth(
            _case(records=records, installations=installations)
        )
        self.assertEqual(result["verdict"], COVERAGE_BELOW_FLOOR)
        self.assertEqual(result["installations_at_depth"], 8)

    def test_pooling_pulls_a_serialised_chain_down_to_the_batch(self):
        records = [
            _record("gi-1", depth="unit-serial", parent=None),
            _record("pool-1", depth="unit-serial", day=20, parent="gi-1", pooled=True),
        ]
        result = assess_traceability_depth(
            _case(records=records, installations=_installations(4, record="pool-1"))
        )
        self.assertEqual(result["verdict"], TRACEABLE_TO_DEPTH)
        self.assertEqual(result["per_installation"][0]["achieved_depth"], "delivery-batch")

    def test_pooling_below_a_deeper_requirement_is_a_shortfall(self):
        records = [
            _record("gi-1", depth="unit-serial", parent=None),
            _record("pool-1", depth="unit-serial", day=20, parent="gi-1", pooled=True),
        ]
        result = assess_traceability_depth(
            _case(
                records=records,
                installations=_installations(4, record="pool-1"),
                policy=_policy(required_depth="manufacturing-lot"),
            )
        )
        self.assertEqual(result["verdict"], COVERAGE_BELOW_FLOOR)

    def test_unresolved_chain_outranks_every_other_finding(self):
        installations = _installations(9)
        installations.append(
            {"part_id": "p-10", "assembly": "asm-1", "record": "kit-9", "day": 30}
        )
        result = assess_traceability_depth(_case(installations=installations))
        self.assertEqual(result["verdict"], CHAIN_UNRESOLVED)
        self.assertEqual(result["unresolved_parts"], ["p-10"])

    def test_record_dated_after_the_installation_is_a_contradiction(self):
        records = [
            _record("gi-1", parent=None, day=10),
            _record("kit-1", parent="gi-1", day=99),
        ]
        result = assess_traceability_depth(_case(records=records))
        self.assertEqual(result["verdict"], DATE_ORDER_CONTRADICTED)
        self.assertEqual(len(result["date_conflict_parts"]), 10)

    def test_root_that_is_not_a_goods_in_entry_leaves_the_chain_open(self):
        records = [_record("kit-1", parent=None, day=20, goods_in=False)]
        result = assess_traceability_depth(_case(records=records))
        self.assertEqual(result["verdict"], CHAIN_UNRESOLVED)

    def test_goods_in_root_requirement_can_be_stood_down(self):
        records = [_record("kit-1", parent=None, day=20, goods_in=False)]
        result = assess_traceability_depth(
            _case(records=records, policy=_policy(require_goods_in_root=False))
        )
        self.assertEqual(result["verdict"], TRACEABLE_TO_DEPTH)

    def test_duplicate_installed_part_rejected(self):
        installations = _installations(2)
        installations[1]["part_id"] = installations[0]["part_id"]
        with self.assertRaises(ValueError):
            assess_traceability_depth(_case(installations=installations))

    def test_missing_installations_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_traceability_depth({"records": _records()})

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_traceability_depth(["records"])

    def test_empty_installation_sequence_rejected(self):
        with self.assertRaises(ValueError):
            assess_traceability_depth(_case(installations=[]))

    def test_depth_setting_link_is_named_per_installation(self):
        records = [
            _record("gi-1", depth="delivery-batch", parent=None),
            _record("kit-1", depth="unit-serial", day=20, parent="gi-1"),
        ]
        result = assess_traceability_depth(_case(records=records))
        self.assertEqual(result["per_installation"][0]["depth_set_by"], "gi-1")


if __name__ == "__main__":
    unittest.main()
