"""Disposition of a material that failed its flammability screening.

Anchor: ECSS-Q-ST-70-21C, evaluation of a failed screening (deciding between
rejecting the material, redesigning the installation it sits in, and running a
further round of testing). Paraphrased into an implementable procedure; no
standard text is reproduced.

Procedure implemented here
--------------------------
1. Rank the observed failure modes by severity and let the most severe one
   govern. A set that both over-burned and shed burning material is decided by
   the burning material.
2. Refuse a use-as-is rationale behind a severe mode. A drip that ignited the
   indicator and a specimen that never self-extinguished describe behaviour no
   paperwork changes.
3. Size the further round of testing from the observed pass fraction: an
   extended set has to be large enough that a failure at the observed rate
   would be expected to appear in it again.
4. Emit the disposition with the actions and the evidence it carries, so the
   route out of a failure is auditable rather than asserted.
"""

import math

__all__ = [
    "FAILURE_SEVERITY",
    "SEVERE_MODES",
    "DEFAULT_MIN_SPECIMENS",
    "MAX_PRACTICAL_FACTOR",
    "MITIGATION_EXCEEDANCE_CEILING",
    "validate_failure_record",
    "governing_mode",
    "observed_pass_fraction",
    "required_retest_specimens",
    "decide_disposition",
    "assess_failed_material",
]

# The observed failure modes, ranked. A higher number is the more severe
# behaviour and governs the disposition when several are present.
FAILURE_SEVERITY = {
    "drip-ignition": 5,
    "full-consumption": 4,
    "burn-length-exceeded": 3,
    "flaming-drips": 2,
    "after-flame-exceeded": 1,
}

# Modes describing behaviour that no rationale on paper changes.
SEVERE_MODES = ("drip-ignition", "full-consumption")

DEFAULT_MIN_SPECIMENS = 3

# Beyond this multiple of the class minimum an extended set stops being a test
# campaign and becomes a way of waiting for a favourable draw.
MAX_PRACTICAL_FACTOR = 5

# A mitigation can carry a marginal exceedance, not an arbitrary one.
MITIGATION_EXCEEDANCE_CEILING = 0.10


