#!/usr/bin/env python3
"""Product-type pre-tailoring matrix logic (ECSS-E-ST-20C clause 8.3 anchor).

Deterministic, offline, stdlib-only. Paraphrased procedure -- no standard
text is reproduced. The module answers one question per matrix cell: before
any project-specific tailoring runs, what disposition does an electrical
engineering provision group hold for a given product type and its declared
feature set, and is the resulting matrix internally consistent?

Dispositions
------------
applicable      the provision group reaches the item as written
tailorable      the group reaches the item but the project may reduce it
not-applicable  the group has no object on this item

A feature (a solar-array-generator, an electrochemical-energy-store, a
radio-frequency-transmitter, an electro-explosive-device, a
high-voltage-assembly, a harness-and-cable-network, a magnetically quiet
item) can only raise a disposition, never lower it: if the hardware exists
on the item, the group that governs it applies whatever the product-type
default said.
"""

import math

__all__ = [
    "PRODUCT_TYPES",
    "FEATURE_TYPES",
    "PROVISION_GROUPS",
    "DISPOSITIONS",
    "normalize_product_type",
    "normalize_feature",
    "normalize_disposition",
    "clause_disposition",
    "build_pre_tailoring_matrix",
    "apply_tailoring_request",
    "audit_matrix_completeness",
    "summarize_matrix",
    "assess_pre_tailoring",
]

# Relative tolerance used when a computed share is compared against a
# declared threshold; a share that lands a few ULPs under an exactly met
# threshold is still met. The engineering limit itself is never widened.
_SHARE_REL_TOL = 1e-9
_SHARE_ABS_TOL = 1e-12

DISPOSITIONS = ("applicable", "tailorable", "not-applicable")
_DISPOSITION_RANK = {"not-applicable": 0, "tailorable": 1, "applicable": 2}

PRODUCT_TYPES = (
    "equipment-unit",
    "subsystem",
    "payload",
    "launcher-stage",
)

_PRODUCT_SYNONYMS = {
    "unit": "equipment-unit",
    "equipment": "equipment-unit",
    "equipment unit": "equipment-unit",
    "box": "equipment-unit",
    "sub-system": "subsystem",
    "sub system": "subsystem",
    "instrument": "payload",
    "payload instrument": "payload",
    "stage": "launcher-stage",
    "launcher stage": "launcher-stage",
    "upper-stage": "launcher-stage",
}

FEATURE_TYPES = (
    "solar-array-generator",
    "electrochemical-energy-store",
    "radio-frequency-transmitter",
    "antenna-subassembly",
    "electro-explosive-device",
    "high-voltage-assembly",
    "harness-and-cable-network",
    "magnetically-quiet-item",
)

_FEATURE_SYNONYMS = {
    "solar array": "solar-array-generator",
    "solar-array": "solar-array-generator",
    "photovoltaic-generator": "solar-array-generator",
    "battery": "electrochemical-energy-store",
    "accumulator": "electrochemical-energy-store",
    "rf transmitter": "radio-frequency-transmitter",
    "transmitter": "radio-frequency-transmitter",
    "antenna": "antenna-subassembly",
    "eed": "electro-explosive-device",
    "pyro-initiator": "electro-explosive-device",
    "high voltage": "high-voltage-assembly",
    "harness": "harness-and-cable-network",
    "cable-network": "harness-and-cable-network",
    "magnetic-cleanliness-item": "magnetically-quiet-item",
}

