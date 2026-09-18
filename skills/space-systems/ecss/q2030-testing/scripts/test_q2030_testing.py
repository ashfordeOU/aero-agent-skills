"""Contract test for the harness testing leaf (stdlib unittest)."""

import unittest

from q2030_testing_logic import (
    CONTINUITY_TOLERANCE_FRACTION,
    DIELECTRIC_RETEST_FACTOR,
    MAX_DIELECTRIC_LEAKAGE_UA,
    MIN_DIELECTRIC_DWELL_S,
    MIN_INSULATION_ELECTRIFICATION_S,
    MIN_INSULATION_RESISTANCE_MOHM,
    MIN_PULL_FORCE_N,
    TEST_CONTINUITY,
    TEST_DIELECTRIC,
    TEST_INSULATION,
    TEST_MECHANICAL,
    TEST_VISUAL,
    assess_harness_lot,
    assess_harness_test_programme,
    continuity_findings,
    continuity_limit_ohm,
    dielectric_findings,
    dielectric_test_voltage_v,
    expected_loop_resistance_ohm,
    insulation_findings,
    mechanical_findings,
    minimum_pull_force_n,
    missing_tests,
    required_tests,
    tests_after_rework,
    validate_harness,
)


def results(**over):
    base = {
        TEST_VISUAL: {"accepted": True},
        TEST_CONTINUITY: {"measured_ohm": 0.05},
        TEST_INSULATION: {
            "measured_mohm": 500.0,
            "test_voltage_v": 500.0,
            "electrification_time_s": 60.0,
        },
        TEST_DIELECTRIC: {"applied_v": 1200.0, "leakage_ua": 10.0, "dwell_s": 60.0},
    }
    base.update(over)
    return base


def harness(hid="H-1", **kw):
    record = {
        "id": hid,
        "conductor_count": 8,
        "contact_pairs": 2,
        "length_m": 2.0,
        "cross_section_mm2": 0.38,
        "shielded": True,
        "working_voltage_v": 100.0,
        "mechanical_test_called": False,
        "reworked": False,
        "results": results(),
    }
    record.update(kw)
    return record


class TestValidateHarness(unittest.TestCase):
    def test_defaults_are_filled_in(self):
        norm = validate_harness(
            {
                "id": "H-1",
                "conductor_count": 1,
                "length_m": 1.0,
                "cross_section_mm2": 0.25,
            }
        )
        self.assertEqual(norm["contact_pairs"], 2)
        self.assertFalse(norm["shielded"])
        self.assertEqual(norm["working_voltage_v"], 0.0)
        self.assertEqual(norm["results"], {})

    def test_non_mapping_raises(self):
        with self.assertRaises(ValueError):
            validate_harness(["H-1"])

    def test_empty_id_raises(self):
        with self.assertRaises(ValueError):
            validate_harness(harness(""))

    def test_zero_conductor_count_raises(self):
        with self.assertRaises(ValueError):
            validate_harness(harness(conductor_count=0))

    def test_boolean_conductor_count_raises(self):
        with self.assertRaises(ValueError):
            validate_harness(harness(conductor_count=True))

    def test_negative_length_raises(self):
        with self.assertRaises(ValueError):
            validate_harness(harness(length_m=-1.0))

    def test_zero_cross_section_raises(self):
        with self.assertRaises(ValueError):
            validate_harness(harness(cross_section_mm2=0.0))

    def test_unknown_test_result_raises(self):
        with self.assertRaises(ValueError):
            validate_harness(harness(results={"smoke-test": {}}))

    def test_non_boolean_shield_flag_raises(self):
        with self.assertRaises(ValueError):
            validate_harness(harness(shielded="yes"))


class TestRequiredTests(unittest.TestCase):
    def test_every_harness_owes_visual_and_continuity(self):
        owed = required_tests(
            harness(conductor_count=1, shielded=False, working_voltage_v=5.0)
        )
        self.assertEqual(owed, [TEST_VISUAL, TEST_CONTINUITY])

    def test_multiconductor_owes_insulation_resistance(self):
        self.assertIn(TEST_INSULATION, required_tests(harness(working_voltage_v=5.0)))

    def test_single_shielded_conductor_owes_insulation_resistance(self):
        owed = required_tests(
            harness(conductor_count=1, shielded=True, working_voltage_v=5.0)
        )
        self.assertIn(TEST_INSULATION, owed)

    def test_low_working_voltage_does_not_owe_a_dielectric_test(self):
        self.assertNotIn(TEST_DIELECTRIC, required_tests(harness(working_voltage_v=50.0)))

    def test_high_working_voltage_owes_a_dielectric_test(self):
        self.assertIn(TEST_DIELECTRIC, required_tests(harness(working_voltage_v=100.0)))

    def test_mechanical_test_is_owed_only_when_called(self):
        self.assertIn(
            TEST_MECHANICAL, required_tests(harness(mechanical_test_called=True))
        )
        self.assertNotIn(TEST_MECHANICAL, required_tests(harness()))

    def test_required_tests_come_back_in_run_order(self):
        owed = required_tests(harness(mechanical_test_called=True))
        self.assertEqual(
            owed,
            [TEST_VISUAL, TEST_CONTINUITY, TEST_INSULATION, TEST_DIELECTRIC, TEST_MECHANICAL],
        )


