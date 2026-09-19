"""Questionnaire on the use of hazardous items and activities.

Anchor: ECSS-Q-ST-20-07C Annex A, normative (the document requirements
definition for the questionnaire a test centre issues to a customer covering
the hazardous items brought into the facility and the hazardous activities
performed there). Paraphrased into an implementable procedure; no standard
text is reproduced.

Procedure implemented here
--------------------------
1. Build the questionnaire from the DRD skeleton for a campaign profile: the
   always-present sections -- identification, the hazardous item checklist,
   the hazardous activity checklist, the authorisation block -- plus the
   detail sections the declared hazard families pull in.
2. Normalise the returned response against the generated form, refusing an
   answer to a question the form does not carry.
3. Grade each question: a text question needs non-empty content, a checklist
   question needs a recognised answer, and a checklist question answered
   affirmatively needs the supporting attachment its family owes.
4. Grade the internal consistency of the form: an activity affirmed while the
   item it operates on is denied is a contradiction inside one response.
5. Grade the authorisation block: signed, dated, and attributed to a role
   that can commit the customer.
6. Return the completeness fraction over the mandatory questions and the
   issue decision: accepted, or returned to the customer with the reasons.
"""

__all__ = [
    "ANSWER_TOKENS",
    "QUESTION_KINDS",
    "BASE_SECTIONS",
    "SECTION_TRIGGERS",
    "SECTION_ORDER",
    "QUESTIONS",
    "CONSISTENCY_PAIRS",
    "AUTHORISED_ROLES",
    "normalise_identifier",
    "section_questions",
    "required_sections",
    "generate_questionnaire",
    "validate_response",
    "grade_question",
    "consistency_findings",
    "authorisation_findings",
    "grade_response",
    "assess_questionnaire",
]

ANSWER_TOKENS = ("yes", "no", "not-applicable")

QUESTION_KINDS = ("text", "checklist")

# Sections every issued questionnaire carries, in DRD order.
BASE_SECTIONS = ("identification", "hazardous-items", "hazardous-activities")

# A declared hazard family pulls in the detail section that covers it.
SECTION_TRIGGERS = {
    "pyrotechnic": "pyrotechnic-detail",
    "propellant": "substance-detail",
    "toxic-substance": "substance-detail",
    "cryogenic": "substance-detail",
    "pressurised-system": "pressure-detail",
    "ionising-radiation-source": "radiation-detail",
    "laser": "laser-detail",
    "lifting": "lifting-detail",
    "high-voltage": "electrical-detail",
}

# The authorisation block always closes the form.
SECTION_ORDER = BASE_SECTIONS + (
    "pyrotechnic-detail",
    "substance-detail",
    "pressure-detail",
    "radiation-detail",
    "laser-detail",
    "lifting-detail",
    "electrical-detail",
    "authorisation",
)


def _text(section, mandatory=True):
    return {"section": section, "kind": "text", "mandatory": mandatory, "attachment": None}


def _check(section, attachment, mandatory=True):
    return {
        "section": section,
        "kind": "checklist",
        "mandatory": mandatory,
        "attachment": attachment,
    }


# The DRD question catalogue. A checklist question answered affirmatively owes
# the attachment named against it.
QUESTIONS = {
    "customer-organisation": _text("identification"),
    "project-name": _text("identification"),
    "campaign-reference": _text("identification"),
    "test-facility": _text("identification"),
    "campaign-start-date": _text("identification"),
    "campaign-end-date": _text("identification"),

    "uses-pyrotechnics": _check("hazardous-items", "transport-and-storage-authorisation"),
    "uses-propellant": _check("hazardous-items", "safety-data-sheet"),
    "uses-toxic-substance": _check("hazardous-items", "safety-data-sheet"),
    "uses-cryogen": _check("hazardous-items", "safety-data-sheet"),
    "uses-pressure-vessel": _check("hazardous-items", "pressure-vessel-certificate"),
    "uses-ionising-radiation-source": _check("hazardous-items", "source-licence"),
    "uses-laser": _check("hazardous-items", "laser-safety-data"),
    "uses-high-voltage-equipment": _check("hazardous-items", "electrical-safety-declaration"),

    "performs-lifting-operation": _check("hazardous-activities", "lifting-equipment-certificate"),
    "performs-pressurisation-operation": _check("hazardous-activities", "pressurisation-procedure"),
    "performs-propellant-loading": _check("hazardous-activities", "propellant-loading-procedure"),
    "performs-pyrotechnic-installation": _check(
        "hazardous-activities", "pyrotechnic-installation-procedure"),
    "performs-laser-alignment": _check("hazardous-activities", "laser-operating-procedure"),

    "pyrotechnic-device-inventory": _text("pyrotechnic-detail"),
    "pyrotechnic-net-explosive-quantity": _text("pyrotechnic-detail"),
    "pyrotechnic-storage-arrangement": _text("pyrotechnic-detail"),

    "substance-inventory": _text("substance-detail"),
    "substance-quantity-held-on-site": _text("substance-detail"),
    "substance-spill-containment": _text("substance-detail"),

    "pressure-vessel-inventory": _text("pressure-detail"),
    "pressure-maximum-working-pressure": _text("pressure-detail"),
    "pressure-relief-arrangement": _text("pressure-detail"),

    "radiation-source-inventory": _text("radiation-detail"),
    "radiation-source-activity": _text("radiation-detail"),
    "radiation-exposure-control": _text("radiation-detail"),

    "laser-inventory": _text("laser-detail"),
    "laser-class-and-wavelength": _text("laser-detail"),
    "laser-beam-containment": _text("laser-detail"),

    "lifting-mass-and-centre-of-gravity": _text("lifting-detail"),
    "lifting-equipment-reference": _text("lifting-detail"),
    "lifting-plan-reference": _text("lifting-detail"),

    "electrical-maximum-voltage": _text("electrical-detail"),
    "electrical-isolation-arrangement": _text("electrical-detail"),

    "safety-responsible-name": _text("authorisation"),
    "safety-responsible-role": _text("authorisation"),
    "signature-date": _text("authorisation"),
    "questionnaire-signed": _check("authorisation", None),
}

