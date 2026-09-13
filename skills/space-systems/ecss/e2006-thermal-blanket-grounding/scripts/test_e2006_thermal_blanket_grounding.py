#!/usr/bin/env python3
"""Gate 3 contract test for e2006-thermal-blanket-grounding."""

import unittest

from e2006_thermal_blanket_grounding_logic import (
    DEFAULT_MAX_GROUND_PATH_RESISTANCE_OHM,
    FINDING_BLANKET_REDUNDANCY,
    FINDING_CHAINED,
    FINDING_NO_STRAP,
    FINDING_RESISTANCE,
    FINDING_STRAP_COUNT,
    FINDING_UNGROUNDED,
    GROUND_REFERENCE,
    assess_blanket_set,
    evaluate_blanket,
    format_grounding_report,
    layer_ground_resistance,
    normalize_blanket,
    normalize_layer,
    parallel_resistance,
    required_strap_count,
    resolve_ground_path,
)


def strap(strap_id="strap-1", resistance_ohm=0.5):
    return {"strap_id": strap_id, "resistance_ohm": resistance_ohm}


def two_straps(prefix, resistance_ohm=0.5):
    return [
        strap("%s-a" % prefix, resistance_ohm),
        strap("%s-b" % prefix, resistance_ohm),
    ]


def layer(layer_id="layer-1", metallized=True, ground_target=GROUND_REFERENCE,
          straps=None, lateral_resistance_ohm=0.0):
    return {
        "layer_id": layer_id,
        "metallized": metallized,
        "ground_target": ground_target,
        "straps": two_straps(layer_id) if straps is None else straps,
        "lateral_resistance_ohm": lateral_resistance_ohm,
    }


def blanket(blanket_id="mli-1", area_m2=1.0, layers=None):
    return {
        "blanket_id": blanket_id,
        "area_m2": area_m2,
        "layers": [layer("layer-1"), layer("layer-2")] if layers is None else layers,
    }


def layers_index(records):
    return {item["layer_id"]: item for item in (normalize_layer(r) for r in records)}


class ParallelResistanceTests(unittest.TestCase):
    def test_two_equal_straps_halve_the_resistance(self):
        self.assertAlmostEqual(parallel_resistance([0.5, 0.5]), 0.25, places=12)

    def test_three_equal_straps_land_on_the_limit(self):
        self.assertAlmostEqual(parallel_resistance([3.0, 3.0, 3.0]), 1.0, places=12)

    def test_unequal_straps_are_dominated_by_the_best_one(self):
        self.assertLess(parallel_resistance([0.1, 10.0]), 0.1)

    def test_empty_strap_list_rejected(self):
        with self.assertRaises(ValueError):
            parallel_resistance([])

    def test_non_sequence_rejected(self):
        with self.assertRaises(ValueError):
            parallel_resistance(0.5)

    def test_zero_resistance_rejected(self):
        with self.assertRaises(ValueError):
            parallel_resistance([0.5, 0.0])

    def test_negative_resistance_rejected(self):
        with self.assertRaises(ValueError):
            parallel_resistance([-0.5])


class LayerResistanceTests(unittest.TestCase):
    def test_layer_without_strap_has_no_bond_point(self):
        value = layer_ground_resistance(normalize_layer(layer(straps=[])))
        self.assertEqual(value, float("inf"))

    def test_straps_combine_in_parallel(self):
        value = layer_ground_resistance(normalize_layer(layer()))
        self.assertAlmostEqual(value, 0.25, places=12)

    def test_lateral_resistance_adds_in_series(self):
        value = layer_ground_resistance(
            normalize_layer(layer(lateral_resistance_ohm=0.4))
        )
        self.assertAlmostEqual(value, 0.65, places=12)


