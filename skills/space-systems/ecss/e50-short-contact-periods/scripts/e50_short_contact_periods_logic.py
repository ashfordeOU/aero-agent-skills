"""Sizing a space link against short contact periods.

Anchor: ECSS-E-ST-50C Rev.2 clause 5.6.3 (paraphrased into an
implementable procedure; no standard text is reproduced).

Procedure implemented here:

1. Take the contact schedule a mission actually gets -- a start time
   and a duration per pass -- together with the acquisition and setup
   time the link needs before user data can flow.
2. Subtract the setup from each pass. What is left is the usable
   transfer time; a pass shorter than its own setup delivers nothing at
   all, and a pass where setup eats most of the window is a short
   contact whose overhead has to be visible in the budget.
3. Convert usable time into a deliverable volume through the channel
   rate, the coding rate and the framing efficiency. The rate on the
   air is not the rate of user data: coding and framing both take their
   share before the first user bit lands.
4. Walk the schedule in time order. Between contacts the onboard store
   fills at the generation rate; during a contact it fills at the same
   rate while it drains at the delivered rate. A store that reaches its
   capacity loses what it cannot hold, and the lost volume is counted
   rather than hidden.
5. Report the backlog at the end of the plan, its peak, whether the
   store was ever cleared, and whether the plan is stable -- a backlog
   no larger at the end than at the start. A plan that is not stable
   does not become stable by being run longer.

Stdlib only, offline, deterministic.
"""

# A pass whose setup takes more than this share of the window is a short
# contact in the sense that matters here: most of the pass buys nothing.
SETUP_DOMINANCE_FRACTION = 0.5

# Volumes are products of measured floats, so a store sitting exactly at
# capacity can land a few units in the last place above it. A microbit is
# far below any telemetry accounting resolution and absorbs that
# representation error without relaxing the capacity itself.
VOLUME_TOLERANCE_BITS = 1.0e-6


def _numeric(label, value, minimum=None):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be numeric, got %r" % (label, value))
    if minimum is not None and value < minimum:
        raise ValueError("%s must be >= %r, got %r" % (label, minimum, value))
    return float(value)


def _fraction(label, value):
    number = _numeric(label, value)
    if not 0.0 < number <= 1.0:
        raise ValueError("%s must be in (0, 1], got %r" % (label, value))
    return number


def validate_contact(contact):
    """Validate one contact record and return a normalized copy."""
    if not isinstance(contact, dict):
        raise ValueError("contact must be a mapping")
    contact_id = contact.get("id")
    if not isinstance(contact_id, str) or not contact_id.strip():
        raise ValueError("contact needs a non-empty string id")
    duration = _numeric("contact %s duration_s" % contact_id, contact.get("duration_s"))
    if duration <= 0:
        raise ValueError("contact %s duration_s must be positive" % contact_id)
    rate = _numeric(
        "contact %s channel_rate_bps" % contact_id, contact.get("channel_rate_bps")
    )
    if rate <= 0:
        raise ValueError("contact %s channel_rate_bps must be positive" % contact_id)
    return {
        "id": contact_id,
        "start_time_s": _numeric(
            "contact %s start_time_s" % contact_id, contact.get("start_time_s", 0.0), 0.0
        ),
        "duration_s": duration,
        "setup_time_s": _numeric(
            "contact %s setup_time_s" % contact_id, contact.get("setup_time_s", 0.0), 0.0
        ),
        "channel_rate_bps": rate,
        "coding_rate": _fraction(
            "contact %s coding_rate" % contact_id, contact.get("coding_rate", 1.0)
        ),
        "framing_efficiency": _fraction(
            "contact %s framing_efficiency" % contact_id,
            contact.get("framing_efficiency", 1.0),
        ),
    }


def usable_transfer_time_s(duration_s, setup_time_s):
    """Pass time left for user data once acquisition and setup are paid."""
    duration = _numeric("duration_s", duration_s)
    setup = _numeric("setup_time_s", setup_time_s, 0.0)
    if duration <= 0:
        raise ValueError("duration_s must be positive")
    remaining = duration - setup
    return remaining if remaining > 0.0 else 0.0


def effective_throughput_bps(channel_rate_bps, coding_rate, framing_efficiency):
    """User-data rate once coding and framing have taken their share."""
    rate = _numeric("channel_rate_bps", channel_rate_bps)
    if rate <= 0:
        raise ValueError("channel_rate_bps must be positive")
    return rate * _fraction("coding_rate", coding_rate) * _fraction(
        "framing_efficiency", framing_efficiency
    )


def setup_overhead_fraction(contact):
    """Share of one pass consumed by acquisition and setup."""
    norm = validate_contact(contact)
    share = norm["setup_time_s"] / norm["duration_s"]
    return share if share < 1.0 else 1.0


def deliverable_volume_bits(contact):
    """User-data volume one pass can move, in bits."""
    norm = validate_contact(contact)
    return usable_transfer_time_s(
        norm["duration_s"], norm["setup_time_s"]
    ) * effective_throughput_bps(
        norm["channel_rate_bps"], norm["coding_rate"], norm["framing_efficiency"]
    )


