"""Radiation verification of sensitive Class 2 EEE parts.

Anchor: ECSS-Q-ST-60C clause 5.3.8 -- radiation testing that verifies a
sensitive Class 2 part against the radiation environment the mission declared.
Paraphrased into an implementable procedure; no standard text is reproduced.

What this module decides
------------------------
Which of three things happens to the part: it is accepted on evidence that
already exists, the flight lot is irradiated to produce evidence, or the part
is rejected because no evidence obtainable from it could close the gap.

The Class 2 shape of the question is heritage credit. Evidence that did not come
from the flight lot is still admissible, but it is worth less the further it
sits from the flight material, so each record is credited through a knockdown
factor for its similarity tier:

  same-lot              the flight material itself, credited whole;
  same-diffusion-lot    the same diffusion run, credited nearly whole;
  same-family           the same technology family, credited well below;
  same-technology-node  the same process node only, credited least.

The credited capability is then compared with the declared mission dose as a
radiation design margin. All of that arithmetic is exact rational arithmetic:
dose ratios land on the required margin constantly, and a float ratio that is
one bit above the bound on one platform and one bit below it on another decides
the same part differently on two machines.

Single event effects are a separate veto, not a term in the margin. A
destructive event whose onset threshold sits below the mission requirement
rejects the part however wide the total dose margin is. The one Class 2
relaxation: a verified box-level mitigation may be credited against latch-up,
which a current limiter can genuinely contain, and against nothing else --
burnout and gate rupture destroy the die before any protection outside it acts.
"""

from fractions import Fraction

__all__ = [
    "RADIATION_CATEGORIES",
    "TIER_ORDER",
    "DEFAULT_HERITAGE_CREDIT",
    "DEFAULT_REQUIRED_MARGIN",
    "DESTRUCTIVE_EVENT_TYPES",
    "MITIGABLE_EVENT_TYPES",
    "ROUTE_PRECEDENCE",
    "normalize_category",
    "heritage_factor",
    "credited_capability",
    "radiation_design_margin",
    "best_heritage_record",
    "single_event_verdict",
    "assess_radiation_verification",
]

# What the project graded the part as. The category decides which checks run at
# all; a part nobody graded sensitive is not put through either of them.
RADIATION_CATEGORIES = (
    "not-sensitive",
    "dose-sensitive",
    "event-sensitive",
    "dose-and-event-sensitive",
)

# Similarity tiers, closest to the flight material first.
TIER_ORDER = (
    "same-lot",
    "same-diffusion-lot",
    "same-family",
    "same-technology-node",
)

# How much of a record's demonstrated dose survives the distance between the
# material tested and the material flying. Exact rationals, never floats.
DEFAULT_HERITAGE_CREDIT = {
    "same-lot": Fraction(1),
    "same-diffusion-lot": Fraction(9, 10),
    "same-family": Fraction(7, 10),
    "same-technology-node": Fraction(1, 2),
}

# The radiation design margin a Class 2 part owes its declared environment.
DEFAULT_REQUIRED_MARGIN = Fraction(3, 2)

# Events that destroy the part rather than upset it.
DESTRUCTIVE_EVENT_TYPES = frozenset(
    {
        "single-event-latch-up",
        "single-event-burnout",
        "single-event-gate-rupture",
        "single-event-snapback",
    }
)

# The only destructive event a protection outside the die can be credited
# against.
MITIGABLE_EVENT_TYPES = frozenset({"single-event-latch-up"})

# Worst first.
ROUTE_PRECEDENCE = (
    "reject-part",
    "irradiate-flight-lot",
    "accept-on-heritage",
    "no-verification-required",
)


def _text(label, value):
    """Return value as a stripped non-empty string."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip()


def _flag(label, value):
    """Return value as a strict boolean."""
    if not isinstance(value, bool):
        raise ValueError("%s must be true or false, got %r" % (label, value))
    return value


def _rational(label, value):
    """Return value as an exact Fraction, going through decimal text for floats.

    Every dose, threshold and factor enters the arithmetic through here, so no
    comparison in this module depends on which side of the last bit a libm
    happened to land on.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float, Fraction)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            raise ValueError("%s must be finite, got %r" % (label, value))
        return Fraction(str(value))
    return Fraction(value)


def _positive(label, value):
    """Return value as a strictly positive exact Fraction."""
    number = _rational(label, value)
    if number <= 0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return number


