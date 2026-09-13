#!/usr/bin/env python3
"""Gate 3 contract test for e20-rf-power-handling-general-requirements.

Offline, deterministic, stdlib unittest. Run:
    python3 test_e20_rf_power_handling_general_requirements.py
"""

import math
import unittest

import e20_rf_power_handling_general_requirements_logic as logic


def element(**overrides):
    """A compliant baseline chain element, overridable field by field."""
    base = {
        "id": "WG-01",
        "insertion_loss_db": 0.0,
        "capability_w": 400.0,
        "rating_basis": "vacuum-substantiated",
        "pressurization": "vented",
        "limitation": "voltage-breakdown",
    }
    base.update(overrides)
    return base


class TestUnitHelpers(unittest.TestCase):
    def test_one_watt_is_thirty_dbm(self):
        self.assertAlmostEqual(logic.watt_to_dbm(1.0), 30.0, places=9)

    def test_dbm_round_trip(self):
        self.assertAlmostEqual(logic.dbm_to_watt(logic.watt_to_dbm(2.5)), 2.5, places=9)

    def test_three_db_is_about_two(self):
        self.assertAlmostEqual(logic.db_to_ratio(3.0102999566398121), 2.0, places=9)

    def test_ratio_to_db_round_trip(self):
        self.assertAlmostEqual(logic.ratio_to_db(logic.db_to_ratio(7.5)), 7.5, places=9)

    def test_zero_watts_raises(self):
        with self.assertRaises(ValueError):
            logic.watt_to_dbm(0.0)

    def test_negative_watts_raises(self):
        with self.assertRaises(ValueError):
            logic.watt_to_dbm(-5.0)

    def test_boolean_power_raises(self):
        with self.assertRaises(ValueError):
            logic.watt_to_dbm(True)

    def test_non_numeric_decibels_raise(self):
        with self.assertRaises(ValueError):
            logic.db_to_ratio("3 dB")

    def test_ratio_to_db_rejects_zero(self):
        with self.assertRaises(ValueError):
            logic.ratio_to_db(0.0)


class TestCarrierSet(unittest.TestCase):
    def test_single_carrier_peak_equals_average(self):
        average, peak = logic.carrier_set_levels([50.0])
        self.assertAlmostEqual(average, 50.0, places=9)
        self.assertAlmostEqual(peak, 50.0, places=9)

    def test_four_equal_carriers_peak_is_four_times_average(self):
        average, peak = logic.carrier_set_levels([25.0] * 4)
        self.assertAlmostEqual(average, 100.0, places=9)
        self.assertAlmostEqual(peak, 400.0, places=9)

    def test_unequal_carriers_use_voltage_addition(self):
        average, peak = logic.carrier_set_levels([9.0, 1.0])
        self.assertAlmostEqual(average, 10.0, places=9)
        self.assertAlmostEqual(peak, 16.0, places=9)

    def test_peak_to_average_ratio_of_eight_carriers(self):
        ratio_db = logic.peak_to_average_ratio_db([10.0] * 8)
        self.assertAlmostEqual(ratio_db, 10.0 * math.log10(8.0), places=9)

    def test_empty_carrier_set_raises(self):
        with self.assertRaises(ValueError):
            logic.carrier_set_levels([])

    def test_non_list_carrier_set_raises(self):
        with self.assertRaises(ValueError):
            logic.carrier_set_levels(100.0)

    def test_zero_power_carrier_raises(self):
        with self.assertRaises(ValueError):
            logic.carrier_set_levels([10.0, 0.0])

    def test_negative_power_carrier_raises(self):
        with self.assertRaises(ValueError):
            logic.carrier_set_levels([-10.0])


