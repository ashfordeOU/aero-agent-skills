"""Equipment and component type grouping for multipaction margin policy.

Anchor: ECSS-E-ST-20-01C clause 4.4.1 (sorting radio-frequency equipment and
components into type groups, which is what drives the applicable multipaction
margin).

Offline, deterministic, python3 standard library only.

Procedure implemented here (paraphrased, no standard text reproduced):

* Two independent properties decide the group of an item. The first is how
  well the gap geometry confines the field: a uniform waveguide or a coaxial
  line has a single well-defined gap, a printed planar line has fringing
  edges, a radiating aperture or a multi-cavity assembly has many
  non-uniform gaps, and a dielectric-loaded part adds surfaces whose charging
  and emission behaviour is the least predictable of all. The second is how
  well the surface itself is known: measured on the flight surface treatment,
  inferred from a representative process coupon, or unknown.
* Each property maps to a tier from 1 (best known) to 4 (least known), and the
  item takes the worse of the two tiers. Ignorance in either property cannot
  be averaged away by confidence in the other.
* The tier fixes a base margin. Design heritage then adds to it: a recurrent
  build of already-qualified hardware adds nothing, a modified recurrent build
  adds one decibel, a new design adds two.
* An assembly inherits the worst tier of its constituents and the largest
  required margin among them, together with its own intrinsic properties. The
  constituent that sets the assembly group is named, so the margin can be
  traced to the part that caused it.
"""

from __future__ import annotations

import math

GEOMETRY_TIERS = {
    "uniform-waveguide": 1,
    "coaxial-line": 1,
    "planar-printed": 2,
    "radiating-aperture": 3,
    "non-uniform-assembly": 3,
    "dielectric-loaded": 4,
}

SURFACE_TIERS = {
    "flight-surface-measured": 1,
    "process-coupon-sample": 2,
    "unknown-surface": 4,
}

HERITAGE_ADDERS_DB = {
    "recurrent-qualified": 0.0,
    "modified-recurrent": 1.0,
    "new-design": 2.0,
}

BASE_MARGIN_DB = {
    1: 3.0,
    2: 4.0,
    3: 6.0,
    4: 8.0,
}

GROUP_NAMES = {
    1: "group-1-uniform-gap-known-surface",
    2: "group-2-fringing-gap-or-sampled-surface",
    3: "group-3-non-uniform-gap-assembly",
    4: "group-4-dielectric-loaded-or-unknown-surface",
}

ITEM_KINDS = ("component", "equipment")

# A declared margin equal to the derived requirement passes: the derived value
# is a sum of decibel terms and can differ from a typed-in figure by a few
# units in the last place. The policy value itself is never lowered.
MARGIN_TOLERANCE_DB = 1e-9


def geometry_tier(family):
    """Tier for a gap-geometry family; unknown families are rejected."""
    if family not in GEOMETRY_TIERS:
        raise ValueError(
            "unknown geometry family %r (known: %s)"
            % (family, ", ".join(sorted(GEOMETRY_TIERS)))
        )
    return GEOMETRY_TIERS[family]


def surface_tier(state):
    """Tier for the state of the secondary-emission surface knowledge."""
    if state not in SURFACE_TIERS:
        raise ValueError(
            "unknown surface state %r (known: %s)"
            % (state, ", ".join(sorted(SURFACE_TIERS)))
        )
    return SURFACE_TIERS[state]


def heritage_adder_db(heritage):
    """Decibel adder carried by the design heritage of the item."""
    if heritage not in HERITAGE_ADDERS_DB:
        raise ValueError(
            "unknown heritage %r (known: %s)"
            % (heritage, ", ".join(sorted(HERITAGE_ADDERS_DB)))
        )
    return HERITAGE_ADDERS_DB[heritage]


def group_name(tier):
    """Human-readable group label for a tier between 1 and 4."""
    if tier not in GROUP_NAMES:
        raise ValueError("tier must be one of 1, 2, 3, 4, got %r" % (tier,))
    return GROUP_NAMES[tier]


