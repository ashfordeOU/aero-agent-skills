"""Contract tests for the clause 10.1 die procurement general approach."""

import unittest

from q6012_die_procurement_general_approach_logic import (
    CANONICAL_ROUTE,
    MAX_START_ADJUSTMENT,
    STAGE_UNITS,
    analytic_wafer_start,
    assess_die_procurement_approach,
    cumulative_survival,
    delivered_quantity,
    forward_projection,
    ownership_gaps,
    size_wafer_start,
    validate_route,
    validate_stage,
)

YIELDS = {
    "wafer_fabrication": 0.5,
    "wafer_acceptance": 1.0,
    "dicing": 1.0,
    "die_visual_inspection": 1.0,
    "die_screening": 0.5,
    "die_lot_acceptance": 1.0,
    "packing_and_storage": 1.0,
    "delivery_acceptance": 1.0,
}


def full_stages(**overrides):
    stages = []
    for name in CANONICAL_ROUTE:
        stages.append(
            {
                "stage": name,
                "yield_fraction": overrides.get(name, YIELDS[name]),
                "owner": "supplier" if name != "delivery_acceptance" else "customer",
                "exit_criterion": "%s report signed" % name.replace("_", " "),
            }
        )
    return stages


def full_case(**overrides):
    case = {
        "stages": full_stages(),
        "dice_required": 100,
        "dice_per_wafer": 200,
        "contingency_fraction": 0.0,
    }
    case.update(overrides)
    return case


class ValidateStageTests(unittest.TestCase):
    def test_canonical_stage_is_ranked_and_united(self):
        record = validate_stage({"stage": "Die-Screening", "yield_fraction": 0.9})
        self.assertEqual(record["stage"], "die_screening")
        self.assertEqual(record["unit"], "die")
        self.assertEqual(record["rank"], CANONICAL_ROUTE.index("die_screening"))

    def test_unknown_stage_rejected(self):
        with self.assertRaises(ValueError):
            validate_stage({"stage": "burn_in_at_module", "yield_fraction": 0.9})

    def test_yield_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_stage({"stage": "dicing", "yield_fraction": 1.2})

    def test_zero_yield_rejected(self):
        with self.assertRaises(ValueError):
            validate_stage({"stage": "dicing", "yield_fraction": 0.0})

    def test_absent_yield_rejected(self):
        with self.assertRaises(ValueError):
            validate_stage({"stage": "dicing"})

    def test_non_numeric_yield_rejected(self):
        with self.assertRaises(ValueError):
            validate_stage({"stage": "dicing", "yield_fraction": "0.9"})

    def test_non_text_owner_rejected(self):
        with self.assertRaises(ValueError):
            validate_stage({"stage": "dicing", "yield_fraction": 0.9, "owner": 7})

    def test_dicing_is_the_unit_transition(self):
        self.assertEqual(STAGE_UNITS["dicing"], "transition")


class ValidateRouteTests(unittest.TestCase):
    def test_full_route_is_clean(self):
        route = validate_route(full_stages())
        self.assertEqual(route["absent_stages"], ())
        self.assertEqual(route["out_of_sequence"], ())

    def test_dropped_stage_is_reported_absent(self):
        stages = [s for s in full_stages() if s["stage"] != "die_lot_acceptance"]
        self.assertEqual(validate_route(stages)["absent_stages"], ("die_lot_acceptance",))

    def test_swapped_pair_is_reported_out_of_sequence(self):
        stages = full_stages()
        stages[3], stages[4] = stages[4], stages[3]
        route = validate_route(stages)
        self.assertEqual(route["out_of_sequence"],
                         (("die_screening", "die_visual_inspection"),))

    def test_repeated_stage_rejected(self):
        stages = full_stages()
        stages.append(stages[0])
        with self.assertRaises(ValueError):
            validate_route(stages)

    def test_empty_route_rejected(self):
        with self.assertRaises(ValueError):
            validate_route([])


class SurvivalTests(unittest.TestCase):
    def test_unit_yields_survive_entirely(self):
        records = validate_route(full_stages(**{name: 1.0 for name in CANONICAL_ROUTE}))["records"]
        self.assertAlmostEqual(cumulative_survival(records), 1.0, places=9)

    def test_two_half_yields_give_a_quarter(self):
        records = validate_route(full_stages())["records"]
        self.assertAlmostEqual(cumulative_survival(records), 0.25, places=9)

    def test_empty_record_list_rejected(self):
        with self.assertRaises(ValueError):
            cumulative_survival([])


class AnalyticStartTests(unittest.TestCase):
    def test_start_covers_the_required_quantity(self):
        self.assertEqual(analytic_wafer_start(100, 200, 0.25), 2)

    def test_contingency_raises_the_start(self):
        self.assertEqual(analytic_wafer_start(100, 200, 0.25, 1.0), 4)

    def test_fractional_result_rounds_up(self):
        self.assertEqual(analytic_wafer_start(101, 200, 0.25), 3)

    def test_zero_required_quantity_rejected(self):
        with self.assertRaises(ValueError):
            analytic_wafer_start(0, 200, 0.25)

    def test_non_integer_required_quantity_rejected(self):
        with self.assertRaises(ValueError):
            analytic_wafer_start(100.0, 200, 0.25)

    def test_survival_above_one_rejected(self):
        with self.assertRaises(ValueError):
            analytic_wafer_start(100, 200, 1.5)

    def test_negative_contingency_rejected(self):
        with self.assertRaises(ValueError):
            analytic_wafer_start(100, 200, 0.25, -0.1)


