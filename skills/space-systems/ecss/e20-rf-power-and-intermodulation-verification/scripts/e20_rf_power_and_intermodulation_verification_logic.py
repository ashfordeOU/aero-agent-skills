#!/usr/bin/env python3
"""RF power-handling and intermodulation verification logic (ECSS-E-ST-20C 7.5).

Deterministic, offline, stdlib-only helpers that:

* decide which verification-method is admissible for a given
  radio-frequency power-handling or intermodulation provision family,
* require a heritage reference and a bounded design-delta behind any
  similarity claim,
* check the demonstrated level against the qualification-margin that
  the declared method has to earn,
* place each item against its allocated review-gate, and
* check that a verification-plan and verification-report reference
  exist before a gate is declared passed.

The clause is cited as the anchor only; the procedure below is a
paraphrase, no normative text is reproduced.
"""

import math

# A demonstrated margin is the difference of two levels, so an exactly
# met requirement can land a few units in the last place low. The
# requirement itself is unchanged; only representation error is absorbed.
MARGIN_TOLERANCE_DB = 1e-9

PROVISION_FAMILIES = (
    "rf-power-handling",
    "multipactor",
    "corona",
    "passive-intermodulation",
)

VERIFICATION_METHODS = ("campaign", "analysis", "similarity", "review-of-design")

ADMISSIBLE_METHODS = {
    "rf-power-handling": ("campaign", "analysis", "similarity"),
    "multipactor": ("campaign", "analysis", "similarity"),
    "corona": ("campaign", "analysis"),
    "passive-intermodulation": ("campaign", "similarity"),
}

# Margin required of each family/method pairing. A method that observes
# the hardware carries the smaller value; an inferring method buys its
# uncertainty back in margin.
REQUIRED_MARGIN_DB = {
    ("rf-power-handling", "campaign"): 3.0,
    ("rf-power-handling", "analysis"): 6.0,
    ("rf-power-handling", "similarity"): 6.0,
    ("multipactor", "campaign"): 3.0,
    ("multipactor", "analysis"): 6.0,
    ("multipactor", "similarity"): 6.0,
    ("corona", "campaign"): 6.0,
    ("corona", "analysis"): 12.0,
    ("passive-intermodulation", "campaign"): 3.0,
    ("passive-intermodulation", "similarity"): 6.0,
}

REVIEW_GATES = ("pdr", "cdr", "qr", "ar")

DEFAULT_CLOSURE_GATE = {
    "rf-power-handling": "cdr",
    "multipactor": "qr",
    "corona": "qr",
    "passive-intermodulation": "qr",
}

ACCEPTED_DESIGN_DELTAS = ("none", "minor")
DESIGN_DELTAS = ("none", "minor", "major")


