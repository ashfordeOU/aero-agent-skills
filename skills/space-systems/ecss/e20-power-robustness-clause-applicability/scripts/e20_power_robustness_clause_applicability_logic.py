#!/usr/bin/env python3
"""ECSS-E-ST-20C clause 5.7.1 -- robustness provision applicability.

Deterministic, offline, stdlib-only support logic for the scoping question
clause 5.7.1 opens the robustness chapter with: a given robustness provision
may be addressed to the power subsystem, to the payload, or to both of them
together, and the elements under assessment have to be matched against that
scope before any robustness number is argued.

Implemented engineering:

* element-role categorization -- a payload that conditions its own power is
  not the same scoping case as a payload that only draws from the bus;
* applicability resolution -- provision scope crossed with element role gives
  applicable, applicable-via-interface (the element only meets the provision
  where it presents the power/payload interface), or not-applicable;
* governing threshold -- where a provision reaches both sides, the threshold
  that governs the shared interface is the strictest demand on either side,
  not the provision's own floor;
* margin checking -- demonstrated capability against the governing threshold,
  with missing evidence kept distinct from a failed margin;
* scoping hygiene -- a not-applicable pair must carry a recorded rationale,
  otherwise the exclusion is untraceable.

No verbatim standard text is reproduced; clause 5.7.1 is the anchor only.
"""

ELEMENT_ROLES = (
    "power-subsystem",
    "payload",
    "payload-with-power-conditioning",
)

PROVISION_SCOPES = ("power-subsystem", "payload", "both")

ROBUSTNESS_PARAMETERS = (
    "bus-overvoltage-withstand-v",
    "bus-undervoltage-ride-through-v",
    "inrush-current-limit-a",
    "fault-clearing-time-ms",
    "reverse-polarity-withstand-v",
)

APPLICABLE = "applicable"
VIA_INTERFACE = "applicable-via-interface"
NOT_APPLICABLE = "not-applicable"

_REQUIRED_PROVISION_KEYS = ("provision_id", "scope", "parameter", "required_withstand")
_REQUIRED_ELEMENT_KEYS = (
    "element_id",
    "role",
    "presents_power_payload_interface",
    "demonstrated",
    "interface_demand",
)


