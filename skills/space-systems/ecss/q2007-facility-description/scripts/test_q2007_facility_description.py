#!/usr/bin/env python3
"""Contract tests for the facility description of clause 5.2.2.

Every workflow step the SKILL.md sets out is exercised here, together
with the stop conditions the gate 3 contract reviews: a refused policy,
a register never opened, an entry declaring no capability, an envelope
missing a required parameter, an inverted bound pair, an entry with no
reference document, a centre capability no facility carries, a stale
description, and a booking demand that sits exactly on a bound, outside
one, or on a parameter the facility never declared.
"""

import unittest

from q2007_facility_description_logic import (
    CAPABILITY_COVERAGE_SHORT,
    DEFAULT_REGISTER_POLICY,
    DEMAND_EXCEEDS,
    DEMAND_INSIDE,
    DEMAND_UNDECLARED,
    FACILITY_ENTRY_INCOMPLETE,
    FACILITY_ENVELOPE_MISSING,
    REFERENCE_DOCUMENTS_MISSING,
    REGISTER_ABSENT,
    REGISTER_MAINTAINED,
    assess_facility_description,
    at_least,
    bound_margin,
    capability_coverage,
    descriptions_past_review,
    envelope_parameter_gaps,
    facilities_without_capabilities,
    find_facility,
    reference_document_gaps,
    screen_demand,
    uncovered_capabilities,
    validate_envelope,
    validate_facility,
    validate_register,
    validate_register_policy,
    within_bounds,
)

CENTRE_CAPABILITIES = ["thermal-vacuum-cycling", "sine-vibration", "emc-radiated-emission"]


def _facility(facility_id="TVAC-01", **overrides):
    entry = {
        "facility_id": facility_id,
        "capabilities": ["thermal-vacuum-cycling"],
        "envelope": {"temperature-degc": (-180.0, 150.0), "pressure-mbar": (1e-6, 1013.0)},
        "reference_documents": ["TC-FAC-TVAC-01"],
        "described_on_day": 1500,
    }
    entry.update(overrides)
    return entry


def _register(**overrides):
    record = {
        "maintained": True,
        "facilities": [
            _facility("TVAC-01"),
            _facility(
                "SHAKER-02",
                capabilities=["sine-vibration"],
                envelope={"temperature-degc": (15.0, 30.0), "pressure-mbar": (900.0, 1050.0)},
                reference_documents=["TC-FAC-SHK-02"],
            ),
            _facility(
                "ANECHOIC-03",
                capabilities=["emc-radiated-emission"],
                envelope={"temperature-degc": (18.0, 28.0), "pressure-mbar": (900.0, 1050.0)},
                reference_documents=["TC-FAC-EMC-03"],
            ),
        ],
        "centre_capabilities": list(CENTRE_CAPABILITIES),
        "as_of_day": 2000,
    }
    record.update(overrides)
    return record


def _case(**overrides):
    case = {"register": _register(), "policy": dict(DEFAULT_REGISTER_POLICY)}
    case.update(overrides)
    return case


class RegisterPolicyValidation(unittest.TestCase):
    def test_default_policy_round_trips(self):
        rules = validate_register_policy({})
        self.assertIn("temperature-degc", rules["required_envelope_parameters"])
        self.assertEqual(rules["min_reference_documents"], 1)

    def test_unrecognised_policy_key_refused(self):
        with self.assertRaises(ValueError):
            validate_register_policy({"envelope": ["temperature-degc"]})

    def test_duplicate_required_parameter_refused(self):
        with self.assertRaises(ValueError):
            validate_register_policy(
                {"required_envelope_parameters": ("temperature-degc", "temperature-degc")}
            )

    def test_fractional_document_floor_refused(self):
        with self.assertRaises(ValueError):
            validate_register_policy({"min_reference_documents": 1.5})

    def test_coverage_above_one_refused(self):
        with self.assertRaises(ValueError):
            validate_register_policy({"min_capability_coverage": 1.2})


class EntryValidation(unittest.TestCase):
    def test_facility_missing_field_refused(self):
        bad = _facility()
        del bad["envelope"]
        with self.assertRaises(ValueError):
            validate_facility(bad)

    def test_inverted_envelope_bound_refused(self):
        with self.assertRaises(ValueError):
            validate_envelope({"temperature-degc": (150.0, -180.0)}, "TVAC-01")

    def test_single_sided_envelope_bound_refused(self):
        with self.assertRaises(ValueError):
            validate_envelope({"temperature-degc": (150.0,)}, "TVAC-01")

    def test_non_numeric_envelope_bound_refused(self):
        with self.assertRaises(ValueError):
            validate_envelope({"temperature-degc": ("cold", 150.0)}, "TVAC-01")

    def test_duplicate_capability_in_one_entry_refused(self):
        with self.assertRaises(ValueError):
            validate_facility(
                _facility(capabilities=["sine-vibration", "sine-vibration"])
            )

    def test_duplicate_facility_id_refused(self):
        with self.assertRaises(ValueError):
            validate_register(_register(facilities=[_facility("TVAC-01"), _facility("TVAC-01")]))

    def test_description_after_the_assessment_day_refused(self):
        with self.assertRaises(ValueError):
            validate_register(_register(facilities=[_facility(described_on_day=2500)]))

    def test_non_mapping_register_refused(self):
        with self.assertRaises(ValueError):
            validate_register(["maintained"])

    def test_find_facility_raises_on_an_unheld_identifier(self):
        with self.assertRaises(ValueError):
            find_facility(_register(), "TVAC-99")

    def test_find_facility_returns_the_entry_it_holds(self):
        self.assertEqual(find_facility(_register(), "SHAKER-02")["facility_id"], "SHAKER-02")


