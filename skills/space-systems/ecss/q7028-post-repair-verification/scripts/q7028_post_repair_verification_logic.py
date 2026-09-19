"""Post-repair verification of a repaired area on a printed board assembly.

Anchor: ECSS-Q-ST-70-28 Verification (verifying a repaired or modified area
by visual, electrical and dimensional means, with radiographic inspection
where the connection cannot be seen). Paraphrased into an implementable
procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Derive the inspection set the repair owes from the work that was actually
   done, rather than accepting whatever inspections happened to be performed.
2. Compare that set with what was performed; an inspection the repair owed
   and did not get makes the verification incomplete, which is a different
   outcome from a failed inspection.
3. Grade each inspection that was performed: the magnification used against
   the magnification the smallest feature demands, insulation and path
   resistance against their limits, a dimension against its band, and the
   void fraction of a radiograph against its maximum.
4. Return accept, reject or incomplete, with every finding named.
"""

import math

__all__ = [
    "RESISTANCE_TOLERANCE",
    "LENGTH_TOLERANCE_MM",
    "FRACTION_TOLERANCE",
    "MAGNIFICATION_TOLERANCE",
    "REFERENCE_APPARENT_SIZE_MM",
    "MAGNIFICATION_STEPS",
    "REPAIR_KINDS",
    "INSPECTIONS",
    "require_real",
    "require_band",
    "required_magnification",
    "required_inspection_set",
    "missing_inspections",
    "grade_visual",
    "grade_electrical",
    "grade_dimensional",
    "grade_radiographic",
    "assess_post_repair_verification",
]

RESISTANCE_TOLERANCE = 1e-9
LENGTH_TOLERANCE_MM = 1e-9
FRACTION_TOLERANCE = 1e-12
MAGNIFICATION_TOLERANCE = 1e-9

# Apparent size the smallest graded feature must reach at the eyepiece.
REFERENCE_APPARENT_SIZE_MM = 3.0

# Magnifications a standard inspection bench can actually be set to.
MAGNIFICATION_STEPS = (1.75, 3.0, 4.0, 7.5, 10.0, 20.0, 30.0)

REPAIR_KINDS = (
    "laminate-repair",
    "plated-hole-repair",
    "solder-joint-rework",
    "conformal-coating-repair",
    "component-replacement",
    "track-cut",
    "added-wire",
)

INSPECTIONS = ("visual", "electrical", "dimensional", "radiographic")

# Work that alters a conductive path owes an electrical check.
_ELECTRICAL_KINDS = frozenset((
    "plated-hole-repair", "solder-joint-rework", "component-replacement",
    "track-cut", "added-wire",
))
# Work that adds or removes material owes a dimensional check.
_DIMENSIONAL_KINDS = frozenset((
    "laminate-repair", "plated-hole-repair", "conformal-coating-repair",
))
# Work whose result is inside the board owes a radiograph.
_RADIOGRAPHIC_KINDS = frozenset(("plated-hole-repair",))


