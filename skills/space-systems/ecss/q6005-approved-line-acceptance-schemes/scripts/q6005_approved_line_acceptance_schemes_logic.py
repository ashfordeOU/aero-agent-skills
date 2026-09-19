"""Acceptance schemes open to a hybrid maker running an approved line.

Anchor: ECSS-Q-ST-60-05C clause 12.2 (the acceptance testing options open to
a supplier operating an approved hybrid production line). Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the supplier profile. The approved line is the entry condition
   for the whole clause: without it neither option here is open and the
   supplier falls to the project-validated route instead.
2. Test each option's own entry conditions independently. The per-lot option
   needs a batch large enough to draw its sample from and somewhere to run
   the tests. The monitoring option needs a run of consecutive monitored
   lots, a capability index at or above the floor, a quorate technical review
   board holding the required roles, and a written criterion for dropping
   back to per-lot testing.
3. Report the gaps for every option, not only the chosen one: a supplier
   two conditions short of the monitoring option needs to know which two.
4. Where both options are open, recommend one from the line's throughput and
   the annual sample burden the per-lot option would carry, and say why.
"""

__all__ = [
    "PRODUCTION_LOT_CONTROL",
    "REVIEW_BOARD_PROCESS_CONTROL",
    "SCHEMES",
    "MIN_MONITORED_LOTS",
    "MIN_CAPABILITY_INDEX",
    "REQUIRED_BOARD_ROLES",
    "BOARD_QUORUM",
    "CONTINUOUS_PRODUCTION_LOTS_PER_YEAR",
    "CAPABILITY_TOLERANCE",
    "validate_profile",
    "board_roles_present",
    "board_is_quorate",
    "annual_sample_burden",
    "scheme_gaps",
    "available_schemes",
    "recommend_scheme",
    "assess_acceptance_scheme_options",
]

PRODUCTION_LOT_CONTROL = "production-lot-control"
REVIEW_BOARD_PROCESS_CONTROL = "review-board-and-process-control"
SCHEMES = (PRODUCTION_LOT_CONTROL, REVIEW_BOARD_PROCESS_CONTROL)

# A run of consecutive monitored lots short of this gives the control chart
# too little history to say the line is stable.
MIN_MONITORED_LOTS = 10

# Capability floor the monitored process holds to stand in for per-lot tests.
MIN_CAPABILITY_INDEX = 1.33

# Capability indices are quotients of measured spreads and land on the floor
# exactly in worked examples; comparisons absorb representation error here.
CAPABILITY_TOLERANCE = 1e-9

# Roles the technical review board draws its members from.
REQUIRED_BOARD_ROLES = (
    "manufacturer-quality-assurance",
    "manufacturing-engineering",
    "component-engineering",
    "customer-product-assurance",
)

# Members needed for the board to decide anything.
BOARD_QUORUM = 3

# Lots a year at or above which the line counts as in continuous production.
CONTINUOUS_PRODUCTION_LOTS_PER_YEAR = 6

_INT_FIELDS = (
    "batch_size",
    "units_available_for_sampling",
    "per_lot_sample_size",
    "monitored_consecutive_lots",
    "lots_per_year",
)
_BOOL_FIELDS = (
    "approved_line",
    "acceptance_test_facility",
    "reversion_criteria_defined",
)


def _require_non_negative_int(value, label):
    """Return value as a non-negative int, raising on anything that is not one."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %d" % (label, value))
    return value


def validate_profile(profile):
    """Return the supplier profile normalised, raising on anything unusable.

    Missing optional evidence normalises to its empty value -- a supplier with
    no board recorded is a supplier without a board, which is a gap to report
    rather than an input error.
    """
    if not isinstance(profile, dict):
        raise ValueError("profile must be a mapping")
    normalised = {}
    for field in _BOOL_FIELDS:
        value = profile.get(field, False)
        if not isinstance(value, bool):
            raise ValueError("%s must be a boolean, got %r" % (field, value))
        normalised[field] = value
    for field in _INT_FIELDS:
        normalised[field] = _require_non_negative_int(profile.get(field, 0), field)
    capability = profile.get("process_capability_index", 0.0)
    if isinstance(capability, bool) or not isinstance(capability, (int, float)):
        raise ValueError("process_capability_index must be a number, got %r" % (capability,))
    if capability < 0:
        raise ValueError("process_capability_index must not be negative")
    normalised["process_capability_index"] = float(capability)
    roles = profile.get("review_board_roles", ())
    if isinstance(roles, str) or not isinstance(roles, (list, tuple, set, frozenset)):
        raise ValueError("review_board_roles must be a sequence of role names")
    cleaned = set()
    for role in roles:
        if not isinstance(role, str) or not role.strip():
            raise ValueError("role names must be non-empty strings, got %r" % (role,))
        cleaned.add(role.strip().lower().replace("_", "-").replace(" ", "-"))
    normalised["review_board_roles"] = cleaned
    reference = profile.get("approval_reference")
    if reference is not None and (not isinstance(reference, str) or not reference.strip()):
        raise ValueError("approval_reference must be a non-empty string when given")
    normalised["approval_reference"] = reference.strip() if reference else None
    if normalised["per_lot_sample_size"] > normalised["batch_size"] > 0:
        raise ValueError("per_lot_sample_size exceeds the batch it is drawn from")
    return normalised


def board_roles_present(profile):
    """Return the required board roles this supplier's board actually holds."""
    held = validate_profile(profile)["review_board_roles"]
    return [role for role in REQUIRED_BOARD_ROLES if role in held]


