"""Screening regime check for Class 2 EEE parts going into flight hardware.

Anchor: ECSS-Q-ST-60C clause 5.3.3 — the screening applied to Class 2 parts
destined for flight standard hardware. Paraphrased into an implementable
procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Decide whether the lot is destined for flight standard hardware at all. A
   lot routed to ground support or engineering models owes marking that keeps
   it out of flight rather than the flight screening sequence.
2. Take the screen set the package family owes. A cavity package owes a
   hermeticity check that an encapsulated part has no cavity to fail, and a
   set copied between families either over-tests or under-tests.
3. Check the screens actually performed against that set, naming the omitted
   ones rather than reporting a count.
4. Check the order of the screens performed. Stress before measurement is the
   whole point of a screening sequence: a hermeticity check taken before
   temperature cycling and a final electrical taken before burn-in both pass
   parts the sequence exists to remove.
5. Convert the burn-in actually run to its equivalent at the reference
   temperature through an Arrhenius acceleration factor, so a shorter burn-in
   run hotter is judged on what it achieved rather than on its clock hours.
6. Compute the percent defective the lot produced and compare it with the
   percent defective allowable, within a representation-sized tolerance.
7. Report the per-lot records, the flight-ready fraction and a verdict
   carrying every finding rather than the first.
"""

import math

__all__ = [
    "BOLTZMANN_EV_PER_KELVIN",
    "KELVIN_OFFSET",
    "ABSOLUTE_ZERO_C",
    "SCREEN_SETS",
    "SCREEN_PRECEDENCE",
    "FLIGHT_DESTINATION",
    "NON_FLIGHT_DESTINATIONS",
    "PDA_TOLERANCE",
    "HOURS_TOLERANCE",
    "normalize_token",
    "screen_set_for",
    "missing_screens",
    "ordering_findings",
    "acceleration_factor",
    "equivalent_burn_in_hours",
    "burn_in_findings",
    "percent_defective",
    "pda_findings",
    "assess_screening_lot",
    "assess_screening_campaign",
]

BOLTZMANN_EV_PER_KELVIN = 8.617333262e-5
KELVIN_OFFSET = 273.15
ABSOLUTE_ZERO_C = -273.15

# The screens a package family owes before its parts may go to flight
# standard hardware. A cavity package carries a hermeticity check; an
# encapsulated part has no cavity for that check to mean anything.
SCREEN_SETS = {
    "hermetic-cavity": (
        "internal-visual",
        "temperature-cycling",
        "constant-acceleration",
        "burn-in",
        "final-electrical",
        "seal-fine-and-gross-leak",
        "external-visual",
    ),
    "encapsulated-nonhermetic": (
        "temperature-cycling",
        "burn-in",
        "final-electrical",
        "external-visual",
    ),
    "passive-chip": (
        "temperature-cycling",
        "burn-in",
        "final-electrical",
        "external-visual",
    ),
}

# Screens that must precede other screens: the stress comes before the
# measurement that decides whether the part survived it.
SCREEN_PRECEDENCE = (
    ("internal-visual", "burn-in"),
    ("temperature-cycling", "seal-fine-and-gross-leak"),
    ("constant-acceleration", "seal-fine-and-gross-leak"),
    ("burn-in", "final-electrical"),
    ("final-electrical", "external-visual"),
)

FLIGHT_DESTINATION = "flight-standard"
NON_FLIGHT_DESTINATIONS = ("ground-support-equipment", "engineering-model", "breadboard")

# Percent defective and burn-in hours are ratios of decimal values compared in
# binary; a value landing on its limit must not be failed on representation.
PDA_TOLERANCE = 1e-9
HOURS_TOLERANCE = 1e-9


def _require_text(value, label):
    """Return a non-blank text field, raising on anything else."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %s" % (label, type(value).__name__))
    text = value.strip()
    if not text:
        raise ValueError("%s must not be blank" % label)
    return text


def _require_real(value, label):
    """Return a real number, raising on a boolean or a non-number."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    return float(value)


