#!/usr/bin/env python3
"""Gate 3 contract test for the clause 7.4.5 passive-intermodulation logic."""

import math
import unittest

from e20_passive_intermodulation_qualification_logic import (
    DEFAULT_QUALIFICATION_MARGIN_DB,
    assess_passive_intermodulation_qualification,
    band_containing,
    evaluate_product,
    intermodulation_products,
    normalize_band,
    normalize_carrier,
    normalize_carrier_plan,
    normalize_reference,
    predict_product_level_dbm,
    qualification_envelope,
)

CARRIERS = [
    {"id": "tx-a", "frequency_hz": 1.0e9, "power_dbm": 40.0},
    {"id": "tx-b", "frequency_hz": 1.1e9, "power_dbm": 40.0},
]

REFERENCE = {"carrier_power_dbm": 40.0, "pim_dbm": -100.0, "order": 3}

RX_BAND = {
    "id": "rx-main",
    "kind": "own-receive",
    "low_hz": 0.85e9,
    "high_hz": 0.95e9,
    "limit_dbm": -110.0,
    "isolation_db": 0.0,
}


def _plan(**overrides):
    plan = {
        "carriers": [dict(c) for c in CARRIERS],
        "bands": [dict(RX_BAND)],
        "reference": dict(REFERENCE),
        "max_order": 5,
    }
    plan.update(overrides)
    return plan


class TestCarrierNormalization(unittest.TestCase):
    def test_carrier_happy_path(self):
        out = normalize_carrier({"id": " tx-a ", "frequency_hz": 1.0e9, "power_dbm": 40})
        self.assertEqual(out["id"], "tx-a")
        self.assertAlmostEqual(out["frequency_hz"], 1.0e9)
        self.assertAlmostEqual(out["power_dbm"], 40.0)

    def test_carrier_rejects_non_mapping(self):
        with self.assertRaises(ValueError):
            normalize_carrier(["tx-a", 1.0e9])

    def test_carrier_rejects_blank_id(self):
        with self.assertRaises(ValueError):
            normalize_carrier({"id": "   ", "frequency_hz": 1.0e9, "power_dbm": 40.0})

    def test_carrier_rejects_non_positive_frequency(self):
        with self.assertRaises(ValueError):
            normalize_carrier({"id": "tx-a", "frequency_hz": 0.0, "power_dbm": 40.0})

    def test_carrier_rejects_non_finite_level(self):
        with self.assertRaises(ValueError):
            normalize_carrier(
                {"id": "tx-a", "frequency_hz": 1.0e9, "power_dbm": float("inf")}
            )

    def test_carrier_rejects_boolean_level(self):
        with self.assertRaises(ValueError):
            normalize_carrier({"id": "tx-a", "frequency_hz": 1.0e9, "power_dbm": True})

    def test_plan_happy_path(self):
        plan = normalize_carrier_plan(CARRIERS)
        self.assertEqual([c["id"] for c in plan], ["tx-a", "tx-b"])

    def test_plan_rejects_single_carrier(self):
        with self.assertRaises(ValueError):
            normalize_carrier_plan([dict(CARRIERS[0])])

    def test_plan_rejects_duplicate_identifier(self):
        clash = [dict(CARRIERS[0]), dict(CARRIERS[1], id="tx-a")]
        with self.assertRaises(ValueError):
            normalize_carrier_plan(clash)

    def test_plan_rejects_non_list(self):
        with self.assertRaises(ValueError):
            normalize_carrier_plan({"id": "tx-a"})

    def test_plan_rejects_oversized_plan(self):
        many = [
            {"id": "tx-%d" % i, "frequency_hz": 1.0e9 + i * 1.0e6, "power_dbm": 40.0}
            for i in range(9)
        ]
        with self.assertRaises(ValueError):
            normalize_carrier_plan(many)


class TestBandAndReference(unittest.TestCase):
    def test_band_happy_path_defaults_isolation(self):
        band = normalize_band(
            {
                "id": "coord-1",
                "kind": "third-party-protected",
                "low_hz": 2.0e9,
                "high_hz": 2.1e9,
                "limit_dbm": -120.0,
            }
        )
        self.assertAlmostEqual(band["isolation_db"], 0.0)
        self.assertEqual(band["kind"], "third-party-protected")

    def test_band_rejects_unknown_kind(self):
        with self.assertRaises(ValueError):
            normalize_band(dict(RX_BAND, kind="transmit"))

    def test_band_rejects_inverted_edges(self):
        with self.assertRaises(ValueError):
            normalize_band(dict(RX_BAND, low_hz=1.0e9, high_hz=0.9e9))

    def test_band_rejects_negative_isolation(self):
        with self.assertRaises(ValueError):
            normalize_band(dict(RX_BAND, isolation_db=-1.0))

    def test_band_rejects_blank_identifier(self):
        with self.assertRaises(ValueError):
            normalize_band(dict(RX_BAND, id=""))

    def test_reference_defaults(self):
        ref = normalize_reference(dict(REFERENCE))
        self.assertEqual(ref["order"], 3)
        self.assertAlmostEqual(ref["order_rolloff_db"], 8.0)

    def test_reference_rejects_even_order(self):
        with self.assertRaises(ValueError):
            normalize_reference(dict(REFERENCE, order=4))

    def test_reference_rejects_order_below_three(self):
        with self.assertRaises(ValueError):
            normalize_reference(dict(REFERENCE, order=1))

    def test_reference_rejects_float_order(self):
        with self.assertRaises(ValueError):
            normalize_reference(dict(REFERENCE, order=3.0))

    def test_reference_rejects_negative_rolloff(self):
        with self.assertRaises(ValueError):
            normalize_reference(dict(REFERENCE, order_rolloff_db=-2.0))


