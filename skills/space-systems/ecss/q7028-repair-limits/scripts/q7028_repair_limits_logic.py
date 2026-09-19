"""How much repair one board is allowed to carry, and where.

Anchor: ECSS-Q-ST-70-28C, limits clause -- the ceilings on repair and
modification of a printed circuit board assembly: how many repairs one board
may carry, how densely they may sit, how many one conductor may take, and how
close two repair sites may be to each other before the laminate between them
stops being undisturbed material. Paraphrased into an implementable procedure;
no standard text is reproduced.

Procedure implemented here
--------------------------
1. Read the allowance the board's assurance level carries, for the count of
   repairs and for their density over the board area.
2. Combine the repairs already on the board with the ones being proposed, and
   refuse a proposal that reuses an existing site identity.
3. Count the whole population against the per-board allowance, and compute
   the density against the allowance per unit area.
4. Count repairs per conductor, because a conductor repaired twice is a
   conductor that is now mostly repair.
5. Measure the in-plane separation of every pair of sites and compare it with
   the minimum that pair requires: two sites on one face interact through the
   surface, two sites on opposite faces interact only through the laminate and
   so take a shorter minimum.
6. Return the disposition with the counts, the closest pair, the governing
   limit and every finding, and say whether the proposal is what broke it.
"""

import math

__all__ = [
    "MAX_REPAIRS_PER_BOARD",
    "MAX_REPAIR_DENSITY_PER_100_CM2",
    "MAX_REPAIRS_PER_CONDUCTOR",
    "MIN_SEPARATION_SAME_SIDE_MM",
    "MIN_SEPARATION_OPPOSITE_SIDES_MM",
    "BOARD_SIDES",
    "DEFAULT_ASSURANCE_LEVEL",
    "TOLERANCE",
    "repair_allowance",
    "density_allowance",
    "normalise_sites",
    "separation_mm",
    "minimum_separation_mm",
    "proximity_violations",
    "conductor_violations",
    "repair_density_per_100_cm2",
    "assess_repair_limits",
]

# Repairs one board may carry, by assurance level. A board past its allowance
# is a board whose qualification rests mostly on rework.
MAX_REPAIRS_PER_BOARD = {1: 3, 2: 5, 3: 8}

# Repairs per 100 square centimetres of board. The count alone would let a
# small board carry the same population as a large one.
MAX_REPAIR_DENSITY_PER_100_CM2 = {1: 1.0, 2: 2.0, 3: 3.0}

# One conductor takes one repair. A second repair on the same conductor leaves
# a run that is more joint than conductor.
MAX_REPAIRS_PER_CONDUCTOR = 1

# Two sites on the same face interact across the surface; two on opposite
# faces interact only through the laminate, so they may sit closer in plan.
MIN_SEPARATION_SAME_SIDE_MM = 10.0
MIN_SEPARATION_OPPOSITE_SIDES_MM = 5.0

BOARD_SIDES = ("top", "bottom")
DEFAULT_ASSURANCE_LEVEL = 2

# Positions and areas are measured quantities; a separation sitting exactly on
# its minimum is acceptable, and this absorbs representation error only.
TOLERANCE = 1e-9


def _require_mapping(value, label):
    if not isinstance(value, dict):
        raise ValueError("%s must be a mapping" % label)
    return value


def _real(value, label):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    return number


def _positive(value, label):
    number = _real(value, label)
    if number <= 0.0:
        raise ValueError("%s must be positive, got %g" % (label, number))
    return number


