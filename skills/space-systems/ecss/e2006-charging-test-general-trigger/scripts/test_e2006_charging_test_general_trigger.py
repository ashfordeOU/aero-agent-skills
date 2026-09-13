#!/usr/bin/env python3
"""Gate 3 contract test for the clause 6.6.1 sample-trigger rule."""

import unittest

import e2006_charging_test_general_trigger_logic as logic


MATERIAL_PROVISION = "conductive-surface-material-rule"
ANALYSIS_PROVISION = "surface-potential-analysis-coverage"
BIAS_PROVISION = "biased-surface-disturbance-analysis"
BONDING_PROVISION = "electrical-continuity-bonding"
RESISTIVITY_PROVISION = "surface-resistivity-limit"

SEVERITY = 5.0


def compliant_provisions():
    rows = {}
    for name, entry in logic.PROVISIONS.items():
        if entry["analysis_acceptable"]:
            rows[name] = {"state": "met", "source": "analysis"}
        else:
            rows[name] = {"state": "met", "source": "measurement"}
    return rows


def item(**kw):
    row = {
        "id": "mli-1",
        "material": "kapton-blanket",
        "provisions": compliant_provisions(),
    }
    row.update(kw)
    return row


def status(provision, **kw):
    row = {"state": "met", "source": "measurement"}
    row.update(kw)
    return logic.normalize_provision_status(provision, row)


class ProvisionStatusTests(unittest.TestCase):
    def test_measured_status_round_trips(self):
        row = status(MATERIAL_PROVISION)
        self.assertEqual(row["state"], "met")
        self.assertEqual(row["source"], "measurement")

    def test_source_defaults_to_none_when_not_met(self):
        row = logic.normalize_provision_status(
            MATERIAL_PROVISION, {"state": "not-met"}
        )
        self.assertEqual(row["source"], "none")

    def test_justification_is_kept(self):
        row = logic.normalize_provision_status(
            MATERIAL_PROVISION,
            {"state": "not-applicable", "waived": True, "justification": "internal only"},
        )
        self.assertEqual(row["justification"], "internal only")

    def test_envelope_is_kept_for_a_non_heritage_source(self):
        row = logic.normalize_provision_status(
            MATERIAL_PROVISION,
            {"state": "met", "source": "measurement", "heritage_envelope_severity": 9.0},
        )
        self.assertAlmostEqual(row["heritage_envelope_severity"], 9.0)

    def test_unknown_provision_rejected(self):
        with self.assertRaises(ValueError):
            logic.normalize_provision_status("thermal-paint-rule", {"state": "not-met"})

    def test_non_mapping_status_rejected(self):
        with self.assertRaises(ValueError):
            logic.normalize_provision_status(MATERIAL_PROVISION, "met")

    def test_unknown_state_rejected(self):
        with self.assertRaises(ValueError):
            logic.normalize_provision_status(MATERIAL_PROVISION, {"state": "partial"})

    def test_met_without_a_source_rejected(self):
        with self.assertRaises(ValueError):
            logic.normalize_provision_status(MATERIAL_PROVISION, {"state": "met"})

    def test_unknown_source_rejected(self):
        with self.assertRaises(ValueError):
            logic.normalize_provision_status(
                MATERIAL_PROVISION, {"state": "met", "source": "vendor-datasheet"}
            )

    def test_heritage_without_an_envelope_rejected(self):
        with self.assertRaises(ValueError):
            logic.normalize_provision_status(
                MATERIAL_PROVISION, {"state": "met", "source": "qualified-heritage"}
            )

    def test_zero_heritage_envelope_rejected(self):
        with self.assertRaises(ValueError):
            logic.normalize_provision_status(
                MATERIAL_PROVISION,
                {
                    "state": "met",
                    "source": "qualified-heritage",
                    "heritage_envelope_severity": 0.0,
                },
            )

    def test_non_boolean_waiver_rejected(self):
        with self.assertRaises(ValueError):
            logic.normalize_provision_status(
                MATERIAL_PROVISION, {"state": "not-met", "waived": "yes"}
            )

    def test_waiver_without_justification_rejected(self):
        with self.assertRaises(ValueError):
            logic.normalize_provision_status(
                MATERIAL_PROVISION, {"state": "not-met", "waived": True}
            )

    def test_waiver_with_blank_justification_rejected(self):
        with self.assertRaises(ValueError):
            logic.normalize_provision_status(
                MATERIAL_PROVISION,
                {"state": "not-met", "waived": True, "justification": "   "},
            )


