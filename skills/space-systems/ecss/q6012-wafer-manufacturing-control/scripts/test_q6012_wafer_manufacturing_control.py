"""Contract tests for the clause 10.2.3 wafer fabrication control assessment."""

import unittest

from q6012_wafer_manufacturing_control_logic import (
    EXCURSION_DISPOSITIONS,
    MANDATORY_STEPS,
    MONITOR_KINDS,
    STEP_KEYS,
    assess_manufacturing_control,
    band_position,
    control_findings,
    excursion_findings,
    missing_mandatory_monitors,
    monitor_report,
    monitor_state,
    monitored_fraction,
    step_kinds,
    step_titles,
    trace_path,
    traceability_report,
    traceable_fraction,
    validate_run,
)


def full_monitors():
    return [
        {"step": step, "value": 10.0, "lower": 8.0, "upper": 12.0}
        for step in MANDATORY_STEPS
    ]


def base_spec(**overrides):
    spec = {
        "lot_id": "LOT-771",
        "mask_set_id": "MASK-A4",
        "wafer_ids": ["W01", "W02"],
        "monitors": full_monitors(),
        "links": [
            {"child": "W01", "parent": "LOT-771"},
            {"child": "W02", "parent": "LOT-771"},
            {"child": "LOT-771", "parent": "MASK-A4"},
        ],
        "excursions": [],
    }
    spec.update(overrides)
    return spec


class RegistryTests(unittest.TestCase):
    def test_step_keys_are_unique(self):
        self.assertEqual(len(STEP_KEYS), len(set(STEP_KEYS)))

    def test_every_step_has_a_title_and_a_monitor_kind(self):
        self.assertEqual(set(step_titles()), set(STEP_KEYS))
        self.assertEqual(set(step_kinds()), set(STEP_KEYS))

    def test_every_monitor_kind_is_a_known_kind(self):
        for kind in step_kinds().values():
            self.assertIn(kind, MONITOR_KINDS)

    def test_mandatory_steps_are_a_non_empty_subset(self):
        self.assertTrue(MANDATORY_STEPS)
        self.assertTrue(set(MANDATORY_STEPS).issubset(set(STEP_KEYS)))

    def test_under_review_is_a_declared_disposition(self):
        self.assertIn("under-review", EXCURSION_DISPOSITIONS)


class BandPositionTests(unittest.TestCase):
    def test_centre_reading_sits_at_zero(self):
        self.assertAlmostEqual(band_position(10.0, 8.0, 12.0), 0.0, places=9)

    def test_lower_limit_reading_sits_at_minus_one(self):
        self.assertAlmostEqual(band_position(8.0, 8.0, 12.0), -1.0, places=9)

    def test_upper_limit_reading_sits_at_plus_one(self):
        self.assertAlmostEqual(band_position(12.0, 8.0, 12.0), 1.0, places=9)

    def test_inverted_band_rejected(self):
        with self.assertRaises(ValueError):
            band_position(10.0, 12.0, 8.0)

    def test_zero_width_band_rejected(self):
        with self.assertRaises(ValueError):
            band_position(10.0, 10.0, 10.0)

    def test_non_numeric_reading_rejected(self):
        with self.assertRaises(ValueError):
            band_position("10", 8.0, 12.0)

    def test_boolean_reading_rejected(self):
        with self.assertRaises(ValueError):
            band_position(True, 8.0, 12.0)

    def test_state_on_the_limit_is_reported_as_the_edge(self):
        self.assertEqual(monitor_state(12.0, 8.0, 12.0), "on-band-edge")

    def test_state_inside_the_band_is_in_band(self):
        self.assertEqual(monitor_state(9.0, 8.0, 12.0), "in-band")

    def test_state_outside_the_band_names_the_side(self):
        self.assertEqual(monitor_state(7.0, 8.0, 12.0), "below-band")
        self.assertEqual(monitor_state(13.0, 8.0, 12.0), "above-band")

    def test_negative_tolerance_rejected(self):
        with self.assertRaises(ValueError):
            monitor_state(10.0, 8.0, 12.0, tolerance=-0.1)


