"""Pre-treatment line for black anodizing with inorganic dyes.

Anchor: ECSS-Q-ST-70-03C, process clause, pre-treatment (paraphrased
into an implementable procedure; no standard text is reproduced).

Procedure implemented here:

1. Read the declared line as an ordered list of steps and reject a step
   the process does not know. A pre-treatment line is a sequence, and a
   sequence with an unrecognized member cannot be graded at all.
2. Enforce the order the chemistry forces. Oils come off before an
   alkaline cleaner sees them, the cleaner runs before the etch, the
   etch runs before the deoxidizer, and the deoxidizer is the last
   chemical step before the part reaches the anodizing tank. Masking
   goes on after the last chemical attack and before anodizing, so the
   maskant is not itself etched off.
3. Demand a rinse between consecutive aqueous baths. Carry-over from
   an alkaline bath into an acid one neutralizes both and leaves smut
   on the part, so an unrinsed pair is a finding wherever it appears.
   A solvent degrease is not an aqueous bath and drains instead, so it
   is outside that rule and inside the ordering rule.
4. Turn the etch into a number. Metal loss is the etch rate times the
   immersion time, and it has to clear the minimum that removes the
   worked surface layer while staying inside the dimensional allowance
   the drawing left.
5. Hold the transfer. A deoxidized surface re-oxidizes in air, so the
   time from the last rinse to the anodizing tank is bounded, and an
   exceeded bound sends the part back to the deoxidizer.
6. Grade the rinse water and the maskant, then report findings, the
   metal loss and one verdict.

Stdlib only, offline, deterministic.
"""

CHEMICAL_STEPS = (
    "solvent-degrease",
    "alkaline-clean",
    "alkaline-etch",
    "deoxidize",
)
NON_CHEMICAL_STEPS = ("rinse", "mask", "dry", "visual-examination")
VALID_STEPS = CHEMICAL_STEPS + NON_CHEMICAL_STEPS

# Aqueous baths, the ones whose carry-over has to be rinsed away. A
# solvent degrease drains and evaporates instead of dragging liquor
# into the next tank, so it is not one of them.
AQUEOUS_STEPS = ("alkaline-clean", "alkaline-etch", "deoxidize")

# Position each chemical step has to hold relative to the others.
CHEMICAL_ORDER = {
    "solvent-degrease": 0,
    "alkaline-clean": 1,
    "alkaline-etch": 2,
    "deoxidize": 3,
}

# Metal the alkaline etch has to remove before the worked and
# rolled-in surface layer is gone, in micrometres per treated surface.
MIN_ETCH_REMOVAL_UM = 1.0

# Longest the part may sit between the last rinse and the anodizing
# tank before the deoxidized surface has to be renewed, in minutes.
MAX_TRANSFER_MINUTES = 10.0

# Rinse water quality: a cascade of at least this many stages, or a
# single stage of at least this resistivity, in megohm-centimetres.
MIN_RINSE_STAGES = 2
MIN_RINSE_RESISTIVITY_MOHM_CM = 0.05

MASKANTS = {
    "peelable-vinyl-lacquer": ("alkaline-clean", "alkaline-etch", "deoxidize"),
    "silicone-plug": ("alkaline-clean", "deoxidize"),
    "ptfe-tape": ("alkaline-clean", "alkaline-etch", "deoxidize"),
    "adhesive-paper-tape": (),
}

# Metal loss is a product of two measured floats, so a part sitting
# exactly on its allowance can land a few units in the last place above
# it. A picometre is far below any drawing tolerance and absorbs that
# representation error without relaxing the allowance.
REMOVAL_TOLERANCE_UM = 1.0e-9


def _numeric(label, value, minimum=None):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be numeric, got %r" % (label, value))
    value = float(value)
    if minimum is not None and value < minimum:
        raise ValueError("%s must be >= %r, got %r" % (label, minimum, value))
    return value


def validate_steps(steps):
    """Validate the declared step list and return it as a tuple."""
    if not isinstance(steps, (list, tuple)) or not steps:
        raise ValueError("steps must be a non-empty sequence")
    out = []
    for step in steps:
        if step not in VALID_STEPS:
            raise ValueError(
                "unknown pre-treatment step %r (expected one of %s)"
                % (step, ", ".join(VALID_STEPS))
            )
        out.append(step)
    return tuple(out)


