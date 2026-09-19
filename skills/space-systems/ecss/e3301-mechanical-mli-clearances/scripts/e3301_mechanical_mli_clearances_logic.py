"""Mechanical clearances between moving and adjacent parts, and to MLI.

Anchor: ECSS-E-ST-33-01C clauses 4.7.5.4.8 and 4.7.5.4.9 (mechanical clearance
held between moving parts and their surroundings, and the separate clearance
rule that applies where multi-layer insulation is one of the two surfaces).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate each declared interface: its nominal gap, its tolerance stack
   contributions, the thermal distortion and load deflection it sees, and the
   mechanism excursion that closes the gap.
2. Combine the tolerance contributions by the declared method -- an arithmetic
   worst case, or a root-sum-square where the contributions are independent and
   the interface carries enough of them for the statistic to mean anything.
3. Subtract every closure term from the nominal gap to get the worst-case
   minimum clearance of that interface.
4. Derive the clearance the interface is required to keep from its kind: a
   moving-to-static pair, a static-to-static adjacent pair, or an MLI pair
   whose blanket inflates on ascent and therefore needs the inflated envelope
   plus a standoff, not the compressed thickness.
5. Report the margin of every interface, name the governing one, and refuse a
   set that declares no interface at all.
"""

import math

__all__ = [
    "MOVING_PART_MIN_CLEARANCE_MM",
    "ADJACENT_PART_MIN_CLEARANCE_MM",
    "MLI_BALLOON_FACTOR",
    "MLI_STANDOFF_MM",
    "RSS_MIN_CONTRIBUTIONS",
    "CLEARANCE_TOLERANCE_MM",
    "INTERFACE_KINDS",
    "validate_positive",
    "combine_tolerances_mm",
    "mli_envelope_mm",
    "required_clearance_mm",
    "worst_case_clearance_mm",
    "assess_interface",
    "assess_clearances",
]

# Default clearance floors by interface kind, in millimetres.
MOVING_PART_MIN_CLEARANCE_MM = 2.0
ADJACENT_PART_MIN_CLEARANCE_MM = 1.0

# An MLI blanket is compressed when it is measured and inflates as the trapped
# gas leaves on ascent; the envelope it sweeps is the inflated one.
MLI_BALLOON_FACTOR = 2.0

# Standoff held beyond the inflated blanket envelope.
MLI_STANDOFF_MM = 5.0

# A root-sum-square stack is only meaningful with enough independent
# contributions; below this it is an arithmetic stack in disguise.
RSS_MIN_CONTRIBUTIONS = 3

# Clearance comparisons are sums and square roots of small numbers; absorb the
# representation error rather than relaxing the floor.
CLEARANCE_TOLERANCE_MM = 1e-9

INTERFACE_KINDS = ("moving", "adjacent", "mli")


