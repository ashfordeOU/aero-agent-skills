#!/usr/bin/env python3
"""Post-braze operations: cleaning, flux residue removal and passivation.

Anchor: ECSS-Q-ST-70-40 post-braze clause on brazing of space hardware.
The procedure below is a paraphrase into implementable steps; no
standard text is reproduced.

What a brazement owes after it leaves the heat depends on what was used
to get the filler to flow, not on how the joint looks.

A flux-free process — a vacuum or a clean inert-gas furnace — leaves no
residue to remove, and inventing a chemical cleaning step for it adds a
corrosion risk instead of removing one. A fluxed process leaves a
residue that is hygroscopic and, for the fluoride and chloride families,
actively corrosive: it keeps attacking the parent metal for as long as
it is on the part, so removal is not a cosmetic step and it has a
deadline. Left to cool and dry the residue vitrifies, and once it does,
the hot-water quench that would have lifted it no longer will.

Removal has to be evidenced, not asserted. The evidence is the
conductivity of the final rinse against the conductivity of the water
that went in: a rinse that comes off the part much more conductive than
it went on is still carrying ionic residue.

Passivation is a separate question again. It restores the chromium-oxide
film on an austenitic stainless steel that the braze thermal cycle and
the cleaning both degrade, and it is meaningless on the alloys that do
not carry one.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

PROCESS_TORCH = "torch-brazing"
PROCESS_INDUCTION = "induction-brazing"
PROCESS_DIP = "dip-brazing"
PROCESS_RESISTANCE = "resistance-brazing"
PROCESS_FURNACE_VACUUM = "furnace-brazing-vacuum"
PROCESS_FURNACE_INERT = "furnace-brazing-inert-gas"

PROCESSES = (
    PROCESS_TORCH,
    PROCESS_INDUCTION,
    PROCESS_DIP,
    PROCESS_RESISTANCE,
    PROCESS_FURNACE_VACUUM,
    PROCESS_FURNACE_INERT,
)

FLUX_NONE = "none"
FLUX_BORAX_BORIC = "borax-boric-acid"
FLUX_FLUORIDE = "fluoride-bearing"
FLUX_CHLORIDE = "chloride-bearing"
FLUX_FLUOROALUMINATE = "non-corrosive-fluoroaluminate"

FLUX_TYPES = (
    FLUX_NONE,
    FLUX_BORAX_BORIC,
    FLUX_FLUORIDE,
    FLUX_CHLORIDE,
    FLUX_FLUOROALUMINATE,
)

# Residues that keep attacking the parent metal until they are removed.
_CORROSIVE_RESIDUE = frozenset((FLUX_FLUORIDE, FLUX_CHLORIDE))

# Hours from the end of the braze cycle within which the residue must be
# taken off while it is still soluble.
_REMOVAL_WINDOW_HOURS = {
    FLUX_BORAX_BORIC: 24.0,
    FLUX_FLUORIDE: 8.0,
    FLUX_CHLORIDE: 4.0,
    FLUX_FLUOROALUMINATE: 48.0,
}

MATERIAL_AUSTENITIC_STAINLESS = "austenitic-stainless-steel"
MATERIAL_NICKEL_ALLOY = "nickel-alloy"
MATERIAL_ALUMINIUM_ALLOY = "aluminium-alloy"
MATERIAL_TITANIUM_ALLOY = "titanium-alloy"
MATERIAL_COPPER_ALLOY = "copper-alloy"

BASE_MATERIALS = (
    MATERIAL_AUSTENITIC_STAINLESS,
    MATERIAL_NICKEL_ALLOY,
    MATERIAL_ALUMINIUM_ALLOY,
    MATERIAL_TITANIUM_ALLOY,
    MATERIAL_COPPER_ALLOY,
)

OP_CONTROLLED_COOL = "controlled-cool-to-handling-temperature"
OP_MECHANICAL_REMOVAL = "mechanical-residue-removal"
OP_HOT_WATER_QUENCH = "hot-water-quench-residue-removal"
OP_CHEMICAL_REMOVAL = "chemical-residue-removal"
OP_FINAL_RINSE = "demineralised-water-final-rinse"
OP_RINSE_VERIFICATION = "final-rinse-conductivity-verification"
OP_PASSIVATION = "stainless-steel-passivation"
OP_DRYING = "controlled-drying"
OP_VISUAL = "post-treatment-visual-inspection"

OPERATIONS = (
    OP_CONTROLLED_COOL,
    OP_MECHANICAL_REMOVAL,
    OP_HOT_WATER_QUENCH,
    OP_CHEMICAL_REMOVAL,
    OP_FINAL_RINSE,
    OP_RINSE_VERIFICATION,
    OP_PASSIVATION,
    OP_DRYING,
    OP_VISUAL,
)

VERDICT_RELEASED = "post-braze-treatment-complete"
VERDICT_INCOMPLETE = "post-braze-treatment-incomplete"

# Final rinse may not come off the part more conductive than the feed
# water by more than this ratio.
DEFAULT_RINSE_RATIO_LIMIT = 1.5

# Floating-point representation tolerance on the rinse comparison.
RINSE_TOLERANCE = 1e-9


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _require_number(name, value, minimum=None, strictly_above=None):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (name, value))
    if minimum is not None and value < minimum:
        raise ValueError("%s must be at least %s, got %r" % (name, minimum, value))
    if strictly_above is not None and value <= strictly_above:
        raise ValueError(
            "%s must be above %s, got %r" % (name, strictly_above, value)
        )
    return float(value)


def flux_leaves_residue(flux_type):
    """Whether the process leaves anything on the part to be removed."""
    _require_choice("flux_type", flux_type, FLUX_TYPES)
    return flux_type != FLUX_NONE


def residue_is_corrosive(flux_type):
    """Whether the residue keeps attacking the parent metal until removed."""
    _require_choice("flux_type", flux_type, FLUX_TYPES)
    return flux_type in _CORROSIVE_RESIDUE


def removal_window_hours(flux_type):
    """Hours after the braze within which the residue is still soluble."""
    _require_choice("flux_type", flux_type, FLUX_TYPES)
    if flux_type == FLUX_NONE:
        raise ValueError(
            "a flux-free process leaves no residue, so it has no removal "
            "window; asking for one means the process record is wrong"
        )
    return _REMOVAL_WINDOW_HOURS[flux_type]


def passivation_applies(base_material):
    """Whether the alloy carries a chromium-oxide film worth restoring."""
    _require_choice("base_material", base_material, BASE_MATERIALS)
    return base_material == MATERIAL_AUSTENITIC_STAINLESS


def required_operations(process, flux_type, base_material):
    """Post-braze operations the brazement owes, in the order they run."""
    _require_choice("process", process, PROCESSES)
    _require_choice("flux_type", flux_type, FLUX_TYPES)
    _require_choice("base_material", base_material, BASE_MATERIALS)
    if process in (PROCESS_FURNACE_VACUUM,) and flux_type != FLUX_NONE:
        raise ValueError(
            "a vacuum furnace cycle cannot carry flux; the process and flux "
            "records contradict each other"
        )
    ordered = [OP_CONTROLLED_COOL]
    if flux_leaves_residue(flux_type):
        ordered.append(OP_HOT_WATER_QUENCH)
        if residue_is_corrosive(flux_type):
            ordered.append(OP_MECHANICAL_REMOVAL)
            ordered.append(OP_CHEMICAL_REMOVAL)
        ordered.append(OP_FINAL_RINSE)
        ordered.append(OP_RINSE_VERIFICATION)
    if passivation_applies(base_material):
        ordered.append(OP_PASSIVATION)
        if OP_FINAL_RINSE not in ordered:
            ordered.append(OP_FINAL_RINSE)
    ordered.append(OP_DRYING)
    ordered.append(OP_VISUAL)
    return ordered


def missing_operations(process, flux_type, base_material, performed):
    """Required operations not recorded, in the order they were owed."""
    required = required_operations(process, flux_type, base_material)
    if not isinstance(performed, (list, tuple, set)):
        raise ValueError("performed must be a sequence of operation names")
    done = set()
    for name in performed:
        done.add(_require_choice("operation name", name, OPERATIONS))
    return [name for name in required if name not in done]


def assess_final_rinse(rinse_conductivity, feed_conductivity, ratio_limit=None):
    """Whether the final rinse evidences that the residue actually left."""
    rinse = _require_number("rinse_conductivity", rinse_conductivity, 0.0)
    feed = _require_number("feed_conductivity", feed_conductivity, strictly_above=0.0)
    limit_ratio = DEFAULT_RINSE_RATIO_LIMIT if ratio_limit is None else _require_number(
        "ratio_limit", ratio_limit, strictly_above=0.0
    )
    if limit_ratio < 1.0:
        raise ValueError(
            "a rinse cannot be required to come off the part cleaner than the "
            "water that went on, got a ratio limit of %r" % (ratio_limit,)
        )
    allowed = feed * limit_ratio
    excess = rinse - allowed
    return {
        "rinse_conductivity": rinse,
        "feed_conductivity": feed,
        "ratio_limit": limit_ratio,
        "allowed_conductivity": allowed,
        "measured_ratio": rinse / feed,
        "excess_conductivity": excess,
        "acceptable": excess <= RINSE_TOLERANCE,
    }


def assess_post_braze(case):
    """Whether the brazement may leave post-braze treatment."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    part_id = case.get("part_id")
    if not isinstance(part_id, str) or not part_id.strip():
        raise ValueError("part_id must be a non-empty string, got %r" % (part_id,))
    process = _require_choice("process", case.get("process"), PROCESSES)
    flux_type = _require_choice("flux_type", case.get("flux_type"), FLUX_TYPES)
    base_material = _require_choice(
        "base_material", case.get("base_material"), BASE_MATERIALS
    )
    performed = case.get("operations_performed", [])
    required = required_operations(process, flux_type, base_material)
    gaps = missing_operations(process, flux_type, base_material, performed)

    findings = []
    if gaps:
        findings.append(
            "%d required post-braze operation(s) are not recorded: %s"
            % (len(gaps), ", ".join(gaps))
        )

    window = None
    elapsed = None
    if flux_leaves_residue(flux_type):
        window = removal_window_hours(flux_type)
        elapsed = _require_number(
            "hours_to_residue_removal", case.get("hours_to_residue_removal"), 0.0
        )
        if elapsed - window > RINSE_TOLERANCE:
            findings.append(
                "the residue was taken off %.2f h after the braze against a "
                "%.2f h window; by then it has vitrified and the quench no "
                "longer lifts it" % (elapsed, window)
            )

    rinse = None
    if OP_RINSE_VERIFICATION in required:
        rinse = assess_final_rinse(
            case.get("rinse_conductivity_us_per_cm"),
            case.get("feed_conductivity_us_per_cm"),
            case.get("rinse_ratio_limit"),
        )
        if not rinse["acceptable"]:
            findings.append(
                "the final rinse came off at %.3f uS/cm against an allowance "
                "of %.3f uS/cm; ionic residue is still on the part"
                % (rinse["rinse_conductivity"], rinse["allowed_conductivity"])
            )

    complete = not findings
    return {
        "part_id": part_id,
        "process": process,
        "flux_type": flux_type,
        "base_material": base_material,
        "residue_expected": flux_leaves_residue(flux_type),
        "residue_corrosive": residue_is_corrosive(flux_type),
        "passivation_required": passivation_applies(base_material),
        "required_operations": required,
        "missing_operations": gaps,
        "removal_window_hours": window,
        "hours_to_residue_removal": elapsed,
        "final_rinse": rinse,
        "verdict": VERDICT_RELEASED if complete else VERDICT_INCOMPLETE,
        "released": complete,
        "findings": findings,
    }
