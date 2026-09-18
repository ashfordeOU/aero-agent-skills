"""GSE end item data package composition and release logic.

Anchor: ECSS-Q-ST-20C clause 5.8.4.1 -- the end item data package that is
produced for ground support equipment being delivered, with the package
content taken from the corresponding Annex B document requirements
definition. Paraphrased into an implementable procedure; no standard text is
reproduced.

Procedure implemented here
--------------------------
1. Validate the GSE item and derive the data package sections it owes from its
   own states rather than from a standing table: a pressurised system, a
   lifting duty, a software-driven controller, a calibrated measuring chain, a
   safety-critical duty and limited-life items each add their own section.
2. Validate the sections actually assembled, refusing a duplicate section, an
   unknown release state and an approved section with nobody behind it.
3. Name every gap: a required section absent, a required section still in
   draft, an approved section without an approver.
4. Require the open nonconformances against the item to be carried in the
   package, since the receiving side accepts the item with them.
5. Compute the approved fraction of the required set and decide whether the
   package may be released.
"""

import math

__all__ = [
    "BASE_EIDP_SECTIONS",
    "SECTION_STATES",
    "COMPLETENESS_TOLERANCE",
    "normalize_token",
    "validate_gse_item",
    "required_eidp_sections",
    "validate_sections",
    "section_findings",
    "nonconformance_findings",
    "package_completeness",
    "assess_gse_eidp",
]

# Sections every delivered GSE end item data package carries.
BASE_EIDP_SECTIONS = (
    "as-built-configuration-list",
    "identification-and-marking-record",
    "acceptance-test-report",
    "statement-of-conformity",
    "nonconformance-summary",
    "operating-and-handling-manual",
)

# The release states a package section may be in.
SECTION_STATES = ("approved", "draft", "superseded")

# The approved fraction is a ratio of two counts and can land a few ULPs short
# of unity; comparisons against a target absorb that here.
COMPLETENESS_TOLERANCE = 1e-9


def normalize_token(value, label="token"):
    """Return a lowercase, hyphen-joined comparison token for a name."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    token = "-".join(value.strip().lower().replace("_", " ").replace("-", " ").split())
    if not token:
        raise ValueError("%s must not be blank" % label)
    return token


def _flag(value, label):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (label, value))
    return value


def validate_gse_item(item):
    """Return the validated GSE item record."""
    if not isinstance(item, dict):
        raise ValueError("item must be a mapping")
    for key in ("item_id", "designation"):
        if key not in item:
            raise ValueError("item is missing '%s'" % key)
    return {
        "item_id": normalize_token(item["item_id"], "item_id"),
        "designation": normalize_token(item["designation"], "designation"),
        "pressurised": _flag(item.get("pressurised", False), "pressurised"),
        "lifting_duty": _flag(item.get("lifting_duty", False), "lifting_duty"),
        "software_driven": _flag(item.get("software_driven", False), "software_driven"),
        "calibrated": _flag(item.get("calibrated", False), "calibrated"),
        "safety_critical": _flag(item.get("safety_critical", False), "safety_critical"),
        "limited_life_items": _flag(
            item.get("limited_life_items", False), "limited_life_items"
        ),
    }


def required_eidp_sections(item):
    """Return the package sections this GSE item's own states make mandatory."""
    record = validate_gse_item(item)
    sections = list(BASE_EIDP_SECTIONS)
    if record["pressurised"]:
        sections.append("pressure-system-certification")
    if record["lifting_duty"]:
        sections.append("proof-load-certificate")
    if record["software_driven"]:
        sections.append("software-version-and-build-record")
    if record["calibrated"]:
        sections.append("calibration-certificate")
    if record["safety_critical"]:
        sections.append("safety-critical-gse-assessment-record")
    if record["limited_life_items"]:
        sections.append("limited-life-item-list")
    return sections