class TestProductEnumeration(unittest.TestCase):
    def test_third_order_lower_product_is_enumerated(self):
        products = intermodulation_products(CARRIERS, 3)
        freqs = [round(p["frequency_hz"]) for p in products]
        self.assertIn(round(2 * 1.0e9 - 1.1e9), freqs)

    def test_all_products_positive_and_odd_order(self):
        products = intermodulation_products(CARRIERS, 7)
        self.assertTrue(products)
        for product in products:
            self.assertGreater(product["frequency_hz"], 0.0)
            self.assertEqual(product["order"] % 2, 1)
            self.assertEqual(
                product["order"], sum(abs(m) for m in product["coefficients"])
            )

    def test_higher_max_order_enumerates_more(self):
        self.assertGreater(
            len(intermodulation_products(CARRIERS, 5)),
            len(intermodulation_products(CARRIERS, 3)),
        )

    def test_three_carrier_plan_raises_three_carrier_products(self):
        three = CARRIERS + [{"id": "tx-c", "frequency_hz": 1.25e9, "power_dbm": 38.0}]
        products = intermodulation_products(three, 3)
        mixed = [p for p in products if all(m != 0 for m in p["coefficients"])]
        self.assertTrue(mixed)

    def test_rejects_even_max_order_below_three(self):
        with self.assertRaises(ValueError):
            intermodulation_products(CARRIERS, 2)

    def test_rejects_max_order_above_cap(self):
        with self.assertRaises(ValueError):
            intermodulation_products(CARRIERS, 17)

    def test_rejects_non_integer_max_order(self):
        with self.assertRaises(ValueError):
            intermodulation_products(CARRIERS, 5.0)


class TestLevelPrediction(unittest.TestCase):
    def test_reference_conditions_return_reference_level(self):
        level = predict_product_level_dbm((2, -1), CARRIERS, REFERENCE)
        self.assertAlmostEqual(level, -100.0)

    def test_third_order_scales_three_db_per_db(self):
        hotter = [dict(c, power_dbm=41.0) for c in CARRIERS]
        level = predict_product_level_dbm((2, -1), hotter, REFERENCE)
        self.assertAlmostEqual(level, -97.0)

    def test_fifth_order_takes_the_order_rolloff(self):
        level = predict_product_level_dbm((3, -2), CARRIERS, REFERENCE)
        self.assertAlmostEqual(level, -116.0)

    def test_coefficient_length_must_match_plan(self):
        with self.assertRaises(ValueError):
            predict_product_level_dbm((2, -1, 0), CARRIERS, REFERENCE)

    def test_rejects_non_integer_coefficient(self):
        with self.assertRaises(ValueError):
            predict_product_level_dbm((2.0, -1), CARRIERS, REFERENCE)

    def test_rejects_order_below_reference_order(self):
        with self.assertRaises(ValueError):
            predict_product_level_dbm((2, -1), CARRIERS, dict(REFERENCE, order=5))


class TestBandMapping(unittest.TestCase):
    def test_lower_edge_is_inside_the_band(self):
        band = band_containing(0.85e9, [dict(RX_BAND)])
        self.assertIsNotNone(band)
        self.assertEqual(band["id"], "rx-main")

    def test_upper_edge_is_inside_the_band(self):
        band = band_containing(0.95e9, [dict(RX_BAND)])
        self.assertIsNotNone(band)

    def test_frequency_outside_every_band_returns_none(self):
        self.assertIsNone(band_containing(3.0e9, [dict(RX_BAND)]))

    def test_rejects_non_positive_frequency(self):
        with self.assertRaises(ValueError):
            band_containing(-1.0, [dict(RX_BAND)])

    def test_rejects_non_list_bands(self):
        with self.assertRaises(ValueError):
            band_containing(0.9e9, dict(RX_BAND))