def normalize_category(value):
    """Return value as one of the radiation categories the project grades to."""
    name = _text("category", value).lower()
    if name not in RADIATION_CATEGORIES:
        raise ValueError(
            "category must be one of %s, got %r"
            % (", ".join(RADIATION_CATEGORIES), value)
        )
    return name


def heritage_factor(tier, credit_table=None):
    """Return the knockdown factor a similarity tier is credited through."""
    name = _text("tier", tier).lower()
    table = DEFAULT_HERITAGE_CREDIT if credit_table is None else credit_table
    if not isinstance(table, dict) or name not in table:
        raise ValueError("no heritage credit declared for tier %r" % (tier,))
    factor = _rational("credit for %s" % name, table[name])
    if factor <= 0 or factor > 1:
        raise ValueError("heritage credit for %s must lie in 0..1" % name)
    return factor


def credited_capability(demonstrated_dose, tier, credit_table=None):
    """Return the dose a record is worth once its similarity tier is applied."""
    dose = _positive("demonstrated_dose", demonstrated_dose)
    return dose * heritage_factor(tier, credit_table)


def radiation_design_margin(capability_dose, mission_dose):
    """Return the exact ratio of demonstrated capability to declared environment."""
    capability = _positive("capability_dose", capability_dose)
    mission = _positive("mission_dose", mission_dose)
    return capability / mission


def best_heritage_record(records, mission_dose, credit_table=None):
    """Return the record whose credited capability is highest.

    Ties break towards the closer tier, because two records worth the same dose
    are not worth the same confidence.
    """
    if not isinstance(records, (list, tuple)):
        raise ValueError("records must be a sequence of irradiation records")
    mission = _positive("mission_dose", mission_dose)
    best = None
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise ValueError("records[%d] must be a mapping" % index)
        for key in ("tier", "demonstrated_dose"):
            if key not in record:
                raise ValueError("records[%d] missing required key '%s'" % (index, key))
        tier = _text("records[%d] tier" % index, record["tier"]).lower()
        if tier not in TIER_ORDER:
            raise ValueError("records[%d] tier %r is not a similarity tier" % (index, record["tier"]))
        credited = credited_capability(record["demonstrated_dose"], tier, credit_table)
        entry = {
            "reference": record.get("reference", "record[%d]" % index),
            "tier": tier,
            "tier_rank": TIER_ORDER.index(tier),
            "demonstrated_dose": _positive(
                "records[%d] demonstrated_dose" % index, record["demonstrated_dose"]
            ),
            "credited_dose": credited,
            "margin": credited / mission,
        }
        if best is None:
            best = entry
        elif entry["credited_dose"] > best["credited_dose"]:
            best = entry
        elif entry["credited_dose"] == best["credited_dose"] and entry["tier_rank"] < best["tier_rank"]:
            best = entry
    return best


def single_event_verdict(events, mission_let, mitigations=None):
    """Return the veto and advisory findings the single event data raises.

    A destructive event with an onset below the mission requirement rejects the
    part. A verified box-level mitigation is credited against latch-up and
    against nothing else. A non-destructive event below the requirement is a
    rate question for the design, not a veto here.
    """
    if events is None:
        events = []
    if not isinstance(events, (list, tuple)):
        raise ValueError("events must be a sequence of single event records")
    required_let = _positive("mission_let", mission_let)
    if mitigations is None:
        mitigations = []
    if not isinstance(mitigations, (list, tuple)):
        raise ValueError("mitigations must be a sequence of mitigation records")

    verified = set()
    for index, item in enumerate(mitigations):
        if not isinstance(item, dict):
            raise ValueError("mitigations[%d] must be a mapping" % index)
        if "event_type" not in item:
            raise ValueError("mitigations[%d] missing required key 'event_type'" % index)
        event_type = _text("mitigations[%d] event_type" % index, item["event_type"]).lower()
        if _flag("mitigations[%d] verified" % index, item.get("verified", False)):
            verified.add(event_type)

    veto = []
    advisory = []
    for index, item in enumerate(events):
        if not isinstance(item, dict):
            raise ValueError("events[%d] must be a mapping" % index)
        for key in ("type", "onset_let"):
            if key not in item:
                raise ValueError("events[%d] missing required key '%s'" % (index, key))
        event_type = _text("events[%d] type" % index, item["type"]).lower()
        onset = _positive("events[%d] onset_let" % index, item["onset_let"])
        if onset >= required_let:
            continue
        if event_type not in DESTRUCTIVE_EVENT_TYPES:
            advisory.append(
                "%s onsets at %s below the mission requirement %s; the rate is a design question"
                % (event_type, float(onset), float(required_let))
            )
            continue
        if event_type in MITIGABLE_EVENT_TYPES and event_type in verified:
            advisory.append(
                "%s onsets at %s below the mission requirement %s, credited to a verified mitigation"
                % (event_type, float(onset), float(required_let))
            )
            continue
        veto.append(
            "%s onsets at %s, below the mission requirement %s"
            % (event_type, float(onset), float(required_let))
        )
    return {"veto": veto, "advisory": advisory}