# Provision groups of the electrical engineering scope. Each carries the
# disposition it holds for a bare product type of each kind, plus the
# features that force it to "applicable" wherever they are declared.
PROVISION_GROUPS = {
    "g-electrical-architecture": {
        "title": "electrical architecture definition",
        "defaults": {
            "equipment-unit": "tailorable",
            "subsystem": "applicable",
            "payload": "applicable",
            "launcher-stage": "applicable",
        },
        "features": (),
    },
    "g-power-generation": {
        "title": "power-generation chain",
        "defaults": {
            "equipment-unit": "not-applicable",
            "subsystem": "tailorable",
            "payload": "not-applicable",
            "launcher-stage": "tailorable",
        },
        "features": ("solar-array-generator",),
    },
    "g-energy-storage": {
        "title": "energy-storage assembly",
        "defaults": {
            "equipment-unit": "not-applicable",
            "subsystem": "tailorable",
            "payload": "not-applicable",
            "launcher-stage": "tailorable",
        },
        "features": ("electrochemical-energy-store",),
    },
    "g-power-distribution": {
        "title": "power-distribution and protection",
        "defaults": {
            "equipment-unit": "tailorable",
            "subsystem": "applicable",
            "payload": "tailorable",
            "launcher-stage": "applicable",
        },
        "features": ("harness-and-cable-network",),
    },
    "g-electromagnetic-compatibility": {
        "title": "electromagnetic-compatibility provisions",
        "defaults": {
            "equipment-unit": "applicable",
            "subsystem": "applicable",
            "payload": "applicable",
            "launcher-stage": "applicable",
        },
        "features": (),
    },
    "g-electro-explosive-devices": {
        "title": "electro-explosive-device circuits",
        "defaults": {
            "equipment-unit": "not-applicable",
            "subsystem": "not-applicable",
            "payload": "not-applicable",
            "launcher-stage": "tailorable",
        },
        "features": ("electro-explosive-device",),
    },
    "g-radio-frequency-chain": {
        "title": "radio-frequency and antenna chain",
        "defaults": {
            "equipment-unit": "not-applicable",
            "subsystem": "tailorable",
            "payload": "tailorable",
            "launcher-stage": "not-applicable",
        },
        "features": ("radio-frequency-transmitter", "antenna-subassembly"),
    },
    "g-grounding-and-bonding": {
        "title": "grounding and bonding scheme",
        "defaults": {
            "equipment-unit": "applicable",
            "subsystem": "applicable",
            "payload": "applicable",
            "launcher-stage": "applicable",
        },
        "features": ("harness-and-cable-network",),
    },
    "g-high-voltage-and-discharge": {
        "title": "high-voltage and gas-discharge control",
        "defaults": {
            "equipment-unit": "not-applicable",
            "subsystem": "not-applicable",
            "payload": "not-applicable",
            "launcher-stage": "not-applicable",
        },
        "features": ("high-voltage-assembly", "radio-frequency-transmitter"),
    },
    "g-magnetic-cleanliness": {
        "title": "magnetic-cleanliness control",
        "defaults": {
            "equipment-unit": "not-applicable",
            "subsystem": "tailorable",
            "payload": "tailorable",
            "launcher-stage": "not-applicable",
        },
        "features": ("magnetically-quiet-item",),
    },
}


def _meets(value, threshold):
    """True when value reaches threshold, absorbing float representation
    error at an exactly met threshold (the threshold is never widened)."""
    if value >= threshold:
        return True
    return math.isclose(value, threshold, rel_tol=_SHARE_REL_TOL,
                        abs_tol=_SHARE_ABS_TOL)


def _canonical(raw, what):
    if not isinstance(raw, str):
        raise ValueError("%s must be a string, got %r" % (what, type(raw).__name__))
    token = " ".join(raw.strip().lower().split())
    if not token:
        raise ValueError("%s must not be empty" % what)
    return token


def normalize_product_type(raw):
    """Resolve a declared product type to its canonical token."""
    token = _canonical(raw, "product type")
    token = _PRODUCT_SYNONYMS.get(token, token.replace(" ", "-"))
    token = _PRODUCT_SYNONYMS.get(token, token)
    if token not in PRODUCT_TYPES:
        raise ValueError(
            "unknown product type %r; expected one of %s"
            % (raw, ", ".join(PRODUCT_TYPES))
        )
    return token


