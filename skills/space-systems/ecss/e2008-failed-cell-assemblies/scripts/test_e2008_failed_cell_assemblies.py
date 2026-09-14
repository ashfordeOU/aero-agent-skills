#!/usr/bin/env python3
"""Contract test for failed solar cell assemblies (offline).

Walks the clause workflow step by step: the mode catalogue split by
basis, the limit overrides and their refusals, the three per-mode
statuses including the refusal to read silence as a clean result, the
boolean/measurement basis mismatch refusals, the inclusive limit edges,
the one-mode-condemns rule and its short circuit past unexamined modes,
and the lot tally. This is the gate 3 review evidence for the leaf.
"""

import unittest

from e2008_failed_cell_assemblies_logic import (
    ASSEMBLY_FAILED,
    ASSEMBLY_NOT_EVALUATED,
    ASSEMBLY_SOUND,
    DEFAULT_FAILURE_LIMITS,
    FAILURE_MODES,
    LOT_CLEAR,
    LOT_HOLDS_FAILED_ASSEMBLIES,
    LOT_NOT_EVALUATED,
    MODE_ABSENT,
    MODE_MEASURED,
    MODE_NOT_EXAMINED,
    MODE_OBSERVED,
    MODE_PRESENT,
    assess_cell_assembly,
    assess_failure_mode,
    assess_inspection_lot,
    failure_mode_catalogue,
    measured_modes,
    normalize_mode,
    observed_modes,
    resolve_failure_limits,
)


def _clean_observations(**overrides):
    """Every listed mode examined and coming out absent, then overridden."""
    record = {}
    for mode in observed_modes():
        record[mode] = False
    record["adhesive-delamination-area"] = 0.0
    record["power-output-degradation"] = 0.0
    record["insulation-resistance-loss"] = 1.0e10
    record.update(overrides)
    return record


class CatalogueTests(unittest.TestCase):
    def test_catalogue_splits_cleanly_into_the_two_bases(self):
        catalogue = failure_mode_catalogue()
        self.assertEqual(
            len(catalogue), len(observed_modes()) + len(measured_modes())
        )
        self.assertGreaterEqual(len(catalogue), 5)

    def test_every_measured_mode_names_a_declared_limit(self):
        for mode in measured_modes():
            self.assertIn(FAILURE_MODES[mode]["limit"], DEFAULT_FAILURE_LIMITS)
            self.assertIn(FAILURE_MODES[mode]["direction"], ("above", "below"))

    def test_every_observed_mode_names_no_limit(self):
        for mode in observed_modes():
            self.assertIsNone(FAILURE_MODES[mode]["limit"])
            self.assertEqual(FAILURE_MODES[mode]["basis"], MODE_OBSERVED)

    def test_mode_name_is_normalized(self):
        self.assertEqual(normalize_mode("  Cell-Fracture "), "cell-fracture")

    def test_unlisted_mode_rejected(self):
        with self.assertRaises(ValueError):
            normalize_mode("paint-scuff")

    def test_non_string_mode_rejected(self):
        with self.assertRaises(ValueError):
            normalize_mode(7)


class LimitTests(unittest.TestCase):
    def test_defaults_are_returned_when_nothing_is_overridden(self):
        self.assertEqual(resolve_failure_limits(), dict(DEFAULT_FAILURE_LIMITS))

    def test_override_replaces_only_the_named_limit(self):
        resolved = resolve_failure_limits({"power_loss_fraction": 0.01})
        self.assertAlmostEqual(resolved["power_loss_fraction"], 0.01, places=9)
        self.assertAlmostEqual(
            resolved["insulation_resistance_ohm"],
            DEFAULT_FAILURE_LIMITS["insulation_resistance_ohm"],
            places=9,
        )

    def test_unrecognized_limit_rejected(self):
        with self.assertRaises(ValueError):
            resolve_failure_limits({"paint_thickness_um": 3.0})

    def test_non_positive_limit_rejected(self):
        with self.assertRaises(ValueError):
            resolve_failure_limits({"power_loss_fraction": 0.0})

    def test_fraction_limit_above_one_rejected(self):
        with self.assertRaises(ValueError):
            resolve_failure_limits({"delamination_area_fraction": 1.5})

    def test_non_mapping_limits_rejected(self):
        with self.assertRaises(ValueError):
            resolve_failure_limits([("power_loss_fraction", 0.01)])


