"""Limits on reattaching interconnect wires inside a hybrid.

Anchor: ECSS-Q-ST-60-05C clause 10.5.3 (reattaching an interconnect wire
during permitted corrective work, and how many bonding attempts a single bond
site may take). Paraphrased into an implementable procedure; no standard text
is reproduced.

Procedure implemented here
--------------------------
1. Validate each bond site: what kind of pad or post it is, how big the
   bondable area is, what has already been bonded there and whether the
   remnant of the previous bond was removed.
2. Count the attempts. Every pad kind carries an attempt allowance covering
   the original bond and the rebonds after it; the allowance is consumed by
   attempts, not by successes.
3. Measure the area. Every bond leaves a footprint, and the footprints
   accumulate on a pad that does not grow. A proposed rebond whose footprint
   does not fit in what is left is refused on geometry alone, whatever the
   attempt count says.
4. Apply the placement rules: a rebond placed over a previous footprint is
   refused where the pad kind does not permit stacking, and any rebond over
   an unremoved remnant is refused outright.
5. Note the wire-to-pad metal pairing as a caution rather than a refusal, and
   return a per-site and an overall disposition.

Footprint areas are quotients and products of physical dimensions that land
exactly on a full pad in realistic layouts, so the utilisation comparison
carries a tolerance instead of being a strict inequality.
"""

import math

__all__ = [
    "RATIO_TOLERANCE",
    "PAD_KINDS",
    "WIRE_PAD_CAUTIONS",
    "validate_bond",
    "bond_footprint_um2",
    "validate_bond_site",
    "pad_area_um2",
    "attempts_used",
    "attempts_allowed",
    "rebonds_remaining",
    "consumed_area_um2",
    "footprint_utilisation",
    "assess_bond_site",
    "assess_rebonding",
]

# A pad filled exactly by its bonds is a designed condition, not a rare one.
RATIO_TOLERANCE = 1e-9

# Attempt allowance covers the first bond plus every rebond after it.
PAD_KINDS = {
    "chip-pad": {"attempt_allowance": 2, "stacking_permitted": False},
    "substrate-pad": {"attempt_allowance": 3, "stacking_permitted": False},
    "package-post": {"attempt_allowance": 3, "stacking_permitted": True},
}

# Wire metal against pad metal. A pairing listed here is workable but carries
# an intermetallic caution; it is not a refusal.
WIRE_PAD_CAUTIONS = {
    ("gold", "aluminium"): "gold wire onto aluminium metallisation forms intermetallics",
    ("aluminium", "gold"): "aluminium wire onto gold metallisation forms intermetallics",
}


def _require_positive_number(value, label):
    """Return value as a strictly positive finite float."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (label, value))
    number = float(value)
    if math.isnan(number) or math.isinf(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if number <= 0.0:
        raise ValueError("%s must be positive, got %g" % (label, number))
    return number


def _require_identity(value, label):
    """Return a stripped, lower-cased, non-empty identity string."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip().lower()


def validate_bond(bond, label="bond"):
    """Return the normalised geometry of one bond.

    A ball bond is described by its flattened diameter; a wedge bond by its
    width and its length. Anything else is an input error -- an unmeasured
    bond cannot be area-budgeted on a pad that does not grow.
    """
    if not isinstance(bond, dict):
        raise ValueError("%s must be a mapping" % label)
    if "bond_type" not in bond:
        raise ValueError("%s missing 'bond_type'" % label)
    bond_type = _require_identity(bond["bond_type"], "%s['bond_type']" % label)
    if bond_type == "ball":
        diameter = _require_positive_number(
            bond.get("diameter_um"), "%s['diameter_um']" % label
        )
        return {"bond_type": "ball", "diameter_um": diameter}
    if bond_type == "wedge":
        return {
            "bond_type": "wedge",
            "width_um": _require_positive_number(
                bond.get("width_um"), "%s['width_um']" % label
            ),
            "length_um": _require_positive_number(
                bond.get("length_um"), "%s['length_um']" % label
            ),
        }
    raise ValueError("%s['bond_type'] must be 'ball' or 'wedge', got %r" % (label, bond_type))


