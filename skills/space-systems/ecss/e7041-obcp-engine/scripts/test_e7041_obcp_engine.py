"""Contract test for the OBCP engine leaf (stdlib unittest)."""

import unittest

from e7041_obcp_engine_logic import (
    apply_requests,
    assess_obcp_engine,
    can_load,
    can_start,
    engine_utilisation,
    free_steps_per_cycle,
    free_store_bytes,
    language_supported,
    steps_used_per_cycle,
    store_used_bytes,
    validate_engine,
    validate_procedure,
    validate_procedure_set,
)


def engine(**kw):
    record = {
        "engine_id": "OBCP-ENG-1",
        "state": "running",
        "max_loaded": 3,
        "max_running": 2,
        "store_bytes": 4000,
        "step_budget_per_cycle": 100,
        "supported_languages": [
            {"language": "procedure-language-a", "versions": ["1.0", "1.1"]}
        ],
    }
    record.update(kw)
    return record


def procedure(pid="P-1", **kw):
    record = {
        "procedure_id": pid,
        "language": "procedure-language-a",
        "language_version": "1.1",
        "code_bytes": 1000,
        "data_bytes": 200,
        "steps_per_cycle": 30,
    }
    record.update(kw)
    return record


PROCEDURES = [
    procedure("P-1"),
    procedure("P-2"),
    procedure("P-3", code_bytes=2000, steps_per_cycle=50),
    procedure("P-OLD", language_version="0.9"),
    procedure("P-OTHER", language="procedure-language-b"),
    procedure("P-BIG", code_bytes=3900, data_bytes=0, steps_per_cycle=10),
    procedure("P-HEAVY", code_bytes=100, steps_per_cycle=95),
]


class TestEngineValidation(unittest.TestCase):
    def test_valid_engine_normalises(self):
        norm = validate_engine(engine())
        self.assertEqual(norm["engine_id"], "OBCP-ENG-1")
        self.assertEqual(norm["supported_languages"][0]["versions"], ["1.0", "1.1"])

    def test_unknown_state_raises(self):
        with self.assertRaises(ValueError):
            validate_engine(engine(state="idling"))

    def test_running_limit_above_loaded_limit_raises(self):
        with self.assertRaises(ValueError):
            validate_engine(engine(max_loaded=1, max_running=2))

    def test_zero_store_raises(self):
        with self.assertRaises(ValueError):
            validate_engine(engine(store_bytes=0))

    def test_zero_step_budget_raises(self):
        with self.assertRaises(ValueError):
            validate_engine(engine(step_budget_per_cycle=0))

    def test_no_supported_language_raises(self):
        with self.assertRaises(ValueError):
            validate_engine(engine(supported_languages=[]))

    def test_language_without_a_version_raises(self):
        with self.assertRaises(ValueError):
            validate_engine(
                engine(supported_languages=[{"language": "procedure-language-a",
                                             "versions": []}])
            )

    def test_duplicate_language_raises(self):
        with self.assertRaises(ValueError):
            validate_engine(
                engine(
                    supported_languages=[
                        {"language": "procedure-language-a", "versions": ["1.0"]},
                        {"language": "procedure-language-a", "versions": ["1.1"]},
                    ]
                )
            )


class TestProcedureValidation(unittest.TestCase):
    def test_footprint_is_code_plus_data(self):
        norm = validate_procedure(procedure())
        self.assertEqual(norm["footprint_bytes"], 1200)

    def test_zero_code_raises(self):
        with self.assertRaises(ValueError):
            validate_procedure(procedure(code_bytes=0))

    def test_negative_data_raises(self):
        with self.assertRaises(ValueError):
            validate_procedure(procedure(data_bytes=-1))

    def test_zero_steps_raises(self):
        with self.assertRaises(ValueError):
            validate_procedure(procedure(steps_per_cycle=0))

    def test_duplicate_procedure_id_raises(self):
        with self.assertRaises(ValueError):
            validate_procedure_set([procedure("P-1"), procedure("P-1")])

    def test_empty_procedure_set_raises(self):
        with self.assertRaises(ValueError):
            validate_procedure_set([])


class TestLanguageSupport(unittest.TestCase):
    def test_supported_language_and_version(self):
        self.assertEqual(language_supported(engine(), "procedure-language-a", "1.1"),
                         (True, None))

    def test_unsupported_version_of_a_supported_language(self):
        supported, reason = language_supported(
            engine(), "procedure-language-a", "2.0"
        )
        self.assertFalse(supported)
        self.assertEqual(reason, "language-version-not-supported")

    def test_unsupported_language(self):
        supported, reason = language_supported(
            engine(), "procedure-language-b", "1.1"
        )
        self.assertFalse(supported)
        self.assertEqual(reason, "language-not-supported")


