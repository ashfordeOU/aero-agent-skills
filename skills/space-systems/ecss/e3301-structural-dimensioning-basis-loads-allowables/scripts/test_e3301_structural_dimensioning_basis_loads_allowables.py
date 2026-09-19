"""Contract test for the structural-dimensioning-basis leaf (stdlib unittest)."""

import unittest

from e3301_structural_dimensioning_basis_loads_allowables_logic import (
    BASIS_TYPICAL,
    MANDATORY_EVENTS,
    MODEL_FACTOR_BY_BASIS,
    allowable_basis_admissible,
    allowable_covers_temperature,
    assess_dimensioning_basis,
    design_allowable,
    design_limit_load,
    envelope_design_limit_load,
    model_factor,
    uncovered_mandatory_events,
    validate_allowable,
    validate_load_case,
)


def case(cid="LC-1", event="launch-quasi-static", **kw):
    record = {
        "id": cid,
        "event": event,
        "load_basis": "coupled-loads-analysis",
        "limit_load": 1000.0,
        "project_factor": 1.0,
    }
    record.update(kw)
    return record


def allowable(prop="yield", **kw):
    record = {
        "material": "titanium-alloy",
        "property": prop,
        "basis": "a-basis",
        "room_value": 800.0,
        "retention_factor": 1.0,
        "stated_temperature_c": 20.0,
    }
    record.update(kw)
    return record


def part(**kw):
    record = {
        "id": "HINGE-BRACKET",
        "load_path": "single",
        "design_temperature_c": 20.0,
        "load_cases": [case("LC-1"), case("LC-2", event="on-orbit-operational")],
        "allowables": [allowable("yield"), allowable("ultimate", room_value=900.0)],
    }
    record.update(kw)
    return record


class TestValidateLoadCase(unittest.TestCase):
    def test_project_factor_defaults_to_one(self):
        norm = validate_load_case(
            {
                "id": "LC-1",
                "event": "launch-shock",
                "load_basis": "measured-test",
                "limit_load": 10.0,
            }
        )
        self.assertAlmostEqual(norm["project_factor"], 1.0, places=9)

    def test_non_mapping_case_raises(self):
        with self.assertRaises(ValueError):
            validate_load_case(["LC-1"])

    def test_blank_id_raises(self):
        with self.assertRaises(ValueError):
            validate_load_case(case("   "))

    def test_unknown_event_raises(self):
        with self.assertRaises(ValueError):
            validate_load_case(case("LC-1", event="coffee-break"))

    def test_unknown_load_basis_raises(self):
        with self.assertRaises(ValueError):
            validate_load_case(case("LC-1", load_basis="hearsay"))

    def test_negative_limit_load_raises(self):
        with self.assertRaises(ValueError):
            validate_load_case(case("LC-1", limit_load=-1.0))

    def test_project_factor_below_one_raises(self):
        with self.assertRaises(ValueError):
            validate_load_case(case("LC-1", project_factor=0.9))

    def test_boolean_limit_load_raises(self):
        with self.assertRaises(ValueError):
            validate_load_case(case("LC-1", limit_load=True))


class TestModelFactor(unittest.TestCase):
    def test_measured_basis_needs_no_uplift(self):
        self.assertAlmostEqual(model_factor("measured-test"), 1.0, places=9)

    def test_estimate_carries_the_largest_uplift(self):
        worst = max(MODEL_FACTOR_BY_BASIS.values())
        self.assertAlmostEqual(model_factor("engineering-estimate"), worst, places=9)

    def test_unknown_basis_raises(self):
        with self.assertRaises(ValueError):
            model_factor("vibes")


class TestDesignLimitLoad(unittest.TestCase):
    def test_model_and_project_factors_both_apply(self):
        value = design_limit_load(case("LC-1", limit_load=100.0, project_factor=1.25))
        self.assertAlmostEqual(value, 100.0 * 1.25 * 1.10, places=9)

    def test_measured_case_passes_through_unchanged(self):
        value = design_limit_load(
            case("LC-1", load_basis="measured-test", limit_load=250.0)
        )
        self.assertAlmostEqual(value, 250.0, places=9)


class TestEnvelope(unittest.TestCase):
    def test_largest_design_load_drives_the_part(self):
        report = envelope_design_limit_load(
            [
                case("LC-1", limit_load=1000.0),
                case("LC-2", event="on-orbit-operational", limit_load=200.0),
            ]
        )
        self.assertEqual(report["driving_case_id"], "LC-1")
        self.assertAlmostEqual(report["design_limit_load"], 1100.0, places=9)

    def test_a_weak_basis_can_make_a_small_load_drive(self):
        report = envelope_design_limit_load(
            [
                case("LC-1", load_basis="measured-test", limit_load=1000.0),
                case(
                    "LC-2",
                    event="actuation-induced",
                    load_basis="engineering-estimate",
                    limit_load=800.0,
                ),
            ]
        )
        self.assertEqual(report["driving_case_id"], "LC-2")
        self.assertAlmostEqual(report["design_limit_load"], 1200.0, places=9)

    def test_duplicate_case_id_raises(self):
        with self.assertRaises(ValueError):
            envelope_design_limit_load([case("LC-1"), case("LC-1")])

    def test_empty_schedule_raises(self):
        with self.assertRaises(ValueError):
            envelope_design_limit_load([])


