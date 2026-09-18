"""Contract tests for the clause 5.2.15.1.1 single-failure line containment logic."""

import unittest

from e2020_single_failure_line_containment_logic import (
    CONTAINMENT_EXPOSURE_OVER_CEILING,
    CONTAINMENT_MULTI_LINE_FAILURE,
    CONTAINMENT_NOT_EVALUATED,
    CONTAINMENT_SATISFIED,
    CONTAINMENT_UNPROTECTED_LINE,
    DEFAULT_LINE_POLICY,
    FAILURE_POINT_KINDS,
    LINE_LOCAL,
    SHARED_COMMAND_PATH,
    SHARED_DRIVE,
    SHARED_HOUSEKEEPING_SUPPLY,
    SHARED_RETURN,
    SHARED_SOURCE_STAGE,
    assess_single_failure_containment,
    categorize_failure_point_kind,
    exposed_line_fraction,
    failure_fan_out,
    find_multi_line_failures,
    lines_disabled_by,
    protected_line_ids,
    shared_dependency_lines,
    unprotected_line_ids,
    untraced_protected_lines,
    validate_failure_points,
    validate_line_inventory,
    validate_line_policy,
)


def _policy(**overrides):
    policy = dict(DEFAULT_LINE_POLICY)
    policy.update(overrides)
    return policy


def _lines(*ids, **kwargs):
    unprotected = set(kwargs.get("unprotected", ()))
    return [{"id": line_id, "protected": line_id not in unprotected} for line_id in ids]


def _local(line_id):
    return {"id": "fp-local-%s" % line_id, "kind": LINE_LOCAL, "line": line_id,
            "disables": [line_id]}


def _design(**overrides):
    design = {
        "lines": _lines("l1", "l2", "l3"),
        "failure_points": [
            _local("l1"),
            _local("l2"),
            _local("l3"),
            {"id": "fp-drive-a", "kind": SHARED_DRIVE, "disables": ["l1"]},
        ],
    }
    design.update(overrides)
    return design


def _inventory(*ids, **kwargs):
    return validate_line_inventory(_lines(*ids, **kwargs))


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(validate_line_policy(DEFAULT_LINE_POLICY), DEFAULT_LINE_POLICY)

    def test_a_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_line_policy("one line")

    def test_a_zero_line_bound_rejected(self):
        with self.assertRaises(ValueError):
            validate_line_policy(_policy(max_lines_per_failure=0))

    def test_a_boolean_line_bound_rejected(self):
        with self.assertRaises(ValueError):
            validate_line_policy(_policy(max_lines_per_failure=True))

    def test_an_exposure_ceiling_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_line_policy(_policy(max_exposed_line_fraction=1.4))

    def test_a_non_boolean_tracing_requirement_rejected(self):
        with self.assertRaises(ValueError):
            validate_line_policy(_policy(require_every_line_traced="yes"))


class InventoryTests(unittest.TestCase):
    def test_inventory_keys_every_declared_line(self):
        inventory = _inventory("l1", "l2")
        self.assertEqual(sorted(inventory), ["l1", "l2"])

    def test_a_duplicate_line_rejected(self):
        with self.assertRaises(ValueError):
            validate_line_inventory(
                [{"id": "l1", "protected": True}, {"id": "l1", "protected": True}]
            )

    def test_a_line_without_a_protection_flag_rejected(self):
        with self.assertRaises(ValueError):
            validate_line_inventory([{"id": "l1"}])

    def test_an_empty_line_list_rejected(self):
        with self.assertRaises(ValueError):
            validate_line_inventory([])

    def test_protected_and_unprotected_lines_separate(self):
        inventory = _inventory("l1", "l2", "l3", unprotected=("l3",))
        self.assertEqual(protected_line_ids(inventory), ("l1", "l2"))
        self.assertEqual(unprotected_line_ids(inventory), ("l3",))


class KindTests(unittest.TestCase):
    def test_every_known_kind_round_trips(self):
        for kind in FAILURE_POINT_KINDS:
            self.assertEqual(categorize_failure_point_kind(kind), kind)

    def test_an_unrecognised_kind_rejected(self):
        with self.assertRaises(ValueError):
            categorize_failure_point_kind("shared-vibe")

    def test_an_empty_kind_rejected(self):
        with self.assertRaises(ValueError):
            categorize_failure_point_kind("  ")