class ProjectionTests(unittest.TestCase):
    def test_unit_changes_from_wafer_to_die_at_dicing(self):
        records = validate_route(full_stages())["records"]
        rows = forward_projection(4, 200, records)
        dicing = [row for row in rows if row["stage"] == "dicing"][0]
        self.assertEqual(dicing["entering_unit"], "wafer")
        self.assertEqual(dicing["leaving_unit"], "die")

    def test_population_never_rises_along_the_route(self):
        records = validate_route(full_stages())["records"]
        rows = forward_projection(4, 200, records)
        after_dicing = [row for row in rows if row["leaving_unit"] == "die"]
        for earlier, later in zip(after_dicing, after_dicing[1:]):
            self.assertLessEqual(later["leaving"], earlier["leaving"])

    def test_delivered_quantity_is_the_last_leaving_population(self):
        records = validate_route(full_stages())["records"]
        rows = forward_projection(2, 200, records)
        self.assertEqual(delivered_quantity(rows), rows[-1]["leaving"])
        self.assertEqual(delivered_quantity(rows), 100)

    def test_odd_wafer_count_is_floored_not_rounded(self):
        records = validate_route(full_stages())["records"]
        rows = forward_projection(3, 200, records)
        self.assertEqual(rows[0]["leaving"], 1)

    def test_zero_wafer_start_rejected(self):
        records = validate_route(full_stages())["records"]
        with self.assertRaises(ValueError):
            forward_projection(0, 200, records)

    def test_zero_dice_per_wafer_rejected(self):
        records = validate_route(full_stages())["records"]
        with self.assertRaises(ValueError):
            forward_projection(2, 0, records)

    def test_empty_projection_has_no_delivered_quantity(self):
        with self.assertRaises(ValueError):
            delivered_quantity([])


class SizingTests(unittest.TestCase):
    def test_clean_case_needs_no_adjustment(self):
        records = validate_route(full_stages())["records"]
        sizing = size_wafer_start(100, 200, records)
        self.assertEqual(sizing["analytic_start"], 2)
        self.assertEqual(sizing["adjustment"], 0)
        self.assertTrue(sizing["target_met"])

    def test_flooring_forces_a_step_up(self):
        stages = full_stages(wafer_fabrication=1.0, die_screening=1.0)
        stages = [dict(s, yield_fraction=0.9) if s["stage"] == "wafer_fabrication" else s
                  for s in stages]
        records = validate_route(stages)["records"]
        sizing = size_wafer_start(180, 200, records)
        self.assertGreaterEqual(sizing["adjustment"], 1)
        self.assertTrue(sizing["target_met"])
        self.assertGreaterEqual(sizing["delivered_dice"], sizing["target_dice"])

    def test_contingency_enlarges_the_target(self):
        records = validate_route(full_stages())["records"]
        sizing = size_wafer_start(100, 200, records, 0.5)
        self.assertEqual(sizing["target_dice"], 150)
        self.assertTrue(sizing["target_met"])

    def test_adjustment_is_bounded(self):
        self.assertEqual(MAX_START_ADJUSTMENT, 50)


class OwnershipTests(unittest.TestCase):
    def test_full_route_has_no_ownership_gap(self):
        records = validate_route(full_stages())["records"]
        gaps = ownership_gaps(records)
        self.assertEqual(gaps["stages_without_owner"], ())
        self.assertEqual(gaps["stages_without_exit_criterion"], ())

    def test_unowned_stage_is_named(self):
        stages = full_stages()
        stages[2]["owner"] = "  "
        records = validate_route(stages)["records"]
        self.assertEqual(ownership_gaps(records)["stages_without_owner"], ("dicing",))

    def test_stage_without_exit_criterion_is_named(self):
        stages = full_stages()
        del stages[5]["exit_criterion"]
        records = validate_route(stages)["records"]
        self.assertEqual(
            ownership_gaps(records)["stages_without_exit_criterion"],
            ("die_lot_acceptance",),
        )


class AssessmentTests(unittest.TestCase):
    def test_complete_case_is_viable(self):
        result = assess_die_procurement_approach(full_case())
        self.assertTrue(result["viable"])
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["cumulative_survival"], 0.25, places=9)
        self.assertEqual(result["sizing"]["wafer_start"], 2)

    def test_absent_stage_makes_the_case_non_viable(self):
        case = full_case()
        case["stages"] = [s for s in case["stages"] if s["stage"] != "die_screening"]
        result = assess_die_procurement_approach(case)
        self.assertFalse(result["viable"])
        self.assertTrue(any("die_screening" in f for f in result["findings"]))

    def test_unowned_stage_makes_the_case_non_viable(self):
        case = full_case()
        case["stages"][0]["owner"] = ""
        result = assess_die_procurement_approach(case)
        self.assertFalse(result["viable"])

    def test_missing_dice_required_rejected(self):
        case = full_case()
        del case["dice_required"]
        with self.assertRaises(ValueError):
            assess_die_procurement_approach(case)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_die_procurement_approach(["stages"])

    def test_harsher_yield_raises_the_wafer_start(self):
        lenient = assess_die_procurement_approach(full_case())
        case = full_case()
        case["stages"] = full_stages(die_screening=0.25)
        harsh = assess_die_procurement_approach(case)
        self.assertGreater(harsh["sizing"]["wafer_start"],
                           lenient["sizing"]["wafer_start"])


if __name__ == "__main__":
    unittest.main()
