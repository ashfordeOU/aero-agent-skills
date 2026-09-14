"""Parts-approval route and justification grading for class 2 commercial EEE parts.

Anchor: ECSS-Q-ST-60-13C clause 5.2.4 (the approval route a commercial
electrical, electronic and electromechanical part takes at the intermediate
assurance class, and the justification record that has to stand behind the
approval). Paraphrased into an implementable procedure; no standard text is
reproduced.

Procedure implemented here
--------------------------
1. Validate the approval policy: the covered share floor, the weighted
   completeness floor, the credit an element carried by a referenced document
   earns, and the marginal band that raises an advisory.
2. Validate the approval record itself: a reference, an issue, a named
   approver drawn from the permitted roles, the approval and first-commitment
   sequence positions, the validity period and the age of the approval.
3. Raise the approval route the declared escalation drivers demand. Every
   driver names a minimum route on the authority ladder and the required route
   is the highest of them; a declared route below that is a finding, one above
   it is recorded but is not.
4. Dispose every required justification element as written into the record,
   carried by an identified referenced document, stated without a rationale
   behind it, or absent, and credit a referenced element below one.
5. Take the covered share and the depth-weighted completeness over the full
   required element list, so deleting a weak element can only lower the score.
6. Compare both figures with their floors under a named tolerance, then check
   the approval age against its validity and the approval position against the
   first procurement commitment.
7. Close on one verdict carrying every finding.
"""

import math

__all__ = [
    "APPROVAL_ROUTES",
    "ROUTE_RANK",
    "ESCALATION_DRIVERS",
    "APPROVER_ROLES",
    "REQUIRED_JUSTIFICATION_ELEMENTS",
    "SCORE_TOLERANCE",
    "validate_approval_policy",
    "validate_citation",
    "validate_approval_record",
    "route_rank",
    "required_route",
    "validate_justification_element",
    "dispose_justification",
    "justification_scores",
    "validity_state",
    "assess_parts_approval",
]

# The authority ladder an approval may be taken at, lowest authority first.
APPROVAL_ROUTES = (
    "component-engineer-approval",
    "parts-control-board-approval",
    "customer-agreed-approval",
)

ROUTE_RANK = {name: index for index, name in enumerate(APPROVAL_ROUTES)}

# Each declared driver names the lowest route that can carry the part.
ESCALATION_DRIVERS = {
    "no-approved-equivalent-on-the-project": "parts-control-board-approval",
    "supplied-outside-the-franchised-network": "parts-control-board-approval",
    "used-beyond-the-published-temperature-range": "parts-control-board-approval",
    "no-published-radiation-data": "customer-agreed-approval",
    "single-point-failure-function": "customer-agreed-approval",
    "obsolete-at-the-order-date": "parts-control-board-approval",
}

# Who may sign a class 2 part approval.
APPROVER_ROLES = (
    "project-component-engineer",
    "parts-control-board",
    "product-assurance-manager",
)

# The content the justification behind the approval has to carry.
REQUIRED_JUSTIFICATION_ELEMENTS = (
    "need-statement",
    "alternatives-examined",
    "residual-risk-statement",
    "compensating-measures",
    "approval-validity-scope",
)

# Shares are ratios of small integers scaled by a credit; an exactly met floor
# must not fail on representation alone.
SCORE_TOLERANCE = 1e-9


def _require_text(value, label):
    """Return a non-blank text field, raising on anything else."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %s" % (label, type(value).__name__))
    text = value.strip()
    if not text:
        raise ValueError("%s must not be blank" % label)
    return text


def _normalize_token(value, label):
    """Return a normalized lower-case hyphenated token."""
    text = _require_text(value, label)
    return "-".join(text.lower().replace("_", " ").replace("-", " ").split())


def _unit_interval(value, label):
    """Return a finite float inside the closed unit interval."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    if number < 0.0 or number > 1.0:
        raise ValueError("%s must lie in [0, 1], got %g" % (label, number))
    return number


