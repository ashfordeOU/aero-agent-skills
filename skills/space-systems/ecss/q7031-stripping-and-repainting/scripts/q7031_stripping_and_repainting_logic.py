#!/usr/bin/env python3
"""Stripping an existing paint system and re-painting the part underneath.

Anchor: ECSS-Q-ST-70-31C, the Rework clause on stripping and re-painting. The
procedure below is a paraphrased, implementable restatement -- no verbatim
standard text. Offline, deterministic, Python standard library only.

A strip is a hardware operation, not a cleaning step. The method has to be
compatible with the substrate it is pointed at, the cumulative loss it leaves
has to stay inside the wall the drawing keeps, the surface it hands over has to
land in the roughness window the new primer needs, and the primer and topcoat
going back on have to be compatible with the substrate and with each other.
This module grades all four and issues the strip-and-repaint disposition.
"""

import math

__all__ = [
    "SUBSTRATES",
    "STRIP_METHODS",
    "PRIMER_FAMILIES",
    "validate_substrate",
    "validate_method",
    "method_permitted_for_substrate",
    "cumulative_material_loss_um",
    "remaining_wall_margin_um",
    "strip_cycles_remaining",
    "roughness_within_window",
    "repaint_system_findings",
    "assess_strip_and_repaint",
    "assess_strip_campaign",
]

# A loss that lands exactly on the allowed wall loss is inside it, and a
# decimal loss per cycle multiplied by an integer count lands a few ULP either
# side of a decimal bound depending on the maths library. These tolerances
# absorb that and nothing else; the wall the drawing keeps never moves.
STRIP_REL_TOL = 1e-9
STRIP_ABS_TOL = 1e-12

SUBSTRATES = (
    "aluminium-alloy",
    "titanium-alloy",
    "magnesium-alloy",
    "stainless-steel",
    "cfrp",
    "gfrp",
)

STRIP_METHODS = (
    "chemical-alkaline",
    "chemical-solvent",
    "abrasive-blast",
    "plastic-media-blast",
    "mechanical-abrasion",
    "laser-ablation",
)

# permitted   -- the method may be used under the qualified procedure
# conditional -- usable only with an approved procedure and a witness coupon
# prohibited  -- the method attacks the substrate and is refused outright
METHOD_MATRIX = {
    "aluminium-alloy": {
        "chemical-alkaline": "prohibited",
        "chemical-solvent": "permitted",
        "abrasive-blast": "conditional",
        "plastic-media-blast": "permitted",
        "mechanical-abrasion": "permitted",
        "laser-ablation": "conditional",
    },
    "titanium-alloy": {
        "chemical-alkaline": "conditional",
        "chemical-solvent": "permitted",
        "abrasive-blast": "conditional",
        "plastic-media-blast": "permitted",
        "mechanical-abrasion": "permitted",
        "laser-ablation": "conditional",
    },
    "magnesium-alloy": {
        "chemical-alkaline": "prohibited",
        "chemical-solvent": "conditional",
        "abrasive-blast": "prohibited",
        "plastic-media-blast": "conditional",
        "mechanical-abrasion": "conditional",
        "laser-ablation": "prohibited",
    },
    "stainless-steel": {
        "chemical-alkaline": "permitted",
        "chemical-solvent": "permitted",
        "abrasive-blast": "permitted",
        "plastic-media-blast": "permitted",
        "mechanical-abrasion": "permitted",
        "laser-ablation": "permitted",
    },
    "cfrp": {
        "chemical-alkaline": "prohibited",
        "chemical-solvent": "prohibited",
        "abrasive-blast": "prohibited",
        "plastic-media-blast": "conditional",
        "mechanical-abrasion": "conditional",
        "laser-ablation": "conditional",
    },
    "gfrp": {
        "chemical-alkaline": "prohibited",
        "chemical-solvent": "prohibited",
        "abrasive-blast": "prohibited",
        "plastic-media-blast": "conditional",
        "mechanical-abrasion": "conditional",
        "laser-ablation": "conditional",
    },
}

# Which primer family bonds to which substrate, and which topcoats that primer
# will carry. A system is compatible only when both halves hold.
PRIMER_FAMILIES = {
    "epoxy-primer": {
        "substrates": ("aluminium-alloy", "titanium-alloy", "stainless-steel", "cfrp", "gfrp"),
        "topcoats": ("polyurethane-topcoat", "silicone-topcoat", "inorganic-black-topcoat"),
    },
    "chromate-free-etch-primer": {
        "substrates": ("aluminium-alloy", "magnesium-alloy"),
        "topcoats": ("polyurethane-topcoat", "silicone-topcoat"),
    },
    "silicate-primer": {
        "substrates": ("titanium-alloy", "stainless-steel"),
        "topcoats": ("inorganic-white-topcoat", "inorganic-black-topcoat"),
    },
}


