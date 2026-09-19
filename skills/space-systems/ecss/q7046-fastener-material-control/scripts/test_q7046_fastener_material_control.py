"""Contract test for the fastener material-control leaf (stdlib unittest)."""

import unittest

from q7046_fastener_material_control_logic import (
    ACCEPTED,
    ACCEPTED_WITH_CONTROLS,
    EMBRITTLEMENT_THRESHOLD_MPA,
    HIGH_RESISTANCE,
    LOW_RESISTANCE,
    MODERATE_RESISTANCE,
    REJECTED,
    SUSTAINED_STRESS_FRACTION,
    alloy_record,
    assess_declaration,
    assess_material_schedule,
    assess_sustained_stress,
    embrittlement_susceptible,
    galvanic_couple,
    scc_category,
    sustained_stress_limit_mpa,
    temperature_coverage,
    validate_declaration,
)


def declaration(**kw):
    record = {
        "alloy": "a286-precipitation-hardened",
        "part_number": "fs-0001",
        "heat_number": "h-88421",
        "yield_mpa": 660.0,
        "uts_mpa": 900.0,
        "sustained_stress_mpa": 0.0,
        "structure_alloy": "stainless-316-austenitic",
        "environment": "general-indoor",
        "mission_min_c": -50.0,
        "mission_max_c": 80.0,
        "electrolytic_finish": False,
        "relief_bake_declared": False,
    }
    record.update(kw)
    return record


class TestAlloyTable(unittest.TestCase):
    def test_an_admitted_alloy_returns_its_record(self):
        data = alloy_record("inconel-718")
        self.assertEqual(data["scc"], HIGH_RESISTANCE)
        self.assertAlmostEqual(data["min_uts_mpa"], 1240.0, places=9)

    def test_an_unknown_alloy_raises(self):
        with self.assertRaises(ValueError):
            alloy_record("unobtainium-grade-3")

    def test_a_non_string_alloy_raises(self):
        with self.assertRaises(ValueError):
            alloy_record(17)

    def test_the_table_returns_a_copy_the_caller_cannot_corrupt(self):
        first = alloy_record("inconel-718")
        first["scc"] = LOW_RESISTANCE
        self.assertEqual(scc_category("inconel-718"), HIGH_RESISTANCE)

    def test_the_two_seven_zero_seven_five_tempers_differ_in_category(self):
        self.assertEqual(scc_category("aluminium-7075-t73"), HIGH_RESISTANCE)
        self.assertEqual(scc_category("aluminium-7075-t6"), LOW_RESISTANCE)


class TestSustainedStress(unittest.TestCase):
    def test_a_high_resistance_alloy_runs_to_the_design_fraction(self):
        limit = sustained_stress_limit_mpa("a286-precipitation-hardened", 800.0)
        self.assertAlmostEqual(limit, 600.0, places=9)

    def test_a_moderate_resistance_alloy_is_held_to_half_yield(self):
        limit = sustained_stress_limit_mpa("stainless-17-4ph-h1150", 800.0)
        self.assertAlmostEqual(limit, 400.0, places=9)

    def test_a_low_resistance_alloy_takes_no_sustained_tension(self):
        limit = sustained_stress_limit_mpa("stainless-410-martensitic", 800.0)
        self.assertAlmostEqual(limit, 0.0, places=9)

    def test_a_stress_exactly_on_the_limit_stays_compliant(self):
        yield_mpa = 800.0
        applied = SUSTAINED_STRESS_FRACTION[HIGH_RESISTANCE] * yield_mpa
        result = assess_sustained_stress(
            "a286-precipitation-hardened", applied, yield_mpa
        )
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["margin_mpa"], 0.0, places=9)

    def test_a_stress_above_the_limit_is_not_compliant(self):
        result = assess_sustained_stress(
            "a286-precipitation-hardened", 700.0, 800.0
        )
        self.assertFalse(result["compliant"])

    def test_a_negative_applied_stress_raises(self):
        with self.assertRaises(ValueError):
            assess_sustained_stress("inconel-718", -5.0, 800.0)


