"""Traceability of metallic test pieces to material lot, heat and location.

Anchor: ECSS-Q-ST-70-45C, test-piece clause (each piece is traceable to the
cast or heat, the lot and the position in the product it was taken from).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate one test-piece record: unique identifier, heat, lot, product form,
   orientation and sampling position.
2. Normalise the orientation onto the longitudinal, long-transverse and
   short-transverse axes, refusing anything that maps to none of them.
3. Resolve the through-thickness sampling location and check a declared depth
   against the product thickness.
4. Cross-check the declared heat and lot against the release documentation and
   list the pieces whose material has no paperwork.
5. Grade the set for orientation coverage, through-thickness coverage and
   concentration in a single heat.
"""

import math

__all__ = [
    "ORIENTATIONS",
    "ORIENTATION_ALIASES",
    "THROUGH_THICKNESS_LOCATIONS",
    "MAX_SINGLE_HEAT_FRACTION",
    "REQUIRED_RECORD_KEYS",
    "normalise_orientation",
    "normalise_location",
    "resolve_depth",
    "validate_piece",
    "cross_check_release",
    "duplicate_identifiers",
    "orientation_coverage",
    "location_coverage",
    "heat_concentration",
    "assess_traceability",
]

# The three axes a rolled, forged or extruded product is sampled along.
ORIENTATIONS = ("longitudinal", "long-transverse", "short-transverse")

ORIENTATION_ALIASES = {
    "l": "longitudinal",
    "longitudinal": "longitudinal",
    "rolling-direction": "longitudinal",
    "lt": "long-transverse",
    "t": "long-transverse",
    "long-transverse": "long-transverse",
    "transverse": "long-transverse",
    "st": "short-transverse",
    "s": "short-transverse",
    "short-transverse": "short-transverse",
    "through-thickness": "short-transverse",
}

# Named positions through the section of the product.
THROUGH_THICKNESS_LOCATIONS = ("surface", "quarter-thickness", "mid-thickness")

# A property meant to represent a material cannot come mostly from one melt.
MAX_SINGLE_HEAT_FRACTION = 0.5

REQUIRED_RECORD_KEYS = (
    "piece_id",
    "heat_id",
    "lot_id",
    "product_form",
    "orientation",
    "location",
)