def _finite_number(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return number


def _at_or_below(value, bound):
    if value <= bound:
        return True
    return math.isclose(value, bound, rel_tol=STRIP_REL_TOL, abs_tol=STRIP_ABS_TOL)


def validate_substrate(substrate):
    """Normalize the substrate the strip is pointed at."""
    if not isinstance(substrate, str) or not substrate.strip():
        raise ValueError("substrate must be a non-empty string")
    key = substrate.strip().lower()
    if key not in SUBSTRATES:
        raise ValueError("unrecognized substrate: %r" % (substrate,))
    return key


def validate_method(method):
    """Normalize the stripping method proposed."""
    if not isinstance(method, str) or not method.strip():
        raise ValueError("method must be a non-empty string")
    key = method.strip().lower()
    if key not in STRIP_METHODS:
        raise ValueError("unrecognized stripping method: %r" % (method,))
    return key


def method_permitted_for_substrate(method, substrate):
    """Return permitted, conditional or prohibited for this method and substrate."""
    return METHOD_MATRIX[validate_substrate(substrate)][validate_method(method)]


def cumulative_material_loss_um(cycles, loss_per_cycle_um, prior_loss_um=0.0):
    """Substrate lost after this strip, counting what earlier strips already took."""
    if isinstance(cycles, bool) or not isinstance(cycles, int):
        raise ValueError("cycles must be an integer, got %r" % (cycles,))
    if cycles < 1:
        raise ValueError("a strip is at least one cycle, got %r" % (cycles,))
    per_cycle = _finite_number(loss_per_cycle_um, "loss_per_cycle_um")
    prior = _finite_number(prior_loss_um, "prior_loss_um")
    if per_cycle < 0.0:
        raise ValueError("loss per cycle cannot be negative, got %r" % (loss_per_cycle_um,))
    if prior < 0.0:
        raise ValueError("prior loss cannot be negative, got %r" % (prior_loss_um,))
    return prior + cycles * per_cycle


def remaining_wall_margin_um(nominal_um, minimum_um, cumulative_loss_um):
    """Wall still available between the stripped part and its minimum thickness."""
    nominal = _finite_number(nominal_um, "nominal_um")
    minimum = _finite_number(minimum_um, "minimum_um")
    loss = _finite_number(cumulative_loss_um, "cumulative_loss_um")
    if nominal <= 0.0:
        raise ValueError("nominal thickness must be strictly positive, got %r" % (nominal_um,))
    if minimum <= 0.0:
        raise ValueError("minimum thickness must be strictly positive, got %r" % (minimum_um,))
    if minimum > nominal:
        raise ValueError("minimum thickness exceeds the nominal thickness")
    if loss < 0.0:
        raise ValueError("cumulative loss cannot be negative, got %r" % (cumulative_loss_um,))
    return (nominal - loss) - minimum


def strip_cycles_remaining(margin_um, loss_per_cycle_um):
    """Whole further strip cycles the remaining wall will carry.

    Integer arithmetic: a part cannot be stripped a fraction of a time. A
    margin that lands exactly on a whole number of cycles is credited with
    that whole number rather than losing one to representation error.
    """
    margin = _finite_number(margin_um, "margin_um")
    per_cycle = _finite_number(loss_per_cycle_um, "loss_per_cycle_um")
    if per_cycle <= 0.0:
        raise ValueError("loss per cycle must be strictly positive, got %r" % (loss_per_cycle_um,))
    if margin < 0.0:
        return 0
    ratio = margin / per_cycle
    whole = math.floor(ratio)
    if math.isclose(ratio, whole + 1, rel_tol=STRIP_REL_TOL, abs_tol=STRIP_ABS_TOL):
        whole += 1
    return int(whole)


def roughness_within_window(ra_um, window):
    """True when the stripped surface lands in the roughness window the primer needs.

    Too smooth and the primer has nothing to key into; too rough and the film
    cannot cover the peaks at its specified thickness. Both edges are inside.
    """
    value = _finite_number(ra_um, "ra_um")
    if value < 0.0:
        raise ValueError("roughness cannot be negative, got %r" % (ra_um,))
    if not isinstance(window, (list, tuple)) or len(window) != 2:
        raise ValueError("roughness window must be a low,high pair, got %r" % (window,))
    low = _finite_number(window[0], "roughness window low")
    high = _finite_number(window[1], "roughness window high")
    if high < low:
        raise ValueError("roughness window is inverted")
    return _at_or_below(low, value) and _at_or_below(value, high)


def repaint_system_findings(primer, topcoat, substrate):
    """Findings about the coating system going back onto the stripped part."""
    key = validate_substrate(substrate)
    if not isinstance(primer, str) or primer.strip().lower() not in PRIMER_FAMILIES:
        raise ValueError("unrecognized primer family: %r" % (primer,))
    primer_key = primer.strip().lower()
    if not isinstance(topcoat, str) or not topcoat.strip():
        raise ValueError("topcoat must be a non-empty string")
    topcoat_key = topcoat.strip().lower()
    family = PRIMER_FAMILIES[primer_key]
    findings = []
    if key not in family["substrates"]:
        findings.append("primer-substrate-incompatible")
    if topcoat_key not in family["topcoats"]:
        findings.append("topcoat-primer-incompatible")
    return sorted(findings)


def assess_strip_and_repaint(job):
    """Grade one strip-and-repaint job and issue its disposition."""
    if not isinstance(job, dict):
        raise ValueError("job must be a mapping, got %r" % type(job))
    name = job.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("strip job requires a non-empty name")

    substrate = validate_substrate(job.get("substrate"))
    method = validate_method(job.get("method"))
    standing = method_permitted_for_substrate(method, substrate)
    findings = []
    if standing == "prohibited":
        findings.append("method-prohibited-on-substrate")
    elif standing == "conditional" and job.get("approved_procedure") is not True:
        findings.append("conditional-method-without-approved-procedure")

    loss = cumulative_material_loss_um(
        job.get("cycles", 1),
        job.get("loss_per_cycle_um"),
        job.get("prior_loss_um", 0.0),
    )
    margin = remaining_wall_margin_um(
        job.get("nominal_thickness_um"),
        job.get("minimum_thickness_um"),
        loss,
    )
    if margin < 0.0 and not math.isclose(margin, 0.0, abs_tol=STRIP_ABS_TOL):
        findings.append("wall-margin-consumed")
    remaining_cycles = strip_cycles_remaining(max(margin, 0.0), job.get("loss_per_cycle_um"))

    window = job.get("roughness_window_um")
    roughness = job.get("roughness_ra_um")
    if window is None or roughness is None:
        findings.append("surface-roughness-not-verified")
    elif not roughness_within_window(roughness, window):
        findings.append("surface-roughness-outside-window")

    findings.extend(repaint_system_findings(
        job.get("primer"), job.get("topcoat"), substrate
    ))

    if job.get("residual_coating_removed") is not True:
        findings.append("residual-coating-not-confirmed-removed")

    findings = sorted(set(findings))
    hard = {
        "method-prohibited-on-substrate",
        "wall-margin-consumed",
        "primer-substrate-incompatible",
        "topcoat-primer-incompatible",
    }
    if not findings:
        disposition = "strip-and-repaint-approved"
    elif hard.intersection(findings):
        disposition = "refused"
    else:
        disposition = "conditions-outstanding"
    return {
        "name": name.strip(),
        "substrate": substrate,
        "method": method,
        "method_standing": standing,
        "cumulative_loss_um": loss,
        "wall_margin_um": margin,
        "further_cycles_available": remaining_cycles,
        "findings": findings,
        "disposition": disposition,
        "approved": disposition == "strip-and-repaint-approved",
    }


def assess_strip_campaign(jobs):
    """Grade a set of strip jobs; the campaign passes only when every job does."""
    if not isinstance(jobs, (list, tuple)) or not jobs:
        raise ValueError("at least one strip job is required")
    results = [assess_strip_and_repaint(item) for item in jobs]
    names = [item["name"] for item in results]
    if len(set(names)) != len(names):
        raise ValueError("strip job names must be unique within a campaign")
    open_findings = sorted(
        "%s:%s" % (item["name"], finding)
        for item in results
        for finding in item["findings"]
    )
    return {
        "jobs": results,
        "refused_jobs": sorted(i["name"] for i in results if i["disposition"] == "refused"),
        "open_findings": open_findings,
        "campaign_approved": not open_findings,
    }
