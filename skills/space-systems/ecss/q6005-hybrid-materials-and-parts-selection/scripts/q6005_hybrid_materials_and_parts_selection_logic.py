"""Selection of the constituent items a hybrid assembly is built from.

Anchor: ECSS-Q-ST-60-05C clause 9.2 (choosing the substrates, adhesives,
bonding wires and other constituent items used to build a hybrid assembly).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate each candidate item: a known constituent category, a name, and the
   property set that category cannot be selected without.
2. Take the item's qualification standing. A qualified item carries its own
   evidence; anything short of that owes an evaluation, and an evaluation owed
   with no evaluation programme open is a refusal, not a deferral.
3. Where the item is attached to something with a different expansion
   coefficient, compute the thermomechanical strain that mismatch imposes over
   the declared temperature excursion and compare it with the allowable.
4. For polymeric items, screen the declared total mass loss and collected
   volatile condensable material against the vacuum limits.
5. For bonding wire, take the wire-to-pad couple: like metals are proven, an
   unlike couple owes an intermetallic evaluation, and a tin-bearing couple is
   refused outright.
6. Merge the per-condition outcomes worst-first into selectable,
   selectable-with-evaluation or not-selectable, and roll the items up into a
   selection that is complete only when nothing is left open.
"""

__all__ = [
    "STRAIN_TOLERANCE",
    "DEFAULT_LIMITS",
    "ITEM_CATEGORIES",
    "POLYMERIC_CATEGORIES",
    "QUALIFICATION_STANDINGS",
    "METAL_ALIASES",
    "KNOWN_METALS",
    "PROVEN_UNLIKE_COUPLES",
    "SELECTABLE",
    "EVALUATION_REQUIRED",
    "NOT_SELECTABLE",
    "normalise_metal",
    "bond_couple_status",
    "cte_mismatch_strain",
    "cte_status",
    "outgassing_status",
    "qualification_status",
    "worst_status",
    "validate_item",
    "assess_item",
    "assess_selection",
]

# Strain, mass loss and condensable figures are quotients and products of
# declared decimals that land exactly on an allowable in the ordinary case.
# Comparisons absorb representation error here rather than by moving a limit.
STRAIN_TOLERANCE = 1e-9

# Allowables the selection is graded against unless the project declares its
# own. Strain is in parts per million over the declared excursion; mass loss
# and condensable material are percentages by mass.
DEFAULT_LIMITS = {
    "cte_strain_ppm": 250.0,
    "cte_evaluation_fraction": 0.75,
    "tml_percent": 1.0,
    "cvcm_percent": 0.10,
}

ITEM_CATEGORIES = (
    "substrate",
    "die-attach",
    "bonding-wire",
    "preform",
    "lid",
    "sealing-material",
    "encapsulant",
    "piece-part",
)

# Categories whose items are polymeric and therefore owe outgassing data.
POLYMERIC_CATEGORIES = ("die-attach", "sealing-material", "encapsulant")

QUALIFICATION_STANDINGS = ("qualified", "qualified-by-similarity", "unqualified")

SELECTABLE = "selectable"
EVALUATION_REQUIRED = "selectable-with-evaluation"
NOT_SELECTABLE = "not-selectable"

_STATUS_ORDER = {SELECTABLE: 0, EVALUATION_REQUIRED: 1, NOT_SELECTABLE: 2}

METAL_ALIASES = {
    "au": "gold",
    "al": "aluminium",
    "aluminum": "aluminium",
    "cu": "copper",
    "ag": "silver",
    "ni": "nickel",
    "pd": "palladium",
    "sn": "tin",
}

KNOWN_METALS = (
    "gold",
    "aluminium",
    "copper",
    "silver",
    "nickel",
    "palladium",
    "tin",
)

# Unlike couples with enough service history behind them to be taken as proven
# without an item-specific intermetallic evaluation.
PROVEN_UNLIKE_COUPLES = (
    frozenset({"gold", "palladium"}),
    frozenset({"gold", "nickel"}),
)