class TestAccounting(unittest.TestCase):
    def setUp(self):
        self.catalogue = validate_procedure_set(PROCEDURES)

    def test_store_used_sums_the_loaded_footprints(self):
        self.assertEqual(store_used_bytes(self.catalogue, ["P-1", "P-2"]), 2400)

    def test_free_store_is_the_remainder(self):
        self.assertEqual(free_store_bytes(engine(), self.catalogue, ["P-1"]), 2800)

    def test_steps_used_sums_the_running_demand(self):
        self.assertEqual(steps_used_per_cycle(self.catalogue, ["P-1", "P-3"]), 80)

    def test_free_steps_is_the_remainder(self):
        self.assertEqual(free_steps_per_cycle(engine(), self.catalogue, ["P-3"]), 50)

    def test_undeclared_loaded_procedure_raises(self):
        with self.assertRaises(ValueError):
            store_used_bytes(self.catalogue, ["P-GHOST"])


class TestLoadAdmission(unittest.TestCase):
    def setUp(self):
        self.catalogue = validate_procedure_set(PROCEDURES)

    def test_plain_load_is_accepted(self):
        self.assertEqual(can_load(engine(), self.catalogue, [], "P-1"),
                         (True, "loaded"))

    def test_stopped_engine_refuses_the_load(self):
        accepted, reason = can_load(
            engine(state="stopped"), self.catalogue, [], "P-1"
        )
        self.assertFalse(accepted)
        self.assertEqual(reason, "engine-stopped")

    def test_already_loaded_is_refused(self):
        accepted, reason = can_load(engine(), self.catalogue, ["P-1"], "P-1")
        self.assertFalse(accepted)
        self.assertEqual(reason, "procedure-already-loaded")

    def test_unsupported_version_is_refused_at_load(self):
        accepted, reason = can_load(engine(), self.catalogue, [], "P-OLD")
        self.assertFalse(accepted)
        self.assertEqual(reason, "language-version-not-supported")

    def test_unsupported_language_is_refused_at_load(self):
        accepted, reason = can_load(engine(), self.catalogue, [], "P-OTHER")
        self.assertFalse(accepted)
        self.assertEqual(reason, "language-not-supported")

    def test_loaded_limit_is_refused(self):
        accepted, reason = can_load(
            engine(max_loaded=2, max_running=2), self.catalogue, ["P-1", "P-2"], "P-3"
        )
        self.assertFalse(accepted)
        self.assertEqual(reason, "loaded-procedure-limit-reached")

    def test_footprint_past_the_free_store_is_refused(self):
        accepted, reason = can_load(engine(), self.catalogue, ["P-1"], "P-BIG")
        self.assertFalse(accepted)
        self.assertEqual(reason, "insufficient-engine-store")

    def test_undeclared_procedure_raises(self):
        with self.assertRaises(ValueError):
            can_load(engine(), self.catalogue, [], "P-GHOST")


class TestStartAdmission(unittest.TestCase):
    def setUp(self):
        self.catalogue = validate_procedure_set(PROCEDURES)

    def test_loaded_procedure_starts(self):
        self.assertEqual(
            can_start(engine(), self.catalogue, ["P-1"], [], "P-1"),
            (True, "running"),
        )

    def test_unloaded_procedure_cannot_start(self):
        accepted, reason = can_start(engine(), self.catalogue, [], [], "P-1")
        self.assertFalse(accepted)
        self.assertEqual(reason, "procedure-not-loaded")

    def test_already_running_is_refused(self):
        accepted, reason = can_start(
            engine(), self.catalogue, ["P-1"], ["P-1"], "P-1"
        )
        self.assertFalse(accepted)
        self.assertEqual(reason, "procedure-already-running")

    def test_running_limit_is_refused(self):
        accepted, reason = can_start(
            engine(), self.catalogue, ["P-1", "P-2", "P-3"], ["P-1", "P-2"], "P-3"
        )
        self.assertFalse(accepted)
        self.assertEqual(reason, "running-procedure-limit-reached")

    def test_step_budget_is_refused(self):
        accepted, reason = can_start(
            engine(), self.catalogue, ["P-HEAVY", "P-1"], ["P-HEAVY"], "P-1"
        )
        self.assertFalse(accepted)
        self.assertEqual(reason, "step-budget-per-cycle-exceeded")

    def test_step_demand_exactly_filling_the_budget_is_accepted(self):
        accepted, reason = can_start(
            engine(step_budget_per_cycle=125), self.catalogue,
            ["P-HEAVY", "P-1"], ["P-HEAVY"], "P-1"
        )
        self.assertTrue(accepted)
        self.assertEqual(reason, "running")

    def test_stopped_engine_refuses_the_start(self):
        accepted, reason = can_start(
            engine(state="stopped"), self.catalogue, ["P-1"], [], "P-1"
        )
        self.assertFalse(accepted)
        self.assertEqual(reason, "engine-stopped")