class ModeStatusTests(unittest.TestCase):
    def test_observed_mode_found_is_present(self):
        record = assess_failure_mode("cell-fracture", True)
        self.assertEqual(record["status"], MODE_PRESENT)
        self.assertTrue(record["findings"])

    def test_observed_mode_not_found_is_absent(self):
        record = assess_failure_mode("cell-fracture", False)
        self.assertEqual(record["status"], MODE_ABSENT)
        self.assertEqual(record["findings"], [])

    def test_unexamined_mode_is_not_absent(self):
        record = assess_failure_mode("cell-fracture", None)
        self.assertEqual(record["status"], MODE_NOT_EXAMINED)
        self.assertNotEqual(record["status"], MODE_ABSENT)
        self.assertTrue(record["findings"])

    def test_measurement_handed_to_an_observed_mode_rejected(self):
        with self.assertRaises(ValueError):
            assess_failure_mode("cell-fracture", 0.3)

    def test_boolean_handed_to_a_measured_mode_rejected(self):
        with self.assertRaises(ValueError):
            assess_failure_mode("power-output-degradation", True)

    def test_negative_measurement_rejected(self):
        with self.assertRaises(ValueError):
            assess_failure_mode("power-output-degradation", -0.01)

    def test_rising_mode_above_its_limit_is_present(self):
        record = assess_failure_mode("power-output-degradation", 0.05)
        self.assertEqual(record["status"], MODE_PRESENT)
        self.assertAlmostEqual(record["measurement"], 0.05, places=9)
        self.assertEqual(record["basis"], MODE_MEASURED)

    def test_rising_mode_exactly_on_its_limit_is_absent(self):
        limit = DEFAULT_FAILURE_LIMITS["power_loss_fraction"]
        record = assess_failure_mode("power-output-degradation", limit)
        self.assertEqual(record["status"], MODE_ABSENT)
        self.assertAlmostEqual(record["limit"], limit, places=9)

    def test_falling_mode_below_its_limit_is_present(self):
        record = assess_failure_mode("insulation-resistance-loss", 1.0e6)
        self.assertEqual(record["status"], MODE_PRESENT)

    def test_falling_mode_exactly_on_its_limit_is_absent(self):
        limit = DEFAULT_FAILURE_LIMITS["insulation_resistance_ohm"]
        record = assess_failure_mode("insulation-resistance-loss", limit)
        self.assertEqual(record["status"], MODE_ABSENT)

    def test_tightened_limit_turns_an_absent_mode_present(self):
        record = assess_failure_mode(
            "power-output-degradation", 0.015, {"power_loss_fraction": 0.01}
        )
        self.assertEqual(record["status"], MODE_PRESENT)


class AssemblyVerdictTests(unittest.TestCase):
    def test_fully_examined_clean_assembly_is_sound(self):
        result = assess_cell_assembly(
            {"assembly_id": "SCA-001", "observations": _clean_observations()}
        )
        self.assertEqual(result["verdict"], ASSEMBLY_SOUND)
        self.assertFalse(result["failed"])
        self.assertEqual(result["present_modes"], ())

    def test_one_observed_mode_condemns_the_assembly(self):
        result = assess_cell_assembly(
            {
                "assembly_id": "SCA-002",
                "observations": _clean_observations(**{"cell-fracture": True}),
            }
        )
        self.assertEqual(result["verdict"], ASSEMBLY_FAILED)
        self.assertTrue(result["failed"])
        self.assertEqual(result["present_modes"], ("cell-fracture",))

    def test_one_measured_mode_condemns_the_assembly(self):
        result = assess_cell_assembly(
            {
                "assembly_id": "SCA-003",
                "observations": _clean_observations(
                    **{"insulation-resistance-loss": 1.0e5}
                ),
            }
        )
        self.assertEqual(result["verdict"], ASSEMBLY_FAILED)
        self.assertIn("insulation-resistance-loss", result["present_modes"])

    def test_a_present_mode_decides_even_with_modes_unexamined(self):
        observations = _clean_observations(**{"coverglass-fracture": True})
        del observations["power-output-degradation"]
        result = assess_cell_assembly(
            {"assembly_id": "SCA-004", "observations": observations}
        )
        self.assertEqual(result["verdict"], ASSEMBLY_FAILED)
        self.assertEqual(result["unexamined_modes"], ("power-output-degradation",))

    def test_clean_assembly_with_an_unexamined_mode_is_not_sound(self):
        observations = _clean_observations()
        del observations["solder-joint-separation"]
        result = assess_cell_assembly(
            {"assembly_id": "SCA-005", "observations": observations}
        )
        self.assertEqual(result["verdict"], ASSEMBLY_NOT_EVALUATED)
        self.assertIsNone(result["failed"])

    def test_several_present_modes_are_all_reported(self):
        result = assess_cell_assembly(
            {
                "assembly_id": "SCA-006",
                "observations": _clean_observations(
                    **{
                        "cell-fracture": True,
                        "solder-joint-separation": True,
                        "adhesive-delamination-area": 0.4,
                    }
                ),
            }
        )
        self.assertEqual(len(result["present_modes"]), 3)
        self.assertEqual(result["verdict"], ASSEMBLY_FAILED)

    def test_every_catalogue_mode_gets_a_record(self):
        result = assess_cell_assembly(
            {"assembly_id": "SCA-007", "observations": _clean_observations()}
        )
        self.assertEqual(len(result["modes"]), len(failure_mode_catalogue()))

    def test_empty_observation_set_leaves_the_assembly_unevaluated(self):
        result = assess_cell_assembly(
            {"assembly_id": "SCA-008", "observations": {}}
        )
        self.assertEqual(result["verdict"], ASSEMBLY_NOT_EVALUATED)
        self.assertEqual(
            len(result["unexamined_modes"]), len(failure_mode_catalogue())
        )

    def test_blank_assembly_id_rejected(self):
        with self.assertRaises(ValueError):
            assess_cell_assembly(
                {"assembly_id": "   ", "observations": _clean_observations()}
            )

    def test_missing_observations_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_cell_assembly({"assembly_id": "SCA-009"})

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_cell_assembly("the assembly looked fine")

    def test_repeated_mode_with_different_spelling_rejected(self):
        observations = _clean_observations()
        observations["Cell-Fracture"] = True
        with self.assertRaises(ValueError):
            assess_cell_assembly(
                {"assembly_id": "SCA-010", "observations": observations}
            )