def normalize_item(raw):
    """Validate one equipment or component declaration and fill its defaults."""
    if not isinstance(raw, dict):
        raise ValueError("item must be a mapping, got %r" % (type(raw).__name__,))
    item_id = raw.get("id")
    if not isinstance(item_id, str) or not item_id.strip():
        raise ValueError("item needs a non-empty string id, got %r" % (item_id,))
    kind = raw.get("kind", "component")
    if kind not in ITEM_KINDS:
        raise ValueError(
            "kind of %r must be one of %s, got %r"
            % (item_id, ", ".join(ITEM_KINDS), kind)
        )
    geometry = raw.get("geometry_family")
    geometry_tier(geometry)  # validation only
    surface = raw.get("surface_state")
    surface_tier(surface)  # validation only
    heritage = raw.get("heritage", "new-design")
    heritage_adder_db(heritage)  # validation only
    constituents = raw.get("constituents", [])
    if not isinstance(constituents, (list, tuple)):
        raise ValueError("constituents of %r must be a list" % (item_id,))
    constituents = list(constituents)
    if constituents and kind != "equipment":
        raise ValueError(
            "item %r is a component and cannot declare constituents" % (item_id,)
        )
    for ref in constituents:
        if not isinstance(ref, str) or not ref.strip():
            raise ValueError(
                "constituent reference of %r must be a non-empty string, got %r"
                % (item_id, ref)
            )
    declared_group = raw.get("declared_group")
    if declared_group is not None and declared_group not in GROUP_NAMES.values():
        raise ValueError(
            "declared_group of %r is not a known group label, got %r"
            % (item_id, declared_group)
        )
    declared_margin = raw.get("declared_margin_db")
    if declared_margin is not None:
        if isinstance(declared_margin, bool) or not isinstance(
            declared_margin, (int, float)
        ):
            raise ValueError(
                "declared_margin_db of %r must be a real number, got %r"
                % (item_id, declared_margin)
            )
        declared_margin = float(declared_margin)
        if not math.isfinite(declared_margin):
            raise ValueError("declared_margin_db of %r must be finite" % (item_id,))
        if declared_margin < 0.0:
            raise ValueError(
                "declared_margin_db of %r must not be negative" % (item_id,)
            )
    return {
        "id": item_id,
        "kind": kind,
        "geometry_family": geometry,
        "surface_state": surface,
        "heritage": heritage,
        "constituents": constituents,
        "declared_group": declared_group,
        "declared_margin_db": declared_margin,
    }


def categorize_item(raw):
    """Derive the intrinsic type group of one item from its own properties."""
    item = normalize_item(raw)
    g_tier = geometry_tier(item["geometry_family"])
    s_tier = surface_tier(item["surface_state"])
    tier = max(g_tier, s_tier)
    driver = "gap-geometry" if g_tier >= s_tier else "surface-knowledge"
    record = dict(item)
    record.update(
        {
            "geometry_tier": g_tier,
            "surface_tier": s_tier,
            "tier": tier,
            "group": group_name(tier),
            "governing_property": driver,
        }
    )
    return record


def required_margin_db(tier, heritage):
    """Applicable multipaction margin for a tier and a heritage state."""
    if tier not in BASE_MARGIN_DB:
        raise ValueError("tier must be one of 1, 2, 3, 4, got %r" % (tier,))
    return BASE_MARGIN_DB[tier] + heritage_adder_db(heritage)


def margin_meets_policy(declared_margin_db, policy_margin_db):
    """True when a declared margin reaches the policy value within tolerance."""
    for value, label in (
        (declared_margin_db, "declared_margin_db"),
        (policy_margin_db, "policy_margin_db"),
    ):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("%s must be a real number, got %r" % (label, value))
        if not math.isfinite(float(value)):
            raise ValueError("%s must be finite, got %r" % (label, value))
    return float(declared_margin_db) >= float(policy_margin_db) - MARGIN_TOLERANCE_DB


