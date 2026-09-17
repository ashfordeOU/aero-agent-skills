"""Screening owed by a Class 3 lot before it enters flight standard hardware.

Anchor: ECSS-Q-ST-60C clause 6.3.3 (the screening regime applied to Class 3
parts destined for flight standard hardware).

Offline, deterministic, python3 standard library only.

Procedure implemented here (paraphrased, no standard text reproduced):

* The destination decides whether screening is owed at all. A lot going to
  ground support equipment, an engineering model or a breadboard owes the
  flight screening regime nothing, but it does owe a marking that keeps it out
  of flight hardware later.
* What is owed comes from the package family, because the failure mechanisms a
  screen addresses are properties of the package.
* At this assurance category much of the regime is already inside the
  manufacturer's standard flow, so a screen may be credited to it. Credit is
  earned by an evidence reference, not by a claim: an uncited claim leaves the
  screen owed to the project, which is the defect this check exists for.
* Each stress has to precede the electrical measurement that judges it. A
  measurement taken before the stress measured nothing about it.
* A burn-in held off its reference temperature is converted to equivalent
  hours through an Arrhenius acceleration factor before it is compared with
  the reduced duration this category allows.
* The percent defective the screening produced is compared with the allowable.
"""

from __future__ import annotations

import math

BOLTZMANN_EV_PER_KELVIN = 8.617333262e-5
KELVIN_OFFSET = 273.15
ABSOLUTE_ZERO_C = -273.15

# Where a screened lot is going.
FLIGHT_DESTINATION = "flight-standard"
NON_FLIGHT_DESTINATIONS = (
    "ground-support-equipment",
    "engineering-model",
    "breadboard",
)
DESTINATIONS = (FLIGHT_DESTINATION,) + NON_FLIGHT_DESTINATIONS

# The screens each package family owes a flight standard lot.
SCREEN_SETS = {
    "plastic-encapsulated": (
        "external-visual-inspection",
        "temperature-cycling",
        "burn-in",
        "final-electrical-measurement",
    ),
    "hermetic-ceramic": (
        "external-visual-inspection",
        "temperature-cycling",
        "constant-acceleration",
        "burn-in",
        "seal-test",
        "final-electrical-measurement",
    ),
    "hermetic-metal": (
        "external-visual-inspection",
        "temperature-cycling",
        "burn-in",
        "seal-test",
        "final-electrical-measurement",
    ),
    "bare-die": (
        "external-visual-inspection",
        "wire-bond-evaluation",
        "final-electrical-measurement",
    ),
}

PACKAGE_FAMILIES = tuple(sorted(SCREEN_SETS))

# The order stresses and the measurement that judges them have to occur in.
SCREEN_PRECEDENCE = (
    "external-visual-inspection",
    "wire-bond-evaluation",
    "temperature-cycling",
    "constant-acceleration",
    "burn-in",
    "seal-test",
    "final-electrical-measurement",
)

PRECEDENCE_RANK = {screen: index for index, screen in enumerate(SCREEN_PRECEDENCE)}

# Who a screen was performed by.
PERFORMERS = ("manufacturer-standard-flow", "project")

# The reduced burn-in this assurance category accepts, at the reference
# temperature the reference duration is stated for.
MINIMUM_BURN_IN_HOURS = 96.0

# The percent defective a Class 3 lot may produce and still be accepted.
PERCENT_DEFECTIVE_ALLOWABLE = 10.0

# Declared quantities and converted durations; a case meant to sit on a bound
# can land a few units in the last place away from it.
HOURS_TOLERANCE = 1e-9
PDA_TOLERANCE = 1e-9

LOT_STATUSES = (
    "class-3-lot-accepted-for-flight-standard-use",
    "class-3-lot-screening-incomplete",
    "class-3-lot-rejected-on-percent-defective",
    "class-3-lot-not-for-flight-standard-use",
)