class TestUtilisation(unittest.TestCase):
    def test_four_fractions_are_independent(self):
        catalogue = validate_procedure_set(PROCEDURES)
        util = engine_utilisation(engine(), catalogue, ["P-1", "P-2"], ["P-1"])
        self.assertAlmostEqual(util["loaded_fraction"], 2.0 / 3.0, places=9)
        self.assertAlmostEqual(util["running_fraction"], 0.5, places=9)
        self.assertAlmostEqual(util["store_fraction"], 0.6, places=9)
        self.assertAlmostEqual(util["step_fraction"], 0.3, places=9)

    def test_empty_engine_is_unused(self):
        catalogue = validate_procedure_set(PROCEDURES)
        util = engine_utilisation(engine(), catalogue, [], [])
        self.assertAlmostEqual(util["store_fraction"], 0.0, places=9)
        self.assertAlmostEqual(util["step_fraction"], 0.0, places=9)


class TestSequencing(unittest.TestCase):
    def setUp(self):
        self.catalogue = validate_procedure_set(PROCEDURES)

    def test_each_acceptance_moves_the_free_resources(self):
        outcome = apply_requests(
            engine(),
            self.catalogue,
            [
                {"action": "load", "procedure_id": "P-1"},
                {"action": "load", "procedure_id": "P-BIG"},
            ],
        )
        self.assertTrue(outcome["results"][0]["accepted"])
        self.assertFalse(outcome["results"][1]["accepted"])
        self.assertEqual(outcome["results"][1]["reason"], "insufficient-engine-store")

    def test_the_reverse_order_admits_the_large_procedure(self):
        outcome = apply_requests(
            engine(),
            self.catalogue,
            [
                {"action": "load", "procedure_id": "P-BIG"},
                {"action": "load", "procedure_id": "P-1"},
            ],
        )
        self.assertTrue(outcome["results"][0]["accepted"])
        self.assertFalse(outcome["results"][1]["accepted"])

    def test_load_then_start_reaches_the_running_set(self):
        outcome = apply_requests(
            engine(),
            self.catalogue,
            [
                {"action": "load", "procedure_id": "P-1"},
                {"action": "start", "procedure_id": "P-1"},
            ],
        )
        self.assertEqual(outcome["loaded_ids"], ["P-1"])
        self.assertEqual(outcome["running_ids"], ["P-1"])

    def test_unknown_action_raises(self):
        with self.assertRaises(ValueError):
            apply_requests(
                engine(), self.catalogue, [{"action": "halt", "procedure_id": "P-1"}]
            )

    def test_non_sequence_requests_raise(self):
        with self.assertRaises(ValueError):
            apply_requests(engine(), self.catalogue, {"action": "load"})


class TestAssessment(unittest.TestCase):
    def test_clean_admission_reports_no_findings(self):
        report = assess_obcp_engine(
            {
                "engine": engine(),
                "procedures": PROCEDURES,
                "requests": [
                    {"action": "load", "procedure_id": "P-1"},
                    {"action": "start", "procedure_id": "P-1"},
                ],
            }
        )
        self.assertTrue(report["clean"])
        self.assertEqual(report["accepted_count"], 2)
        self.assertAlmostEqual(report["utilisation"]["step_fraction"], 0.3, places=9)

    def test_refusal_reaches_the_findings_with_its_reason(self):
        report = assess_obcp_engine(
            {
                "engine": engine(),
                "procedures": PROCEDURES,
                "requests": [{"action": "start", "procedure_id": "P-1"}],
            }
        )
        self.assertFalse(report["clean"])
        self.assertIn("procedure-not-loaded", report["findings"][0])
        self.assertEqual(report["refused_count"], 1)

    def test_stopped_engine_admits_nothing(self):
        report = assess_obcp_engine(
            {
                "engine": engine(state="stopped"),
                "procedures": PROCEDURES,
                "requests": [{"action": "load", "procedure_id": "P-1"}],
            }
        )
        self.assertEqual(report["loaded_ids"], [])
        self.assertIn("engine-stopped", report["findings"][0])

    def test_missing_spec_key_raises(self):
        with self.assertRaises(ValueError):
            assess_obcp_engine({"engine": engine()})

    def test_non_mapping_spec_raises(self):
        with self.assertRaises(ValueError):
            assess_obcp_engine([engine()])


if __name__ == "__main__":
    unittest.main()
