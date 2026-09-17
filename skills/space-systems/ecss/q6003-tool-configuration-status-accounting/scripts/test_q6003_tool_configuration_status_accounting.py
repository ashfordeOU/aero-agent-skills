"""Contract tests for the clause 8.2.3 tool status accounting logic."""

import unittest

from q6003_tool_configuration_status_accounting_logic import (
    FLOATING_VERSION_TOKENS,
    INDEX_TOLERANCE,
    QUALIFICATION_STATES,
    RECORD_FIELDS,
    TOOL_ROLES,
    accounting_index,
    assess_tool_status,
    build_record_index,
    flow_roles,
    is_floating_version,
    missing_role_records,
    normalize_role,
    normalize_token,
    normalize_version,
    parse_iso_date,
    stale_role_records,
    unmitigated_conditions,
    validate_record,
    version_drift,
)

FLOW = ["synthesis", "place-and-route", "static-timing-analysis"]


def record(role="synthesis", **overrides):
    base = {
        "role": role,
        "tool_name": "flow-tool-%s" % role,
        "version": "2024.3",
        "build_or_patch": "sp2",
        "option_set_digest": "d41f8a",
        "host_platform": "linux-x86-64",
        "qualification_state": "qualified",
        "used_on": "2026-04-18",
    }
    base.update(overrides)
    return base


def full_spec(**overrides):
    base = {
        "build_flow": list(FLOW),
        "records": [record(r) for r in FLOW],
        "as_run": {},
        "open_advisories": [],
        "required_index": 1.0,
    }
    base.update(overrides)
    return base


class NormalisationTests(unittest.TestCase):
    def test_token_is_trimmed_and_lower_cased(self):
        self.assertEqual(normalize_token("  Synth Tool ", "tool_name"), "synth tool")

    def test_blank_token_rejected(self):
        with self.assertRaises(ValueError):
            normalize_token("  ", "tool_name")

    def test_role_vocabulary_is_closed(self):
        self.assertIn("place-and-route", TOOL_ROLES)
        with self.assertRaises(ValueError):
            normalize_role("coffee-making")

    def test_version_keeps_its_case(self):
        self.assertEqual(normalize_version(" 2024.3-RC1 "), "2024.3-RC1")

    def test_non_string_version_rejected(self):
        with self.assertRaises(ValueError):
            normalize_version(2024.3)

    def test_record_field_list_is_complete(self):
        for field in ("option_set_digest", "host_platform", "used_on"):
            self.assertIn(field, RECORD_FIELDS)


class FloatingVersionTests(unittest.TestCase):
    def test_bare_floating_token_detected(self):
        self.assertTrue(is_floating_version("latest"))

    def test_suffixed_floating_token_detected(self):
        self.assertTrue(is_floating_version("2024.3-nightly"))

    def test_wildcard_detected(self):
        self.assertTrue(is_floating_version("2024.*"))

    def test_pinned_version_is_not_floating(self):
        self.assertFalse(is_floating_version("2024.3"))

    def test_floating_token_list_is_populated(self):
        self.assertIn("current", FLOATING_VERSION_TOKENS)


class DateTests(unittest.TestCase):
    def test_valid_date_parsed(self):
        self.assertEqual(parse_iso_date("2026-04-18"), (2026, 4, 18))

    def test_short_form_rejected(self):
        with self.assertRaises(ValueError):
            parse_iso_date("2026-4-18")

    def test_month_out_of_range_rejected(self):
        with self.assertRaises(ValueError):
            parse_iso_date("2026-13-01")

    def test_non_numeric_date_rejected(self):
        with self.assertRaises(ValueError):
            parse_iso_date("20xx-01-01")