class SurfaceItemTests(unittest.TestCase):
    def test_happy_item_keeps_every_provision(self):
        row = logic.normalize_surface_item(item())
        self.assertEqual(len(row["provisions"]), len(logic.PROVISIONS))

    def test_non_mapping_item_rejected(self):
        with self.assertRaises(ValueError):
            logic.normalize_surface_item(["mli-1"])

    def test_blank_id_rejected(self):
        with self.assertRaises(ValueError):
            logic.normalize_surface_item(item(id=""))

    def test_missing_material_rejected(self):
        with self.assertRaises(ValueError):
            logic.normalize_surface_item(item(material=None))

    def test_empty_provisions_rejected(self):
        with self.assertRaises(ValueError):
            logic.normalize_surface_item(item(provisions={}))

    def test_non_mapping_provisions_rejected(self):
        with self.assertRaises(ValueError):
            logic.normalize_surface_item(item(provisions=[MATERIAL_PROVISION]))

    def test_unknown_provision_key_rejected(self):
        with self.assertRaises(ValueError):
            logic.normalize_surface_item(
                item(provisions={"paint-rule": {"state": "not-met"}})
            )

    def test_set_length(self):
        self.assertEqual(
            len(logic.build_surface_set([item(), item(id="mli-2")])), 2
        )

    def test_empty_set_rejected(self):
        with self.assertRaises(ValueError):
            logic.build_surface_set([])

    def test_non_list_set_rejected(self):
        with self.assertRaises(ValueError):
            logic.build_surface_set(item())

    def test_duplicate_item_id_rejected(self):
        with self.assertRaises(ValueError):
            logic.build_surface_set([item(), item()])


class EffectiveStateTests(unittest.TestCase):
    def test_measured_evidence_carries_a_material_provision(self):
        resolved = logic.effective_provision_state(status(MATERIAL_PROVISION), SEVERITY)
        self.assertEqual(resolved["state"], "met")

    def test_analysis_carries_an_analysis_provision(self):
        resolved = logic.effective_provision_state(
            status(ANALYSIS_PROVISION, source="analysis"), SEVERITY
        )
        self.assertEqual(resolved["state"], "met")

    def test_analysis_cannot_carry_a_material_provision(self):
        resolved = logic.effective_provision_state(
            status(MATERIAL_PROVISION, source="analysis"), SEVERITY
        )
        self.assertEqual(resolved["state"], "not-demonstrated")
        self.assertEqual(
            resolved["reason"], "analysis-cannot-carry-a-material-provision"
        )

    def test_heritage_inside_its_envelope_carries_the_provision(self):
        resolved = logic.effective_provision_state(
            status(
                MATERIAL_PROVISION,
                source="qualified-heritage",
                heritage_envelope_severity=8.0,
            ),
            SEVERITY,
        )
        self.assertEqual(resolved["state"], "met")

    def test_heritage_short_of_the_mission_does_not_carry_it(self):
        resolved = logic.effective_provision_state(
            status(
                MATERIAL_PROVISION,
                source="qualified-heritage",
                heritage_envelope_severity=2.0,
            ),
            SEVERITY,
        )
        self.assertEqual(resolved["state"], "not-demonstrated")
        self.assertEqual(resolved["reason"], "heritage-envelope-shortfall")

    def test_heritage_exactly_at_the_mission_severity_carries_it(self):
        resolved = logic.effective_provision_state(
            status(
                MATERIAL_PROVISION,
                source="qualified-heritage",
                heritage_envelope_severity=0.3,
            ),
            0.1 + 0.2,
        )
        self.assertEqual(resolved["state"], "met")

    def test_declaration_carries_nothing(self):
        resolved = logic.effective_provision_state(
            status(MATERIAL_PROVISION, source="declaration"), SEVERITY
        )
        self.assertEqual(resolved["reason"], "declaration-only-evidence")

    def test_declared_not_met_stays_not_met(self):
        resolved = logic.effective_provision_state(
            logic.normalize_provision_status(MATERIAL_PROVISION, {"state": "not-met"}),
            SEVERITY,
        )
        self.assertEqual(resolved["state"], "not-met")

    def test_not_applicable_stays_not_applicable(self):
        resolved = logic.effective_provision_state(
            logic.normalize_provision_status(
                BIAS_PROVISION, {"state": "not-applicable"}
            ),
            SEVERITY,
        )
        self.assertEqual(resolved["state"], "not-applicable")

    def test_zero_mission_severity_rejected(self):
        with self.assertRaises(ValueError):
            logic.effective_provision_state(status(MATERIAL_PROVISION), 0.0)

    def test_negative_mission_severity_rejected(self):
        with self.assertRaises(ValueError):
            logic.effective_provision_state(status(MATERIAL_PROVISION), -1.0)

    def test_non_numeric_mission_severity_rejected(self):
        with self.assertRaises(ValueError):
            logic.effective_provision_state(status(MATERIAL_PROVISION), "severe")