class StrapCountTests(unittest.TestCase):
    def test_small_blanket_still_needs_the_redundancy_minimum(self):
        self.assertEqual(required_strap_count(0.5), 2)

    def test_large_blanket_scales_with_area(self):
        self.assertEqual(required_strap_count(10.0), 5)

    def test_exact_area_multiple_is_not_rounded_up(self):
        self.assertEqual(required_strap_count(4.0), 2)

    def test_area_just_above_a_multiple_adds_a_strap(self):
        self.assertEqual(required_strap_count(4.1), 3)

    def test_zero_area_rejected(self):
        with self.assertRaises(ValueError):
            required_strap_count(0.0)

    def test_zero_area_per_strap_rejected(self):
        with self.assertRaises(ValueError):
            required_strap_count(4.0, area_per_strap_m2=0.0)

    def test_minimum_below_one_rejected(self):
        with self.assertRaises(ValueError):
            required_strap_count(4.0, minimum=0)

    def test_boolean_minimum_rejected(self):
        with self.assertRaises(ValueError):
            required_strap_count(4.0, minimum=True)


class GroundPathTests(unittest.TestCase):
    def test_direct_path_reaches_structure_in_one_hop(self):
        index = layers_index([layer("layer-1")])
        out = resolve_ground_path("layer-1", index)
        self.assertEqual(out["terminal"], GROUND_REFERENCE)
        self.assertEqual(out["hops"], 1)
        self.assertEqual(out["path"], ["layer-1", GROUND_REFERENCE])

    def test_chained_path_takes_two_hops(self):
        index = layers_index(
            [layer("layer-1"), layer("layer-2", ground_target="layer-1")]
        )
        out = resolve_ground_path("layer-2", index)
        self.assertEqual(out["hops"], 2)
        self.assertEqual(out["path"], ["layer-2", "layer-1", GROUND_REFERENCE])

    def test_layer_without_target_dead_ends(self):
        index = layers_index([layer("layer-1", ground_target=None)])
        out = resolve_ground_path("layer-1", index)
        self.assertIsNone(out["terminal"])
        self.assertEqual(out["hops"], 0)

    def test_unknown_target_rejected(self):
        index = layers_index([layer("layer-1", ground_target="layer-9")])
        with self.assertRaises(ValueError):
            resolve_ground_path("layer-1", index)

    def test_self_referencing_target_rejected(self):
        index = layers_index([layer("layer-1", ground_target="layer-1")])
        with self.assertRaises(ValueError):
            resolve_ground_path("layer-1", index)

    def test_two_layer_loop_rejected(self):
        index = layers_index(
            [
                layer("layer-1", ground_target="layer-2"),
                layer("layer-2", ground_target="layer-1"),
            ]
        )
        with self.assertRaises(ValueError):
            resolve_ground_path("layer-1", index)

    def test_unknown_start_layer_rejected(self):
        index = layers_index([layer("layer-1")])
        with self.assertRaises(ValueError):
            resolve_ground_path("layer-7", index)


class NormalizeLayerTests(unittest.TestCase):
    def test_valid_layer_is_normalized(self):
        out = normalize_layer(layer(" layer-3 "))
        self.assertEqual(out["layer_id"], "layer-3")
        self.assertEqual(len(out["straps"]), 2)

    def test_non_mapping_layer_rejected(self):
        with self.assertRaises(ValueError):
            normalize_layer(["layer-1"])

    def test_blank_identifier_rejected(self):
        with self.assertRaises(ValueError):
            normalize_layer(layer(""))

    def test_identifier_shadowing_structure_rejected(self):
        with self.assertRaises(ValueError):
            normalize_layer(layer(GROUND_REFERENCE))

    def test_non_boolean_metallized_flag_rejected(self):
        with self.assertRaises(ValueError):
            normalize_layer(layer(metallized="yes"))

    def test_non_string_ground_target_rejected(self):
        with self.assertRaises(ValueError):
            normalize_layer(layer(ground_target=7))

    def test_straps_must_be_a_list(self):
        with self.assertRaises(ValueError):
            normalize_layer(layer(straps=strap()))

    def test_strap_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            normalize_layer(layer(straps=["strap-1"]))

    def test_duplicate_strap_identifier_rejected(self):
        with self.assertRaises(ValueError):
            normalize_layer(layer(straps=[strap("s"), strap("s")]))

    def test_non_positive_strap_resistance_rejected(self):
        with self.assertRaises(ValueError):
            normalize_layer(layer(straps=[strap("s", 0.0)]))

    def test_negative_lateral_resistance_rejected(self):
        with self.assertRaises(ValueError):
            normalize_layer(layer(lateral_resistance_ohm=-0.1))


