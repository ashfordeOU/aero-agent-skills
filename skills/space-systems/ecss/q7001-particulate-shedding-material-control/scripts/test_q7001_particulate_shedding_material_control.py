"""Contract tests for the particulate-shedding material control logic."""

import unittest

from q7001_particulate_shedding_material_control_logic import (
    CLEANLINESS_LEVELS,
    CONTROL_CREDIT,
    ORIENTATION_CAPTURE,
    SHEDDING_FAMILIES,
    aggregate_contributions,
    assess_particulate_control,
    capture_factor,
    cleanliness_budget_pct,
    control_findings,
    mandatory_control,
    normalise_identifier,
    shedding_family,
    source_contribution_pct,
    validate_source,
)

VELCRO = {
    "name": "blanket-fastener-strip",
    "family": "hook-and-loop-fastener",
    "area_cm2": 40.0,
    "orientation": "upward-facing",
    "view_factor": 1.0,
}
PAINT = {
    "name": "radiator-backing-paint",
    "family": "sealed-paint",
    "area_cm2": 800.0,
    "orientation": "vertical",
    "view_factor": 0.4,
}
FOAM = {
    "name": "handling-cradle-foam",
    "family": "open-cell-foam",
    "area_cm2": 300.0,
    "orientation": "upward-facing",
    "view_factor": 0.6,
}


def _spec(**overrides):
    spec = {
        "sources": [dict(VELCRO), dict(PAINT)],
        "surface_area_cm2": 2000.0,
        "exposure_hours": 500.0,
        "cleanliness_level": "level-500",
    }
    spec.update(overrides)
    return spec


class NormaliseIdentifierTests(unittest.TestCase):
    def test_trims_and_lowercases(self):
        self.assertEqual(normalise_identifier(" Velcro-Strip ", "name"),
                         "velcro-strip")

    def test_non_string_rejected(self):
        with self.assertRaises(ValueError):
            normalise_identifier(None, "name")

    def test_blank_rejected(self):
        with self.assertRaises(ValueError):
            normalise_identifier("\t", "name")


class SheddingFamilyTests(unittest.TestCase):
    def test_known_family_returned(self):
        entry = shedding_family("Hook-And-Loop-Fastener")
        self.assertEqual(entry["family"], "hook-and-loop-fastener")
        self.assertGreater(entry["index_pac_per_1000h"], 0.0)

    def test_unknown_family_rejected(self):
        with self.assertRaises(ValueError):
            shedding_family("moon-dust")

    def test_fastener_sheds_more_than_polished_metal(self):
        self.assertGreater(
            shedding_family("hook-and-loop-fastener")["index_pac_per_1000h"],
            shedding_family("polished-metal")["index_pac_per_1000h"],
        )

    def test_sealing_a_paint_lowers_its_index(self):
        self.assertGreater(
            shedding_family("unsealed-paint")["index_pac_per_1000h"],
            shedding_family("sealed-paint")["index_pac_per_1000h"],
        )

    def test_every_family_index_is_positive(self):
        for name, entry in SHEDDING_FAMILIES.items():
            self.assertGreater(entry["index_pac_per_1000h"], 0.0, name)

    def test_benign_families_carry_no_mandatory_control(self):
        self.assertIsNone(mandatory_control("polished-metal"))

    def test_fastener_carries_a_mandatory_control(self):
        self.assertIsNotNone(mandatory_control("hook-and-loop-fastener"))


class CaptureFactorTests(unittest.TestCase):
    def test_upward_facing_full_view_collects_everything(self):
        self.assertAlmostEqual(capture_factor("upward-facing", 1.0), 1.0, places=9)

    def test_downward_facing_barely_collects(self):
        self.assertAlmostEqual(
            capture_factor("downward-facing", 1.0),
            ORIENTATION_CAPTURE["downward-facing"],
            places=9,
        )

    def test_view_factor_scales_linearly(self):
        self.assertAlmostEqual(capture_factor("vertical", 0.5),
                               ORIENTATION_CAPTURE["vertical"] * 0.5, places=9)

    def test_zero_view_factor_collects_nothing(self):
        self.assertAlmostEqual(capture_factor("upward-facing", 0.0), 0.0, places=9)

    def test_view_factor_above_unity_rejected(self):
        with self.assertRaises(ValueError):
            capture_factor("vertical", 1.2)

    def test_unknown_orientation_rejected(self):
        with self.assertRaises(ValueError):
            capture_factor("edge-on", 0.5)

    def test_negative_view_factor_rejected(self):
        with self.assertRaises(ValueError):
            capture_factor("vertical", -0.1)