def etch_metal_loss_um(etch_rate_um_per_min, etch_minutes):
    """Metal removed from one surface by the alkaline etch, in micrometres."""
    rate = _numeric("etch_rate_um_per_min", etch_rate_um_per_min, 0.0)
    minutes = _numeric("etch_minutes", etch_minutes, 0.0)
    return rate * minutes


def etch_minutes_for_removal(etch_rate_um_per_min, target_removal_um):
    """Immersion time that removes a target depth of metal, in minutes."""
    rate = _numeric("etch_rate_um_per_min", etch_rate_um_per_min)
    if rate <= 0.0:
        raise ValueError("etch_rate_um_per_min must be positive")
    target = _numeric("target_removal_um", target_removal_um, 0.0)
    return target / rate


def check_order(steps):
    """Findings about the order of the chemical steps and the masking."""
    steps = validate_steps(steps)
    findings = []
    seen = [s for s in steps if s in CHEMICAL_ORDER]
    for earlier, later in zip(seen, seen[1:]):
        if CHEMICAL_ORDER[later] < CHEMICAL_ORDER[earlier]:
            findings.append("chemical-step-out-of-order-%s-before-%s"
                            % (later, earlier))
    if "alkaline-etch" in steps and "deoxidize" not in steps:
        findings.append("etch-without-a-deoxidizing-step")
    if "deoxidize" in steps and seen[-1] != "deoxidize":
        findings.append("deoxidize-is-not-the-last-chemical-step")
    if "deoxidize" not in steps:
        findings.append("no-deoxidizing-step-before-anodizing")
    if "mask" in steps:
        mask_at = steps.index("mask")
        last_chemical = max(
            i for i, s in enumerate(steps) if s in CHEMICAL_ORDER
        )
        if mask_at < last_chemical:
            findings.append("maskant-applied-before-a-chemical-attack")
    return findings


def check_rinses(steps):
    """Findings about missing rinses between consecutive aqueous baths."""
    steps = validate_steps(steps)
    findings = []
    previous_bath = None
    rinsed = True
    for step in steps:
        if step == "rinse":
            rinsed = True
            continue
        if step in AQUEOUS_STEPS:
            if previous_bath is not None and not rinsed:
                findings.append(
                    "no-rinse-between-%s-and-%s" % (previous_bath, step)
                )
            previous_bath = step
            rinsed = False
    if previous_bath is not None and not rinsed:
        findings.append("no-final-rinse-after-%s" % previous_bath)
    return findings


def check_rinse_quality(stages, resistivity_mohm_cm):
    """Findings about the rinse water arrangement."""
    if not isinstance(stages, int) or isinstance(stages, bool) or stages < 0:
        raise ValueError("stages must be a non-negative integer, got %r" % (stages,))
    resistivity = _numeric("resistivity_mohm_cm", resistivity_mohm_cm, 0.0)
    findings = []
    if stages < MIN_RINSE_STAGES and resistivity < MIN_RINSE_RESISTIVITY_MOHM_CM:
        findings.append("rinse-neither-cascaded-nor-of-adequate-resistivity")
    if stages == 0:
        findings.append("no-rinse-stage-declared")
    return findings


def check_transfer(transfer_minutes):
    """Findings about the hold between the last rinse and the anodizing tank."""
    minutes = _numeric("transfer_minutes", transfer_minutes, 0.0)
    if minutes > MAX_TRANSFER_MINUTES:
        return ["deoxidized-surface-held-too-long-before-anodizing"]
    return []


def check_maskant(maskant, steps):
    """Findings about maskant compatibility with the chemistries it meets."""
    if maskant is None:
        return []
    if maskant not in MASKANTS:
        raise ValueError(
            "unknown maskant %r (expected one of %s)"
            % (maskant, ", ".join(sorted(MASKANTS)))
        )
    steps = validate_steps(steps)
    if "mask" not in steps:
        return ["maskant-declared-but-no-masking-step-in-the-line"]
    survives = MASKANTS[maskant]
    mask_at = steps.index("mask")
    findings = []
    for step in steps[mask_at:]:
        if step in CHEMICAL_ORDER and step not in survives:
            findings.append("maskant-not-resistant-to-%s" % step)
    return findings