def _non_negative_int(value, label):
    """Return a non-negative integer position or duration."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %d" % (label, value))
    return value


def validate_approval_policy(policy):
    """Return the validated grading policy for a class 2 part approval."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping")
    for key in ("covered_floor", "completeness_floor", "reference_credit",
                "marginal_band"):
        if key not in policy:
            raise ValueError("policy missing required key '%s'" % key)
    covered_floor = _unit_interval(policy["covered_floor"], "covered_floor")
    completeness_floor = _unit_interval(
        policy["completeness_floor"], "completeness_floor"
    )
    reference_credit = _unit_interval(policy["reference_credit"], "reference_credit")
    marginal_band = _unit_interval(policy["marginal_band"], "marginal_band")
    if completeness_floor > covered_floor:
        raise ValueError(
            "completeness_floor %g cannot exceed covered_floor %g; a credited "
            "element can never score above a written one"
            % (completeness_floor, covered_floor)
        )
    if reference_credit <= 0.0:
        raise ValueError("reference_credit must be positive; a credit of nothing "
                         "makes a referenced element indistinguishable from an "
                         "absent one")
    if reference_credit >= 1.0:
        raise ValueError("reference_credit must be below 1; a full credit makes a "
                         "record of pure pointers score as a written record")
    if marginal_band > covered_floor:
        raise ValueError(
            "marginal_band %g is wider than covered_floor %g; the advisory band "
            "would cover every possible score" % (marginal_band, covered_floor)
        )
    return {
        "covered_floor": covered_floor,
        "completeness_floor": completeness_floor,
        "reference_credit": reference_credit,
        "marginal_band": marginal_band,
    }


def validate_citation(citation, label="citation"):
    """Return the validated (document, issue) pointer of a referenced element."""
    if not isinstance(citation, dict):
        raise ValueError("%s must be a mapping" % label)
    for key in ("document", "issue"):
        if key not in citation:
            raise ValueError("%s missing required key '%s'" % (label, key))
    return {
        "document": _require_text(citation["document"], "%s document" % label),
        "issue": _require_text(citation["issue"], "%s issue" % label),
    }


def validate_approval_record(record):
    """Return the validated identity, authority and timing of the approval."""
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping")
    for key in ("reference", "issue", "approver_role", "declared_route",
                "approval_position", "first_commitment_position",
                "validity_months", "age_months"):
        if key not in record:
            raise ValueError("record missing required key '%s'" % key)
    approver_role = _normalize_token(record["approver_role"], "approver_role")
    if approver_role not in APPROVER_ROLES:
        raise ValueError(
            "approver_role '%s' is not a permitted approval authority; expected "
            "one of %s" % (approver_role, ", ".join(APPROVER_ROLES))
        )
    declared_route = _normalize_token(record["declared_route"], "declared_route")
    if declared_route not in ROUTE_RANK:
        raise ValueError(
            "declared_route '%s' is not a recognized approval route; expected one "
            "of %s" % (declared_route, ", ".join(APPROVAL_ROUTES))
        )
    validity_months = _non_negative_int(record["validity_months"], "validity_months")
    if validity_months < 1:
        raise ValueError("validity_months must be at least 1; an approval valid "
                         "for no time approves nothing")
    return {
        "reference": _require_text(record["reference"], "reference"),
        "issue": _require_text(record["issue"], "issue"),
        "approver_role": approver_role,
        "declared_route": declared_route,
        "approval_position": _non_negative_int(
            record["approval_position"], "approval_position"
        ),
        "first_commitment_position": _non_negative_int(
            record["first_commitment_position"], "first_commitment_position"
        ),
        "validity_months": validity_months,
        "age_months": _non_negative_int(record["age_months"], "age_months"),
    }


def route_rank(route):
    """Return the authority rank of an approval route, lowest authority zero."""
    token = _normalize_token(route, "route")
    if token not in ROUTE_RANK:
        raise ValueError(
            "route '%s' is not a recognized approval route; expected one of %s"
            % (token, ", ".join(APPROVAL_ROUTES))
        )
    return ROUTE_RANK[token]