def normalize_feature(raw):
    """Resolve a declared feature to its canonical token."""
    token = _canonical(raw, "feature")
    token = _FEATURE_SYNONYMS.get(token, token.replace(" ", "-"))
    token = _FEATURE_SYNONYMS.get(token, token)
    if token not in FEATURE_TYPES:
        raise ValueError(
            "unknown feature %r; expected one of %s"
            % (raw, ", ".join(FEATURE_TYPES))
        )
    return token


def normalize_disposition(raw):
    """Resolve a declared disposition to its canonical token."""
    token = _canonical(raw, "disposition")
    token = token.replace(" ", "-")
    aliases = {
        "n/a": "not-applicable",
        "na": "not-applicable",
        "applies": "applicable",
        "tailorable-with-justification": "tailorable",
    }
    token = aliases.get(token, token)
    if token not in DISPOSITIONS:
        raise ValueError(
            "unknown disposition %r; expected one of %s"
            % (raw, ", ".join(DISPOSITIONS))
        )
    return token


def clause_disposition(group_id, product_type, features=()):
    """Derive the pre-tailoring disposition of one provision group.

    Returns a record naming the disposition and the driver that set it:
    "product-type-default" when the bare product type decided, or the
    feature token when declared hardware raised the disposition.
    """
    if group_id not in PROVISION_GROUPS:
        raise ValueError(
            "unknown provision group %r; expected one of %s"
            % (group_id, ", ".join(sorted(PROVISION_GROUPS)))
        )
    ptype = normalize_product_type(product_type)
    if isinstance(features, str):
        raise ValueError("features must be a sequence, not a bare string")
    declared = sorted({normalize_feature(f) for f in (features or ())})
    group = PROVISION_GROUPS[group_id]
    disposition = group["defaults"][ptype]
    driver = "product-type-default"
    for feature in declared:
        if feature in group["features"]:
            if _DISPOSITION_RANK["applicable"] > _DISPOSITION_RANK[disposition]:
                disposition = "applicable"
            driver = feature
            break
    return {
        "group": group_id,
        "title": group["title"],
        "product_type": ptype,
        "disposition": disposition,
        "driver": driver,
    }


def build_pre_tailoring_matrix(products):
    """Build one matrix row set per declared product item.

    products: sequence of mappings with keys "name", "product_type" and an
    optional "features" sequence. Returns a list of cell records ordered by
    item name then provision group.
    """
    if isinstance(products, dict) or not hasattr(products, "__iter__"):
        raise ValueError("products must be a sequence of mappings")
    rows = []
    seen = set()
    for index, item in enumerate(products):
        if not isinstance(item, dict):
            raise ValueError("products[%d] must be a mapping" % index)
        name = item.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("products[%d] needs a non-empty 'name'" % index)
        name = name.strip()
        if name in seen:
            raise ValueError("duplicate product item name %r" % name)
        seen.add(name)
        ptype = normalize_product_type(item.get("product_type"))
        features = item.get("features") or ()
        for group_id in sorted(PROVISION_GROUPS):
            cell = clause_disposition(group_id, ptype, features)
            cell["item"] = name
            rows.append(cell)
    if not rows:
        raise ValueError("products must declare at least one item")
    return sorted(rows, key=lambda r: (r["item"], r["group"]))


def apply_tailoring_request(cell, requested, justification=None,
                            approval_authority=None):
    """Apply one tailoring request to a matrix cell.

    A request that raises the disposition is admitted unconditionally. A
    request that lowers it is admitted only when both a justification text
    and a named approval authority are on record; otherwise the cell keeps
    its derived disposition and the request is recorded as rejected.
    """
    if not isinstance(cell, dict) or "disposition" not in cell:
        raise ValueError("cell must be a matrix record with a 'disposition'")
    target = normalize_disposition(requested)
    current = normalize_disposition(cell["disposition"])
    result = dict(cell)
    result["requested"] = target
    if _DISPOSITION_RANK[target] >= _DISPOSITION_RANK[current]:
        result["disposition"] = target
        result["tailoring"] = "raised" if target != current else "unchanged"
        result["rejected_reason"] = None
        return result
    missing = []
    if not (isinstance(justification, str) and justification.strip()):
        missing.append("justification")
    if not (isinstance(approval_authority, str) and approval_authority.strip()):
        missing.append("approval-authority")
    if missing:
        result["tailoring"] = "rejected"
        result["rejected_reason"] = "downgrade needs " + " and ".join(missing)
        return result
    result["disposition"] = target
    result["tailoring"] = "lowered"
    result["justification"] = justification.strip()
    result["approval_authority"] = approval_authority.strip()
    result["rejected_reason"] = None
    return result


