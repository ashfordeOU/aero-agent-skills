#!/usr/bin/env python3
"""Gate 3 contract test for e2007-test-cable-representativeness.

Offline, deterministic, stdlib unittest only.
"""

import unittest

import e2007_test_cable_representativeness_logic as logic


def build(lay=50.0, coverage=85.0, foil=False, backshell=True,
          pigtail=None, pigtail_diameter=None, exposed=2.0):
    record = {
        "lay_length_mm": lay,
        "braid_coverage_percent": coverage,
        "foil_present": foil,
        "circumferential_backshell": backshell,
        "exposed_length_m": exposed,
    }
    if pigtail is not None:
        record["circumferential_backshell"] = False
        record["pigtail_length_mm"] = pigtail
        record["pigtail_diameter_mm"] = pigtail_diameter
    return record


def run(run_id="H1", flight=None, sample=None, required=2.0, **extra):
    record = {
        "run_id": run_id,
        "flight_build": flight if flight is not None else build(),
        "sample_build": sample if sample is not None else build(),
        "required_length_m": required,
    }
    record.update(extra)
    return record


class TwistingTests(unittest.TestCase):
    def test_lay_length_converts_to_twists_per_metre(self):
        self.assertAlmostEqual(logic.twists_per_metre(50.0), 20.0, places=12)

    def test_tighter_lay_gives_more_twists_per_metre(self):
        self.assertGreater(logic.twists_per_metre(25.0),
                           logic.twists_per_metre(50.0))

    def test_identical_lay_lengths_raise_no_finding(self):
        result = logic.compare_twisting(50.0, 50.0)
        self.assertTrue(result["within_tolerance"])
        self.assertEqual(result["findings"], [])

    def test_loose_sample_against_a_tight_flight_run_is_flagged(self):
        result = logic.compare_twisting(25.0, 100.0)
        self.assertFalse(result["within_tolerance"])
        self.assertIn("twist-lay-length-deviation", result["findings"][0])

    def test_allowance_scales_with_the_flight_twist_density(self):
        tight = logic.compare_twisting(20.0, 20.0)
        loose = logic.compare_twisting(80.0, 80.0)
        self.assertAlmostEqual(tight["allowed"], 5.0, places=12)
        self.assertAlmostEqual(loose["allowed"], 1.25, places=12)

    def test_representation_error_at_the_boundary_is_absorbed(self):
        # A 20 mm sample lay against a 22 mm flight lay is exactly 10 percent
        # tighter, but the twists-per-metre difference lands a few ULPs above
        # the allowance; the compliant case must still pass.
        result = logic.compare_twisting(22.0, 20.0, 0.10)
        self.assertGreater(result["deviation"], result["allowed"])
        self.assertTrue(result["within_tolerance"])
        self.assertEqual(result["findings"], [])

    def test_zero_lay_length_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.twists_per_metre(0.0)

    def test_negative_lay_length_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.compare_twisting(-50.0, 50.0)

    def test_tolerance_above_unity_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.compare_twisting(50.0, 50.0, 1.4)

    def test_zero_tolerance_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.compare_twisting(50.0, 50.0, 0.0)