class TestProductEvaluation(unittest.TestCase):
    def test_out_of_band_product_is_dropped(self):
        product = {"coefficients": (2, -1), "order": 3, "frequency_hz": 3.0e9}
        self.assertIsNone(evaluate_product(product, CARRIERS, [dict(RX_BAND)], REFERENCE))

    def test_isolation_reduces_the_arriving_level(self):
        product = {"coefficients": (2, -1), "order": 3, "frequency_hz": 0.9e9}
        band = dict(RX_BAND, isolation_db=20.0)
        finding = evaluate_product(product, CARRIERS, [band], REFERENCE)
        self.assertAlmostEqual(finding["generated_dbm"], -100.0)
        self.assertAlmostEqual(finding["arriving_dbm"], -120.0)
        self.assertAlmostEqual(finding["margin_db"], 10.0)
        self.assertTrue(finding["compliant"])

    def test_exceedance_is_reported_as_non_compliant(self):
        product = {"coefficients": (2, -1), "order": 3, "frequency_hz": 0.9e9}
        finding = evaluate_product(product, CARRIERS, [dict(RX_BAND)], REFERENCE)
        self.assertAlmostEqual(finding["margin_db"], -10.0)
        self.assertFalse(finding["compliant"])

    def test_exactly_met_limit_survives_representation_error(self):
        carriers = [
            {"id": "tx-a", "frequency_hz": 1.0e9, "power_dbm": 43.3},
            {"id": "tx-b", "frequency_hz": 1.1e9, "power_dbm": 46.7},
        ]
        generated = predict_product_level_dbm((2, -1), carriers, REFERENCE)
        band = dict(RX_BAND, limit_dbm=-86.7, isolation_db=0.0)
        product = {"coefficients": (2, -1), "order": 3, "frequency_hz": 0.9e9}
        finding = evaluate_product(product, carriers, [band], REFERENCE)
        self.assertAlmostEqual(finding["generated_dbm"], generated)
        self.assertAlmostEqual(finding["margin_db"], 0.0, places=9)
        self.assertTrue(finding["compliant"])


class TestQualificationEnvelope(unittest.TestCase):
    def test_envelope_raises_every_carrier_by_the_margin(self):
        env = qualification_envelope(CARRIERS, 3.0, 2.0)
        self.assertAlmostEqual(env["carriers"][0]["qualification_dbm"], 43.0)
        self.assertAlmostEqual(env["carriers"][1]["qualification_dbm"], 43.0)
        self.assertAlmostEqual(env["dwell_hours"], 2.0)

    def test_composite_level_of_two_equal_carriers(self):
        env = qualification_envelope(CARRIERS, 3.0, 1.0)
        self.assertAlmostEqual(
            env["composite_qualification_dbm"], 43.0 + 10.0 * math.log10(2.0), places=9
        )

    def test_zero_margin_is_allowed_but_flat(self):
        env = qualification_envelope(CARRIERS, 0.0, 1.0)
        self.assertAlmostEqual(env["carriers"][0]["qualification_dbm"], 40.0)

    def test_rejects_negative_margin(self):
        with self.assertRaises(ValueError):
            qualification_envelope(CARRIERS, -1.0, 1.0)

    def test_rejects_non_positive_dwell(self):
        with self.assertRaises(ValueError):
            qualification_envelope(CARRIERS, 3.0, 0.0)


class TestAssessment(unittest.TestCase):
    def test_compliant_carrier_plan(self):
        result = assess_passive_intermodulation_qualification(
            _plan(bands=[dict(RX_BAND, isolation_db=30.0)])
        )
        self.assertTrue(result["compliant"])
        self.assertEqual(result["violations"], [])
        self.assertGreater(result["in_band_count"], 0)

    def test_violating_carrier_plan(self):
        result = assess_passive_intermodulation_qualification(_plan())
        self.assertFalse(result["compliant"])
        self.assertTrue(result["violations"])
        self.assertLess(result["worst_margin_db"], 0.0)

    def test_worst_margin_is_the_minimum_margin(self):
        result = assess_passive_intermodulation_qualification(_plan())
        margins = [f["margin_db"] for f in result["findings"]]
        self.assertAlmostEqual(result["worst_margin_db"], min(margins))

    def test_missing_band_declaration_is_a_defect(self):
        result = assess_passive_intermodulation_qualification(_plan(bands=[]))
        self.assertFalse(result["compliant"])
        self.assertTrue(result["defects"])
        self.assertEqual(result["in_band_count"], 0)

    def test_default_qualification_margin_is_applied(self):
        result = assess_passive_intermodulation_qualification(_plan())
        self.assertAlmostEqual(
            result["qualification"]["margin_db"], DEFAULT_QUALIFICATION_MARGIN_DB
        )

    def test_rejects_non_mapping_plan(self):
        with self.assertRaises(ValueError):
            assess_passive_intermodulation_qualification([CARRIERS])

    def test_rejects_missing_band_list(self):
        broken = _plan()
        broken.pop("bands")
        with self.assertRaises(ValueError):
            assess_passive_intermodulation_qualification(broken)

    def test_rejects_non_mapping_qualification_block(self):
        with self.assertRaises(ValueError):
            assess_passive_intermodulation_qualification(_plan(qualification=[3.0]))

    def test_third_party_band_is_assessed_alongside_the_receive_band(self):
        coord = {
            "id": "coord-1",
            "kind": "third-party-protected",
            "low_hz": 0.88e9,
            "high_hz": 0.92e9,
            "limit_dbm": -130.0,
            "isolation_db": 0.0,
        }
        result = assess_passive_intermodulation_qualification(
            _plan(bands=[dict(RX_BAND), coord])
        )
        kinds = {f["band_kind"] for f in result["findings"]}
        self.assertIn("own-receive", kinds)


if __name__ == "__main__":
    unittest.main()