def _worst(routes):
    """Return the worst route earned."""
    for candidate in ROUTE_PRECEDENCE:
        if candidate in routes:
            return candidate
    return "no-verification-required"


def assess_radiation_verification(spec):
    """Return the clause 5.3.8 verification route for one Class 2 part.

    spec keys: category, optional mission_dose, mission_let, records, events,
    mitigations, required_margin and credit_table.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    if "category" not in spec:
        raise ValueError("spec missing required key 'category'")
    category = normalize_category(spec["category"])
    required_margin = _positive(
        "required_margin", spec.get("required_margin", DEFAULT_REQUIRED_MARGIN)
    )
    credit_table = spec.get("credit_table")

    routes = []
    findings = []
    dose = {"checked": False}
    events = {"checked": False, "veto": [], "advisory": []}

    if category in ("dose-sensitive", "dose-and-event-sensitive"):
        if "mission_dose" not in spec:
            raise ValueError("a dose-sensitive part needs a declared mission_dose")
        mission_dose = _positive("mission_dose", spec["mission_dose"])
        records = spec.get("records", [])
        best = best_heritage_record(records, mission_dose, credit_table)
        dose = {
            "checked": True,
            "mission_dose": float(mission_dose),
            "required_margin": float(required_margin),
            "best_record": None,
            "margin": None,
            "margin_met": False,
        }
        if best is None:
            routes.append("irradiate-flight-lot")
            findings.append(
                "no irradiation record exists for the part; the flight lot owes its own test"
            )
        else:
            met = best["margin"] >= required_margin
            dose["best_record"] = best["reference"]
            dose["tier"] = best["tier"]
            dose["credited_dose"] = float(best["credited_dose"])
            dose["margin"] = float(best["margin"])
            dose["margin_met"] = met
            if met:
                routes.append("accept-on-heritage")
                findings.append(
                    "%s credited at the %s tier gives a margin of %s against the required %s"
                    % (
                        best["reference"],
                        best["tier"],
                        float(best["margin"]),
                        float(required_margin),
                    )
                )
            elif best["tier"] == "same-lot":
                routes.append("reject-part")
                findings.append(
                    "the flight lot itself demonstrates a margin of %s against the required %s; no further irradiation of it can close that"
                    % (float(best["margin"]), float(required_margin))
                )
            else:
                routes.append("irradiate-flight-lot")
                findings.append(
                    "best evidence is %s at the %s tier, a margin of %s against the required %s; the flight lot owes its own test"
                    % (
                        best["reference"],
                        best["tier"],
                        float(best["margin"]),
                        float(required_margin),
                    )
                )

    if category in ("event-sensitive", "dose-and-event-sensitive"):
        if "mission_let" not in spec:
            raise ValueError("an event-sensitive part needs a declared mission_let")
        verdict = single_event_verdict(
            spec.get("events"), spec["mission_let"], spec.get("mitigations")
        )
        events = {
            "checked": True,
            "mission_let": float(_positive("mission_let", spec["mission_let"])),
            "veto": verdict["veto"],
            "advisory": verdict["advisory"],
        }
        findings.extend(verdict["veto"])
        findings.extend(verdict["advisory"])
        if verdict["veto"]:
            routes.append("reject-part")
        elif not spec.get("events"):
            routes.append("irradiate-flight-lot")
            findings.append(
                "no single event data exists for the part; the flight lot owes its own test"
            )

    if category == "not-sensitive":
        findings.append(
            "part is not graded radiation sensitive; clause 5.3.8 raises no test"
        )

    return {
        "category": category,
        "dose": dose,
        "events": events,
        "route": _worst(routes),
        "findings": findings,
    }