class NormalizeBlanketTests(unittest.TestCase):
    def test_valid_blanket_is_normalized(self):
        out = normalize_blanket(blanket())
        self.assertEqual(out["blanket_id"], "mli-1")
        self.assertEqual(len(out["layers"]), 2)

    def test_non_mapping_blanket_rejected(self):
        with self.assertRaises(ValueError):
            normalize_blanket("mli-1")

    def test_missing_layer_list_rejected(self):
        record = blanket()
        del record["layers"]
        with self.assertRaises(ValueError):
            normalize_blanket(record)

    def test_empty_layer_list_rejected(self):
        with self.assertRaises(ValueError):
            normalize_blanket(blanket(layers=[]))

    def test_duplicate_layer_identifier_rejected(self):
        with self.assertRaises(ValueError):
            normalize_blanket(blanket(layers=[layer("layer-1"), layer("layer-1")]))

    def test_non_positive_area_rejected(self):
        with self.assertRaises(ValueError):
            normalize_blanket(blanket(area_m2=0.0))


class BlanketEvaluationTests(unittest.TestCase):
    def test_directly_strapped_blanket_is_compliant(self):
        out = evaluate_blanket(blanket())
        self.assertTrue(out["compliant"])
        self.assertEqual(out["open_findings"], [])
        self.assertEqual(out["direct_strap_count"], 4)

    def test_chained_layer_is_flagged(self):
        out = evaluate_blanket(
            blanket(
                layers=[layer("layer-1"), layer("layer-2", ground_target="layer-1")]
            )
        )
        self.assertIn(("layer-2", FINDING_CHAINED), out["open_findings"])
        self.assertFalse(out["compliant"])

    def test_chained_path_accumulates_resistance(self):
        out = evaluate_blanket(
            blanket(
                layers=[layer("layer-1"), layer("layer-2", ground_target="layer-1")]
            )
        )
        chained = [r for r in out["layer_results"] if r["layer_id"] == "layer-2"][0]
        self.assertAlmostEqual(chained["path_resistance_ohm"], 0.5, places=12)

    def test_ungrounded_metallic_layer_is_flagged(self):
        out = evaluate_blanket(
            blanket(
                layers=[
                    layer("layer-1"),
                    layer("layer-2", ground_target=None, straps=[]),
                ]
            )
        )
        self.assertIn(("layer-2", FINDING_UNGROUNDED), out["open_findings"])

    def test_non_metallic_layer_is_out_of_scope(self):
        out = evaluate_blanket(
            blanket(
                layers=[
                    layer("layer-1"),
                    layer("layer-2", metallized=False, ground_target=None, straps=[]),
                ]
            )
        )
        outer = [r for r in out["layer_results"] if r["layer_id"] == "layer-2"][0]
        self.assertFalse(outer["applicable"])
        self.assertEqual(outer["findings"], [])
        self.assertTrue(out["compliant"])

    def test_declared_path_without_strap_is_flagged(self):
        out = evaluate_blanket(
            blanket(layers=[layer("layer-1"), layer("layer-2", straps=[])])
        )
        findings = [
            r for r in out["layer_results"] if r["layer_id"] == "layer-2"
        ][0]["findings"]
        self.assertIn(FINDING_NO_STRAP, findings)
        self.assertIn(FINDING_RESISTANCE, findings)

    def test_strap_count_below_the_area_requirement_is_flagged(self):
        out = evaluate_blanket(blanket(area_m2=10.0))
        self.assertIn(("layer-1", FINDING_STRAP_COUNT), out["open_findings"])
        first = out["layer_results"][0]
        self.assertEqual(first["required_strap_count"], 5)

    def test_resistance_above_the_bonding_limit_is_flagged(self):
        out = evaluate_blanket(
            blanket(layers=[layer("layer-1", straps=two_straps("layer-1", 3.0))])
        )
        self.assertIn(("layer-1", FINDING_RESISTANCE), out["open_findings"])

    def test_resistance_exactly_on_the_limit_is_compliant(self):
        three = [
            strap("layer-1-a", 3.0),
            strap("layer-1-b", 3.0),
            strap("layer-1-c", 3.0),
        ]
        out = evaluate_blanket(blanket(layers=[layer("layer-1", straps=three)]))
        first = out["layer_results"][0]
        self.assertAlmostEqual(
            first["path_resistance_ohm"],
            DEFAULT_MAX_GROUND_PATH_RESISTANCE_OHM,
            places=12,
        )
        self.assertEqual(first["findings"], [])
        self.assertTrue(out["compliant"])

    def test_lateral_resistance_can_break_the_limit(self):
        out = evaluate_blanket(
            blanket(layers=[layer("layer-1", lateral_resistance_ohm=0.9)])
        )
        self.assertIn(("layer-1", FINDING_RESISTANCE), out["open_findings"])

    def test_single_direct_strap_loses_blanket_redundancy(self):
        out = evaluate_blanket(
            blanket(layers=[layer("layer-1", straps=[strap("layer-1-a", 0.5)])])
        )
        self.assertIn(FINDING_BLANKET_REDUNDANCY, out["blanket_findings"])
        self.assertIn(("layer-1", FINDING_STRAP_COUNT), out["open_findings"])
        self.assertFalse(out["compliant"])

    def test_all_layers_chained_to_one_bonded_layer_keeps_redundancy_count(self):
        out = evaluate_blanket(
            blanket(
                layers=[
                    layer("layer-1"),
                    layer("layer-2", ground_target="layer-1"),
                    layer("layer-3", ground_target="layer-2"),
                ]
            )
        )
        self.assertEqual(out["direct_strap_count"], 2)
        self.assertEqual(out["blanket_findings"], [])
        self.assertEqual(len(out["open_findings"]), 2)

    def test_custom_resistance_limit_changes_the_verdict(self):
        out = evaluate_blanket(blanket(), max_resistance_ohm=0.1)
        self.assertIn(("layer-1", FINDING_RESISTANCE), out["open_findings"])

    def test_anchor_clause_is_reported(self):
        self.assertEqual(evaluate_blanket(blanket())["anchor"], "ECSS-E-ST-20-06C 6.3.3.3")

    def test_looped_topology_propagates_value_error(self):
        with self.assertRaises(ValueError):
            evaluate_blanket(
                blanket(
                    layers=[
                        layer("layer-1", ground_target="layer-2"),
                        layer("layer-2", ground_target="layer-1"),
                    ]
                )
            )


