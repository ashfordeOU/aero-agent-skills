"""Failed solar cell assemblies.

Anchor: ECSS-E-ST-20-08C clause 6.5.2. The procedure below is a paraphrase
into implementable steps; no standard text is reproduced.

The clause settles one question about an inspected cell assembly: is it
failed. The answer is disjunctive. A listed failure mode found on the unit
condemns it on its own -- the modes are not weighted against one another,
they are not traded off against the ones that came out clean, and a unit
showing one mode is not half-failed because the other seven were sound.

That shape has two consequences the implementation has to honour.

    one mode decides     a present mode makes the unit failed no matter
                         what the remaining modes did or did not show, so
                         the verdict short-circuits and never waits for a
                         complete examination
    silence is not a     a mode nobody examined is not a mode that came
    clean result         out clean; a unit with no present mode and an
                         unexamined mode is unevaluated, never sound

The catalogue mixes two bases. Some modes are seen -- a fracture is there
or it is not -- and the observation for those is a boolean. Others are
only visible as a quantity crossing a limit, and the observation for
those is a measurement graded against that limit. Handing a boolean to a
measured mode, or a number to an observed one, is an input defect rather
than a lenient reading, because a truthy number would condemn every unit
that was measured at all.

Limits are inclusive. A measurement landing exactly on the limit is not
the mode, so the comparison absorbs representation error instead of the
limit being nudged to make the arithmetic tidy.

The limit values below are declared project policy, not physical
constants; a project may substitute its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

__all__ = [
    "ASSEMBLY_FAILED",
    "ASSEMBLY_NOT_EVALUATED",
    "ASSEMBLY_SOUND",
    "DEFAULT_FAILURE_LIMITS",
    "FAILURE_MODES",
    "LOT_CLEAR",
    "LOT_HOLDS_FAILED_ASSEMBLIES",
    "LOT_NOT_EVALUATED",
    "MODE_ABSENT",
    "MODE_MEASURED",
    "MODE_NOT_EXAMINED",
    "MODE_OBSERVED",
    "MODE_PRESENT",
    "assess_failure_mode",
    "assess_cell_assembly",
    "assess_inspection_lot",
    "failure_mode_catalogue",
    "measured_modes",
    "normalize_mode",
    "observed_modes",
    "resolve_failure_limits",
]

MODE_OBSERVED = "observed"
MODE_MEASURED = "measured"

# The failure modes a cell assembly is examined for. An observed mode is
# seen or not seen; a measured mode is a quantity graded against a limit,
# either for rising above it or for falling below it.
FAILURE_MODES = {
    "cell-fracture": {"basis": MODE_OBSERVED, "direction": None, "limit": None},
    "coverglass-fracture": {
        "basis": MODE_OBSERVED,
        "direction": None,
        "limit": None,
    },
    "interconnector-fracture": {
        "basis": MODE_OBSERVED,
        "direction": None,
        "limit": None,
    },
    "solder-joint-separation": {
        "basis": MODE_OBSERVED,
        "direction": None,
        "limit": None,
    },
    "contact-metallization-lift": {
        "basis": MODE_OBSERVED,
        "direction": None,
        "limit": None,
    },
    "adhesive-delamination-area": {
        "basis": MODE_MEASURED,
        "direction": "above",
        "limit": "delamination_area_fraction",
    },
    "power-output-degradation": {
        "basis": MODE_MEASURED,
        "direction": "above",
        "limit": "power_loss_fraction",
    },
    "insulation-resistance-loss": {
        "basis": MODE_MEASURED,
        "direction": "below",
        "limit": "insulation_resistance_ohm",
    },
}

DEFAULT_FAILURE_LIMITS = {
    "delamination_area_fraction": 0.05,
    "power_loss_fraction": 0.02,
    "insulation_resistance_ohm": 1.0e8,
}

_FRACTION_LIMITS = ("delamination_area_fraction", "power_loss_fraction")

MODE_PRESENT = "mode-present"
MODE_ABSENT = "mode-absent"
MODE_NOT_EXAMINED = "mode-not-examined"

ASSEMBLY_FAILED = "assembly-failed"
ASSEMBLY_SOUND = "assembly-sound"
ASSEMBLY_NOT_EVALUATED = "assembly-not-evaluated"

LOT_HOLDS_FAILED_ASSEMBLIES = "lot-holds-failed-assemblies"
LOT_CLEAR = "lot-clear"
LOT_NOT_EVALUATED = "lot-not-evaluated"

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_non_negative(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return float(value)


def _require_positive(name, value):
    value = _require_non_negative(name, value)
    if value == 0.0:
        raise ValueError("%s must be greater than zero" % name)
    return value


def _identifier(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip()


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def failure_mode_catalogue():
    """Return the listed failure modes in catalogue order."""
    return tuple(FAILURE_MODES)


def observed_modes():
    """Return the modes settled by seeing them rather than measuring."""
    return tuple(
        mode
        for mode, entry in FAILURE_MODES.items()
        if entry["basis"] == MODE_OBSERVED
    )


def measured_modes():
    """Return the modes settled by a quantity crossing a limit."""
    return tuple(
        mode
        for mode, entry in FAILURE_MODES.items()
        if entry["basis"] == MODE_MEASURED
    )


def normalize_mode(mode):
    """Return a listed failure mode, refusing anything outside the list."""
    if not isinstance(mode, str):
        raise ValueError("failure mode must be a string, got %r" % (mode,))
    cleaned = mode.strip().lower()
    if cleaned not in FAILURE_MODES:
        raise ValueError(
            "unlisted failure mode %r; listed modes: %s"
            % (mode, ", ".join(FAILURE_MODES))
        )
    return cleaned


def resolve_failure_limits(limits=None):
    """Merge project limit overrides onto the declared defaults."""
    resolved = dict(DEFAULT_FAILURE_LIMITS)
    if limits is None:
        return resolved
    if not isinstance(limits, dict):
        raise ValueError("limits must be a mapping of limit name to value")
    unknown = sorted(set(limits) - set(DEFAULT_FAILURE_LIMITS))
    if unknown:
        raise ValueError(
            "unrecognized limit(s): %s; recognized: %s"
            % (", ".join(unknown), ", ".join(sorted(DEFAULT_FAILURE_LIMITS)))
        )
    for name, value in limits.items():
        resolved[name] = _require_positive(name, value)
        if name in _FRACTION_LIMITS and resolved[name] > 1.0:
            raise ValueError(
                "%s is a fraction of the whole and cannot exceed 1.0, got %r"
                % (name, value)
            )
    return resolved


def assess_failure_mode(mode, observation, limits=None):
    """Reduce one observation to present, absent or never examined."""
    name = normalize_mode(mode)
    entry = FAILURE_MODES[name]
    resolved = resolve_failure_limits(limits)
    record = {
        "mode": name,
        "basis": entry["basis"],
        "direction": entry["direction"],
        "measurement": None,
        "limit": None,
        "status": MODE_NOT_EXAMINED,
        "findings": [],
    }
    if observation is None:
        record["findings"].append(
            "mode '%s' was never examined, which is not the same as finding "
            "it absent" % name
        )
        return record

    if entry["basis"] == MODE_OBSERVED:
        if not isinstance(observation, bool):
            raise ValueError(
                "mode '%s' is settled by observation and takes True or False, "
                "got %r" % (name, observation)
            )
        record["status"] = MODE_PRESENT if observation else MODE_ABSENT
        if observation:
            record["findings"].append(
                "mode '%s' was found on the assembly" % name
            )
        return record

    if isinstance(observation, bool):
        raise ValueError(
            "mode '%s' is settled by a measurement graded against a limit, "
            "not by True or False" % name
        )
    value = _require_non_negative("%s measurement" % name, observation)
    limit = resolved[entry["limit"]]
    record["measurement"] = value
    record["limit"] = limit
    if entry["direction"] == "above":
        present = not _at_most(value, limit)
        crossed = "rose to %.6g, above the %.6g limit" % (value, limit)
    else:
        present = not _at_least(value, limit)
        crossed = "fell to %.6g, below the %.6g limit" % (value, limit)
    record["status"] = MODE_PRESENT if present else MODE_ABSENT
    if present:
        record["findings"].append("mode '%s' %s" % (name, crossed))
    return record


def assess_cell_assembly(spec):
    """Settle whether one cell assembly is treated as failed.

    spec keys: assembly_id, observations (mode -> observation);
    optional limits (limit name -> value).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("assembly_id", "observations"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    assembly_id = _identifier(spec["assembly_id"], "assembly_id")
    observations = spec["observations"]
    if not isinstance(observations, dict):
        raise ValueError("observations must be a mapping of mode to observation")
    limits = resolve_failure_limits(spec.get("limits"))

    seen = {}
    for raw, value in observations.items():
        mode = normalize_mode(raw)
        if mode in seen:
            raise ValueError("mode '%s' was observed twice for one assembly" % mode)
        seen[mode] = value

    modes = []
    present = []
    unexamined = []
    findings = []
    for mode in failure_mode_catalogue():
        record = assess_failure_mode(mode, seen.get(mode), limits)
        modes.append(record)
        if record["status"] == MODE_PRESENT:
            present.append(mode)
        elif record["status"] == MODE_NOT_EXAMINED:
            unexamined.append(mode)
        findings.extend(record["findings"])

    if present:
        verdict = ASSEMBLY_FAILED
        failed = True
        findings.insert(
            0,
            "assembly %s is treated as failed; %d listed mode(s) present"
            % (assembly_id, len(present)),
        )
    elif unexamined:
        verdict = ASSEMBLY_NOT_EVALUATED
        failed = None
    else:
        verdict = ASSEMBLY_SOUND
        failed = False

    return {
        "assembly_id": assembly_id,
        "modes": tuple(modes),
        "present_modes": tuple(present),
        "unexamined_modes": tuple(unexamined),
        "verdict": verdict,
        "failed": failed,
        "findings": findings,
    }


def assess_inspection_lot(spec):
    """Roll the assemblies of one inspection lot into a tally.

    spec keys: lot_id, assemblies (a sequence of assembly specs);
    optional limits applied to every assembly that declares none.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("lot_id", "assemblies"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    lot_id = _identifier(spec["lot_id"], "lot_id")
    assemblies = spec["assemblies"]
    if not isinstance(assemblies, (list, tuple)) or not assemblies:
        raise ValueError("assemblies must be a non-empty sequence of assembly specs")
    lot_limits = spec.get("limits")

    results = []
    seen = set()
    for index, item in enumerate(assemblies):
        if not isinstance(item, dict):
            raise ValueError("assemblies[%d] must be a mapping" % index)
        case = dict(item)
        if lot_limits is not None and "limits" not in case:
            case["limits"] = lot_limits
        result = assess_cell_assembly(case)
        if result["assembly_id"] in seen:
            raise ValueError(
                "assembly %s appears twice in lot %s"
                % (result["assembly_id"], lot_id)
            )
        seen.add(result["assembly_id"])
        results.append(result)

    failed = tuple(r["assembly_id"] for r in results if r["verdict"] == ASSEMBLY_FAILED)
    sound = tuple(r["assembly_id"] for r in results if r["verdict"] == ASSEMBLY_SOUND)
    open_units = tuple(
        r["assembly_id"] for r in results if r["verdict"] == ASSEMBLY_NOT_EVALUATED
    )
    settled = len(failed) + len(sound)
    failed_fraction = float(len(failed)) / float(settled) if settled else None

    findings = []
    if failed:
        findings.append(
            "lot %s holds %d failed assembly(ies): %s"
            % (lot_id, len(failed), ", ".join(failed))
        )
    if open_units:
        findings.append(
            "lot %s holds %d assembly(ies) with an unexamined mode: %s"
            % (lot_id, len(open_units), ", ".join(open_units))
        )

    if failed:
        verdict = LOT_HOLDS_FAILED_ASSEMBLIES
    elif open_units:
        verdict = LOT_NOT_EVALUATED
    else:
        verdict = LOT_CLEAR

    return {
        "lot_id": lot_id,
        "assemblies": tuple(results),
        "failed_assembly_ids": failed,
        "sound_assembly_ids": sound,
        "unevaluated_assembly_ids": open_units,
        "settled_count": settled,
        "failed_fraction": failed_fraction,
        "verdict": verdict,
        "findings": findings,
    }
