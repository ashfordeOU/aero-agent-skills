"""Single failure tolerance of a shared undervoltage protection.

Anchor: ECSS-E-ST-20-20C clause 5.2.5.3.1 (an undervoltage protection common
to several current limiters has to survive any single point failure).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
The shared protection is modelled as an ordered chain of stages -- bus
sensing, comparison, voting, trip distribution -- each stage holding a set of
named units and a k-of-n vote, and each stage serving either every limiter or
a named subset of them. A unit identifier may appear in more than one stage;
that is how shared hardware and cross-strapping are expressed, and the single
failure walk removes such a unit from every stage it appears in at once.

Two failure directions are walked, because tolerating one is not tolerating
the other:

* loss of protection -- one unit is removed; a stage still works when at least
  k of its surviving units remain, and a limiter stays protected only while
  every stage serving it works. Any limiter left unprotected is a single point
  failure of the passive kind.
* spurious trip -- one unit fails active and commands a trip on its own. Its
  stage passes that command on when a single active input satisfies the vote,
  and the healthy downstream stages then forward what looks to them like a
  legitimate trip. Any limiter switched off that way is a single point failure
  of the active kind.

An architecture is single failure tolerant only when neither walk finds a
point, which in practice means every stage votes at least two of at least
three. The scope of the clause is also reported: a protection serving fewer
than two limiters is not the shared case the clause addresses.
"""

__all__ = [
    "MIN_SHARED_LIMITERS",
    "validate_architecture",
    "architecture_units",
    "stage_limiters",
    "stage_functional",
    "protected_limiters",
    "loss_single_points",
    "spurious_single_points",
    "assess_centralised_protection",
]

# Below this many served limiters the protection is dedicated, not shared, and
# the clause's centralised case does not apply.
MIN_SHARED_LIMITERS = 2


def _validate_identifier(value, label):
    """Return a non-empty identifier string."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    text = value.strip()
    if not text:
        raise ValueError("%s must not be empty" % label)
    return text


def validate_architecture(spec):
    """Return the architecture as (served_limiters, stages), or raise.

    spec keys: served_limiters (sequence of names), stages (sequence of
    mappings with name, units, vote and optional serves).
    """
    if not isinstance(spec, dict):
        raise ValueError("architecture spec must be a mapping")
    for key in ("served_limiters", "stages"):
        if key not in spec:
            raise ValueError("architecture spec missing required key '%s'" % key)

    raw_limiters = spec["served_limiters"]
    if not isinstance(raw_limiters, (list, tuple)) or not raw_limiters:
        raise ValueError("served_limiters must be a non-empty sequence")
    limiters = []
    for i, item in enumerate(raw_limiters):
        name = _validate_identifier(item, "served_limiters[%d]" % i)
        if name in limiters:
            raise ValueError("served limiter %r is listed twice" % name)
        limiters.append(name)

    raw_stages = spec["stages"]
    if not isinstance(raw_stages, (list, tuple)) or not raw_stages:
        raise ValueError("stages must be a non-empty sequence")
    stages = []
    seen_stage_names = set()
    for i, item in enumerate(raw_stages):
        if not isinstance(item, dict):
            raise ValueError("stages[%d] must be a mapping" % i)
        for key in ("name", "units", "vote"):
            if key not in item:
                raise ValueError("stages[%d] missing required key '%s'" % (i, key))
        stage_name = _validate_identifier(item["name"], "stages[%d]['name']" % i)
        if stage_name in seen_stage_names:
            raise ValueError("stage name %r is used twice" % stage_name)
        seen_stage_names.add(stage_name)

        raw_units = item["units"]
        if not isinstance(raw_units, (list, tuple)) or not raw_units:
            raise ValueError("stage %r needs a non-empty unit list" % stage_name)
        units = []
        for j, unit in enumerate(raw_units):
            unit_name = _validate_identifier(unit, "stage %r units[%d]" % (stage_name, j))
            if unit_name in units:
                raise ValueError(
                    "unit %r is listed twice inside stage %r" % (unit_name, stage_name)
                )
            units.append(unit_name)

        vote = item["vote"]
        if not isinstance(vote, int) or isinstance(vote, bool):
            raise ValueError("stage %r vote must be an integer" % stage_name)
        if vote < 1:
            raise ValueError("stage %r vote must be at least one, got %d" % (stage_name, vote))
        if vote > len(units):
            raise ValueError(
                "stage %r votes %d of %d units, which can never be met"
                % (stage_name, vote, len(units))
            )

        serves = item.get("serves")
        if serves is None:
            served = list(limiters)
        else:
            if not isinstance(serves, (list, tuple)) or not serves:
                raise ValueError("stage %r 'serves' must be a non-empty sequence" % stage_name)
            served = []
            for j, target in enumerate(serves):
                target_name = _validate_identifier(
                    target, "stage %r serves[%d]" % (stage_name, j)
                )
                if target_name not in limiters:
                    raise ValueError(
                        "stage %r serves unknown limiter %r" % (stage_name, target_name)
                    )
                if target_name not in served:
                    served.append(target_name)
        stages.append(
            {"name": stage_name, "units": units, "vote": vote, "serves": served}
        )
    return (limiters, stages)


def architecture_units(stages):
    """Return every distinct unit identifier, in first-seen order."""
    units = []
    for stage in stages:
        for unit in stage["units"]:
            if unit not in units:
                units.append(unit)
    return units


def stage_limiters(stages, limiter):
    """Return the stages that serve one limiter."""
    return [stage for stage in stages if limiter in stage["serves"]]


def stage_functional(stage, failed_units):
    """Return True when enough of the stage's units survive the failure set."""
    survivors = [unit for unit in stage["units"] if unit not in failed_units]
    return len(survivors) >= stage["vote"]