def validate_positive(label, value, allow_zero=False):
    """Return value as a finite positive (or non-negative) float."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    v = float(value)
    if not math.isfinite(v):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if allow_zero:
        if v < 0.0:
            raise ValueError("%s must be non-negative, got %g" % (label, v))
    elif v <= 0.0:
        raise ValueError("%s must be positive, got %g" % (label, v))
    return v


def combine_tolerances_mm(contributions, method="worst-case"):
    """Combine tolerance contributions into a single gap-closing amount."""
    if not isinstance(contributions, (list, tuple)):
        raise ValueError("contributions must be a sequence of millimetre values")
    if method not in ("worst-case", "rss"):
        raise ValueError("method must be 'worst-case' or 'rss', got %r" % (method,))
    values = []
    for i, item in enumerate(contributions):
        values.append(validate_positive("contributions[%d]" % i, item, allow_zero=True))
    if not values:
        return 0.0
    if method == "worst-case":
        return math.fsum(values)
    if len(values) < RSS_MIN_CONTRIBUTIONS:
        raise ValueError(
            "a root-sum-square stack needs at least %d independent contributions, got %d"
            % (RSS_MIN_CONTRIBUTIONS, len(values))
        )
    return math.sqrt(math.fsum(v * v for v in values))


def mli_envelope_mm(blanket_thickness_mm, balloon_factor=MLI_BALLOON_FACTOR):
    """Inflated envelope swept by an MLI blanket, in millimetres."""
    thickness = validate_positive("blanket_thickness_mm", blanket_thickness_mm)
    factor = validate_positive("balloon_factor", balloon_factor)
    if factor < 1.0:
        raise ValueError("balloon_factor must be at least 1.0, got %g" % factor)
    return thickness * factor


def required_clearance_mm(kind, blanket_thickness_mm=None,
                          balloon_factor=MLI_BALLOON_FACTOR,
                          standoff_mm=MLI_STANDOFF_MM, override_mm=None):
    """Return the clearance an interface of this kind is required to keep."""
    if kind not in INTERFACE_KINDS:
        raise ValueError(
            "kind must be one of %s, got %r" % (", ".join(INTERFACE_KINDS), kind)
        )
    if override_mm is not None:
        return validate_positive("override_mm", override_mm)
    if kind == "moving":
        return MOVING_PART_MIN_CLEARANCE_MM
    if kind == "adjacent":
        return ADJACENT_PART_MIN_CLEARANCE_MM
    if blanket_thickness_mm is None:
        raise ValueError("an mli interface needs blanket_thickness_mm")
    standoff = validate_positive("standoff_mm", standoff_mm)
    return mli_envelope_mm(blanket_thickness_mm, balloon_factor) + standoff


def worst_case_clearance_mm(nominal_gap_mm, tolerance_mm, thermal_distortion_mm,
                            deflection_mm, excursion_mm):
    """Nominal gap less every term that closes it, in millimetres."""
    nominal = validate_positive("nominal_gap_mm", nominal_gap_mm)
    closures = math.fsum(
        (
            validate_positive("tolerance_mm", tolerance_mm, allow_zero=True),
            validate_positive(
                "thermal_distortion_mm", thermal_distortion_mm, allow_zero=True
            ),
            validate_positive("deflection_mm", deflection_mm, allow_zero=True),
            validate_positive("excursion_mm", excursion_mm, allow_zero=True),
        )
    )
    return nominal - closures


def assess_interface(record):
    """Assess one declared clearance interface and return its record.

    record keys: name, kind, nominal_gap_mm; optional tolerances,
    tolerance_method, thermal_distortion_mm, deflection_mm, excursion_mm,
    blanket_thickness_mm, balloon_factor, standoff_mm, required_clearance_mm.
    """
    if not isinstance(record, dict):
        raise ValueError("interface record must be a mapping")
    for key in ("name", "kind", "nominal_gap_mm"):
        if key not in record:
            raise ValueError("interface record missing required key '%s'" % key)
    name = record["name"]
    if not isinstance(name, str) or not name.strip():
        raise ValueError("interface name must be a non-empty string")
    kind = record["kind"]
    if kind not in INTERFACE_KINDS:
        raise ValueError(
            "interface %r has unknown kind %r; known: %s"
            % (name, kind, ", ".join(INTERFACE_KINDS))
        )
    if kind == "moving" and "excursion_mm" not in record:
        raise ValueError(
            "moving interface %r must declare excursion_mm, even when it is zero" % name
        )
    tolerance = combine_tolerances_mm(
        record.get("tolerances", ()), record.get("tolerance_method", "worst-case")
    )
    clearance = worst_case_clearance_mm(
        record["nominal_gap_mm"], tolerance,
        record.get("thermal_distortion_mm", 0.0),
        record.get("deflection_mm", 0.0),
        record.get("excursion_mm", 0.0),
    )
    required = required_clearance_mm(
        kind, record.get("blanket_thickness_mm"),
        record.get("balloon_factor", MLI_BALLOON_FACTOR),
        record.get("standoff_mm", MLI_STANDOFF_MM),
        record.get("required_clearance_mm"),
    )
    margin = clearance - required
    compliant = margin > 0.0 or math.isclose(
        margin, 0.0, rel_tol=0.0, abs_tol=CLEARANCE_TOLERANCE_MM
    )
    return {
        "name": name,
        "kind": kind,
        "tolerance_mm": tolerance,
        "worst_case_clearance_mm": clearance,
        "required_clearance_mm": required,
        "margin_mm": margin,
        "contact": clearance < 0.0,
        "compliant": compliant,
    }


def assess_clearances(spec):
    """Run the full clause 4.7.5.4.8-4.7.5.4.9 clearance assessment.

    spec keys: interfaces (a non-empty sequence of interface records).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    if "interfaces" not in spec:
        raise ValueError("spec missing required key 'interfaces'")
    interfaces = spec["interfaces"]
    if not isinstance(interfaces, (list, tuple)) or not interfaces:
        raise ValueError("interfaces must be a non-empty sequence of records")

    results = []
    seen = set()
    for record in interfaces:
        assessed = assess_interface(record)
        key = assessed["name"].strip().lower()
        if key in seen:
            raise ValueError("duplicate interface name %r" % assessed["name"])
        seen.add(key)
        results.append(assessed)

    findings = []
    for item in results:
        if item["contact"]:
            findings.append(
                "interface '%s' closes to contact: worst-case clearance %.4f mm"
                % (item["name"], item["worst_case_clearance_mm"])
            )
        elif not item["compliant"]:
            findings.append(
                "interface '%s' keeps %.4f mm against a required %.4f mm"
                % (item["name"], item["worst_case_clearance_mm"],
                   item["required_clearance_mm"])
            )
    governing = min(results, key=lambda r: r["margin_mm"])
    return {
        "interfaces": results,
        "governing_interface": governing["name"],
        "governing_margin_mm": governing["margin_mm"],
        "interface_count": len(results),
        "compliant": all(item["compliant"] for item in results),
        "findings": findings,
    }
