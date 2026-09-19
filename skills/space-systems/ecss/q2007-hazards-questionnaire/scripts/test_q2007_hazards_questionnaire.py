"""Contract tests for the Annex A hazardous-items questionnaire logic."""

import unittest

from q2007_hazards_questionnaire_logic import (
    AUTHORISED_ROLES,
    BASE_SECTIONS,
    QUESTIONS,
    SECTION_ORDER,
    SECTION_TRIGGERS,
    assess_questionnaire,
    authorisation_findings,
    consistency_findings,
    generate_questionnaire,
    grade_question,
    grade_response,
    normalise_identifier,
    required_sections,
    section_questions,
    validate_response,
)

PROFILE = {
    "customer": "customer-oue",
    "project": "demo-platform",
    "campaign": "tv-campaign-1",
    "facility": "thermal-vacuum-hall",
    "hazard_families": [],
}


def profile(**overrides):
    data = dict(PROFILE)
    data.update(overrides)
    return data


def complete_response(form, overrides=None):
    overrides = overrides or {}
    out = []
    for qid, meta in form["questions"].items():
        if qid in overrides:
            item = dict(overrides[qid])
            item.setdefault("question", qid)
            out.append(item)
            continue
        if meta["kind"] == "checklist":
            answer = "yes" if qid == "questionnaire-signed" else "no"
        elif qid == "safety-responsible-role":
            answer = "customer-safety-officer"
        else:
            answer = "stated by the customer"
        out.append({"question": qid, "answer": answer})
    return out


class NormaliseTests(unittest.TestCase):
    def test_trims_and_lowercases(self):
        self.assertEqual(normalise_identifier(" Uses-Laser ", "x"), "uses-laser")

    def test_non_string_rejected(self):
        with self.assertRaises(ValueError):
            normalise_identifier(None, "x")


class CatalogueTests(unittest.TestCase):
    def test_every_question_sits_in_a_known_section(self):
        for qid, meta in QUESTIONS.items():
            self.assertIn(meta["section"], SECTION_ORDER, qid)

    def test_every_trigger_names_a_known_section(self):
        for section in SECTION_TRIGGERS.values():
            self.assertIn(section, SECTION_ORDER)

    def test_section_questions_are_scoped_to_the_section(self):
        for qid in section_questions("authorisation"):
            self.assertEqual(QUESTIONS[qid]["section"], "authorisation")

    def test_unknown_section_rejected(self):
        with self.assertRaises(ValueError):
            section_questions("weather")


class RequiredSectionTests(unittest.TestCase):
    def test_base_and_authorisation_always_present(self):
        sections = required_sections([])
        for section in BASE_SECTIONS + ("authorisation",):
            self.assertIn(section, sections)

    def test_declared_family_pulls_in_its_detail_section(self):
        self.assertIn("laser-detail", required_sections(["laser"]))

    def test_two_families_can_share_one_detail_section(self):
        sections = required_sections(["propellant", "cryogenic"])
        self.assertEqual(sections.count("substance-detail"), 1)

    def test_sections_follow_the_drd_order(self):
        sections = required_sections(["laser", "pyrotechnic"])
        self.assertEqual(list(sections), [s for s in SECTION_ORDER if s in sections])

    def test_unknown_family_rejected(self):
        with self.assertRaises(ValueError):
            required_sections(["space-magic"])

    def test_non_collection_rejected(self):
        with self.assertRaises(ValueError):
            required_sections("laser")