def required_route(drivers):
    """Return the route the declared escalation drivers demand, and their names.

    With no driver declared the delegated component-engineer route carries the
    part; every declared driver raises the floor and the highest one wins.
    """
    if not isinstance(drivers, (list, tuple)):
        raise ValueError("drivers must be a sequence of declared driver names")
    seen = []
    highest = 0
    raising = []
    for index, value in enumerate(drivers):
        token = _normalize_token(value, "drivers[%d]" % index)
        if token not in ESCALATION_DRIVERS:
            raise ValueError(
                "escalation driver '%s' is not recognized; expected one of %s"
                % (token, ", ".join(sorted(ESCALATION_DRIVERS)))
            )
        if token in seen:
            raise ValueError("escalation driver '%s' is declared twice" % token)
        seen.append(token)
        rank = ROUTE_RANK[ESCALATION_DRIVERS[token]]
        if rank > highest:
            highest = rank
            raising = [token]
        elif rank == highest and rank > 0:
            raising.append(token)
    return {
        "route": APPROVAL_ROUTES[highest],
        "rank": highest,
        "drivers": seen,
        "raised_by": raising,
    }


def validate_justification_element(element):
    """Return one validated justification element of the approval record."""
    if not isinstance(element, dict):
        raise ValueError("each justification element must be a mapping")
    if "name" not in element:
        raise ValueError("justification element missing required key 'name'")
    name = _normalize_token(element["name"], "justification element name")
    if name not in REQUIRED_JUSTIFICATION_ELEMENTS:
        raise ValueError(
            "justification element '%s' is not one the class requires; expected "
            "one of %s" % (name, ", ".join(REQUIRED_JUSTIFICATION_ELEMENTS))
        )
    rationale = element.get("rationale", "")
    if rationale is None:
        rationale = ""
    if not isinstance(rationale, str):
        raise ValueError("rationale for '%s' must be a string" % name)
    citation = element.get("citation")
    written = bool(rationale.strip())
    if citation is not None and written:
        raise ValueError(
            "element '%s' carries both a rationale and a referenced document; "
            "one basis per element" % name
        )
    reference = validate_citation(citation, "element '%s' citation" % name) \
        if citation is not None else None
    return {
        "name": name,
        "rationale": rationale.strip(),
        "citation": reference,
    }


def dispose_justification(elements, policy):
    """Return the per-element dispositions over the full required element list."""
    graded_policy = validate_approval_policy(policy)
    if not isinstance(elements, (list, tuple)):
        raise ValueError("elements must be a sequence")
    declared = {}
    for element in elements:
        record = validate_justification_element(element)
        if record["name"] in declared:
            raise ValueError(
                "justification element '%s' is declared twice" % record["name"]
            )
        declared[record["name"]] = record

    dispositions = []
    for name in REQUIRED_JUSTIFICATION_ELEMENTS:
        record = declared.get(name)
        if record is None:
            dispositions.append(
                {"name": name, "state": "absent", "weight": 0.0, "treated": False}
            )
        elif record["citation"] is not None:
            dispositions.append(
                {
                    "name": name,
                    "state": "carried-by-reference",
                    "weight": graded_policy["reference_credit"],
                    "treated": True,
                    "citation": record["citation"],
                }
            )
        elif record["rationale"]:
            dispositions.append(
                {"name": name, "state": "written", "weight": 1.0, "treated": True}
            )
        else:
            dispositions.append(
                {
                    "name": name,
                    "state": "stated-without-a-rationale",
                    "weight": 0.0,
                    "treated": False,
                }
            )
    return dispositions


def justification_scores(dispositions):
    """Return the covered share and the weighted completeness of the record."""
    if not isinstance(dispositions, (list, tuple)) or not dispositions:
        raise ValueError("dispositions must be a non-empty sequence")
    total = len(dispositions)
    treated = 0
    weight = 0.0
    for entry in dispositions:
        if not isinstance(entry, dict) or "state" not in entry:
            raise ValueError("each disposition must be a graded mapping")
        if entry.get("treated"):
            treated += 1
        weight += float(entry.get("weight", 0.0))
    return {
        "required": total,
        "treated": treated,
        "covered_share": treated / total,
        "completeness": weight / total,
    }


def validity_state(record):
    """Return whether the approval is still inside its declared validity."""
    if not isinstance(record, dict):
        raise ValueError("record must be a validated approval mapping")
    for key in ("validity_months", "age_months"):
        if key not in record:
            raise ValueError("record missing required key '%s'" % key)
    age = _non_negative_int(record["age_months"], "age_months")
    validity = _non_negative_int(record["validity_months"], "validity_months")
    return {
        "age_months": age,
        "validity_months": validity,
        "remaining_months": validity - age,
        "lapsed": age > validity,
    }


