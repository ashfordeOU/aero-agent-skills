"""Contract test for the system radiofrequency compatibility test leaf."""

import unittest

from e2007_system_radiofrequency_compatibility_test_logic import (
    BAND_IN,
    BAND_OUT,
    DEFAULT_REQUIRED_MARGIN_DB,
    HARMONIC_ROLLOFF_DB_PER_ORDER,
    MECHANISM_FUNDAMENTAL,
    MECHANISM_HARMONIC,
    MECHANISM_PASSIVE_INTERMODULATION,
    MECHANISM_SPURIOUS,
    assess_rf_compatibility,
    band_of_product,
    build_test_matrix,
    check_margins,
    check_matrix_coverage,
    coupled_level_dbm,
    effective_susceptibility_dbm,
    emission_products,
    interference_margin_db,
    is_in_test_scope,
    isolation_for_pair,
    mandatory_case_ids,
    modes_can_coexist,
    validate_case_results,
    validate_emitter,
    validate_receiver,
)

FUNDAMENTAL_CASE = "TX-S/RX-NAV/fundamental/1"


def emitter(eid="TX-S", **kw):
    record = {
        "id": eid,
        "frequency_mhz": 2200.0,
        "power_dbm": 33.0,
        "antenna_gain_dbi": 6.0,
        "harmonic_suppression_db": 60.0,
        "operating_modes": ["nominal"],
    }
    record.update(kw)
    return record


def receiver(rid="RX-NAV", **kw):
    record = {
        "id": rid,
        "centre_frequency_mhz": 1575.0,
        "bandwidth_mhz": 20.0,
        "susceptibility_dbm": -110.0,
        "antenna_gain_dbi": 3.0,
        "out_of_band_rejection_db": 60.0,
        "operating_modes": ["nominal"],
    }
    record.update(kw)
    return record


def system(isolation_db=130.0, **kw):
    record = {
        "emitters": [emitter()],
        "receivers": [receiver()],
        "isolations": {("TX-S", "RX-NAV"): isolation_db},
        "max_harmonic_order": 3,
    }
    record.update(kw)
    return record


class TestValidateEmitter(unittest.TestCase):
    def test_defaults_are_filled_in(self):
        norm = validate_emitter(
            {"id": "TX-S", "frequency_mhz": 2200.0, "power_dbm": 30.0}
        )
        self.assertAlmostEqual(norm["antenna_gain_dbi"], 0.0, places=9)
        self.assertEqual(norm["spurious_lines"], ())
        self.assertEqual(norm["operating_modes"], ("transmit",))

    def test_non_mapping_raises(self):
        with self.assertRaises(ValueError):
            validate_emitter(["TX-S"])

    def test_empty_id_raises(self):
        with self.assertRaises(ValueError):
            validate_emitter(emitter(""))

    def test_zero_frequency_raises(self):
        with self.assertRaises(ValueError):
            validate_emitter(emitter(frequency_mhz=0.0))

    def test_missing_power_raises(self):
        with self.assertRaises(ValueError):
            validate_emitter({"id": "TX-S", "frequency_mhz": 2200.0})

    def test_negative_harmonic_suppression_raises(self):
        with self.assertRaises(ValueError):
            validate_emitter(emitter(harmonic_suppression_db=-1.0))

    def test_unknown_spurious_mechanism_raises(self):
        with self.assertRaises(ValueError):
            validate_emitter(
                emitter(spurious_lines=[{"frequency_mhz": 1575.0,
                                         "mechanism": "cosmic"}])
            )

    def test_empty_operating_modes_raises(self):
        with self.assertRaises(ValueError):
            validate_emitter(emitter(operating_modes=[]))


class TestValidateReceiver(unittest.TestCase):
    def test_defaults_are_filled_in(self):
        norm = validate_receiver(
            {"id": "RX-NAV", "centre_frequency_mhz": 1575.0,
             "bandwidth_mhz": 20.0, "susceptibility_dbm": -110.0}
        )
        self.assertAlmostEqual(norm["out_of_band_rejection_db"], 30.0, places=9)
        self.assertEqual(norm["operating_modes"], ("receive",))

    def test_non_mapping_raises(self):
        with self.assertRaises(ValueError):
            validate_receiver("RX-NAV")

    def test_zero_bandwidth_raises(self):
        with self.assertRaises(ValueError):
            validate_receiver(receiver(bandwidth_mhz=0.0))

    def test_negative_centre_frequency_raises(self):
        with self.assertRaises(ValueError):
            validate_receiver(receiver(centre_frequency_mhz=-1575.0))

    def test_negative_rejection_raises(self):
        with self.assertRaises(ValueError):
            validate_receiver(receiver(out_of_band_rejection_db=-10.0))

    def test_non_numeric_susceptibility_raises(self):
        with self.assertRaises(ValueError):
            validate_receiver(receiver(susceptibility_dbm="-110"))