def _require_real(value, label):
    """Return ``value`` as a finite float or raise for anything else."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return number


def _require_count(value, label):
    """Return a required non-negative whole count or raise."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be a whole number, got %r" % (label, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %r" % (label, value))
    return value


def _require_text(value, label):
    """Return a required non-empty string field or raise."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip()


def _require_mapping(value, label):
    """Return a required mapping field or raise."""
    if not isinstance(value, dict):
        raise ValueError("%s must be a mapping, got %r" % (label, type(value).__name__))
    return value


def _require_flag(mapping, key):
    """Return a required boolean field of a mapping or raise."""
    value = mapping.get(key)
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (key, value))
    return value


def _celsius_to_kelvin(value, label):
    """Convert a temperature to kelvin, refusing anything at or below zero."""
    celsius = _require_real(value, label)
    if celsius <= ABSOLUTE_ZERO_C:
        raise ValueError("%s must lie above absolute zero, got %r" % (label, value))
    return celsius + KELVIN_OFFSET


def screening_is_owed(destination):
    """True when the destination puts the lot into flight standard hardware."""
    if destination not in DESTINATIONS:
        raise ValueError(
            "unknown destination %r (known: %s)" % (destination, ", ".join(DESTINATIONS))
        )
    return destination == FLIGHT_DESTINATION


def screen_set_for(package_family):
    """The screens a package family owes a flight standard lot."""
    if package_family not in SCREEN_SETS:
        raise ValueError(
            "unknown package family %r (known: %s)"
            % (package_family, ", ".join(PACKAGE_FAMILIES))
        )
    return SCREEN_SETS[package_family]


def normalize_performed(performed):
    """Validate the screening record entry by entry."""
    if isinstance(performed, str) or not isinstance(performed, (list, tuple)):
        raise ValueError(
            "performed must be a list or tuple of mappings, got %r" % (performed,)
        )
    normalized = []
    seen = set()
    for raw in performed:
        entry = _require_mapping(raw, "performed screen")
        screen = entry.get("screen")
        if screen not in PRECEDENCE_RANK:
            raise ValueError(
                "unknown screen %r (known: %s)"
                % (screen, ", ".join(SCREEN_PRECEDENCE))
            )
        if screen in seen:
            raise ValueError("screen %r appears twice in the record" % (screen,))
        seen.add(screen)
        performer = entry.get("performed_by")
        if performer not in PERFORMERS:
            raise ValueError(
                "unknown performed_by %r (known: %s)"
                % (performer, ", ".join(PERFORMERS))
            )
        reference = entry.get("evidence_reference")
        if reference is not None and not isinstance(reference, str):
            raise ValueError(
                "evidence_reference must be a string or None, got %r" % (reference,)
            )
        normalized.append(
            {
                "screen": screen,
                "performed_by": performer,
                "evidence_reference": reference,
            }
        )
    return normalized


def credited_screens(performed):
    """Screens that actually count, with uncredited manufacturer claims dropped."""
    credited = []
    for entry in normalize_performed(performed):
        if entry["performed_by"] == "manufacturer-standard-flow":
            reference = entry["evidence_reference"]
            if not isinstance(reference, str) or not reference.strip():
                continue
        credited.append(entry["screen"])
    return tuple(credited)


def uncredited_claims(performed):
    """Manufacturer flow claims that cited no evidence and so earn no credit."""
    claims = []
    for entry in normalize_performed(performed):
        if entry["performed_by"] != "manufacturer-standard-flow":
            continue
        reference = entry["evidence_reference"]
        if not isinstance(reference, str) or not reference.strip():
            claims.append(entry["screen"])
    return tuple(claims)


def missing_screens(performed, package_family):
    """Screens the package family owes that nothing credible covered."""
    credited = set(credited_screens(performed))
    return tuple(
        screen for screen in screen_set_for(package_family) if screen not in credited
    )


def ordering_findings(performed):
    """Findings raised where a stress did not precede the measurement."""
    order = [PRECEDENCE_RANK[entry["screen"]] for entry in normalize_performed(performed)]
    names = [entry["screen"] for entry in normalize_performed(performed)]
    findings = []
    for index in range(1, len(order)):
        if order[index] < order[index - 1]:
            findings.append(
                {
                    "finding": "screen-performed-out-of-the-required-order",
                    "detail": "%s before %s" % (names[index], names[index - 1]),
                }
            )
    return tuple(findings)


def acceleration_factor(activation_energy_ev, reference_c, actual_c):
    """Arrhenius factor between the reference and the actual burn-in temperature."""
    energy = _require_real(activation_energy_ev, "activation_energy_ev")
    if energy <= 0.0:
        raise ValueError(
            "activation_energy_ev must be positive, got %r" % (activation_energy_ev,)
        )
    reference_k = _celsius_to_kelvin(reference_c, "reference_c")
    actual_k = _celsius_to_kelvin(actual_c, "actual_c")
    exponent = (energy / BOLTZMANN_EV_PER_KELVIN) * (1.0 / reference_k - 1.0 / actual_k)
    return math.exp(exponent)


def equivalent_burn_in_hours(hours, activation_energy_ev, reference_c, actual_c):
    """Burn-in hours referred back to the reference temperature."""
    duration = _require_real(hours, "burn_in_hours")
    if duration < 0.0:
        raise ValueError("burn_in_hours must not be negative, got %r" % (hours,))
    return duration * acceleration_factor(activation_energy_ev, reference_c, actual_c)


def burn_in_findings(burn_in, minimum_hours=MINIMUM_BURN_IN_HOURS):
    """Findings raised by the burn-in actually run on the lot."""
    entry = _require_mapping(burn_in, "burn_in")
    minimum = _require_real(minimum_hours, "minimum_burn_in_hours")
    if minimum <= 0.0:
        raise ValueError("minimum_burn_in_hours must be positive, got %r" % (minimum,))
    equivalent = equivalent_burn_in_hours(
        entry.get("hours"),
        entry.get("activation_energy_ev"),
        entry.get("reference_c"),
        entry.get("actual_c"),
    )
    if equivalent < minimum - HOURS_TOLERANCE:
        return (
            {
                "finding": "burn-in-short-of-the-reduced-duration-allowed",
                "detail": "%.2f equivalent hours against %.2f" % (equivalent, minimum),
            },
        )
    return ()


def percent_defective(devices_screened, devices_rejected):
    """Percent of the lot the screening rejected."""
    screened = _require_count(devices_screened, "devices_screened")
    rejected = _require_count(devices_rejected, "devices_rejected")
    if screened == 0:
        raise ValueError("devices_screened must be positive to form a percentage")
    if rejected > screened:
        raise ValueError("devices_rejected must not exceed devices_screened")
    return 100.0 * float(rejected) / float(screened)


def pda_findings(devices_screened, devices_rejected, allowable=PERCENT_DEFECTIVE_ALLOWABLE):
    """Findings raised by the percent defective against the allowable."""
    limit = _require_real(allowable, "percent_defective_allowable")
    if not (0.0 < limit <= 100.0):
        raise ValueError("percent_defective_allowable must lie in (0, 100], got %r" % (allowable,))
    produced = percent_defective(devices_screened, devices_rejected)
    if produced > limit + PDA_TOLERANCE:
        return (
            {
                "finding": "percent-defective-above-the-allowable",
                "detail": "%.3f percent against %.3f" % (produced, limit),
            },
        )
    return ()


def assess_screening_lot(lot, policy=None):
    """Read one screened lot and return its status with findings."""
    entry = _require_mapping(lot, "lot")
    lot_id = _require_text(entry.get("lot_id"), "lot_id")
    category = _require_text(entry.get("declared_category"), "declared_category")
    destination = entry.get("destination")
    owed = screening_is_owed(destination)
    rules = _require_mapping(policy if policy is not None else {}, "policy")
    minimum_hours = _require_real(
        rules.get("minimum_burn_in_hours", MINIMUM_BURN_IN_HOURS),
        "minimum_burn_in_hours",
    )
    allowable = _require_real(
        rules.get("percent_defective_allowable", PERCENT_DEFECTIVE_ALLOWABLE),
        "percent_defective_allowable",
    )

    findings = []
    if category != "class-3":
        findings.append(
            {
                "lot_id": lot_id,
                "finding": "declared-category-is-not-the-one-being-checked",
                "detail": category,
            }
        )

    if not owed:
        if not _require_flag(entry, "non_flight_marking_present"):
            findings.append(
                {
                    "lot_id": lot_id,
                    "finding": "non-flight-lot-carries-no-marking",
                    "detail": destination,
                }
            )
        return {
            "lot_id": lot_id,
            "destination": destination,
            "screening_owed": False,
            "status": "class-3-lot-not-for-flight-standard-use",
            "missing_screens": [],
            "uncredited_claims": [],
            "percent_defective": None,
            "findings": findings,
            "accepted": False,
        }

    package_family = entry.get("package_family")
    performed = entry.get("performed", [])
    absent = missing_screens(performed, package_family)
    claims = uncredited_claims(performed)

    for screen in claims:
        findings.append(
            {
                "lot_id": lot_id,
                "finding": "manufacturer-flow-credit-claimed-without-evidence",
                "detail": screen,
            }
        )
    for screen in absent:
        findings.append(
            {
                "lot_id": lot_id,
                "finding": "owed-screen-not-covered",
                "detail": screen,
            }
        )
    for finding in ordering_findings(performed):
        findings.append(dict(finding, lot_id=lot_id))

    if "burn-in" in screen_set_for(package_family) and "burn-in" in set(
        credited_screens(performed)
    ):
        for finding in burn_in_findings(entry.get("burn_in"), minimum_hours):
            findings.append(dict(finding, lot_id=lot_id))

    produced = percent_defective(
        entry.get("devices_screened"), entry.get("devices_rejected")
    )
    pda = pda_findings(
        entry.get("devices_screened"), entry.get("devices_rejected"), allowable
    )
    for finding in pda:
        findings.append(dict(finding, lot_id=lot_id))

    if pda:
        status = "class-3-lot-rejected-on-percent-defective"
    elif findings:
        status = "class-3-lot-screening-incomplete"
    else:
        status = "class-3-lot-accepted-for-flight-standard-use"

    return {
        "lot_id": lot_id,
        "destination": destination,
        "screening_owed": True,
        "package_family": package_family,
        "status": status,
        "missing_screens": list(absent),
        "uncredited_claims": list(claims),
        "percent_defective": produced,
        "findings": findings,
        "accepted": status == "class-3-lot-accepted-for-flight-standard-use",
    }


def assess_class_3_screening_campaign(campaign):
    """Judge every lot in a Class 3 screening campaign."""
    entry = _require_mapping(campaign, "campaign")
    campaign_id = _require_text(entry.get("campaign_id"), "campaign_id")
    lots = entry.get("lots")
    if isinstance(lots, str) or not isinstance(lots, (list, tuple)):
        raise ValueError("lots must be a list or tuple of mappings, got %r" % (lots,))
    if not lots:
        raise ValueError("at least one lot is required")
    policy = entry.get("policy")

    records = []
    seen = set()
    findings = []
    for lot in lots:
        record = assess_screening_lot(lot, policy)
        if record["lot_id"] in seen:
            raise ValueError("duplicate lot_id %r" % (record["lot_id"],))
        seen.add(record["lot_id"])
        records.append(record)
        findings.extend(record["findings"])

    accepted = [r["lot_id"] for r in records if r["accepted"]]
    flight_lots = [r for r in records if r["screening_owed"]]
    counts = {status: 0 for status in LOT_STATUSES}
    for record in records:
        counts[record["status"]] += 1

    return {
        "campaign_id": campaign_id,
        "lot_records": records,
        "accepted_lots": accepted,
        "flight_lot_count": len(flight_lots),
        "accepted_fraction": (
            float(len(accepted)) / float(len(flight_lots)) if flight_lots else 0.0
        ),
        "status_counts": counts,
        "findings": findings,
        "campaign_clear": not findings,
    }