# An affirmed activity implies the item it operates on.
CONSISTENCY_PAIRS = (
    ("performs-propellant-loading", "uses-propellant"),
    ("performs-pyrotechnic-installation", "uses-pyrotechnics"),
    ("performs-laser-alignment", "uses-laser"),
    ("performs-pressurisation-operation", "uses-pressure-vessel"),
)

# Who can commit the customer to the answers.
AUTHORISED_ROLES = (
    "customer-safety-officer",
    "product-assurance-manager",
    "project-manager",
)

_PROFILE_KEYS = ("customer", "project", "campaign", "facility")


def normalise_identifier(value, label):
    """Return a trimmed lowercase identifier; raise on anything else."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    text = value.strip().lower()
    if not text:
        raise ValueError("%s must not be empty" % label)
    return text


def section_questions(section):
    """Return the ordered question identifiers of a DRD section."""
    name = normalise_identifier(section, "section")
    if name not in SECTION_ORDER:
        raise ValueError(
            "unknown section %r; the DRD sections are %s" % (name, "/".join(SECTION_ORDER))
        )
    return tuple(q for q in QUESTIONS if QUESTIONS[q]["section"] == name)


def required_sections(hazard_families):
    """Return the ordered sections the form needs for these hazard families."""
    if not isinstance(hazard_families, (list, tuple, set, frozenset)):
        raise ValueError("hazard_families must be a collection of family names")
    needed = set(BASE_SECTIONS) | {"authorisation"}
    for family in hazard_families:
        name = normalise_identifier(family, "hazard family")
        if name not in SECTION_TRIGGERS:
            raise ValueError(
                "unknown hazard family %r; known families are %s"
                % (name, "/".join(sorted(SECTION_TRIGGERS)))
            )
        needed.add(SECTION_TRIGGERS[name])
    return tuple(s for s in SECTION_ORDER if s in needed)


def generate_questionnaire(profile):
    """Build the questionnaire form for a campaign profile."""
    if not isinstance(profile, dict):
        raise ValueError("profile must be a mapping")
    for key in _PROFILE_KEYS:
        if key not in profile:
            raise ValueError("profile missing required key %r" % key)
        normalise_identifier(profile[key], "profile[%r]" % key)
    families = profile.get("hazard_families", [])
    sections = required_sections(families)
    layout = []
    index = {}
    for section in sections:
        ids = section_questions(section)
        layout.append({"section": section, "questions": list(ids)})
        for qid in ids:
            index[qid] = dict(QUESTIONS[qid])
    return {
        "profile": {key: normalise_identifier(profile[key], key) for key in _PROFILE_KEYS},
        "sections": layout,
        "questions": index,
        "mandatory": tuple(sorted(q for q in index if index[q]["mandatory"])),
    }


def validate_response(form, response):
    """Return the normalised response keyed by question identifier."""
    if not isinstance(form, dict) or "questions" not in form:
        raise ValueError("form must be a generated questionnaire")
    if response is None:
        response = []
    if not isinstance(response, (list, tuple)):
        raise ValueError("response must be a sequence of answered questions")
    answers = {}
    for position, item in enumerate(response):
        if not isinstance(item, dict):
            raise ValueError("response[%d] must be a mapping" % position)
        qid = normalise_identifier(item.get("question"), "response[%d].question" % position)
        if qid not in form["questions"]:
            raise ValueError("response[%d] answers %r, which is not on this form"
                             % (position, qid))
        if qid in answers:
            raise ValueError("duplicate answer for question %r" % qid)
        meta = form["questions"][qid]
        raw = item.get("answer")
        if raw is not None and not isinstance(raw, str):
            raise ValueError("response[%d].answer must be a string when given" % position)
        if meta["kind"] == "checklist" and raw is not None and raw.strip():
            token = raw.strip().lower()
            if token not in ANSWER_TOKENS:
                raise ValueError(
                    "response[%d].answer must be one of %s for a checklist question, got %r"
                    % (position, "/".join(ANSWER_TOKENS), token)
                )
            answer = token
        elif raw is None or not raw.strip():
            answer = None
        else:
            answer = raw.strip()
        attachment = item.get("attachment")
        if attachment is not None and not isinstance(attachment, str):
            raise ValueError("response[%d].attachment must be a string when given" % position)
        answers[qid] = {
            "question": qid,
            "answer": answer,
            "attachment": (
                None if attachment is None or not attachment.strip()
                else attachment.strip().lower()
            ),
        }
    return answers


def grade_question(meta, entry):
    """Return the status of one question: answered, unanswered, or a defect."""
    if not isinstance(meta, dict) or "kind" not in meta:
        raise ValueError("meta must be a question definition")
    if entry is None or entry.get("answer") is None:
        return "unanswered"
    if meta["kind"] == "checklist":
        if entry["answer"] == "yes" and meta["attachment"] and entry["attachment"] is None:
            return "attachment-missing"
        return "answered"
    return "answered"


def consistency_findings(answers):
    """Report an affirmed activity whose underlying item is denied."""
    if not isinstance(answers, dict):
        raise ValueError("answers must be the normalised response mapping")
    findings = []
    for activity, item in CONSISTENCY_PAIRS:
        act = answers.get(activity)
        itm = answers.get(item)
        if act is None or act.get("answer") != "yes":
            continue
        if itm is not None and itm.get("answer") in ("no", "not-applicable"):
            findings.append({
                "code": "activity-without-matching-item",
                "severity": "blocking",
                "question": activity,
                "message": "%s is affirmed while %s is denied in the same response"
                           % (activity, item),
            })
    return findings


def authorisation_findings(answers):
    """Report a questionnaire that is unsigned, undated or wrongly attributed."""
    if not isinstance(answers, dict):
        raise ValueError("answers must be the normalised response mapping")
    findings = []
    signed = answers.get("questionnaire-signed")
    if signed is None or signed.get("answer") != "yes":
        findings.append({
            "code": "questionnaire-not-signed",
            "severity": "blocking",
            "question": "questionnaire-signed",
            "message": "the authorisation block does not carry a signature",
        })
    role = answers.get("safety-responsible-role")
    if role is not None and role.get("answer") is not None:
        if role["answer"].strip().lower() not in AUTHORISED_ROLES:
            findings.append({
                "code": "authorisation-role-not-recognised",
                "severity": "blocking",
                "question": "safety-responsible-role",
                "message": "%r cannot commit the customer; the recognised roles are %s"
                           % (role["answer"], "/".join(AUTHORISED_ROLES)),
            })
    return findings


def grade_response(form, response):
    """Grade a returned questionnaire against the form that was issued."""
    answers = validate_response(form, response)
    statuses = {}
    findings = []
    answered_mandatory = 0
    for qid in sorted(form["questions"]):
        meta = form["questions"][qid]
        status = grade_question(meta, answers.get(qid))
        statuses[qid] = status
        if status == "answered" and meta["mandatory"]:
            answered_mandatory += 1
        if status == "unanswered" and meta["mandatory"]:
            findings.append({
                "code": "mandatory-question-unanswered",
                "severity": "blocking",
                "question": qid,
                "message": "mandatory question %s of section %s is unanswered"
                           % (qid, meta["section"]),
            })
        elif status == "attachment-missing":
            findings.append({
                "code": "supporting-attachment-missing",
                "severity": "blocking",
                "question": qid,
                "message": "%s is affirmed without the %s it owes"
                           % (qid, meta["attachment"]),
            })
    findings.extend(consistency_findings(answers))
    findings.extend(authorisation_findings(answers))
    mandatory_total = len(form["mandatory"])
    blocking = [f for f in findings if f["severity"] == "blocking"]
    return {
        "answers": answers,
        "statuses": statuses,
        "findings": findings,
        "blocking_findings": blocking,
        "completeness": answered_mandatory / float(mandatory_total),
        "decision": "returned-to-customer" if blocking else "accepted",
    }


def assess_questionnaire(spec):
    """Generate the form for a profile and grade the response against it.

    spec keys: profile (mapping), response (sequence of answered questions).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    if "profile" not in spec:
        raise ValueError("spec missing required key 'profile'")
    form = generate_questionnaire(spec["profile"])
    graded = grade_response(form, spec.get("response"))
    graded["form"] = form
    return graded
