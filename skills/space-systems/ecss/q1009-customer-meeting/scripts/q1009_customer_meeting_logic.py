"""Customer review board processing of a submitted major nonconformance.

Anchor: ECSS-Q-ST-10-09 clauses 5.2.3.1 to 5.2.3.3 (the customer board meets on
a submitted departure, assesses the impacts the supplier could not see from
inside its own scope, and confirms the causes and consequences with the
supplier before any disposition is taken). Paraphrased into an implementable
procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Convene the board: the customer functions that have to sit, and the
   supplier representative who has to be there for the confirmation step. The
   two are reported separately because a board can be properly constituted and
   still unable to confirm anything.
2. Assess the higher-level impacts the supplier's own analysis cannot reach:
   the share of a system-level budget the departure consumes, every interface
   parameter against the range the interface document agreed, and the schedule
   slip against the float the activity actually holds.
3. Confirm causes and consequences with the supplier. Each submitted statement
   comes back confirmed, disputed or still open, and a disputed statement is
   an action on somebody, not a rounding error in the minutes.
4. Decide what the sitting can produce. A disposition may only be taken by a
   quorate board that has assessed every impact dimension and holds no
   unconfirmed statement; anything short of that is a named deferral with the
   reason attached, so the next sitting knows what it is waiting for.
"""

import math

__all__ = [
    "IMPACT_TOLERANCE",
    "MANDATORY_CUSTOMER_FUNCTIONS",
    "SUPPLIER_FUNCTION",
    "IMPACT_DIMENSIONS",
    "CONFIRMATION_STATES",
    "normalize_token",
    "validate_attendance",
    "convening_status",
    "budget_impact",
    "interface_impact",
    "schedule_impact",
    "assess_higher_level_impacts",
    "confirmation_status",
    "assess_customer_meeting",
]

# Budget shares and interface bounds are float comparisons that a value sitting
# exactly on its limit can land either side of. Absorb that here rather than
# widening the agreed limit.
IMPACT_TOLERANCE = 1e-9

# The customer side that has to sit for the board to be constituted.
MANDATORY_CUSTOMER_FUNCTIONS = (
    "customer-chair",
    "customer-engineering",
    "customer-product-assurance",
)

# The supplier side that has to be there for anything to be confirmed.
SUPPLIER_FUNCTION = "supplier-representative"

# The impact dimensions the customer board owns because the supplier cannot see
# them from inside its own scope.
IMPACT_DIMENSIONS = ("system-budget", "interfaces", "schedule")

CONFIRMATION_STATES = ("confirmed", "disputed", "open")

_CONFIRMATION_SET = frozenset(CONFIRMATION_STATES)


def normalize_token(value, label="token"):
    """Return a token in canonical hyphen form."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    text = " ".join(value.strip().lower().split())
    if not text:
        raise ValueError("%s must not be empty or whitespace only" % label)
    return text.replace(" ", "-").replace("_", "-")


def _finite(value, label):
    """Return a finite real number."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return number


def validate_attendance(members):
    """Return the validated attendance list for the sitting."""
    if not isinstance(members, (list, tuple)) or not members:
        raise ValueError("attendance must be a non-empty sequence of members")
    seen = set()
    roster = []
    for entry in members:
        if not isinstance(entry, dict):
            raise ValueError("attendance entry must be a mapping, got %r" % (entry,))
        for key in ("function", "present"):
            if key not in entry:
                raise ValueError("attendance entry missing required key '%s'" % key)
        function = normalize_token(entry["function"], "function")
        if function in seen:
            raise ValueError("function '%s' listed more than once" % function)
        seen.add(function)
        if not isinstance(entry["present"], bool):
            raise ValueError("function '%s' presence must be a boolean" % function)
        roster.append({"function": function, "present": entry["present"]})
    return roster


def convening_status(members):
    """Return whether the board is constituted and whether it can confirm."""
    roster = validate_attendance(members)
    present = {r["function"] for r in roster if r["present"]}
    absent = tuple(f for f in MANDATORY_CUSTOMER_FUNCTIONS if f not in present)
    supplier_present = SUPPLIER_FUNCTION in present
    return {
        "absent_customer_functions": absent,
        "quorate": not absent,
        "supplier_present": supplier_present,
        "confirmation_possible": supplier_present,
    }


