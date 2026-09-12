"""
Lightning-protection verification logic — ECSS-E-ST-32C clause 4.6.3.25.

Implements deterministic, offline engineering checks for:
  - Strike-zone assignment (Zone A / B / C)
  - Bond-resistance verification by bond class
  - Lightning-current-path continuity
  - Shielding coverage on Zone A / B surfaces
  - Bonding strap and fastener inspection record completeness
"""

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Valid strike zones and their descriptions (no verbatim ECSS text)
STRIKE_ZONES = {
    "A": "direct lightning attachment (first / last attachment point)",
    "B": "swept stroke (channel sweeps along surface during flight)",
    "C": "protected interior or transition region (no direct channel contact)",
}

# Bond classes and their maximum allowable resistance in milliohms
BOND_RESISTANCE_LIMITS_MOHM = {
    "primary": 2.5,    # main lightning-current path through outer structure
    "secondary": 10.0, # sub-structure connections
    "equipment": 25.0, # equipment enclosures bonded to structure
}

# Zones requiring shielding disposition
SHIELDED_ZONES = {"A", "B"}


# ---------------------------------------------------------------------------
# Strike-zone assignment
# ---------------------------------------------------------------------------

def categorize_strike_zone(zone_id: str) -> dict:
    """
    Return the zone category record for *zone_id*.

    Returns a dict with keys:
      zone       — the canonical zone identifier ("A", "B", or "C")
      description — human-readable category description
      error      — None on success, error string on failure
    """
    if not isinstance(zone_id, str):
        return {"zone": None, "description": None,
                "error": f"zone_id must be a string, got {type(zone_id).__name__}"}
    normalized = zone_id.strip().upper()
    if normalized not in STRIKE_ZONES:
        return {
            "zone": None,
            "description": None,
            "error": (
                f"Unrecognized strike zone '{zone_id}'. "
                f"Valid values: {sorted(STRIKE_ZONES.keys())}."
            ),
        }
    return {
        "zone": normalized,
        "description": STRIKE_ZONES[normalized],
        "error": None,
    }


# ---------------------------------------------------------------------------
# Bond-resistance check
# ---------------------------------------------------------------------------

def check_bond_resistance(measured_mohm: float, bond_class: str) -> dict:
    """
    Verify a single bond joint against its class resistance limit.

    Args:
        measured_mohm: Measured resistance in milliohms (must be >= 0).
        bond_class:    One of "primary", "secondary", "equipment".

    Returns a dict with keys:
      bond_class    — normalized class name
      limit_mohm    — allowable limit for the class
      measured_mohm — the supplied measurement
      margin_mohm   — limit − measured (positive = headroom, negative = exceedance)
      status        — "PASS" or "FAIL"
      error         — None on success, error string on failure
    """
    if not isinstance(bond_class, str):
        return {"bond_class": bond_class, "limit_mohm": None, "measured_mohm": measured_mohm,
                "margin_mohm": None, "status": "FAIL",
                "error": f"bond_class must be a string, got {type(bond_class).__name__}"}
    normalized_class = bond_class.strip().lower()
    if normalized_class not in BOND_RESISTANCE_LIMITS_MOHM:
        return {
            "bond_class": bond_class,
            "limit_mohm": None,
            "measured_mohm": measured_mohm,
            "margin_mohm": None,
            "status": "FAIL",
            "error": (
                f"Unrecognized bond class '{bond_class}'. "
                f"Valid values: {sorted(BOND_RESISTANCE_LIMITS_MOHM.keys())}."
            ),
        }
    if not isinstance(measured_mohm, (int, float)) or measured_mohm < 0:
        return {
            "bond_class": normalized_class,
            "limit_mohm": BOND_RESISTANCE_LIMITS_MOHM[normalized_class],
            "measured_mohm": measured_mohm,
            "margin_mohm": None,
            "status": "FAIL",
            "error": f"measured_mohm must be a non-negative number, got {measured_mohm!r}",
        }
    limit = BOND_RESISTANCE_LIMITS_MOHM[normalized_class]
    margin = limit - measured_mohm
    return {
        "bond_class": normalized_class,
        "limit_mohm": limit,
        "measured_mohm": measured_mohm,
        "margin_mohm": round(margin, 6),
        "status": "PASS" if margin >= 0 else "FAIL",
        "error": None,
    }


