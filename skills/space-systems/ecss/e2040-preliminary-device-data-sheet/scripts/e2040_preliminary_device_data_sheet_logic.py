#!/usr/bin/env python3
"""Preliminary device data sheet (ECSS-E-ST-20-40C clause 5.4.5).

Offline, deterministic, standard library only. The ECSS clause is cited as
the anchor; the procedure below is a paraphrase into implementable logic.

Model
-----
The clause puts an early summary of device characteristics in front of
readers outside the development. They cannot ask what a figure meant, so
every entry has to stand on its own line:

* a numeric figure carries a unit. A dimensionless figure carries the
  unit 1, so an absent unit always means an omission rather than a
  quantity that happens to have none;
* the sheet declares its own ranges, so a figure can be checked without
  any outside source. A figure landing exactly on a declared bound is
  inside it, because the bound is the commitment and the comparison has
  to absorb representation error;
* maturity has to match the basis. A figure called confirmed while it
  rests on an estimate or a simulation invites the reader to design
  against it, and that statement cannot be withdrawn later;
* a mandatory group left empty is a gap, never nothing to say. The
  reader cannot tell an absent limit from an unwritten section.
"""

import math

FUNCTIONAL = "functional"
ELECTRICAL = "electrical"
TIMING = "timing"
PHYSICAL = "physical"
ENVIRONMENTAL = "environmental"
CHARACTERISTIC_GROUPS = (FUNCTIONAL, ELECTRICAL, TIMING, PHYSICAL, ENVIRONMENTAL)
MANDATORY_GROUPS = (FUNCTIONAL, ELECTRICAL, TIMING, ENVIRONMENTAL)
_GROUP_ALIASES = {
    "functional": FUNCTIONAL,
    "function": FUNCTIONAL,
    "functions": FUNCTIONAL,
    "electrical": ELECTRICAL,
    "electric": ELECTRICAL,
    "power": ELECTRICAL,
    "timing": TIMING,
    "time": TIMING,
    "performance": TIMING,
    "physical": PHYSICAL,
    "mechanical": PHYSICAL,
    "package": PHYSICAL,
    "environmental": ENVIRONMENTAL,
    "environment": ENVIRONMENTAL,
    "radiation": ENVIRONMENTAL,
}

PRELIMINARY = "preliminary"
CONFIRMED = "confirmed"
MATURITIES = (PRELIMINARY, CONFIRMED)
_MATURITY_ALIASES = {
    "preliminary": PRELIMINARY,
    "provisional": PRELIMINARY,
    "target": PRELIMINARY,
    "tbc": PRELIMINARY,
    "confirmed": CONFIRMED,
    "final": CONFIRMED,
    "verified": CONFIRMED,
}

ESTIMATE = "estimate"
SIMULATION = "simulation"
ANALYSIS = "analysis"
MEASUREMENT = "measurement"
BASES = (ESTIMATE, SIMULATION, ANALYSIS, MEASUREMENT)
# A confirmed figure may only rest on these.
CONFIRMING_BASES = (MEASUREMENT,)
_BASIS_ALIASES = {
    "estimate": ESTIMATE,
    "estimated": ESTIMATE,
    "engineering judgement": ESTIMATE,
    "simulation": SIMULATION,
    "simulated": SIMULATION,
    "model": SIMULATION,
    "analysis": ANALYSIS,
    "calculation": ANALYSIS,
    "measurement": MEASUREMENT,
    "measured": MEASUREMENT,
    "test": MEASUREMENT,
}

DIMENSIONLESS_UNIT = "1"

REL_TOL = 1e-12
ABS_TOL = 1e-18

_CHARACTERISTIC_KEYS = (
    "name",
    "group",
    "value",
    "unit",
    "minimum",
    "maximum",
    "maturity",
    "basis",
    "description",
)
_SHEET_REQUIRED_KEYS = ("characteristics",)
_SHEET_OPTIONAL_KEYS = ("completeness_threshold",)


def _text(name, value, allow_empty=False):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (name, value))
    out = value.strip()
    if not out and not allow_empty:
        raise ValueError("%s must be a non-empty string" % name)
    return out


def _real(name, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (name, value))
    out = float(value)
    if math.isnan(out) or math.isinf(out):
        raise ValueError("%s must be finite, got %r" % (name, value))
    return out


def _fraction(name, value):
    out = _real(name, value)
    if not 0.0 <= out <= 1.0:
        raise ValueError("%s must lie in [0, 1], got %g" % (name, out))
    return out