class TestEmissionProducts(unittest.TestCase):
    def test_the_fundamental_is_always_present(self):
        products = emission_products(emitter(), 1)
        self.assertEqual(len(products), 1)
        self.assertEqual(products[0]["mechanism"], MECHANISM_FUNDAMENTAL)
        self.assertAlmostEqual(products[0]["frequency_mhz"], 2200.0, places=9)

    def test_harmonics_sit_at_integer_multiples(self):
        products = emission_products(emitter(), 3)
        harmonics = [p for p in products if p["mechanism"] == MECHANISM_HARMONIC]
        self.assertEqual(len(harmonics), 2)
        self.assertAlmostEqual(harmonics[0]["frequency_mhz"], 4400.0, places=9)
        self.assertAlmostEqual(harmonics[1]["frequency_mhz"], 6600.0, places=9)

    def test_the_second_harmonic_sits_at_the_declared_suppression(self):
        harmonic = emission_products(emitter(), 2)[1]
        self.assertAlmostEqual(harmonic["level_dbm"], 33.0 - 60.0, places=9)

    def test_each_further_order_adds_the_rolloff(self):
        products = emission_products(emitter(), 3)
        self.assertAlmostEqual(
            products[2]["level_dbm"],
            products[1]["level_dbm"] - HARMONIC_ROLLOFF_DB_PER_ORDER,
            places=9,
        )

    def test_a_spurious_line_is_referred_to_the_carrier(self):
        products = emission_products(
            emitter(spurious_lines=[{"frequency_mhz": 1575.0, "level_dbc": -70.0}]), 1
        )
        spurious = [p for p in products if p["mechanism"] == MECHANISM_SPURIOUS]
        self.assertAlmostEqual(spurious[0]["level_dbm"], 33.0 - 70.0, places=9)

    def test_zero_harmonic_order_raises(self):
        with self.assertRaises(ValueError):
            emission_products(emitter(), 0)

    def test_non_integer_harmonic_order_raises(self):
        with self.assertRaises(ValueError):
            emission_products(emitter(), 2.5)


class TestScopeAndBand(unittest.TestCase):
    def test_a_harmonic_is_owned_by_this_test(self):
        self.assertTrue(is_in_test_scope(MECHANISM_HARMONIC))

    def test_a_passive_intermodulation_product_is_excluded(self):
        self.assertFalse(is_in_test_scope(MECHANISM_PASSIVE_INTERMODULATION))

    def test_an_unknown_mechanism_raises(self):
        with self.assertRaises(ValueError):
            is_in_test_scope("thermal")

    def test_a_product_on_the_centre_frequency_is_in_band(self):
        self.assertEqual(band_of_product(1575.0, receiver()), BAND_IN)

    def test_a_product_on_the_passband_edge_is_in_band(self):
        self.assertEqual(band_of_product(1585.0, receiver()), BAND_IN)

    def test_a_product_beyond_the_passband_edge_is_out_of_band(self):
        self.assertEqual(band_of_product(1600.0, receiver()), BAND_OUT)

    def test_a_non_positive_product_frequency_raises(self):
        with self.assertRaises(ValueError):
            band_of_product(0.0, receiver())