# ---------------------------------------------------------------------------
# Current-path continuity
# ---------------------------------------------------------------------------

def check_current_path_continuity(path_segments: list) -> dict:
    """
    Verify lightning-current-path continuity across a list of bond segments.

    Each element of *path_segments* must be a dict produced by
    check_bond_resistance (or a compatible record with at least the keys
    "status" and "error").

    Returns a dict with keys:
      total_segments — number of segments evaluated
      failing        — list of (index, record) pairs for failed or errored segments
      status         — "PASS" if all segments pass, "FAIL" otherwise
      error          — None on success, description of input error on failure
    """
    if not isinstance(path_segments, list):
        return {
            "total_segments": None,
            "failing": [],
            "status": "FAIL",
            "error": f"path_segments must be a list, got {type(path_segments).__name__}",
        }
    if len(path_segments) == 0:
        return {
            "total_segments": 0,
            "failing": [],
            "status": "FAIL",
            "error": "path_segments is empty; at least one segment is required.",
        }
    failing = []
    for idx, seg in enumerate(path_segments):
        if not isinstance(seg, dict):
            failing.append((idx, {"error": f"segment {idx} is not a dict"}))
            continue
        seg_status = seg.get("status")
        seg_error = seg.get("error")
        if seg_error is not None or seg_status != "PASS":
            failing.append((idx, seg))
    return {
        "total_segments": len(path_segments),
        "failing": failing,
        "status": "PASS" if len(failing) == 0 else "FAIL",
        "error": None,
    }


# ---------------------------------------------------------------------------
# Shielding coverage
# ---------------------------------------------------------------------------

def check_shielding_coverage(surface_records: list) -> dict:
    """
    Verify that every Zone A and Zone B surface has a shielding disposition.

    Each element of *surface_records* must be a dict with:
      id          — surface identifier string
      zone        — "A", "B", or "C"
      disposition — "shielded", "non-critical", or None / missing key

    Returns a dict with keys:
      total_surfaces      — number of records evaluated
      unresolved_surfaces — list of surface ids with missing disposition
      status              — "PASS" if no Zone A/B surface lacks a disposition
      error               — None on success, error string on input failure
    """
    if not isinstance(surface_records, list):
        return {
            "total_surfaces": None,
            "unresolved_surfaces": [],
            "status": "FAIL",
            "error": f"surface_records must be a list, got {type(surface_records).__name__}",
        }
    unresolved = []
    for rec in surface_records:
        if not isinstance(rec, dict):
            unresolved.append({"id": "<invalid record>", "error": "record is not a dict"})
            continue
        zone = (rec.get("zone") or "").strip().upper()
        if zone not in SHIELDED_ZONES:
            continue  # Zone C and unknown zones are not checked here
        disposition = rec.get("disposition")
        if disposition not in ("shielded", "non-critical"):
            unresolved.append({
                "id": rec.get("id", "<no id>"),
                "zone": zone,
                "disposition": disposition,
            })
    return {
        "total_surfaces": len(surface_records),
        "unresolved_surfaces": unresolved,
        "status": "PASS" if len(unresolved) == 0 else "FAIL",
        "error": None,
    }


# ---------------------------------------------------------------------------
# Inspection record completeness
# ---------------------------------------------------------------------------

