"""General selection duties for commercial components at the lowest class.

Anchor: ECSS-Q-ST-60-13C clause 6.2.1 (the general selection duties that apply
when commercial components are chosen for a design working at the lowest
assurance class). Paraphrased into an implementable procedure; no standard
text is reproduced.

Procedure implemented here
--------------------------
1. Validate the duty register: every duty must be declared, and the weights
   must sum to unity.
2. Read the declared state of each duty for a component. A duty is credited
   only where an evidence reference is cited; an asserted duty stays open.
3. Drop a duty from the denominator only where it is discretionary at this
   class and the not-applicable claim carries a recorded justification. A
   not-applicable claim on a duty the class keeps mandatory is refused and the
   duty stays open.
4. Weight the credited duties into a coverage fraction over the applicable
   duties and compare it with the declared floor.
5. Categorize each component, keep the lowest-coverage component as the
   governing case, and return the outstanding duties with one selection
   verdict for the list.
"""

import math

__all__ = [
    "COVERAGE_TOLERANCE",
    "SELECTION_DUTIES",
    "DUTY_STATES",
    "SELECTION_CATEGORIES",
    "validate_identifier",
    "validate_duty_register",
    "duty_disposition",
    "component_dispositions",
    "selection_coverage",
    "outstanding_duties",
    "component_category",
    "evaluate_component_selection",
    "assess_class3_selection",
]

# Coverage is a ratio of summed weights; an exactly-met floor can land a few
# ULPs low. Absorb that here, never by moving the floor.
COVERAGE_TOLERANCE = 1e-9

# Selection duty -> the share of the selection argument it carries, and
# whether the lowest assurance class still keeps it mandatory. A mandatory
# duty cannot be dropped from the denominator by a not-applicable claim.
SELECTION_DUTIES = {
    "application-suitability": {"weight": 0.20, "mandatory": True},
    "operating-range-coverage": {"weight": 0.20, "mandatory": True},
    "manufacturer-identification": {"weight": 0.15, "mandatory": True},
    "excluded-technology-check": {"weight": 0.10, "mandatory": True},
    "known-defect-review": {"weight": 0.15, "mandatory": False},
    "procurement-availability": {"weight": 0.10, "mandatory": False},
    "obsolescence-outlook": {"weight": 0.10, "mandatory": False},
}

DUTY_STATES = ("evidenced", "asserted", "not-applicable", "open")

SELECTION_CATEGORIES = (
    "selection-closed",
    "selection-open",
    "selection-blocked",
)

_CATEGORY_SEVERITY = {
    "selection-blocked": 0,
    "selection-open": 1,
    "selection-closed": 2,
}