class Completeness(unittest.TestCase):
    def test_an_entry_with_no_capability_is_named(self):
        register = _register(facilities=[_facility(capabilities=[])])
        self.assertEqual(facilities_without_capabilities(register), ["TVAC-01"])

    def test_a_missing_required_parameter_is_named(self):
        register = _register(
            facilities=[_facility(envelope={"temperature-degc": (-180.0, 150.0)})]
        )
        self.assertEqual(envelope_parameter_gaps(register, {}), [("TVAC-01", ["pressure-mbar"])])

    def test_an_entry_with_no_reference_document_is_named(self):
        register = _register(facilities=[_facility(reference_documents=[])])
        self.assertEqual(reference_document_gaps(register, {}), ["TVAC-01"])

    def test_a_complete_register_has_no_gaps(self):
        register = _register()
        self.assertEqual(facilities_without_capabilities(register), [])
        self.assertEqual(envelope_parameter_gaps(register, {}), [])
        self.assertEqual(reference_document_gaps(register, {}), [])

    def test_full_capability_coverage_is_exactly_one(self):
        self.assertAlmostEqual(capability_coverage(_register()), 1.0, places=9)

    def test_a_capability_no_facility_carries_is_named(self):
        register = _register(facilities=[_facility("TVAC-01")])
        self.assertAlmostEqual(capability_coverage(register), 1.0 / 3.0, places=9)
        self.assertEqual(
            uncovered_capabilities(register), ["sine-vibration", "emc-radiated-emission"]
        )

    def test_a_centre_declaring_no_capability_has_zero_coverage(self):
        register = _register(centre_capabilities=[])
        self.assertAlmostEqual(capability_coverage(register), 0.0, places=9)

    def test_a_description_exactly_at_the_review_age_is_not_stale(self):
        register = _register(as_of_day=2000, facilities=[_facility(described_on_day=905)])
        self.assertEqual(descriptions_past_review(register, {}), [])

    def test_a_description_one_day_past_the_review_age_is_stale(self):
        register = _register(as_of_day=2000, facilities=[_facility(described_on_day=904)])
        self.assertEqual(descriptions_past_review(register, {}), ["TVAC-01"])


class EnvelopeArithmetic(unittest.TestCase):
    def test_a_value_inside_the_envelope_is_inside(self):
        self.assertTrue(within_bounds(20.0, -180.0, 150.0))

    def test_a_value_exactly_on_the_upper_bound_is_inside(self):
        self.assertTrue(within_bounds(150.0, -180.0, 150.0))

    def test_a_value_exactly_on_the_lower_bound_is_inside(self):
        self.assertTrue(within_bounds(-180.0, -180.0, 150.0))

    def test_a_value_above_the_upper_bound_is_outside(self):
        self.assertFalse(within_bounds(151.0, -180.0, 150.0))

    def test_margin_on_a_bound_is_zero(self):
        self.assertAlmostEqual(bound_margin(150.0, -180.0, 150.0), 0.0, places=9)

    def test_margin_inside_is_the_distance_to_the_nearer_bound(self):
        self.assertAlmostEqual(bound_margin(140.0, -180.0, 150.0), 10.0, places=9)

    def test_margin_outside_is_negative(self):
        self.assertAlmostEqual(bound_margin(160.0, -180.0, 150.0), -10.0, places=9)

    def test_an_inverted_bound_pair_is_refused_by_the_arithmetic_too(self):
        with self.assertRaises(ValueError):
            within_bounds(20.0, 150.0, -180.0)

    def test_at_least_accepts_an_exact_equality(self):
        self.assertTrue(at_least(1.0 / 3.0, 1.0 / 3.0))


