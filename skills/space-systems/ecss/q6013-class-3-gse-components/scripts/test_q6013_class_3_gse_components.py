"""Contract tests for the clause 6.1.5 lowest-class ground support equipment logic."""

import unittest

from q6013_class_3_gse_components_logic import (
    CONTROL_ELEMENTS,
    CONTROL_STATES,
    CONTROL_TIERS,
    COVERAGE_TOLERANCE,
    DATA_ROLES,
    HAZARD_VOLTAGE_V,
    LEAD_TIME_LIMIT_DAYS,
    assess_class3_gse_controls,
    control_coverage,
    credited_controls,
    evaluate_gse_part,
    part_tier,
    required_controls,
    validate_identifier,
)


def evidenced(reference="QA-001"):
    """Return a control entry carrying an evidence reference."""
    return {"state": "evidenced", "evidence": reference}


def part(**overrides):
    """Return a plain catalogue bench part with optional overrides."""
    base = {
        "part_id": "GSE-100",
        "flight_connected": False,
        "data_role": "none",
        "supply_voltage_v": 24.0,
        "replacement_lead_days": 5,
        "controls": {"part-identification": evidenced()},
    }
    base.update(overrides)
    return base


class ValidateIdentifierTests(unittest.TestCase):
    def test_strips_surrounding_space(self):
        self.assertEqual(validate_identifier("  GSE-100 ", "part_id"), "GSE-100")

    def test_blank_rejected(self):
        with self.assertRaises(ValueError):
            validate_identifier("   ", "part_id")

    def test_non_string_rejected(self):
        with self.assertRaises(ValueError):
            validate_identifier(17, "part_id")


class RequiredControlsTests(unittest.TestCase):
    def test_identification_is_owed_by_every_part(self):
        self.assertEqual(required_controls(part()), ("part-identification",))

    def test_flight_connection_pulls_in_isolation(self):
        owed = required_controls(part(flight_connected=True))
        self.assertIn("flight-interface-isolation", owed)

    def test_acceptance_data_pulls_in_calibration_and_verification(self):
        owed = required_controls(part(data_role="acceptance-evidence"))
        self.assertIn("calibration-record", owed)
        self.assertIn("functional-verification", owed)

    def test_monitoring_pulls_in_verification_but_not_calibration(self):
        owed = required_controls(part(data_role="monitoring"))
        self.assertIn("functional-verification", owed)
        self.assertNotIn("calibration-record", owed)

    def test_hazard_voltage_boundary_is_inclusive(self):
        owed = required_controls(part(supply_voltage_v=HAZARD_VOLTAGE_V))
        self.assertIn("operator-safety-barrier", owed)

    def test_below_hazard_voltage_owes_no_safety_barrier(self):
        owed = required_controls(part(supply_voltage_v=HAZARD_VOLTAGE_V / 2.0))
        self.assertNotIn("operator-safety-barrier", owed)

    def test_long_lead_time_pulls_in_spares(self):
        owed = required_controls(part(replacement_lead_days=LEAD_TIME_LIMIT_DAYS + 1))
        self.assertIn("spares-provision", owed)

    def test_lead_time_exactly_at_the_limit_owes_no_spares(self):
        owed = required_controls(part(replacement_lead_days=LEAD_TIME_LIMIT_DAYS))
        self.assertNotIn("spares-provision", owed)

    def test_owed_set_is_sorted_and_unique(self):
        owed = required_controls(
            part(flight_connected=True, data_role="acceptance-evidence")
        )
        self.assertEqual(list(owed), sorted(set(owed)))

    def test_unknown_data_role_rejected(self):
        with self.assertRaises(ValueError):
            required_controls(part(data_role="sometimes"))

    def test_non_boolean_connection_rejected(self):
        with self.assertRaises(ValueError):
            required_controls(part(flight_connected="yes"))

    def test_zero_supply_voltage_rejected(self):
        with self.assertRaises(ValueError):
            required_controls(part(supply_voltage_v=0.0))

    def test_negative_lead_time_rejected(self):
        with self.assertRaises(ValueError):
            required_controls(part(replacement_lead_days=-1))

    def test_every_declared_role_is_accepted(self):
        for role in DATA_ROLES:
            self.assertIn("part-identification", required_controls(part(data_role=role)))


