"""Whether a completed board repair may be accepted.

Anchor: ECSS-Q-ST-70-28C, acceptance clause -- the limits a finished repair or
modification of a printed circuit board assembly has to meet, which differ by
the category of repair that was performed and by the defect it was performed
on, and which tighten or relax with the assurance level of the product.
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Resolve the defect to the repair category that addresses it, and report a
   repair carried out under a category that does not treat the defect found.
2. Pull the criteria that category carries. Each criterion is a bound in a
   named direction: some quantities may not exceed a limit, others may not
   fall below one.
3. Scale every bound by the assurance level of the product, tightening a
   ceiling and raising a floor together so one level is uniformly stricter.
4. Express each measurement as a utilisation of its own bound, so a ceiling
   and a floor can be compared on one scale and the criterion closest to
   failing can be named.
5. Treat a criterion with no measurement behind it as an open item. An absent
   measurement is missing evidence, never a compliant one.
6. Return the verdict, the governing criterion, every breach and every open
   item, so a refused repair says what would have to change.
"""

import math

__all__ = [
    "ASSURANCE_LEVEL_FACTORS",
    "DEFAULT_ASSURANCE_LEVEL",
    "DEFECT_REPAIR_CATEGORY",
    "REPAIR_CRITERIA",
    "TOLERANCE",
    "defect_repair_category",
    "repair_criteria",
    "criterion_names",
    "scaled_limit",
    "criterion_utilisation",
    "open_items",
    "grade_measurements",
    "assess_repair_acceptance",
]

# Which repair category treats which defect. A repair recorded under a
# category that does not treat the defect found was either mis-recorded or
# performed with the wrong procedure, and both are findings.
DEFECT_REPAIR_CATEGORY = {
    "broken-conductor": "conductor-repair",
    "conductor-nick": "conductor-repair",
    "conductor-short": "conductor-repair",
    "lifted-land": "land-repair",
    "missing-land": "land-repair",
    "barrel-crack": "plated-through-hole-repair",
    "dewetted-barrel": "plated-through-hole-repair",
    "measling": "laminate-damage-repair",
    "laminate-gouge": "laminate-damage-repair",
    "coating-void": "coating-repair",
    "coating-lift": "coating-repair",
    "failed-component": "component-replacement",
    "wrong-component": "component-replacement",
}

# The acceptance criteria each repair category carries. "max" is a ceiling the
# measurement may sit on but not pass; "min" is a floor it may sit on but not
# fall below. Limits are stated at assurance level 2.
REPAIR_CRITERIA = {
    "conductor-repair": (
        {"name": "conductor-width-reduction", "bound": "max", "limit": 0.20, "unit": "fraction"},
        {"name": "jumper-overlap-length-mm", "bound": "min", "limit": 3.0, "unit": "mm"},
        {"name": "conductor-resistance-increase", "bound": "max", "limit": 0.10, "unit": "fraction"},
    ),
    "land-repair": (
        {"name": "land-area-loss", "bound": "max", "limit": 0.25, "unit": "fraction"},
        {"name": "land-bond-pull-strength-n", "bound": "min", "limit": 4.4, "unit": "N"},
        {"name": "land-to-conductor-overlap-mm", "bound": "min", "limit": 1.0, "unit": "mm"},
    ),
    "plated-through-hole-repair": (
        {"name": "barrel-wall-void-fraction", "bound": "max", "limit": 0.05, "unit": "fraction"},
        {"name": "eyelet-seating-gap-mm", "bound": "max", "limit": 0.05, "unit": "mm"},
        {"name": "hole-diameter-increase", "bound": "max", "limit": 0.15, "unit": "fraction"},
    ),
    "laminate-damage-repair": (
        {"name": "laminate-damage-depth-mm", "bound": "max", "limit": 0.25, "unit": "mm"},
        {"name": "laminate-damage-area-mm2", "bound": "max", "limit": 25.0, "unit": "mm2"},
        {"name": "dielectric-withstand-margin", "bound": "min", "limit": 1.0, "unit": "ratio"},
    ),
    "coating-repair": (
        {"name": "coating-thickness-mm", "bound": "min", "limit": 0.03, "unit": "mm"},
        {"name": "coating-overlap-mm", "bound": "min", "limit": 2.0, "unit": "mm"},
        {"name": "coating-repair-area-fraction", "bound": "max", "limit": 0.10, "unit": "fraction"},
    ),
    "component-replacement": (
        {"name": "termination-rework-cycles", "bound": "max", "limit": 3.0, "unit": "cycles"},
        {"name": "peak-termination-temperature-c", "bound": "max", "limit": 260.0, "unit": "degC"},
        {"name": "insulation-resistance-mohm", "bound": "min", "limit": 100.0, "unit": "Mohm"},
    ),
}