def _finite(value, label):
    """Return value as a float, rejecting non-numeric and non-finite input."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return out


def gate_index(gate):
    """Ordinal of a review-gate; raises on an unknown gate name."""
    if not isinstance(gate, str) or gate.strip().lower() not in REVIEW_GATES:
        raise ValueError(
            "review-gate %r unknown; expected one of %s" % (gate, list(REVIEW_GATES))
        )
    return REVIEW_GATES.index(gate.strip().lower())


def admissible_methods(provision_family):
    """Verification methods admissible for one provision family."""
    if provision_family not in ADMISSIBLE_METHODS:
        raise ValueError(
            "provision family %r unknown; expected one of %s"
            % (provision_family, list(PROVISION_FAMILIES))
        )
    return ADMISSIBLE_METHODS[provision_family]


def required_margin_db(provision_family, method):
    """Qualification-margin the family/method pairing has to demonstrate."""
    allowed = admissible_methods(provision_family)
    if method not in VERIFICATION_METHODS:
        raise ValueError(
            "verification-method %r unknown; expected one of %s"
            % (method, list(VERIFICATION_METHODS))
        )
    if method not in allowed:
        raise ValueError(
            "method %r is not admissible for %r (admissible: %s)"
            % (method, provision_family, list(allowed))
        )
    return REQUIRED_MARGIN_DB[(provision_family, method)]


def normalize_item(item):
    """Validate one verification provision item and fill its defaults."""
    if not isinstance(item, dict):
        raise ValueError("provision item must be a mapping, got %r" % (item,))
    iid = item.get("id")
    if not isinstance(iid, str) or not iid.strip():
        raise ValueError("provision item id must be a non-empty string, got %r" % (iid,))
    family = item.get("family")
    if family not in PROVISION_FAMILIES:
        raise ValueError(
            "item %s family %r unknown; expected one of %s"
            % (iid, family, list(PROVISION_FAMILIES))
        )
    method = item.get("method")
    if method not in VERIFICATION_METHODS:
        raise ValueError(
            "item %s verification-method %r unknown; expected one of %s"
            % (iid, method, list(VERIFICATION_METHODS))
        )
    nominal = _finite(item.get("nominal_dbm"), "item %s nominal_dbm" % iid)
    demonstrated = item.get("demonstrated_dbm")
    if demonstrated is not None:
        demonstrated = _finite(demonstrated, "item %s demonstrated_dbm" % iid)
    gate = item.get("closure_gate", DEFAULT_CLOSURE_GATE[family])
    gate_index(gate)
    delta = item.get("design_delta")
    if delta is not None and delta not in DESIGN_DELTAS:
        raise ValueError(
            "item %s design_delta %r unknown; expected one of %s"
            % (iid, delta, list(DESIGN_DELTAS))
        )
    override = item.get("required_margin_db")
    if override is not None:
        override = _finite(override, "item %s required_margin_db" % iid)
        if override < 0.0:
            raise ValueError(
                "item %s required_margin_db must be >= 0, got %r" % (iid, override)
            )
    heritage = item.get("heritage_reference")
    if heritage is not None and not isinstance(heritage, str):
        raise ValueError(
            "item %s heritage_reference must be a string, got %r" % (iid, heritage)
        )
    return {
        "id": iid.strip(),
        "family": family,
        "method": method,
        "nominal_dbm": nominal,
        "demonstrated_dbm": demonstrated,
        "closure_gate": gate.strip().lower(),
        "design_delta": delta,
        "required_margin_db": override,
        "heritage_reference": (heritage or "").strip(),
        "plan_ref": (item.get("plan_ref") or "").strip(),
        "report_ref": (item.get("report_ref") or "").strip(),
    }


def check_method_admissibility(item):
    """Findings raised by the declared method for this provision family."""
    entry = normalize_item(item)
    findings = []
    allowed = admissible_methods(entry["family"])
    if entry["method"] not in allowed:
        findings.append(
            "%s: method %s is not admissible for %s (admissible: %s)"
            % (entry["id"], entry["method"], entry["family"], ", ".join(allowed))
        )
        return findings
    if entry["method"] == "similarity":
        if not entry["heritage_reference"]:
            findings.append(
                "%s: similarity claim carries no heritage reference" % entry["id"]
            )
        if entry["design_delta"] is None:
            findings.append(
                "%s: similarity claim carries no design-delta record" % entry["id"]
            )
        elif entry["design_delta"] not in ACCEPTED_DESIGN_DELTAS:
            findings.append(
                "%s: design-delta %s is beyond minor, similarity is not admissible"
                % (entry["id"], entry["design_delta"])
            )
    return findings


def check_margin(item):
    """Demonstrated margin against the margin the method has to earn."""
    entry = normalize_item(item)
    allowed = admissible_methods(entry["family"])
    if entry["method"] not in allowed:
        raise ValueError(
            "item %s: margin cannot be judged, method %s is inadmissible for %s"
            % (entry["id"], entry["method"], entry["family"])
        )
    baseline = required_margin_db(entry["family"], entry["method"])
    required = baseline if entry["required_margin_db"] is None else max(
        baseline, entry["required_margin_db"]
    )
    if entry["demonstrated_dbm"] is None:
        return {
            "id": entry["id"],
            "required_margin_db": required,
            "achieved_margin_db": None,
            "shortfall_db": None,
            "evidence": False,
            "compliant": False,
        }
    achieved = entry["demonstrated_dbm"] - entry["nominal_dbm"]
    compliant = achieved >= required - MARGIN_TOLERANCE_DB
    return {
        "id": entry["id"],
        "required_margin_db": required,
        "achieved_margin_db": achieved,
        "shortfall_db": 0.0 if compliant else required - achieved,
        "evidence": True,
        "compliant": compliant,
    }


def check_gate_closure(item, current_gate):
    """Closure status of one item against the gate the programme has reached."""
    entry = normalize_item(item)
    reached = gate_index(current_gate)
    allocated = gate_index(entry["closure_gate"])
    if entry["demonstrated_dbm"] is not None:
        status = "closed"
    elif allocated > reached:
        status = "open"
    else:
        status = "overdue"
    return {
        "id": entry["id"],
        "closure_gate": entry["closure_gate"],
        "current_gate": REVIEW_GATES[reached],
        "status": status,
    }


def check_documentation(item):
    """Plan and report reference findings for one item."""
    entry = normalize_item(item)
    findings = []
    if not entry["plan_ref"]:
        findings.append("%s: no verification-plan reference on record" % entry["id"])
    if entry["demonstrated_dbm"] is not None and not entry["report_ref"]:
        findings.append(
            "%s: evidence claimed with no verification-report reference" % entry["id"]
        )
    return findings


def evaluate_item(item, current_gate):
    """Aggregate the admissibility, margin, gate and documentation checks."""
    entry = normalize_item(item)
    findings = list(check_method_admissibility(entry))
    admissible = entry["method"] in admissible_methods(entry["family"])
    margin = check_margin(entry) if admissible else None
    if margin is not None and margin["evidence"] and not margin["compliant"]:
        findings.append(
            "%s: demonstrated margin %.3f dB is short of the required %.3f dB"
            % (entry["id"], margin["achieved_margin_db"], margin["required_margin_db"])
        )
    closure = check_gate_closure(entry, current_gate)
    if closure["status"] == "overdue":
        findings.append(
            "%s: allocated to %s with no evidence; that gate is reached"
            % (entry["id"], closure["closure_gate"].upper())
        )
    findings.extend(check_documentation(entry))
    return {
        "id": entry["id"],
        "family": entry["family"],
        "method": entry["method"],
        "margin": margin,
        "closure": closure,
        "findings": findings,
        "compliant": not findings,
    }


def assess_rf_power_and_intermodulation_verification(items, current_gate):
    """Top-level clause 7.5 close-out assessment for one review-gate."""
    if not isinstance(items, (list, tuple)):
        raise ValueError("items must be a list, got %r" % (items,))
    if not items:
        raise ValueError("items must not be empty; nothing to close out")
    gate_index(current_gate)
    seen = set()
    evaluated = []
    for raw in items:
        result = evaluate_item(raw, current_gate)
        if result["id"] in seen:
            raise ValueError("duplicate provision item id %r" % result["id"])
        seen.add(result["id"])
        evaluated.append(result)
    findings = [f for result in evaluated for f in result["findings"]]
    closed = [r for r in evaluated if r["closure"]["status"] == "closed"]
    overdue = [r for r in evaluated if r["closure"]["status"] == "overdue"]
    return {
        "current_gate": current_gate.strip().lower(),
        "item_count": len(evaluated),
        "items": evaluated,
        "closed_count": len(closed),
        "overdue_count": len(overdue),
        "closure_fraction": len(closed) / float(len(evaluated)),
        "findings": findings,
        "gate_passable": not findings,
    }