def meets_completeness_threshold(achieved, threshold):
    """True when achieved completeness reaches the threshold, exact landings included."""
    achieved = _fraction("achieved", achieved)
    threshold = _fraction("threshold", threshold)
    return achieved > threshold or math.isclose(
        achieved, threshold, rel_tol=REL_TOL, abs_tol=ABS_TOL
    )


def normalize_group(value):
    """Fold a characteristic group spelling onto a recognised group."""
    key = " ".join(_text("group", value).lower().replace("_", " ").split())
    if key in _GROUP_ALIASES:
        return _GROUP_ALIASES[key]
    raise ValueError(
        "unknown characteristic group %r; use one of %s"
        % (value, ", ".join(CHARACTERISTIC_GROUPS))
    )


def normalize_maturity(value):
    """Fold a maturity spelling onto preliminary or confirmed."""
    key = " ".join(_text("maturity", value).lower().replace("_", " ").split())
    if key in _MATURITY_ALIASES:
        return _MATURITY_ALIASES[key]
    raise ValueError(
        "unknown maturity %r; use one of %s" % (value, ", ".join(MATURITIES))
    )


def normalize_basis(value):
    """Fold the basis of a figure onto a recognised one."""
    key = " ".join(_text("basis", value).lower().replace("_", " ").split())
    if key in _BASIS_ALIASES:
        return _BASIS_ALIASES[key]
    raise ValueError("unknown basis %r; use one of %s" % (value, ", ".join(BASES)))


def basis_supports_confirmation(basis):
    """True when a figure resting on this basis may be called confirmed."""
    return normalize_basis(basis) in CONFIRMING_BASES


def within_declared_range(value, minimum=None, maximum=None):
    """True when the figure lies inside its declared range, bounds included.

    A value landing exactly on a bound is inside it: the bound is the
    commitment, so representation error in a computed figure must not push
    a compliant value outside.
    """
    figure = _real("value", value)
    if minimum is not None:
        low = _real("minimum", minimum)
        if figure < low and not math.isclose(
            figure, low, rel_tol=REL_TOL, abs_tol=ABS_TOL
        ):
            return False
    if maximum is not None:
        high = _real("maximum", maximum)
        if figure > high and not math.isclose(
            figure, high, rel_tol=REL_TOL, abs_tol=ABS_TOL
        ):
            return False
    return True


def validate_characteristics(records):
    """Check the characteristic list and return it resolved in declared order."""
    if not isinstance(records, (list, tuple)):
        raise ValueError("characteristics must be a list")
    resolved = []
    seen = set()
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise ValueError("characteristics[%d] must be a mapping" % index)
        unknown = sorted(set(record) - set(_CHARACTERISTIC_KEYS))
        if unknown:
            raise ValueError(
                "characteristics[%d] has unknown keys: %s" % (index, ", ".join(unknown))
            )
        for key in ("name", "group"):
            if key not in record:
                raise ValueError("characteristics[%d] missing key: %s" % (index, key))
        name = _text("characteristics[%d].name" % index, record["name"])
        if name in seen:
            raise ValueError("duplicate characteristic name %r" % name)
        seen.add(name)
        raw_value = record.get("value", "")
        if isinstance(raw_value, bool):
            raise ValueError("characteristics[%d].value must be a number or text" % index)
        if isinstance(raw_value, (int, float)):
            value = _real("characteristics[%d].value" % index, raw_value)
            numeric = True
        else:
            value = _text(
                "characteristics[%d].value" % index, raw_value, allow_empty=True
            )
            numeric = False
        minimum = record.get("minimum")
        maximum = record.get("maximum")
        if minimum is not None:
            minimum = _real("characteristics[%d].minimum" % index, minimum)
        if maximum is not None:
            maximum = _real("characteristics[%d].maximum" % index, maximum)
        if minimum is not None and maximum is not None and minimum > maximum:
            raise ValueError(
                "characteristic %r declares a range whose minimum %g exceeds its "
                "maximum %g" % (name, minimum, maximum)
            )
        if not numeric and (minimum is not None or maximum is not None):
            raise ValueError(
                "characteristic %r declares a range on a value that is not numeric"
                % name
            )
        resolved.append(
            {
                "name": name,
                "group": normalize_group(record["group"]),
                "value": value,
                "numeric": numeric,
                "unit": _text(
                    "characteristics[%d].unit" % index,
                    record.get("unit", ""),
                    allow_empty=True,
                ),
                "minimum": minimum,
                "maximum": maximum,
                "maturity": normalize_maturity(record.get("maturity", PRELIMINARY)),
                "basis": normalize_basis(record.get("basis", ESTIMATE)),
                "description": _text(
                    "characteristics[%d].description" % index,
                    record.get("description", ""),
                    allow_empty=True,
                ),
            }
        )
    return resolved


