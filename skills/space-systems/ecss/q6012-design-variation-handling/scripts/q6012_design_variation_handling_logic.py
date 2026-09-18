"""Handling of alternative circuit versions sharing one mask set.

Anchor: ECSS-Q-ST-60-12 clause 7.2.2 (managing alternative circuit versions
placed on a common wafer or mask set). Paraphrased into an implementable
procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate every declared variant: a unique identifier, an optional baseline
   it derives from, a process option, an identification marking, a positive
   site count and a positive die area.
2. Resolve each variant's derivation chain back to a root, refusing a baseline
   that the mask set never declares and a derivation loop.
3. Detect process options that cannot share a wafer: the set runs one option
   unless every declared option sits inside one compatible group.
4. Report the variants whose die carries no marking, and the markings shared by
   more than one variant, since either makes a die unidentifiable after dicing.
5. Report the variants whose site count falls below the minimum a statistical
   evaluation needs.
6. Sum the reticle field area the variants occupy, compare it with the declared
   budget, and return the release verdict for the mask set.
"""

import math

__all__ = [
    "MIN_SITES_PER_VARIANT",
    "AREA_TOLERANCE",
    "normalise_option",
    "validate_variant",
    "build_variant_set",
    "derivation_chain",
    "baseline_findings",
    "process_option_conflict",
    "marking_gaps",
    "duplicate_markings",
    "site_shortfalls",
    "occupied_area_mm2",
    "assess_mask_set",
]

# A variant carried on the mask set for evaluation needs enough sites across
# the wafer for the measured spread to mean anything.
MIN_SITES_PER_VARIANT = 5

# Area comparisons are sums of products; absorb representation error at the
# budget instead of trimming the budget itself.
AREA_TOLERANCE = 1e-9


def _require_text(value, label):
    """Return a stripped non-empty string, or raise."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    text = value.strip()
    if not text:
        raise ValueError("%s must not be empty" % label)
    return text


def _optional_text(value, label):
    """Return a stripped string, or None when the field is absent."""
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("%s must be a string or None, got %r" % (label, value))
    text = value.strip()
    return text or None


def _positive_real(value, label):
    """Return a strictly positive finite float, or raise."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    if number <= 0.0:
        raise ValueError("%s must be positive, got %g" % (label, number))
    return number


def normalise_option(name):
    """Return the canonical spelling of a process option name."""
    text = _require_text(name, "process option")
    return "-".join(text.lower().replace("_", " ").replace("-", " ").split())


def validate_variant(variant):
    """Return one validated variant record, or raise on a malformed entry."""
    if not isinstance(variant, dict):
        raise ValueError("each variant must be a mapping, got %r" % (variant,))
    for key in ("id", "process_option", "sites", "die_area_mm2"):
        if key not in variant:
            raise ValueError("variant missing required key '%s'" % key)
    identifier = _require_text(variant["id"], "variant id")
    baseline = _optional_text(variant.get("baseline"), "variant baseline")
    if baseline == identifier:
        raise ValueError("variant %s derives from itself" % identifier)
    option = normalise_option(variant["process_option"])
    sites = variant["sites"]
    if not isinstance(sites, int) or isinstance(sites, bool):
        raise ValueError("variant %s sites must be an integer" % identifier)
    if sites <= 0:
        raise ValueError("variant %s sites must be positive, got %d" % (identifier, sites))
    area = _positive_real(variant["die_area_mm2"], "variant %s die_area_mm2" % identifier)
    return {
        "id": identifier,
        "baseline": baseline,
        "process_option": option,
        "marking": _optional_text(variant.get("marking"), "variant marking"),
        "sites": sites,
        "die_area_mm2": area,
    }


def build_variant_set(variants):
    """Return the validated variant set, refusing a duplicate identifier."""
    if not isinstance(variants, (list, tuple)) or not variants:
        raise ValueError("variants must be a non-empty sequence of mappings")
    records = []
    seen = set()
    for variant in variants:
        record = validate_variant(variant)
        if record["id"] in seen:
            raise ValueError("duplicate variant id %r" % record["id"])
        seen.add(record["id"])
        records.append(record)
    return records


def derivation_chain(records, variant_id):
    """Return the chain from a variant back to its root baseline.

    Raises on a baseline the mask set does not declare and on a loop.
    """
    by_id = {record["id"]: record for record in records}
    if variant_id not in by_id:
        raise ValueError("variant %r is not declared on this mask set" % variant_id)
    chain = [variant_id]
    seen = {variant_id}
    current = by_id[variant_id]
    while current["baseline"] is not None:
        parent = current["baseline"]
        if parent not in by_id:
            raise ValueError(
                "variant %s derives from baseline %r, which the mask set does not declare"
                % (current["id"], parent)
            )
        if parent in seen:
            raise ValueError(
                "derivation loop reached from variant %s through %s"
                % (variant_id, " -> ".join(chain))
            )
        chain.append(parent)
        seen.add(parent)
        current = by_id[parent]
    return chain