def _require_text(value, label):
    """Return value as a stripped non-empty string, raising on anything else."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    stripped = value.strip()
    if not stripped:
        raise ValueError("%s must not be blank" % label)
    return stripped


def _require_number(value, label, minimum=None):
    """Return value as a float, raising on a non-number or an out-of-range one."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (label, value))
    number = float(value)
    if number != number:
        raise ValueError("%s must be a real number, got %r" % (label, value))
    if minimum is not None and number < minimum:
        raise ValueError("%s must be at least %s, got %s" % (label, minimum, number))
    return number


def normalise_metal(name):
    """Return the canonical metal name for a wire or pad finish.

    Chemical symbols and the American spelling of aluminium are accepted; an
    unrecognised finish raises, because guessing a bond couple is worse than
    refusing to grade one.
    """
    text = _require_text(name, "metal").lower().replace("_", "-")
    canonical = METAL_ALIASES.get(text, text)
    if canonical not in KNOWN_METALS:
        raise ValueError("unrecognised metal finish %r" % (name,))
    return canonical


def bond_couple_status(wire_metal, pad_metal):
    """Return the selectability of a wire-to-pad metallurgical couple.

    Like metals are proven. A tin-bearing couple is refused whichever side the
    tin is on. Every other unlike couple owes an intermetallic evaluation over
    the assembly's thermal life before it can be selected.
    """
    wire = normalise_metal(wire_metal)
    pad = normalise_metal(pad_metal)
    if "tin" in (wire, pad):
        return NOT_SELECTABLE
    if wire == pad:
        return SELECTABLE
    if frozenset({wire, pad}) in PROVEN_UNLIKE_COUPLES:
        return SELECTABLE
    return EVALUATION_REQUIRED


def cte_mismatch_strain(item_cte, mating_cte, temperature_excursion_k):
    """Return the mismatch strain in ppm imposed across a joint.

    The item's expansion coefficient and that of what it is attached to are in
    ppm per kelvin; the excursion is the temperature swing the joint sees.
    """
    item = _require_number(item_cte, "item_cte", minimum=0.0)
    mating = _require_number(mating_cte, "mating_cte", minimum=0.0)
    excursion = _require_number(temperature_excursion_k, "temperature_excursion_k", minimum=0.0)
    return abs(item - mating) * excursion


def cte_status(strain_ppm, limits=None):
    """Return the selectability implied by a mismatch strain.

    Strain above the allowable refuses the item. Strain inside the evaluation
    band below the allowable is selectable only with a joint evaluation, since
    a joint sitting just under its limit has no margin for a process shift.
    """
    applied = dict(DEFAULT_LIMITS)
    applied.update(_validated_limits(limits))
    strain = _require_number(strain_ppm, "strain_ppm", minimum=0.0)
    limit = applied["cte_strain_ppm"]
    band = applied["cte_evaluation_fraction"] * limit
    if strain > limit + STRAIN_TOLERANCE:
        return NOT_SELECTABLE
    if strain > band + STRAIN_TOLERANCE:
        return EVALUATION_REQUIRED
    return SELECTABLE


def _validated_limits(limits):
    """Return a validated partial limit override mapping."""
    if limits is None:
        return {}
    if not isinstance(limits, dict):
        raise ValueError("limits must be a mapping")
    validated = {}
    for key, value in limits.items():
        if key not in DEFAULT_LIMITS:
            raise ValueError("unrecognised limit %r" % (key,))
        validated[key] = _require_number(value, "limits[%r]" % key, minimum=0.0)
    return validated


def outgassing_status(tml_percent, cvcm_percent, limits=None):
    """Return the vacuum outgassing screen outcome for a polymeric item.

    Either figure above its allowable refuses the item; a figure landing on the
    allowable meets it, which is why the comparison carries a tolerance.
    """
    applied = dict(DEFAULT_LIMITS)
    applied.update(_validated_limits(limits))
    tml = _require_number(tml_percent, "tml_percent", minimum=0.0)
    cvcm = _require_number(cvcm_percent, "cvcm_percent", minimum=0.0)
    findings = []
    if tml > applied["tml_percent"] + STRAIN_TOLERANCE:
        findings.append(
            "total mass loss %.4f%% exceeds the %.4f%% allowable"
            % (tml, applied["tml_percent"])
        )
    if cvcm > applied["cvcm_percent"] + STRAIN_TOLERANCE:
        findings.append(
            "condensable volatiles %.4f%% exceed the %.4f%% allowable"
            % (cvcm, applied["cvcm_percent"])
        )
    return {
        "tml_percent": tml,
        "cvcm_percent": cvcm,
        "status": NOT_SELECTABLE if findings else SELECTABLE,
        "findings": findings,
    }