def bond_footprint_um2(bond, label="bond"):
    """Return the pad area one bond occupies, in square micrometres."""
    geometry = validate_bond(bond, label)
    if geometry["bond_type"] == "ball":
        radius = geometry["diameter_um"] / 2.0
        return math.pi * radius * radius
    return geometry["width_um"] * geometry["length_um"]


def validate_bond_site(site, label="site"):
    """Return the normalised bond-site record.

    Bonds already placed are history, not an error, even when there are more
    of them than the allowance -- an over-bonded pad is the case this
    assessment exists to catch.
    """
    if not isinstance(site, dict):
        raise ValueError("%s must be a mapping" % label)
    for key in ("site_id", "pad_kind", "pad_width_um", "pad_length_um"):
        if key not in site:
            raise ValueError("%s missing required key '%s'" % (label, key))
    pad_kind = _require_identity(site["pad_kind"], "%s['pad_kind']" % label)
    if pad_kind not in PAD_KINDS:
        raise ValueError(
            "unknown pad kind %r; known: %s" % (site["pad_kind"], ", ".join(sorted(PAD_KINDS)))
        )
    prior = site.get("prior_bonds", [])
    if isinstance(prior, dict) or not isinstance(prior, (list, tuple)):
        raise ValueError("%s['prior_bonds'] must be a sequence of bond geometries" % label)
    return {
        "site_id": _require_identity(site["site_id"], "%s['site_id']" % label),
        "pad_kind": pad_kind,
        "pad_width_um": _require_positive_number(
            site["pad_width_um"], "%s['pad_width_um']" % label
        ),
        "pad_length_um": _require_positive_number(
            site["pad_length_um"], "%s['pad_length_um']" % label
        ),
        "prior_bonds": [
            validate_bond(b, "%s['prior_bonds'][%d]" % (label, i)) for i, b in enumerate(prior)
        ],
        "remnant_removed": bool(site.get("remnant_removed", False)),
        "over_previous_footprint": bool(site.get("over_previous_footprint", False)),
        "wire_material": _require_identity(
            site.get("wire_material", "aluminium"), "%s['wire_material']" % label
        ),
        "pad_metallisation": _require_identity(
            site.get("pad_metallisation", "aluminium"), "%s['pad_metallisation']" % label
        ),
    }


def pad_area_um2(site):
    """Return the bondable area of the pad or post at this site."""
    record = validate_bond_site(site)
    return record["pad_width_um"] * record["pad_length_um"]


def attempts_used(site):
    """Return how many bonding attempts this site has already taken."""
    return len(validate_bond_site(site)["prior_bonds"])


def attempts_allowed(pad_kind, allowances=None):
    """Return the attempt allowance for a pad kind, original bond included."""
    kind = _require_identity(pad_kind, "pad_kind")
    table = PAD_KINDS if allowances is None else allowances
    if kind not in table:
        raise ValueError("unknown pad kind %r" % (pad_kind,))
    return table[kind]["attempt_allowance"]


def rebonds_remaining(site, allowances=None):
    """Return how many further attempts this site's allowance still permits."""
    record = validate_bond_site(site)
    return max(0, attempts_allowed(record["pad_kind"], allowances) - len(record["prior_bonds"]))


def consumed_area_um2(site):
    """Return the pad area the bonds already placed at this site occupy."""
    record = validate_bond_site(site)
    return sum(bond_footprint_um2(b) for b in record["prior_bonds"])


def footprint_utilisation(site, proposed_bond):
    """Return the fraction of the pad used once the proposed rebond is added."""
    area = pad_area_um2(site)
    return (consumed_area_um2(site) + bond_footprint_um2(proposed_bond, "proposed_bond")) / area


