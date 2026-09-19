"""Contract tests for the clause 5.6.7 per-phase communication logic."""

import unittest

from e50_mission_phases_logic import (
    COMPLIANT,
    INCOMPLETE,
    TIMELINE_DEFECT,
    assess_mission_phases,
    covered_duration_h,
    mission_span_h,
    missing_critical_services,
    order_phases,
    timeline_coverage_fraction,
    timeline_findings,
    unallocated_services,
    validate_epoch_h,
    validate_phase,
)

OMNI = "s-band-omni"
HGA = "x-band-hga"


def _leop(**overrides):
    base = {
        "name": "leop",
        "start_h": 0.0,
        "end_h": 72.0,
        "critical": True,
        "links": (OMNI,),
        "service_allocation": {
            "essential-telemetry": OMNI,
            "emergency-telecommand": OMNI,
        },
    }
    base.update(overrides)
    return base


def _transfer(**overrides):
    base = {
        "name": "transfer",
        "start_h": 72.0,
        "end_h": 240.0,
        "critical": False,
        "links": (OMNI, HGA),
        "service_allocation": {"housekeeping-telemetry": OMNI, "telecommand": OMNI},
    }
    base.update(overrides)
    return base


def _science(**overrides):
    base = {
        "name": "science",
        "start_h": 240.0,
        "end_h": 8760.0,
        "critical": False,
        "links": (HGA,),
        "service_allocation": {"payload-downlink": HGA},
    }
    base.update(overrides)
    return base


def _mission():
    return (_leop(), _transfer(), _science())


class ValidationTests(unittest.TestCase):
    def test_phase_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            validate_phase(["leop", 0.0, 72.0])

    def test_blank_phase_name_rejected(self):
        with self.assertRaises(ValueError):
            validate_phase(_leop(name="  "))

    def test_phase_ending_before_it_starts_rejected(self):
        with self.assertRaises(ValueError):
            validate_phase(_leop(start_h=72.0, end_h=0.0))

    def test_zero_length_phase_rejected(self):
        with self.assertRaises(ValueError):
            validate_phase(_leop(start_h=10.0, end_h=10.0))

    def test_non_boolean_criticality_rejected(self):
        with self.assertRaises(ValueError):
            validate_phase(_leop(critical="yes"))

    def test_non_mapping_allocation_rejected(self):
        with self.assertRaises(ValueError):
            validate_phase(_leop(service_allocation=["essential-telemetry"]))

    def test_infinite_epoch_rejected(self):
        with self.assertRaises(ValueError):
            validate_epoch_h(float("inf"))

    def test_boolean_epoch_rejected(self):
        with self.assertRaises(ValueError):
            validate_epoch_h(True)

    def test_duplicate_phase_name_rejected(self):
        with self.assertRaises(ValueError):
            order_phases([_leop(), _leop(start_h=100.0, end_h=200.0)])

    def test_empty_mission_rejected(self):
        with self.assertRaises(ValueError):
            order_phases([])

    def test_phase_duration_is_derived(self):
        self.assertAlmostEqual(validate_phase(_leop())["duration_h"], 72.0, places=9)


class TimelineTests(unittest.TestCase):
    def test_phases_are_returned_in_timeline_order(self):
        ordered = order_phases([_science(), _leop(), _transfer()])
        self.assertEqual(tuple(p["name"] for p in ordered), ("leop", "transfer", "science"))

    def test_mission_span_is_first_start_to_last_end(self):
        self.assertAlmostEqual(mission_span_h(_mission()), 8760.0, places=9)

    def test_contiguous_phases_cover_the_whole_span(self):
        self.assertAlmostEqual(covered_duration_h(_mission()), 8760.0, places=9)

    def test_abutting_phases_report_no_finding(self):
        self.assertEqual(timeline_findings(_mission()), ())

    def test_a_gap_is_reported_with_its_length(self):
        findings = timeline_findings((_leop(), _transfer(start_h=100.0)))
        self.assertEqual(len(findings), 1)
        self.assertIn("28", findings[0])

    def test_an_overlap_is_reported_as_a_shared_claim(self):
        findings = timeline_findings((_leop(), _transfer(start_h=48.0)))
        self.assertTrue(any("both claim" in f for f in findings))

    def test_overlap_is_counted_once_in_the_covered_duration(self):
        phases = (
            {"name": "a", "start_h": 0.0, "end_h": 20.0, "links": (OMNI,), "service_allocation": {"telecommand": OMNI}},
            {"name": "b", "start_h": 10.0, "end_h": 30.0, "links": (OMNI,), "service_allocation": {"telecommand": OMNI}},
        )
        self.assertAlmostEqual(covered_duration_h(phases), 30.0, places=9)

    def test_gap_reduces_the_coverage_fraction(self):
        phases = (
            {"name": "a", "start_h": 0.0, "end_h": 10.0, "links": (OMNI,), "service_allocation": {"telecommand": OMNI}},
            {"name": "b", "start_h": 20.0, "end_h": 30.0, "links": (OMNI,), "service_allocation": {"telecommand": OMNI}},
        )
        self.assertAlmostEqual(timeline_coverage_fraction(phases), 2.0 / 3.0, places=9)

    def test_full_coverage_fraction(self):
        self.assertAlmostEqual(timeline_coverage_fraction(_mission()), 1.0, places=9)

    def test_phases_abutting_exactly_are_contiguous(self):
        self.assertAlmostEqual(_leop()["end_h"], _transfer()["start_h"], places=9)
        self.assertEqual(timeline_findings((_leop(), _transfer())), ())