class ProvisionRowTests(unittest.TestCase):
    def test_one_row_per_registry_provision(self):
        rows = logic.provision_rows_for_item(
            logic.normalize_surface_item(item()), SEVERITY
        )
        self.assertEqual(len(rows), len(logic.PROVISIONS))

    def test_rows_are_in_provision_order(self):
        rows = logic.provision_rows_for_item(
            logic.normalize_surface_item(item()), SEVERITY
        )
        names = [row["provision"] for row in rows]
        self.assertEqual(names, sorted(names))

    def test_absent_provision_is_not_demonstrated(self):
        provisions = compliant_provisions()
        del provisions[BONDING_PROVISION]
        rows = logic.provision_rows_for_item(
            logic.normalize_surface_item(item(provisions=provisions)), SEVERITY
        )
        row = [r for r in rows if r["provision"] == BONDING_PROVISION][0]
        self.assertEqual(row["reason"], "no-status-on-record")
        self.assertTrue(row["triggered"])

    def test_compliant_item_triggers_nothing(self):
        rows = logic.provision_rows_for_item(
            logic.normalize_surface_item(item()), SEVERITY
        )
        self.assertFalse(any(row["triggered"] for row in rows))

    def test_waiver_flag_is_carried(self):
        provisions = compliant_provisions()
        provisions[RESISTIVITY_PROVISION] = {
            "state": "not-met",
            "waived": True,
            "justification": "schedule",
        }
        rows = logic.provision_rows_for_item(
            logic.normalize_surface_item(item(provisions=provisions)), SEVERITY
        )
        row = [r for r in rows if r["provision"] == RESISTIVITY_PROVISION][0]
        self.assertTrue(row["waived"])


class SampleKindTests(unittest.TestCase):
    def test_no_kinds_when_nothing_is_triggered(self):
        rows = logic.provision_rows_for_item(
            logic.normalize_surface_item(item()), SEVERITY
        )
        self.assertEqual(logic.triggered_sample_kinds(rows), [])

    def test_kinds_follow_the_sequence_rank(self):
        provisions = compliant_provisions()
        provisions[ANALYSIS_PROVISION] = {"state": "not-met"}
        provisions[MATERIAL_PROVISION] = {"state": "not-met"}
        rows = logic.provision_rows_for_item(
            logic.normalize_surface_item(item(provisions=provisions)), SEVERITY
        )
        self.assertEqual(
            logic.triggered_sample_kinds(rows),
            ["material-characterisation-sample", "electron-beam-exposure-sample"],
        )

    def test_kinds_are_deduplicated(self):
        provisions = compliant_provisions()
        provisions[MATERIAL_PROVISION] = {"state": "not-met"}
        rows = logic.provision_rows_for_item(
            logic.normalize_surface_item(item(provisions=provisions)), SEVERITY
        )
        doubled = rows + rows
        self.assertEqual(len(logic.triggered_sample_kinds(doubled)), 1)

    def test_one_material_takes_the_base_count(self):
        self.assertEqual(
            logic.sample_count_for_kind("material-characterisation-sample", 1),
            logic.BASE_SAMPLE_COUNT,
        )

    def test_extra_materials_add_samples(self):
        self.assertEqual(
            logic.sample_count_for_kind("bonding-continuity-sample", 3),
            logic.BASE_SAMPLE_COUNT + 2,
        )

    def test_count_is_capped(self):
        self.assertEqual(
            logic.sample_count_for_kind("bonding-continuity-sample", 40),
            logic.MAX_SAMPLE_COUNT,
        )

    def test_unknown_sample_kind_rejected(self):
        with self.assertRaises(ValueError):
            logic.sample_count_for_kind("vibration-sample", 2)

    def test_zero_materials_rejected(self):
        with self.assertRaises(ValueError):
            logic.sample_count_for_kind("bonding-continuity-sample", 0)

    def test_boolean_material_count_rejected(self):
        with self.assertRaises(ValueError):
            logic.sample_count_for_kind("bonding-continuity-sample", True)

    def test_fractional_material_count_rejected(self):
        with self.assertRaises(ValueError):
            logic.sample_count_for_kind("bonding-continuity-sample", 2.5)