class GenerationTests(unittest.TestCase):
    def test_form_carries_the_profile_identification(self):
        form = generate_questionnaire(profile())
        self.assertEqual(form["profile"]["facility"], "thermal-vacuum-hall")

    def test_form_without_families_omits_detail_sections(self):
        form = generate_questionnaire(profile())
        self.assertNotIn("laser-inventory", form["questions"])

    def test_form_with_a_family_carries_its_detail_questions(self):
        form = generate_questionnaire(profile(hazard_families=["laser"]))
        self.assertIn("laser-class-and-wavelength", form["questions"])

    def test_mandatory_list_matches_the_catalogue(self):
        form = generate_questionnaire(profile())
        self.assertEqual(
            set(form["mandatory"]),
            {q for q, m in form["questions"].items() if m["mandatory"]},
        )

    def test_missing_profile_key_rejected(self):
        with self.assertRaises(ValueError):
            generate_questionnaire({"customer": "a", "project": "b", "campaign": "c"})

    def test_empty_profile_value_rejected(self):
        with self.assertRaises(ValueError):
            generate_questionnaire(profile(facility="   "))

    def test_non_mapping_profile_rejected(self):
        with self.assertRaises(ValueError):
            generate_questionnaire(["customer"])


class ResponseValidationTests(unittest.TestCase):
    def test_checklist_answer_is_normalised(self):
        form = generate_questionnaire(profile())
        answers = validate_response(form, [{"question": "uses-laser", "answer": " YES "}])
        self.assertEqual(answers["uses-laser"]["answer"], "yes")

    def test_answer_to_a_question_not_on_the_form_rejected(self):
        form = generate_questionnaire(profile())
        with self.assertRaises(ValueError):
            validate_response(form, [{"question": "laser-inventory", "answer": "x"}])

    def test_duplicate_answer_rejected(self):
        form = generate_questionnaire(profile())
        with self.assertRaises(ValueError):
            validate_response(form, [
                {"question": "uses-laser", "answer": "no"},
                {"question": "uses-laser", "answer": "yes"},
            ])

    def test_unrecognised_checklist_token_rejected(self):
        form = generate_questionnaire(profile())
        with self.assertRaises(ValueError):
            validate_response(form, [{"question": "uses-laser", "answer": "possibly"}])

    def test_blank_text_answer_becomes_unanswered(self):
        form = generate_questionnaire(profile())
        answers = validate_response(form, [{"question": "project-name", "answer": "  "}])
        self.assertIsNone(answers["project-name"]["answer"])

    def test_non_string_answer_rejected(self):
        form = generate_questionnaire(profile())
        with self.assertRaises(ValueError):
            validate_response(form, [{"question": "project-name", "answer": 7}])

    def test_absent_response_is_empty(self):
        form = generate_questionnaire(profile())
        self.assertEqual(validate_response(form, None), {})


class QuestionGradingTests(unittest.TestCase):
    def test_unanswered_question(self):
        self.assertEqual(grade_question(QUESTIONS["uses-laser"], None), "unanswered")

    def test_affirmed_checklist_without_attachment(self):
        entry = {"question": "uses-laser", "answer": "yes", "attachment": None}
        self.assertEqual(grade_question(QUESTIONS["uses-laser"], entry), "attachment-missing")

    def test_affirmed_checklist_with_attachment(self):
        entry = {"question": "uses-laser", "answer": "yes", "attachment": "lsd-17"}
        self.assertEqual(grade_question(QUESTIONS["uses-laser"], entry), "answered")

    def test_denied_checklist_needs_no_attachment(self):
        entry = {"question": "uses-laser", "answer": "no", "attachment": None}
        self.assertEqual(grade_question(QUESTIONS["uses-laser"], entry), "answered")

    def test_malformed_meta_rejected(self):
        with self.assertRaises(ValueError):
            grade_question("uses-laser", None)


class ConsistencyTests(unittest.TestCase):
    def test_affirmed_activity_with_denied_item_is_a_finding(self):
        answers = {
            "performs-laser-alignment": {"answer": "yes", "attachment": "p-1"},
            "uses-laser": {"answer": "no", "attachment": None},
        }
        findings = consistency_findings(answers)
        self.assertEqual(findings[0]["code"], "activity-without-matching-item")

    def test_affirmed_activity_with_affirmed_item_is_clean(self):
        answers = {
            "performs-laser-alignment": {"answer": "yes", "attachment": "p-1"},
            "uses-laser": {"answer": "yes", "attachment": "lsd-17"},
        }
        self.assertEqual(consistency_findings(answers), [])

    def test_unanswered_activity_is_not_a_consistency_finding(self):
        self.assertEqual(consistency_findings({}), [])

    def test_non_mapping_rejected(self):
        with self.assertRaises(ValueError):
            consistency_findings([])


