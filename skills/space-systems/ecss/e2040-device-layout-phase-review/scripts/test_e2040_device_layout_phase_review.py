"""Contract test for the device-layout-phase-review leaf (stdlib unittest)."""

import unittest

from e2040_device_layout_phase_review_logic import (
    ACTION_CLOSED,
    ACTION_OPEN,
    FINDING_CARRIED_ACTION_OPEN,
    FINDING_INPUT_ABSENT,
    FINDING_INPUT_IN_DRAFT,
    FINDING_INPUT_LATE,
    FINDING_MAJOR_ITEM_OPEN,
    FINDING_MINOR_ITEMS_ABOVE_CAP,
    FINDING_MINOR_ITEM_UNDATED,
    FINDING_MINOR_ITEM_UNOWNED,
    OUTCOME_PASS,
    OUTCOME_PASS_WITH_ACTIONS,
    OUTCOME_REPEAT,
    SEVERITY_MAJOR,
    SEVERITY_MINOR,
    STATUS_ABSENT,
    STATUS_DRAFT,
    STATUS_ISSUED,
    assess_device_layout_phase_review,
    check_input,
    disposition_findings,
    group_items_by_severity,
    lead_working_days,
    required_inputs,
    validate_action,
    validate_input_record,
    validate_item,
    validate_review,
)


def review(**kw):
    record = {
        "device_id": "DEV-1",
        "review_day": 100,
        "required_lead_working_days": 10,
        "minor_item_cap": 5,
        "evaluation_route": False,
    }
    record.update(kw)
    return record


def input_record(name, status=STATUS_ISSUED, distributed_day=85):
    return {"name": name, "status": status, "distributed_day": distributed_day}


def full_inputs(rev):
    return [input_record(name) for name in required_inputs(rev)]


def minor(iid="RID-1", owner="lead-designer", close_out_day=120):
    return {
        "id": iid,
        "severity": SEVERITY_MINOR,
        "owner": owner,
        "close_out_day": close_out_day,
    }


def major(iid="RID-9"):
    return {
        "id": iid,
        "severity": SEVERITY_MAJOR,
        "owner": "lead-designer",
        "close_out_day": 110,
    }


class TestValidateReview(unittest.TestCase):
    def test_normalizes_a_good_record(self):
        norm = validate_review(review())
        self.assertEqual(norm["review_day"], 100)
        self.assertEqual(norm["minor_item_cap"], 5)

    def test_non_mapping_raises(self):
        with self.assertRaises(ValueError):
            validate_review("DEV-1")

    def test_negative_lead_time_raises(self):
        with self.assertRaises(ValueError):
            validate_review(review(required_lead_working_days=-1))

    def test_negative_cap_raises(self):
        with self.assertRaises(ValueError):
            validate_review(review(minor_item_cap=-2))

    def test_non_boolean_route_raises(self):
        with self.assertRaises(ValueError):
            validate_review(review(evaluation_route="yes"))


class TestRequiredInputs(unittest.TestCase):
    def test_escc_specification_is_conditional(self):
        self.assertNotIn(
            "preliminary-escc-detail-specification", required_inputs(review())
        )

    def test_evaluation_route_adds_the_escc_specification(self):
        self.assertIn(
            "preliminary-escc-detail-specification",
            required_inputs(review(evaluation_route=True)),
        )

    def test_unknown_input_name_raises(self):
        with self.assertRaises(ValueError):
            validate_input_record(input_record("coffee-order"))

    def test_unknown_input_status_raises(self):
        with self.assertRaises(ValueError):
            validate_input_record(
                input_record("layout-verification-report", status="nearly")
            )


class TestLeadTime(unittest.TestCase):
    def test_lead_time_is_the_day_difference(self):
        self.assertEqual(lead_working_days(85, 100), 15)

    def test_same_day_distribution_is_zero(self):
        self.assertEqual(lead_working_days(100, 100), 0)

    def test_non_integer_day_raises(self):
        with self.assertRaises(ValueError):
            lead_working_days(85.5, 100)


class TestCheckInput(unittest.TestCase):
    def test_issued_and_early_is_clean(self):
        self.assertEqual(
            check_input(input_record("layout-verification-report"), review()), []
        )

    def test_exactly_on_the_lead_time_is_clean(self):
        self.assertEqual(
            check_input(
                input_record("layout-verification-report", distributed_day=90),
                review(),
            ),
            [],
        )

    def test_one_day_inside_the_lead_time_is_late(self):
        self.assertIn(
            FINDING_INPUT_LATE,
            check_input(
                input_record("layout-verification-report", distributed_day=91),
                review(),
            ),
        )

    def test_absent_input_short_circuits(self):
        self.assertEqual(
            check_input(
                input_record("layout-verification-report", status=STATUS_ABSENT),
                review(),
            ),
            [FINDING_INPUT_ABSENT],
        )

    def test_draft_input_is_a_finding(self):
        self.assertIn(
            FINDING_INPUT_IN_DRAFT,
            check_input(
                input_record("layout-verification-report", status=STATUS_DRAFT),
                review(),
            ),
        )

    def test_undistributed_input_is_late(self):
        self.assertIn(
            FINDING_INPUT_LATE,
            check_input(
                input_record("layout-verification-report", distributed_day=None),
                review(),
            ),
        )