class CampaignTests(unittest.TestCase):
    def test_compliant_set_needs_no_campaign(self):
        surface_set = logic.build_surface_set([item()])
        self.assertEqual(logic.build_sample_campaign(surface_set, SEVERITY), {})

    def test_two_items_share_one_sample_kind(self):
        provisions = compliant_provisions()
        provisions[MATERIAL_PROVISION] = {"state": "not-met"}
        surface_set = logic.build_surface_set(
            [
                item(provisions=provisions),
                item(id="mli-2", material="kapton-blanket", provisions=provisions),
            ]
        )
        campaign = logic.build_sample_campaign(surface_set, SEVERITY)
        entry = campaign["material-characterisation-sample"]
        self.assertEqual(entry["item_ids"], ["mli-1", "mli-2"])
        self.assertEqual(entry["materials"], ["kapton-blanket"])

    def test_distinct_materials_raise_the_sample_count(self):
        provisions = compliant_provisions()
        provisions[MATERIAL_PROVISION] = {"state": "not-met"}
        surface_set = logic.build_surface_set(
            [
                item(provisions=provisions),
                item(id="osr-1", material="quartz-reflector", provisions=provisions),
            ]
        )
        campaign = logic.build_sample_campaign(surface_set, SEVERITY)
        self.assertEqual(
            campaign["material-characterisation-sample"]["sample_count"],
            logic.BASE_SAMPLE_COUNT + 1,
        )

    def test_campaign_records_the_triggering_provision(self):
        provisions = compliant_provisions()
        provisions[BONDING_PROVISION] = {"state": "not-met"}
        surface_set = logic.build_surface_set([item(provisions=provisions)])
        campaign = logic.build_sample_campaign(surface_set, SEVERITY)
        self.assertEqual(
            campaign["bonding-continuity-sample"]["provisions"], [BONDING_PROVISION]
        )

    def test_sequence_is_empty_without_a_campaign(self):
        self.assertEqual(logic.campaign_sequence({}), [])

    def test_sequence_runs_material_work_first(self):
        provisions = compliant_provisions()
        provisions[MATERIAL_PROVISION] = {"state": "not-met"}
        provisions[BIAS_PROVISION] = {"state": "not-met"}
        surface_set = logic.build_surface_set([item(provisions=provisions)])
        sequence = logic.campaign_sequence(
            logic.build_sample_campaign(surface_set, SEVERITY)
        )
        self.assertEqual(sequence[0], "material-characterisation-sample")
        self.assertEqual(sequence[-1], "biased-plasma-exposure-sample")


class EvidenceAssessmentTests(unittest.TestCase):
    def test_clean_item_has_no_findings(self):
        surface_set = logic.build_surface_set([item()])
        self.assertEqual(logic.assess_evidence(surface_set, SEVERITY), [])

    def test_waiver_on_an_unmet_provision_is_a_finding(self):
        provisions = compliant_provisions()
        provisions[RESISTIVITY_PROVISION] = {
            "state": "not-met",
            "waived": True,
            "justification": "schedule",
        }
        surface_set = logic.build_surface_set([item(provisions=provisions)])
        kinds = [f["kind"] for f in logic.assess_evidence(surface_set, SEVERITY)]
        self.assertIn("invalid-sample-waiver", kinds)

    def test_waiver_on_a_non_applicable_provision_is_accepted(self):
        provisions = compliant_provisions()
        provisions[BIAS_PROVISION] = {
            "state": "not-applicable",
            "waived": True,
            "justification": "no biased surface",
        }
        surface_set = logic.build_surface_set([item(provisions=provisions)])
        self.assertEqual(logic.assess_evidence(surface_set, SEVERITY), [])

    def test_missing_status_is_a_finding(self):
        provisions = compliant_provisions()
        del provisions[BONDING_PROVISION]
        surface_set = logic.build_surface_set([item(provisions=provisions)])
        kinds = [f["kind"] for f in logic.assess_evidence(surface_set, SEVERITY)]
        self.assertIn("provision-status-missing", kinds)

    def test_heritage_shortfall_is_a_finding(self):
        provisions = compliant_provisions()
        provisions[MATERIAL_PROVISION] = {
            "state": "met",
            "source": "qualified-heritage",
            "heritage_envelope_severity": 1.0,
        }
        surface_set = logic.build_surface_set([item(provisions=provisions)])
        kinds = [f["kind"] for f in logic.assess_evidence(surface_set, SEVERITY)]
        self.assertIn("heritage-envelope-shortfall", kinds)

    def test_declaration_only_claim_is_a_finding(self):
        provisions = compliant_provisions()
        provisions[MATERIAL_PROVISION] = {"state": "met", "source": "declaration"}
        surface_set = logic.build_surface_set([item(provisions=provisions)])
        kinds = [f["kind"] for f in logic.assess_evidence(surface_set, SEVERITY)]
        self.assertIn("unsupported-compliance-claim", kinds)