class AuthorisationTests(unittest.TestCase):
    def test_unsigned_form_is_a_finding(self):
        self.assertEqual(
            authorisation_findings({})[0]["code"], "questionnaire-not-signed"
        )

    def test_unrecognised_role_is_a_finding(self):
        answers = {
            "questionnaire-signed": {"answer": "yes", "attachment": None},
            "safety-responsible-role": {"answer": "work-experience-student",
                                        "attachment": None},
        }
        self.assertEqual(
            authorisation_findings(answers)[0]["code"], "authorisation-role-not-recognised"
        )

    def test_every_recognised_role_passes(self):
        for role in AUTHORISED_ROLES:
            answers = {
                "questionnaire-signed": {"answer": "yes", "attachment": None},
                "safety-responsible-role": {"answer": role, "attachment": None},
            }
            self.assertEqual(authorisation_findings(answers), [])


class ResponseGradingTests(unittest.TestCase):
    def test_complete_response_is_accepted(self):
        form = generate_questionnaire(profile())
        graded = grade_response(form, complete_response(form))
        self.assertEqual(graded["decision"], "accepted")
        self.assertAlmostEqual(graded["completeness"], 1.0, places=9)

    def test_one_missing_mandatory_answer_lowers_completeness(self):
        form = generate_questionnaire(profile())
        total = len(form["mandatory"])
        response = [r for r in complete_response(form) if r["question"] != "project-name"]
        graded = grade_response(form, response)
        self.assertAlmostEqual(graded["completeness"], (total - 1) / float(total), places=9)
        self.assertEqual(graded["decision"], "returned-to-customer")

    def test_affirmed_item_without_attachment_is_returned(self):
        form = generate_questionnaire(profile(hazard_families=["laser"]))
        response = complete_response(form, {"uses-laser": {"answer": "yes"}})
        graded = grade_response(form, response)
        codes = [f["code"] for f in graded["findings"]]
        self.assertIn("supporting-attachment-missing", codes)

    def test_affirmed_item_with_attachment_is_accepted(self):
        form = generate_questionnaire(profile(hazard_families=["laser"]))
        response = complete_response(
            form, {"uses-laser": {"answer": "yes", "attachment": "LSD-17"}}
        )
        self.assertEqual(grade_response(form, response)["decision"], "accepted")

    def test_empty_response_returns_every_mandatory_question(self):
        form = generate_questionnaire(profile())
        graded = grade_response(form, [])
        self.assertAlmostEqual(graded["completeness"], 0.0, places=9)
        self.assertEqual(
            len([f for f in graded["findings"]
                 if f["code"] == "mandatory-question-unanswered"]),
            len(form["mandatory"]),
        )


class AssessmentTests(unittest.TestCase):
    def test_assessment_carries_the_generated_form(self):
        form = generate_questionnaire(profile())
        result = assess_questionnaire({
            "profile": profile(), "response": complete_response(form)
        })
        self.assertEqual(result["decision"], "accepted")
        self.assertIn("questions", result["form"])

    def test_detail_section_questions_are_graded_too(self):
        form = generate_questionnaire(profile(hazard_families=["pressurised-system"]))
        response = [r for r in complete_response(form)
                    if r["question"] != "pressure-relief-arrangement"]
        result = assess_questionnaire({
            "profile": profile(hazard_families=["pressurised-system"]),
            "response": response,
        })
        self.assertEqual(result["decision"], "returned-to-customer")

    def test_missing_profile_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_questionnaire({"response": []})

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_questionnaire("profile")


if __name__ == "__main__":
    unittest.main(verbosity=0)
