"""Site security and access control for a space test centre.

Anchor: ECSS-Q-ST-20-07C clause 5.5.4 (paraphrased into an implementable
procedure; no standard text is reproduced).

Three separate things are protected and each fails differently:

A. The facility. Zones carry a protection tier from 1 (site perimeter) to
   4 (the enclosure a flight article sits in). A person is admitted to a
   zone only when their badge is still valid on the day of the request,
   the request falls inside the hours the zone is open, and the party is
   authorised to the zone tier.

   Who supplies that authorisation is the one non-obvious rule here. A
   visitor entering anything above the perimeter has to be escorted, and
   the escort is the accountable party for the whole visit -- so it is
   the escort's tier, not the visitor's, that is graded against the zone.
   That is the point of escorting: it lets an unauthorised person into a
   zone under someone else's authority. An unescorted visitor is refused
   for the missing escort alone, not additionally for the low tier the
   escort would have supplied, because one fix closes both.

B. The visit. A visit that was signed in and never signed out is an open
   visit. It is not a paperwork nit: the centre cannot state who is
   inside a zone during an emergency, and it cannot state who had hands
   near the article during the window a defect appeared in.

C. The test item and its data. Both carry a sensitivity tier and are held
   somewhere. A storage location whose zone tier is below the item's
   sensitivity tier is a finding regardless of how well the doors work,
   because the protection an item receives is the protection of the place
   it is left in, not the protection of the place it was meant for.

Every decision returns the reasons, all of them, not the first one hit: a
request that fails on three counts needs three fixes and reporting only
the first sends the holder back three times.

Stdlib only, offline, deterministic. The evaluation day and the time of
day are inputs, never read from the clock.
"""

MIN_TIER = 1
MAX_TIER = 4

MINUTES_PER_DAY = 24 * 60

DECISION_GRANTED = "granted"
DECISION_DENIED = "denied"

REASON_BADGE_EXPIRED = "badge-expired"
REASON_TIER_TOO_LOW = "authorisation-tier-below-zone-tier"
REASON_NO_ESCORT = "visitor-without-a-named-escort"
REASON_ESCORT_TIER_TOO_LOW = "escort-authorisation-tier-below-zone-tier"
REASON_ESCORT_BADGE_EXPIRED = "escort-badge-expired"
REASON_OUTSIDE_HOURS = "request-outside-the-authorised-hours"

FINDING_OPEN_VISIT = "visit-signed-in-and-never-signed-out"
FINDING_ITEM_UNDER_PROTECTED = "item-held-below-its-sensitivity-tier"
FINDING_DATA_UNDER_PROTECTED = "data-held-below-its-sensitivity-tier"
FINDING_UNKNOWN_ZONE = "record-points-at-an-undeclared-zone"


def _integer(label, value, minimum=None, maximum=None):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if minimum is not None and value < minimum:
        raise ValueError("%s must be >= %d, got %d" % (label, minimum, value))
    if maximum is not None and value > maximum:
        raise ValueError("%s must be <= %d, got %d" % (label, maximum, value))
    return value


