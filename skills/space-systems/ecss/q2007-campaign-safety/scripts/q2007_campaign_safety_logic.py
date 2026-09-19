"""Safety management of a test campaign.

Anchor: ECSS-Q-ST-20-07C clause 5.9.4 (safety of a test campaign: identifying
the hazardous items and hazardous operations a campaign brings into the test
centre, obtaining the customer questionnaire covering their use, and feeding
the outcome into the design of the test process). Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Normalise the campaign declaration: every item and every operation the
   customer intends to bring or perform, with the hazard family it belongs to
   and the metric that family is graded on.
2. Decide per entry whether the declared metric reaches the threshold that
   makes that family hazardous for the campaign. Some families are hazardous
   at any declared quantity; others only above a stated level.
3. Reconcile the customer safety questionnaire against the resulting hazard
   set in both directions: a hazard with no answered topic, a topic that
   contradicts the declaration, a yes with no supporting detail, and a yes
   for a family the declaration never lists.
4. Check where each confirmed hazard is to be kept or operated, since a
   hazardous entry outside a controlled area is a campaign-level constraint
   and not a housekeeping note.
5. Derive the safety inputs the test process design owes each confirmed
   hazard family and return the campaign readiness decision.
"""

import math

__all__ = [
    "THRESHOLD_TOLERANCE",
    "HAZARD_FAMILIES",
    "DESIGN_INPUTS",
    "QUESTIONNAIRE_ANSWERS",
    "ENTRY_KINDS",
    "CONTROLLED_LOCATIONS",
    "normalise_identifier",
    "family_rule",
    "is_hazardous",
    "validate_declaration",
    "identify_hazards",
    "validate_questionnaire",
    "reconcile_questionnaire",
    "location_findings",
    "safety_design_inputs",
    "assess_campaign_safety",
]

# Threshold comparisons are inclusive: a declared value sitting exactly on the
# level is at the level. Absorb representation error here rather than by
# nudging the engineering threshold.
THRESHOLD_TOLERANCE = 1e-9

# Each hazard family is graded on one declared metric. A threshold of 0.0
# means any declared presence is hazardous; None means the family never is.
HAZARD_FAMILIES = {
    "pyrotechnic": {"metric": "quantity", "threshold": 0.0, "unit": "device"},
    "propellant": {"metric": "mass_kg", "threshold": 0.0, "unit": "kg"},
    "toxic-substance": {"metric": "mass_kg", "threshold": 0.0, "unit": "kg"},
    "ionising-radiation-source": {"metric": "activity_mbq", "threshold": 0.0, "unit": "MBq"},
    "cryogenic": {"metric": "volume_l", "threshold": 0.0, "unit": "l"},
    "pressurised-system": {"metric": "pressure_bar", "threshold": 5.0, "unit": "bar"},
    "high-voltage": {"metric": "voltage_v", "threshold": 50.0, "unit": "V"},
    "laser": {"metric": "class_rank", "threshold": 3.0, "unit": "rank"},
    "lifting": {"metric": "mass_kg", "threshold": 25.0, "unit": "kg"},
    "magnetic-field": {"metric": "flux_density_mt", "threshold": 0.5, "unit": "mT"},
    "inert": {"metric": "quantity", "threshold": None, "unit": "item"},
}

# What the test process design owes a family once it is confirmed hazardous.
DESIGN_INPUTS = {
    "pyrotechnic": (
        "dedicated-safety-authorisation",
        "electro-explosive-device-handling-controls",
        "hazardous-operation-procedure",
        "restricted-access-area-during-operation",
    ),
    "propellant": (
        "dedicated-safety-authorisation",
        "hazardous-operation-procedure",
        "material-compatibility-and-spill-controls",
        "personal-protective-equipment-plan",
        "restricted-access-area-during-operation",
    ),
    "toxic-substance": (
        "exposure-monitoring-arrangement",
        "hazardous-operation-procedure",
        "material-compatibility-and-spill-controls",
        "personal-protective-equipment-plan",
    ),
    "ionising-radiation-source": (
        "dedicated-safety-authorisation",
        "exposure-monitoring-arrangement",
        "hazardous-operation-procedure",
        "restricted-access-area-during-operation",
    ),
    "cryogenic": (
        "hazardous-operation-procedure",
        "oxygen-depletion-monitoring",
        "personal-protective-equipment-plan",
    ),
    "pressurised-system": (
        "hazardous-operation-procedure",
        "pressure-relief-and-proof-test-evidence",
        "restricted-access-area-during-operation",
    ),
    "high-voltage": (
        "hazardous-operation-procedure",
        "isolation-and-earthing-controls",
        "personal-protective-equipment-plan",
    ),
    "laser": (
        "hazardous-operation-procedure",
        "personal-protective-equipment-plan",
        "restricted-access-area-during-operation",
    ),
    "lifting": (
        "hazardous-operation-procedure",
        "lifting-equipment-certification-evidence",
        "restricted-access-area-during-operation",
    ),
    "magnetic-field": (
        "hazardous-operation-procedure",
        "restricted-access-area-during-operation",
    ),
    "inert": (),
}