def baseline_findings(records):
    """Return (variant_id, reason) for every unresolvable derivation."""
    findings = []
    for record in records:
        try:
            derivation_chain(records, record["id"])
        except ValueError as exc:
            findings.append((record["id"], str(exc)))
    return findings


def process_option_conflict(records, compatible_groups=None):
    """Return the process options that cannot share one wafer.

    A mask set runs a single option unless every declared option sits inside
    one of the declared compatible groups. The returned list is empty when the
    set is buildable as one wafer flow.
    """
    groups = []
    for group in compatible_groups or []:
        if isinstance(group, str) or not isinstance(
            group, (list, tuple, set, frozenset)
        ):
            raise ValueError("each compatible group must be a sequence of option names")
        groups.append({normalise_option(name) for name in group})
    declared = sorted({record["process_option"] for record in records})
    if len(declared) <= 1:
        return []
    for group in groups:
        if set(declared) <= group:
            return []
    return declared


def marking_gaps(records):
    """Return the identifiers of variants whose die carries no marking."""
    return [record["id"] for record in records if record["marking"] is None]


def duplicate_markings(records):
    """Return the markings shared by more than one variant."""
    counts = {}
    for record in records:
        marking = record["marking"]
        if marking is None:
            continue
        counts[marking] = counts.get(marking, 0) + 1
    return sorted(marking for marking, count in counts.items() if count > 1)


def site_shortfalls(records, minimum_sites=MIN_SITES_PER_VARIANT):
    """Return (variant_id, sites) for every variant below the site minimum."""
    if not isinstance(minimum_sites, int) or isinstance(minimum_sites, bool):
        raise ValueError("minimum_sites must be an integer")
    if minimum_sites < 1:
        raise ValueError("minimum_sites must be at least 1, got %d" % minimum_sites)
    return [(r["id"], r["sites"]) for r in records if r["sites"] < minimum_sites]


def occupied_area_mm2(records):
    """Return the reticle field area the declared variants occupy."""
    return sum(record["sites"] * record["die_area_mm2"] for record in records)


def assess_mask_set(spec):
    """Run the full clause 7.2.2 mask-set variant assessment.

    spec keys: variants (sequence), reticle_field_area_mm2, optional
    compatible_process_groups and minimum_sites.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("variants", "reticle_field_area_mm2"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    budget = _positive_real(spec["reticle_field_area_mm2"], "reticle_field_area_mm2")
    minimum_sites = spec.get("minimum_sites", MIN_SITES_PER_VARIANT)

    records = build_variant_set(spec["variants"])
    baselines = baseline_findings(records)
    conflict = process_option_conflict(records, spec.get("compatible_process_groups"))
    unmarked = marking_gaps(records)
    repeated = duplicate_markings(records)
    shortfalls = site_shortfalls(records, minimum_sites)
    used = occupied_area_mm2(records)
    slack = max(abs(used), abs(budget), 1.0) * AREA_TOLERANCE
    over_budget = used > budget + slack

    findings = []
    if baselines:
        findings.append(
            "%d variant(s) do not resolve to a declared baseline: %s"
            % (len(baselines), ", ".join(item[0] for item in baselines))
        )
    if conflict:
        findings.append(
            "process options cannot share one wafer flow: %s" % ", ".join(conflict)
        )
    if unmarked:
        findings.append(
            "%d variant(s) carry no identification marking and cannot be told apart "
            "after dicing: %s" % (len(unmarked), ", ".join(unmarked))
        )
    if repeated:
        findings.append(
            "%d marking(s) are shared by more than one variant: %s"
            % (len(repeated), ", ".join(repeated))
        )
    if shortfalls:
        findings.append(
            "%d variant(s) carry fewer than %d sites: %s"
            % (
                len(shortfalls),
                minimum_sites,
                ", ".join("%s (%d)" % item for item in shortfalls),
            )
        )
    if over_budget:
        findings.append(
            "the declared variants occupy %.4f mm2 of a %.4f mm2 reticle field"
            % (used, budget)
        )

    return {
        "variants": records,
        "baseline_findings": baselines,
        "process_option_conflict": conflict,
        "unmarked_variants": unmarked,
        "duplicate_markings": repeated,
        "site_shortfalls": shortfalls,
        "occupied_area_mm2": used,
        "reticle_field_area_mm2": budget,
        "area_utilisation": used / budget,
        "minimum_sites": minimum_sites,
        "findings": findings,
        "releasable": not findings,
    }
