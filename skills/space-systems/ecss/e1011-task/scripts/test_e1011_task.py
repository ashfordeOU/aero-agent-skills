import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from e1011_task_logic import (
    Task,
    TaskWorkload,
    VALID_CRITICALITIES,
    VALID_FREQUENCIES,
    analyze_task_inventory,
    compute_workload_score,
    is_high_risk,
    validate_task,
    workload_band,
)


def _wl(physical="low", cognitive="low", time_pressure="low", error_consequence="low"):
    return TaskWorkload(
        physical=physical,
        cognitive=cognitive,
        time_pressure=time_pressure,
        error_consequence=error_consequence,
    )


def _task(
    name="Verify hatch seal",
    phase="Ascent",
    frequency="occasional",
    criticality="non-critical",
    workload=None,
):
    return Task(
        name=name,
        phase=phase,
        frequency=frequency,
        criticality=criticality,
        workload=workload if workload is not None else _wl(),
    )


class TestValidateTask(unittest.TestCase):

    def test_valid_task_has_no_errors(self):
        self.assertEqual(validate_task(_task()), [])

    def test_empty_name_produces_error(self):
        errors = validate_task(_task(name=""))
        self.assertTrue(any("name" in e for e in errors))

    def test_whitespace_only_name_produces_error(self):
        errors = validate_task(_task(name="   "))
        self.assertTrue(any("name" in e for e in errors))

    def test_empty_phase_produces_error(self):
        errors = validate_task(_task(phase=""))
        self.assertTrue(any("phase" in e for e in errors))

    def test_unknown_frequency_produces_error(self):
        errors = validate_task(_task(frequency="frequently"))
        self.assertTrue(any("frequency" in e for e in errors))

    def test_unknown_criticality_produces_error(self):
        errors = validate_task(_task(criticality="moderate"))
        self.assertTrue(any("criticality" in e for e in errors))

    def test_unknown_physical_demand_produces_error(self):
        wl = TaskWorkload(physical="extreme", cognitive="low", time_pressure="low", error_consequence="low")
        errors = validate_task(_task(workload=wl))
        self.assertTrue(any("physical" in e for e in errors))

    def test_all_valid_frequencies_pass(self):
        for freq in VALID_FREQUENCIES:
            with self.subTest(frequency=freq):
                self.assertEqual(validate_task(_task(frequency=freq)), [])

    def test_all_valid_criticalities_pass(self):
        for crit in VALID_CRITICALITIES:
            with self.subTest(criticality=crit):
                self.assertEqual(validate_task(_task(criticality=crit)), [])

    def test_multiple_bad_fields_produce_multiple_errors(self):
        errors = validate_task(_task(frequency="bad", criticality="bad"))
        self.assertGreaterEqual(len(errors), 2)


class TestWorkloadScore(unittest.TestCase):

    def test_all_high_yields_twelve(self):
        self.assertEqual(compute_workload_score(_wl("high", "high", "high", "high")), 12)

    def test_all_low_yields_four(self):
        self.assertEqual(compute_workload_score(_wl("low", "low", "low", "low")), 4)

    def test_all_medium_yields_eight(self):
        self.assertEqual(compute_workload_score(_wl("medium", "medium", "medium", "medium")), 8)

    def test_mixed_score_is_correct(self):
        # high(3) + medium(2) + low(1) + medium(2) = 8
        self.assertEqual(compute_workload_score(_wl("high", "medium", "low", "medium")), 8)

    def test_boundary_score_nine(self):
        # high(3) + high(3) + low(1) + medium(2) = 9
        self.assertEqual(compute_workload_score(_wl("high", "high", "low", "medium")), 9)

    def test_boundary_score_ten(self):
        # high(3) + high(3) + high(3) + low(1) = 10
        self.assertEqual(compute_workload_score(_wl("high", "high", "high", "low")), 10)

    def test_invalid_dimension_raises_value_error(self):
        wl = TaskWorkload(physical="extreme", cognitive="low", time_pressure="low", error_consequence="low")
        with self.assertRaises(ValueError):
            compute_workload_score(wl)


class TestWorkloadBand(unittest.TestCase):

    def test_score_ten_maps_to_high(self):
        self.assertEqual(workload_band(10), "high")

    def test_score_twelve_maps_to_high(self):
        self.assertEqual(workload_band(12), "high")

    def test_score_nine_maps_to_medium(self):
        self.assertEqual(workload_band(9), "medium")

    def test_score_seven_maps_to_medium(self):
        self.assertEqual(workload_band(7), "medium")

    def test_score_six_maps_to_low(self):
        self.assertEqual(workload_band(6), "low")

    def test_score_four_maps_to_low(self):
        self.assertEqual(workload_band(4), "low")

    def test_score_below_four_raises_value_error(self):
        with self.assertRaises(ValueError):
            workload_band(3)

    def test_score_above_twelve_raises_value_error(self):
        with self.assertRaises(ValueError):
            workload_band(13)


