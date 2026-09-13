#!/usr/bin/env python3
"""Spacecraft provisions for sensitive plasma-measurement instruments.

Anchor: ECSS-E-ST-20-06C clause 6.7 (paraphrased into an implementable
procedure; no standard text is reproduced).

Rule implemented here: a mission carrying plasma-measurement instruments owes
provisions beyond the baseline charging-control set, because the spacecraft
itself perturbs the measurement. The instrument with the lowest measured
particle-energy drives a spacecraft-level floating-potential limit and a
surface-potential uniformity limit; probes need booms that clear the
photoelectron sheath; and where the passive design cannot hold the potential,
an active-potential-control emitter is required and has to be sized from the
net collected current.

Deterministic, offline, stdlib only.
"""

import math

# Absorbs floating-point representation error when a computed quantity is
# compared against a derived limit. An exact match is compliant; this never
# relaxes the engineering limit itself.
REPR_TOL = 1e-9

# Instrument catalogue. plasma-sensitive instruments carry clause 6.7
# provisions; the distortion allowance is the fraction of the lowest measured
# particle-energy that the body potential may consume.
INSTRUMENT_CATALOGUE = {
    "electron-spectrometer": {
        "plasma-sensitive": True,
        "distortion-allowance": 0.10,
        "needs-boom": False,
        "debye-multiple": 0.0,
    },
    "ion-spectrometer": {
        "plasma-sensitive": True,
        "distortion-allowance": 0.10,
        "needs-boom": False,
        "debye-multiple": 0.0,
    },
    "langmuir-probe": {
        "plasma-sensitive": True,
        "distortion-allowance": 0.05,
        "needs-boom": True,
        "debye-multiple": 3.0,
    },
    "electric-field-double-probe": {
        "plasma-sensitive": True,
        "distortion-allowance": 0.02,
        "needs-boom": True,
        "debye-multiple": 5.0,
    },
    "thermal-ion-analyser": {
        "plasma-sensitive": True,
        "distortion-allowance": 0.05,
        "needs-boom": False,
        "debye-multiple": 0.0,
    },
    "star-tracker": {
        "plasma-sensitive": False,
        "distortion-allowance": 1.0,
        "needs-boom": False,
        "debye-multiple": 0.0,
    },
    "imaging-radiometer": {
        "plasma-sensitive": False,
        "distortion-allowance": 1.0,
        "needs-boom": False,
        "debye-multiple": 0.0,
    },
}

# Fraction of the tolerable body potential allowed as surface-potential spread
# across the exposed skin; the uniformity limit is the tighter of the two.
UNIFORMITY_FRACTION = 0.5

# Minimum conductive-surface coverage of the exposed outer area for an
# electrostatically-clean spacecraft carrying plasma instruments.
MIN_CONDUCTIVE_COVERAGE = 0.95

# Control margin applied to the net collected current when sizing an emitter.
DEFAULT_CONTROL_MARGIN = 1.5