def assess_parts_approval(case):
    """Run the full clause 5.2.4 part-approval assessment.

    case keys: policy, record, escalation_drivers, justification.
    """
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping")
    for key in ("policy", "record", "escalation_drivers", "justification"):
        if key not in case:
            raise ValueError("case missing required key '%s'" % key)

    policy = validate_approval_policy(case["policy"])
    record = case["record"]
    findings = []

    if record is None:
        return {
            "policy": policy,
            "record": None,
            "verdict": "approval not established",
            "approved": False,
            "findings": ["no approval record exists for the part"],
        }

    approval = validate_approval_record(record)
    demanded = required_route(case["escalation_drivers"])
    declared_rank = ROUTE_RANK[approval["declared_route"]]

    route_short = declared_rank < demanded["rank"]
    if route_short:
        findings.append(
            "approval taken at '%s' but the declared drivers (%s) demand '%s'"
            % (
                approval["declared_route"],
                ", ".join(demanded["raised_by"]) or "none",
                demanded["route"],
            )
        )
    route_above = declared_rank > demanded["rank"]

    dispositions = dispose_justification(case["justification"], policy)
    scores = justification_scores(dispositions)

    absent = [d["name"] for d in dispositions if d["state"] == "absent"]
    heading_only = [
        d["name"] for d in dispositions if d["state"] == "stated-without-a-rationale"
    ]
    referenced = [d["name"] for d in dispositions if d["state"] == "carried-by-reference"]
    for name in absent:
        findings.append("justification element '%s' is absent from the record" % name)
    for name in heading_only:
        findings.append(
            "justification element '%s' is named with no rationale behind it" % name
        )

    covered_short = scores["covered_share"] < policy["covered_floor"] and not math.isclose(
        scores["covered_share"], policy["covered_floor"],
        rel_tol=0.0, abs_tol=SCORE_TOLERANCE,
    )
    completeness_short = scores["completeness"] < policy["completeness_floor"] and \
        not math.isclose(
            scores["completeness"], policy["completeness_floor"],
            rel_tol=0.0, abs_tol=SCORE_TOLERANCE,
        )
    if covered_short:
        findings.append(
            "justification covers %.3f of the required elements, below the floor %.3f"
            % (scores["covered_share"], policy["covered_floor"])
        )
    if completeness_short:
        findings.append(
            "weighted justification completeness %.3f is below the floor %.3f"
            % (scores["completeness"], policy["completeness_floor"])
        )

    validity = validity_state(approval)
    if validity["lapsed"]:
        findings.append(
            "approval is %d months old against a validity of %d months"
            % (validity["age_months"], validity["validity_months"])
        )

    late = approval["approval_position"] > approval["first_commitment_position"]
    if late:
        findings.append(
            "approval recorded at position %d, after the first procurement "
            "commitment at position %d"
            % (approval["approval_position"], approval["first_commitment_position"])
        )

    advisories = []
    margin = scores["completeness"] - policy["completeness_floor"]
    if not completeness_short and 0.0 <= margin <= policy["marginal_band"]:
        advisories.append(
            "weighted completeness %.3f sits inside the marginal band above its floor"
            % scores["completeness"]
        )
    if route_above:
        advisories.append(
            "approval taken at '%s', above the '%s' the drivers demand"
            % (approval["declared_route"], demanded["route"])
        )

    if route_short:
        verdict = "approval route below the required level"
    elif validity["lapsed"]:
        verdict = "approval lapsed"
    elif late:
        verdict = "approval recorded after the procurement commitment"
    elif covered_short or completeness_short or absent or heading_only:
        verdict = "justification record short of the required content"
    else:
        verdict = "part approved for class 2 use"

    return {
        "policy": policy,
        "record": approval,
        "required_route": demanded,
        "dispositions": dispositions,
        "scores": scores,
        "absent_elements": absent,
        "heading_only_elements": heading_only,
        "referenced_elements": referenced,
        "validity": validity,
        "advisories": advisories,
        "verdict": verdict,
        "approved": verdict == "part approved for class 2 use",
        "findings": findings,
    }