def protected_limiters(limiters, stages, failed_units=()):
    """Return the limiters whose whole serving chain still works."""
    failed = set(failed_units)
    protected = []
    for limiter in limiters:
        serving = stage_limiters(stages, limiter)
        if not serving:
            continue
        if all(stage_functional(stage, failed) for stage in serving):
            protected.append(limiter)
    return protected


def loss_single_points(limiters, stages):
    """Return every unit whose loss leaves at least one limiter unprotected."""
    points = []
    baseline = set(protected_limiters(limiters, stages))
    for unit in architecture_units(stages):
        remaining = set(protected_limiters(limiters, stages, {unit}))
        lost = [name for name in limiters if name in baseline and name not in remaining]
        if lost:
            points.append(
                {
                    "unit": unit,
                    "stages": [s["name"] for s in stages if unit in s["units"]],
                    "limiters_lost": lost,
                }
            )
    return points


def spurious_single_points(limiters, stages):
    """Return every unit that can command a trip on its own.

    A unit failing active satisfies its own stage's vote when that vote is one;
    the healthy stages downstream of it then forward a command they cannot
    tell from a real one, so every limiter the stage serves is switched off.
    """
    points = []
    for unit in architecture_units(stages):
        tripped = []
        origins = []
        for stage in stages:
            if unit not in stage["units"]:
                continue
            if stage["vote"] > 1:
                continue
            origins.append(stage["name"])
            for limiter in stage["serves"]:
                if limiter not in tripped:
                    tripped.append(limiter)
        if tripped:
            points.append(
                {
                    "unit": unit,
                    "stages": origins,
                    "limiters_tripped": [name for name in limiters if name in tripped],
                }
            )
    return points


def assess_centralised_protection(spec):
    """Grade a shared undervoltage protection against clause 5.2.5.3.1."""
    limiters, stages = validate_architecture(spec)

    findings = []
    unserved = [name for name in limiters if not stage_limiters(stages, name)]
    if unserved:
        findings.append(
            "no protection stage serves %s" % ", ".join(unserved)
        )

    centralised = len(limiters) >= MIN_SHARED_LIMITERS
    if not centralised:
        findings.append(
            "protection serves %d limiter; the clause addresses a protection "
            "shared by several, so this case is graded for information"
            % len(limiters)
        )

    loss = loss_single_points(limiters, stages)
    spurious = spurious_single_points(limiters, stages)
    for point in loss:
        findings.append(
            "loss of %s (stage %s) leaves %s unprotected"
            % (
                point["unit"],
                "/".join(point["stages"]),
                ", ".join(point["limiters_lost"]),
            )
        )
    for point in spurious:
        findings.append(
            "%s failing active at stage %s trips %s on its own"
            % (
                point["unit"],
                "/".join(point["stages"]),
                ", ".join(point["limiters_tripped"]),
            )
        )

    tolerant = not loss and not spurious and not unserved
    return {
        "served_limiters": limiters,
        "centralised": centralised,
        "stage_count": len(stages),
        "unit_count": len(architecture_units(stages)),
        "unserved_limiters": unserved,
        "loss_single_points": loss,
        "spurious_single_points": spurious,
        "single_failure_tolerant": tolerant,
        "verdict": "compliant" if tolerant else "non-compliant",
        "findings": findings,
    }
