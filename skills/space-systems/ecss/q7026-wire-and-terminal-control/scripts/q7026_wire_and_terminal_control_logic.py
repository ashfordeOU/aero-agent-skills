"""Control of wire and terminal combinations and of strip length.

Anchor: ECSS-Q-ST-70-26C, the materials clause of the crimping practice
that binds a conductor to a qualified terminal and fixes the length the
insulation is cut back to (paraphrased into an implementable procedure;
no standard text is reproduced).

Procedure implemented here:

1. A terminal and a conductor are a combination, not two independent
   choices. The qualified list is keyed on the terminal part number and
   carries the conductor cross-section range that terminal was
   qualified with. A terminal not on the list has no range at all, and
   a conductor outside the range is a different failure from a terminal
   nobody qualified: they go to different people.
2. The strip length is derived, never guessed. It is the barrel length
   plus the gap the insulation has to stand off the barrel mouth, held
   inside a tolerance. Cutting to a remembered number is how one
   terminal's window gets applied to another terminal's barrel.
3. Short and long fail differently. A short strip leaves the barrel
   part empty, so the crimp grips insulation instead of metal. A long
   strip leaves bare conductor outside the barrel, which is a clearance
   problem and not a grip problem, and the two are reworked
   differently.
4. Exposed conductor is measured from the barrel, not from the window.
   A strip inside its tolerance can still leave more bare metal than
   the installation allows when the barrel is short.
5. Every strand goes in the barrel. A strand combed outside — the
   brush — is not a fraction of a good crimp; it is a loose conductor
   next to a terminal, and the count is the only way to see it.

Stdlib only, offline, deterministic.
"""

TOLERANCE = 1.0e-9

# How far a cut strip may sit either side of its derived nominal.
STRIP_TOLERANCE_MM = 0.4

# Bare conductor permitted between the insulation and the barrel mouth.
MAX_EXPOSED_CONDUCTOR_MM = 1.0

QUALIFIED = "combination-qualified"
TERMINAL_NOT_LISTED = "terminal-not-on-the-qualified-list"
CONDUCTOR_OUT_OF_RANGE = "conductor-outside-the-qualified-barrel-range"

STRIP_SHORT = "strip-short-barrel-not-filled"
STRIP_IN_WINDOW = "strip-in-window"
STRIP_LONG = "strip-long-conductor-exposed"

BRUSH_FINDING = "conductor-strand-outside-the-barrel"
EXPOSED_FINDING = "bare-conductor-beyond-the-installation-limit"