def _token(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string" % label)
    return value.strip().lower()


def _level(value):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("assurance level must be an integer, got %r" % (value,))
    if value not in MAX_REPAIRS_PER_BOARD:
        raise ValueError(
            "unknown assurance level %d; known: %s"
            % (value, ", ".join(str(k) for k in sorted(MAX_REPAIRS_PER_BOARD)))
        )
    return value


def repair_allowance(level=DEFAULT_ASSURANCE_LEVEL):
    """Return how many repairs one board may carry at an assurance level."""
    return MAX_REPAIRS_PER_BOARD[_level(level)]


def density_allowance(level=DEFAULT_ASSURANCE_LEVEL):
    """Return the repairs per 100 cm2 allowed at an assurance level."""
    return MAX_REPAIR_DENSITY_PER_100_CM2[_level(level)]


def normalise_sites(sites, status="existing"):
    """Validate a sequence of repair sites and return them normalised."""
    if isinstance(sites, dict) or not isinstance(sites, (list, tuple)):
        raise ValueError("sites must be a sequence of repair-site mappings")
    state = _token(status, "status")
    out = []
    for index, raw in enumerate(sites):
        _require_mapping(raw, "repair site %d" % index)
        for key in ("id", "side", "x_mm", "y_mm"):
            if key not in raw:
                raise ValueError("repair site %d missing required key '%s'" % (index, key))
        side = _token(raw["side"], "repair site side")
        if side not in BOARD_SIDES:
            raise ValueError(
                "repair site '%s' is on side '%s'; sides are %s"
                % (raw["id"], side, ", ".join(BOARD_SIDES))
            )
        out.append(
            {
                "id": _token(raw["id"], "repair site id"),
                "side": side,
                "x_mm": _real(raw["x_mm"], "repair site x_mm"),
                "y_mm": _real(raw["y_mm"], "repair site y_mm"),
                "conductor": (
                    _token(raw["conductor"], "conductor") if raw.get("conductor") else None
                ),
                "status": state,
            }
        )
    return out


def separation_mm(site_a, site_b):
    """Return the in-plane distance between two repair sites in millimetres."""
    _require_mapping(site_a, "site_a")
    _require_mapping(site_b, "site_b")
    return math.hypot(
        _real(site_a["x_mm"], "site_a x_mm") - _real(site_b["x_mm"], "site_b x_mm"),
        _real(site_a["y_mm"], "site_a y_mm") - _real(site_b["y_mm"], "site_b y_mm"),
    )


def minimum_separation_mm(site_a, site_b):
    """Return the minimum separation the pair requires, by their sides."""
    side_a = _token(site_a["side"], "site_a side")
    side_b = _token(site_b["side"], "site_b side")
    for side in (side_a, side_b):
        if side not in BOARD_SIDES:
            raise ValueError("unknown board side '%s'" % side)
    if side_a == side_b:
        return MIN_SEPARATION_SAME_SIDE_MM
    return MIN_SEPARATION_OPPOSITE_SIDES_MM


def proximity_violations(sites):
    """Return every pair of sites closer than the minimum that pair requires."""
    violations = []
    for i in range(len(sites)):
        for j in range(i + 1, len(sites)):
            first, second = sites[i], sites[j]
            distance = separation_mm(first, second)
            minimum = minimum_separation_mm(first, second)
            if distance < minimum - TOLERANCE:
                violations.append(
                    {
                        "sites": (first["id"], second["id"]),
                        "separation_mm": distance,
                        "minimum_mm": minimum,
                        "same_side": first["side"] == second["side"],
                    }
                )
    return violations


def conductor_violations(sites):
    """Return every conductor carrying more repairs than it is allowed."""
    counts = {}
    for site in sites:
        conductor = site.get("conductor")
        if conductor is None:
            continue
        counts.setdefault(conductor, []).append(site["id"])
    return [
        {"conductor": conductor, "sites": tuple(ids), "count": len(ids)}
        for conductor, ids in sorted(counts.items())
        if len(ids) > MAX_REPAIRS_PER_CONDUCTOR
    ]


def repair_density_per_100_cm2(count, board_area_cm2):
    """Return the repair density of a board in repairs per 100 cm2."""
    if not isinstance(count, int) or isinstance(count, bool) or count < 0:
        raise ValueError("count must be a non-negative integer, got %r" % (count,))
    area = _positive(board_area_cm2, "board_area_cm2")
    return count * 100.0 / area


def assess_repair_limits(board):
    """Decide whether a board stays inside its repair limits.

    board keys: board_area_cm2, and optionally assurance_level,
    existing_repairs and proposed_repairs. Each repair site carries id, side,
    x_mm, y_mm and optionally conductor.
    """
    _require_mapping(board, "board")
    if "board_area_cm2" not in board:
        raise ValueError("board missing required key 'board_area_cm2'")
    area = _positive(board["board_area_cm2"], "board_area_cm2")
    level = _level(board.get("assurance_level", DEFAULT_ASSURANCE_LEVEL))

    existing = normalise_sites(board.get("existing_repairs", ()), "existing")
    proposed = normalise_sites(board.get("proposed_repairs", ()), "proposed")
    sites = existing + proposed

    seen = {}
    for site in sites:
        if site["id"] in seen:
            raise ValueError("repair site id '%s' is used twice" % site["id"])
        seen[site["id"]] = site

    count = len(sites)
    allowance = repair_allowance(level)
    density = repair_density_per_100_cm2(count, area)
    density_limit = density_allowance(level)

    findings = []
    utilisations = {}

    utilisations["repairs-per-board"] = count / float(allowance)
    if count > allowance:
        findings.append(
            "%d repairs on the board exceed the allowance of %d at assurance level %d"
            % (count, allowance, level)
        )

    utilisations["repair-density"] = density / density_limit
    if density > density_limit + TOLERANCE:
        findings.append(
            "repair density of %.3f per 100 cm2 over %g cm2 exceeds the %.3f per "
            "100 cm2 allowed at assurance level %d"
            % (density, area, density_limit, level)
        )

    conductors = conductor_violations(sites)
    for entry in conductors:
        findings.append(
            "conductor '%s' carries %d repairs (%s); %d is the allowance"
            % (
                entry["conductor"],
                entry["count"],
                ", ".join(entry["sites"]),
                MAX_REPAIRS_PER_CONDUCTOR,
            )
        )

    close_pairs = proximity_violations(sites)
    for entry in close_pairs:
        where = "on the same face" if entry["same_side"] else "on opposite faces"
        findings.append(
            "repair sites %s and %s sit %.3f mm apart %s; %g mm is the minimum"
            % (
                entry["sites"][0],
                entry["sites"][1],
                entry["separation_mm"],
                where,
                entry["minimum_mm"],
            )
        )

    closest = None
    if len(sites) >= 2:
        pairs = [
            (separation_mm(sites[i], sites[j]), sites[i]["id"], sites[j]["id"])
            for i in range(len(sites))
            for j in range(i + 1, len(sites))
        ]
        distance, first, second = min(pairs)
        closest = {"sites": (first, second), "separation_mm": distance}

    governing = None
    if utilisations:
        governing = max(utilisations, key=lambda k: utilisations[k])

    proposal_ids = set(site["id"] for site in proposed)
    proposal_implicated = bool(proposed) and (
        count > allowance
        or density > density_limit + TOLERANCE
        or any(set(entry["sites"]) & proposal_ids for entry in close_pairs)
        or any(set(entry["sites"]) & proposal_ids for entry in conductors)
    )

    return {
        "assurance_level": level,
        "board_area_cm2": area,
        "existing_count": len(existing),
        "proposed_count": len(proposed),
        "total_count": count,
        "allowance": allowance,
        "density_per_100_cm2": density,
        "density_allowance": density_limit,
        "utilisations": utilisations,
        "governing_limit": governing,
        "conductor_violations": conductors,
        "proximity_violations": close_pairs,
        "closest_pair": closest,
        "proposal_implicated": proposal_implicated,
        "findings": findings,
        "within_limits": not findings,
    }