class TestContinuity(unittest.TestCase):
    def test_expected_resistance_sums_conductor_and_contacts(self):
        value = expected_loop_resistance_ohm(2.0, 0.38, 2)
        self.assertAlmostEqual(value, 1.72e-8 * 2.0 / 0.38e-6 + 0.01, places=9)

    def test_expected_resistance_rejects_a_zero_cross_section(self):
        with self.assertRaises(ValueError):
            expected_loop_resistance_ohm(2.0, 0.0, 2)

    def test_expected_resistance_rejects_a_fractional_contact_count(self):
        with self.assertRaises(ValueError):
            expected_loop_resistance_ohm(2.0, 0.38, 1.5)

    def test_limit_widens_the_expectation_by_the_tolerance(self):
        self.assertAlmostEqual(
            continuity_limit_ohm(0.1), 0.1 * (1.0 + CONTINUITY_TOLERANCE_FRACTION), places=9
        )

    def test_reading_exactly_on_the_limit_is_accepted(self):
        expected = expected_loop_resistance_ohm(2.0, 0.38, 2)
        limit = continuity_limit_ohm(expected)
        on_limit = harness(results=results(**{TEST_CONTINUITY: {"measured_ohm": limit}}))
        self.assertEqual(continuity_findings(on_limit), [])

    def test_reading_above_the_limit_is_a_finding(self):
        bad = harness(results=results(**{TEST_CONTINUITY: {"measured_ohm": 5.0}}))
        self.assertIn(
            "continuity-resistance-above-the-computed-limit", continuity_findings(bad)
        )

    def test_absent_continuity_result_is_a_finding(self):
        bare = harness(results={TEST_VISUAL: {"accepted": True}})
        self.assertEqual(
            continuity_findings(bare), ["no-continuity-measurement-on-record"]
        )


class TestInsulation(unittest.TestCase):
    def test_healthy_insulation_result_is_clean(self):
        self.assertEqual(insulation_findings(harness()), [])

    def test_resistance_below_the_floor_is_a_finding(self):
        low = harness(
            results=results(
                **{
                    TEST_INSULATION: {
                        "measured_mohm": MIN_INSULATION_RESISTANCE_MOHM / 2.0,
                        "electrification_time_s": MIN_INSULATION_ELECTRIFICATION_S,
                    }
                }
            )
        )
        self.assertIn("insulation-resistance-below-the-floor", insulation_findings(low))

    def test_reading_on_the_floor_exactly_is_accepted(self):
        on_floor = harness(
            results=results(
                **{
                    TEST_INSULATION: {
                        "measured_mohm": MIN_INSULATION_RESISTANCE_MOHM,
                        "electrification_time_s": MIN_INSULATION_ELECTRIFICATION_S,
                    }
                }
            )
        )
        self.assertEqual(insulation_findings(on_floor), [])

    def test_short_electrification_time_is_a_finding(self):
        early = harness(
            results=results(
                **{
                    TEST_INSULATION: {
                        "measured_mohm": 500.0,
                        "electrification_time_s": 5.0,
                    }
                }
            )
        )
        self.assertIn(
            "insulation-reading-taken-before-electrification-time",
            insulation_findings(early),
        )

    def test_insulation_is_not_graded_when_not_owed(self):
        single = harness(conductor_count=1, shielded=False, results=results())
        self.assertEqual(insulation_findings(single), [])


class TestDielectric(unittest.TestCase):
    def test_voltage_is_derived_from_the_working_voltage(self):
        self.assertAlmostEqual(dielectric_test_voltage_v(100.0), 1200.0, places=9)

    def test_retest_voltage_is_reduced(self):
        self.assertAlmostEqual(
            dielectric_test_voltage_v(100.0, previously_tested=True),
            1200.0 * DIELECTRIC_RETEST_FACTOR,
            places=9,
        )

    def test_non_boolean_retest_flag_raises(self):
        with self.assertRaises(ValueError):
            dielectric_test_voltage_v(100.0, previously_tested="yes")

    def test_applied_below_the_derived_level_is_a_finding(self):
        low = harness(
            results=results(
                **{TEST_DIELECTRIC: {"applied_v": 500.0, "leakage_ua": 1.0, "dwell_s": 60.0}}
            )
        )
        self.assertIn(
            "dielectric-test-voltage-below-the-derived-level", dielectric_findings(low)
        )

    def test_leakage_above_the_limit_is_a_finding(self):
        leaky = harness(
            results=results(
                **{
                    TEST_DIELECTRIC: {
                        "applied_v": 1200.0,
                        "leakage_ua": MAX_DIELECTRIC_LEAKAGE_UA * 2.0,
                        "dwell_s": MIN_DIELECTRIC_DWELL_S,
                    }
                }
            )
        )
        self.assertIn(
            "dielectric-leakage-current-above-the-limit", dielectric_findings(leaky)
        )

    def test_short_dwell_is_a_finding(self):
        brief = harness(
            results=results(
                **{TEST_DIELECTRIC: {"applied_v": 1200.0, "leakage_ua": 1.0, "dwell_s": 5.0}}
            )
        )
        self.assertIn("dielectric-dwell-shorter-than-required", dielectric_findings(brief))

    def test_retest_at_the_full_level_is_a_finding(self):
        over = harness(
            reworked=True,
            results=results(
                **{
                    TEST_DIELECTRIC: {
                        "applied_v": 1200.0,
                        "leakage_ua": 1.0,
                        "dwell_s": 60.0,
                    }
                }
            ),
        )
        self.assertIn("retest-applied-above-the-reduced-level", dielectric_findings(over))

    def test_retest_at_the_reduced_level_is_clean(self):
        clean = harness(
            reworked=True,
            results=results(
                **{
                    TEST_DIELECTRIC: {
                        "applied_v": 1200.0 * DIELECTRIC_RETEST_FACTOR,
                        "leakage_ua": 1.0,
                        "dwell_s": 60.0,
                    }
                }
            ),
        )
        self.assertEqual(dielectric_findings(clean), [])