class ShieldConstructionTests(unittest.TestCase):
    def test_braid_only_is_categorized_as_braid(self):
        self.assertEqual(
            logic.categorize_shield_construction({"braid_coverage_percent": 90.0}),
            "braid",
        )

    def test_foil_only_is_categorized_as_foil(self):
        self.assertEqual(
            logic.categorize_shield_construction({"foil_present": True}), "foil"
        )

    def test_braid_over_foil_is_its_own_construction(self):
        record = {"braid_coverage_percent": 85.0, "foil_present": True}
        self.assertEqual(logic.categorize_shield_construction(record),
                         "braid-over-foil")

    def test_no_shield_hardware_is_uncategorized_as_unshielded(self):
        self.assertEqual(logic.categorize_shield_construction({}), "unshielded")

    def test_zero_coverage_is_not_a_braid(self):
        self.assertEqual(
            logic.categorize_shield_construction({"braid_coverage_percent": 0.0}),
            "unshielded",
        )

    def test_every_construction_is_in_the_declared_tuple(self):
        for record in ({"braid_coverage_percent": 90.0}, {"foil_present": True},
                       {"braid_coverage_percent": 80.0, "foil_present": True},
                       {}):
            self.assertIn(logic.categorize_shield_construction(record),
                          logic.SHIELD_CONSTRUCTIONS)

    def test_coverage_is_reported_for_a_braid(self):
        self.assertAlmostEqual(
            logic.braid_coverage({"braid_coverage_percent": 88.0}), 88.0,
            places=12,
        )

    def test_coverage_is_absent_for_a_foil(self):
        self.assertIsNone(logic.braid_coverage({"foil_present": True}))

    def test_coverage_above_one_hundred_percent_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.categorize_shield_construction({"braid_coverage_percent": 120.0})

    def test_negative_coverage_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.categorize_shield_construction({"braid_coverage_percent": -3.0})

    def test_non_boolean_foil_flag_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.categorize_shield_construction({"foil_present": "yes"})

    def test_non_mapping_shield_record_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.categorize_shield_construction("braid")


class ShieldComparisonTests(unittest.TestCase):
    def test_matching_braids_raise_no_finding(self):
        result = logic.compare_shielding({"braid_coverage_percent": 85.0},
                                         {"braid_coverage_percent": 85.0})
        self.assertEqual(result["findings"], [])

    def test_foil_substituted_for_braid_is_flagged(self):
        result = logic.compare_shielding({"braid_coverage_percent": 85.0},
                                         {"foil_present": True})
        self.assertIn("shield-construction-mismatch",
                      " ".join(result["findings"]))

    def test_coverage_within_the_allowance_raises_no_finding(self):
        result = logic.compare_shielding({"braid_coverage_percent": 85.0},
                                         {"braid_coverage_percent": 82.0})
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["coverage_deviation_points"], 3.0,
                               places=12)

    def test_coverage_beyond_the_allowance_is_flagged(self):
        result = logic.compare_shielding({"braid_coverage_percent": 90.0},
                                         {"braid_coverage_percent": 70.0})
        self.assertIn("braid-optical-coverage-deviation",
                      " ".join(result["findings"]))

    def test_coverage_allowance_can_be_tightened(self):
        result = logic.compare_shielding({"braid_coverage_percent": 90.0},
                                         {"braid_coverage_percent": 87.0}, 1.0)
        self.assertIn("braid-optical-coverage-deviation",
                      " ".join(result["findings"]))

    def test_unshielded_sample_against_a_shielded_flight_run_is_flagged(self):
        result = logic.compare_shielding({"braid_coverage_percent": 90.0}, {})
        self.assertEqual(result["sample_construction"], "unshielded")
        self.assertTrue(result["findings"])

    def test_negative_coverage_allowance_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.compare_shielding({"braid_coverage_percent": 90.0},
                                    {"braid_coverage_percent": 90.0}, -1.0)


class ShieldTerminationTests(unittest.TestCase):
    def test_backshell_is_categorized(self):
        self.assertEqual(
            logic.categorize_shield_termination(
                {"circumferential_backshell": True}
            ),
            "circumferential-backshell",
        )

    def test_pigtail_is_categorized(self):
        self.assertEqual(
            logic.categorize_shield_termination({"pigtail_length_mm": 20.0}),
            "pigtail",
        )

    def test_no_landing_is_uncategorized_as_unterminated(self):
        self.assertEqual(logic.categorize_shield_termination({}),
                         "unterminated")

    def test_every_termination_is_in_the_declared_tuple(self):
        for record in ({"circumferential_backshell": True},
                       {"pigtail_length_mm": 20.0}, {}):
            self.assertIn(logic.categorize_shield_termination(record),
                          logic.SHIELD_TERMINATIONS)

    def test_backshell_and_pigtail_together_are_rejected(self):
        with self.assertRaises(ValueError):
            logic.categorize_shield_termination(
                {"circumferential_backshell": True, "pigtail_length_mm": 20.0}
            )

    def test_zero_pigtail_length_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.categorize_shield_termination({"pigtail_length_mm": 0.0})

    def test_non_boolean_backshell_flag_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.categorize_shield_termination(
                {"circumferential_backshell": 1}
            )


