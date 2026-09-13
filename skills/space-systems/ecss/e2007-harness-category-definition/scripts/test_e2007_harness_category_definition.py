"""Contract test for the harness category-definition leaf (stdlib unittest)."""

import unittest

from e2007_harness_category_definition_logic import (
    CAT_INTERFERING,
    CAT_POWER,
    CAT_SENSITIVE,
    CAT_SIGNAL,
    assess_harness_categorization,
    categorize_wire,
    check_bundle_composition,
    check_critical_line_treatment,
    check_route_separations,
    declared_separation_mm,
    required_separation_mm,
    separation_is_met,
    switching_rates,
    validate_wire,
)


def wire(wid="W-1", function="digital-data-bus", **kw):
    record = {"id": wid, "function": function}
    record.update(kw)
    return record


def sensor(wid="W-S"):
    return wire(wid, "low-level-analog-sensor", amplitude_v=0.05,
                source_impedance_ohm=1.0e5, rise_time_us=100.0)


def power(wid="W-P"):
    return wire(wid, "primary-power-distribution", amplitude_v=28.0,
                peak_current_a=5.0, rise_time_us=1000.0)


def pyro(wid="W-K", partner="W-K2", construction="twisted-shielded-pair"):
    return wire(wid, "pyrotechnic-firing", amplitude_v=28.0, peak_current_a=5.0,
                rise_time_us=10.0, critical=True, construction=construction,
                redundant_partner_id=partner)


def bundle(bid, route_id, wire_ids):
    return {"id": bid, "route_id": route_id, "wire_ids": list(wire_ids)}


def index(wires):
    return {w["id"]: w for w in wires}


class TestValidateWire(unittest.TestCase):
    def test_defaults_are_filled_in(self):
        norm = validate_wire(wire())
        self.assertEqual(norm["construction"], "single-wire")
        self.assertFalse(norm["critical"])
        self.assertAlmostEqual(norm["rise_time_us"], 1.0)

    def test_non_mapping_raises(self):
        with self.assertRaises(ValueError):
            validate_wire(["W-1"])

    def test_empty_id_raises(self):
        with self.assertRaises(ValueError):
            validate_wire(wire(""))

    def test_unknown_function_raises(self):
        with self.assertRaises(ValueError):
            validate_wire(wire("W-1", "coffee-machine-feed"))

    def test_non_boolean_criticality_raises(self):
        with self.assertRaises(ValueError):
            validate_wire(wire("W-1", critical="yes"))

    def test_zero_rise_time_raises(self):
        with self.assertRaises(ValueError):
            validate_wire(wire("W-1", rise_time_us=0.0))

    def test_negative_amplitude_raises(self):
        with self.assertRaises(ValueError):
            validate_wire(wire("W-1", amplitude_v=-1.0))

    def test_non_numeric_current_raises(self):
        with self.assertRaises(ValueError):
            validate_wire(wire("W-1", peak_current_a="5"))


class TestSwitchingRates(unittest.TestCase):
    def test_current_slew_is_computed(self):
        didt, _ = switching_rates(wire("W-1", peak_current_a=6.0, rise_time_us=2.0))
        self.assertAlmostEqual(didt, 3.0)

    def test_voltage_slew_is_computed(self):
        _, dvdt = switching_rates(wire("W-1", amplitude_v=5.0, rise_time_us=0.5))
        self.assertAlmostEqual(dvdt, 10.0)