def assess_bond_site(site, proposed_bond, allowances=None):
    """Grade one proposed rebond at one site."""
    record = validate_bond_site(site)
    proposed = validate_bond(proposed_bond, "proposed_bond")
    allowance = attempts_allowed(record["pad_kind"], allowances)
    used = len(record["prior_bonds"])
    remaining = max(0, allowance - used)
    utilisation = footprint_utilisation(site, proposed_bond)
    stacking_permitted = (PAD_KINDS if allowances is None else allowances)[record["pad_kind"]][
        "stacking_permitted"
    ]

    refusals = []
    cautions = []
    if remaining <= 0:
        refusals.append(
            "site %s has taken %d of %d permitted attempts" % (record["site_id"], used, allowance)
        )
    if utilisation > 1.0 + RATIO_TOLERANCE:
        refusals.append(
            "proposed bond takes pad utilisation to %.4f; it does not fit the bondable area"
            % utilisation
        )
    if used > 0 and not record["remnant_removed"]:
        refusals.append(
            "remnant of the previous bond at site %s was not removed" % record["site_id"]
        )
    if record["over_previous_footprint"] and not stacking_permitted:
        refusals.append(
            "a %s does not accept a bond placed over a previous footprint" % record["pad_kind"]
        )
    caution = WIRE_PAD_CAUTIONS.get((record["wire_material"], record["pad_metallisation"]))
    if caution:
        cautions.append(caution)

    if refusals:
        disposition = "rebond-not-permitted"
    elif cautions:
        disposition = "rebond-permitted-with-caution"
    else:
        disposition = "rebond-permitted"
    return {
        "site_id": record["site_id"],
        "pad_kind": record["pad_kind"],
        "attempts_used": used,
        "attempts_allowed": allowance,
        "attempts_remaining": remaining,
        "pad_area_um2": pad_area_um2(site),
        "proposed_footprint_um2": bond_footprint_um2(proposed, "proposed_bond"),
        "footprint_utilisation": utilisation,
        "refusals": refusals,
        "cautions": cautions,
        "disposition": disposition,
        "permitted": disposition != "rebond-not-permitted",
    }


def assess_rebonding(spec):
    """Run the full clause 10.5.3 rebonding assessment over a set of sites.

    spec keys: sites -- a sequence of records each carrying a bond site under
    'site' and the bond it would take under 'proposed_bond'; optional
    allowances overriding PAD_KINDS, and optional approved_procedure
    (default False).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    if "sites" not in spec:
        raise ValueError("spec missing required key 'sites'")
    sites = spec["sites"]
    if isinstance(sites, dict) or not isinstance(sites, (list, tuple)):
        raise ValueError("spec['sites'] must be a sequence of site records")
    if not sites:
        raise ValueError("no bond sites to assess")
    approved = spec.get("approved_procedure", False)
    if not isinstance(approved, bool):
        raise ValueError("approved_procedure must be a boolean")
    allowances = spec.get("allowances")

    results = []
    for index, entry in enumerate(sites):
        if not isinstance(entry, dict) or "site" not in entry or "proposed_bond" not in entry:
            raise ValueError(
                "sites[%d] must be a mapping with 'site' and 'proposed_bond'" % index
            )
        results.append(assess_bond_site(entry["site"], entry["proposed_bond"], allowances))

    refused = [r for r in results if not r["permitted"]]
    cautioned = [r for r in results if r["permitted"] and r["cautions"]]
    blockers = []
    if not approved:
        blockers.append("no approved rebonding procedure covers this corrective work")
    if refused:
        blockers.append(
            "%d of %d site(s) refuse the proposed rebond" % (len(refused), len(results))
        )
    if blockers:
        overall = "not-permitted"
    elif cautioned:
        overall = "permitted-with-caution"
    else:
        overall = "permitted"
    return {
        "site_count": len(results),
        "sites": results,
        "refused_sites": [r["site_id"] for r in refused],
        "cautioned_sites": [r["site_id"] for r in cautioned],
        "blockers": blockers,
        "disposition": overall,
        "permitted": overall != "not-permitted",
    }