def check_inspection_records(strap_records: list) -> dict:
    """
    Verify that every bonding strap and fastener has a complete inspection record.

    Each element of *strap_records* must be a dict with:
      id        — strap/fastener identifier string
      inspected — True if inspection record exists and is marked complete

    Returns a dict with keys:
      total_items         — number of items evaluated
      uninspected_items   — list of ids with missing or incomplete records
      status              — "PASS" if all items are inspected
      error               — None on success, error string on input failure
    """
    if not isinstance(strap_records, list):
        return {
            "total_items": None,
            "uninspected_items": [],
            "status": "FAIL",
            "error": f"strap_records must be a list, got {type(strap_records).__name__}",
        }
    if len(strap_records) == 0:
        return {
            "total_items": 0,
            "uninspected_items": [],
            "status": "FAIL",
            "error": "strap_records is empty; at least one item is required.",
        }
    uninspected = []
    for rec in strap_records:
        if not isinstance(rec, dict):
            uninspected.append("<invalid record>")
            continue
        if not rec.get("inspected"):
            uninspected.append(rec.get("id", "<no id>"))
    return {
        "total_items": len(strap_records),
        "uninspected_items": uninspected,
        "status": "PASS" if len(uninspected) == 0 else "FAIL",
        "error": None,
    }


# ---------------------------------------------------------------------------
# Aggregate compliance
# ---------------------------------------------------------------------------

def aggregate_compliance(
    bond_results: list,
    path_result: dict,
    shielding_result: dict,
    inspection_result: dict,
) -> dict:
    """
    Aggregate all sub-check results into a single compliance verdict.

    Args:
        bond_results:       List of dicts from check_bond_resistance.
        path_result:        Dict from check_current_path_continuity.
        shielding_result:   Dict from check_shielding_coverage.
        inspection_result:  Dict from check_inspection_records.

    Returns a dict with keys:
      bond_status       — "PASS" / "FAIL" / "ERROR"
      path_status       — "PASS" / "FAIL" / "ERROR"
      shielding_status  — "PASS" / "FAIL" / "ERROR"
      inspection_status — "PASS" / "FAIL" / "ERROR"
      overall_status    — "PASS" only when all four are "PASS", else "FAIL"
      findings          — list of human-readable finding strings
    """
    findings = []

    # Bond results aggregate
    bond_status = "PASS"
    if not isinstance(bond_results, list) or len(bond_results) == 0:
        bond_status = "ERROR"
        findings.append("Bond results list is empty or invalid.")
    else:
        for r in bond_results:
            if not isinstance(r, dict):
                bond_status = "ERROR"
                findings.append("A bond result record is not a dict.")
                break
            if r.get("error"):
                bond_status = "FAIL"
                findings.append(f"Bond check error: {r['error']}")
            elif r.get("status") != "PASS":
                bond_status = "FAIL"
                findings.append(
                    f"Bond FAIL — class '{r.get('bond_class')}' "
                    f"measured {r.get('measured_mohm')} mΩ "
                    f"(limit {r.get('limit_mohm')} mΩ, "
                    f"margin {r.get('margin_mohm')} mΩ)."
                )

    # Path continuity
    path_status = path_result.get("status", "ERROR") if isinstance(path_result, dict) else "ERROR"
    if path_status != "PASS":
        failing = path_result.get("failing", []) if isinstance(path_result, dict) else []
        findings.append(
            f"Current path FAIL — {len(failing)} segment(s) failed continuity check."
        )

    # Shielding coverage
    shielding_status = shielding_result.get("status", "ERROR") if isinstance(shielding_result, dict) else "ERROR"
    if shielding_status != "PASS":
        unresolved = shielding_result.get("unresolved_surfaces", []) if isinstance(shielding_result, dict) else []
        findings.append(
            f"Shielding FAIL — {len(unresolved)} surface(s) in Zone A/B lack disposition."
        )

    # Inspection completeness
    inspection_status = inspection_result.get("status", "ERROR") if isinstance(inspection_result, dict) else "ERROR"
    if inspection_status != "PASS":
        uninspected = inspection_result.get("uninspected_items", []) if isinstance(inspection_result, dict) else []
        findings.append(
            f"Inspection FAIL — {len(uninspected)} strap/fastener item(s) not inspected."
        )

    overall = (
        "PASS"
        if bond_status == "PASS"
        and path_status == "PASS"
        and shielding_status == "PASS"
        and inspection_status == "PASS"
        else "FAIL"
    )

    return {
        "bond_status": bond_status,
        "path_status": path_status,
        "shielding_status": shielding_status,
        "inspection_status": inspection_status,
        "overall_status": overall,
        "findings": findings,
    }