class TestCategorizeWire(unittest.TestCase):
    def test_low_level_sensor_is_sensitive(self):
        self.assertEqual(categorize_wire(sensor()), CAT_SENSITIVE)

    def test_data_bus_is_a_signal_line(self):
        self.assertEqual(categorize_wire(wire()), CAT_SIGNAL)

    def test_power_distribution_is_a_power_line(self):
        self.assertEqual(categorize_wire(power()), CAT_POWER)

    def test_pyrotechnic_line_is_interfering(self):
        self.assertEqual(categorize_wire(pyro()), CAT_INTERFERING)

    def test_fast_current_slew_promotes_to_interfering(self):
        fast = wire("W-1", "secondary-power-distribution", peak_current_a=40.0,
                    rise_time_us=1.0)
        self.assertEqual(categorize_wire(fast), CAT_INTERFERING)

    def test_fast_voltage_slew_promotes_to_interfering(self):
        fast = wire("W-1", "discrete-command", amplitude_v=28.0, rise_time_us=0.1)
        self.assertEqual(categorize_wire(fast), CAT_INTERFERING)

    def test_quiet_high_impedance_signal_is_demoted_to_sensitive(self):
        quiet = wire("W-1", "telemetry-acquisition", amplitude_v=0.05,
                     source_impedance_ohm=1.0e5, rise_time_us=100.0)
        self.assertEqual(categorize_wire(quiet), CAT_SENSITIVE)

    def test_low_impedance_signal_stays_a_signal_line(self):
        quiet = wire("W-1", "telemetry-acquisition", amplitude_v=0.05,
                     source_impedance_ohm=50.0, rise_time_us=100.0)
        self.assertEqual(categorize_wire(quiet), CAT_SIGNAL)

    def test_promotion_wins_over_demotion(self):
        odd = wire("W-1", "digital-data-bus", amplitude_v=0.05,
                   source_impedance_ohm=1.0e5, peak_current_a=20.0,
                   rise_time_us=1.0)
        self.assertEqual(categorize_wire(odd), CAT_INTERFERING)

    def test_amplitude_exactly_at_the_sensitive_limit_is_demoted(self):
        edge = wire("W-1", "telemetry-acquisition", amplitude_v=0.1,
                    source_impedance_ohm=1.0e4, rise_time_us=100.0)
        self.assertEqual(categorize_wire(edge), CAT_SENSITIVE)


class TestRequiredSeparation(unittest.TestCase):
    def test_same_category_needs_no_separation(self):
        self.assertAlmostEqual(required_separation_mm(CAT_SIGNAL, CAT_SIGNAL), 0.0)

    def test_sensitive_against_interfering_is_the_widest(self):
        self.assertAlmostEqual(
            required_separation_mm(CAT_SENSITIVE, CAT_INTERFERING), 200.0
        )

    def test_lookup_is_symmetric(self):
        self.assertAlmostEqual(
            required_separation_mm(CAT_INTERFERING, CAT_SENSITIVE),
            required_separation_mm(CAT_SENSITIVE, CAT_INTERFERING),
        )

    def test_signal_against_power(self):
        self.assertAlmostEqual(required_separation_mm(CAT_SIGNAL, CAT_POWER), 50.0)

    def test_unknown_category_raises(self):
        with self.assertRaises(ValueError):
            required_separation_mm("cat-9-mystery", CAT_SIGNAL)


class TestSeparationIsMet(unittest.TestCase):
    def test_exact_equality_is_met(self):
        self.assertTrue(separation_is_met(150.0, 150.0))

    def test_short_separation_is_not_met(self):
        self.assertFalse(separation_is_met(149.0, 150.0))

    def test_representation_error_is_absorbed(self):
        summed = 82.6 + 52.3 + 15.1
        self.assertLess(summed, 150.0)
        self.assertTrue(separation_is_met(summed, 150.0))

    def test_generous_separation_is_met(self):
        self.assertTrue(separation_is_met(400.0, 200.0))

    def test_negative_actual_raises(self):
        with self.assertRaises(ValueError):
            separation_is_met(-1.0, 150.0)


class TestDeclaredSeparation(unittest.TestCase):
    def test_explicit_value_is_read(self):
        record = {"route_a": "R-1", "route_b": "R-2", "separation_mm": 180.0}
        self.assertAlmostEqual(declared_separation_mm(record), 180.0)

    def test_offset_segments_are_summed(self):
        record = {"route_a": "R-1", "route_b": "R-2",
                  "offset_segments_mm": [82.6, 52.3, 15.1]}
        self.assertAlmostEqual(declared_separation_mm(record), 150.0, places=9)

    def test_same_route_twice_raises(self):
        with self.assertRaises(ValueError):
            declared_separation_mm({"route_a": "R-1", "route_b": "R-1",
                                    "separation_mm": 10.0})

    def test_empty_segments_raise(self):
        with self.assertRaises(ValueError):
            declared_separation_mm({"route_a": "R-1", "route_b": "R-2",
                                    "offset_segments_mm": []})

    def test_missing_route_raises(self):
        with self.assertRaises(ValueError):
            declared_separation_mm({"route_a": "R-1", "separation_mm": 10.0})

    def test_non_mapping_raises(self):
        with self.assertRaises(ValueError):
            declared_separation_mm(["R-1", "R-2", 10.0])

    def test_missing_value_raises(self):
        with self.assertRaises(ValueError):
            declared_separation_mm({"route_a": "R-1", "route_b": "R-2"})