def validate_identifier(value, label):
    """Return a non-blank stripped identifier, or raise."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    text = value.strip()
    if not text:
        raise ValueError("%s must not be blank" % label)
    return text


def validate_duty_register(register=None):
    """Return a validated duty register whose weights sum to unity."""
    if register is None:
        register = SELECTION_DUTIES
    if not isinstance(register, dict) or not register:
        raise ValueError("duty register must be a non-empty mapping")
    cleaned = {}
    for name, entry in register.items():
        duty = validate_identifier(name, "duty name")
        if not isinstance(entry, dict):
            raise ValueError("register entry for %s must be a mapping" % duty)
        if "weight" not in entry or "mandatory" not in entry:
            raise ValueError(
                "register entry for %s must declare weight and mandatory" % duty
            )
        weight = entry["weight"]
        if isinstance(weight, bool) or not isinstance(weight, (int, float)):
            raise ValueError("weight of %s must be a real number" % duty)
        weight = float(weight)
        if not math.isfinite(weight) or weight <= 0.0:
            raise ValueError("weight of %s must be positive and finite" % duty)
        if not isinstance(entry["mandatory"], bool):
            raise ValueError("mandatory flag of %s must be a boolean" % duty)
        cleaned[duty] = {"weight": weight, "mandatory": entry["mandatory"]}
    if not any(entry["mandatory"] for entry in cleaned.values()):
        raise ValueError("a selection register must keep at least one duty mandatory")
    total = math.fsum(entry["weight"] for entry in cleaned.values())
    if not math.isclose(total, 1.0, rel_tol=0.0, abs_tol=COVERAGE_TOLERANCE):
        raise ValueError("duty weights must sum to unity, got %.12f" % total)
    return cleaned


def duty_disposition(duty, entry, register):
    """Return how one declared duty is dispositioned, with its note."""
    name = validate_identifier(duty, "duty name")
    if name not in register:
        raise ValueError("duty %s is not in the declared register" % name)
    if entry is None:
        return {
            "duty": name,
            "state": "open",
            "credited": False,
            "applicable": True,
            "note": "%s not addressed in the selection record" % name,
        }
    if not isinstance(entry, dict):
        raise ValueError("declaration for %s must be a mapping" % name)
    state = validate_identifier(entry.get("state"), "state of %s" % name)
    if state not in DUTY_STATES:
        raise ValueError(
            "state %s of %s is not one of %s" % (state, name, ", ".join(DUTY_STATES))
        )
    if state == "evidenced":
        reference = entry.get("evidence")
        if not isinstance(reference, str) or not reference.strip():
            raise ValueError(
                "%s is declared evidenced without an evidence reference" % name
            )
        return {
            "duty": name,
            "state": state,
            "credited": True,
            "applicable": True,
            "note": None,
        }
    if state == "asserted":
        return {
            "duty": name,
            "state": state,
            "credited": False,
            "applicable": True,
            "note": "%s asserted without an evidence reference" % name,
        }
    if state == "open":
        return {
            "duty": name,
            "state": state,
            "credited": False,
            "applicable": True,
            "note": "%s left open in the selection record" % name,
        }
    if register[name]["mandatory"]:
        return {
            "duty": name,
            "state": "open",
            "credited": False,
            "applicable": True,
            "note": "%s is mandatory at this class and cannot be claimed "
            "not applicable" % name,
        }
    justification = entry.get("justification")
    if not isinstance(justification, str) or not justification.strip():
        return {
            "duty": name,
            "state": "open",
            "credited": False,
            "applicable": True,
            "note": "%s claimed not applicable without a recorded justification"
            % name,
        }
    return {
        "duty": name,
        "state": "not-applicable",
        "credited": False,
        "applicable": False,
        "note": "%s dropped on a recorded justification" % name,
    }


def component_dispositions(declared, register=None):
    """Return the disposition of every duty in the register for a component."""
    graded = validate_duty_register(register)
    if not isinstance(declared, dict):
        raise ValueError("declared duties must be a mapping")
    for name in declared:
        duty = validate_identifier(name, "declared duty name")
        if duty not in graded:
            raise ValueError("duty %s is not in the declared register" % duty)
    return tuple(
        duty_disposition(duty, declared.get(duty), graded) for duty in sorted(graded)
    )


def selection_coverage(dispositions, register=None):
    """Return the weighted share of the applicable duties that are credited."""
    graded = validate_duty_register(register)
    if not isinstance(dispositions, (list, tuple)) or not dispositions:
        raise ValueError("dispositions must be a non-empty sequence")
    applicable = 0.0
    credited = 0.0
    for record in dispositions:
        if not isinstance(record, dict):
            raise ValueError("each disposition must be a mapping")
        duty = validate_identifier(record.get("duty"), "duty name")
        if duty not in graded:
            raise ValueError("duty %s is not in the declared register" % duty)
        if not record.get("applicable", True):
            continue
        applicable += graded[duty]["weight"]
        if record.get("credited"):
            credited += graded[duty]["weight"]
    if applicable <= 0.0:
        raise ValueError("no applicable duty remains; the register cannot be graded")
    return credited / applicable


def outstanding_duties(dispositions):
    """Return the duties still owed, mandatory ones first."""
    if not isinstance(dispositions, (list, tuple)):
        raise ValueError("dispositions must be a sequence")
    owed = []
    for record in dispositions:
        if not isinstance(record, dict):
            raise ValueError("each disposition must be a mapping")
        if record.get("applicable", True) and not record.get("credited"):
            owed.append(validate_identifier(record.get("duty"), "duty name"))
    return tuple(sorted(owed))


def component_category(dispositions, coverage, floor, register=None):
    """Return the selection category a component earns."""
    graded = validate_duty_register(register)
    if isinstance(coverage, bool) or not isinstance(coverage, (int, float)):
        raise ValueError("coverage must be a real number")
    value = float(coverage)
    if not math.isfinite(value) or value < 0.0 or value > 1.0:
        raise ValueError("coverage must lie in [0, 1], got %r" % (coverage,))
    if isinstance(floor, bool) or not isinstance(floor, (int, float)):
        raise ValueError("floor must be a real number")
    limit = float(floor)
    if not math.isfinite(limit) or limit < 0.0 or limit > 1.0:
        raise ValueError("floor must lie in [0, 1], got %r" % (floor,))
    owed = outstanding_duties(dispositions)
    if any(graded[duty]["mandatory"] for duty in owed):
        return "selection-blocked"
    meets = value > limit or math.isclose(
        value, limit, rel_tol=0.0, abs_tol=COVERAGE_TOLERANCE
    )
    if not meets:
        return "selection-open"
    return "selection-closed"


def evaluate_component_selection(item, floor=0.7, register=None):
    """Return the selection record of one candidate component.

    item keys: component (identifier), duties (mapping of duty declarations).
    """
    if not isinstance(item, dict):
        raise ValueError("each component item must be a mapping")
    component = validate_identifier(item.get("component"), "component")
    if "duties" not in item:
        raise ValueError("component %s declares no duties mapping" % component)
    graded = validate_duty_register(register)
    dispositions = component_dispositions(item["duties"], graded)
    coverage = selection_coverage(dispositions, graded)
    owed = outstanding_duties(dispositions)
    notes = tuple(
        record["note"] for record in dispositions if record["note"] is not None
    )
    return {
        "component": component,
        "dispositions": dispositions,
        "coverage": coverage,
        "outstanding": owed,
        "mandatory_outstanding": tuple(
            duty for duty in owed if graded[duty]["mandatory"]
        ),
        "category": component_category(dispositions, coverage, floor, graded),
        "notes": notes,
    }


def assess_class3_selection(spec):
    """Run the full clause 6.2.1 selection duty assessment for a parts list.

    spec keys: components (non-empty sequence of items), optional floor
    (default 0.7), optional register.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    if "components" not in spec:
        raise ValueError("spec missing required key 'components'")
    components = spec["components"]
    if not isinstance(components, (list, tuple)) or not components:
        raise ValueError("spec['components'] must be a non-empty sequence")
    floor = spec.get("floor", 0.7)
    if isinstance(floor, bool) or not isinstance(floor, (int, float)):
        raise ValueError("floor must be a real number")
    floor = float(floor)
    if not math.isfinite(floor) or floor < 0.0 or floor > 1.0:
        raise ValueError("floor must lie in [0, 1], got %r" % (spec.get("floor"),))
    graded = validate_duty_register(spec.get("register"))

    records = [
        evaluate_component_selection(item, floor, graded) for item in components
    ]
    seen = set()
    for record in records:
        if record["component"] in seen:
            raise ValueError("component %s is declared twice" % record["component"])
        seen.add(record["component"])

    counts = {category: 0 for category in SELECTION_CATEGORIES}
    for record in records:
        counts[record["category"]] += 1
    list_coverage = math.fsum(record["coverage"] for record in records) / len(records)
    governing = sorted(records, key=lambda r: (r["coverage"], r["component"]))[0]
    list_outstanding = sorted(
        set(duty for record in records for duty in record["outstanding"])
    )

    findings = []
    for record in records:
        if record["category"] == "selection-closed":
            continue
        findings.append(
            {
                "severity": _CATEGORY_SEVERITY[record["category"]],
                "component": record["component"],
                "detail": "%s still owes %s"
                % (record["component"], ", ".join(record["outstanding"]))
                if record["outstanding"]
                else "%s is below the declared coverage floor" % record["component"],
            }
        )
    findings.sort(key=lambda item: (item["severity"], item["component"]))

    meets_floor = list_coverage > floor or math.isclose(
        list_coverage, floor, rel_tol=0.0, abs_tol=COVERAGE_TOLERANCE
    )
    if counts["selection-blocked"]:
        verdict = "selection-blocked"
    elif counts["selection-open"] or not meets_floor:
        verdict = "selection-open"
    else:
        verdict = "selection-closed"
    return {
        "records": records,
        "list_coverage": list_coverage,
        "floor": floor,
        "meets_floor": meets_floor,
        "category_counts": counts,
        "governing_component": governing,
        "outstanding_duties": tuple(list_outstanding),
        "findings": findings,
        "verdict": verdict,
    }