def _require_count(value, label):
    """Return a non-negative integer count."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %d" % (label, value))
    return value


def _require_mapping(value, label):
    """Return a mapping, raising on anything else."""
    if not isinstance(value, dict):
        raise ValueError("%s must be a mapping" % label)
    return value


def normalize_token(value, label):
    """Return a lower-case hyphenated token from a free-text field."""
    text = _require_text(value, label)
    return "-".join(text.lower().replace("_", " ").replace("-", " ").split())


def screen_set_for(package_family):
    """Return the screens a package family owes for flight standard use."""
    family = normalize_token(package_family, "package family")
    if family not in SCREEN_SETS:
        raise ValueError(
            "package family '%s' has no screen set; known families are %s"
            % (family, ", ".join(sorted(SCREEN_SETS)))
        )
    return SCREEN_SETS[family]


def _performed_tokens(performed):
    """Return the performed screens as an ordered token list, rejecting repeats."""
    if not isinstance(performed, (list, tuple)):
        raise ValueError("performed screens must be an ordered sequence")
    tokens = []
    for position, value in enumerate(performed):
        token = normalize_token(value, "performed[%d]" % position)
        if token in tokens:
            raise ValueError("screen '%s' is recorded twice in the sequence" % token)
        tokens.append(token)
    return tokens


def missing_screens(performed, package_family):
    """Return the screens the family owes that the sequence does not carry."""
    tokens = _performed_tokens(performed)
    return [screen for screen in screen_set_for(package_family) if screen not in tokens]


def ordering_findings(performed):
    """Return the findings raised by the order the screens were run in."""
    tokens = _performed_tokens(performed)
    findings = []
    for first, second in SCREEN_PRECEDENCE:
        if first in tokens and second in tokens:
            if tokens.index(first) > tokens.index(second):
                findings.append(
                    "'%s' was run after '%s', so the stress the sequence exists to "
                    "apply came too late to be measured" % (first, second)
                )
    return findings


def acceleration_factor(activation_energy_ev, reference_c, actual_c):
    """Return the Arrhenius acceleration of a burn-in run off its reference."""
    energy = _require_real(activation_energy_ev, "activation_energy_ev")
    if energy <= 0.0:
        raise ValueError("activation_energy_ev must be positive, got %g" % energy)
    reference = _require_real(reference_c, "reference_c")
    actual = _require_real(actual_c, "actual_c")
    for label, value in (("reference_c", reference), ("actual_c", actual)):
        if value <= ABSOLUTE_ZERO_C:
            raise ValueError("%s must lie above absolute zero, got %g" % (label, value))
    reference_k = reference + KELVIN_OFFSET
    actual_k = actual + KELVIN_OFFSET
    exponent = (energy / BOLTZMANN_EV_PER_KELVIN) * (1.0 / reference_k - 1.0 / actual_k)
    return math.exp(exponent)


def equivalent_burn_in_hours(hours, activation_energy_ev, reference_c, actual_c):
    """Return the burn-in achieved, expressed at the reference temperature."""
    run = _require_real(hours, "burn_in_hours")
    if run < 0.0:
        raise ValueError("burn_in_hours must not be negative, got %g" % run)
    return run * acceleration_factor(activation_energy_ev, reference_c, actual_c)


def burn_in_findings(burn_in, policy):
    """Return the equivalent burn-in achieved and any shortfall against policy."""
    _require_mapping(burn_in, "burn_in")
    _require_mapping(policy, "policy")
    for key in ("hours", "temperature_c"):
        if key not in burn_in:
            raise ValueError("burn_in missing required key '%s'" % key)
    for key in ("burn_in_reference_c", "burn_in_required_hours", "activation_energy_ev"):
        if key not in policy:
            raise ValueError("policy missing required key '%s'" % key)

    required = _require_real(policy["burn_in_required_hours"], "burn_in_required_hours")
    if required <= 0.0:
        raise ValueError("burn_in_required_hours must be positive, got %g" % required)
    achieved = equivalent_burn_in_hours(
        burn_in["hours"],
        policy["activation_energy_ev"],
        policy["burn_in_reference_c"],
        burn_in["temperature_c"],
    )
    findings = []
    if achieved < required - HOURS_TOLERANCE:
        findings.append(
            "burn-in achieved %.3f equivalent hours at %g C reference, short of the "
            "%.3f required"
            % (achieved, _require_real(policy["burn_in_reference_c"], "burn_in_reference_c"), required)
        )
    return {
        "equivalent_hours": achieved,
        "required_hours": required,
        "findings": findings,
    }


def percent_defective(devices_screened, devices_rejected):
    """Return the percent defective a screened lot produced."""
    screened = _require_count(devices_screened, "devices_screened")
    if screened < 1:
        raise ValueError("devices_screened must be at least 1")
    rejected = _require_count(devices_rejected, "devices_rejected")
    if rejected > screened:
        raise ValueError(
            "devices_rejected %d exceeds the %d screened" % (rejected, screened)
        )
    return rejected / float(screened) * 100.0


def pda_findings(devices_screened, devices_rejected, pda_percent):
    """Return the percent defective and any breach of the allowable."""
    allowable = _require_real(pda_percent, "pda_percent")
    if not 0.0 <= allowable <= 100.0:
        raise ValueError("pda_percent must lie in 0..100, got %g" % allowable)
    observed = percent_defective(devices_screened, devices_rejected)
    findings = []
    if observed > allowable + PDA_TOLERANCE:
        findings.append(
            "the lot rejected %.3f percent at screening, above the %.3f percent allowable"
            % (observed, allowable)
        )
    return {
        "percent_defective": observed,
        "pda_percent": allowable,
        "findings": findings,
    }


def assess_screening_lot(lot, policy):
    """Return one Class 2 lot screening record carrying its findings."""
    _require_mapping(lot, "lot")
    _require_mapping(policy, "policy")
    if "lot_id" not in lot:
        raise ValueError("lot missing required key 'lot_id'")
    lot_id = _require_text(lot["lot_id"], "lot_id")
    if "destination" not in lot:
        raise ValueError("lot '%s' missing required key 'destination'" % lot_id)
    destination = normalize_token(lot["destination"], "destination")
    known = (FLIGHT_DESTINATION,) + NON_FLIGHT_DESTINATIONS
    if destination not in known:
        raise ValueError("destination '%s' is not a recognised destination" % destination)

    if destination != FLIGHT_DESTINATION:
        findings = []
        if not lot.get("marked_non_flight", False):
            findings.append(
                "lot '%s' is routed to '%s' without flight screening and is not marked "
                "to keep it out of flight hardware" % (lot_id, destination)
            )
        return {
            "lot_id": lot_id,
            "destination": destination,
            "flight_screened": False,
            "missing_screens": [],
            "burn_in": None,
            "pda": None,
            "findings": findings,
            "acceptable": not findings,
        }

    for key in (
        "package_family",
        "screens_performed",
        "burn_in",
        "devices_screened",
        "devices_rejected",
    ):
        if key not in lot:
            raise ValueError("lot '%s' missing required key '%s'" % (lot_id, key))
    if "pda_percent" not in policy:
        raise ValueError("policy missing required key 'pda_percent'")

    findings = []
    omitted = missing_screens(lot["screens_performed"], lot["package_family"])
    for screen in omitted:
        findings.append(
            "lot '%s' went to flight standard hardware without the '%s' screen its "
            "package family owes" % (lot_id, screen)
        )
    findings.extend(ordering_findings(lot["screens_performed"]))

    burn_in = burn_in_findings(lot["burn_in"], policy)
    findings.extend(burn_in["findings"])

    pda = pda_findings(lot["devices_screened"], lot["devices_rejected"], policy["pda_percent"])
    findings.extend(pda["findings"])

    return {
        "lot_id": lot_id,
        "destination": destination,
        "flight_screened": True,
        "missing_screens": omitted,
        "burn_in": burn_in,
        "pda": pda,
        "findings": findings,
        "acceptable": not findings,
    }


def assess_screening_campaign(campaign):
    """Run the full clause 5.3.3 Class 2 screening assessment.

    campaign keys: build_reference, policy, lots.
    """
    _require_mapping(campaign, "campaign")
    for key in ("build_reference", "policy", "lots"):
        if key not in campaign:
            raise ValueError("campaign missing required key '%s'" % key)
    build_reference = _require_text(campaign["build_reference"], "build_reference")
    lots = campaign["lots"]
    if not isinstance(lots, (list, tuple)) or not lots:
        raise ValueError("lots must be a non-empty sequence")

    records = []
    seen = []
    for lot in lots:
        record = assess_screening_lot(lot, campaign["policy"])
        if record["lot_id"] in seen:
            raise ValueError("lot '%s' is reported twice" % record["lot_id"])
        seen.append(record["lot_id"])
        records.append(record)

    findings = []
    for record in records:
        findings.extend(record["findings"])

    flight = [r for r in records if r["destination"] == FLIGHT_DESTINATION]
    ready = [r for r in flight if r["acceptable"]]
    return {
        "build_reference": build_reference,
        "lots": records,
        "flight_lot_count": len(flight),
        "flight_ready_fraction": (len(ready) / float(len(flight))) if flight else 0.0,
        "screening_complete": not findings,
        "findings": findings,
    }