def assess_item(raw):
    """Categorize one item and audit whatever it declared about itself."""
    record = categorize_item(raw)
    record["required_margin_db"] = required_margin_db(record["tier"], record["heritage"])
    findings = []
    declared_group = record["declared_group"]
    if declared_group is not None and declared_group != record["group"]:
        declared_tier = None
        for tier, label in GROUP_NAMES.items():
            if label == declared_group:
                declared_tier = tier
        if declared_tier is not None and declared_tier < record["tier"]:
            findings.append("group-understated")
        else:
            findings.append("group-overstated")
    declared_margin = record["declared_margin_db"]
    if declared_margin is not None and not margin_meets_policy(
        declared_margin, record["required_margin_db"]
    ):
        findings.append("margin-below-type-group-policy")
    record["findings"] = findings
    return record


def rollup_assembly(assembly, components):
    """Group and margin an assembly inherits from itself and its constituents.

    ``components`` is a mapping of component id to an assessed record (the
    output of :func:`assess_item`). Every constituent named by the assembly
    must be present, otherwise the roll-up is incomplete and is rejected.
    """
    record = assess_item(assembly)
    if record["kind"] != "equipment":
        raise ValueError("roll-up applies to an equipment item, got %r" % (record["kind"],))
    if not isinstance(components, dict):
        raise ValueError(
            "components must be a mapping of id to assessed record, got %r"
            % (type(components).__name__,)
        )
    tier = record["tier"]
    margin = record["required_margin_db"]
    governing_id = record["id"]
    for ref in record["constituents"]:
        if ref not in components:
            raise ValueError(
                "assembly %r names constituent %r which is not in the inventory"
                % (record["id"], ref)
            )
        child = components[ref]
        child_tier = child["tier"]
        child_margin = child["required_margin_db"]
        if (child_tier, child_margin) > (tier, margin):
            tier = child_tier
            margin = max(margin, child_margin)
            governing_id = ref
        elif child_margin > margin:
            margin = child_margin
            governing_id = ref
    rolled = dict(record)
    rolled.update(
        {
            "tier": tier,
            "group": group_name(tier),
            "required_margin_db": margin,
            "governing_item_id": governing_id,
        }
    )
    return rolled


def categorize_inventory(items):
    """Sort a whole inventory into type groups and roll up every assembly.

    Components are categorized first, then assemblies inherit from them. The
    return carries the per-item records, a count per group, the findings and
    the most demanding margin in the inventory.
    """
    if not isinstance(items, (list, tuple)):
        raise ValueError("items must be a list or tuple, got %r" % (type(items).__name__,))
    if len(items) == 0:
        raise ValueError("inventory must contain at least one item")
    normalized = [normalize_item(raw) for raw in items]
    seen = set()
    for item in normalized:
        if item["id"] in seen:
            raise ValueError("duplicate item id %r" % (item["id"],))
        seen.add(item["id"])
    assessed = {}
    for item in normalized:
        if item["kind"] == "component":
            assessed[item["id"]] = assess_item(item)
    records = []
    for item in normalized:
        if item["kind"] == "component":
            records.append(assessed[item["id"]])
        else:
            records.append(rollup_assembly(item, assessed))
    counts = {}
    for record in records:
        counts[record["group"]] = counts.get(record["group"], 0) + 1
    findings = []
    for record in records:
        for finding in record["findings"]:
            findings.append({"id": record["id"], "finding": finding})
    worst = max(records, key=lambda r: (r["required_margin_db"], r["id"]))
    return {
        "records": records,
        "group_counts": counts,
        "findings": findings,
        "worst_case_item_id": worst["id"],
        "worst_case_margin_db": worst["required_margin_db"],
        "consistent": len(findings) == 0,
    }