class DemandScreening(unittest.TestCase):
    def test_a_demand_inside_the_envelope_passes(self):
        result = screen_demand(_facility(), {"temperature-degc": 100.0})
        self.assertEqual(result["verdict"], DEMAND_INSIDE)

    def test_a_demand_exactly_on_a_bound_passes_with_zero_margin(self):
        result = screen_demand(_facility(), {"temperature-degc": 150.0})
        self.assertEqual(result["verdict"], DEMAND_INSIDE)
        self.assertAlmostEqual(result["parameters"][0]["margin"], 0.0, places=9)

    def test_a_demand_past_a_bound_exceeds(self):
        result = screen_demand(_facility(), {"temperature-degc": 200.0})
        self.assertEqual(result["verdict"], DEMAND_EXCEEDS)

    def test_a_demand_on_an_undeclared_parameter_is_reported_apart(self):
        result = screen_demand(_facility(), {"acceleration-g": 12.0})
        self.assertEqual(result["verdict"], DEMAND_UNDECLARED)
        self.assertIsNone(result["parameters"][0]["margin"])

    def test_an_undeclared_parameter_outranks_an_exceeded_one(self):
        result = screen_demand(
            _facility(), {"temperature-degc": 200.0, "acceleration-g": 12.0}
        )
        self.assertEqual(result["verdict"], DEMAND_UNDECLARED)

    def test_an_empty_demand_set_is_refused(self):
        with self.assertRaises(ValueError):
            screen_demand(_facility(), {})

    def test_a_non_numeric_demand_is_refused(self):
        with self.assertRaises(ValueError):
            screen_demand(_facility(), {"temperature-degc": "hot"})


class Verdicts(unittest.TestCase):
    def test_a_complete_register_is_maintained(self):
        result = assess_facility_description(_case())
        self.assertEqual(result["verdict"], REGISTER_MAINTAINED)
        self.assertEqual(result["findings"], [])

    def test_a_register_never_opened_short_circuits(self):
        result = assess_facility_description(_case(register=_register(maintained=False)))
        self.assertEqual(result["verdict"], REGISTER_ABSENT)

    def test_a_register_with_no_facilities_is_absent(self):
        result = assess_facility_description(_case(register=_register(facilities=[])))
        self.assertEqual(result["verdict"], REGISTER_ABSENT)

    def test_a_blank_capability_outranks_an_envelope_gap(self):
        register = _register(
            facilities=[_facility(capabilities=[], envelope={"temperature-degc": (0.0, 10.0)})]
        )
        result = assess_facility_description(_case(register=register))
        self.assertEqual(result["verdict"], FACILITY_ENTRY_INCOMPLETE)

    def test_an_envelope_gap_outranks_a_document_gap(self):
        register = _register(
            facilities=[
                _facility(envelope={"temperature-degc": (0.0, 10.0)}, reference_documents=[])
            ]
        )
        result = assess_facility_description(_case(register=register))
        self.assertEqual(result["verdict"], FACILITY_ENVELOPE_MISSING)

    def test_a_document_gap_outranks_a_coverage_shortfall(self):
        register = _register(facilities=[_facility(reference_documents=[])])
        result = assess_facility_description(_case(register=register))
        self.assertEqual(result["verdict"], REFERENCE_DOCUMENTS_MISSING)

    def test_a_coverage_shortfall_is_the_last_verdict_before_pass(self):
        register = _register(facilities=[_facility("TVAC-01")])
        result = assess_facility_description(_case(register=register))
        self.assertEqual(result["verdict"], CAPABILITY_COVERAGE_SHORT)
        self.assertEqual(len(result["uncovered_capabilities"]), 2)

    def test_a_stale_description_is_an_advisory_not_a_verdict(self):
        register = _register()
        register["facilities"][0]["described_on_day"] = 100
        result = assess_facility_description(_case(register=register))
        self.assertEqual(result["verdict"], REGISTER_MAINTAINED)
        self.assertEqual(len(result["advisories"]), 1)

    def test_a_booking_inside_the_envelope_adds_no_finding(self):
        booking = {"facility_id": "TVAC-01", "demands": {"temperature-degc": 150.0}}
        result = assess_facility_description(_case(booking=booking))
        self.assertEqual(result["verdict"], REGISTER_MAINTAINED)
        self.assertEqual(result["booking_screening"]["verdict"], DEMAND_INSIDE)
        self.assertEqual(result["findings"], [])

    def test_a_booking_past_the_envelope_adds_a_finding(self):
        booking = {"facility_id": "SHAKER-02", "demands": {"temperature-degc": 60.0}}
        result = assess_facility_description(_case(booking=booking))
        self.assertEqual(result["booking_screening"]["verdict"], DEMAND_EXCEEDS)
        self.assertEqual(len(result["findings"]), 1)

    def test_a_booking_on_an_unheld_facility_is_refused(self):
        booking = {"facility_id": "TVAC-99", "demands": {"temperature-degc": 20.0}}
        with self.assertRaises(ValueError):
            assess_facility_description(_case(booking=booking))

    def test_a_booking_missing_its_demands_is_refused(self):
        with self.assertRaises(ValueError):
            assess_facility_description(_case(booking={"facility_id": "TVAC-01"}))

    def test_a_case_without_a_register_is_refused(self):
        with self.assertRaises(ValueError):
            assess_facility_description({"policy": {}})

    def test_a_non_mapping_case_is_refused(self):
        with self.assertRaises(ValueError):
            assess_facility_description(("register",))


if __name__ == "__main__":
    unittest.main()