class BlanketSetTests(unittest.TestCase):
    def test_blanket_set_is_aggregated(self):
        out = assess_blanket_set(
            [
                blanket("mli-1"),
                blanket("mli-2", layers=[layer("layer-1", straps=[])]),
            ]
        )
        self.assertEqual(out["compliant_count"], 1)
        self.assertEqual(out["non_compliant"], ["mli-2"])
        self.assertFalse(out["compliant"])

    def test_all_compliant_blanket_set(self):
        out = assess_blanket_set([blanket("mli-1"), blanket("mli-2")])
        self.assertTrue(out["compliant"])

    def test_duplicate_blanket_identifier_rejected(self):
        with self.assertRaises(ValueError):
            assess_blanket_set([blanket("mli-1"), blanket("mli-1")])

    def test_empty_blanket_set_rejected(self):
        with self.assertRaises(ValueError):
            assess_blanket_set([])

    def test_non_sequence_blanket_set_rejected(self):
        with self.assertRaises(ValueError):
            assess_blanket_set(blanket())


class ReportTests(unittest.TestCase):
    def test_report_lists_blankets_and_findings(self):
        assessment = assess_blanket_set(
            [
                blanket("mli-1"),
                blanket("mli-2", layers=[layer("layer-1", straps=[strap("a", 0.5)])]),
            ]
        )
        text = format_grounding_report(assessment)
        self.assertIn("mli-1 area=1 m2", text)
        self.assertIn("layer-1: %s" % FINDING_STRAP_COUNT, text)
        self.assertIn("blanket: %s" % FINDING_BLANKET_REDUNDANCY, text)
        self.assertIn("compliant=false", text)

    def test_report_rejects_foreign_input(self):
        with self.assertRaises(ValueError):
            format_grounding_report({"blankets_missing": True})


if __name__ == "__main__":
    unittest.main()