def required_channel_rate_bps(volume_bits, contact):
    """Channel rate one pass would need to move a given volume."""
    norm = validate_contact(contact)
    volume = _numeric("volume_bits", volume_bits, 0.0)
    usable = usable_transfer_time_s(norm["duration_s"], norm["setup_time_s"])
    if usable <= 0.0:
        raise ValueError(
            "contact %s has no usable transfer time; no channel rate can "
            "move a volume through it" % norm["id"]
        )
    return volume / (usable * norm["coding_rate"] * norm["framing_efficiency"])


def contact_findings(contact):
    """Findings about one pass taken on its own."""
    norm = validate_contact(contact)
    findings = []
    if usable_transfer_time_s(norm["duration_s"], norm["setup_time_s"]) <= 0.0:
        findings.append("contact-fully-consumed-by-link-setup")
    elif setup_overhead_fraction(norm) > SETUP_DOMINANCE_FRACTION:
        findings.append("link-setup-consumes-most-of-a-short-contact")
    return findings


def _ordered_contacts(contacts):
    if not isinstance(contacts, list) or not contacts:
        raise ValueError("contacts must be a non-empty list")
    normalized = [validate_contact(c) for c in contacts]
    seen = set()
    for norm in normalized:
        if norm["id"] in seen:
            raise ValueError("duplicate contact id %r" % (norm["id"],))
        seen.add(norm["id"])
    normalized.sort(key=lambda c: (c["start_time_s"], c["id"]))
    previous_end = None
    for norm in normalized:
        if previous_end is not None and norm["start_time_s"] < previous_end:
            raise ValueError(
                "contact %s starts before contact schedule time %r"
                % (norm["id"], previous_end)
            )
        previous_end = norm["start_time_s"] + norm["duration_s"]
    return normalized


def assess_contact_schedule(
    contacts,
    generation_rate_bps,
    initial_backlog_bits=0.0,
    storage_capacity_bits=None,
):
    """Run the clause 5.6.3 assessment over a contact schedule."""
    ordered = _ordered_contacts(contacts)
    generation = _numeric("generation_rate_bps", generation_rate_bps, 0.0)
    backlog = _numeric("initial_backlog_bits", initial_backlog_bits, 0.0)
    capacity = storage_capacity_bits
    if capacity is not None:
        capacity = _numeric("storage_capacity_bits", capacity)
        if capacity <= 0:
            raise ValueError("storage_capacity_bits must be positive")
        if backlog > capacity + VOLUME_TOLERANCE_BITS:
            raise ValueError("initial_backlog_bits exceeds storage_capacity_bits")

    clock = ordered[0]["start_time_s"]
    peak = backlog
    lost = 0.0
    passes = []
    findings = []
    cleared_once = False

    def _apply_capacity(value):
        nonlocal lost
        if capacity is not None and value > capacity + VOLUME_TOLERANCE_BITS:
            lost += value - capacity
            if "onboard-storage-overflowed-before-a-contact" not in findings:
                findings.append("onboard-storage-overflowed-before-a-contact")
            return capacity
        return value

    for norm in ordered:
        backlog = _apply_capacity(backlog + generation * (norm["start_time_s"] - clock))
        at_start = backlog
        generated = generation * norm["duration_s"]
        deliverable = deliverable_volume_bits(norm)
        delivered = at_start + generated
        if delivered > deliverable:
            delivered = deliverable
        backlog = at_start + generated - delivered
        if backlog < 0.0:
            backlog = 0.0
        backlog = _apply_capacity(backlog)
        if backlog <= VOLUME_TOLERANCE_BITS:
            cleared_once = True
        if backlog > peak:
            peak = backlog
        if at_start > peak:
            peak = at_start
        pass_findings = contact_findings(norm)
        for finding in pass_findings:
            if finding not in findings:
                findings.append(finding)
        passes.append(
            {
                "id": norm["id"],
                "usable_time_s": usable_transfer_time_s(
                    norm["duration_s"], norm["setup_time_s"]
                ),
                "setup_overhead_fraction": setup_overhead_fraction(norm),
                "deliverable_bits": deliverable,
                "delivered_bits": delivered,
                "backlog_before_bits": at_start,
                "backlog_after_bits": backlog,
                "findings": pass_findings,
            }
        )
        clock = norm["start_time_s"] + norm["duration_s"]

    stable = backlog <= _numeric("initial_backlog_bits", initial_backlog_bits, 0.0) + VOLUME_TOLERANCE_BITS
    if not stable:
        findings.append("backlog-grows-across-the-contact-plan")
    return {
        "contacts": passes,
        "final_backlog_bits": backlog,
        "peak_backlog_bits": peak,
        "lost_bits": lost,
        "store_cleared_at_least_once": cleared_once,
        "backlog_stable": stable,
        "findings": findings,
        "compliant": not findings,
    }