class TestMandatoryEvents(unittest.TestCase):
    def test_full_schedule_leaves_nothing_uncovered(self):
        cases = [case("LC-%d" % i, event=e) for i, e in enumerate(MANDATORY_EVENTS)]
        self.assertEqual(uncovered_mandatory_events(cases), [])

    def test_missing_operational_case_is_reported(self):
        self.assertEqual(
            uncovered_mandatory_events([case("LC-1")]), ["on-orbit-operational"]
        )


class TestAllowables(unittest.TestCase):
    def test_typical_average_is_never_admissible(self):
        for path in ("single", "redundant"):
            ok, reason = allowable_basis_admissible(BASIS_TYPICAL, path)
            self.assertFalse(ok)
            self.assertIn("population", reason)

    def test_b_basis_fails_a_single_load_path(self):
        ok, _ = allowable_basis_admissible("b-basis", "single")
        self.assertFalse(ok)

    def test_b_basis_passes_a_redundant_load_path(self):
        ok, _ = allowable_basis_admissible("b-basis", "redundant")
        self.assertTrue(ok)

    def test_unknown_load_path_raises(self):
        with self.assertRaises(ValueError):
            allowable_basis_admissible("a-basis", "triple")

    def test_retention_reduces_the_design_allowable(self):
        value = design_allowable(allowable(room_value=1000.0, retention_factor=0.72))
        self.assertAlmostEqual(value, 720.0, places=9)

    def test_retention_above_unity_raises(self):
        with self.assertRaises(ValueError):
            validate_allowable(allowable(retention_factor=1.2))

    def test_zero_room_value_raises(self):
        with self.assertRaises(ValueError):
            validate_allowable(allowable(room_value=0.0))

    def test_unknown_property_raises(self):
        with self.assertRaises(ValueError):
            validate_allowable(allowable(prop="fatigue"))

    def test_hot_design_point_needs_a_hot_allowable(self):
        hot = allowable(stated_temperature_c=20.0)
        self.assertFalse(allowable_covers_temperature(hot, 120.0))
        self.assertTrue(
            allowable_covers_temperature(allowable(stated_temperature_c=140.0), 120.0)
        )

    def test_cold_design_point_needs_a_cold_allowable(self):
        self.assertFalse(
            allowable_covers_temperature(allowable(stated_temperature_c=-20.0), -80.0)
        )
        self.assertTrue(
            allowable_covers_temperature(allowable(stated_temperature_c=-100.0), -80.0)
        )


class TestAssessDimensioningBasis(unittest.TestCase):
    def test_complete_basis_passes(self):
        report = assess_dimensioning_basis(part())
        self.assertTrue(report["basis_complete"])
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["driving_case_id"], "LC-1")

    def test_typical_allowable_fails_the_basis(self):
        report = assess_dimensioning_basis(
            part(allowables=[allowable("yield", basis=BASIS_TYPICAL), allowable("ultimate")])
        )
        self.assertFalse(report["basis_complete"])
        self.assertIn("allowable-basis-not-admissible:yield", report["findings"])

    def test_missing_ultimate_allowable_is_reported(self):
        report = assess_dimensioning_basis(part(allowables=[allowable("yield")]))
        self.assertIn("allowable-missing:ultimate", report["findings"])

    def test_missing_launch_case_is_reported(self):
        report = assess_dimensioning_basis(
            part(load_cases=[case("LC-2", event="on-orbit-operational")])
        )
        self.assertIn(
            "mandatory-event-not-covered:launch-quasi-static", report["findings"]
        )

    def test_hot_part_with_room_allowables_is_reported(self):
        report = assess_dimensioning_basis(part(design_temperature_c=150.0))
        self.assertIn(
            "allowable-not-stated-at-design-temperature:yield", report["findings"]
        )

    def test_duplicate_property_raises(self):
        with self.assertRaises(ValueError):
            assess_dimensioning_basis(
                part(allowables=[allowable("yield"), allowable("yield")])
            )

    def test_missing_load_cases_raises(self):
        with self.assertRaises(ValueError):
            assess_dimensioning_basis(part(load_cases=[]))

    def test_unknown_load_path_raises(self):
        with self.assertRaises(ValueError):
            assess_dimensioning_basis(part(load_path="some"))


if __name__ == "__main__":
    unittest.main()