class RecordTests(unittest.TestCase):
    def test_valid_record_normalised(self):
        item = validate_record(record())
        self.assertEqual(item["role"], "synthesis")
        self.assertEqual(item["used_on"], (2026, 4, 18))
        self.assertFalse(item["floating_version"])

    def test_missing_field_rejected(self):
        broken = record()
        del broken["option_set_digest"]
        with self.assertRaises(ValueError):
            validate_record(broken)

    def test_unknown_qualification_state_rejected(self):
        with self.assertRaises(ValueError):
            validate_record(record(qualification_state="probably-fine"))

    def test_qualification_vocabulary_is_closed(self):
        self.assertIn("qualified-with-restrictions", QUALIFICATION_STATES)

    def test_duplicate_role_record_rejected(self):
        with self.assertRaises(ValueError):
            build_record_index([record("synthesis"), record("synthesis")])

    def test_records_must_be_a_sequence(self):
        with self.assertRaises(ValueError):
            build_record_index(record())


class FlowCoverageTests(unittest.TestCase):
    def test_flow_roles_deduplicated_and_sorted(self):
        self.assertEqual(
            flow_roles(["synthesis", "Synthesis", "simulation"]),
            ["simulation", "synthesis"],
        )

    def test_empty_flow_rejected(self):
        with self.assertRaises(ValueError):
            flow_roles([])

    def test_missing_record_for_a_used_role(self):
        index = build_record_index([record("synthesis")])
        self.assertEqual(
            missing_role_records(FLOW, index),
            ["place-and-route", "static-timing-analysis"],
        )

    def test_stale_record_for_an_unused_role(self):
        index = build_record_index([record(r) for r in FLOW] + [record("simulation")])
        self.assertEqual(stale_role_records(FLOW, index), ["simulation"])


class DriftTests(unittest.TestCase):
    def setUp(self):
        self.index = build_record_index([record(r) for r in FLOW])

    def test_matching_as_run_state_has_no_drift(self):
        as_run = {"synthesis": {"version": "2024.3", "build_or_patch": "sp2"}}
        self.assertEqual(version_drift(self.index, as_run), [])

    def test_version_drift_names_both_sides(self):
        as_run = {"synthesis": {"version": "2024.4"}}
        drift = version_drift(self.index, as_run)
        self.assertEqual(drift[0]["recorded"], "2024.3")
        self.assertEqual(drift[0]["as_run"], "2024.4")

    def test_option_digest_drift_detected(self):
        as_run = {"place-and-route": {"option_set_digest": "ffffff"}}
        drift = version_drift(self.index, as_run)
        self.assertEqual(drift[0]["field"], "option_set_digest")

    def test_as_run_for_an_unrecorded_role_is_ignored_here(self):
        as_run = {"simulation": {"version": "9.9"}}
        self.assertEqual(version_drift(self.index, as_run), [])

    def test_as_run_state_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            version_drift(self.index, {"synthesis": "2024.4"})


class MitigationTests(unittest.TestCase):
    def test_qualified_tool_needs_no_mitigation(self):
        index = build_record_index([record("synthesis")])
        self.assertEqual(unmitigated_conditions(index), [])

    def test_unqualified_tool_without_mitigation_is_reported(self):
        index = build_record_index(
            [record("synthesis", qualification_state="unqualified")]
        )
        self.assertEqual(unmitigated_conditions(index)[0]["role"], "synthesis")

    def test_named_mitigation_clears_the_unqualified_tool(self):
        index = build_record_index(
            [
                record(
                    "synthesis",
                    qualification_state="unqualified",
                    mitigation_reference="mit-12",
                )
            ]
        )
        self.assertEqual(unmitigated_conditions(index), [])

    def test_open_advisory_on_a_qualified_tool_still_needs_mitigation(self):
        index = build_record_index([record("synthesis")])
        result = unmitigated_conditions(index, ["synthesis"])
        self.assertTrue(result[0]["advisory_open"])

    def test_advisory_list_must_be_a_sequence(self):
        index = build_record_index([record("synthesis")])
        with self.assertRaises(ValueError):
            unmitigated_conditions(index, "synthesis")


