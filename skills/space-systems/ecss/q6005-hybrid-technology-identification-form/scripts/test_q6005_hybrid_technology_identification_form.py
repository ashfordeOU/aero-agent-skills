"""Contract tests for the clause 6.2 identification-form application logic."""

import unittest

from q6005_hybrid_technology_identification_form_logic import (
    ACTIVITY_DEPENDENCIES,
    ASSESSMENT_AREAS,
    CONSTRUCTION_TECHNOLOGIES,
    FORM_SECTIONS,
    HERMETIC_PACKAGES,
    NON_HERMETIC_PACKAGES,
    READINESS_STATES,
    TECHNOLOGY_FAMILIES,
    absent_form_sections,
    activity_status,
    assess_form_application,
    coverage_percent,
    covered_assessment_areas,
    group_technologies_by_family,
    normalize_sections,
    normalize_technologies,
    normalize_token,
    relevant_assessment_areas,
    required_form_sections,
    sealing_category,
    uncovered_assessment_areas,
)

THICK_FILM_HYBRID = [
    "thick-film-substrate",
    "eutectic-die-attach",
    "gold-wire-bonding",
    "internal-active-die",
    "internal-passive-attachment",
    "seam-welded-package",
]


def full_spec(**overrides):
    base = {
        "declared_technologies": list(THICK_FILM_HYBRID),
        "form_submitted": True,
        "form_sections": list(required_form_sections(THICK_FILM_HYBRID)),
    }
    base.update(overrides)
    return base


class VocabularyTests(unittest.TestCase):
    def test_token_is_trimmed_and_lower_cased(self):
        self.assertEqual(
            normalize_token(" Gold-Wire-Bonding ", "construction technology"),
            "gold-wire-bonding",
        )

    def test_blank_token_rejected(self):
        with self.assertRaises(ValueError):
            normalize_token("   ", "construction technology")

    def test_non_string_token_rejected(self):
        with self.assertRaises(ValueError):
            normalize_token(17, "construction technology")

    def test_assessment_areas_are_derived_from_the_technology_map(self):
        derived = set()
        for areas in CONSTRUCTION_TECHNOLOGIES.values():
            derived.update(areas)
        self.assertEqual(set(ASSESSMENT_AREAS), derived)

    def test_every_form_section_area_is_a_known_assessment_area(self):
        for areas in FORM_SECTIONS.values():
            for area in areas:
                self.assertIn(area, ASSESSMENT_AREAS)

    def test_every_technology_belongs_to_exactly_one_family(self):
        for technology in CONSTRUCTION_TECHNOLOGIES:
            homes = [
                family
                for family, members in TECHNOLOGY_FAMILIES.items()
                if technology in members
            ]
            self.assertEqual(len(homes), 1, technology)

    def test_hermetic_and_non_hermetic_package_sets_are_disjoint(self):
        self.assertEqual(set(HERMETIC_PACKAGES) & set(NON_HERMETIC_PACKAGES), set())

    def test_readiness_state_vocabulary_is_closed(self):
        self.assertEqual(len(READINESS_STATES), 3)
        self.assertIn("assessment-may-start", READINESS_STATES)


class NormalisationTests(unittest.TestCase):
    def test_unknown_technology_rejected(self):
        with self.assertRaises(ValueError):
            normalize_technologies(["glass-frit-magic"])

    def test_empty_technology_declaration_rejected(self):
        with self.assertRaises(ValueError):
            normalize_technologies([])

    def test_a_bare_string_is_not_a_technology_sequence(self):
        with self.assertRaises(ValueError):
            normalize_technologies("gold-wire-bonding")

    def test_technologies_deduplicated_and_sorted(self):
        got = normalize_technologies(
            ["gold-wire-bonding", "Gold-Wire-Bonding", "eutectic-die-attach"]
        )
        self.assertEqual(got, ["eutectic-die-attach", "gold-wire-bonding"])

    def test_unknown_form_section_rejected(self):
        with self.assertRaises(ValueError):
            normalize_sections(["astrology-data"])

    def test_empty_section_list_is_allowed(self):
        self.assertEqual(normalize_sections([]), [])


class GroupingTests(unittest.TestCase):
    def test_declaration_is_grouped_by_construction_step(self):
        grouped = group_technologies_by_family(THICK_FILM_HYBRID)
        self.assertEqual(grouped["substrate"], ["thick-film-substrate"])
        self.assertEqual(grouped["packaging"], ["seam-welded-package"])

    def test_a_family_with_no_declared_member_is_reported_empty(self):
        grouped = group_technologies_by_family(["thick-film-substrate"])
        self.assertEqual(grouped["interconnection"], [])

    def test_grouping_covers_every_family(self):
        grouped = group_technologies_by_family(THICK_FILM_HYBRID)
        self.assertEqual(set(grouped), set(TECHNOLOGY_FAMILIES))


class AreaTests(unittest.TestCase):
    def test_thick_film_pulls_in_the_resistor_trim_area(self):
        areas = relevant_assessment_areas(["thick-film-substrate"])
        self.assertIn("resistor-trim-assessment", areas)

    def test_co_fired_substrate_does_not_pull_in_resistor_trim(self):
        areas = relevant_assessment_areas(["co-fired-ceramic-substrate"])
        self.assertNotIn("resistor-trim-assessment", areas)

    def test_adhesive_die_attach_pulls_in_outgassing(self):
        areas = relevant_assessment_areas(["adhesive-die-attach"])
        self.assertIn("outgassing-and-materials-assessment", areas)

    def test_covered_areas_come_from_the_submitted_sections_only(self):
        covered = covered_assessment_areas(["die-attach-data"])
        self.assertEqual(covered, ("die-attach-assessment",))

    def test_required_sections_follow_the_declared_technologies(self):
        owed = required_form_sections(["flip-chip-attach"])
        self.assertIn("materials-and-contamination-data", owed)
        self.assertIn("interconnection-data", owed)

    def test_absent_sections_are_the_owed_ones_not_submitted(self):
        absent = absent_form_sections(THICK_FILM_HYBRID, ["die-attach-data"])
        self.assertIn("substrate-and-conductor-data", absent)
        self.assertNotIn("die-attach-data", absent)

    def test_uncovered_areas_are_empty_for_a_complete_submission(self):
        owed = list(required_form_sections(THICK_FILM_HYBRID))
        self.assertEqual(uncovered_assessment_areas(THICK_FILM_HYBRID, owed), [])