class TestGalvanicCouple(unittest.TestCase):
    def test_a_like_for_like_couple_has_no_difference(self):
        couple = galvanic_couple(
            "stainless-316-austenitic", "stainless-316-austenitic", "coastal-launch-site"
        )
        self.assertAlmostEqual(couple["difference_v"], 0.0, places=9)
        self.assertTrue(couple["admissible"])

    def test_a_couple_exactly_on_the_limit_is_admissible(self):
        couple = galvanic_couple(
            "low-alloy-steel-4340", "aluminium-7075-t73", "general-indoor"
        )
        self.assertAlmostEqual(couple["difference_v"], 0.25, places=9)
        self.assertTrue(couple["admissible"])

    def test_the_same_couple_fails_the_wetter_environment(self):
        couple = galvanic_couple(
            "low-alloy-steel-4340", "aluminium-7075-t73", "coastal-launch-site"
        )
        self.assertFalse(couple["admissible"])

    def test_the_more_anodic_member_is_named(self):
        couple = galvanic_couple(
            "inconel-718", "magnesium-az31", "controlled-cleanroom"
        )
        self.assertEqual(couple["anodic_member"], "magnesium-az31")
        self.assertFalse(couple["admissible"])

    def test_an_unknown_structure_alloy_raises(self):
        with self.assertRaises(ValueError):
            galvanic_couple("inconel-718", "papier-mache", "general-indoor")

    def test_an_unknown_environment_raises(self):
        with self.assertRaises(ValueError):
            galvanic_couple("inconel-718", "aluminium-6061-t6", "swamp")


class TestEmbrittlement(unittest.TestCase):
    def test_a_high_strength_alloy_is_susceptible(self):
        self.assertTrue(embrittlement_susceptible("low-alloy-steel-4340"))

    def test_a_moderate_strength_alloy_is_not(self):
        self.assertFalse(embrittlement_susceptible("stainless-316-austenitic"))

    def test_a_declaration_exactly_on_the_threshold_is_susceptible(self):
        self.assertTrue(
            embrittlement_susceptible(
                "stainless-316-austenitic", EMBRITTLEMENT_THRESHOLD_MPA
            )
        )

    def test_a_declared_strength_overrides_the_table_minimum(self):
        self.assertFalse(embrittlement_susceptible("inconel-718", 850.0))


class TestTemperatureCoverage(unittest.TestCase):
    def test_a_mission_inside_the_band_is_covered(self):
        coverage = temperature_coverage("titanium-6al-4v", -100.0, 200.0)
        self.assertTrue(coverage["covered"])

    def test_a_mission_exactly_on_the_hot_end_is_covered(self):
        coverage = temperature_coverage("titanium-6al-4v", -100.0, 315.0)
        self.assertTrue(coverage["hot_end_covered"])

    def test_an_uncharacterized_cold_end_is_reported_on_its_own(self):
        coverage = temperature_coverage("low-alloy-steel-4340", -180.0, 100.0)
        self.assertFalse(coverage["cold_end_covered"])
        self.assertTrue(coverage["hot_end_covered"])

    def test_an_inverted_mission_band_raises(self):
        with self.assertRaises(ValueError):
            temperature_coverage("inconel-718", 200.0, -40.0)


class TestValidateDeclaration(unittest.TestCase):
    def test_a_well_formed_declaration_normalizes(self):
        norm = validate_declaration(declaration())
        self.assertEqual(norm["heat_number"], "h-88421")
        self.assertAlmostEqual(norm["yield_mpa"], 660.0, places=9)

    def test_a_non_mapping_raises(self):
        with self.assertRaises(ValueError):
            validate_declaration(["a286-precipitation-hardened"])

    def test_a_missing_heat_number_raises(self):
        with self.assertRaises(ValueError):
            validate_declaration(declaration(heat_number="   "))

    def test_a_missing_part_number_raises(self):
        with self.assertRaises(ValueError):
            validate_declaration(declaration(part_number=""))

    def test_a_strength_below_yield_raises(self):
        with self.assertRaises(ValueError):
            validate_declaration(declaration(uts_mpa=400.0))

    def test_a_zero_yield_raises(self):
        with self.assertRaises(ValueError):
            validate_declaration(declaration(yield_mpa=0.0))


