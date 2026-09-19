"""What may be done with a refused hybrid lot.

Anchor: ECSS-Q-ST-60-05C clause 10.4.3 (the options open to a batch that has
been declared unacceptable, including rework, downgrading, scrapping and
telling the customer). Paraphrased into an implementable procedure; no
standard text is reproduced.

Procedure implemented here
--------------------------
1. Hold the disposition routes in preference order, each with the conditions
   that have to hold before it is open and the records or approvals it drags
   with it.
2. Test every route against the rejection context and report the blockers by
   name, rather than returning a single answer nobody can argue with.
3. Keep scrapping always open. It is the fallback that guarantees a decision
   exists, and the only route whose conditions are about what happens to the
   material afterwards rather than whether it qualifies.
4. Treat customer notification as unconditional and prior. A disposition
   chosen before the customer has been told is recorded as inadmissible,
   because the choice removes options that were theirs to take.
5. Recommend the first open route in preference order and return it with its
   obligations, the blocked routes and their reasons.
"""

__all__ = [
    "DISPOSITION_OPTIONS",
    "OPTION_OBLIGATIONS",
    "customer_notification",
    "eligible_dispositions",
    "normalize_option",
    "option_blockers",
    "recommend_disposition",
    "validate_context",
]

# Routes in preference order: recover the material if it can be recovered,
# hand it back if it is still the manufacturer's, concede only with a waiver,
# and scrap when nothing else is open.
DISPOSITION_OPTIONS = (
    "rework-and-resubmit",
    "screen-to-lower-grade",
    "return-to-manufacturer",
    "use-as-is-under-waiver",
    "scrap",
)

OPTION_OBLIGATIONS = {
    "rework-and-resubmit": (
        "repair-authorization",
        "re-screen-from-the-failing-stage",
        "updated-lot-travel-record",
    ),
    "screen-to-lower-grade": (
        "customer-approval-of-the-downgrade",
        "re-marking-to-the-lower-grade",
        "segregation-from-the-original-grade-stock",
    ),
    "return-to-manufacturer": (
        "return-authorization",
        "traceability-record-handover",
    ),
    "use-as-is-under-waiver": (
        "signed-customer-waiver",
        "waiver-reference-in-the-delivery-documentation",
    ),
    "scrap": (
        "scrapping-record",
        "physical-defacement-so-the-parts-cannot-re-enter-supply",
    ),
}

# Context flags read by the route conditions, all boolean.
_BOOLEAN_KEYS = (
    "failure_mode_is_reworkable",
    "repair_permitted_at_assembly_stage",
    "defect_is_lot_wide_materials_or_design",
    "lower_grade_defined_in_specification",
    "customer_agreed_downgrade",
    "units_individually_pass_lower_grade",
    "defect_affects_every_grade",
    "lot_within_manufacturer_responsibility",
    "customer_waiver_granted",
    "exceedance_is_functional_or_hermetic",
    "customer_notified",
)


def normalize_option(option):
    """Return a disposition route name normalised for case and separator."""
    if not isinstance(option, str):
        raise ValueError("disposition option must be a string, got %r" % (option,))
    token = option.strip().lower().replace("_", "-").replace(" ", "-")
    if token not in DISPOSITION_OPTIONS:
        raise ValueError("unknown disposition option %r" % (option,))
    return token


def validate_context(context):
    """Return the rejection context with every flag defaulted and checked."""
    if not isinstance(context, dict):
        raise ValueError("context must be a mapping")
    resolved = {}
    for key in _BOOLEAN_KEYS:
        value = context.get(key, False)
        if not isinstance(value, bool):
            raise ValueError("%s must be a boolean, got %r" % (key, value))
        resolved[key] = value
    allowance = context.get("remaining_repair_allowance", 0)
    if not isinstance(allowance, int) or isinstance(allowance, bool):
        raise ValueError(
            "remaining_repair_allowance must be an integer, got %r" % (allowance,)
        )
    if allowance < 0:
        raise ValueError(
            "remaining_repair_allowance must not be negative, got %d" % allowance
        )
    resolved["remaining_repair_allowance"] = allowance
    return resolved


def option_blockers(option, context):
    """Return the conditions that keep a disposition route closed."""
    route = normalize_option(option)
    state = validate_context(context)
    blockers = []
    if route == "rework-and-resubmit":
        if not state["failure_mode_is_reworkable"]:
            blockers.append("the failure mode cannot be reworked")
        if not state["repair_permitted_at_assembly_stage"]:
            blockers.append("repair is not permitted at the assembly stage reached")
        if state["remaining_repair_allowance"] <= 0:
            blockers.append("the repair allowance for these units is used up")
        if state["defect_is_lot_wide_materials_or_design"]:
            blockers.append("a lot-wide materials or design defect is not reworkable")
    elif route == "screen-to-lower-grade":
        if not state["lower_grade_defined_in_specification"]:
            blockers.append("no lower grade is defined in the procurement specification")
        if not state["customer_agreed_downgrade"]:
            blockers.append("the customer has not agreed to a downgrade")
        if not state["units_individually_pass_lower_grade"]:
            blockers.append("the units do not individually meet the lower grade")
        if state["defect_affects_every_grade"]:
            blockers.append("the defect fails the units at every grade")
    elif route == "return-to-manufacturer":
        if not state["lot_within_manufacturer_responsibility"]:
            blockers.append("the lot has passed out of the manufacturer's responsibility")
    elif route == "use-as-is-under-waiver":
        if not state["customer_waiver_granted"]:
            blockers.append("no customer waiver has been granted")
        if state["exceedance_is_functional_or_hermetic"]:
            blockers.append("a functional or hermeticity failure cannot be waived")
    return blockers


def customer_notification(context):
    """Return the notification obligation, which no route can remove."""
    state = validate_context(context)
    return {
        "required": True,
        "satisfied": state["customer_notified"],
        "obligation": "notify-the-customer-of-the-rejection-before-dispositioning",
    }


def eligible_dispositions(context):
    """Return every disposition route with its eligibility and blockers."""
    return [
        {
            "option": option,
            "eligible": not option_blockers(option, context),
            "blockers": option_blockers(option, context),
            "obligations": list(OPTION_OBLIGATIONS[option]),
        }
        for option in DISPOSITION_OPTIONS
    ]


def recommend_disposition(context):
    """Run the full clause 10.4.3 disposition assessment for a refused lot."""
    routes = eligible_dispositions(context)
    notification = customer_notification(context)
    open_routes = [route for route in routes if route["eligible"]]
    blocked = [route for route in routes if not route["eligible"]]
    recommended = open_routes[0]
    findings = []
    if not notification["satisfied"]:
        findings.append(
            "the customer has not been notified; any disposition taken now is "
            "inadmissible until that notification is made"
        )
    if recommended["option"] == "scrap":
        findings.append(
            "every recovery route is closed, so the lot falls to scrapping"
        )
    return {
        "recommended": recommended["option"],
        "recommended_obligations": recommended["obligations"],
        "eligible_options": [route["option"] for route in open_routes],
        "blocked_options": [
            {"option": route["option"], "blockers": route["blockers"]} for route in blocked
        ],
        "notification": notification,
        "admissible": notification["satisfied"],
        "findings": findings,
        "routes": routes,
    }