class PigtailInductanceTests(unittest.TestCase):
    def test_inductance_follows_the_round_wire_relation(self):
        import math
        value = logic.pigtail_inductance_nh(25.0, 1.0)
        expected = 0.2 * 25.0 * (math.log(100.0) - 0.75)
        self.assertAlmostEqual(value, expected, places=9)

    def test_inductance_grows_with_pigtail_length(self):
        short = logic.pigtail_inductance_nh(15.0, 1.0)
        long = logic.pigtail_inductance_nh(60.0, 1.0)
        self.assertGreater(long, short)

    def test_thicker_wire_only_weakly_reduces_inductance(self):
        thin = logic.pigtail_inductance_nh(40.0, 0.5)
        thick = logic.pigtail_inductance_nh(40.0, 2.0)
        self.assertLess(thick, thin)
        self.assertGreater(thick, 0.5 * thin)

    def test_zero_diameter_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.pigtail_inductance_nh(25.0, 0.0)

    def test_negative_length_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.pigtail_inductance_nh(-25.0, 1.0)

    def test_length_close_to_the_diameter_is_out_of_range(self):
        with self.assertRaises(ValueError):
            logic.pigtail_inductance_nh(1.0, 4.0)


class TerminationComparisonTests(unittest.TestCase):
    def test_matching_backshells_raise_no_finding(self):
        result = logic.compare_termination(
            {"circumferential_backshell": True},
            {"circumferential_backshell": True},
        )
        self.assertEqual(result["findings"], [])

    def test_pigtail_substituted_for_a_backshell_is_flagged(self):
        result = logic.compare_termination(
            {"circumferential_backshell": True},
            {"pigtail_length_mm": 20.0, "pigtail_diameter_mm": 1.0},
        )
        self.assertIn("shield-termination-mismatch",
                      " ".join(result["findings"]))

    def test_unterminated_sample_is_flagged_on_its_own(self):
        result = logic.compare_termination(
            {"circumferential_backshell": True}, {}
        )
        self.assertIn("sample-shield-unterminated",
                      " ".join(result["findings"]))

    def test_matching_short_pigtails_raise_no_finding(self):
        flight = {"pigtail_length_mm": 15.0, "pigtail_diameter_mm": 1.0}
        sample = {"pigtail_length_mm": 15.0, "pigtail_diameter_mm": 1.0}
        result = logic.compare_termination(flight, sample)
        self.assertEqual(result["findings"], [])
        self.assertGreater(result["sample_pigtail_inductance_nh"], 0.0)

    def test_long_pigtail_breaches_both_ceilings(self):
        flight = {"pigtail_length_mm": 15.0, "pigtail_diameter_mm": 1.0}
        sample = {"pigtail_length_mm": 120.0, "pigtail_diameter_mm": 1.0}
        result = logic.compare_termination(flight, sample)
        joined = " ".join(result["findings"])
        self.assertIn("pigtail-length-exceeded", joined)
        self.assertIn("pigtail-inductance-exceeded", joined)

    def test_pigtail_without_a_diameter_is_rejected(self):
        flight = {"pigtail_length_mm": 15.0, "pigtail_diameter_mm": 1.0}
        sample = {"pigtail_length_mm": 15.0}
        with self.assertRaises(ValueError):
            logic.compare_termination(flight, sample)

    def test_zero_length_ceiling_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.compare_termination({"circumferential_backshell": True},
                                      {"circumferential_backshell": True}, 0.0)