class SealingTests(unittest.TestCase):
    def test_seam_welded_package_is_hermetic(self):
        self.assertEqual(sealing_category(["seam-welded-package"]), "hermetic")

    def test_polymer_sealed_package_is_non_hermetic(self):
        self.assertEqual(sealing_category(["polymer-sealed-package"]), "non-hermetic")

    def test_no_packaging_technology_leaves_sealing_underived(self):
        self.assertEqual(
            sealing_category(["thick-film-substrate"]), "sealing-not-declared"
        )

    def test_contradictory_packaging_declaration_rejected(self):
        with self.assertRaises(ValueError):
            sealing_category(["seam-welded-package", "polymer-sealed-package"])


class CoverageTests(unittest.TestCase):
    def test_complete_submission_is_one_hundred_percent(self):
        owed = list(required_form_sections(THICK_FILM_HYBRID))
        self.assertAlmostEqual(
            coverage_percent(THICK_FILM_HYBRID, owed), 100.0, places=9
        )

    def test_empty_submission_is_zero_percent(self):
        self.assertAlmostEqual(coverage_percent(THICK_FILM_HYBRID, []), 0.0, places=9)

    def test_partial_submission_lands_on_the_expected_fraction(self):
        technologies = ["co-fired-ceramic-substrate", "gold-wire-bonding"]
        got = coverage_percent(technologies, ["interconnection-data"])
        self.assertAlmostEqual(got, 50.0, places=9)


class ActivityTests(unittest.TestCase):
    def test_complete_submission_enables_the_technology_review(self):
        owed = list(required_form_sections(THICK_FILM_HYBRID))
        status = activity_status(THICK_FILM_HYBRID, owed)
        self.assertEqual(status["supplier-technology-review"], "enabled")

    def test_irrelevant_activity_is_not_applicable_rather_than_enabled(self):
        technologies = ["co-fired-ceramic-substrate", "gold-wire-bonding"]
        owed = list(required_form_sections(technologies))
        status = activity_status(technologies, owed)
        self.assertEqual(status["materials-and-contamination-review"], "not-applicable")

    def test_missing_section_blocks_only_the_activities_that_need_it(self):
        status = activity_status(THICK_FILM_HYBRID, ["internal-component-data"])
        self.assertEqual(status["internal-part-procurement-review"], "enabled")
        self.assertEqual(status["manufacturing-line-audit"], "blocked")

    def test_every_activity_gets_a_state(self):
        owed = list(required_form_sections(THICK_FILM_HYBRID))
        status = activity_status(THICK_FILM_HYBRID, owed)
        self.assertEqual(set(status), set(ACTIVITY_DEPENDENCIES))


class AssessmentTests(unittest.TestCase):
    def test_complete_submission_is_ready_for_assessment(self):
        result = assess_form_application(full_spec())
        self.assertEqual(result["readiness"], "assessment-may-start")
        self.assertTrue(result["ready_for_assessment"])

    def test_missing_section_blocks_the_assessment(self):
        result = assess_form_application(full_spec(form_sections=["die-attach-data"]))
        self.assertEqual(result["readiness"], "assessment-blocked")
        self.assertFalse(result["ready_for_assessment"])

    def test_unsubmitted_form_is_its_own_readiness_state(self):
        result = assess_form_application(
            full_spec(form_submitted=False, form_sections=[])
        )
        self.assertEqual(result["readiness"], "form-not-submitted")
        self.assertTrue(result["findings"])

    def test_sections_listed_for_an_unsubmitted_form_rejected(self):
        with self.assertRaises(ValueError):
            assess_form_application(
                full_spec(form_submitted=False, form_sections=["die-attach-data"])
            )

    def test_non_boolean_submission_flag_rejected(self):
        with self.assertRaises(ValueError):
            assess_form_application(full_spec(form_submitted="yes"))

    def test_spec_missing_a_key_rejected(self):
        spec = full_spec()
        del spec["form_sections"]
        with self.assertRaises(ValueError):
            assess_form_application(spec)

    def test_spec_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            assess_form_application(["declared_technologies"])

    def test_missing_packaging_step_is_reported_as_a_finding(self):
        result = assess_form_application(
            full_spec(
                declared_technologies=["co-fired-ceramic-substrate", "gold-wire-bonding"],
                form_sections=list(
                    required_form_sections(
                        ["co-fired-ceramic-substrate", "gold-wire-bonding"]
                    )
                ),
            )
        )
        self.assertIn(
            "the declaration names no 'packaging' technology", result["findings"]
        )

    def test_result_carries_the_sealing_category(self):
        result = assess_form_application(full_spec())
        self.assertEqual(result["sealing_category"], "hermetic")

    def test_result_coverage_is_complete_for_a_complete_form(self):
        result = assess_form_application(full_spec())
        self.assertAlmostEqual(result["coverage_percent"], 100.0, places=9)


if __name__ == "__main__":
    unittest.main()