def audit_matrix_completeness(matrix, group_ids=None):
    """List the (item, provision group) pairs the matrix leaves undeclared."""
    if not matrix:
        raise ValueError("matrix must not be empty")
    expected = tuple(sorted(group_ids)) if group_ids else tuple(sorted(PROVISION_GROUPS))
    for group_id in expected:
        if group_id not in PROVISION_GROUPS:
            raise ValueError("unknown provision group %r in audit set" % group_id)
    declared = {}
    for cell in matrix:
        declared.setdefault(cell["item"], set()).add(cell["group"])
    gaps = []
    for item in sorted(declared):
        for group_id in expected:
            if group_id not in declared[item]:
                gaps.append({"item": item, "group": group_id,
                             "finding": "cell-undeclared"})
    return gaps


def summarize_matrix(matrix):
    """Count dispositions and compute the share of cells that bind."""
    if not matrix:
        raise ValueError("matrix must not be empty")
    counts = {d: 0 for d in DISPOSITIONS}
    for cell in matrix:
        counts[normalize_disposition(cell["disposition"])] += 1
    total = len(matrix)
    binding = counts["applicable"] + counts["tailorable"]
    return {
        "cells": total,
        "counts": counts,
        "binding_share": binding / total,
        "applicable_share": counts["applicable"] / total,
    }


def assess_pre_tailoring(products, tailoring_requests=(), min_binding_share=0.0):
    """Run the full clause 8.3 pre-tailoring pass over a product set.

    Returns the tailored matrix, the completeness gaps, the disposition
    summary and a compliant flag. The pass is compliant when no cell is
    undeclared, no tailoring request was rejected, and the share of binding
    cells reaches min_binding_share.
    """
    if not isinstance(min_binding_share, (int, float)) or isinstance(
            min_binding_share, bool):
        raise ValueError("min_binding_share must be a number")
    if not 0.0 <= float(min_binding_share) <= 1.0:
        raise ValueError("min_binding_share must lie in [0, 1]")
    matrix = build_pre_tailoring_matrix(products)
    index = {(c["item"], c["group"]): c for c in matrix}
    findings = []
    for position, request in enumerate(tailoring_requests or ()):
        if not isinstance(request, dict):
            raise ValueError("tailoring_requests[%d] must be a mapping" % position)
        key = (request.get("item"), request.get("group"))
        if key not in index:
            raise ValueError(
                "tailoring request %d targets unknown cell %r" % (position, key)
            )
        updated = apply_tailoring_request(
            index[key],
            request.get("requested"),
            request.get("justification"),
            request.get("approval_authority"),
        )
        index[key] = updated
        if updated.get("tailoring") == "rejected":
            findings.append({
                "item": key[0], "group": key[1],
                "finding": "tailoring-rejected",
                "detail": updated["rejected_reason"],
            })
    tailored = sorted(index.values(), key=lambda r: (r["item"], r["group"]))
    gaps = audit_matrix_completeness(tailored)
    findings.extend(gaps)
    summary = summarize_matrix(tailored)
    share_ok = _meets(summary["binding_share"], float(min_binding_share))
    if not share_ok:
        findings.append({
            "finding": "binding-share-below-floor",
            "detail": "%.6f < %.6f" % (summary["binding_share"],
                                       float(min_binding_share)),
        })
    return {
        "matrix": tailored,
        "summary": summary,
        "findings": findings,
        "compliant": not findings,
    }