class TestIsHighRisk(unittest.TestCase):

    def test_safety_critical_high_workload_is_high_risk(self):
        task = _task(criticality="safety-critical", workload=_wl("high", "high", "high", "high"))
        self.assertTrue(is_high_risk(task))

    def test_mission_critical_high_workload_is_high_risk(self):
        task = _task(criticality="mission-critical", workload=_wl("high", "high", "high", "high"))
        self.assertTrue(is_high_risk(task))

    def test_non_critical_high_workload_is_not_high_risk(self):
        task = _task(criticality="non-critical", workload=_wl("high", "high", "high", "high"))
        self.assertFalse(is_high_risk(task))

    def test_safety_critical_low_workload_is_not_high_risk(self):
        task = _task(criticality="safety-critical", workload=_wl("low", "low", "low", "low"))
        self.assertFalse(is_high_risk(task))

    def test_safety_critical_medium_workload_is_not_high_risk(self):
        task = _task(criticality="safety-critical", workload=_wl("medium", "medium", "medium", "medium"))
        self.assertFalse(is_high_risk(task))

    def test_boundary_score_ten_with_mission_critical_is_high_risk(self):
        # high(3)+high(3)+high(3)+low(1) = 10 → high band
        task = _task(criticality="mission-critical", workload=_wl("high", "high", "high", "low"))
        self.assertTrue(is_high_risk(task))

    def test_boundary_score_nine_with_safety_critical_is_not_high_risk(self):
        # high(3)+high(3)+low(1)+medium(2) = 9 → medium band
        task = _task(criticality="safety-critical", workload=_wl("high", "high", "low", "medium"))
        self.assertFalse(is_high_risk(task))


class TestAnalyzeTaskInventory(unittest.TestCase):

    def _sample_tasks(self):
        t1 = _task(
            name="EVA suit pressure verification",
            phase="Pre-EVA",
            frequency="occasional",
            criticality="safety-critical",
            workload=_wl("high", "high", "high", "high"),
        )
        t2 = _task(
            name="Crew daily status log",
            phase="Cruise",
            frequency="routine",
            criticality="non-critical",
            workload=_wl("low", "low", "low", "low"),
        )
        t3 = _task(
            name="Rendezvous approach monitoring",
            phase="Rendezvous",
            frequency="rare",
            criticality="mission-critical",
            workload=_wl("medium", "high", "high", "high"),
        )
        return [t1, t2, t3]

    def test_all_valid_tasks_are_counted(self):
        result = analyze_task_inventory(self._sample_tasks())
        self.assertEqual(len(result["valid_tasks"]), 3)

    def test_invalid_task_excluded_from_valid_list(self):
        result = analyze_task_inventory([_task(name="")])
        self.assertEqual(result["valid_tasks"], [])
        self.assertIn("", result["invalid_tasks"])

    def test_high_risk_task_appears_in_high_risk_list(self):
        result = analyze_task_inventory(self._sample_tasks())
        self.assertIn("EVA suit pressure verification", result["high_risk_tasks"])

    def test_non_critical_task_absent_from_high_risk_list(self):
        result = analyze_task_inventory(self._sample_tasks())
        self.assertNotIn("Crew daily status log", result["high_risk_tasks"])

    def test_workload_score_and_band_recorded_for_valid_task(self):
        result = analyze_task_inventory(self._sample_tasks())
        score, band = result["workload_scores"]["EVA suit pressure verification"]
        self.assertEqual(score, 12)
        self.assertEqual(band, "high")

    def test_low_workload_task_maps_to_low_band(self):
        result = analyze_task_inventory(self._sample_tasks())
        score, band = result["workload_scores"]["Crew daily status log"]
        self.assertEqual(score, 4)
        self.assertEqual(band, "low")

    def test_criticality_counts_are_correct(self):
        result = analyze_task_inventory(self._sample_tasks())
        self.assertEqual(result["criticality_counts"]["safety-critical"], 1)
        self.assertEqual(result["criticality_counts"]["mission-critical"], 1)
        self.assertEqual(result["criticality_counts"]["non-critical"], 1)

    def test_frequency_counts_are_correct(self):
        result = analyze_task_inventory(self._sample_tasks())
        self.assertEqual(result["frequency_counts"]["routine"], 1)
        self.assertEqual(result["frequency_counts"]["occasional"], 1)
        self.assertEqual(result["frequency_counts"]["rare"], 1)

    def test_empty_inventory_returns_empty_results(self):
        result = analyze_task_inventory([])
        self.assertEqual(result["valid_tasks"], [])
        self.assertEqual(result["invalid_tasks"], {})
        self.assertEqual(result["high_risk_tasks"], [])

    def test_mixed_valid_and_invalid_tasks(self):
        tasks = self._sample_tasks() + [_task(name="Bad task", criticality="unknown")]
        result = analyze_task_inventory(tasks)
        self.assertEqual(len(result["valid_tasks"]), 3)
        self.assertEqual(len(result["invalid_tasks"]), 1)


if __name__ == "__main__":
    unittest.main()