class TestAssessDeclaration(unittest.TestCase):
    def test_a_clean_declaration_is_accepted(self):
        result = assess_declaration(declaration())
        self.assertEqual(result["disposition"], ACCEPTED)
        self.assertEqual(result["findings"], [])

    def test_a_moderate_alloy_is_accepted_with_a_written_control(self):
        result = assess_declaration(
            declaration(
                alloy="stainless-17-4ph-h1150",
                yield_mpa=1000.0,
                uts_mpa=1070.0,
                sustained_stress_mpa=300.0,
                mission_min_c=-40.0,
                mission_max_c=120.0,
            )
        )
        self.assertEqual(result["disposition"], ACCEPTED_WITH_CONTROLS)
        self.assertIn("hold-sustained-stress-below-half-yield", result["controls"])

    def test_a_low_resistance_alloy_under_sustained_tension_is_rejected(self):
        result = assess_declaration(
            declaration(
                alloy="aluminium-7075-t6",
                yield_mpa=460.0,
                uts_mpa=525.0,
                sustained_stress_mpa=50.0,
                structure_alloy="aluminium-6061-t6",
                mission_min_c=-50.0,
                mission_max_c=80.0,
            )
        )
        self.assertEqual(result["disposition"], REJECTED)
        self.assertIn(
            "low-resistance-alloy-under-sustained-tension", result["findings"]
        )

    def test_the_same_alloy_unloaded_is_not_rejected_for_stress_corrosion(self):
        result = assess_declaration(
            declaration(
                alloy="aluminium-7075-t6",
                yield_mpa=460.0,
                uts_mpa=525.0,
                sustained_stress_mpa=0.0,
                structure_alloy="aluminium-6061-t6",
                mission_min_c=-50.0,
                mission_max_c=80.0,
            )
        )
        self.assertNotIn(
            "low-resistance-alloy-under-sustained-tension", result["findings"]
        )

    def test_an_electrolytic_finish_without_a_bake_is_rejected(self):
        result = assess_declaration(
            declaration(
                alloy="inconel-718",
                yield_mpa=1030.0,
                uts_mpa=1240.0,
                electrolytic_finish=True,
                relief_bake_declared=False,
            )
        )
        self.assertEqual(result["disposition"], REJECTED)
        self.assertIn("electrolytic-finish-without-a-relief-bake", result["findings"])

    def test_the_same_finish_with_a_bake_carries_a_control_instead(self):
        result = assess_declaration(
            declaration(
                alloy="inconel-718",
                yield_mpa=1030.0,
                uts_mpa=1240.0,
                electrolytic_finish=True,
                relief_bake_declared=True,
            )
        )
        self.assertEqual(result["disposition"], ACCEPTED_WITH_CONTROLS)
        self.assertIn(
            "constrain-the-finish-route-for-embrittlement", result["controls"]
        )

    def test_a_cold_mission_end_outside_the_band_is_rejected(self):
        result = assess_declaration(
            declaration(
                alloy="stainless-17-4ph-h1150",
                yield_mpa=1000.0,
                uts_mpa=1070.0,
                mission_min_c=-180.0,
                mission_max_c=80.0,
            )
        )
        self.assertEqual(result["disposition"], REJECTED)
        self.assertIn("mission-cold-end-outside-the-alloy-band", result["findings"])

    def test_a_bad_couple_is_rejected_even_with_a_sound_alloy(self):
        result = assess_declaration(
            declaration(
                alloy="inconel-718",
                yield_mpa=1030.0,
                uts_mpa=1240.0,
                structure_alloy="magnesium-az31",
                environment="coastal-launch-site",
                relief_bake_declared=True,
            )
        )
        self.assertEqual(result["disposition"], REJECTED)
        self.assertIn(
            "galvanic-couple-above-the-environment-limit", result["findings"]
        )


class TestAssessMaterialSchedule(unittest.TestCase):
    def test_a_clean_schedule_is_accepted(self):
        report = assess_material_schedule(
            [declaration(), declaration(part_number="fs-0002", heat_number="h-9")]
        )
        self.assertEqual(report["build_disposition"], ACCEPTED)
        self.assertEqual(report["rejected_parts"], [])

    def test_the_worst_declaration_sets_the_build_disposition(self):
        report = assess_material_schedule(
            [
                declaration(),
                declaration(
                    part_number="fs-0003",
                    heat_number="h-10",
                    alloy="aluminium-7075-t6",
                    yield_mpa=460.0,
                    uts_mpa=525.0,
                    sustained_stress_mpa=40.0,
                    structure_alloy="aluminium-6061-t6",
                ),
            ]
        )
        self.assertEqual(report["build_disposition"], REJECTED)
        self.assertEqual(report["rejected_parts"], ["fs-0003"])

    def test_controlled_parts_are_listed_separately(self):
        report = assess_material_schedule(
            [
                declaration(),
                declaration(
                    part_number="fs-0004",
                    heat_number="h-11",
                    alloy="stainless-17-4ph-h1150",
                    yield_mpa=1000.0,
                    uts_mpa=1070.0,
                    sustained_stress_mpa=200.0,
                    mission_min_c=-40.0,
                    mission_max_c=120.0,
                ),
            ]
        )
        self.assertEqual(report["controlled_parts"], ["fs-0004"])

    def test_a_repeated_part_and_heat_raises(self):
        with self.assertRaises(ValueError):
            assess_material_schedule([declaration(), declaration()])

    def test_an_empty_schedule_raises(self):
        with self.assertRaises(ValueError):
            assess_material_schedule([])


if __name__ == "__main__":
    unittest.main()