class TestNormalization(unittest.TestCase):
    def test_rating_basis_alias(self):
        self.assertEqual(logic.normalize_rating_basis("VACUUM"), "vacuum-substantiated")

    def test_pressurization_alias(self):
        self.assertEqual(logic.normalize_pressurization("sealed"), "hermetically-sealed")

    def test_limitation_alias(self):
        self.assertEqual(logic.normalize_limitation("breakdown"), "voltage-breakdown")

    def test_unknown_rating_basis_raises(self):
        with self.assertRaises(ValueError):
            logic.normalize_rating_basis("guessed")

    def test_unknown_limitation_raises(self):
        with self.assertRaises(ValueError):
            logic.normalize_limitation("mechanical")

    def test_empty_token_raises(self):
        with self.assertRaises(ValueError):
            logic.normalize_pressurization("  ")

    def test_non_string_token_raises(self):
        with self.assertRaises(ValueError):
            logic.normalize_limitation(3)


class TestDerating(unittest.TestCase):
    def test_vacuum_basis_is_not_derated(self):
        self.assertAlmostEqual(
            logic.vacuum_derating_factor("vacuum-substantiated", "vented"), 1.0, places=12
        )

    def test_ambient_basis_vented_is_derated(self):
        self.assertAlmostEqual(
            logic.vacuum_derating_factor("ambient-air", "vented"),
            logic.AMBIENT_AIR_VACUUM_DERATING,
            places=12,
        )

    def test_ambient_basis_sealed_keeps_capability(self):
        self.assertAlmostEqual(
            logic.vacuum_derating_factor("ambient-air", "hermetically-sealed"),
            1.0,
            places=12,
        )

    def test_unsubstantiated_basis_raises(self):
        with self.assertRaises(ValueError):
            logic.vacuum_derating_factor("unsubstantiated", "vented")

    def test_effective_capability_applies_the_factor(self):
        value = logic.effective_capability_w(
            element(capability_w=200.0, rating_basis="ambient-air", pressurization="vented")
        )
        self.assertAlmostEqual(value, 100.0, places=9)

    def test_effective_capability_rejects_zero_capability(self):
        with self.assertRaises(ValueError):
            logic.effective_capability_w(element(capability_w=0.0))


class TestElementValidation(unittest.TestCase):
    def test_valid_element_normalizes(self):
        item = logic.validate_element(element(id=" WG-01 ", limitation="peak"))
        self.assertEqual(item["id"], "WG-01")
        self.assertEqual(item["limitation"], "voltage-breakdown")

    def test_missing_identifier_raises(self):
        with self.assertRaises(ValueError):
            logic.validate_element(element(id=""))

    def test_non_mapping_element_raises(self):
        with self.assertRaises(ValueError):
            logic.validate_element(["WG-01"])

    def test_negative_insertion_loss_raises(self):
        with self.assertRaises(ValueError):
            logic.validate_element(element(insertion_loss_db=-1.0))

    def test_non_numeric_insertion_loss_raises(self):
        with self.assertRaises(ValueError):
            logic.validate_element(element(insertion_loss_db="0.5 dB"))

    def test_pressurization_defaults_to_vented(self):
        item = dict(element())
        item.pop("pressurization")
        self.assertEqual(logic.validate_element(item)["pressurization"], "vented")


class TestPropagation(unittest.TestCase):
    def test_levels_fall_through_the_chain(self):
        chain = [
            logic.validate_element(element(id="A", insertion_loss_db=3.0)),
            logic.validate_element(element(id="B", insertion_loss_db=3.0)),
            logic.validate_element(element(id="C")),
        ]
        incident = logic.propagate_chain_levels(100.0, 400.0, chain)
        self.assertAlmostEqual(incident[0][0], 100.0, places=9)
        self.assertAlmostEqual(incident[1][0], 100.0 * 10 ** (-0.3), places=9)
        self.assertAlmostEqual(incident[2][0], 100.0 * 10 ** (-0.6), places=9)

    def test_peak_and_average_attenuate_together(self):
        chain = [logic.validate_element(element(id="A", insertion_loss_db=10.0))]
        incident = logic.propagate_chain_levels(100.0, 800.0, chain)
        self.assertAlmostEqual(incident[0][1] / incident[0][0], 8.0, places=9)

    def test_zero_drive_level_raises(self):
        with self.assertRaises(ValueError):
            logic.propagate_chain_levels(0.0, 10.0, [])

    def test_peak_below_average_raises(self):
        with self.assertRaises(ValueError):
            logic.propagate_chain_levels(100.0, 50.0, [])

    def test_within_capability_accepts_exact_equality(self):
        self.assertTrue(logic.within_capability(10.0, 10.0))

    def test_within_capability_absorbs_summation_representation_error(self):
        stress = 0.1 + 0.2  # a sum of carrier powers, one unit in the last place over
        self.assertGreater(stress, 0.3)
        self.assertTrue(logic.within_capability(stress, 0.3))

    def test_within_capability_still_rejects_a_real_exceedance(self):
        self.assertFalse(logic.within_capability(10.1, 10.0))