# Assurance level scaling. Level 1 is the strictest: ceilings come down and
# floors go up by the same factor, so a level is uniformly stricter rather
# than stricter in one direction only.
ASSURANCE_LEVEL_FACTORS = {1: 0.8, 2: 1.0, 3: 1.25}
DEFAULT_ASSURANCE_LEVEL = 2

# Measurements are physical quantities; a value sitting on its bound meets the
# criterion, and this absorbs representation error only.
TOLERANCE = 1e-9


def _require_mapping(value, label):
    if not isinstance(value, dict):
        raise ValueError("%s must be a mapping" % label)
    return value


def _real(value, label):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    return number


def _token(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string" % label)
    return value.strip().lower()


def _level(value):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("assurance level must be an integer, got %r" % (value,))
    if value not in ASSURANCE_LEVEL_FACTORS:
        raise ValueError(
            "unknown assurance level %d; known: %s"
            % (value, ", ".join(str(k) for k in sorted(ASSURANCE_LEVEL_FACTORS)))
        )
    return value


def defect_repair_category(defect):
    """Return the repair category that treats a given defect."""
    name = _token(defect, "defect")
    if name not in DEFECT_REPAIR_CATEGORY:
        raise ValueError(
            "unknown defect '%s'; known: %s"
            % (name, ", ".join(sorted(DEFECT_REPAIR_CATEGORY)))
        )
    return DEFECT_REPAIR_CATEGORY[name]


def repair_criteria(category):
    """Return the acceptance criteria a repair category carries."""
    name = _token(category, "category")
    if name not in REPAIR_CRITERIA:
        raise ValueError(
            "unknown repair category '%s'; known: %s"
            % (name, ", ".join(sorted(REPAIR_CRITERIA)))
        )
    return REPAIR_CRITERIA[name]


def criterion_names(category):
    """Return the names of the criteria a repair category carries."""
    return tuple(c["name"] for c in repair_criteria(category))


def scaled_limit(criterion, level=DEFAULT_ASSURANCE_LEVEL):
    """Return a criterion's bound scaled to an assurance level."""
    _require_mapping(criterion, "criterion")
    for key in ("name", "bound", "limit"):
        if key not in criterion:
            raise ValueError("criterion missing required key '%s'" % key)
    if criterion["bound"] not in ("max", "min"):
        raise ValueError("criterion bound must be 'max' or 'min', got %r" % (criterion["bound"],))
    limit = _real(criterion["limit"], "criterion limit")
    if limit <= 0.0:
        raise ValueError("criterion limit must be positive, got %g" % limit)
    factor = ASSURANCE_LEVEL_FACTORS[_level(level)]
    if criterion["bound"] == "max":
        return limit * factor
    return limit / factor


def criterion_utilisation(criterion, value, level=DEFAULT_ASSURANCE_LEVEL):
    """Return a measurement as a fraction of its own bound.

    A utilisation at or below one meets the criterion whichever direction the
    bound runs in, so a ceiling and a floor sit on the same scale.
    """
    bound = scaled_limit(criterion, level)
    measurement = _real(value, "measurement for '%s'" % criterion["name"])
    if criterion["bound"] == "max":
        if measurement < 0.0:
            raise ValueError(
                "measurement for '%s' must be non-negative, got %g"
                % (criterion["name"], measurement)
            )
        return measurement / bound
    if measurement <= 0.0:
        raise ValueError(
            "measurement for '%s' must be positive, got %g"
            % (criterion["name"], measurement)
        )
    return bound / measurement


def open_items(category, measurements):
    """Return the criteria of a category that have no measurement behind them."""
    _require_mapping(measurements, "measurements")
    names = criterion_names(category)
    supplied = set(_token(k, "measurement name") for k in measurements)
    unknown = sorted(supplied - set(names))
    if unknown:
        raise ValueError(
            "measurement(s) %s do not belong to repair category '%s'"
            % (", ".join(unknown), _token(category, "category"))
        )
    return [
        "criterion '%s' has no measurement behind it; acceptance is not "
        "demonstrated" % name
        for name in names
        if name not in supplied
    ]


def grade_measurements(category, measurements, level=DEFAULT_ASSURANCE_LEVEL):
    """Grade every supplied measurement of a category against its bound."""
    _require_mapping(measurements, "measurements")
    normalised = dict((_token(k, "measurement name"), v) for k, v in measurements.items())
    graded = []
    for criterion in repair_criteria(category):
        if criterion["name"] not in normalised:
            continue
        value = normalised[criterion["name"]]
        bound = scaled_limit(criterion, level)
        utilisation = criterion_utilisation(criterion, value, level)
        graded.append(
            {
                "name": criterion["name"],
                "bound": criterion["bound"],
                "unit": criterion["unit"],
                "value": _real(value, criterion["name"]),
                "limit": bound,
                "utilisation": utilisation,
                "met": utilisation <= 1.0 + TOLERANCE,
            }
        )
    return graded


def assess_repair_acceptance(repair):
    """Decide whether a finished repair may be accepted, and on what grounds.

    repair keys: defect, measurements, and optionally repair_category and
    assurance_level. When repair_category is absent it is resolved from the
    defect; when it is present and does not treat the defect, that mismatch
    is itself a finding.
    """
    _require_mapping(repair, "repair")
    for key in ("defect", "measurements"):
        if key not in repair:
            raise ValueError("repair missing required key '%s'" % key)

    expected = defect_repair_category(repair["defect"])
    declared = repair.get("repair_category")
    category = expected if declared is None else _token(declared, "repair_category")
    if category not in REPAIR_CRITERIA:
        raise ValueError(
            "unknown repair category '%s'; known: %s"
            % (category, ", ".join(sorted(REPAIR_CRITERIA)))
        )
    level = _level(repair.get("assurance_level", DEFAULT_ASSURANCE_LEVEL))

    findings = []
    if category != expected:
        findings.append(
            "defect '%s' is treated by a %s, but the repair was recorded as a %s"
            % (_token(repair["defect"], "defect"), expected, category)
        )

    graded = grade_measurements(category, repair["measurements"], level)
    unmet = [g for g in graded if not g["met"]]
    for entry in unmet:
        direction = "above its ceiling of" if entry["bound"] == "max" else "below its floor of"
        findings.append(
            "'%s' at %g %s is %s %g %s (utilisation %.3f)"
            % (
                entry["name"],
                entry["value"],
                entry["unit"],
                direction,
                entry["limit"],
                entry["unit"],
                entry["utilisation"],
            )
        )

    outstanding = open_items(category, repair["measurements"])
    findings.extend(outstanding)

    governing = None
    if graded:
        worst = max(graded, key=lambda g: g["utilisation"])
        governing = worst["name"]

    return {
        "defect": _token(repair["defect"], "defect"),
        "repair_category": category,
        "expected_category": expected,
        "assurance_level": level,
        "criteria": graded,
        "governing_criterion": governing,
        "governing_utilisation": (
            max(g["utilisation"] for g in graded) if graded else None
        ),
        "breaches": [g["name"] for g in unmet],
        "open_items": outstanding,
        "findings": findings,
        "accepted": not findings,
    }