class ValidateRunTests(unittest.TestCase):
    def test_normalises_step_tokens_to_lower_case(self):
        spec = base_spec(monitors=[{"step": "Epitaxy", "value": 10.0,
                                    "lower": 8.0, "upper": 12.0}])
        run = validate_run(spec)
        self.assertEqual(run["monitors"][0]["step"], "epitaxy")

    def test_excursions_default_to_empty(self):
        spec = base_spec()
        del spec["excursions"]
        self.assertEqual(validate_run(spec)["excursions"], ())

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            validate_run(["lot_id"])

    def test_missing_required_key_rejected(self):
        spec = base_spec()
        del spec["mask_set_id"]
        with self.assertRaises(ValueError):
            validate_run(spec)

    def test_unknown_key_rejected_rather_than_ignored(self):
        with self.assertRaises(ValueError):
            validate_run(base_spec(excursoins=[]))

    def test_unknown_process_step_rejected(self):
        with self.assertRaises(ValueError):
            validate_run(base_spec(monitors=[{"step": "anneal", "value": 1.0,
                                              "lower": 0.0, "upper": 2.0}]))

    def test_duplicate_reading_for_one_step_rejected(self):
        monitors = full_monitors() + [
            {"step": MANDATORY_STEPS[0], "value": 9.0, "lower": 8.0, "upper": 12.0}
        ]
        with self.assertRaises(ValueError):
            validate_run(base_spec(monitors=monitors))

    def test_inverted_control_band_in_a_reading_rejected(self):
        with self.assertRaises(ValueError):
            validate_run(base_spec(monitors=[{"step": "epitaxy", "value": 10.0,
                                              "lower": 12.0, "upper": 8.0}]))

    def test_duplicate_wafer_id_rejected(self):
        with self.assertRaises(ValueError):
            validate_run(base_spec(wafer_ids=["W01", "W01"]))

    def test_empty_wafer_list_rejected(self):
        with self.assertRaises(ValueError):
            validate_run(base_spec(wafer_ids=[]))

    def test_node_with_two_parents_rejected(self):
        links = base_spec()["links"] + [{"child": "W01", "parent": "MASK-A4"}]
        with self.assertRaises(ValueError):
            validate_run(base_spec(links=links))

    def test_self_parent_link_rejected(self):
        with self.assertRaises(ValueError):
            validate_run(base_spec(links=[{"child": "W01", "parent": "W01"}]))

    def test_unknown_excursion_disposition_rejected(self):
        with self.assertRaises(ValueError):
            validate_run(base_spec(excursions=[{"step": "epitaxy",
                                                "disposition": "waived"}]))

    def test_monitors_are_returned_in_registry_order(self):
        shuffled = list(reversed(full_monitors()))
        run = validate_run(base_spec(monitors=shuffled))
        steps = [m["step"] for m in run["monitors"]]
        self.assertEqual(steps, [s for s in STEP_KEYS if s in set(steps)])


class MonitorCoverageTests(unittest.TestCase):
    def test_full_run_reports_no_missing_monitors(self):
        run = validate_run(base_spec())
        self.assertEqual(missing_mandatory_monitors(run), [])
        self.assertAlmostEqual(monitored_fraction(run), 1.0, places=9)

    def test_dropped_mandatory_step_is_reported_as_unmonitored(self):
        monitors = [m for m in full_monitors() if m["step"] != MANDATORY_STEPS[1]]
        run = validate_run(base_spec(monitors=monitors))
        self.assertIn(MANDATORY_STEPS[1], missing_mandatory_monitors(run))
        self.assertLess(monitored_fraction(run), 1.0)

    def test_report_marks_mandatory_readings(self):
        run = validate_run(base_spec())
        self.assertTrue(all(r["mandatory"] for r in monitor_report(run)))

    def test_report_rejects_a_raw_spec(self):
        with self.assertRaises(ValueError):
            monitor_report(base_spec())