class TestElementAssessment(unittest.TestCase):
    def test_breakdown_element_is_assessed_on_the_peak_envelope(self):
        result = logic.assess_element(
            logic.validate_element(element(limitation="voltage-breakdown")), 100.0, 400.0
        )
        self.assertAlmostEqual(result["stress_w"], 400.0, places=9)
        self.assertTrue(result["compliant"])

    def test_thermal_element_is_assessed_on_the_average(self):
        result = logic.assess_element(
            logic.validate_element(element(limitation="thermal")), 100.0, 400.0
        )
        self.assertAlmostEqual(result["stress_w"], 100.0, places=9)

    def test_exceedance_is_flagged(self):
        result = logic.assess_element(
            logic.validate_element(element(capability_w=300.0)), 100.0, 400.0
        )
        self.assertFalse(result["compliant"])
        self.assertTrue(
            any(
                f.startswith("level-exceeds-effective-capability")
                for f in result["findings"]
            )
        )

    def test_capability_ratio_is_reported_in_decibels(self):
        result = logic.assess_element(
            logic.validate_element(element(capability_w=800.0, limitation="thermal")),
            100.0,
            400.0,
        )
        self.assertAlmostEqual(result["capability_ratio_db"], 9.0308998699194354, places=9)

    def test_unsubstantiated_basis_yields_no_capability_and_a_finding(self):
        result = logic.assess_element(
            logic.validate_element(element(rating_basis="unsubstantiated")), 10.0, 10.0
        )
        self.assertIsNone(result["effective_capability_w"])
        self.assertTrue(
            any(
                f.startswith("capability-basis-unsubstantiated")
                for f in result["findings"]
            )
        )

    def test_vented_ambient_capability_is_flagged_and_derated(self):
        result = logic.assess_element(
            logic.validate_element(
                element(capability_w=400.0, rating_basis="ambient-air")
            ),
            100.0,
            300.0,
        )
        self.assertAlmostEqual(result["effective_capability_w"], 200.0, places=9)
        self.assertTrue(
            any(
                f.startswith("ambient-air-capability-vented-to-vacuum")
                for f in result["findings"]
            )
        )
        self.assertTrue(
            any(
                f.startswith("level-exceeds-effective-capability")
                for f in result["findings"]
            )
        )

    def test_sealed_ambient_capability_without_leak_evidence_is_flagged(self):
        result = logic.assess_element(
            logic.validate_element(
                element(rating_basis="ambient-air", pressurization="hermetically-sealed")
            ),
            100.0,
            200.0,
        )
        self.assertTrue(
            any(
                f.startswith("hermetic-capability-without-leak-evidence")
                for f in result["findings"]
            )
        )

    def test_sealed_ambient_capability_with_leak_evidence_passes(self):
        result = logic.assess_element(
            logic.validate_element(
                element(
                    rating_basis="ambient-air",
                    pressurization="hermetically-sealed",
                    seal_evidence="LEAK-0044",
                )
            ),
            100.0,
            200.0,
        )
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["effective_capability_w"], 400.0, places=9)