class TestMechanical(unittest.TestCase):
    def test_pull_force_scales_with_cross_section(self):
        self.assertAlmostEqual(minimum_pull_force_n(1.0), 60.0, places=9)

    def test_fine_gauge_pull_force_is_floored(self):
        self.assertAlmostEqual(minimum_pull_force_n(0.05), MIN_PULL_FORCE_N, places=9)

    def test_pull_force_rejects_a_zero_cross_section(self):
        with self.assertRaises(ValueError):
            minimum_pull_force_n(0.0)

    def test_pull_below_the_minimum_is_a_finding(self):
        weak = harness(
            mechanical_test_called=True,
            cross_section_mm2=1.0,
            results=results(**{TEST_MECHANICAL: {"applied_force_n": 10.0}}),
        )
        self.assertIn("pull-force-below-the-scaled-minimum", mechanical_findings(weak))

    def test_pull_exactly_on_the_minimum_is_accepted(self):
        exact = harness(
            mechanical_test_called=True,
            cross_section_mm2=1.0,
            results=results(**{TEST_MECHANICAL: {"applied_force_n": 60.0}}),
        )
        self.assertEqual(mechanical_findings(exact), [])


class TestRework(unittest.TestCase):
    def test_an_untouched_harness_repeats_nothing(self):
        self.assertEqual(tests_after_rework(harness()), [])

    def test_rework_repeats_visual_and_continuity(self):
        self.assertEqual(
            tests_after_rework(harness(reworked=True)), [TEST_VISUAL, TEST_CONTINUITY]
        )

    def test_insulation_rework_repeats_the_isolation_tests(self):
        repeats = tests_after_rework(
            harness(reworked=True, rework_touched_insulation=True)
        )
        self.assertEqual(
            repeats, [TEST_VISUAL, TEST_CONTINUITY, TEST_INSULATION, TEST_DIELECTRIC]
        )


class TestAssessment(unittest.TestCase):
    def test_a_complete_harness_is_compliant(self):
        report = assess_harness_test_programme(harness())
        self.assertTrue(report["compliant"])
        self.assertEqual(report["missing_tests"], [])
        self.assertAlmostEqual(report["dielectric_test_voltage_v"], 1200.0, places=9)

    def test_missing_results_are_named(self):
        bare = harness(results={TEST_VISUAL: {"accepted": True}})
        report = assess_harness_test_programme(bare)
        self.assertEqual(
            report["missing_tests"], [TEST_CONTINUITY, TEST_INSULATION, TEST_DIELECTRIC]
        )
        self.assertFalse(report["compliant"])

    def test_rejected_visual_is_a_finding(self):
        rejected = harness(results=results(**{TEST_VISUAL: {"accepted": False}}))
        report = assess_harness_test_programme(rejected)
        self.assertIn("visual-examination-not-accepted", report["findings"])

    def test_missing_tests_matches_the_owed_set(self):
        bare = harness(results={})
        self.assertEqual(missing_tests(bare), required_tests(bare))

    def test_lot_groups_reworked_harnesses(self):
        report = assess_harness_lot(
            [
                harness("H-1"),
                harness(
                    "H-2",
                    reworked=True,
                    results=results(
                        **{
                            TEST_DIELECTRIC: {
                                "applied_v": 1200.0 * DIELECTRIC_RETEST_FACTOR,
                                "leakage_ua": 1.0,
                                "dwell_s": 60.0,
                            }
                        }
                    ),
                ),
            ]
        )
        self.assertEqual(report["reworked_ids"], ["H-2"])
        self.assertTrue(report["compliant"])

    def test_duplicate_harness_id_raises(self):
        with self.assertRaises(ValueError):
            assess_harness_lot([harness("H-1"), harness("H-1")])

    def test_empty_lot_raises(self):
        with self.assertRaises(ValueError):
            assess_harness_lot([])

    def test_non_list_lot_raises(self):
        with self.assertRaises(ValueError):
            assess_harness_lot(harness())


if __name__ == "__main__":
    unittest.main()