def _token(value, label):
    """Return a stripped, lower-cased non-empty token."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    token = value.strip().lower()
    if not token:
        raise ValueError("%s must not be empty" % label)
    return token


def normalise_orientation(value):
    """Return the canonical sampling orientation for a declared token."""
    token = _token(value, "orientation")
    if token not in ORIENTATION_ALIASES:
        raise ValueError(
            "orientation %r maps to none of %s; record the axis the piece was "
            "cut along rather than guessing" % (token, ", ".join(ORIENTATIONS))
        )
    return ORIENTATION_ALIASES[token]


def normalise_location(value):
    """Return the canonical through-thickness sampling location."""
    token = _token(value, "location")
    aliases = {
        "surface": "surface",
        "skin": "surface",
        "quarter": "quarter-thickness",
        "quarter-thickness": "quarter-thickness",
        "t/4": "quarter-thickness",
        "mid": "mid-thickness",
        "mid-thickness": "mid-thickness",
        "centre": "mid-thickness",
        "center": "mid-thickness",
        "t/2": "mid-thickness",
    }
    if token not in aliases:
        raise ValueError(
            "location %r maps to none of %s"
            % (token, ", ".join(THROUGH_THICKNESS_LOCATIONS))
        )
    return aliases[token]


def resolve_depth(depth_mm, product_thickness_mm):
    """Return the validated sampling depth, checked against the thickness."""
    for label, value in (
        ("depth_mm", depth_mm),
        ("product_thickness_mm", product_thickness_mm),
    ):
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError("%s must be a real number, got %r" % (label, value))
        if not math.isfinite(float(value)):
            raise ValueError("%s must be finite" % label)
    depth = float(depth_mm)
    thickness = float(product_thickness_mm)
    if thickness <= 0.0:
        raise ValueError("product_thickness_mm must be positive, got %g" % thickness)
    if depth < 0.0:
        raise ValueError("depth_mm must not be negative, got %g" % depth)
    if depth > thickness and not math.isclose(
        depth, thickness, rel_tol=0.0, abs_tol=1e-9
    ):
        raise ValueError(
            "depth %g mm lies outside the %g mm product thickness" % (depth, thickness)
        )
    return depth


def validate_piece(record):
    """Return a normalised test-piece record plus its traceability findings."""
    if not isinstance(record, dict):
        raise ValueError("piece record must be a mapping")
    findings = []
    missing = [key for key in REQUIRED_RECORD_KEYS if key not in record]
    if missing:
        findings.append("record omits %s" % ", ".join(sorted(missing)))
    piece_id = record.get("piece_id")
    normalised = {
        "piece_id": piece_id.strip() if isinstance(piece_id, str) else piece_id,
    }
    for key in ("heat_id", "lot_id", "product_form"):
        value = record.get(key)
        if value is None or (isinstance(value, str) and not value.strip()):
            if key not in missing:
                findings.append("%s is blank" % key)
            normalised[key] = None
        else:
            normalised[key] = _token(value, key)
    for key, fn in (
        ("orientation", normalise_orientation),
        ("location", normalise_location),
    ):
        value = record.get(key)
        if value is None or (isinstance(value, str) and not value.strip()):
            if key not in missing:
                findings.append("%s is blank" % key)
            normalised[key] = None
        else:
            normalised[key] = fn(value)
    if "depth_mm" in record:
        thickness = record.get("product_thickness_mm")
        if thickness is None:
            raise ValueError(
                "a declared depth_mm needs product_thickness_mm to be checked against"
            )
        normalised["depth_mm"] = resolve_depth(record["depth_mm"], thickness)
        normalised["product_thickness_mm"] = float(thickness)
    if not isinstance(piece_id, str) or not piece_id.strip():
        if "piece_id" not in missing:
            findings.append("piece_id is blank")
    return {"record": normalised, "traceable": not findings, "findings": findings}


def cross_check_release(pieces, release_records):
    """Return the pieces whose declared heat or lot has no release record."""
    if not isinstance(release_records, (list, tuple)):
        raise ValueError("release_records must be a sequence of mappings")
    heats = set()
    lots = set()
    for index, entry in enumerate(release_records):
        if not isinstance(entry, dict):
            raise ValueError("release_records[%d] must be a mapping" % index)
        if "heat_id" not in entry:
            raise ValueError("release_records[%d] omits heat_id" % index)
        heats.add(_token(entry["heat_id"], "release heat_id"))
        if entry.get("lot_id") is not None:
            lots.add(_token(entry["lot_id"], "release lot_id"))
    orphans = []
    for piece in pieces:
        normalised = validate_piece(piece)["record"]
        heat = normalised.get("heat_id")
        lot = normalised.get("lot_id")
        reasons = []
        if heat is None or heat not in heats:
            reasons.append("heat %r is not on the release documentation" % heat)
        if lots and (lot is None or lot not in lots):
            reasons.append("lot %r is not on the release documentation" % lot)
        if reasons:
            orphans.append({"piece_id": normalised.get("piece_id"), "reasons": reasons})
    return orphans


def duplicate_identifiers(pieces):
    """Return the piece identifiers that appear more than once."""
    if not isinstance(pieces, (list, tuple)):
        raise ValueError("pieces must be a sequence of records")
    seen = {}
    for piece in pieces:
        if not isinstance(piece, dict):
            raise ValueError("each piece must be a mapping")
        identifier = piece.get("piece_id")
        if not isinstance(identifier, str) or not identifier.strip():
            continue
        key = identifier.strip().lower()
        seen[key] = seen.get(key, 0) + 1
    return sorted(key for key, count in seen.items() if count > 1)


def orientation_coverage(pieces, required):
    """Return the required orientations that the sampled set does not cover."""
    if not isinstance(required, (list, tuple)) or not required:
        raise ValueError("required orientations must be a non-empty sequence")
    wanted = {normalise_orientation(item) for item in required}
    sampled = set()
    for piece in pieces:
        value = piece.get("orientation") if isinstance(piece, dict) else None
        if isinstance(value, str) and value.strip():
            sampled.add(normalise_orientation(value))
    return {
        "required": sorted(wanted),
        "sampled": sorted(sampled),
        "missing": sorted(wanted - sampled),
    }


def location_coverage(pieces, required=None):
    """Return the through-thickness locations sampled and those still missing."""
    wanted = set()
    if required:
        wanted = {normalise_location(item) for item in required}
    sampled = set()
    for piece in pieces:
        value = piece.get("location") if isinstance(piece, dict) else None
        if isinstance(value, str) and value.strip():
            sampled.add(normalise_location(value))
    return {
        "required": sorted(wanted),
        "sampled": sorted(sampled),
        "missing": sorted(wanted - sampled),
    }


def heat_concentration(pieces):
    """Return the share of the set that came from the single most-used heat."""
    counts = {}
    total = 0
    for piece in pieces:
        value = piece.get("heat_id") if isinstance(piece, dict) else None
        if not isinstance(value, str) or not value.strip():
            continue
        key = value.strip().lower()
        counts[key] = counts.get(key, 0) + 1
        total += 1
    if total == 0:
        return {"heats": {}, "dominant_heat": None, "fraction": None, "total": 0}
    dominant = max(sorted(counts), key=lambda k: counts[k])
    return {
        "heats": counts,
        "dominant_heat": dominant,
        "fraction": counts[dominant] / total,
        "total": total,
    }


def assess_traceability(pieces, release_records=None, required_orientations=None,
                        required_locations=None,
                        max_single_heat_fraction=MAX_SINGLE_HEAT_FRACTION):
    """Grade a set of test pieces for per-piece traceability and set coverage."""
    if not isinstance(pieces, (list, tuple)) or not pieces:
        raise ValueError("pieces must be a non-empty sequence of records")
    if not isinstance(max_single_heat_fraction, (int, float)) or isinstance(
        max_single_heat_fraction, bool
    ):
        raise ValueError("max_single_heat_fraction must be a real number")
    limit = float(max_single_heat_fraction)
    if not (0.0 < limit <= 1.0):
        raise ValueError(
            "max_single_heat_fraction must lie in (0, 1], got %g" % limit
        )

    per_piece = []
    findings = []
    for piece in pieces:
        result = validate_piece(piece)
        per_piece.append(result)
        if not result["traceable"]:
            findings.append(
                "piece %r is not individually traceable: %s"
                % (result["record"].get("piece_id"), "; ".join(result["findings"]))
            )

    duplicates = duplicate_identifiers(pieces)
    if duplicates:
        findings.append(
            "duplicate piece identifier(s) %s make two results indistinguishable"
            % ", ".join(duplicates)
        )

    orphans = []
    if release_records is not None:
        orphans = cross_check_release(pieces, release_records)
        for orphan in orphans:
            findings.append(
                "piece %r is orphaned: %s"
                % (orphan["piece_id"], "; ".join(orphan["reasons"]))
            )

    orientations = None
    if required_orientations:
        orientations = orientation_coverage(pieces, required_orientations)
        if orientations["missing"]:
            findings.append(
                "orientation(s) %s were never sampled" % ", ".join(orientations["missing"])
            )

    locations = location_coverage(pieces, required_locations)
    if locations["missing"]:
        findings.append(
            "through-thickness location(s) %s were never sampled"
            % ", ".join(locations["missing"])
        )

    concentration = heat_concentration(pieces)
    if concentration["fraction"] is not None:
        over = concentration["fraction"] > limit and not math.isclose(
            concentration["fraction"], limit, rel_tol=0.0, abs_tol=1e-12
        )
        if over:
            findings.append(
                "%.0f %% of the set comes from heat %r, above the %.0f %% a "
                "material property may draw from one melt"
                % (100.0 * concentration["fraction"], concentration["dominant_heat"],
                   100.0 * limit)
            )

    every_piece_traceable = all(item["traceable"] for item in per_piece) and not orphans
    return {
        "pieces": per_piece,
        "duplicates": duplicates,
        "orphans": orphans,
        "orientation_coverage": orientations,
        "location_coverage": locations,
        "heat_concentration": concentration,
        "every_piece_traceable": every_piece_traceable,
        "set_acceptable": not findings,
        "status": "traceable" if not findings else "traceability-finding",
        "findings": findings,
    }