class AllocationTests(unittest.TestCase):
    def test_service_on_an_available_link_is_allocated(self):
        self.assertEqual(unallocated_services(_leop()), ())

    def test_service_on_a_link_the_phase_lacks_is_stranded(self):
        phase = _leop(service_allocation={"payload-downlink": HGA})
        self.assertEqual(unallocated_services(phase), ("payload-downlink",))

    def test_stranded_services_are_reported_sorted(self):
        phase = _leop(
            service_allocation={"z-service": HGA, "a-service": HGA},
        )
        self.assertEqual(unallocated_services(phase), ("a-service", "z-service"))

    def test_critical_phase_with_recovery_services_is_complete(self):
        self.assertEqual(missing_critical_services(_leop()), ())

    def test_critical_phase_without_emergency_command_is_short(self):
        phase = _leop(service_allocation={"essential-telemetry": OMNI})
        self.assertEqual(missing_critical_services(phase), ("emergency-telecommand",))

    def test_non_critical_phase_is_not_held_to_recovery_services(self):
        self.assertEqual(missing_critical_services(_science()), ())


class AssessTests(unittest.TestCase):
    def test_complete_contiguous_mission_is_compliant(self):
        result = assess_mission_phases(_mission())
        self.assertEqual(result["verdict"], COMPLIANT)
        self.assertEqual(result["findings"], ())

    def test_phase_order_is_carried(self):
        result = assess_mission_phases(_mission())
        self.assertEqual(result["phase_order"], ("leop", "transfer", "science"))

    def test_gap_is_a_timeline_defect(self):
        result = assess_mission_phases((_leop(), _transfer(start_h=100.0), _science()))
        self.assertEqual(result["verdict"], TIMELINE_DEFECT)
        self.assertFalse(result["contiguous"])

    def test_timeline_defect_outranks_a_declaration_gap(self):
        result = assess_mission_phases(
            (_leop(links=()), _transfer(start_h=100.0), _science())
        )
        self.assertEqual(result["verdict"], TIMELINE_DEFECT)

    def test_phase_with_no_link_is_incomplete(self):
        result = assess_mission_phases((_leop(links=()), _transfer(), _science()))
        self.assertEqual(result["verdict"], INCOMPLETE)
        self.assertIn("leop", result["phase_findings"])

    def test_phase_with_no_service_is_incomplete(self):
        result = assess_mission_phases(
            (_leop(service_allocation={}, critical=False), _transfer(), _science())
        )
        self.assertEqual(result["verdict"], INCOMPLETE)

    def test_stranded_service_is_named_in_the_findings(self):
        phase = _science(service_allocation={"payload-downlink": OMNI})
        result = assess_mission_phases((_leop(), _transfer(), phase))
        self.assertTrue(any("does not have" in f for f in result["findings"]))

    def test_critical_phase_shortfall_is_named(self):
        phase = _leop(service_allocation={"essential-telemetry": OMNI})
        result = assess_mission_phases((phase, _transfer(), _science()))
        self.assertTrue(any("cannot be recovered" in f for f in result["findings"]))

    def test_findings_are_prefixed_with_the_phase(self):
        result = assess_mission_phases((_leop(links=()), _transfer(), _science()))
        self.assertTrue(any(f.startswith("leop: ") for f in result["findings"]))

    def test_coverage_fraction_is_carried(self):
        result = assess_mission_phases(_mission())
        self.assertAlmostEqual(result["timeline_coverage_fraction"], 1.0, places=9)

    def test_single_phase_mission_is_assessable(self):
        result = assess_mission_phases((_leop(),))
        self.assertEqual(result["verdict"], COMPLIANT)

    def test_non_sequence_mission_rejected(self):
        with self.assertRaises(ValueError):
            assess_mission_phases("leop")


if __name__ == "__main__":
    unittest.main()