def budget_impact(consumed, allocated):
    """Return the share of a system-level budget the departure consumes."""
    used = _finite(consumed, "consumed")
    total = _finite(allocated, "allocated")
    if total <= 0.0:
        raise ValueError("allocated budget must be positive, got %r" % (allocated,))
    if used < 0.0:
        raise ValueError("consumed budget must not be negative, got %r" % (consumed,))
    share = used / total
    exceeded = share > 1.0 and not math.isclose(
        share, 1.0, rel_tol=0.0, abs_tol=IMPACT_TOLERANCE
    )
    return {
        "consumed": used,
        "allocated": total,
        "share": share,
        "exceeded": exceeded,
    }


def interface_impact(parameters):
    """Return the interface parameters that fall outside their agreed range."""
    if not isinstance(parameters, (list, tuple)) or not parameters:
        raise ValueError("parameters must be a non-empty sequence")
    records = []
    seen = set()
    for entry in parameters:
        if not isinstance(entry, dict):
            raise ValueError("interface parameter must be a mapping, got %r" % (entry,))
        for key in ("name", "value", "lower", "upper"):
            if key not in entry:
                raise ValueError("interface parameter missing required key '%s'" % key)
        name = normalize_token(entry["name"], "parameter name")
        if name in seen:
            raise ValueError("interface parameter '%s' listed more than once" % name)
        seen.add(name)
        value = _finite(entry["value"], "value")
        lower = _finite(entry["lower"], "lower")
        upper = _finite(entry["upper"], "upper")
        if lower > upper:
            raise ValueError(
                "interface parameter '%s' has an inverted range [%g, %g]" % (name, lower, upper)
            )
        below = value < lower and not math.isclose(
            value, lower, rel_tol=0.0, abs_tol=IMPACT_TOLERANCE
        )
        above = value > upper and not math.isclose(
            value, upper, rel_tol=0.0, abs_tol=IMPACT_TOLERANCE
        )
        records.append(
            {
                "name": name,
                "value": value,
                "lower": lower,
                "upper": upper,
                "conforming": not (below or above),
            }
        )
    return {
        "parameters": records,
        "non_conforming": tuple(r["name"] for r in records if not r["conforming"]),
        "conforming": all(r["conforming"] for r in records),
    }


def schedule_impact(slip_days, float_days):
    """Return what the slip does to the activity's float and to the critical path."""
    for label, value in (("slip_days", slip_days), ("float_days", float_days)):
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError("%s must be an integer, got %r" % (label, value))
        if value < 0:
            raise ValueError("%s must not be negative, got %d" % (label, value))
    remaining = float_days - slip_days
    return {
        "slip_days": slip_days,
        "float_days": float_days,
        "float_remaining": remaining,
        "float_exhausted": remaining <= 0,
        "critical_path_impact": remaining < 0,
        "delay_days": -remaining if remaining < 0 else 0,
    }


def assess_higher_level_impacts(impacts):
    """Assess every higher-level dimension the customer board owns."""
    if not isinstance(impacts, dict):
        raise ValueError("impacts must be a mapping of dimension to inputs")
    missing = [d for d in IMPACT_DIMENSIONS if d not in impacts]
    if missing:
        raise ValueError("impact dimensions left unassessed: %s" % ", ".join(missing))
    unknown = [d for d in impacts if d not in IMPACT_DIMENSIONS]
    if unknown:
        raise ValueError("unknown impact dimension(s): %s" % ", ".join(sorted(unknown)))
    budget_inputs = impacts["system-budget"]
    if not isinstance(budget_inputs, dict):
        raise ValueError("system-budget inputs must be a mapping")
    for key in ("consumed", "allocated"):
        if key not in budget_inputs:
            raise ValueError("system-budget inputs missing '%s'" % key)
    schedule_inputs = impacts["schedule"]
    if not isinstance(schedule_inputs, dict):
        raise ValueError("schedule inputs must be a mapping")
    for key in ("slip_days", "float_days"):
        if key not in schedule_inputs:
            raise ValueError("schedule inputs missing '%s'" % key)
    budget = budget_impact(budget_inputs["consumed"], budget_inputs["allocated"])
    interfaces = interface_impact(impacts["interfaces"])
    schedule = schedule_impact(schedule_inputs["slip_days"], schedule_inputs["float_days"])
    findings = []
    if budget["exceeded"]:
        findings.append(
            "system budget consumed to %.4f of its allocation" % budget["share"]
        )
    for name in interfaces["non_conforming"]:
        findings.append("interface parameter '%s' outside its agreed range" % name)
    if schedule["critical_path_impact"]:
        findings.append(
            "slip exceeds the activity float by %d day(s)" % schedule["delay_days"]
        )
    elif schedule["float_exhausted"]:
        findings.append("slip consumes the whole activity float")
    return {
        "system-budget": budget,
        "interfaces": interfaces,
        "schedule": schedule,
        "findings": findings,
        "acceptable": not budget["exceeded"]
        and interfaces["conforming"]
        and not schedule["critical_path_impact"],
    }