class ValidateSourceTests(unittest.TestCase):
    def test_source_normalised(self):
        record = validate_source(dict(VELCRO))
        self.assertEqual(record["family"], "hook-and-loop-fastener")
        self.assertFalse(record["control_applied"])

    def test_missing_key_rejected(self):
        bad = dict(VELCRO)
        del bad["area_cm2"]
        with self.assertRaises(ValueError):
            validate_source(bad)

    def test_non_mapping_rejected(self):
        with self.assertRaises(ValueError):
            validate_source(["velcro"])

    def test_zero_area_rejected(self):
        bad = dict(VELCRO)
        bad["area_cm2"] = 0.0
        with self.assertRaises(ValueError):
            validate_source(bad)

    def test_boolean_area_rejected(self):
        bad = dict(VELCRO)
        bad["area_cm2"] = True
        with self.assertRaises(ValueError):
            validate_source(bad)


class ContributionTests(unittest.TestCase):
    def test_contribution_matches_the_closed_form(self):
        record = validate_source(dict(VELCRO))
        value = source_contribution_pct(record, 2000.0, 1000.0)
        expected = 0.90 * (40.0 / 2000.0) * 1.0 * 1.0
        self.assertAlmostEqual(value, expected, places=12)

    def test_contribution_scales_with_exposure(self):
        record = validate_source(dict(VELCRO))
        short = source_contribution_pct(record, 2000.0, 500.0)
        long_run = source_contribution_pct(record, 2000.0, 1000.0)
        self.assertAlmostEqual(long_run, short * 2.0, places=12)

    def test_zero_exposure_contributes_nothing(self):
        record = validate_source(dict(VELCRO))
        self.assertAlmostEqual(
            source_contribution_pct(record, 2000.0, 0.0), 0.0, places=12
        )

    def test_applied_control_earns_the_credit(self):
        bare = validate_source(dict(VELCRO))
        controlled = dict(VELCRO)
        controlled["control_applied"] = True
        credited = validate_source(controlled)
        self.assertAlmostEqual(
            source_contribution_pct(credited, 2000.0, 1000.0),
            source_contribution_pct(bare, 2000.0, 1000.0) * CONTROL_CREDIT,
            places=12,
        )

    def test_control_flag_on_a_benign_family_earns_nothing(self):
        controlled = dict(PAINT)
        controlled["control_applied"] = True
        credited = validate_source(controlled)
        bare = validate_source(dict(PAINT))
        self.assertAlmostEqual(
            source_contribution_pct(credited, 2000.0, 1000.0),
            source_contribution_pct(bare, 2000.0, 1000.0),
            places=12,
        )

    def test_zero_surface_area_rejected(self):
        record = validate_source(dict(VELCRO))
        with self.assertRaises(ValueError):
            source_contribution_pct(record, 0.0, 1000.0)

    def test_negative_exposure_rejected(self):
        record = validate_source(dict(VELCRO))
        with self.assertRaises(ValueError):
            source_contribution_pct(record, 2000.0, -10.0)


class BudgetTests(unittest.TestCase):
    def test_known_level_budget(self):
        self.assertAlmostEqual(
            cleanliness_budget_pct("Level-500"), CLEANLINESS_LEVELS["level-500"],
            places=12,
        )

    def test_tighter_level_has_a_smaller_budget(self):
        self.assertLess(
            cleanliness_budget_pct("level-100"), cleanliness_budget_pct("level-750")
        )

    def test_unknown_level_rejected(self):
        with self.assertRaises(ValueError):
            cleanliness_budget_pct("level-9000")