def validate_sections(sections):
    """Return the assembled package sections keyed by their comparison token."""
    if not isinstance(sections, (list, tuple)):
        raise ValueError("sections must be a sequence of section records")
    assembled = {}
    for i, section in enumerate(sections):
        if not isinstance(section, dict):
            raise ValueError("sections[%d] must be a mapping" % i)
        for key in ("name", "state"):
            if key not in section:
                raise ValueError("sections[%d] is missing '%s'" % (i, key))
        token = normalize_token(section["name"], "sections[%d]['name']" % i)
        if token in assembled:
            raise ValueError("section %r appears twice in the package" % token)
        state = normalize_token(section["state"], "sections[%d]['state']" % i)
        if state not in SECTION_STATES:
            raise ValueError("sections[%d] state %r is not a release state" % (i, state))
        approver = section.get("approver")
        if approver is not None:
            approver = normalize_token(approver, "sections[%d]['approver']" % i)
        assembled[token] = {"name": token, "state": state, "approver": approver}
    return assembled


def section_findings(sections, required_sections):
    """Return the gaps between the assembled package and the sections required."""
    assembled = validate_sections(sections)
    if not isinstance(required_sections, (list, tuple)):
        raise ValueError("required_sections must be a sequence of section names")
    findings = []
    for name in required_sections:
        token = normalize_token(name, "required section")
        entry = assembled.get(token)
        if entry is None:
            findings.append("package has no %s section" % token)
            continue
        if entry["state"] == "draft":
            findings.append("%s is still in draft and cannot be delivered" % token)
        elif entry["state"] == "superseded":
            findings.append("%s in the package has been superseded" % token)
        elif entry["approver"] is None:
            findings.append("%s is marked approved with no approver named" % token)
    return findings


def nonconformance_findings(open_nonconformances, listed_nonconformances):
    """Return the open nonconformances the package does not carry."""
    if not isinstance(open_nonconformances, (list, tuple)):
        raise ValueError("open_nonconformances must be a sequence of identifiers")
    if not isinstance(listed_nonconformances, (list, tuple)):
        raise ValueError("listed_nonconformances must be a sequence of identifiers")
    listed = {normalize_token(n, "listed nonconformance") for n in listed_nonconformances}
    findings = []
    for item in open_nonconformances:
        token = normalize_token(item, "open nonconformance")
        if token not in listed:
            findings.append("open nonconformance %s is not carried in the package" % token)
    return findings


def package_completeness(sections, required_sections):
    """Return the approved fraction of the required package sections."""
    assembled = validate_sections(sections)
    if not isinstance(required_sections, (list, tuple)) or not required_sections:
        raise ValueError("required_sections must be a non-empty sequence")
    tokens = [normalize_token(n, "required section") for n in required_sections]
    approved = 0
    for token in tokens:
        entry = assembled.get(token)
        if entry is not None and entry["state"] == "approved" and entry["approver"] is not None:
            approved += 1
    return approved / float(len(tokens))


def assess_gse_eidp(spec):
    """Run the full clause 5.8.4.1 GSE data package assessment.

    spec keys: item, sections, open_nonconformances, listed_nonconformances.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("item", "sections", "open_nonconformances", "listed_nonconformances"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    item = validate_gse_item(spec["item"])
    required = required_eidp_sections(spec["item"])
    sections = section_findings(spec["sections"], required)
    nonconformances = nonconformance_findings(
        spec["open_nonconformances"], spec["listed_nonconformances"]
    )
    completeness = package_completeness(spec["sections"], required)
    findings = list(sections) + list(nonconformances)
    complete = math.isclose(
        completeness, 1.0, rel_tol=0.0, abs_tol=COMPLETENESS_TOLERANCE
    )
    return {
        "item": item,
        "required_sections": required,
        "section_findings": sections,
        "nonconformance_findings": nonconformances,
        "completeness": completeness,
        "findings": findings,
        "package_releasable": complete and not findings,
    }