def _text(label, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string" % label)
    return " ".join(value.split())


def _numeric(label, value, minimum=None):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be numeric, got %r" % (label, value))
    if minimum is not None and value < minimum:
        raise ValueError("%s must be >= %r, got %r" % (label, minimum, value))
    return float(value)


def _count(label, value, minimum=0):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value < minimum:
        raise ValueError("%s must be >= %d, got %d" % (label, minimum, value))
    return value


def validate_qualified_entry(entry):
    """Validate one row of the qualified wire and terminal list."""
    if not isinstance(entry, dict):
        raise ValueError("qualified entry must be a mapping")
    low = _numeric("conductor_csa_min_mm2", entry.get("conductor_csa_min_mm2"), 0.0)
    high = _numeric("conductor_csa_max_mm2", entry.get("conductor_csa_max_mm2"), 0.0)
    if low <= 0.0:
        raise ValueError("conductor_csa_min_mm2 must be greater than zero")
    if high < low:
        raise ValueError("conductor_csa_max_mm2 must not be below the minimum")
    barrel = _numeric("barrel_length_mm", entry.get("barrel_length_mm"), 0.0)
    if barrel <= 0.0:
        raise ValueError("barrel_length_mm must be greater than zero")
    return {
        "terminal_part_number": _text(
            "terminal_part_number", entry.get("terminal_part_number")
        ).upper(),
        "conductor_csa_min_mm2": low,
        "conductor_csa_max_mm2": high,
        "barrel_length_mm": barrel,
        "insulation_support_gap_mm": _numeric(
            "insulation_support_gap_mm", entry.get("insulation_support_gap_mm"), 0.0
        ),
    }


def build_qualified_list(entries):
    """Index the qualified list by terminal part number."""
    if not isinstance(entries, list) or not entries:
        raise ValueError("entries must be a non-empty list")
    index = {}
    for entry in entries:
        checked = validate_qualified_entry(entry)
        key = checked["terminal_part_number"]
        if key in index:
            raise ValueError("terminal %s is listed twice" % key)
        index[key] = checked
    return index


def validate_item(item):
    """Validate one wire and terminal pairing from a build sheet."""
    if not isinstance(item, dict):
        raise ValueError("item must be a mapping")
    strands = _count("strand_count", item.get("strand_count", 1), 1)
    in_barrel = _count("strands_in_barrel", item.get("strands_in_barrel", strands), 0)
    if in_barrel > strands:
        raise ValueError("strands_in_barrel cannot exceed strand_count")
    csa = _numeric("conductor_csa_mm2", item.get("conductor_csa_mm2"), 0.0)
    if csa <= 0.0:
        raise ValueError("conductor_csa_mm2 must be greater than zero")
    return {
        "item_id": _text("item_id", item.get("item_id")),
        "terminal_part_number": _text(
            "terminal_part_number", item.get("terminal_part_number")
        ).upper(),
        "conductor_csa_mm2": csa,
        "measured_strip_length_mm": _numeric(
            "measured_strip_length_mm", item.get("measured_strip_length_mm"), 0.0
        ),
        "strand_count": strands,
        "strands_in_barrel": in_barrel,
    }


def combination_verdict(qualified, item):
    """Is this conductor qualified with this terminal?"""
    checked = validate_item(item)
    entry = qualified.get(checked["terminal_part_number"])
    if entry is None:
        return {"verdict": TERMINAL_NOT_LISTED, "entry": None}
    csa = checked["conductor_csa_mm2"]
    if csa < entry["conductor_csa_min_mm2"] - TOLERANCE:
        return {"verdict": CONDUCTOR_OUT_OF_RANGE, "entry": entry}
    if csa > entry["conductor_csa_max_mm2"] + TOLERANCE:
        return {"verdict": CONDUCTOR_OUT_OF_RANGE, "entry": entry}
    return {"verdict": QUALIFIED, "entry": entry}


def strip_length_window(barrel_length_mm, insulation_support_gap_mm,
                        tolerance_mm=STRIP_TOLERANCE_MM):
    """Derive the strip length window from the barrel and the stand-off."""
    barrel = _numeric("barrel_length_mm", barrel_length_mm, 0.0)
    if barrel <= 0.0:
        raise ValueError("barrel_length_mm must be greater than zero")
    gap = _numeric("insulation_support_gap_mm", insulation_support_gap_mm, 0.0)
    tol = _numeric("tolerance_mm", tolerance_mm, 0.0)
    if tol <= 0.0:
        raise ValueError("tolerance_mm must be greater than zero")
    nominal = barrel + gap
    return {
        "nominal_mm": nominal,
        "minimum_mm": nominal - tol,
        "maximum_mm": nominal + tol,
    }


def assess_strip(measured_strip_length_mm, window):
    """Categorize a measured strip against its derived window."""
    measured = _numeric(
        "measured_strip_length_mm", measured_strip_length_mm, 0.0
    )
    if not isinstance(window, dict):
        raise ValueError("window must be a mapping from strip_length_window")
    if measured < window["minimum_mm"] - TOLERANCE:
        return STRIP_SHORT
    if measured > window["maximum_mm"] + TOLERANCE:
        return STRIP_LONG
    return STRIP_IN_WINDOW


def exposed_conductor(measured_strip_length_mm, barrel_length_mm):
    """Bare conductor left between the insulation and the barrel mouth."""
    measured = _numeric(
        "measured_strip_length_mm", measured_strip_length_mm, 0.0
    )
    barrel = _numeric("barrel_length_mm", barrel_length_mm, 0.0)
    return max(0.0, measured - barrel)


def brush_free(item):
    """Every strand inside the barrel."""
    checked = validate_item(item)
    return checked["strands_in_barrel"] == checked["strand_count"]


def assess_item(qualified, item):
    """Qualification, strip window and strand containment for one pairing."""
    checked = validate_item(item)
    combination = combination_verdict(qualified, item)
    findings = []
    result = {
        "item_id": checked["item_id"],
        "terminal_part_number": checked["terminal_part_number"],
        "combination_verdict": combination["verdict"],
        "strip_verdict": None,
        "window": None,
        "exposed_conductor_mm": None,
        "findings": findings,
        "acceptable": False,
    }
    if combination["verdict"] != QUALIFIED:
        findings.append(combination["verdict"])
        return result

    entry = combination["entry"]
    window = strip_length_window(
        entry["barrel_length_mm"], entry["insulation_support_gap_mm"]
    )
    verdict = assess_strip(checked["measured_strip_length_mm"], window)
    exposed = exposed_conductor(
        checked["measured_strip_length_mm"], entry["barrel_length_mm"]
    )
    result["window"] = window
    result["strip_verdict"] = verdict
    result["exposed_conductor_mm"] = exposed

    if verdict != STRIP_IN_WINDOW:
        findings.append(verdict)
    if exposed > MAX_EXPOSED_CONDUCTOR_MM + TOLERANCE:
        findings.append(EXPOSED_FINDING)
    if not brush_free(item):
        findings.append(BRUSH_FINDING)

    result["acceptable"] = not findings
    return result


def assess_lot(qualified_entries, items):
    """Apply the qualified list and the strip window across a build lot."""
    qualified = build_qualified_list(qualified_entries)
    if not isinstance(items, list) or not items:
        raise ValueError("items must be a non-empty list")
    results = [assess_item(qualified, item) for item in items]
    findings = []
    for result in results:
        for finding in result["findings"]:
            findings.append("%s: %s" % (result["item_id"], finding))
    return {
        "results": results,
        "accepted": [r["item_id"] for r in results if r["acceptable"]],
        "rejected": [r["item_id"] for r in results if not r["acceptable"]],
        "findings": findings,
        "clean": not findings,
    }