def _count(value, label, minimum=0):
    """Return value as an integer count, refusing anything else."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value < minimum:
        raise ValueError("%s must be at least %d, got %d" % (label, minimum, value))
    return value


def _flag(value, label):
    """Return value as a boolean, refusing anything else."""
    if not isinstance(value, bool):
        raise ValueError("%s must be boolean, got %r" % (label, value))
    return value


def validate_failure_record(record):
    """Return one normalised failed-screening record."""
    if not isinstance(record, dict):
        raise ValueError("a failure record must be a mapping")
    material = record.get("material")
    if not isinstance(material, str) or not material.strip():
        raise ValueError("the record must name the material")
    modes = record.get("modes")
    if not isinstance(modes, (list, tuple)) or not modes:
        raise ValueError("the record must list at least one observed failure mode")
    seen = []
    for mode in modes:
        if mode not in FAILURE_SEVERITY:
            raise ValueError("unknown failure mode %r; known modes are %s"
                             % (mode, ", ".join(sorted(FAILURE_SEVERITY))))
        if mode not in seen:
            seen.append(mode)
    total = _count(record.get("total_specimens"), "total_specimens", minimum=1)
    failed = _count(record.get("failed_specimens"), "failed_specimens", minimum=1)
    if failed > total:
        raise ValueError("failed_specimens %d exceeds total_specimens %d" % (failed, total))
    exceedance = record.get("exceedance_ratio", 0.0)
    if isinstance(exceedance, bool) or not isinstance(exceedance, (int, float)):
        raise ValueError("exceedance_ratio must be a real number")
    exceedance = float(exceedance)
    if not math.isfinite(exceedance) or exceedance < 0.0:
        raise ValueError("exceedance_ratio must be non-negative and finite")
    rationale = record.get("use_as_is_rationale_ref")
    if rationale is not None and (not isinstance(rationale, str) or not rationale.strip()):
        raise ValueError("use_as_is_rationale_ref must be a non-empty string when given")
    return {
        "material": material.strip(),
        "modes": seen,
        "total_specimens": total,
        "failed_specimens": failed,
        "exceedance_ratio": exceedance,
        "configuration_changeable": _flag(record.get("configuration_changeable", False),
                                          "configuration_changeable"),
        "mitigation_available": _flag(record.get("mitigation_available", False),
                                      "mitigation_available"),
        "use_as_is_requested": _flag(record.get("use_as_is_requested", False),
                                     "use_as_is_requested"),
        "use_as_is_rationale_ref": rationale.strip() if rationale else None,
    }


def governing_mode(modes):
    """Return the most severe of the observed modes, ties broken by name."""
    if not isinstance(modes, (list, tuple)) or not modes:
        raise ValueError("modes must be a non-empty sequence")
    for mode in modes:
        if mode not in FAILURE_SEVERITY:
            raise ValueError("unknown failure mode %r" % (mode,))
    return sorted(modes, key=lambda m: (-FAILURE_SEVERITY[m], m))[0]


def observed_pass_fraction(total_specimens, failed_specimens):
    """Return the fraction of the burned set that passed."""
    total = _count(total_specimens, "total_specimens", minimum=1)
    failed = _count(failed_specimens, "failed_specimens", minimum=0)
    if failed > total:
        raise ValueError("failed_specimens %d exceeds total_specimens %d" % (failed, total))
    return (total - failed) / float(total)


def required_retest_specimens(total_specimens, failed_specimens,
                              min_specimens=DEFAULT_MIN_SPECIMENS):
    """Size an extended set from the observed pass fraction.

    Returns the specimen count an extended set owes, or None when the observed
    behaviour gives no basis for a retest of the same configuration.
    """
    minimum = _count(min_specimens, "min_specimens", minimum=1)
    total = _count(total_specimens, "total_specimens", minimum=1)
    failed = _count(failed_specimens, "failed_specimens", minimum=0)
    if failed > total:
        raise ValueError("failed_specimens %d exceeds total_specimens %d" % (failed, total))
    passed = total - failed
    if passed <= 0:
        return None
    # Smallest n with n * passed >= minimum * total, i.e. an extended set that
    # still yields the class minimum of clean specimens at the observed rate.
    # Integer arithmetic throughout, so the size does not depend on how a
    # platform rounds a division.
    needed = -(-(minimum * total) // passed)
    if needed > minimum * MAX_PRACTICAL_FACTOR:
        return None
    return needed


def decide_disposition(record, min_specimens=DEFAULT_MIN_SPECIMENS):
    """Decide the disposition of one failed screening and name what it carries."""
    entry = validate_failure_record(record)
    minimum = _count(min_specimens, "min_specimens", minimum=1)
    mode = governing_mode(entry["modes"])
    severe = mode in SEVERE_MODES
    findings = []
    actions = []
    evidence = []
    if entry["use_as_is_requested"]:
        if severe:
            findings.append("use-as-is refused: %s describes behaviour a rationale "
                            "does not change" % mode)
        elif entry["use_as_is_rationale_ref"] is None:
            findings.append("use-as-is requested with no rationale reference behind it")
    retest_size = required_retest_specimens(entry["total_specimens"],
                                            entry["failed_specimens"], minimum)
    isolated = entry["failed_specimens"] * 2 <= entry["total_specimens"]
    if severe:
        if entry["configuration_changeable"]:
            disposition = "redesign-installation"
            actions.append("remove the material from the exposed installation or "
                           "interpose a barrier, then screen the changed build")
            evidence.append("changed-configuration screening run")
        else:
            disposition = "reject"
            actions.append("withdraw the material from this application")
            evidence.append("materials-list update and replacement selection")
    elif entry["failed_specimens"] == entry["total_specimens"]:
        if entry["configuration_changeable"]:
            disposition = "configuration-change-and-retest"
            actions.append("change the installation the specimens represent, then "
                           "screen a fresh set of at least %d specimens" % minimum)
            evidence.append("changed-configuration screening run")
        else:
            disposition = "reject"
            actions.append("withdraw the material from this application")
            evidence.append("materials-list update and replacement selection")
    elif isolated and retest_size is not None:
        disposition = "retest-extended-set"
        actions.append("burn an extended set of %d specimens from the same build"
                       % retest_size)
        evidence.append("extended-set screening run with the specimen count justified")
    elif entry["configuration_changeable"]:
        disposition = "configuration-change-and-retest"
        actions.append("change the installation the specimens represent, then "
                       "screen a fresh set of at least %d specimens" % minimum)
        evidence.append("changed-configuration screening run")
    elif (entry["mitigation_available"]
          and entry["exceedance_ratio"] <= MITIGATION_EXCEEDANCE_CEILING):
        disposition = "accept-with-mitigation"
        actions.append("apply the declared mitigation and record it against the "
                       "installation")
        evidence.append("mitigation description and a hazard assessment of the "
                        "residual exceedance")
    else:
        disposition = "reject"
        actions.append("withdraw the material from this application")
        evidence.append("materials-list update and replacement selection")
    if not severe and not isolated and entry["failed_specimens"] < entry["total_specimens"]:
        findings.append("%d of %d specimens failed; a majority failure is the material "
                        "behaving as it does, not an unlucky draw, so an extended set "
                        "of the same build is not the route"
                        % (entry["failed_specimens"], entry["total_specimens"]))
    return {
        "material": entry["material"],
        "governing_mode": mode,
        "severe": severe,
        "isolated_failure": isolated,
        "pass_fraction": observed_pass_fraction(entry["total_specimens"],
                                                entry["failed_specimens"]),
        "retest_specimens": retest_size,
        "disposition": disposition,
        "actions": actions,
        "evidence_required": evidence,
        "findings": findings,
    }


def assess_failed_material(spec):
    """Run the full failed-screening disposition assessment.

    spec keys: record (the failed-screening record), optional min_specimens.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    if "record" not in spec:
        raise ValueError("spec missing required key 'record'")
    result = decide_disposition(spec["record"], spec.get("min_specimens",
                                                         DEFAULT_MIN_SPECIMENS))
    result["closed"] = result["disposition"] in ("reject", "accept-with-mitigation")
    return result