QUESTIONNAIRE_ANSWERS = ("yes", "no", "not-applicable")

ENTRY_KINDS = ("item", "operation")

# Areas of the test centre where a hazardous entry may be kept or operated.
CONTROLLED_LOCATIONS = (
    "clean-room",
    "hazardous-storage",
    "propellant-bay",
    "test-hall",
)


def normalise_identifier(value, label):
    """Return a trimmed lowercase identifier; raise on anything else."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    text = value.strip().lower()
    if not text:
        raise ValueError("%s must not be empty" % label)
    return text


def family_rule(family):
    """Return the (metric, threshold, unit) grading rule of a hazard family."""
    name = normalise_identifier(family, "family")
    if name not in HAZARD_FAMILIES:
        raise ValueError(
            "unknown hazard family %r; known families are %s"
            % (name, "/".join(sorted(HAZARD_FAMILIES)))
        )
    rule = HAZARD_FAMILIES[name]
    return (rule["metric"], rule["threshold"], rule["unit"])


def _positive_real(value, label):
    """Return value as a strictly positive finite float."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    if number <= 0.0:
        raise ValueError("%s must be positive, got %g" % (label, number))
    return number


def is_hazardous(family, value):
    """Return True when the declared metric reaches the family threshold."""
    _metric, threshold, _unit = family_rule(family)
    number = _positive_real(value, "declared value")
    if threshold is None:
        return False
    if number > threshold:
        return True
    return math.isclose(number, threshold, rel_tol=0.0, abs_tol=THRESHOLD_TOLERANCE)


def validate_declaration(declaration):
    """Return the normalised campaign declaration keyed by entry identifier."""
    if not isinstance(declaration, (list, tuple)) or not declaration:
        raise ValueError("declaration must be a non-empty sequence of entries")
    entries = {}
    for index, item in enumerate(declaration):
        if not isinstance(item, dict):
            raise ValueError("declaration[%d] must be a mapping" % index)
        ref = normalise_identifier(item.get("id"), "declaration[%d].id" % index)
        if ref in entries:
            raise ValueError("duplicate declaration entry %r" % ref)
        family = normalise_identifier(item.get("family"), "declaration[%d].family" % index)
        metric, threshold, unit = family_rule(family)
        kind = normalise_identifier(item.get("kind"), "declaration[%d].kind" % index)
        if kind not in ENTRY_KINDS:
            raise ValueError(
                "declaration[%d].kind must be one of %s, got %r"
                % (index, "/".join(ENTRY_KINDS), kind)
            )
        value = _positive_real(item.get("value"), "declaration[%d].value" % index)
        location = item.get("location")
        entries[ref] = {
            "id": ref,
            "family": family,
            "kind": kind,
            "metric": metric,
            "threshold": threshold,
            "unit": unit,
            "value": value,
            "location": (
                None if location is None
                else normalise_identifier(location, "declaration[%d].location" % index)
            ),
            "hazardous": is_hazardous(family, value),
        }
    return entries


def identify_hazards(entries):
    """Group the normalised entries into hazardous and below-threshold sets."""
    if not isinstance(entries, dict) or not entries:
        raise ValueError("entries must be a non-empty mapping of normalised entries")
    hazardous = {}
    below = {}
    for ref in sorted(entries):
        entry = entries[ref]
        if not isinstance(entry, dict) or "family" not in entry:
            raise ValueError("entry %r must be a normalised declaration mapping" % ref)
        bucket = hazardous if entry.get("hazardous") else below
        bucket.setdefault(entry["family"], []).append(ref)
    return {"hazardous": hazardous, "below_threshold": below}


def validate_questionnaire(response):
    """Return the normalised customer safety questionnaire keyed by topic."""
    if response is None:
        response = []
    if not isinstance(response, (list, tuple)):
        raise ValueError("questionnaire response must be a sequence")
    topics = {}
    for index, item in enumerate(response):
        if not isinstance(item, dict):
            raise ValueError("questionnaire[%d] must be a mapping" % index)
        topic = normalise_identifier(item.get("topic"), "questionnaire[%d].topic" % index)
        if topic not in HAZARD_FAMILIES:
            raise ValueError(
                "questionnaire[%d].topic %r is not a hazard family" % (index, topic)
            )
        if topic in topics:
            raise ValueError("duplicate questionnaire topic %r" % topic)
        answer = normalise_identifier(item.get("answer"), "questionnaire[%d].answer" % index)
        if answer not in QUESTIONNAIRE_ANSWERS:
            raise ValueError(
                "questionnaire[%d].answer must be one of %s, got %r"
                % (index, "/".join(QUESTIONNAIRE_ANSWERS), answer)
            )
        detail = item.get("detail")
        if detail is not None and not isinstance(detail, str):
            raise ValueError("questionnaire[%d].detail must be a string when given" % index)
        topics[topic] = {
            "topic": topic,
            "answer": answer,
            "detail": None if detail is None or not detail.strip() else detail.strip(),
        }
    return topics