class ExposedRunLengthTests(unittest.TestCase):
    def test_adequate_run_length_raises_no_finding(self):
        result = logic.check_exposed_run_length(2.0, 2.0)
        self.assertTrue(result["adequate"])
        self.assertEqual(result["findings"], [])

    def test_short_run_is_flagged(self):
        result = logic.check_exposed_run_length(0.8, 2.0)
        self.assertFalse(result["adequate"])
        self.assertIn("exposed-run-length-short", result["findings"][0])

    def test_longer_than_required_is_accepted(self):
        self.assertTrue(logic.check_exposed_run_length(3.5, 2.0)["adequate"])

    def test_zero_sample_length_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.check_exposed_run_length(0.0, 2.0)

    def test_zero_required_length_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.check_exposed_run_length(2.0, 0.0)


class HarnessRunTests(unittest.TestCase):
    def test_a_faithful_sample_passes(self):
        result = logic.assess_harness_run(run())
        self.assertTrue(result["representative"])
        self.assertEqual(result["findings"], [])

    def test_a_bench_lash_up_collects_several_findings(self):
        sample = build(lay=200.0, coverage=None, foil=False, backshell=False,
                       exposed=0.5)
        result = logic.assess_harness_run(run(sample=sample))
        self.assertFalse(result["representative"])
        self.assertGreaterEqual(len(result["findings"]), 3)

    def test_run_reports_each_comparison_block(self):
        result = logic.assess_harness_run(run())
        for key in ("twisting", "shielding", "termination", "run_length"):
            self.assertIn(key, result)

    def test_missing_run_id_is_rejected(self):
        record = run()
        del record["run_id"]
        with self.assertRaises(ValueError):
            logic.assess_harness_run(record)

    def test_blank_run_id_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.assess_harness_run(run(run_id="  "))

    def test_missing_sample_build_is_rejected(self):
        record = run()
        del record["sample_build"]
        with self.assertRaises(ValueError):
            logic.assess_harness_run(record)

    def test_missing_required_length_is_rejected(self):
        record = run()
        del record["required_length_m"]
        with self.assertRaises(ValueError):
            logic.assess_harness_run(record)


class SetupAssessmentTests(unittest.TestCase):
    def test_every_faithful_run_passes(self):
        setup = {"unit_id": "TRX-1", "harness_runs": [run("H1"), run("H2")]}
        result = logic.assess_cable_representativeness(setup)
        self.assertTrue(result["representative"])
        self.assertEqual(result["run_count"], 2)

    def test_findings_are_tagged_with_the_run_identifier(self):
        bad = run("H2", sample=build(backshell=False))
        setup = {"unit_id": "TRX-1", "harness_runs": [run("H1"), bad]}
        result = logic.assess_cable_representativeness(setup)
        self.assertFalse(result["representative"])
        self.assertTrue(all(f.startswith("H2:") for f in result["findings"]))

    def test_tolerance_fraction_applies_to_every_run(self):
        sample = build(lay=54.0)
        setup = {"unit_id": "TRX-1", "harness_runs": [run("H1", sample=sample)],
                 "tolerance_fraction": 0.02}
        result = logic.assess_cable_representativeness(setup)
        self.assertIn("twist-lay-length-deviation",
                      " ".join(result["findings"]))

    def test_coverage_allowance_applies_to_every_run(self):
        sample = build(coverage=82.0)
        setup = {"unit_id": "TRX-1", "harness_runs": [run("H1", sample=sample)],
                 "coverage_allowance_points": 1.0}
        result = logic.assess_cable_representativeness(setup)
        self.assertIn("braid-optical-coverage-deviation",
                      " ".join(result["findings"]))

    def test_repeated_run_identifier_is_rejected(self):
        setup = {"unit_id": "TRX-1", "harness_runs": [run("H1"), run("H1")]}
        with self.assertRaises(ValueError):
            logic.assess_cable_representativeness(setup)

    def test_empty_harness_list_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.assess_cable_representativeness({"unit_id": "TRX-1",
                                                   "harness_runs": []})

    def test_harness_runs_given_as_a_mapping_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.assess_cable_representativeness({"unit_id": "TRX-1",
                                                   "harness_runs": run("H1")})

    def test_missing_unit_id_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.assess_cable_representativeness({"harness_runs": [run("H1")]})

    def test_non_mapping_setup_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.assess_cable_representativeness("TRX-1")


if __name__ == "__main__":
    unittest.main()
