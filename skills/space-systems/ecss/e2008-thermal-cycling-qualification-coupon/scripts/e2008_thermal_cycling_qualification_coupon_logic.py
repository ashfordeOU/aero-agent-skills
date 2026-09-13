"""Definition record of the coupon a solar-array thermal-cycling run uses.

Anchor: ECSS-E-ST-20-08C clause 5.5.1.3.3 (thermal cycling -- the coupon the
cycling is performed on is defined, and the definition is carried by a drawing
or by a definition matrix). Paraphrased into an implementable procedure; no
standard text is reproduced.

Procedure implemented here
--------------------------
1. Normalise every declared feature of the coupon and build the register,
   refusing a feature declared twice.
2. Resolve the record each feature is defined by: a drawing reference or a
   cell of a definition matrix. A free-text note that is neither is refused,
   because it does not fix the build the cycling result is attributed to.
3. Check the register against the feature families a photovoltaic coupon has
   to define, and name the ones missing.
4. Compare the register with the flight assembly: name every flight feature
   the coupon leaves out, and every coupon feature the flight assembly does
   not carry.
5. Measure the coverage of the required families the register reaches and
   compare it with the minimum the programme asked for.
6. Report the register, the grouping by record medium, the coverage and every
   finding; the coupon is defined only when the finding list is empty.
"""

import math
import re

__all__ = [
    "COVERAGE_TOLERANCE",
    "REQUIRED_FEATURES",
    "RECORD_MEDIA",
    "DRAWING_PATTERN",
    "MATRIX_PATTERN",
    "normalize_feature",
    "reference_kind",
    "validate_entry",
    "build_register",
    "coverage_fraction",
    "missing_required",
    "unrepresented_flight_features",
    "extraneous_features",
    "assess_coupon_definition",
]

# Coverage is a ratio of counts; an exactly satisfied minimum must not be
# rejected by representation error in the division.
COVERAGE_TOLERANCE = 1e-9

# The families a photovoltaic-assembly coupon has to define before a cycling
# result can be attributed to a build.
REQUIRED_FEATURES = (
    "solar-cell",
    "interconnect",
    "coverglass",
    "adhesive",
    "substrate",
    "wiring-termination",
)

RECORD_MEDIA = ("drawing", "matrix")

# A drawing reference: an alphabetic prefix, a number, an optional dash-suffix
# and an optional revision, e.g. "SA-104275" or "PVA-2210-B rev C".
DRAWING_PATTERN = re.compile(
    r"^[A-Za-z]{2,5}-\d{3,8}(?:-[A-Za-z0-9]{1,4})?(?:\s+rev\s+[A-Za-z0-9]{1,3})?$",
    re.IGNORECASE,
)

# A definition-matrix cell: the matrix identifier, then a row and a column,
# e.g. "MTX-7:R3C4".
MATRIX_PATTERN = re.compile(r"^[A-Za-z]{2,5}-\d{1,4}:R\d{1,3}C\d{1,3}$", re.IGNORECASE)