class TestItems(unittest.TestCase):
    def test_grouping_splits_by_severity(self):
        grouped = group_items_by_severity([minor(), major()])
        self.assertEqual(len(grouped[SEVERITY_MINOR]), 1)
        self.assertEqual(len(grouped[SEVERITY_MAJOR]), 1)

    def test_unknown_severity_raises(self):
        with self.assertRaises(ValueError):
            validate_item({"id": "RID-2", "severity": "cosmetic"})

    def test_duplicate_item_id_raises(self):
        with self.assertRaises(ValueError):
            group_items_by_severity([minor("RID-1"), minor("RID-1")])

    def test_major_item_blocks(self):
        self.assertIn(
            ("RID-9", FINDING_MAJOR_ITEM_OPEN),
            disposition_findings([major()], review()),
        )

    def test_unowned_minor_blocks(self):
        self.assertIn(
            ("RID-1", FINDING_MINOR_ITEM_UNOWNED),
            disposition_findings([minor(owner=None)], review()),
        )

    def test_undated_minor_blocks(self):
        self.assertIn(
            ("RID-1", FINDING_MINOR_ITEM_UNDATED),
            disposition_findings([minor(close_out_day=None)], review()),
        )

    def test_minors_inside_the_cap_do_not_block(self):
        items = [minor("RID-%d" % n) for n in range(5)]
        self.assertEqual(disposition_findings(items, review()), [])

    def test_minors_above_the_cap_block(self):
        items = [minor("RID-%d" % n) for n in range(6)]
        self.assertIn(
            ("DEV-1", FINDING_MINOR_ITEMS_ABOVE_CAP),
            disposition_findings(items, review()),
        )


class TestActions(unittest.TestCase):
    def test_closed_action_validates(self):
        self.assertEqual(
            validate_action({"id": "A-1", "status": ACTION_CLOSED})["status"],
            ACTION_CLOSED,
        )

    def test_unknown_action_status_raises(self):
        with self.assertRaises(ValueError):
            validate_action({"id": "A-1", "status": "in-progress-ish"})


class TestAssessment(unittest.TestCase):
    def test_clean_gate_passes(self):
        rev = review()
        report = assess_device_layout_phase_review(rev, full_inputs(rev))
        self.assertEqual(report["outcome"], OUTCOME_PASS)
        self.assertTrue(report["holdable"])

    def test_dated_minor_items_give_pass_with_actions(self):
        rev = review()
        report = assess_device_layout_phase_review(
            rev, full_inputs(rev), [], [minor()]
        )
        self.assertEqual(report["outcome"], OUTCOME_PASS_WITH_ACTIONS)
        self.assertEqual(report["open_minor_ids"], ["RID-1"])

    def test_major_item_forces_a_repeat(self):
        rev = review()
        report = assess_device_layout_phase_review(
            rev, full_inputs(rev), [], [major()]
        )
        self.assertEqual(report["outcome"], OUTCOME_REPEAT)

    def test_open_carried_action_forces_a_repeat(self):
        rev = review()
        report = assess_device_layout_phase_review(
            rev, full_inputs(rev), [{"id": "A-7", "status": ACTION_OPEN}]
        )
        self.assertEqual(report["outcome"], OUTCOME_REPEAT)
        self.assertIn(("A-7", FINDING_CARRIED_ACTION_OPEN), report["blocking_findings"])

    def test_missing_input_makes_the_gate_unholdable(self):
        rev = review()
        inputs = full_inputs(rev)[1:]
        report = assess_device_layout_phase_review(rev, inputs)
        self.assertFalse(report["holdable"])
        self.assertEqual(report["outcome"], OUTCOME_REPEAT)

    def test_late_input_is_reported_with_its_lead_time(self):
        rev = review()
        inputs = full_inputs(rev)
        inputs[0] = input_record(inputs[0]["name"], distributed_day=99)
        report = assess_device_layout_phase_review(rev, inputs)
        self.assertEqual(report["lead_working_days"][inputs[0]["name"]], 1)
        self.assertIn((inputs[0]["name"], FINDING_INPUT_LATE), report["entry_findings"])

    def test_evaluation_route_requires_the_escc_specification(self):
        rev = review(evaluation_route=True)
        inputs = [
            input_record(name)
            for name in required_inputs(rev)
            if name != "preliminary-escc-detail-specification"
        ]
        report = assess_device_layout_phase_review(rev, inputs)
        self.assertIn(
            ("preliminary-escc-detail-specification", FINDING_INPUT_ABSENT),
            report["entry_findings"],
        )

    def test_duplicate_input_raises(self):
        rev = review()
        inputs = full_inputs(rev)
        inputs.append(input_record(inputs[0]["name"]))
        with self.assertRaises(ValueError):
            assess_device_layout_phase_review(rev, inputs)

    def test_duplicate_action_raises(self):
        rev = review()
        with self.assertRaises(ValueError):
            assess_device_layout_phase_review(
                rev,
                full_inputs(rev),
                [{"id": "A-1", "status": ACTION_CLOSED}] * 2,
            )

    def test_non_list_inputs_raises(self):
        with self.assertRaises(ValueError):
            assess_device_layout_phase_review(review(), input_record("layout-verification-report"))


if __name__ == "__main__":
    unittest.main()