def _as_float(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (label, value))
    out = float(value)
    if math.isnan(out) or math.isinf(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return out


def _within(value, limit):
    """True when value <= limit, an exact match included."""
    if value <= limit:
        return True
    return math.isclose(value, limit, rel_tol=REPR_TOL, abs_tol=0.0)


def _reaches(value, required):
    """True when value >= required, an exact match included."""
    if value >= required:
        return True
    return math.isclose(value, required, rel_tol=REPR_TOL, abs_tol=0.0)


def categorize_instrument(kind):
    """Return the catalogue entry for an instrument kind.

    Raises ValueError for an unrecognized kind.
    """
    if not isinstance(kind, str) or not kind.strip():
        raise ValueError("instrument kind must be a non-empty string, got %r" % (kind,))
    key = kind.strip().lower().replace("_", "-").replace(" ", "-")
    if key not in INSTRUMENT_CATALOGUE:
        raise ValueError(
            "unrecognized instrument kind %r (known: %s)"
            % (kind, ", ".join(sorted(INSTRUMENT_CATALOGUE)))
        )
    entry = dict(INSTRUMENT_CATALOGUE[key])
    entry["kind"] = key
    return entry


def tolerable_body_potential_v(min_energy_ev, allowance):
    """Body potential an instrument tolerates, in volts.

    A singly-charged particle of energy E eV is shifted by the body potential
    in volts, so the tolerable potential is the allowed fraction of E.
    """
    energy = _as_float(min_energy_ev, "lowest measured particle-energy")
    if energy <= 0.0:
        raise ValueError("lowest measured particle-energy must be positive, got %r" % (energy,))
    frac = _as_float(allowance, "distortion allowance")
    if not 0.0 < frac <= 1.0:
        raise ValueError("distortion allowance must be in (0, 1], got %r" % (frac,))
    return energy * frac


def measurement_distortion(potential_v, min_energy_ev):
    """Fractional energy distortion imposed on the lowest measured channel."""
    energy = _as_float(min_energy_ev, "lowest measured particle-energy")
    if energy <= 0.0:
        raise ValueError("lowest measured particle-energy must be positive, got %r" % (energy,))
    return abs(_as_float(potential_v, "potential")) / energy


def normalize_instrument(instrument):
    """Validate one payload instrument record and derive its limits."""
    if not isinstance(instrument, dict):
        raise ValueError("instrument must be a mapping, got %r" % (type(instrument).__name__,))
    ident = instrument.get("id")
    if not isinstance(ident, str) or not ident.strip():
        raise ValueError("instrument id must be a non-empty string, got %r" % (ident,))
    entry = categorize_instrument(instrument.get("kind"))
    rec = {
        "id": ident.strip(),
        "kind": entry["kind"],
        "plasma-sensitive": entry["plasma-sensitive"],
        "debye-multiple": entry["debye-multiple"],
        "needs-boom": entry["needs-boom"],
    }
    if not entry["plasma-sensitive"]:
        rec["min-energy-ev"] = None
        rec["tolerable-body-potential-v"] = None
        rec["uniformity-limit-v"] = None
        rec["boom-length-m"] = None
        return rec
    allowance = _as_float(
        instrument.get("distortion-allowance", entry["distortion-allowance"]),
        "instrument %s distortion-allowance" % ident,
    )
    tolerable = tolerable_body_potential_v(instrument.get("min-energy-ev"), allowance)
    rec["min-energy-ev"] = _as_float(instrument.get("min-energy-ev"), "min-energy-ev")
    rec["distortion-allowance"] = allowance
    rec["tolerable-body-potential-v"] = tolerable
    rec["uniformity-limit-v"] = tolerable * UNIFORMITY_FRACTION
    if entry["needs-boom"]:
        boom = _as_float(instrument.get("boom-length-m"), "instrument %s boom-length-m" % ident)
        if boom < 0.0:
            raise ValueError("instrument %s boom-length-m must be non-negative" % ident)
        rec["boom-length-m"] = boom
    else:
        rec["boom-length-m"] = None
    return rec


def required_boom_length_m(debye_multiple, debye_length_m, photoelectron_cloud_m):
    """Boom length needed to clear the sheath: debye multiple plus cloud extent."""
    mult = _as_float(debye_multiple, "debye multiple")
    debye = _as_float(debye_length_m, "debye-length")
    cloud = _as_float(photoelectron_cloud_m, "photoelectron-cloud extent")
    if mult < 0.0:
        raise ValueError("debye multiple must be non-negative, got %r" % (mult,))
    if debye <= 0.0:
        raise ValueError("debye-length must be positive, got %r" % (debye,))
    if cloud < 0.0:
        raise ValueError("photoelectron-cloud extent must be non-negative, got %r" % (cloud,))
    return mult * debye + cloud


def surface_findings(surface):
    """Check the exposed outer skin for electrostatic cleanliness.

    Requires conductive-area coverage at or above the minimum, every
    conductive area bonded to the common reference, and a declared
    surface-potential spread.
    """
    if not isinstance(surface, dict):
        raise ValueError("surface must be a mapping, got %r" % (type(surface).__name__,))
    total = _as_float(surface.get("exposed-area-m2"), "surface exposed-area-m2")
    conductive = _as_float(surface.get("conductive-area-m2"), "surface conductive-area-m2")
    if total <= 0.0:
        raise ValueError("surface exposed-area-m2 must be positive, got %r" % (total,))
    if conductive < 0.0 or conductive > total:
        raise ValueError("surface conductive-area-m2 must lie in [0, exposed-area-m2]")
    unbonded = surface.get("unbonded-conductive-areas", 0)
    if isinstance(unbonded, bool) or not isinstance(unbonded, int) or unbonded < 0:
        raise ValueError("surface unbonded-conductive-areas must be a non-negative integer")
    spread = _as_float(surface.get("potential-spread-v"), "surface potential-spread-v")
    if spread < 0.0:
        raise ValueError("surface potential-spread-v must be non-negative")
    coverage = conductive / total
    findings = []
    if not _reaches(coverage, MIN_CONDUCTIVE_COVERAGE):
        findings.append(
            "conductive-surface coverage %.4f below the required %.4f"
            % (coverage, MIN_CONDUCTIVE_COVERAGE)
        )
    if unbonded:
        findings.append("%d conductive area(s) not bonded to the common reference" % unbonded)
    return {"coverage": coverage, "potential-spread-v": spread, "findings": findings}


def emitter_sizing(net_collected_current_a, device_capability_a, margin=DEFAULT_CONTROL_MARGIN):
    """Size an active-potential-control emitter against the net collected current."""
    net = _as_float(net_collected_current_a, "net collected current")
    if net <= 0.0:
        raise ValueError("net collected current must be positive, got %r" % (net,))
    capability = _as_float(device_capability_a, "emitter capability")
    if capability < 0.0:
        raise ValueError("emitter capability must be non-negative, got %r" % (capability,))
    fac = _as_float(margin, "control margin")
    if fac < 1.0:
        raise ValueError("control margin must be >= 1.0, got %r" % (fac,))
    required = net * fac
    return {
        "required-current-a": required,
        "capability-a": capability,
        "adequate": _reaches(capability, required),
        "margin-a": capability - required,
    }


def evaluate_instrument(instrument, design):
    """Check one instrument against a candidate spacecraft design."""
    rec = instrument if isinstance(instrument, dict) and "plasma-sensitive" in instrument else normalize_instrument(instrument)
    if not isinstance(design, dict):
        raise ValueError("design must be a mapping, got %r" % (type(design).__name__,))
    if not rec["plasma-sensitive"]:
        return {"instrument": rec["id"], "kind": rec["kind"], "applicable": False, "findings": []}
    body_v = abs(_as_float(design.get("body-potential-v"), "design body-potential-v"))
    surface = surface_findings(design.get("surface"))
    findings = list(surface["findings"])
    if not _within(body_v, rec["tolerable-body-potential-v"]):
        findings.append(
            "body potential %.6g V exceeds the %.6g V tolerated by %s"
            % (body_v, rec["tolerable-body-potential-v"], rec["id"])
        )
    if not _within(surface["potential-spread-v"], rec["uniformity-limit-v"]):
        findings.append(
            "surface-potential spread %.6g V exceeds the %.6g V uniformity limit"
            % (surface["potential-spread-v"], rec["uniformity-limit-v"])
        )
    if rec["needs-boom"]:
        required = required_boom_length_m(
            rec["debye-multiple"],
            design.get("debye-length-m"),
            design.get("photoelectron-cloud-m"),
        )
        if not _reaches(rec["boom-length-m"], required):
            findings.append(
                "boom %.6g m short of the %.6g m needed to clear the photoelectron sheath"
                % (rec["boom-length-m"], required)
            )
    return {
        "instrument": rec["id"],
        "kind": rec["kind"],
        "applicable": True,
        "distortion": measurement_distortion(body_v, rec["min-energy-ev"]),
        "tolerable-body-potential-v": rec["tolerable-body-potential-v"],
        "uniformity-limit-v": rec["uniformity-limit-v"],
        "findings": findings,
        "compliant": not findings,
    }


def assess_mission_provisions(instruments, design):
    """Union the clause 6.7 provisions across the payload.

    Returns the driving instrument, the spacecraft-level limits it sets, the
    per-instrument results, whether active-potential-control is required and
    the aggregate compliance verdict.
    """
    if not isinstance(instruments, (list, tuple)) or not instruments:
        raise ValueError("instruments must be a non-empty list")
    seen = set()
    records = []
    for entry in instruments:
        rec = normalize_instrument(entry)
        if rec["id"] in seen:
            raise ValueError("duplicate instrument id %r" % rec["id"])
        seen.add(rec["id"])
        records.append(rec)
    sensitive = [r for r in records if r["plasma-sensitive"]]
    if not sensitive:
        return {
            "driving-instrument": None,
            "applicable": False,
            "results": [evaluate_instrument(r, design) for r in records],
            "active-control-required": False,
            "effective-body-potential-v": None,
            "findings": [],
            "compliant": True,
        }
    driver = min(sensitive, key=lambda r: (r["tolerable-body-potential-v"], r["id"]))
    passive_v = abs(_as_float(design.get("body-potential-v"), "design body-potential-v"))
    active_required = not _within(passive_v, driver["tolerable-body-potential-v"])
    findings = []
    emitter = None
    effective_v = passive_v
    if active_required:
        capability = design.get("emitter-capability-a")
        if capability is None:
            findings.append("active-potential-control required but no emitter is on record")
        else:
            emitter = emitter_sizing(design.get("net-collected-current-a"), capability)
            if not emitter["adequate"]:
                findings.append(
                    "emitter capability %.6g A below the %.6g A required to control the potential"
                    % (emitter["capability-a"], emitter["required-current-a"])
                )
            elif design.get("controlled-body-potential-v") is None:
                findings.append(
                    "emitter is adequately sized but the controlled body potential is not predicted"
                )
            else:
                effective_v = abs(
                    _as_float(
                        design.get("controlled-body-potential-v"),
                        "design controlled-body-potential-v",
                    )
                )
    effective_design = dict(design)
    effective_design["body-potential-v"] = effective_v
    results = [evaluate_instrument(r, effective_design) for r in records]
    for result in results:
        findings.extend(result["findings"])
    return {
        "driving-instrument": driver["id"],
        "applicable": True,
        "body-potential-limit-v": driver["tolerable-body-potential-v"],
        "uniformity-limit-v": driver["uniformity-limit-v"],
        "passive-body-potential-v": passive_v,
        "effective-body-potential-v": effective_v,
        "results": results,
        "active-control-required": active_required,
        "emitter": emitter,
        "findings": sorted(set(findings)),
        "compliant": not findings,
    }