class DisabledLineTests(unittest.TestCase):
    def test_a_shared_drive_names_the_lines_it_takes(self):
        inventory = _inventory("l1", "l2", "l3")
        point = {"id": "fp-1", "kind": SHARED_DRIVE, "disables": ["l2", "l1"]}
        self.assertEqual(lines_disabled_by(point, inventory), ("l1", "l2"))

    def test_a_line_local_point_on_its_own_line_accepted(self):
        inventory = _inventory("l1", "l2")
        self.assertEqual(lines_disabled_by(_local("l1"), inventory), ("l1",))

    def test_a_line_local_point_reaching_past_its_line_rejected(self):
        inventory = _inventory("l1", "l2")
        point = {"id": "fp-1", "kind": LINE_LOCAL, "line": "l1",
                 "disables": ["l1", "l2"]}
        with self.assertRaises(ValueError):
            lines_disabled_by(point, inventory)

    def test_a_point_naming_an_unknown_line_rejected(self):
        inventory = _inventory("l1")
        point = {"id": "fp-1", "kind": SHARED_RETURN, "disables": ["l9"]}
        with self.assertRaises(ValueError):
            lines_disabled_by(point, inventory)

    def test_a_point_naming_the_same_line_twice_rejected(self):
        inventory = _inventory("l1", "l2")
        point = {"id": "fp-1", "kind": SHARED_RETURN, "disables": ["l1", "l1"]}
        with self.assertRaises(ValueError):
            lines_disabled_by(point, inventory)

    def test_a_point_disabling_nothing_rejected(self):
        inventory = _inventory("l1")
        point = {"id": "fp-1", "kind": SHARED_RETURN, "disables": []}
        with self.assertRaises(ValueError):
            lines_disabled_by(point, inventory)


class FanOutTests(unittest.TestCase):
    def test_fan_out_counts_only_protected_lines(self):
        inventory = _inventory("l1", "l2", "l3", unprotected=("l2",))
        point = {"id": "fp-1", "kind": SHARED_SOURCE_STAGE,
                 "disables": ["l1", "l2", "l3"]}
        self.assertEqual(failure_fan_out(point, inventory), 2)

    def test_a_shared_point_over_the_bound_is_found(self):
        inventory = _inventory("l1", "l2")
        records = validate_failure_points(
            [{"id": "fp-1", "kind": SHARED_COMMAND_PATH, "disables": ["l1", "l2"]}],
            inventory,
        )
        offenders = find_multi_line_failures(records)
        self.assertEqual([record["id"] for record in offenders], ["fp-1"])

    def test_offenders_are_ordered_worst_first(self):
        inventory = _inventory("l1", "l2", "l3")
        records = validate_failure_points(
            [
                {"id": "fp-two", "kind": SHARED_DRIVE, "disables": ["l1", "l2"]},
                {"id": "fp-three", "kind": SHARED_RETURN,
                 "disables": ["l1", "l2", "l3"]},
            ],
            inventory,
        )
        offenders = find_multi_line_failures(records)
        self.assertEqual([record["id"] for record in offenders],
                         ["fp-three", "fp-two"])

    def test_a_duplicate_failure_point_id_rejected(self):
        inventory = _inventory("l1", "l2")
        with self.assertRaises(ValueError):
            validate_failure_points([_local("l1"), _local("l1")], inventory)

    def test_an_empty_failure_point_list_rejected(self):
        inventory = _inventory("l1")
        with self.assertRaises(ValueError):
            validate_failure_points([], inventory)


class ExposureTests(unittest.TestCase):
    def test_exposure_counts_protected_lines_on_shared_hardware(self):
        inventory = _inventory("l1", "l2", "l3")
        records = validate_failure_points(
            [
                _local("l1"),
                {"id": "fp-hk", "kind": SHARED_HOUSEKEEPING_SUPPLY,
                 "disables": ["l2"]},
                {"id": "fp-ret", "kind": SHARED_RETURN, "disables": ["l3"]},
            ],
            inventory,
        )
        self.assertEqual(shared_dependency_lines(records, inventory), ("l2", "l3"))
        self.assertAlmostEqual(
            exposed_line_fraction(records, inventory), 2.0 / 3.0, places=9
        )

    def test_a_line_local_point_adds_no_exposure(self):
        inventory = _inventory("l1", "l2")
        records = validate_failure_points([_local("l1"), _local("l2")], inventory)
        self.assertAlmostEqual(exposed_line_fraction(records, inventory), 0.0,
                               places=9)

    def test_exposure_exactly_on_the_ceiling_is_accepted(self):
        design = {
            "lines": _lines("l1", "l2", "l3", "l4"),
            "failure_points": [
                _local("l1"), _local("l2"), _local("l3"), _local("l4"),
                {"id": "fp-drive-a", "kind": SHARED_DRIVE, "disables": ["l1"]},
            ],
        }
        inventory = validate_line_inventory(design["lines"])
        records = validate_failure_points(design["failure_points"], inventory)
        self.assertAlmostEqual(exposed_line_fraction(records, inventory), 0.25,
                               places=9)
        result = assess_single_failure_containment(
            design, _policy(max_exposed_line_fraction=0.25)
        )
        self.assertEqual(result["verdict"], CONTAINMENT_SATISFIED)

    def test_exposure_with_no_protected_line_rejected(self):
        inventory = _inventory("l1", unprotected=("l1",))
        records = validate_failure_points([_local("l1")], inventory)
        with self.assertRaises(ValueError):
            exposed_line_fraction(records, inventory)