class LotTallyTests(unittest.TestCase):
    def _lot(self, *assemblies, **extra):
        spec = {"lot_id": "LOT-77", "assemblies": list(assemblies)}
        spec.update(extra)
        return spec

    def test_clean_lot_is_clear(self):
        result = assess_inspection_lot(
            self._lot(
                {"assembly_id": "A", "observations": _clean_observations()},
                {"assembly_id": "B", "observations": _clean_observations()},
            )
        )
        self.assertEqual(result["verdict"], LOT_CLEAR)
        self.assertEqual(result["failed_assembly_ids"], ())
        self.assertAlmostEqual(result["failed_fraction"], 0.0, places=9)

    def test_one_failed_assembly_marks_the_lot(self):
        result = assess_inspection_lot(
            self._lot(
                {"assembly_id": "A", "observations": _clean_observations()},
                {
                    "assembly_id": "B",
                    "observations": _clean_observations(**{"cell-fracture": True}),
                },
            )
        )
        self.assertEqual(result["verdict"], LOT_HOLDS_FAILED_ASSEMBLIES)
        self.assertEqual(result["failed_assembly_ids"], ("B",))
        self.assertAlmostEqual(result["failed_fraction"], 0.5, places=9)

    def test_unexamined_unit_leaves_a_clean_lot_unevaluated(self):
        observations = _clean_observations()
        del observations["cell-fracture"]
        result = assess_inspection_lot(
            self._lot(
                {"assembly_id": "A", "observations": _clean_observations()},
                {"assembly_id": "B", "observations": observations},
            )
        )
        self.assertEqual(result["verdict"], LOT_NOT_EVALUATED)
        self.assertEqual(result["unevaluated_assembly_ids"], ("B",))
        self.assertEqual(result["settled_count"], 1)

    def test_lot_limits_reach_every_assembly_that_declares_none(self):
        result = assess_inspection_lot(
            self._lot(
                {
                    "assembly_id": "A",
                    "observations": _clean_observations(
                        **{"power-output-degradation": 0.015}
                    ),
                },
                limits={"power_loss_fraction": 0.01},
            )
        )
        self.assertEqual(result["verdict"], LOT_HOLDS_FAILED_ASSEMBLIES)

    def test_assembly_limits_override_the_lot_limits(self):
        result = assess_inspection_lot(
            self._lot(
                {
                    "assembly_id": "A",
                    "observations": _clean_observations(
                        **{"power-output-degradation": 0.015}
                    ),
                    "limits": {"power_loss_fraction": 0.03},
                },
                limits={"power_loss_fraction": 0.01},
            )
        )
        self.assertEqual(result["verdict"], LOT_CLEAR)

    def test_repeated_assembly_id_rejected(self):
        with self.assertRaises(ValueError):
            assess_inspection_lot(
                self._lot(
                    {"assembly_id": "A", "observations": _clean_observations()},
                    {"assembly_id": "A", "observations": _clean_observations()},
                )
            )

    def test_empty_lot_rejected(self):
        with self.assertRaises(ValueError):
            assess_inspection_lot(self._lot())

    def test_findings_name_the_failed_units(self):
        result = assess_inspection_lot(
            self._lot(
                {
                    "assembly_id": "A",
                    "observations": _clean_observations(**{"cell-fracture": True}),
                }
            )
        )
        self.assertTrue(any("A" in item for item in result["findings"]))


if __name__ == "__main__":
    unittest.main()