def groups_present(characteristics):
    """Characteristic groups the sheet actually fills, in canonical order."""
    filled = {c["group"] for c in characteristics}
    return [group for group in CHARACTERISTIC_GROUPS if group in filled]


def missing_mandatory_groups(characteristics):
    """Mandatory groups the sheet left empty."""
    filled = {c["group"] for c in characteristics}
    return [group for group in MANDATORY_GROUPS if group not in filled]


def group_completeness(characteristics):
    """Fraction of the mandatory groups the sheet fills."""
    filled = {c["group"] for c in characteristics}
    covered = sum(1 for group in MANDATORY_GROUPS if group in filled)
    return covered / len(MANDATORY_GROUPS)


def evaluate_data_sheet(sheet):
    """Full clause 5.4.5 assessment of one preliminary device data sheet.

    Returns the groups filled, the completeness reached, the findings and
    the verdict.
    """
    if not isinstance(sheet, dict):
        raise ValueError(
            "sheet must be a mapping of characteristics and an optional threshold"
        )
    known = set(_SHEET_REQUIRED_KEYS) | set(_SHEET_OPTIONAL_KEYS)
    unknown = sorted(set(sheet) - known)
    if unknown:
        raise ValueError("unknown sheet keys: %s" % ", ".join(unknown))
    absent = [key for key in _SHEET_REQUIRED_KEYS if key not in sheet]
    if absent:
        raise ValueError("sheet missing required keys: %s" % ", ".join(absent))

    characteristics = validate_characteristics(sheet["characteristics"])
    if not characteristics:
        raise ValueError("sheet must carry at least one characteristic")

    findings = []
    for entry in characteristics:
        if entry["numeric"] and not entry["unit"]:
            findings.append(
                {
                    "code": "numeric-figure-without-unit",
                    "characteristic": entry["name"],
                    "detail": "%s publishes a bare number; give it a unit, or %s "
                    "if it is dimensionless" % (entry["name"], DIMENSIONLESS_UNIT),
                }
            )
        if entry["numeric"] and not within_declared_range(
            entry["value"], entry["minimum"], entry["maximum"]
        ):
            findings.append(
                {
                    "code": "figure-outside-declared-range",
                    "characteristic": entry["name"],
                    "value": entry["value"],
                    "minimum": entry["minimum"],
                    "maximum": entry["maximum"],
                    "detail": "%s reads %g, outside the range the sheet declares "
                    "for it" % (entry["name"], entry["value"]),
                }
            )
        if entry["maturity"] == CONFIRMED and not basis_supports_confirmation(
            entry["basis"]
        ):
            findings.append(
                {
                    "code": "confirmed-figure-on-unconfirmed-basis",
                    "characteristic": entry["name"],
                    "basis": entry["basis"],
                    "detail": "%s is called confirmed while it rests on %s; an "
                    "outside reader will design against it"
                    % (entry["name"], entry["basis"]),
                }
            )
        if not entry["description"]:
            findings.append(
                {
                    "code": "characteristic-without-description",
                    "characteristic": entry["name"],
                    "detail": "%s carries no plain description, so a reader outside "
                    "the development has nothing to act on" % entry["name"],
                }
            )
        if not entry["numeric"] and not entry["value"]:
            findings.append(
                {
                    "code": "characteristic-without-value",
                    "characteristic": entry["name"],
                    "detail": "%s is listed and states nothing" % entry["name"],
                }
            )

    for group in missing_mandatory_groups(characteristics):
        findings.append(
            {
                "code": "mandatory-group-empty",
                "group": group,
                "detail": "the %s group is empty; a reader cannot tell an absent "
                "limit from an unwritten section" % group,
            }
        )

    completeness = group_completeness(characteristics)
    threshold = sheet.get("completeness_threshold")
    if threshold is not None:
        threshold_value = _fraction("completeness_threshold", threshold)
        if not meets_completeness_threshold(completeness, threshold_value):
            findings.append(
                {
                    "code": "group-completeness-below-threshold",
                    "achieved": completeness,
                    "threshold": threshold_value,
                    "detail": "the sheet fills %.1f %% of the mandatory groups "
                    "against a %.1f %% threshold"
                    % (100.0 * completeness, 100.0 * threshold_value),
                }
            )

    return {
        "characteristic_count": len(characteristics),
        "groups_present": groups_present(characteristics),
        "missing_mandatory_groups": missing_mandatory_groups(characteristics),
        "group_completeness": completeness,
        "findings": findings,
        "acceptable": not findings,
    }