def qualification_status(standing):
    """Return the selectability implied by an item's qualification standing."""
    text = _require_text(standing, "qualification").lower().replace("_", "-")
    if text not in QUALIFICATION_STANDINGS:
        raise ValueError("unrecognised qualification standing %r" % (standing,))
    if text == "qualified":
        return SELECTABLE
    return EVALUATION_REQUIRED


def worst_status(statuses):
    """Return the most restrictive of a set of per-condition outcomes."""
    if isinstance(statuses, str) or not isinstance(statuses, (list, tuple)):
        raise ValueError("statuses must be a sequence of status strings")
    if not statuses:
        raise ValueError("no statuses to merge")
    for status in statuses:
        if status not in _STATUS_ORDER:
            raise ValueError("unrecognised status %r" % (status,))
    return max(statuses, key=lambda status: _STATUS_ORDER[status])


def validate_item(item):
    """Return a normalised candidate item record.

    A polymeric item without its outgassing figures and a bonding wire without
    its couple are input errors: the condition that governs the choice was not
    declared, so there is nothing to grade.
    """
    if not isinstance(item, dict):
        raise ValueError("item must be a mapping")
    name = _require_text(item.get("name"), "item['name']")
    category = _require_text(item.get("category"), "item['category']").lower().replace("_", "-")
    if category not in ITEM_CATEGORIES:
        raise ValueError("unrecognised constituent category %r" % (item.get("category"),))
    standing = _require_text(item.get("qualification"), "item['qualification']")
    record = {
        "name": name,
        "category": category,
        "qualification": standing.lower().replace("_", "-"),
    }
    if record["qualification"] not in QUALIFICATION_STANDINGS:
        raise ValueError("unrecognised qualification standing %r" % (standing,))
    if category in POLYMERIC_CATEGORIES:
        if "tml_percent" not in item or "cvcm_percent" not in item:
            raise ValueError(
                "%s is polymeric and needs tml_percent and cvcm_percent" % name
            )
        record["tml_percent"] = _require_number(item["tml_percent"], "tml_percent", minimum=0.0)
        record["cvcm_percent"] = _require_number(item["cvcm_percent"], "cvcm_percent", minimum=0.0)
    if category == "bonding-wire":
        if "wire_metal" not in item or "pad_metal" not in item:
            raise ValueError("%s is a bonding wire and needs wire_metal and pad_metal" % name)
        record["wire_metal"] = normalise_metal(item["wire_metal"])
        record["pad_metal"] = normalise_metal(item["pad_metal"])
    if "cte_ppm_per_k" in item:
        record["cte_ppm_per_k"] = _require_number(
            item["cte_ppm_per_k"], "cte_ppm_per_k", minimum=0.0
        )
    return record