def _text(value, label):
    """Return value as a trimmed non-empty string."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    cleaned = value.strip()
    if not cleaned:
        raise ValueError("%s must not be empty" % label)
    return cleaned


def normalize_feature(name):
    """Return a feature-family name lowered, trimmed and hyphenated."""
    cleaned = _text(name, "feature name")
    collapsed = " ".join(cleaned.lower().replace("_", " ").replace("-", " ").split())
    return collapsed.replace(" ", "-")


def reference_kind(reference):
    """Return 'drawing' or 'matrix' for a definition reference."""
    cleaned = " ".join(_text(reference, "reference").split())
    if MATRIX_PATTERN.match(cleaned):
        return "matrix"
    if DRAWING_PATTERN.match(cleaned):
        return "drawing"
    raise ValueError(
        "reference '%s' is neither a drawing reference nor a definition-matrix "
        "cell; a free-text note does not define the coupon" % cleaned
    )


def validate_entry(entry):
    """Return the normalised register entry of one declared coupon feature."""
    if not isinstance(entry, dict):
        raise ValueError("feature entry must be a mapping")
    for key in ("name", "reference"):
        if key not in entry:
            raise ValueError("feature entry missing required key '%s'" % key)
    name = normalize_feature(entry["name"])
    reference = " ".join(_text(entry["reference"], "reference").split())
    record = reference_kind(reference)
    process = entry.get("process")
    if process is not None:
        process = normalize_feature(process)
    return {
        "name": name,
        "reference": reference,
        "record": record,
        "process": process,
    }


def build_register(features):
    """Return the coupon register, refusing a feature declared twice."""
    if not isinstance(features, (list, tuple)) or not features:
        raise ValueError("features must be a non-empty sequence of entries")
    register = []
    seen = set()
    for entry in features:
        record = validate_entry(entry)
        if record["name"] in seen:
            raise ValueError(
                "feature '%s' is declared twice in the coupon definition"
                % record["name"]
            )
        seen.add(record["name"])
        register.append(record)
    return register


def _normalized_names(names, label):
    """Return a list of normalised family names from a sequence."""
    if not isinstance(names, (list, tuple)):
        raise ValueError("%s must be a sequence of names" % label)
    return [normalize_feature(name) for name in names]


def coverage_fraction(defined_names, required=REQUIRED_FEATURES):
    """Return the fraction of the required families the register reaches."""
    wanted = _normalized_names(required, "required")
    if not wanted:
        raise ValueError("required must name at least one family")
    defined = set(_normalized_names(defined_names, "defined_names"))
    hits = sum(1 for name in wanted if name in defined)
    return hits / float(len(wanted))


def missing_required(defined_names, required=REQUIRED_FEATURES):
    """Return the required families the register never defines."""
    wanted = _normalized_names(required, "required")
    defined = set(_normalized_names(defined_names, "defined_names"))
    return [name for name in wanted if name not in defined]


def unrepresented_flight_features(defined_names, flight_features):
    """Return the flight features the coupon does not reproduce."""
    flight = _normalized_names(flight_features, "flight_features")
    defined = set(_normalized_names(defined_names, "defined_names"))
    return [name for name in flight if name not in defined]


def extraneous_features(defined_names, flight_features):
    """Return the coupon features the flight assembly does not carry."""
    flight = set(_normalized_names(flight_features, "flight_features"))
    defined = _normalized_names(defined_names, "defined_names")
    return [name for name in defined if name not in flight]


def assess_coupon_definition(spec):
    """Run the full clause 5.5.1.3.3 coupon-definition assessment.

    spec keys: features (each: name, reference, optional process); optional
    flight_features, required_features, minimum_coverage.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    if "features" not in spec:
        raise ValueError("spec missing required key 'features'")
    required = spec.get("required_features", REQUIRED_FEATURES)
    minimum = spec.get("minimum_coverage", 1.0)
    if not isinstance(minimum, (int, float)) or isinstance(minimum, bool):
        raise ValueError("minimum_coverage must be a real number")
    minimum = float(minimum)
    if not math.isfinite(minimum) or minimum < 0.0 or minimum > 1.0:
        raise ValueError("minimum_coverage must lie in [0, 1], got %g" % minimum)

    register = build_register(spec["features"])
    names = [record["name"] for record in register]
    grouping = dict((medium, 0) for medium in RECORD_MEDIA)
    for record in register:
        grouping[record["record"]] += 1

    coverage = coverage_fraction(names, required)
    missing = missing_required(names, required)
    findings = [
        "required feature family '%s' is not defined on the coupon" % name
        for name in missing
    ]
    if coverage < minimum - COVERAGE_TOLERANCE:
        findings.append(
            "coupon defines %.3f of the required families, below the %.3f asked "
            "for" % (coverage, minimum)
        )
    unrepresented = []
    extraneous = []
    if spec.get("flight_features") is not None:
        unrepresented = unrepresented_flight_features(names, spec["flight_features"])
        extraneous = extraneous_features(names, spec["flight_features"])
        findings.extend(
            "flight feature '%s' has no counterpart on the coupon" % name
            for name in unrepresented
        )
        findings.extend(
            "coupon feature '%s' is not on the flight assembly; the coupon is not "
            "representative" % name
            for name in extraneous
        )
    return {
        "register": register,
        "record_grouping": grouping,
        "coverage": coverage,
        "minimum_coverage": minimum,
        "missing_required": missing,
        "unrepresented_flight_features": unrepresented,
        "extraneous_features": extraneous,
        "findings": findings,
        "defined": not findings,
    }