class ReportTests(unittest.TestCase):
    def test_compliant_vehicle_needs_no_sampling(self):
        report = logic.evaluate_charging_test_trigger([item()], SEVERITY)
        self.assertFalse(report["sample_required"])
        self.assertTrue(report["provisions_met_without_sampling"])

    def test_one_shortfall_triggers_the_campaign(self):
        provisions = compliant_provisions()
        provisions[MATERIAL_PROVISION] = {"state": "not-met"}
        report = logic.evaluate_charging_test_trigger(
            [item(provisions=provisions)], SEVERITY
        )
        self.assertTrue(report["sample_required"])
        self.assertEqual(
            report["campaign_sequence"], ["material-characterisation-sample"]
        )

    def test_item_row_carries_its_own_sample_kinds(self):
        provisions = compliant_provisions()
        provisions[BONDING_PROVISION] = {"state": "not-met"}
        report = logic.evaluate_charging_test_trigger(
            [item(provisions=provisions), item(id="mli-2")], SEVERITY
        )
        first, second = report["items"]
        self.assertEqual(first["sample_kinds"], ["bonding-continuity-sample"])
        self.assertFalse(second["sample_required"])

    def test_mission_severity_is_echoed(self):
        report = logic.evaluate_charging_test_trigger([item()], SEVERITY)
        self.assertAlmostEqual(report["mission_severity"], SEVERITY)

    def test_item_count_is_reported(self):
        report = logic.evaluate_charging_test_trigger(
            [item(), item(id="mli-2")], SEVERITY
        )
        self.assertEqual(report["item_count"], 2)

    def test_every_provision_triggers_its_own_sample_kind(self):
        for name, entry in sorted(logic.PROVISIONS.items()):
            provisions = compliant_provisions()
            provisions[name] = {"state": "not-met"}
            report = logic.evaluate_charging_test_trigger(
                [item(provisions=provisions)], SEVERITY
            )
            self.assertEqual(report["campaign_sequence"], [entry["sample_kind"]])

    def test_report_is_deterministic(self):
        provisions = compliant_provisions()
        provisions[MATERIAL_PROVISION] = {"state": "met", "source": "declaration"}
        first = logic.evaluate_charging_test_trigger(
            [item(provisions=provisions)], SEVERITY
        )
        second = logic.evaluate_charging_test_trigger(
            [item(provisions=provisions)], SEVERITY
        )
        self.assertEqual(first["campaign_sequence"], second["campaign_sequence"])
        self.assertEqual(len(first["findings"]), len(second["findings"]))

    def test_summary_counts_every_finding(self):
        provisions = compliant_provisions()
        provisions[MATERIAL_PROVISION] = {"state": "met", "source": "declaration"}
        del provisions[BONDING_PROVISION]
        report = logic.evaluate_charging_test_trigger(
            [item(provisions=provisions)], SEVERITY
        )
        counts = logic.summarize_findings(report)
        self.assertEqual(sum(counts.values()), len(report["findings"]))

    def test_summary_rejects_a_foreign_mapping(self):
        with self.assertRaises(ValueError):
            logic.summarize_findings({"items": []})

    def test_zero_severity_rejected_by_the_report(self):
        with self.assertRaises(ValueError):
            logic.evaluate_charging_test_trigger([item()], 0.0)


if __name__ == "__main__":
    unittest.main()
