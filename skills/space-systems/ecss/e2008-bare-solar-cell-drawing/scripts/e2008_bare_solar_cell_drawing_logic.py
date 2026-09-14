#!/usr/bin/env python3
"""Source control drawing content for a bare solar cell.

Anchor: ECSS-E-ST-20-08C Annex C. The procedure below is a paraphrase into
implementable steps; no standard text is reproduced.

The drawing describing a bare solar cell is a list of characteristics, and a
characteristic on that drawing is only worth something when three things are
true at once.

It carries a unit.
    A thickness of 150 is a number somebody will read as micrometres or as
    thousandths of an inch, and both readings look reasonable.

It carries a limit, not just a value.
    A minimum, a maximum, a range, or a nominal with a band. A nominal on its
    own is what the supplier intends today, and nothing about it lets anyone
    reject a cell tomorrow. A range whose two bounds coincide is the same
    failure written as a band: it names a point no real cell lands on.

If it is electrical, it carries the conditions it was measured at.
    An open-circuit voltage without the spectrum, the intensity and the
    temperature behind it is a number from an unnamed experiment. Two
    suppliers can both meet it while shipping different cells.

The annex names a floor, not a ceiling: characteristics beyond the required
set are graded and reported, and a weak one among them does not stop a
drawing whose required set is sound.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

__all__ = [
    "REQUIRED_CHARACTERISTICS",
    "CHARACTERISTIC_WEIGHTS",
    "CHARACTERISTIC_KINDS",
    "LIMIT_FORMS",
    "REQUIRED_CONDITION_KEYS",
    "CHAR_CONTROLLED",
    "CHAR_OPEN",
    "CHAR_UNCONTROLLED",
    "BARE_CELL_DRAWING_RELEASABLE",
    "BARE_CELL_DRAWING_OPEN_ITEMS",
    "BARE_CELL_DRAWING_NOT_RELEASABLE",
    "limit_bounds",
    "measurement_conditions",
    "characteristic_control",
    "controlled_characteristic_share",
    "assess_bare_cell_drawing",
]

# The characteristics Annex C expects on a bare solar cell drawing, with the
# kind each one is and how much of the cell it pins down.
REQUIRED_CHARACTERISTICS = (
    ("cell-length", "geometric", 3),
    ("cell-width", "geometric", 3),
    ("cell-thickness", "geometric", 3),
    ("contact-grid-geometry", "geometric", 2),
    ("antireflection-coating", "physical", 2),
    ("cell-mass", "physical", 2),
    ("open-circuit-voltage", "electrical", 3),
    ("short-circuit-current", "electrical", 3),
    ("maximum-power-point", "electrical", 3),
)

CHARACTERISTIC_WEIGHTS = {name: weight for name, _kind, weight in REQUIRED_CHARACTERISTICS}

CHARACTERISTIC_KINDS = ("geometric", "physical", "electrical")

LIMIT_FORMS = (
    "minimum",
    "maximum",
    "range",
    "nominal-with-tolerance",
    "nominal-only",
)

# An electrical number is meaningless unless the drawing says what it was
# measured against.
REQUIRED_CONDITION_KEYS = ("spectrum", "irradiance", "temperature")

CHAR_CONTROLLED = "characteristic-controlled"
CHAR_OPEN = "characteristic-open"
CHAR_UNCONTROLLED = "characteristic-uncontrolled"

BARE_CELL_DRAWING_RELEASABLE = "bare-cell-drawing-releasable"
BARE_CELL_DRAWING_OPEN_ITEMS = "bare-cell-drawing-releasable-with-open-items"
BARE_CELL_DRAWING_NOT_RELEASABLE = "bare-cell-drawing-not-releasable"

# Bounds and weighted shares are computed from the drawing's own numbers, so a
# band whose ends are meant to coincide, or a share sitting on its threshold,
# can land a few units in the last place off. The comparisons absorb that; the
# written values stay as written.
_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _label(name, value):
    """Return a non-empty stripped string, or raise."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _real(name, value):
    """Return a finite float, or raise."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (name, value))
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("%s must be finite, got %r" % (name, value))
    return value


def _same(left, right):
    """True when two computed bounds coincide, absorbing representation error."""
    return math.isclose(left, right, rel_tol=_REL_TOL, abs_tol=_ABS_TOL)


def _at_least(value, bound):
    """True when value is at or above bound, absorbing representation error."""
    return value > bound or math.isclose(
        value, bound, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _need(record, key, form):
    """Pull a required numeric field for a limit form, or raise."""
    if key not in record:
        raise ValueError(
            "limit form '%s' needs a '%s' value and the record carries none"
            % (form, key)
        )
    return _real(key, record[key])


def limit_bounds(record):
    """Turn a stated limit into bounds, and say whether it bands anything.

    record keys: limit_form, plus the values that form needs.
    """
    if not isinstance(record, dict):
        raise ValueError("limit record must be a mapping")
    if "limit_form" not in record:
        raise ValueError("limit record missing required key 'limit_form'")
    form = record["limit_form"]
    if form not in LIMIT_FORMS:
        raise ValueError("limit_form must be one of %s, got %r" % (LIMIT_FORMS, form))

    findings = []
    if form == "nominal-only":
        nominal = _need(record, "nominal", form)
        findings.append(
            "the value %.6g is stated as a nominal with no limit; it is what "
            "the supplier intends, not something a cell can be rejected "
            "against" % nominal
        )
        return {
            "form": form,
            "lower": None,
            "upper": None,
            "banded": False,
            "degenerate": False,
            "findings": findings,
        }

    if form == "minimum":
        lower = _need(record, "minimum", form)
        return {
            "form": form,
            "lower": lower,
            "upper": None,
            "banded": True,
            "degenerate": False,
            "findings": findings,
        }

    if form == "maximum":
        upper = _need(record, "maximum", form)
        return {
            "form": form,
            "lower": None,
            "upper": upper,
            "banded": True,
            "degenerate": False,
            "findings": findings,
        }

    if form == "range":
        lower = _need(record, "minimum", form)
        upper = _need(record, "maximum", form)
        if upper < lower and not _same(lower, upper):
            raise ValueError(
                "a range runs from %.6g up to %.6g, which is not a range"
                % (lower, upper)
            )
        degenerate = _same(lower, upper)
        if degenerate:
            findings.append(
                "the range bounds coincide at %.6g; a band of no width names a "
                "point no real cell lands on" % lower
            )
        return {
            "form": form,
            "lower": lower,
            "upper": upper,
            "banded": not degenerate,
            "degenerate": degenerate,
            "findings": findings,
        }

    nominal = _need(record, "nominal", form)
    tolerance = _need(record, "tolerance", form)
    if tolerance < 0.0:
        raise ValueError("a tolerance of %.6g is not a band" % tolerance)
    degenerate = _same(tolerance, 0.0)
    if degenerate:
        findings.append(
            "the tolerance on %.6g is zero; no cell can be made to it and none "
            "can be rejected against it" % nominal
        )
    return {
        "form": form,
        "lower": nominal - tolerance,
        "upper": nominal + tolerance,
        "banded": not degenerate,
        "degenerate": degenerate,
        "findings": findings,
    }


def measurement_conditions(conditions):
    """Check the conditions an electrical number was measured at are all named."""
    if conditions is None:
        conditions = {}
    if not isinstance(conditions, dict):
        raise ValueError("measurement conditions must be a mapping")
    stated = {}
    for key, value in conditions.items():
        name = _label("condition key", key)
        if isinstance(value, str):
            if not value.strip():
                raise ValueError("condition '%s' is stated as an empty string" % name)
            stated[name] = value.strip()
        elif isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(
                "condition '%s' must be a number or a named value, got %r"
                % (name, value)
            )
        else:
            stated[name] = _real(name, value)
    missing = [key for key in REQUIRED_CONDITION_KEYS if key not in stated]
    findings = []
    for key in missing:
        findings.append(
            "no %s is stated for this electrical characteristic; the number "
            "comes from an unnamed measurement" % key
        )
    return {
        "stated": stated,
        "missing": missing,
        "complete": not missing,
        "findings": findings,
    }


def characteristic_control(record):
    """Decide whether one drawing characteristic is actually controlled.

    record keys: characteristic, kind, unit, limit_form, the values that form
    needs, and for an electrical kind a conditions mapping.
    """
    if not isinstance(record, dict):
        raise ValueError("characteristic record must be a mapping")
    for key in ("characteristic", "kind", "unit", "limit_form"):
        if key not in record:
            raise ValueError("characteristic record missing required key '%s'" % key)
    name = _label("characteristic", record["characteristic"])
    kind = record["kind"]
    if kind not in CHARACTERISTIC_KINDS:
        raise ValueError(
            "characteristic kind must be one of %s, got %r"
            % (CHARACTERISTIC_KINDS, kind)
        )
    unit = _label("unit", record["unit"])

    bounds = limit_bounds(record)
    findings = ["%s: %s" % (name, text) for text in bounds["findings"]]

    if kind == "electrical":
        conditions = measurement_conditions(record.get("conditions"))
    else:
        conditions = {"stated": {}, "missing": [], "complete": True, "findings": []}
    findings.extend("%s: %s" % (name, text) for text in conditions["findings"])

    if bounds["form"] == "nominal-only" or not conditions["complete"]:
        state = CHAR_UNCONTROLLED
    elif bounds["degenerate"]:
        state = CHAR_OPEN
    else:
        state = CHAR_CONTROLLED

    return {
        "characteristic": name,
        "kind": kind,
        "unit": unit,
        "bounds": bounds,
        "conditions": conditions,
        "state": state,
        "controlled": state == CHAR_CONTROLLED,
        "findings": findings,
    }


def controlled_characteristic_share(results):
    """Weight the controlled required characteristics by what each pins down."""
    if not isinstance(results, (list, tuple)):
        raise ValueError("results must be a sequence of graded characteristics")
    total = float(sum(CHARACTERISTIC_WEIGHTS.values()))
    if total <= 0.0:
        raise ValueError("the required characteristic set carries no weight")
    earned = 0.0
    for item in results:
        weight = CHARACTERISTIC_WEIGHTS.get(item.get("characteristic"))
        if weight is None:
            continue
        if item.get("state") == CHAR_CONTROLLED:
            earned += float(weight)
    return earned / total


def assess_bare_cell_drawing(spec):
    """Assess a bare solar cell source control drawing.

    spec keys: drawing, characteristics, optional required_control_share.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("drawing", "characteristics"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    drawing = _label("drawing", spec["drawing"])
    if not isinstance(spec["characteristics"], (list, tuple)):
        raise ValueError("spec['characteristics'] must be a sequence")
    if not spec["characteristics"]:
        raise ValueError("a bare cell drawing stating no characteristic is an input error")

    required_share = spec.get("required_control_share", 1.0)
    if isinstance(required_share, bool) or not isinstance(
        required_share, (int, float)
    ):
        raise ValueError("required_control_share must be a real number")
    required_share = float(required_share)
    if not math.isfinite(required_share) or not 0.0 <= required_share <= 1.0:
        raise ValueError(
            "required_control_share must lie in [0, 1], got %r"
            % (spec.get("required_control_share"),)
        )

    results = [characteristic_control(item) for item in spec["characteristics"]]
    seen = set()
    for item in results:
        if item["characteristic"] in seen:
            raise ValueError(
                "characteristic '%s' is stated twice on drawing %s"
                % (item["characteristic"], drawing)
            )
        seen.add(item["characteristic"])

    findings = []
    missing = []
    for name, kind, _weight in REQUIRED_CHARACTERISTICS:
        if name in seen:
            match = next(i for i in results if i["characteristic"] == name)
            if match["kind"] != kind:
                findings.append(
                    "characteristic '%s' is stated as %s and the annex treats "
                    "it as %s" % (name, match["kind"], kind)
                )
            continue
        missing.append(name)
        findings.append(
            "characteristic '%s' is required by the annex and the drawing does "
            "not state it" % name
        )

    for item in results:
        findings.extend(item["findings"])

    required_names = set(CHARACTERISTIC_WEIGHTS)
    uncontrolled = [
        i["characteristic"]
        for i in results
        if i["state"] == CHAR_UNCONTROLLED and i["characteristic"] in required_names
    ]
    open_items = [
        i["characteristic"]
        for i in results
        if i["state"] == CHAR_OPEN and i["characteristic"] in required_names
    ]
    weak_extras = [
        i["characteristic"]
        for i in results
        if i["characteristic"] not in required_names and not i["controlled"]
    ]
    mistyped = [
        i["characteristic"]
        for i in results
        if i["characteristic"] in required_names
        and i["kind"] != next(
            k for n, k, _w in REQUIRED_CHARACTERISTICS if n == i["characteristic"]
        )
    ]

    share = controlled_characteristic_share(results)
    share_met = _at_least(share, required_share)
    if not share_met:
        findings.append(
            "weighted control share is %.4f against a required %.4f"
            % (share, required_share)
        )

    blocking = bool(missing or uncontrolled or mistyped) or not share_met
    conditional = bool(open_items or weak_extras)

    if blocking:
        verdict = BARE_CELL_DRAWING_NOT_RELEASABLE
    elif conditional:
        verdict = BARE_CELL_DRAWING_OPEN_ITEMS
    else:
        verdict = BARE_CELL_DRAWING_RELEASABLE

    return {
        "drawing": drawing,
        "characteristics": results,
        "missing_characteristics": missing,
        "uncontrolled_characteristics": uncontrolled,
        "open_characteristics": open_items,
        "weak_extra_characteristics": weak_extras,
        "miskinded_characteristics": mistyped,
        "control_share": share,
        "required_control_share": required_share,
        "verdict": verdict,
        "findings": findings,
    }