class TestCriticalLineTreatment(unittest.TestCase):
    def test_noncritical_wire_has_no_extra_treatment(self):
        self.assertEqual(check_critical_line_treatment(wire(), "R-1", "R-2"), [])

    def test_well_treated_critical_line_is_clean(self):
        self.assertEqual(check_critical_line_treatment(pyro(), "R-1", "R-2"), [])

    def test_plain_construction_is_flagged(self):
        findings = check_critical_line_treatment(
            pyro(construction="single-wire"), "R-1", "R-2"
        )
        self.assertIn("critical-line-not-twisted-shielded-pair", findings)

    def test_missing_redundant_partner_is_flagged(self):
        findings = check_critical_line_treatment(pyro(partner=None), "R-1", None)
        self.assertIn("critical-line-has-no-redundant-partner", findings)

    def test_unrouted_partner_is_flagged(self):
        findings = check_critical_line_treatment(pyro(), "R-1", None)
        self.assertIn("critical-line-redundant-partner-not-routed", findings)

    def test_shared_route_with_partner_is_flagged(self):
        findings = check_critical_line_treatment(pyro(), "R-1", "R-1")
        self.assertIn("critical-line-shares-route-with-redundant-partner", findings)


class TestBundleComposition(unittest.TestCase):
    def test_uniform_bundle_is_clean(self):
        wires = [wire("W-1"), wire("W-2")]
        findings, cats = check_bundle_composition(
            bundle("B-1", "R-1", ["W-1", "W-2"]), index(wires)
        )
        self.assertEqual(findings, [])
        self.assertEqual(cats, {CAT_SIGNAL})

    def test_mixed_categories_are_flagged(self):
        wires = [wire("W-1"), power("W-2")]
        findings, cats = check_bundle_composition(
            bundle("B-1", "R-1", ["W-1", "W-2"]), index(wires)
        )
        self.assertIn("bundle-mixes-wire-categories", findings)
        self.assertEqual(cats, {CAT_SIGNAL, CAT_POWER})

    def test_critical_mixed_with_noncritical_is_flagged(self):
        wires = [pyro("W-1"), wire("W-2", "motor-drive", peak_current_a=1.0,
                                   rise_time_us=100.0)]
        findings, _ = check_bundle_composition(
            bundle("B-1", "R-1", ["W-1", "W-2"]), index(wires)
        )
        self.assertIn("critical-line-bundled-with-noncritical-wire", findings)

    def test_unknown_wire_raises(self):
        with self.assertRaises(ValueError):
            check_bundle_composition(bundle("B-1", "R-1", ["W-9"]), index([wire("W-1")]))

    def test_empty_bundle_raises(self):
        with self.assertRaises(ValueError):
            check_bundle_composition(bundle("B-1", "R-1", []), index([wire("W-1")]))

    def test_missing_route_raises(self):
        bad = {"id": "B-1", "wire_ids": ["W-1"]}
        with self.assertRaises(ValueError):
            check_bundle_composition(bad, index([wire("W-1")]))

    def test_non_mapping_bundle_raises(self):
        with self.assertRaises(ValueError):
            check_bundle_composition("B-1", index([wire("W-1")]))


class TestRouteSeparations(unittest.TestCase):
    def setUp(self):
        self.layout = {
            "B-1": {"route_id": "R-1", "categories": {CAT_SENSITIVE}},
            "B-2": {"route_id": "R-2", "categories": {CAT_INTERFERING}},
        }

    def test_sufficient_separation_is_clean(self):
        records = [{"route_a": "R-1", "route_b": "R-2", "separation_mm": 250.0}]
        self.assertEqual(check_route_separations(self.layout, records), [])

    def test_insufficient_separation_is_flagged(self):
        records = [{"route_a": "R-1", "route_b": "R-2", "separation_mm": 120.0}]
        findings = check_route_separations(self.layout, records)
        self.assertEqual(findings[0]["finding"], "insufficient-route-separation")
        self.assertAlmostEqual(findings[0]["required_mm"], 200.0)

    def test_undeclared_separation_is_flagged(self):
        findings = check_route_separations(self.layout, [])
        self.assertEqual(findings[0]["finding"], "route-separation-not-declared")

    def test_shared_route_between_categories_is_flagged(self):
        layout = dict(self.layout)
        layout["B-2"] = {"route_id": "R-1", "categories": {CAT_INTERFERING}}
        findings = check_route_separations(layout, [])
        self.assertEqual(findings[0]["finding"], "categories-share-one-route")

    def test_same_category_may_share_a_route(self):
        layout = {
            "B-1": {"route_id": "R-1", "categories": {CAT_SIGNAL}},
            "B-2": {"route_id": "R-1", "categories": {CAT_SIGNAL}},
        }
        self.assertEqual(check_route_separations(layout, []), [])

    def test_summed_offsets_meeting_the_limit_are_clean(self):
        record = {"route_a": "R-1", "route_b": "R-2",
                  "offset_segments_mm": [128.2, 22.2, 49.6]}
        layout = {
            "B-1": {"route_id": "R-1", "categories": {CAT_SENSITIVE}},
            "B-2": {"route_id": "R-2", "categories": {CAT_INTERFERING}},
        }
        # The segment accumulation lands a few ULPs short of the 200 mm
        # requirement; the named tolerance absorbs it.
        self.assertLessEqual(declared_separation_mm(record), 200.0)
        self.assertAlmostEqual(declared_separation_mm(record), 200.0, places=9)
        self.assertEqual(check_route_separations(layout, [record]), [])