def _text(label, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip()


def _boolean(label, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (label, value))
    return value


def validate_zone(record):
    """Validate one zone declaration and return a normalized copy."""
    if not isinstance(record, dict):
        raise ValueError("zone record must be a mapping")
    zone_id = _text("zone id", record.get("id"))
    tier = _integer("zone %s tier" % zone_id, record.get("tier"), MIN_TIER, MAX_TIER)
    opens = _integer(
        "zone %s opens_minute" % zone_id,
        record.get("opens_minute", 0),
        0,
        MINUTES_PER_DAY,
    )
    closes = _integer(
        "zone %s closes_minute" % zone_id,
        record.get("closes_minute", MINUTES_PER_DAY),
        0,
        MINUTES_PER_DAY,
    )
    if opens > closes:
        raise ValueError(
            "zone %s opens at minute %d after it closes at %d"
            % (zone_id, opens, closes)
        )
    return {"id": zone_id, "tier": tier, "opens_minute": opens,
            "closes_minute": closes}


def validate_person(record):
    """Validate one person record and return a normalized copy."""
    if not isinstance(record, dict):
        raise ValueError("person record must be a mapping")
    person_id = _text("person id", record.get("id"))
    tier = _integer(
        "person %s authorisation tier" % person_id,
        record.get("authorisation_tier", 0),
        0,
        MAX_TIER,
    )
    expiry = record.get("badge_valid_until_day")
    if expiry is not None:
        expiry = _integer("person %s badge_valid_until_day" % person_id, expiry)
    return {
        "id": person_id,
        "authorisation_tier": tier,
        "is_visitor": _boolean(
            "person %s is_visitor" % person_id, record.get("is_visitor", False)
        ),
        "badge_valid_until_day": expiry,
    }


def badge_is_valid(person, as_of_day):
    """True when the badge is still good on the evaluation day."""
    norm = validate_person(person)
    day = _integer("as_of_day", as_of_day)
    if norm["badge_valid_until_day"] is None:
        return False
    return norm["badge_valid_until_day"] >= day


def escort_required(zone, person):
    """True when this person needs a named escort for this zone."""
    zone_norm = validate_zone(zone)
    person_norm = validate_person(person)
    return person_norm["is_visitor"] and zone_norm["tier"] > MIN_TIER


def within_authorised_hours(zone, minute_of_day):
    """True when the request time falls inside the zone's open window."""
    zone_norm = validate_zone(zone)
    minute = _integer("minute_of_day", minute_of_day, 0, MINUTES_PER_DAY)
    return zone_norm["opens_minute"] <= minute <= zone_norm["closes_minute"]


def admitting_party(zone, person, escort=None):
    """Whose authorisation tier is graded against the zone: person or escort."""
    zone_norm = validate_zone(zone)
    person_norm = validate_person(person)
    if escort_required(zone_norm, person_norm) and escort is not None:
        return "escort"
    return "person"


def evaluate_access(zone, person, as_of_day, minute_of_day, escort=None):
    """Decide one access request and return every reason it would be denied."""
    zone_norm = validate_zone(zone)
    person_norm = validate_person(person)
    reasons = []
    if not badge_is_valid(person_norm, as_of_day):
        reasons.append(REASON_BADGE_EXPIRED)
    if not within_authorised_hours(zone_norm, minute_of_day):
        reasons.append(REASON_OUTSIDE_HOURS)
    if escort_required(zone_norm, person_norm):
        if escort is None:
            # The escort would have supplied the tier, so the missing
            # escort is the single finding: one fix closes both.
            reasons.append(REASON_NO_ESCORT)
        else:
            escort_norm = validate_person(escort)
            if escort_norm["authorisation_tier"] < zone_norm["tier"]:
                reasons.append(REASON_ESCORT_TIER_TOO_LOW)
            if not badge_is_valid(escort_norm, as_of_day):
                reasons.append(REASON_ESCORT_BADGE_EXPIRED)
    elif person_norm["authorisation_tier"] < zone_norm["tier"]:
        reasons.append(REASON_TIER_TOO_LOW)
    decision = DECISION_DENIED if reasons else DECISION_GRANTED
    return {
        "zone": zone_norm["id"],
        "person": person_norm["id"],
        "decision": decision,
        "admitting_party": admitting_party(zone_norm, person_norm, escort),
        "reasons": reasons,
    }


def validate_visit(record):
    """Validate one visit-log entry and return a normalized copy."""
    if not isinstance(record, dict):
        raise ValueError("visit record must be a mapping")
    visit_id = _text("visit id", record.get("id"))
    signed_in = record.get("signed_in_minute")
    signed_in = _integer(
        "visit %s signed_in_minute" % visit_id, signed_in, 0, MINUTES_PER_DAY
    )
    signed_out = record.get("signed_out_minute")
    if signed_out is not None:
        signed_out = _integer(
            "visit %s signed_out_minute" % visit_id, signed_out, 0, MINUTES_PER_DAY
        )
        if signed_out < signed_in:
            raise ValueError(
                "visit %s signs out at minute %d before it signed in at %d"
                % (visit_id, signed_out, signed_in)
            )
    return {
        "id": visit_id,
        "person": _text("visit %s person" % visit_id, record.get("person")),
        "zone": _text("visit %s zone" % visit_id, record.get("zone")),
        "signed_in_minute": signed_in,
        "signed_out_minute": signed_out,
    }


def open_visits(visit_log):
    """Identifiers of visits that were signed in and never signed out."""
    if not isinstance(visit_log, list):
        raise ValueError("visit_log must be a list")
    seen = set()
    open_ids = []
    for entry in visit_log:
        visit = validate_visit(entry)
        if visit["id"] in seen:
            raise ValueError("duplicate visit id %r" % (visit["id"],))
        seen.add(visit["id"])
        if visit["signed_out_minute"] is None:
            open_ids.append(visit["id"])
    return open_ids


def zone_occupancy(visit_log, minute_of_day):
    """People inside each zone at a given minute, by zone identifier."""
    minute = _integer("minute_of_day", minute_of_day, 0, MINUTES_PER_DAY)
    occupancy = {}
    for entry in visit_log:
        visit = validate_visit(entry)
        if visit["signed_in_minute"] > minute:
            continue
        if visit["signed_out_minute"] is not None and (
            visit["signed_out_minute"] <= minute
        ):
            continue
        occupancy.setdefault(visit["zone"], []).append(visit["person"])
    return {zone: sorted(people) for zone, people in occupancy.items()}


def validate_holding(record, kind):
    """Validate a test-item or data holding record."""
    if not isinstance(record, dict):
        raise ValueError("%s record must be a mapping" % kind)
    holding_id = _text("%s id" % kind, record.get("id"))
    tier = _integer(
        "%s %s sensitivity tier" % (kind, holding_id),
        record.get("sensitivity_tier"),
        MIN_TIER,
        MAX_TIER,
    )
    return {
        "id": holding_id,
        "sensitivity_tier": tier,
        "held_in_zone": _text(
            "%s %s held_in_zone" % (kind, holding_id), record.get("held_in_zone")
        ),
    }


def holding_findings(holdings, zones, kind):
    """Findings for items or data held below their own sensitivity tier."""
    by_id = {}
    for zone in zones:
        norm = validate_zone(zone)
        if norm["id"] in by_id:
            raise ValueError("duplicate zone id %r" % (norm["id"],))
        by_id[norm["id"]] = norm
    finding = (
        FINDING_ITEM_UNDER_PROTECTED if kind == "item" else FINDING_DATA_UNDER_PROTECTED
    )
    out = []
    for record in holdings:
        holding = validate_holding(record, kind)
        zone = by_id.get(holding["held_in_zone"])
        if zone is None:
            out.append({"id": holding["id"], "finding": FINDING_UNKNOWN_ZONE})
            continue
        if zone["tier"] < holding["sensitivity_tier"]:
            out.append({"id": holding["id"], "finding": finding})
    return out


def assess_site_security(
    zones, requests, visit_log, items, data, as_of_day, minute_of_day
):
    """Run the full clause 5.5.4 assessment over a test-centre site."""
    if not isinstance(zones, list) or not zones:
        raise ValueError("zones must be a non-empty list")
    by_id = {}
    for zone in zones:
        norm = validate_zone(zone)
        if norm["id"] in by_id:
            raise ValueError("duplicate zone id %r" % (norm["id"],))
        by_id[norm["id"]] = norm
    decisions = []
    for request in requests:
        if not isinstance(request, dict):
            raise ValueError("access request must be a mapping")
        zone_id = _text("request zone", request.get("zone"))
        if zone_id not in by_id:
            raise ValueError("request points at undeclared zone %r" % (zone_id,))
        decisions.append(
            evaluate_access(
                by_id[zone_id],
                request.get("person"),
                as_of_day,
                minute_of_day,
                request.get("escort"),
            )
        )
    findings = holding_findings(items, zones, "item") + holding_findings(
        data, zones, "data"
    )
    open_ids = open_visits(visit_log)
    for visit_id in open_ids:
        findings.append({"id": visit_id, "finding": FINDING_OPEN_VISIT})
    return {
        "decisions": decisions,
        "denied_requests": [
            d for d in decisions if d["decision"] == DECISION_DENIED
        ],
        "open_visit_ids": open_ids,
        "occupancy": zone_occupancy(visit_log, minute_of_day),
        "findings": findings,
        "secure": not findings and all(
            d["decision"] == DECISION_GRANTED for d in decisions
        ),
    }