class CreditedControlsTests(unittest.TestCase):
    def test_evidenced_control_is_credited(self):
        credited, notes = credited_controls(
            {"part-identification": evidenced()}, ("part-identification",)
        )
        self.assertEqual(credited, ("part-identification",))
        self.assertEqual(notes, ())

    def test_asserted_control_earns_nothing_and_is_noted(self):
        credited, notes = credited_controls(
            {"part-identification": {"state": "asserted"}}, ("part-identification",)
        )
        self.assertEqual(credited, ())
        self.assertTrue(any("asserted" in note for note in notes))

    def test_undeclared_owed_control_is_noted(self):
        credited, notes = credited_controls({}, ("part-identification",))
        self.assertEqual(credited, ())
        self.assertTrue(any("not declared" in note for note in notes))

    def test_waiver_of_a_waivable_element_with_justification_is_credited(self):
        credited, _ = credited_controls(
            {"spares-provision": {"state": "waived", "justification": "shelf stock held"}},
            ("spares-provision",),
        )
        self.assertEqual(credited, ("spares-provision",))

    def test_waiver_without_justification_earns_nothing(self):
        credited, notes = credited_controls(
            {"spares-provision": {"state": "waived"}}, ("spares-provision",)
        )
        self.assertEqual(credited, ())
        self.assertTrue(any("without a recorded justification" in n for n in notes))

    def test_waiver_of_a_non_waivable_element_earns_nothing(self):
        credited, notes = credited_controls(
            {
                "operator-safety-barrier": {
                    "state": "waived",
                    "justification": "the bench is supervised",
                }
            },
            ("operator-safety-barrier",),
        )
        self.assertEqual(credited, ())
        self.assertTrue(any("may not be waived" in note for note in notes))

    def test_untriggered_declaration_is_noted_not_credited(self):
        credited, notes = credited_controls(
            {
                "part-identification": evidenced(),
                "spares-provision": evidenced("QA-009"),
            },
            ("part-identification",),
        )
        self.assertEqual(credited, ("part-identification",))
        self.assertTrue(any("no exposure triggers it" in note for note in notes))

    def test_evidenced_without_a_reference_rejected(self):
        with self.assertRaises(ValueError):
            credited_controls(
                {"part-identification": {"state": "evidenced"}}, ("part-identification",)
            )

    def test_unknown_state_rejected(self):
        with self.assertRaises(ValueError):
            credited_controls(
                {"part-identification": {"state": "probably"}}, ("part-identification",)
            )

    def test_unknown_element_rejected(self):
        with self.assertRaises(ValueError):
            credited_controls({"gaffer-tape": evidenced()}, ("part-identification",))

    def test_empty_required_set_rejected(self):
        with self.assertRaises(ValueError):
            credited_controls({}, ())

    def test_declared_states_are_the_published_set(self):
        self.assertEqual(len(CONTROL_STATES), 3)


class ControlCoverageTests(unittest.TestCase):
    def test_full_credit_is_unity(self):
        owed = ("part-identification", "flight-interface-isolation")
        self.assertAlmostEqual(control_coverage(owed, owed), 1.0, places=9)

    def test_no_credit_is_zero(self):
        self.assertAlmostEqual(
            control_coverage((), ("part-identification",)), 0.0, places=9
        )

    def test_partial_credit_is_the_weight_share(self):
        owed = ("part-identification", "flight-interface-isolation")
        value = control_coverage(("part-identification",), owed)
        self.assertAlmostEqual(value, 0.20 / 0.45, places=9)

    def test_crediting_an_unowed_element_rejected(self):
        with self.assertRaises(ValueError):
            control_coverage(("spares-provision",), ("part-identification",))

    def test_empty_owed_set_rejected(self):
        with self.assertRaises(ValueError):
            control_coverage(("part-identification",), ())

    def test_element_weights_sum_to_unity(self):
        total = sum(entry["weight"] for entry in CONTROL_ELEMENTS.values())
        self.assertAlmostEqual(total, 1.0, places=9)


class PartTierTests(unittest.TestCase):
    def test_identification_only_and_discharged_is_catalogue(self):
        owed = ("part-identification",)
        self.assertEqual(part_tier(owed, owed), "catalogue-control")

    def test_exposed_and_discharged_is_recorded(self):
        owed = ("flight-interface-isolation", "part-identification")
        self.assertEqual(part_tier(owed, owed), "recorded-control")

    def test_anything_missing_is_open(self):
        owed = ("flight-interface-isolation", "part-identification")
        self.assertEqual(part_tier(owed, ("part-identification",)), "open-control")

    def test_credit_beyond_the_owed_set_rejected(self):
        with self.assertRaises(ValueError):
            part_tier(("part-identification",), ("spares-provision",))

    def test_tiers_are_the_published_set(self):
        self.assertEqual(len(CONTROL_TIERS), 3)