def assess_item(item, context=None):
    """Return the selection verdict for one candidate constituent item.

    context keys: optional mating_cte_ppm_per_k and temperature_excursion_k,
    which together make the mismatch condition applicable; optional
    evaluation_programme_available (default True); optional limits.
    """
    record = validate_item(item)
    settings = _validated_context(context)
    statuses = []
    findings = []
    measurements = {}

    standing_status = qualification_status(record["qualification"])
    statuses.append(standing_status)
    if standing_status != SELECTABLE:
        findings.append(
            "%s is %s and owes a qualification evaluation" % (record["name"], record["qualification"])
        )

    if "tml_percent" in record:
        screen = outgassing_status(
            record["tml_percent"], record["cvcm_percent"], settings["limits"]
        )
        statuses.append(screen["status"])
        findings.extend(screen["findings"])
        measurements["tml_percent"] = screen["tml_percent"]
        measurements["cvcm_percent"] = screen["cvcm_percent"]

    if "wire_metal" in record:
        couple = bond_couple_status(record["wire_metal"], record["pad_metal"])
        statuses.append(couple)
        measurements["bond_couple"] = "%s-to-%s" % (record["wire_metal"], record["pad_metal"])
        if couple == NOT_SELECTABLE:
            findings.append(
                "the %s couple is tin-bearing and is refused for flight hardware"
                % measurements["bond_couple"]
            )
        elif couple == EVALUATION_REQUIRED:
            findings.append(
                "the %s couple is unlike and owes an intermetallic evaluation"
                % measurements["bond_couple"]
            )

    if "cte_ppm_per_k" in record and settings["mating_cte_ppm_per_k"] is not None:
        strain = cte_mismatch_strain(
            record["cte_ppm_per_k"],
            settings["mating_cte_ppm_per_k"],
            settings["temperature_excursion_k"],
        )
        status = cte_status(strain, settings["limits"])
        statuses.append(status)
        measurements["cte_mismatch_strain_ppm"] = strain
        if status == NOT_SELECTABLE:
            findings.append(
                "mismatch strain %.3f ppm exceeds the allowable for %s" % (strain, record["name"])
            )
        elif status == EVALUATION_REQUIRED:
            findings.append(
                "mismatch strain %.3f ppm sits inside the evaluation band for %s"
                % (strain, record["name"])
            )

    status = worst_status(statuses)
    if status == EVALUATION_REQUIRED and not settings["evaluation_programme_available"]:
        status = NOT_SELECTABLE
        findings.append(
            "%s owes an evaluation and no evaluation programme is open" % record["name"]
        )
    return {
        "name": record["name"],
        "category": record["category"],
        "qualification": record["qualification"],
        "status": status,
        "findings": findings,
        "measurements": measurements,
    }


def _validated_context(context):
    """Return the validated selection context with its defaults filled in."""
    if context is None:
        context = {}
    if not isinstance(context, dict):
        raise ValueError("context must be a mapping")
    known = {
        "mating_cte_ppm_per_k",
        "temperature_excursion_k",
        "evaluation_programme_available",
        "limits",
    }
    for key in context:
        if key not in known:
            raise ValueError("unrecognised context key %r" % (key,))
    available = context.get("evaluation_programme_available", True)
    if not isinstance(available, bool):
        raise ValueError("evaluation_programme_available must be a boolean")
    mating = context.get("mating_cte_ppm_per_k")
    excursion = context.get("temperature_excursion_k")
    if mating is not None:
        mating = _require_number(mating, "mating_cte_ppm_per_k", minimum=0.0)
        if excursion is None:
            raise ValueError(
                "mating_cte_ppm_per_k needs a temperature_excursion_k to be gradeable"
            )
        excursion = _require_number(excursion, "temperature_excursion_k", minimum=0.0)
    return {
        "mating_cte_ppm_per_k": mating,
        "temperature_excursion_k": excursion,
        "evaluation_programme_available": available,
        "limits": _validated_limits(context.get("limits")),
    }


def assess_selection(spec):
    """Run the full clause 9.2 constituent-item selection assessment.

    spec keys: items (a non-empty sequence of candidate records) and the
    optional context keys accepted by assess_item.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    if "items" not in spec:
        raise ValueError("spec missing required key 'items'")
    items = spec["items"]
    if isinstance(items, dict) or not isinstance(items, (list, tuple)):
        raise ValueError("items must be a sequence of candidate records")
    if not items:
        raise ValueError("selection contains no candidate items")
    context = {key: value for key, value in spec.items() if key != "items"}
    verdicts = [assess_item(item, context) for item in items]
    seen = set()
    for verdict in verdicts:
        key = verdict["name"].lower()
        if key in seen:
            raise ValueError("duplicate candidate item %r" % verdict["name"])
        seen.add(key)
    refused = [v["name"] for v in verdicts if v["status"] == NOT_SELECTABLE]
    open_items = [v["name"] for v in verdicts if v["status"] == EVALUATION_REQUIRED]
    ratio = (len(verdicts) - len(refused) - len(open_items)) / float(len(verdicts))
    return {
        "item_count": len(verdicts),
        "items": verdicts,
        "refused_items": refused,
        "items_requiring_evaluation": open_items,
        "settled_fraction": ratio,
        "selection_complete": not refused and not open_items,
        "buildable": not refused,
    }