class TraceabilityTests(unittest.TestCase):
    def test_wafer_chain_reaches_the_mask_set(self):
        run = validate_run(base_spec())
        report = traceability_report(run)
        self.assertEqual(report["broken"], [])
        self.assertEqual(report["paths"]["W01"], ["W01", "LOT-771", "MASK-A4"])

    def test_broken_chain_is_reported_not_guessed(self):
        links = [{"child": "W01", "parent": "LOT-771"}]
        run = validate_run(base_spec(links=links))
        report = traceability_report(run)
        self.assertEqual(report["broken"], ["W01", "W02"])
        self.assertAlmostEqual(traceable_fraction(run), 0.0, places=9)

    def test_partial_chain_gives_a_partial_fraction(self):
        links = [
            {"child": "W01", "parent": "LOT-771"},
            {"child": "LOT-771", "parent": "MASK-A4"},
        ]
        run = validate_run(base_spec(links=links))
        self.assertAlmostEqual(traceable_fraction(run), 0.5, places=9)

    def test_trace_path_refuses_a_cycle(self):
        with self.assertRaises(ValueError):
            trace_path("a", {"a": "b", "b": "a"}, "root")

    def test_trace_path_rejects_a_non_mapping_parent_table(self):
        with self.assertRaises(ValueError):
            trace_path("a", [("a", "b")], "root")


class ExcursionTests(unittest.TestCase):
    def test_open_excursion_is_flagged(self):
        run = validate_run(base_spec(excursions=[{"step": "epitaxy",
                                                  "disposition": "under-review"}]))
        self.assertTrue(any("still under review" in f for f in excursion_findings(run)))

    def test_closed_excursion_with_a_reference_is_clean(self):
        run = validate_run(base_spec(excursions=[{"step": "epitaxy",
                                                  "disposition": "reworked",
                                                  "reference": "NCR-12"}]))
        self.assertEqual(excursion_findings(run), [])

    def test_closed_excursion_without_a_reference_is_flagged(self):
        run = validate_run(base_spec(excursions=[{"step": "epitaxy",
                                                  "disposition": "scrapped"}]))
        self.assertTrue(any("no record reference" in f for f in excursion_findings(run)))

    def test_excursion_at_an_unmonitored_step_is_flagged(self):
        run = validate_run(base_spec(excursions=[{"step": "implant",
                                                  "disposition": "reworked",
                                                  "reference": "NCR-9"}]))
        self.assertTrue(any("no monitor reading" in f for f in excursion_findings(run)))


class AssessmentTests(unittest.TestCase):
    def test_clean_run_is_released_to_acceptance(self):
        result = assess_manufacturing_control(base_spec())
        self.assertEqual(result["disposition"], "release-to-acceptance")
        self.assertEqual(result["findings"], [])

    def test_out_of_band_reading_holds_the_lot(self):
        monitors = full_monitors()
        monitors[0] = {"step": monitors[0]["step"], "value": 14.0,
                       "lower": 8.0, "upper": 12.0}
        result = assess_manufacturing_control(base_spec(monitors=monitors))
        self.assertEqual(result["disposition"], "hold")
        self.assertTrue(any("above the band" in f for f in result["findings"]))

    def test_edge_reading_is_reported_rather_than_absorbed(self):
        monitors = full_monitors()
        monitors[0] = {"step": monitors[0]["step"], "value": 8.0,
                       "lower": 8.0, "upper": 12.0}
        findings = control_findings(validate_run(base_spec(monitors=monitors)))
        self.assertTrue(any("band edge" in f for f in findings))

    def test_broken_traceability_holds_the_lot(self):
        result = assess_manufacturing_control(base_spec(links=[]))
        self.assertEqual(result["disposition"], "hold")
        self.assertAlmostEqual(result["traceable_fraction"], 0.0, places=9)

    def test_open_excursions_are_listed_separately(self):
        result = assess_manufacturing_control(
            base_spec(excursions=[{"step": "epitaxy", "disposition": "under-review"}])
        )
        self.assertEqual(result["open_excursions"], ["epitaxy"])

    def test_assessment_rejects_a_bad_spec(self):
        with self.assertRaises(ValueError):
            assess_manufacturing_control(base_spec(lot_id=""))


if __name__ == "__main__":
    unittest.main()