def reconcile_questionnaire(hazard_families, questionnaire):
    """Reconcile the hazard set against the questionnaire in both directions."""
    if not isinstance(hazard_families, (list, tuple, set, frozenset)):
        raise ValueError("hazard_families must be a collection of family names")
    if not isinstance(questionnaire, dict):
        raise ValueError("questionnaire must be the normalised topic mapping")
    families = set()
    for family in hazard_families:
        name = normalise_identifier(family, "hazard family")
        if name not in HAZARD_FAMILIES:
            raise ValueError("unknown hazard family %r" % name)
        families.add(name)
    findings = []
    for family in sorted(families):
        entry = questionnaire.get(family)
        if entry is None:
            findings.append({
                "code": "questionnaire-topic-missing",
                "severity": "blocking",
                "family": family,
                "message": "the campaign carries %s but the questionnaire has no answered "
                           "topic for it" % family,
            })
            continue
        if entry["answer"] != "yes":
            findings.append({
                "code": "questionnaire-contradicts-declaration",
                "severity": "blocking",
                "family": family,
                "message": "questionnaire answers %r for %s while the declaration crosses "
                           "its threshold" % (entry["answer"], family),
            })
            continue
        if entry["detail"] is None:
            findings.append({
                "code": "questionnaire-detail-missing",
                "severity": "blocking",
                "family": family,
                "message": "questionnaire confirms %s without the supporting detail the "
                           "test process design needs" % family,
            })
    for family in sorted(questionnaire):
        entry = questionnaire[family]
        if entry["answer"] == "yes" and family not in families:
            findings.append({
                "code": "declaration-missing-for-questionnaire-topic",
                "severity": "blocking",
                "family": family,
                "message": "questionnaire confirms %s but no declared item or operation "
                           "reaches that family threshold" % family,
            })
    return findings


def location_findings(entries):
    """Report hazardous entries kept or operated outside a controlled area."""
    if not isinstance(entries, dict):
        raise ValueError("entries must be the normalised declaration mapping")
    findings = []
    for ref in sorted(entries):
        entry = entries[ref]
        if not entry.get("hazardous"):
            continue
        location = entry.get("location")
        if location is None:
            findings.append({
                "code": "hazardous-entry-location-undeclared",
                "severity": "advisory",
                "family": entry["family"],
                "message": "hazardous entry %r declares no location inside the test centre"
                           % ref,
            })
        elif location not in CONTROLLED_LOCATIONS:
            findings.append({
                "code": "hazardous-entry-outside-controlled-area",
                "severity": "blocking",
                "family": entry["family"],
                "message": "hazardous entry %r is placed at %r, which is not a controlled "
                           "area" % (ref, location),
            })
    return findings


def safety_design_inputs(hazard_families):
    """Return the sorted union of design inputs owed to the hazard families."""
    if not isinstance(hazard_families, (list, tuple, set, frozenset)):
        raise ValueError("hazard_families must be a collection of family names")
    required = set()
    for family in hazard_families:
        name = normalise_identifier(family, "hazard family")
        if name not in DESIGN_INPUTS:
            raise ValueError("unknown hazard family %r" % name)
        required.update(DESIGN_INPUTS[name])
    return tuple(sorted(required))


def assess_campaign_safety(spec):
    """Run the clause 5.9.4 campaign safety assessment.

    spec keys: declaration (sequence of entries), questionnaire (sequence of
    answered topics, may be empty or absent).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    if "declaration" not in spec:
        raise ValueError("spec missing required key 'declaration'")
    entries = validate_declaration(spec["declaration"])
    grouped = identify_hazards(entries)
    questionnaire = validate_questionnaire(spec.get("questionnaire"))
    families = sorted(grouped["hazardous"])
    findings = reconcile_questionnaire(families, questionnaire)
    findings.extend(location_findings(entries))
    hazardous_count = sum(len(ids) for ids in grouped["hazardous"].values())
    operations = sorted(
        ref for ref, entry in entries.items()
        if entry["kind"] == "operation" and entry["hazardous"]
    )
    blocking = [f for f in findings if f["severity"] == "blocking"]
    if blocking:
        decision = "blocked"
    elif families:
        decision = "ready-with-safety-actions"
    else:
        decision = "ready"
    return {
        "entries": entries,
        "hazard_families": families,
        "hazardous_entries": grouped["hazardous"],
        "below_threshold_entries": grouped["below_threshold"],
        "hazardous_operations": operations,
        "hazardous_fraction": hazardous_count / float(len(entries)),
        "design_inputs": safety_design_inputs(families),
        "findings": findings,
        "blocking_findings": blocking,
        "decision": decision,
    }