def confirmation_status(statements, supplier_present):
    """Return the confirmation state of the submitted causes and consequences."""
    if not isinstance(supplier_present, bool):
        raise ValueError("supplier_present must be a boolean, got %r" % (supplier_present,))
    if not isinstance(statements, (list, tuple)) or not statements:
        raise ValueError("statements must be a non-empty sequence")
    seen = set()
    records = []
    for entry in statements:
        if not isinstance(entry, dict):
            raise ValueError("statement must be a mapping, got %r" % (entry,))
        for key in ("id", "kind", "state"):
            if key not in entry:
                raise ValueError("statement missing required key '%s'" % key)
        ident = normalize_token(entry["id"], "statement id")
        if ident in seen:
            raise ValueError("statement '%s' listed more than once" % ident)
        seen.add(ident)
        kind = normalize_token(entry["kind"], "statement kind")
        if kind not in ("cause", "consequence"):
            raise ValueError("statement kind must be 'cause' or 'consequence', got '%s'" % kind)
        state = normalize_token(entry["state"], "statement state")
        if state not in _CONFIRMATION_SET:
            raise ValueError("unknown confirmation state '%s'" % state)
        records.append({"id": ident, "kind": kind, "state": state})
    disputed = tuple(r["id"] for r in records if r["state"] == "disputed")
    still_open = tuple(r["id"] for r in records if r["state"] == "open")
    if not supplier_present:
        # Nothing can be confirmed against an empty chair, whatever the
        # submission said; every statement reverts to open for this sitting.
        return {
            "statements": records,
            "disputed": disputed,
            "open": tuple(r["id"] for r in records),
            "all_confirmed": False,
            "blocked_by": "supplier-not-present",
        }
    all_confirmed = not disputed and not still_open
    return {
        "statements": records,
        "disputed": disputed,
        "open": still_open,
        "all_confirmed": all_confirmed,
        "blocked_by": None if all_confirmed else "unconfirmed-statements",
    }


def assess_customer_meeting(spec):
    """Run the full clause 5.2.3 customer-board sitting assessment.

    spec keys: attendance, impacts, statements.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("attendance", "impacts", "statements"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    convening = convening_status(spec["attendance"])
    impacts = assess_higher_level_impacts(spec["impacts"])
    confirmation = confirmation_status(spec["statements"], convening["supplier_present"])
    findings = []
    for function in convening["absent_customer_functions"]:
        findings.append("mandatory customer function '%s' not sitting" % function)
    if not convening["supplier_present"]:
        findings.append(
            "supplier representative absent; causes and consequences cannot be confirmed"
        )
    findings.extend(impacts["findings"])
    for ident in confirmation["disputed"]:
        findings.append("statement '%s' disputed by the supplier" % ident)
    for ident in confirmation["open"]:
        if ident not in confirmation["disputed"]:
            findings.append("statement '%s' left open" % ident)
    if not convening["quorate"]:
        outcome = "not-quorate"
    elif not confirmation["all_confirmed"]:
        outcome = "deferred-pending-confirmation"
    else:
        outcome = "disposition-decidable"
    return {
        "convening": convening,
        "impacts": impacts,
        "confirmation": confirmation,
        "findings": findings,
        "outcome": outcome,
        "disposition_decidable": outcome == "disposition-decidable",
        "impacts_acceptable": impacts["acceptable"],
    }