class UntracedTests(unittest.TestCase):
    def test_an_untraced_protected_line_is_named(self):
        inventory = _inventory("l1", "l2", "l3")
        records = validate_failure_points([_local("l1"), _local("l2")], inventory)
        self.assertEqual(untraced_protected_lines(records, inventory), ("l3",))

    def test_a_fully_traced_design_leaves_nothing_untraced(self):
        inventory = _inventory("l1", "l2")
        records = validate_failure_points([_local("l1"), _local("l2")], inventory)
        self.assertEqual(untraced_protected_lines(records, inventory), ())


class DesignAssessmentTests(unittest.TestCase):
    def test_a_contained_design_is_satisfied(self):
        result = assess_single_failure_containment(_design())
        self.assertEqual(result["verdict"], CONTAINMENT_SATISFIED)
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["worst_fan_out"], 1)

    def test_a_shared_drive_taking_two_lines_is_the_clause_failure(self):
        result = assess_single_failure_containment(
            _design(
                failure_points=[
                    _local("l1"), _local("l2"), _local("l3"),
                    {"id": "fp-drive-a", "kind": SHARED_DRIVE,
                     "disables": ["l1", "l2"]},
                ]
            )
        )
        self.assertEqual(result["verdict"], CONTAINMENT_MULTI_LINE_FAILURE)
        self.assertEqual(result["worst_fan_out"], 2)

    def test_an_untraced_line_outranks_a_multi_line_failure(self):
        result = assess_single_failure_containment(
            _design(
                failure_points=[
                    _local("l1"),
                    {"id": "fp-drive-a", "kind": SHARED_DRIVE,
                     "disables": ["l1", "l2"]},
                ]
            )
        )
        self.assertEqual(result["verdict"], CONTAINMENT_NOT_EVALUATED)
        self.assertEqual(result["untraced_protected_lines"], ("l3",))

    def test_tracing_can_be_waived_by_policy(self):
        design = _design(
            failure_points=[
                _local("l1"), _local("l2"),
                {"id": "fp-drive-a", "kind": SHARED_DRIVE, "disables": ["l1"]},
            ]
        )
        result = assess_single_failure_containment(
            design, _policy(require_every_line_traced=False)
        )
        self.assertEqual(result["verdict"], CONTAINMENT_SATISFIED)
        self.assertEqual(result["untraced_protected_lines"], ("l3",))

    def test_exposure_over_the_ceiling_is_reported_on_its_own(self):
        result = assess_single_failure_containment(
            _design(
                failure_points=[
                    _local("l1"), _local("l2"), _local("l3"),
                    {"id": "fp-drive-a", "kind": SHARED_DRIVE, "disables": ["l1"]},
                    {"id": "fp-ret-b", "kind": SHARED_RETURN, "disables": ["l2"]},
                ]
            )
        )
        self.assertEqual(result["verdict"], CONTAINMENT_EXPOSURE_OVER_CEILING)
        self.assertEqual(result["multi_line_failures"], [])
        self.assertAlmostEqual(result["exposed_line_fraction"], 2.0 / 3.0, places=9)

    def test_an_unprotected_line_is_reported_below_the_bound(self):
        result = assess_single_failure_containment(
            _design(
                lines=_lines("l1", "l2", "l3", "l4", unprotected=("l4",)),
                failure_points=[
                    _local("l1"), _local("l2"), _local("l3"), _local("l4"),
                    {"id": "fp-drive-a", "kind": SHARED_DRIVE, "disables": ["l1"]},
                ],
            )
        )
        self.assertEqual(result["verdict"], CONTAINMENT_UNPROTECTED_LINE)
        self.assertEqual(result["unprotected_lines"], ("l4",))

    def test_a_non_mapping_design_rejected(self):
        with self.assertRaises(ValueError):
            assess_single_failure_containment(["l1", "l2"])

    def test_a_design_with_no_lines_rejected(self):
        with self.assertRaises(ValueError):
            assess_single_failure_containment({"failure_points": []})

    def test_every_finding_is_a_readable_sentence(self):
        result = assess_single_failure_containment(
            _design(
                failure_points=[
                    _local("l1"), _local("l2"), _local("l3"),
                    {"id": "fp-src", "kind": SHARED_SOURCE_STAGE,
                     "disables": ["l1", "l2", "l3"]},
                ]
            )
        )
        self.assertTrue(result["findings"])
        for note in result["findings"]:
            self.assertIsInstance(note, str)
            self.assertGreater(len(note), 20)

    def test_every_failure_point_is_recorded_once(self):
        result = assess_single_failure_containment(_design())
        ids = [record["id"] for record in result["failure_points"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(ids), 4)


if __name__ == "__main__":
    unittest.main()