class IndexTests(unittest.TestCase):
    def test_full_index_on_a_complete_flow(self):
        index = build_record_index([record(r) for r in FLOW])
        self.assertAlmostEqual(accounting_index(FLOW, index), 1.0, places=9)

    def test_missing_record_lowers_the_index(self):
        index = build_record_index([record("synthesis"), record("place-and-route")])
        self.assertAlmostEqual(accounting_index(FLOW, index), 2.0 / 3.0, places=9)

    def test_floating_version_does_not_count_as_accounted(self):
        index = build_record_index(
            [record("synthesis", version="latest")]
            + [record(r) for r in FLOW[1:]]
        )
        self.assertAlmostEqual(accounting_index(FLOW, index), 2.0 / 3.0, places=9)

    def test_drifted_role_does_not_count_as_accounted(self):
        index = build_record_index([record(r) for r in FLOW])
        value = accounting_index(FLOW, index, ["synthesis"])
        self.assertAlmostEqual(value, 2.0 / 3.0, places=9)

    def test_tolerance_is_small_and_positive(self):
        self.assertGreater(INDEX_TOLERANCE, 0.0)
        self.assertLess(INDEX_TOLERANCE, 1e-6)


class AssessmentTests(unittest.TestCase):
    def test_complete_flow_is_reproducible(self):
        result = assess_tool_status(full_spec())
        self.assertTrue(result["build_reproducible"])
        self.assertEqual(result["findings"], [])

    def test_missing_record_breaks_reproducibility(self):
        result = assess_tool_status(full_spec(records=[record("synthesis")]))
        self.assertFalse(result["build_reproducible"])
        self.assertIn("place-and-route", result["missing_records"])

    def test_floating_version_is_reported_and_blocks(self):
        records = [record("synthesis", version="current")] + [
            record(r) for r in FLOW[1:]
        ]
        result = assess_tool_status(full_spec(records=records))
        self.assertEqual(result["floating_versions"], ["synthesis"])
        self.assertFalse(result["build_reproducible"])

    def test_drift_is_reported_and_blocks(self):
        result = assess_tool_status(
            full_spec(as_run={"synthesis": {"build_or_patch": "sp3"}})
        )
        self.assertEqual(result["drift"][0]["as_run"], "sp3")
        self.assertFalse(result["build_reproducible"])

    def test_exactly_met_index_floor_passes(self):
        records = [record("synthesis"), record("place-and-route")]
        result = assess_tool_status(
            full_spec(records=records, required_index=2.0 / 3.0)
        )
        self.assertTrue(result["index_ok"])
        self.assertAlmostEqual(
            result["accounting_index"], result["required_index"], places=9
        )

    def test_stale_record_is_a_finding_but_not_a_reproducibility_block(self):
        records = [record(r) for r in FLOW] + [record("simulation")]
        result = assess_tool_status(full_spec(records=records))
        self.assertEqual(result["stale_records"], ["simulation"])
        self.assertTrue(result["build_reproducible"])

    def test_out_of_range_required_index_rejected(self):
        with self.assertRaises(ValueError):
            assess_tool_status(full_spec(required_index=-0.1))

    def test_spec_missing_records_rejected(self):
        spec = full_spec()
        del spec["records"]
        with self.assertRaises(ValueError):
            assess_tool_status(spec)

    def test_spec_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            assess_tool_status(["build_flow"])

    def test_findings_name_each_defect_kind(self):
        records = [
            record("synthesis", version="latest"),
            record("place-and-route", qualification_state="unqualified"),
            record("simulation"),
        ]
        result = assess_tool_status(
            full_spec(
                records=records,
                as_run={"place-and-route": {"version": "2025.1"}},
            )
        )
        joined = " | ".join(result["findings"])
        self.assertIn("has no tool status record", joined)
        self.assertIn("not used by the build flow", joined)
        self.assertIn("floating version", joined)
        self.assertIn("but ran", joined)
        self.assertIn("no mitigation reference", joined)


if __name__ == "__main__":
    unittest.main()