def board_is_quorate(profile, quorum=BOARD_QUORUM):
    """Return whether the board holds enough of the required roles to decide."""
    return len(board_roles_present(profile)) >= _require_non_negative_int(quorum, "quorum")


def annual_sample_burden(profile):
    """Return the units a year the per-lot option would consume in sampling."""
    normalised = validate_profile(profile)
    return normalised["per_lot_sample_size"] * normalised["lots_per_year"]


def scheme_gaps(profile, scheme):
    """Return the unmet entry conditions for one acceptance option."""
    if scheme not in SCHEMES:
        raise ValueError("unknown scheme %r; expected one of %s" % (scheme, ", ".join(SCHEMES)))
    p = validate_profile(profile)
    gaps = []
    if not p["approved_line"]:
        gaps.append("the production line is not an approved hybrid line")
    elif p["approval_reference"] is None:
        gaps.append("the line approval carries no reference to cite")

    if scheme == PRODUCTION_LOT_CONTROL:
        if p["per_lot_sample_size"] <= 0:
            gaps.append("no per-lot sample size has been set")
        if p["units_available_for_sampling"] < p["per_lot_sample_size"]:
            gaps.append(
                "each lot yields %d units for sampling against a sample of %d"
                % (p["units_available_for_sampling"], p["per_lot_sample_size"])
            )
        if not p["acceptance_test_facility"]:
            gaps.append("no acceptance test facility is available to the line")
    else:
        if p["monitored_consecutive_lots"] < MIN_MONITORED_LOTS:
            gaps.append(
                "only %d consecutive monitored lots against the %d the chart needs"
                % (p["monitored_consecutive_lots"], MIN_MONITORED_LOTS)
            )
        if p["process_capability_index"] < MIN_CAPABILITY_INDEX - CAPABILITY_TOLERANCE:
            gaps.append(
                "process capability index %.4f is below the floor of %.2f"
                % (p["process_capability_index"], MIN_CAPABILITY_INDEX)
            )
        missing_roles = [r for r in REQUIRED_BOARD_ROLES if r not in p["review_board_roles"]]
        if not board_is_quorate(profile):
            gaps.append(
                "technical review board is not quorate; missing %s" % ", ".join(missing_roles)
            )
        if "customer-product-assurance" not in p["review_board_roles"]:
            gaps.append("technical review board carries no customer product assurance member")
        if not p["reversion_criteria_defined"]:
            gaps.append("no written criterion for dropping back to per-lot testing")
    return gaps


def available_schemes(profile):
    """Return the acceptance options this supplier may actually operate."""
    return [scheme for scheme in SCHEMES if not scheme_gaps(profile, scheme)]


def recommend_scheme(profile):
    """Return the recommended option and the reason for it.

    With both open, a line in continuous production carrying a heavy annual
    sampling burden is better served by monitoring than by testing every lot;
    an occasional line is not, because the chart never accumulates history.
    """
    open_schemes = available_schemes(profile)
    if not open_schemes:
        return {"scheme": None, "rationale": "no acceptance option under this clause is open"}
    p = validate_profile(profile)
    burden = annual_sample_burden(profile)
    if len(open_schemes) == 1:
        return {
            "scheme": open_schemes[0],
            "rationale": "the only option whose entry conditions are met",
        }
    continuous = p["lots_per_year"] >= CONTINUOUS_PRODUCTION_LOTS_PER_YEAR
    if continuous:
        return {
            "scheme": REVIEW_BOARD_PROCESS_CONTROL,
            "rationale": (
                "line runs %d lots a year and per-lot testing would consume %d units "
                "annually; a monitored line with a quorate board carries that better"
                % (p["lots_per_year"], burden)
            ),
        }
    return {
        "scheme": PRODUCTION_LOT_CONTROL,
        "rationale": (
            "line runs %d lots a year, too few for a control chart to hold history "
            "between builds; each lot earns its own sample" % p["lots_per_year"]
        ),
    }


def assess_acceptance_scheme_options(profile):
    """Run the full clause 12.2 assessment of the options open to a supplier."""
    p = validate_profile(profile)
    gaps = {scheme: scheme_gaps(profile, scheme) for scheme in SCHEMES}
    open_schemes = [scheme for scheme in SCHEMES if not gaps[scheme]]
    recommendation = recommend_scheme(profile)
    return {
        "approved_line": p["approved_line"],
        "approval_reference": p["approval_reference"],
        "available_schemes": open_schemes,
        "gaps": gaps,
        "board_roles_present": board_roles_present(profile),
        "board_quorate": board_is_quorate(profile),
        "annual_sample_burden": annual_sample_burden(profile),
        "continuous_production": p["lots_per_year"] >= CONTINUOUS_PRODUCTION_LOTS_PER_YEAR,
        "recommended_scheme": recommendation["scheme"],
        "rationale": recommendation["rationale"],
        "falls_to_project_validation": not p["approved_line"],
    }