def require_real(label, value, minimum=None, allow_equal=True):
    """Return value as a float, raising ValueError on anything unusable."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if minimum is not None:
        if allow_equal and out < minimum:
            raise ValueError("%s must be at least %g, got %g" % (label, minimum, out))
        if not allow_equal and out <= minimum:
            raise ValueError("%s must exceed %g, got %g" % (label, minimum, out))
    return out


def require_band(label, band, minimum=None):
    """Return a validated (low, high) pair with low <= high."""
    if not isinstance(band, (list, tuple)) or len(band) != 2:
        raise ValueError("%s must be a (low, high) pair, got %r" % (label, band))
    low = require_real("%s low" % label, band[0], minimum=minimum)
    high = require_real("%s high" % label, band[1], minimum=minimum)
    if low > high:
        raise ValueError("%s low %g exceeds high %g" % (label, low, high))
    return (low, high)


def required_magnification(smallest_feature_mm):
    """Return the bench magnification step the smallest graded feature demands."""
    feature = require_real("smallest_feature_mm", smallest_feature_mm, minimum=0.0,
                           allow_equal=False)
    wanted = REFERENCE_APPARENT_SIZE_MM / feature
    for step in MAGNIFICATION_STEPS:
        if step >= wanted - MAGNIFICATION_TOLERANCE:
            return step
    raise ValueError(
        "a %g mm feature demands %gx, beyond the %gx the bench can reach"
        % (feature, wanted, MAGNIFICATION_STEPS[-1])
    )


def required_inspection_set(repair_kinds, hidden_connection=False):
    """Return the inspections the repair owes, from the work that was done."""
    if not isinstance(repair_kinds, (list, tuple, set, frozenset)) or not repair_kinds:
        raise ValueError("repair_kinds must be a non-empty sequence of repair kinds")
    if not isinstance(hidden_connection, bool):
        raise ValueError("hidden_connection must be a bool, got %r"
                         % (hidden_connection,))
    kinds = []
    for kind in repair_kinds:
        if kind not in REPAIR_KINDS:
            raise ValueError(
                "repair kind must be one of %s, got %r"
                % (", ".join(REPAIR_KINDS), kind)
            )
        kinds.append(kind)
    required = {"visual"}
    for kind in kinds:
        if kind in _ELECTRICAL_KINDS:
            required.add("electrical")
        if kind in _DIMENSIONAL_KINDS:
            required.add("dimensional")
        if kind in _RADIOGRAPHIC_KINDS:
            required.add("radiographic")
    if hidden_connection:
        required.add("radiographic")
    return sorted(required)


def missing_inspections(required, performed):
    """Return the required inspections that were not performed."""
    if not isinstance(performed, (list, tuple, set, frozenset)):
        raise ValueError("performed must be a sequence of inspection names")
    for name in performed:
        if name not in INSPECTIONS:
            raise ValueError(
                "inspection must be one of %s, got %r" % (", ".join(INSPECTIONS), name)
            )
    done = set(performed)
    return sorted(name for name in required if name not in done)


def grade_visual(magnification_used, smallest_feature_mm):
    """Grade the visual inspection on the magnification actually used."""
    used = require_real("magnification_used", magnification_used, minimum=0.0,
                        allow_equal=False)
    needed = required_magnification(smallest_feature_mm)
    under = used < needed - MAGNIFICATION_TOLERANCE
    return {
        "magnification_used": used,
        "magnification_required": needed,
        "under_magnified": under,
        "acceptable": not under,
    }


def grade_electrical(insulation_mohm, min_insulation_mohm,
                     path_resistance_mohm, max_path_resistance_mohm):
    """Grade the electrical check on insulation and on path resistance."""
    insulation = require_real("insulation_mohm", insulation_mohm, minimum=0.0)
    min_insulation = require_real("min_insulation_mohm", min_insulation_mohm,
                                  minimum=0.0, allow_equal=False)
    path = require_real("path_resistance_mohm", path_resistance_mohm, minimum=0.0)
    max_path = require_real("max_path_resistance_mohm", max_path_resistance_mohm,
                            minimum=0.0, allow_equal=False)
    leaky = insulation < min_insulation - RESISTANCE_TOLERANCE
    resistive = path > max_path + RESISTANCE_TOLERANCE
    return {
        "insulation_mohm": insulation,
        "min_insulation_mohm": min_insulation,
        "path_resistance_mohm": path,
        "max_path_resistance_mohm": max_path,
        "insulation_low": leaky,
        "path_resistance_high": resistive,
        "acceptable": not (leaky or resistive),
    }


def grade_dimensional(measured_mm, band_mm):
    """Grade a dimension of the repaired area against its band."""
    measured = require_real("measured_mm", measured_mm, minimum=0.0)
    low, high = require_band("dimension_band_mm", band_mm, minimum=0.0)
    under = measured < low - LENGTH_TOLERANCE_MM
    over = measured > high + LENGTH_TOLERANCE_MM
    return {
        "measured_mm": measured,
        "band_mm": (low, high),
        "under_band": under,
        "over_band": over,
        "acceptable": not (under or over),
    }


def grade_radiographic(void_fraction, max_void_fraction):
    """Grade a radiograph of the repaired connection on its void fraction."""
    voids = require_real("void_fraction", void_fraction, minimum=0.0)
    limit = require_real("max_void_fraction", max_void_fraction, minimum=0.0,
                         allow_equal=False)
    if voids > 1.0 + FRACTION_TOLERANCE:
        raise ValueError("void_fraction must not exceed 1.0, got %g" % voids)
    if limit > 1.0:
        raise ValueError("max_void_fraction must not exceed 1.0, got %g" % limit)
    excessive = voids > limit + FRACTION_TOLERANCE
    return {
        "void_fraction": voids,
        "max_void_fraction": limit,
        "excessive_voiding": excessive,
        "acceptable": not excessive,
    }


def assess_post_repair_verification(spec):
    """Verify a repaired area and return accept, reject or incomplete.

    spec keys: repair_kinds, optional hidden_connection, and a results mapping
    keyed by inspection name carrying the readings each grade function needs.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    if "repair_kinds" not in spec:
        raise ValueError("spec missing required key 'repair_kinds'")
    if "results" not in spec or not isinstance(spec["results"], dict):
        raise ValueError("spec must carry a 'results' mapping of inspection readings")

    required = required_inspection_set(
        spec["repair_kinds"], spec.get("hidden_connection", False)
    )
    results = spec["results"]
    performed = sorted(results)
    for name in performed:
        if name not in INSPECTIONS:
            raise ValueError(
                "results carries an unknown inspection %r; expected one of %s"
                % (name, ", ".join(INSPECTIONS))
            )
    missing = missing_inspections(required, performed)

    findings = []
    graded = {}

    if "visual" in results:
        record = results["visual"]
        if not isinstance(record, dict):
            raise ValueError("results['visual'] must be a mapping")
        for key in ("magnification_used", "smallest_feature_mm"):
            if key not in record:
                raise ValueError("results['visual'] missing key '%s'" % key)
        graded["visual"] = grade_visual(record["magnification_used"],
                                        record["smallest_feature_mm"])
        if graded["visual"]["under_magnified"]:
            findings.append(
                "visual inspection used %gx against the %gx the smallest feature needs"
                % (graded["visual"]["magnification_used"],
                   graded["visual"]["magnification_required"])
            )

    if "electrical" in results:
        record = results["electrical"]
        if not isinstance(record, dict):
            raise ValueError("results['electrical'] must be a mapping")
        for key in ("insulation_mohm", "min_insulation_mohm",
                    "path_resistance_mohm", "max_path_resistance_mohm"):
            if key not in record:
                raise ValueError("results['electrical'] missing key '%s'" % key)
        graded["electrical"] = grade_electrical(
            record["insulation_mohm"], record["min_insulation_mohm"],
            record["path_resistance_mohm"], record["max_path_resistance_mohm"],
        )
        if graded["electrical"]["insulation_low"]:
            findings.append(
                "insulation resistance %.3f MOhm is under the %.3f MOhm minimum"
                % (graded["electrical"]["insulation_mohm"],
                   graded["electrical"]["min_insulation_mohm"])
            )
        if graded["electrical"]["path_resistance_high"]:
            findings.append(
                "path resistance %.3f mOhm is over the %.3f mOhm maximum"
                % (graded["electrical"]["path_resistance_mohm"],
                   graded["electrical"]["max_path_resistance_mohm"])
            )

    if "dimensional" in results:
        record = results["dimensional"]
        if not isinstance(record, dict):
            raise ValueError("results['dimensional'] must be a mapping")
        for key in ("measured_mm", "band_mm"):
            if key not in record:
                raise ValueError("results['dimensional'] missing key '%s'" % key)
        graded["dimensional"] = grade_dimensional(record["measured_mm"],
                                                  record["band_mm"])
        if not graded["dimensional"]["acceptable"]:
            findings.append(
                "repaired area measures %.3f mm against the band %.3f-%.3f mm"
                % (graded["dimensional"]["measured_mm"],
                   graded["dimensional"]["band_mm"][0],
                   graded["dimensional"]["band_mm"][1])
            )

    if "radiographic" in results:
        record = results["radiographic"]
        if not isinstance(record, dict):
            raise ValueError("results['radiographic'] must be a mapping")
        for key in ("void_fraction", "max_void_fraction"):
            if key not in record:
                raise ValueError("results['radiographic'] missing key '%s'" % key)
        graded["radiographic"] = grade_radiographic(record["void_fraction"],
                                                    record["max_void_fraction"])
        if graded["radiographic"]["excessive_voiding"]:
            findings.append(
                "radiograph shows %.4f voiding against a limit of %.4f"
                % (graded["radiographic"]["void_fraction"],
                   graded["radiographic"]["max_void_fraction"])
            )

    for name in missing:
        findings.append("the repair owes a %s inspection that was not performed" % name)

    failed = [name for name, rec in graded.items() if not rec["acceptable"]]
    if failed:
        verdict = "reject"
    elif missing:
        verdict = "incomplete"
    else:
        verdict = "accept"

    return {
        "required_inspections": required,
        "performed_inspections": performed,
        "missing_inspections": missing,
        "graded": graded,
        "failed_inspections": sorted(failed),
        "verdict": verdict,
        "findings": findings,
    }