class ControlFindingTests(unittest.TestCase):
    def test_uncontrolled_source_in_view_is_reported(self):
        records = [validate_source(dict(VELCRO))]
        self.assertEqual(len(control_findings(records)), 1)

    def test_controlled_source_is_silent(self):
        controlled = dict(VELCRO)
        controlled["control_applied"] = True
        self.assertEqual(control_findings([validate_source(controlled)]), [])

    def test_out_of_sight_source_is_silent(self):
        hidden = dict(VELCRO)
        hidden["view_factor"] = 0.0
        self.assertEqual(control_findings([validate_source(hidden)]), [])

    def test_benign_family_is_silent(self):
        self.assertEqual(control_findings([validate_source(dict(PAINT))]), [])


class AggregateTests(unittest.TestCase):
    def test_total_is_the_sum_of_contributions(self):
        records = [validate_source(dict(VELCRO)), validate_source(dict(PAINT))]
        rolled = aggregate_contributions(records, 2000.0, 1000.0)
        self.assertAlmostEqual(
            rolled["total_pac_pct"],
            sum(c["contribution_pac_pct"] for c in rolled["contributions"]),
            places=12,
        )

    def test_contributions_are_ordered_worst_first(self):
        records = [validate_source(dict(PAINT)), validate_source(dict(VELCRO))]
        rolled = aggregate_contributions(records, 2000.0, 1000.0)
        self.assertEqual(rolled["contributions"][0]["name"], "blanket-fastener-strip")

    def test_empty_sequence_rejected(self):
        with self.assertRaises(ValueError):
            aggregate_contributions([], 2000.0, 1000.0)


class AssessParticulateControlTests(unittest.TestCase):
    def test_uncontrolled_fastener_owes_a_control(self):
        result = assess_particulate_control(_spec())
        self.assertEqual(result["verdict"], "controls-owed")
        self.assertEqual(result["dominant_source"], "blanket-fastener-strip")

    def test_controlled_installation_passes(self):
        controlled = dict(VELCRO)
        controlled["control_applied"] = True
        result = assess_particulate_control(
            _spec(sources=[controlled, dict(PAINT)])
        )
        self.assertEqual(result["verdict"], "installation-controlled")
        self.assertTrue(result["within_budget"])

    def test_tight_level_breaks_a_budget_a_loose_one_absorbs(self):
        controlled = dict(VELCRO)
        controlled["control_applied"] = True
        loose = assess_particulate_control(
            _spec(sources=[controlled], cleanliness_level="level-750",
                  exposure_hours=1000.0)
        )
        tight = assess_particulate_control(
            _spec(sources=[controlled], cleanliness_level="level-100",
                  exposure_hours=1000.0)
        )
        self.assertTrue(loose["within_budget"])
        self.assertFalse(tight["within_budget"])

    def test_margin_is_budget_less_total(self):
        result = assess_particulate_control(_spec())
        self.assertAlmostEqual(
            result["margin_pac_pct"],
            result["budget_pac_pct"] - result["total_pac_pct"],
            places=12,
        )

    def test_foam_out_of_sight_contributes_nothing(self):
        hidden = dict(FOAM)
        hidden["view_factor"] = 0.0
        result = assess_particulate_control(_spec(sources=[hidden]))
        self.assertAlmostEqual(result["total_pac_pct"], 0.0, places=12)
        self.assertEqual(result["verdict"], "installation-controlled")

    def test_duplicate_source_name_rejected(self):
        with self.assertRaises(ValueError):
            assess_particulate_control(_spec(sources=[dict(VELCRO), dict(VELCRO)]))

    def test_empty_source_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_particulate_control(_spec(sources=[]))

    def test_missing_spec_key_rejected(self):
        spec = _spec()
        del spec["cleanliness_level"]
        with self.assertRaises(ValueError):
            assess_particulate_control(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_particulate_control(["sources"])

    def test_budget_exceedance_is_named_in_the_findings(self):
        result = assess_particulate_control(
            _spec(cleanliness_level="level-100")
        )
        self.assertTrue(any("budget exceeded" in f for f in result["findings"]))


if __name__ == "__main__":
    unittest.main()