def check_etch(etch_rate_um_per_min, etch_minutes, allowance_um):
    """Findings about the etch depth, plus the metal loss it produced."""
    loss = etch_metal_loss_um(etch_rate_um_per_min, etch_minutes)
    allowance = _numeric("allowance_um", allowance_um, 0.0)
    findings = []
    if loss + REMOVAL_TOLERANCE_UM < MIN_ETCH_REMOVAL_UM:
        findings.append("etch-too-light-to-remove-the-worked-surface-layer")
    if loss > allowance + REMOVAL_TOLERANCE_UM:
        findings.append("etch-removal-exceeds-the-dimensional-allowance")
    return findings, loss


def validate_line(line):
    """Validate one pre-treatment line record and return a normalized copy."""
    if not isinstance(line, dict):
        raise ValueError("line must be a mapping")
    line_id = line.get("id")
    if not isinstance(line_id, str) or not line_id.strip():
        raise ValueError("line needs a non-empty string id")
    steps = validate_steps(line.get("steps", []))
    stages = line.get("rinse_stages", 0)
    if not isinstance(stages, int) or isinstance(stages, bool) or stages < 0:
        raise ValueError("line %s rinse_stages must be a non-negative integer" % line_id)
    maskant = line.get("maskant")
    if maskant is not None and maskant not in MASKANTS:
        raise ValueError("line %s has unknown maskant %r" % (line_id, maskant))
    return {
        "id": line_id.strip(),
        "steps": steps,
        "etch_rate_um_per_min": _numeric(
            "line %s etch_rate_um_per_min" % line_id,
            line.get("etch_rate_um_per_min", 0.5),
            0.0,
        ),
        "etch_minutes": _numeric(
            "line %s etch_minutes" % line_id, line.get("etch_minutes", 3.0), 0.0
        ),
        "allowance_um": _numeric(
            "line %s allowance_um" % line_id, line.get("allowance_um", 25.0), 0.0
        ),
        "rinse_stages": stages,
        "rinse_resistivity_mohm_cm": _numeric(
            "line %s rinse_resistivity_mohm_cm" % line_id,
            line.get("rinse_resistivity_mohm_cm", 0.0),
            0.0,
        ),
        "transfer_minutes": _numeric(
            "line %s transfer_minutes" % line_id,
            line.get("transfer_minutes", 5.0),
            0.0,
        ),
        "maskant": maskant,
    }


def assess_pre_treatment(line):
    """Assess one declared pre-treatment line against the process clause."""
    norm = validate_line(line)
    findings = []
    findings.extend(check_order(norm["steps"]))
    findings.extend(check_rinses(norm["steps"]))
    findings.extend(
        check_rinse_quality(norm["rinse_stages"], norm["rinse_resistivity_mohm_cm"])
    )
    findings.extend(check_transfer(norm["transfer_minutes"]))
    findings.extend(check_maskant(norm["maskant"], norm["steps"]))
    etch_findings, loss = check_etch(
        norm["etch_rate_um_per_min"], norm["etch_minutes"], norm["allowance_um"]
    )
    findings.extend(etch_findings)
    return {
        "id": norm["id"],
        "etch_removal_um": loss,
        "findings": findings,
        "compliant": not findings,
    }


def assess_pre_treatment_lines(lines):
    """Assess several declared pre-treatment lines together."""
    if not isinstance(lines, list) or not lines:
        raise ValueError("lines must be a non-empty list")
    results = []
    seen = set()
    for line in lines:
        result = assess_pre_treatment(line)
        if result["id"] in seen:
            raise ValueError("duplicate line id %r" % (result["id"],))
        seen.add(result["id"])
        results.append(result)
    return {
        "lines": results,
        "non_compliant_ids": [r["id"] for r in results if not r["compliant"]],
        "compliant": all(r["compliant"] for r in results),
    }