class TestChainAssessment(unittest.TestCase):
    def _chain(self):
        return [
            element(id="SW-01", insertion_loss_db=0.2, capability_w=2000.0),
            element(
                id="FLT-01",
                insertion_loss_db=0.5,
                capability_w=2000.0,
                limitation="voltage-breakdown",
            ),
            element(
                id="LOAD-01",
                insertion_loss_db=0.0,
                capability_w=400.0,
                limitation="thermal",
            ),
        ]

    def test_healthy_chain_is_compliant(self):
        report = logic.assess_chain_power_handling([100.0] * 4, self._chain())
        self.assertTrue(report["compliant"])
        self.assertEqual(report["finding_total"], 0)
        self.assertAlmostEqual(report["average_drive_w"], 400.0, places=9)
        self.assertAlmostEqual(report["peak_envelope_drive_w"], 1600.0, places=9)

    def test_multi_carrier_peak_overloads_a_breakdown_element(self):
        chain = self._chain()
        chain[1]["capability_w"] = 900.0
        report = logic.assess_chain_power_handling([100.0] * 4, chain)
        self.assertFalse(report["compliant"])
        self.assertEqual(report["worst_element_id"], "FLT-01")

    def test_same_average_on_one_carrier_is_compliant(self):
        chain = self._chain()
        chain[1]["capability_w"] = 900.0
        report = logic.assess_chain_power_handling([400.0], chain)
        self.assertTrue(report["compliant"])

    def test_peak_to_average_is_reported(self):
        report = logic.assess_chain_power_handling([50.0] * 2, self._chain())
        self.assertAlmostEqual(report["peak_to_average_db"], 10.0 * math.log10(2.0), places=9)

    def test_total_insertion_loss_is_summed(self):
        report = logic.assess_chain_power_handling([100.0], self._chain())
        self.assertAlmostEqual(report["total_insertion_loss_db"], 0.7, places=9)

    def test_worst_element_is_the_tightest_ratio(self):
        report = logic.assess_chain_power_handling([100.0], self._chain())
        self.assertEqual(report["worst_element_id"], "LOAD-01")
        self.assertAlmostEqual(
            report["worst_capability_ratio_db"],
            10.0 * math.log10(400.0 / (100.0 * 10.0 ** (-0.07))),
            places=9,
        )

    def test_duplicate_element_identifier_raises(self):
        chain = self._chain()
        chain[2]["id"] = "SW-01"
        with self.assertRaises(ValueError):
            logic.assess_chain_power_handling([100.0], chain)

    def test_empty_chain_raises(self):
        with self.assertRaises(ValueError):
            logic.assess_chain_power_handling([100.0], [])

    def test_non_list_chain_raises(self):
        with self.assertRaises(ValueError):
            logic.assess_chain_power_handling([100.0], element())

    def test_chain_with_unsubstantiated_element_has_no_ratio_for_it(self):
        chain = self._chain()
        chain[0]["rating_basis"] = "unsubstantiated"
        report = logic.assess_chain_power_handling([100.0], chain)
        self.assertIsNone(report["results"][0]["capability_ratio_db"])
        self.assertFalse(report["compliant"])
        self.assertEqual(report["worst_element_id"], "LOAD-01")

    def test_exactly_loaded_thermal_element_stays_compliant(self):
        chain = [
            element(
                id="LOAD-02",
                insertion_loss_db=0.0,
                capability_w=0.3,
                limitation="thermal",
            )
        ]
        report = logic.assess_chain_power_handling([0.1, 0.2], chain)
        self.assertGreater(report["average_drive_w"], 0.3)
        self.assertTrue(report["compliant"])

    def test_attenuation_ahead_of_an_element_relieves_it(self):
        chain = [
            element(id="ATT-01", insertion_loss_db=10.0, capability_w=5000.0),
            element(id="FEED-01", insertion_loss_db=0.0, capability_w=110.0),
        ]
        report = logic.assess_chain_power_handling([1000.0], chain)
        self.assertTrue(report["compliant"])
        self.assertAlmostEqual(report["results"][1]["stress_w"], 100.0, places=6)


if __name__ == "__main__":
    unittest.main()