class TestAssessHarnessCategorization(unittest.TestCase):
    def clean_harness(self):
        wires = [
            sensor("W-S1"),
            wire("W-D1"),
            power("W-P1"),
            pyro("W-K1", "W-K2"),
            pyro("W-K2", "W-K1"),
        ]
        bundles = [
            bundle("B-S", "R-S", ["W-S1"]),
            bundle("B-D", "R-D", ["W-D1"]),
            bundle("B-P", "R-P", ["W-P1"]),
            bundle("B-K1", "R-K1", ["W-K1"]),
            bundle("B-K2", "R-K2", ["W-K2"]),
        ]
        routes = ["R-S", "R-D", "R-P", "R-K1", "R-K2"]
        records = []
        for i, ra in enumerate(routes):
            for rb in routes[i + 1:]:
                records.append({"route_a": ra, "route_b": rb, "separation_mm": 400.0})
        return wires, bundles, records

    def test_clean_harness_is_compliant(self):
        wires, bundles, records = self.clean_harness()
        report = assess_harness_categorization(wires, bundles, records)
        self.assertTrue(report["compliant"])
        self.assertEqual(report["categories"]["W-S1"], CAT_SENSITIVE)
        self.assertEqual(report["categories"]["W-K1"], CAT_INTERFERING)

    def test_unassigned_wire_is_flagged(self):
        wires, bundles, records = self.clean_harness()
        wires.append(wire("W-D2"))
        report = assess_harness_categorization(wires, bundles, records)
        self.assertFalse(report["compliant"])
        self.assertIn("wire-not-assigned-to-a-bundle", report["wire_findings"]["W-D2"])

    def test_critical_pair_on_one_route_is_flagged(self):
        wires, bundles, records = self.clean_harness()
        bundles[4] = bundle("B-K2", "R-K1", ["W-K2"])
        report = assess_harness_categorization(wires, bundles, records)
        self.assertFalse(report["compliant"])
        self.assertIn(
            "critical-line-shares-route-with-redundant-partner",
            report["wire_findings"]["W-K1"],
        )

    def test_missing_separation_declaration_is_flagged(self):
        wires, bundles, _ = self.clean_harness()
        report = assess_harness_categorization(wires, bundles, [])
        self.assertFalse(report["compliant"])
        self.assertTrue(report["route_findings"])

    def test_duplicate_wire_id_raises(self):
        wires, bundles, records = self.clean_harness()
        wires.append(wire("W-D1"))
        with self.assertRaises(ValueError):
            assess_harness_categorization(wires, bundles, records)

    def test_wire_in_two_bundles_raises(self):
        wires, bundles, records = self.clean_harness()
        bundles.append(bundle("B-X", "R-X", ["W-D1"]))
        with self.assertRaises(ValueError):
            assess_harness_categorization(wires, bundles, records)

    def test_duplicate_bundle_id_raises(self):
        wires, bundles, records = self.clean_harness()
        bundles.append(bundle("B-D", "R-X", ["W-P1"]))
        with self.assertRaises(ValueError):
            assess_harness_categorization(wires, bundles, records)

    def test_empty_wire_list_raises(self):
        _, bundles, records = self.clean_harness()
        with self.assertRaises(ValueError):
            assess_harness_categorization([], bundles, records)

    def test_empty_bundle_list_raises(self):
        wires, _, records = self.clean_harness()
        with self.assertRaises(ValueError):
            assess_harness_categorization(wires, [], records)

    def test_non_list_separation_records_raise(self):
        wires, bundles, _ = self.clean_harness()
        with self.assertRaises(ValueError):
            assess_harness_categorization(wires, bundles, {"route_a": "R-S"})


if __name__ == "__main__":
    unittest.main()