class TestCouplingArithmetic(unittest.TestCase):
    def test_gains_add_and_isolation_subtracts(self):
        self.assertAlmostEqual(
            coupled_level_dbm(33.0, 6.0, 3.0, 90.0), -48.0, places=9
        )

    def test_negative_isolation_raises(self):
        with self.assertRaises(ValueError):
            coupled_level_dbm(33.0, 6.0, 3.0, -1.0)

    def test_in_band_susceptibility_is_the_declared_one(self):
        self.assertAlmostEqual(
            effective_susceptibility_dbm(receiver(), BAND_IN), -110.0, places=9
        )

    def test_out_of_band_susceptibility_carries_the_rejection(self):
        self.assertAlmostEqual(
            effective_susceptibility_dbm(receiver(), BAND_OUT), -50.0, places=9
        )

    def test_an_unknown_band_raises(self):
        with self.assertRaises(ValueError):
            effective_susceptibility_dbm(receiver(), "near-band")

    def test_margin_is_the_threshold_less_the_coupled_level(self):
        self.assertAlmostEqual(
            interference_margin_db(-48.0, -50.0), -2.0, places=9
        )

    def test_a_coupled_level_on_the_threshold_gives_a_null_margin(self):
        self.assertAlmostEqual(
            interference_margin_db(-50.0, -50.0), 0.0, places=9
        )

    def test_a_declared_isolation_is_returned(self):
        self.assertAlmostEqual(
            isolation_for_pair({("TX-S", "RX-NAV"): 95.0}, "TX-S", "RX-NAV"),
            95.0,
            places=9,
        )

    def test_a_missing_pair_isolation_raises(self):
        with self.assertRaises(ValueError):
            isolation_for_pair({}, "TX-S", "RX-NAV")

    def test_units_sharing_a_mode_can_coexist(self):
        self.assertTrue(modes_can_coexist(emitter(), receiver()))

    def test_units_with_disjoint_modes_cannot_coexist(self):
        self.assertFalse(
            modes_can_coexist(emitter(operating_modes=["launch"]), receiver())
        )


class TestMatrixConstruction(unittest.TestCase):
    def test_every_in_scope_product_meets_every_receiver(self):
        matrix = build_test_matrix(system())
        self.assertEqual(len(matrix["cases"]), 3)
        self.assertEqual(matrix["excluded"], [])

    def test_a_passive_intermodulation_line_is_excluded_by_name(self):
        matrix = build_test_matrix(
            system(
                emitters=[
                    emitter(
                        spurious_lines=[
                            {
                                "frequency_mhz": 1575.0,
                                "level_dbc": -60.0,
                                "mechanism": MECHANISM_PASSIVE_INTERMODULATION,
                            }
                        ]
                    )
                ]
            )
        )
        self.assertEqual(len(matrix["excluded"]), 1)
        self.assertEqual(
            matrix["excluded"][0]["reason"],
            "passive-intermodulation-outside-this-test",
        )
        self.assertNotIn(
            MECHANISM_PASSIVE_INTERMODULATION,
            [case["mechanism"] for case in matrix["cases"]],
        )

    def test_a_well_isolated_system_makes_no_case_mandatory(self):
        self.assertEqual(mandatory_case_ids(build_test_matrix(system())), [])

    def test_a_poorly_isolated_fundamental_becomes_mandatory(self):
        matrix = build_test_matrix(system(isolation_db=90.0))
        self.assertEqual(mandatory_case_ids(matrix), [FUNDAMENTAL_CASE])

    def test_an_in_band_product_is_mandatory_whatever_the_margin(self):
        matrix = build_test_matrix(
            system(
                isolation_db=200.0,
                emitters=[emitter(frequency_mhz=1575.0)],
            )
        )
        in_band = [case for case in matrix["cases"] if case["band"] == BAND_IN]
        self.assertEqual(len(in_band), 1)
        self.assertTrue(in_band[0]["mandatory"])

    def test_units_that_never_run_together_make_no_mandatory_case(self):
        matrix = build_test_matrix(
            system(isolation_db=90.0, emitters=[emitter(operating_modes=["launch"])])
        )
        self.assertEqual(mandatory_case_ids(matrix), [])

    def test_a_duplicate_emitter_id_raises(self):
        with self.assertRaises(ValueError):
            build_test_matrix(system(emitters=[emitter(), emitter()]))

    def test_a_duplicate_receiver_id_raises(self):
        with self.assertRaises(ValueError):
            build_test_matrix(system(receivers=[receiver(), receiver()]))

    def test_an_empty_emitter_list_raises(self):
        with self.assertRaises(ValueError):
            build_test_matrix(system(emitters=[]))

    def test_a_missing_receiver_list_raises(self):
        with self.assertRaises(ValueError):
            build_test_matrix({"emitters": [emitter()]})

    def test_an_undeclared_pair_isolation_raises(self):
        with self.assertRaises(ValueError):
            build_test_matrix(system(isolations={}))