def _as_float(value, field):
    """Coerce a numeric field, rejecting bools and non-numbers."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("field %r must be a real number, got %r" % (field, value))
    return float(value)


def _as_param_map(value, field):
    """Validate a parameter -> value mapping."""
    if not isinstance(value, dict):
        raise ValueError("field %r must be a mapping of parameter to value" % field)
    out = {}
    for key, raw in value.items():
        if key not in ROBUSTNESS_PARAMETERS:
            raise ValueError(
                "unknown robustness parameter %r in %r; expected one of %s"
                % (key, field, ", ".join(ROBUSTNESS_PARAMETERS))
            )
        number = _as_float(raw, "%s[%s]" % (field, key))
        if number < 0.0:
            raise ValueError("%s[%s] must be >= 0, got %g" % (field, key, number))
        out[key] = number
    return out


def validate_provision(provision):
    """Return a normalized robustness provision or raise ValueError."""
    if not isinstance(provision, dict):
        raise ValueError(
            "provision must be a mapping, got %r" % type(provision).__name__
        )
    missing = [k for k in _REQUIRED_PROVISION_KEYS if k not in provision]
    if missing:
        raise ValueError(
            "provision missing required field(s): %s" % ", ".join(sorted(missing))
        )
    provision_id = provision["provision_id"]
    if not isinstance(provision_id, str) or not provision_id.strip():
        raise ValueError("provision_id must be a non-empty string")
    scope = provision["scope"]
    if scope not in PROVISION_SCOPES:
        raise ValueError(
            "unknown provision scope %r; expected one of %s"
            % (scope, ", ".join(PROVISION_SCOPES))
        )
    parameter = provision["parameter"]
    if parameter not in ROBUSTNESS_PARAMETERS:
        raise ValueError(
            "unknown robustness parameter %r; expected one of %s"
            % (parameter, ", ".join(ROBUSTNESS_PARAMETERS))
        )
    required = _as_float(provision["required_withstand"], "required_withstand")
    if required <= 0.0:
        raise ValueError("required_withstand must be > 0, got %g" % required)
    return {
        "provision_id": provision_id.strip(),
        "scope": scope,
        "parameter": parameter,
        "required_withstand": required,
    }


def validate_element(element):
    """Return a normalized element under assessment or raise ValueError."""
    if not isinstance(element, dict):
        raise ValueError("element must be a mapping, got %r" % type(element).__name__)
    missing = [k for k in _REQUIRED_ELEMENT_KEYS if k not in element]
    if missing:
        raise ValueError(
            "element missing required field(s): %s" % ", ".join(sorted(missing))
        )
    element_id = element["element_id"]
    if not isinstance(element_id, str) or not element_id.strip():
        raise ValueError("element_id must be a non-empty string")
    role = element["role"]
    if role not in ELEMENT_ROLES:
        raise ValueError(
            "unknown element role %r; expected one of %s"
            % (role, ", ".join(ELEMENT_ROLES))
        )
    presents = element["presents_power_payload_interface"]
    if not isinstance(presents, bool):
        raise ValueError("presents_power_payload_interface must be a boolean")
    return {
        "element_id": element_id.strip(),
        "role": role,
        "presents_power_payload_interface": presents,
        "demonstrated": _as_param_map(element["demonstrated"], "demonstrated"),
        "interface_demand": _as_param_map(
            element["interface_demand"], "interface_demand"
        ),
    }


def categorize_element_role(element):
    """Return the canonical scoping role of an element."""
    return validate_element(element)["role"]


def resolve_applicability(provision, element):
    """Resolve how a robustness provision reaches one element."""
    prov = validate_provision(provision)
    elem = validate_element(element)
    scope = prov["scope"]
    role = elem["role"]
    if scope == "both":
        return APPLICABLE
    if role == "payload-with-power-conditioning":
        return APPLICABLE
    if scope == "power-subsystem":
        if role == "power-subsystem":
            return APPLICABLE
        return VIA_INTERFACE if elem["presents_power_payload_interface"] else NOT_APPLICABLE
    # scope == "payload"
    if role == "payload":
        return APPLICABLE
    return VIA_INTERFACE if elem["presents_power_payload_interface"] else NOT_APPLICABLE


def governing_threshold(provision, elements):
    """Strictest threshold that governs the provision across its scope.

    The provision's own figure is a floor; where an element on either side of
    the interface demands more, that demand governs instead.
    """
    prov = validate_provision(provision)
    if not isinstance(elements, (list, tuple)) or not elements:
        raise ValueError("elements must be a non-empty list of element records")
    governing = prov["required_withstand"]
    reached = 0
    for element in elements:
        state = resolve_applicability(prov, element)
        if state == NOT_APPLICABLE:
            continue
        reached += 1
        demand = validate_element(element)["interface_demand"].get(prov["parameter"])
        if demand is not None and demand > governing:
            governing = demand
    if reached == 0:
        raise ValueError(
            "provision %r reaches no element in the assessed set" % prov["provision_id"]
        )
    return governing


def check_margin(provision, element, governing):
    """Grade one element against the governing threshold."""
    prov = validate_provision(provision)
    elem = validate_element(element)
    threshold = _as_float(governing, "governing")
    if threshold <= 0.0:
        raise ValueError("governing threshold must be > 0, got %g" % threshold)
    shown = elem["demonstrated"].get(prov["parameter"])
    if shown is None:
        return {"verdict": "evidence-missing", "margin_pct": None, "demonstrated": None}
    margin = (shown - threshold) / threshold * 100.0
    return {
        "verdict": "pass" if shown >= threshold else "fail",
        "margin_pct": margin,
        "demonstrated": shown,
    }


def justification_finding(provision, element, justifications):
    """Return a finding when a not-applicable pair carries no rationale."""
    prov = validate_provision(provision)
    elem = validate_element(element)
    if not isinstance(justifications, dict):
        raise ValueError("justifications must be a mapping of 'provision/element' keys")
    key = "%s/%s" % (prov["provision_id"], elem["element_id"])
    text = justifications.get(key)
    if isinstance(text, str) and text.strip():
        return None
    return "not-applicable-without-rationale:%s" % key


def build_applicability_matrix(provisions, elements):
    """Resolve every provision/element pair once, rejecting duplicate ids."""
    if not isinstance(provisions, (list, tuple)) or not provisions:
        raise ValueError("provisions must be a non-empty list")
    if not isinstance(elements, (list, tuple)) or not elements:
        raise ValueError("elements must be a non-empty list")
    normalized_provisions = []
    seen = set()
    for provision in provisions:
        prov = validate_provision(provision)
        if prov["provision_id"] in seen:
            raise ValueError("duplicate provision_id %r" % prov["provision_id"])
        seen.add(prov["provision_id"])
        normalized_provisions.append(prov)
    normalized_elements = []
    seen = set()
    for element in elements:
        elem = validate_element(element)
        if elem["element_id"] in seen:
            raise ValueError("duplicate element_id %r" % elem["element_id"])
        seen.add(elem["element_id"])
        normalized_elements.append(elem)
    rows = []
    for prov in normalized_provisions:
        for elem in normalized_elements:
            rows.append(
                {
                    "provision_id": prov["provision_id"],
                    "element_id": elem["element_id"],
                    "scope": prov["scope"],
                    "role": elem["role"],
                    "parameter": prov["parameter"],
                    "applicability": resolve_applicability(prov, elem),
                }
            )
    return rows


def assess_robustness_applicability(provisions, elements, justifications=None):
    """Full clause 5.7.1 scoping assessment across provisions and elements."""
    justifications = {} if justifications is None else justifications
    if not isinstance(justifications, dict):
        raise ValueError("justifications must be a mapping of 'provision/element' keys")
    rows = build_applicability_matrix(provisions, elements)
    by_element = {validate_element(e)["element_id"]: e for e in elements}
    by_provision = {validate_provision(p)["provision_id"]: p for p in provisions}
    findings = []
    graded = 0
    passed = 0
    for row in rows:
        provision = by_provision[row["provision_id"]]
        element = by_element[row["element_id"]]
        if row["applicability"] == NOT_APPLICABLE:
            finding = justification_finding(provision, element, justifications)
            if finding is not None:
                findings.append(finding)
            row["verdict"] = NOT_APPLICABLE
            row["margin_pct"] = None
            continue
        threshold = governing_threshold(provision, elements)
        result = check_margin(provision, element, threshold)
        row["governing_threshold"] = threshold
        row["verdict"] = result["verdict"]
        row["margin_pct"] = result["margin_pct"]
        graded += 1
        if result["verdict"] == "pass":
            passed += 1
        else:
            findings.append(
                "%s:%s/%s" % (result["verdict"], row["provision_id"], row["element_id"])
            )
    coverage = (passed / graded) if graded else 0.0
    return {
        "rows": rows,
        "applicable_pairs": graded,
        "passing_pairs": passed,
        "coverage_fraction": coverage,
        "findings": tuple(findings),
        "scoping_closed": not findings,
    }


if __name__ == "__main__":  # pragma: no cover - manual smoke run
    provisions = [
        {
            "provision_id": "ROB-01",
            "scope": "both",
            "parameter": "bus-overvoltage-withstand-v",
            "required_withstand": 40.0,
        }
    ]
    elements = [
        {
            "element_id": "PCDU",
            "role": "power-subsystem",
            "presents_power_payload_interface": True,
            "demonstrated": {"bus-overvoltage-withstand-v": 50.0},
            "interface_demand": {"bus-overvoltage-withstand-v": 45.0},
        },
        {
            "element_id": "INSTR-A",
            "role": "payload",
            "presents_power_payload_interface": True,
            "demonstrated": {"bus-overvoltage-withstand-v": 46.0},
            "interface_demand": {},
        },
    ]
    out = assess_robustness_applicability(provisions, elements)
    for key in sorted(out):
        if key != "rows":
            print("%-22s %s" % (key, out[key]))