class EvaluateGsePartTests(unittest.TestCase):
    def test_plain_bench_part_is_catalogue_control(self):
        record = evaluate_gse_part(part())
        self.assertEqual(record["tier"], "catalogue-control")
        self.assertAlmostEqual(record["coverage"], 1.0, places=9)

    def test_flight_connected_part_without_isolation_is_open(self):
        record = evaluate_gse_part(part(part_id="GSE-200", flight_connected=True))
        self.assertEqual(record["tier"], "open-control")
        self.assertIn("flight-interface-isolation", record["missing_controls"])

    def test_flight_connected_part_with_isolation_is_recorded(self):
        record = evaluate_gse_part(
            part(
                part_id="GSE-201",
                flight_connected=True,
                controls={
                    "part-identification": evidenced(),
                    "flight-interface-isolation": evidenced("QA-021"),
                },
            )
        )
        self.assertEqual(record["tier"], "recorded-control")
        self.assertEqual(record["missing_controls"], ())

    def test_mains_part_owes_a_safety_barrier_no_waiver_can_buy(self):
        record = evaluate_gse_part(
            part(
                part_id="GSE-202",
                supply_voltage_v=230.0,
                controls={
                    "part-identification": evidenced(),
                    "operator-safety-barrier": {
                        "state": "waived",
                        "justification": "trained operators only",
                    },
                },
            )
        )
        self.assertEqual(record["tier"], "open-control")
        self.assertIn("operator-safety-barrier", record["missing_controls"])

    def test_missing_part_id_rejected(self):
        broken = part()
        del broken["part_id"]
        with self.assertRaises(ValueError):
            evaluate_gse_part(broken)

    def test_zero_quantity_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_gse_part(part(quantity=0))

    def test_non_mapping_item_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_gse_part(["GSE-100"])


class AssessClass3GseControlsTests(unittest.TestCase):
    def _spec(self, **overrides):
        base = {
            "parts": [
                part(),
                part(
                    part_id="GSE-101",
                    flight_connected=True,
                    controls={
                        "part-identification": evidenced(),
                        "flight-interface-isolation": evidenced("QA-021"),
                    },
                ),
            ]
        }
        base.update(overrides)
        return base

    def test_closed_rack_is_accepted(self):
        result = assess_class3_gse_controls(self._spec())
        self.assertEqual(result["verdict"], "accept")
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["rack_coverage"], 1.0, places=9)

    def test_one_open_part_escalates_the_whole_rack(self):
        spec = self._spec(
            parts=[part(), part(part_id="GSE-102", flight_connected=True)]
        )
        result = assess_class3_gse_controls(spec)
        self.assertEqual(result["verdict"], "escalate")
        self.assertEqual(result["tier_counts"]["open-control"], 1)

    def test_governing_part_is_the_lowest_coverage(self):
        spec = self._spec(
            parts=[part(), part(part_id="GSE-102", flight_connected=True)]
        )
        result = assess_class3_gse_controls(spec)
        self.assertEqual(result["governing_part"]["part_id"], "GSE-102")

    def test_governing_tie_breaks_on_the_part_identifier(self):
        spec = self._spec(parts=[part(part_id="GSE-900"), part(part_id="GSE-110")])
        result = assess_class3_gse_controls(spec)
        self.assertEqual(result["governing_part"]["part_id"], "GSE-110")

    def test_findings_rank_the_open_part_first(self):
        spec = self._spec(
            parts=[
                part(
                    part_id="GSE-100",
                    controls={
                        "part-identification": evidenced(),
                        "spares-provision": evidenced("QA-030"),
                    },
                ),
                part(part_id="GSE-102", flight_connected=True),
            ]
        )
        result = assess_class3_gse_controls(spec)
        self.assertEqual(result["findings"][0]["severity"], 0)
        self.assertEqual(result["findings"][0]["part_id"], "GSE-102")

    def test_quantity_weights_the_rack_coverage(self):
        spec = self._spec(
            parts=[
                part(part_id="GSE-100", quantity=3),
                part(part_id="GSE-102", flight_connected=True, quantity=1),
            ]
        )
        result = assess_class3_gse_controls(spec)
        single = assess_class3_gse_controls(
            self._spec(
                parts=[
                    part(part_id="GSE-100", quantity=1),
                    part(part_id="GSE-102", flight_connected=True, quantity=1),
                ]
            )
        )
        self.assertGreater(result["rack_coverage"], single["rack_coverage"])

    def test_floor_of_zero_still_escalates_an_open_part(self):
        spec = self._spec(
            parts=[part(), part(part_id="GSE-102", flight_connected=True)],
            floor=0.0,
        )
        result = assess_class3_gse_controls(spec)
        self.assertTrue(result["meets_floor"])
        self.assertEqual(result["verdict"], "escalate")

    def test_exactly_met_floor_counts_as_met(self):
        result = assess_class3_gse_controls(self._spec(floor=1.0))
        self.assertTrue(result["meets_floor"])
        self.assertEqual(result["verdict"], "accept")

    def test_duplicate_part_id_rejected(self):
        with self.assertRaises(ValueError):
            assess_class3_gse_controls(self._spec(parts=[part(), part()]))

    def test_empty_parts_rejected(self):
        with self.assertRaises(ValueError):
            assess_class3_gse_controls(self._spec(parts=[]))

    def test_missing_parts_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_class3_gse_controls({"floor": 0.9})

    def test_floor_above_one_rejected(self):
        with self.assertRaises(ValueError):
            assess_class3_gse_controls(self._spec(floor=1.5))

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_class3_gse_controls(["parts"])

    def test_tolerance_is_representation_sized(self):
        self.assertLess(COVERAGE_TOLERANCE, 1e-6)


if __name__ == "__main__":
    unittest.main()