class TestResultsAndCoverage(unittest.TestCase):
    def test_a_missing_result_map_is_empty(self):
        self.assertEqual(validate_case_results(None), {})

    def test_an_unknown_result_value_raises(self):
        with self.assertRaises(ValueError):
            validate_case_results({FUNDAMENTAL_CASE: "probably"})

    def test_a_non_mapping_result_set_raises(self):
        with self.assertRaises(ValueError):
            validate_case_results([FUNDAMENTAL_CASE])

    def test_an_unexercised_mandatory_case_is_a_finding(self):
        matrix = build_test_matrix(system(isolation_db=90.0))
        self.assertEqual(
            check_matrix_coverage(matrix, {}),
            ["mandatory-case-not-exercised:%s" % FUNDAMENTAL_CASE],
        )

    def test_an_exercised_mandatory_case_clears_coverage(self):
        matrix = build_test_matrix(system(isolation_db=90.0))
        self.assertEqual(
            check_matrix_coverage(matrix, {FUNDAMENTAL_CASE: "pass"}), []
        )

    def test_a_result_for_an_unknown_case_is_a_finding(self):
        matrix = build_test_matrix(system())
        self.assertEqual(
            check_matrix_coverage(matrix, {"TX-X/RX-Y/fundamental/1": "pass"}),
            ["executed-case-absent-from-the-matrix:TX-X/RX-Y/fundamental/1"],
        )

    def test_a_margin_shortfall_without_a_test_is_a_finding(self):
        matrix = build_test_matrix(system(isolation_db=90.0))
        self.assertEqual(
            check_margins(matrix, {}),
            ["interference-margin-below-required:%s" % FUNDAMENTAL_CASE],
        )

    def test_a_passing_system_test_clears_a_margin_shortfall(self):
        matrix = build_test_matrix(system(isolation_db=90.0))
        self.assertEqual(check_margins(matrix, {FUNDAMENTAL_CASE: "pass"}), [])

    def test_a_failing_system_test_is_reported_as_interference(self):
        matrix = build_test_matrix(system(isolation_db=90.0))
        self.assertEqual(
            check_margins(matrix, {FUNDAMENTAL_CASE: "fail"}),
            ["system-test-demonstrated-interference:%s" % FUNDAMENTAL_CASE],
        )

    def test_a_margin_exactly_on_the_required_value_is_clean(self):
        matrix = build_test_matrix(system(isolation_db=130.0))
        case = [c for c in matrix["cases"]
                if c["mechanism"] == MECHANISM_FUNDAMENTAL][0]
        shifted = dict(case)
        shifted["margin_db"] = DEFAULT_REQUIRED_MARGIN_DB
        matrix["cases"] = [shifted]
        matrix["required_margin_db"] = DEFAULT_REQUIRED_MARGIN_DB
        self.assertEqual(check_margins(matrix, {}), [])


class TestAssessRfCompatibility(unittest.TestCase):
    def test_a_well_isolated_system_is_compliant(self):
        report = assess_rf_compatibility(system())
        self.assertEqual(report["findings"], [])
        self.assertTrue(report["compliant"])

    def test_an_uncovered_shortfall_raises_two_findings(self):
        report = assess_rf_compatibility(system(isolation_db=90.0))
        self.assertFalse(report["compliant"])
        self.assertIn(
            "interference-margin-below-required:%s" % FUNDAMENTAL_CASE,
            report["findings"],
        )
        self.assertIn(
            "mandatory-case-not-exercised:%s" % FUNDAMENTAL_CASE,
            report["findings"],
        )

    def test_a_demonstrated_case_closes_both_findings(self):
        report = assess_rf_compatibility(
            system(isolation_db=90.0, case_results={FUNDAMENTAL_CASE: "pass"})
        )
        self.assertEqual(report["findings"], [])
        self.assertTrue(report["compliant"])

    def test_the_excluded_products_stay_visible_in_the_report(self):
        report = assess_rf_compatibility(
            system(
                emitters=[
                    emitter(
                        spurious_lines=[
                            {
                                "frequency_mhz": 1575.0,
                                "level_dbc": -20.0,
                                "mechanism": MECHANISM_PASSIVE_INTERMODULATION,
                            }
                        ]
                    )
                ]
            )
        )
        self.assertEqual(len(report["excluded"]), 1)
        self.assertTrue(report["compliant"])

    def test_the_required_margin_can_be_tightened_per_system(self):
        report = assess_rf_compatibility(
            system(isolation_db=130.0, required_margin_db=60.0)
        )
        self.assertFalse(report["compliant"])

    def test_a_non_mapping_system_raises(self):
        with self.assertRaises(ValueError):
            assess_rf_compatibility([emitter()])


if __name__ == "__main__":
    unittest.main()
