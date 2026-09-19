"""Contamination source control in the design: what emits, and what stops it.

Anchor: ECSS-Q-ST-70-01C, the *design* clause -- identifying the contamination
sources a design carries (lubricants, adhesives, outgassing surfaces,
particulate shedders), sizing what each one puts on the surfaces that matter,
and crediting only the control measures that have a verification basis behind
them. Paraphrased into an implementable procedure; no standard text is
reproduced.

Procedure implemented here
--------------------------
1. Scale each source's specific emission rate to its own operating temperature
   through an activation-temperature factor, referenced to the temperature the
   rate was measured at.
2. Turn the emission into what lands on the receiving surface: source area,
   geometric view factor, the share that sticks, exposure duration, and the
   receiving area it is spread over.
3. Credit control measures that apply to the source kind and carry a
   verification basis; refuse credit for a control that has none, and refuse
   the same control credited twice against one source.
4. Total the contributions in their own currency -- deposited areal mass for
   molecular sources, added obscured-area fraction for particulate ones -- and
   compare each total with its allocation.
5. Rank the sources and name the smallest set that accounts for a stated share
   of the total, because that set is where a design change is worth making.
"""

import math

__all__ = [
    "BUDGET_TOLERANCE",
    "CURRENCIES",
    "validate_positive",
    "validate_fraction",
    "temperature_factor",
    "source_emission_per_s",
    "deposited_contribution",
    "control_retention_factor",
    "evaluate_source",
    "rank_sources",
    "dominant_sources",
    "assess_source_control",
]

# A contribution total compared with an allocation is a sum of products; a
# design sized exactly to its allocation must grade as meeting it, so the
# representation error is absorbed here rather than by moving the allocation.
BUDGET_TOLERANCE = 1e-12

# Molecular contributions are a deposited areal mass; particulate ones are an
# added obscured-area fraction. They do not add to each other.
CURRENCIES = ("molecular", "particulate")

SOURCE_KINDS = ("lubricant", "adhesive", "outgassing-surface", "particulate-shedder")


def validate_positive(value, label, allow_zero=False):
    """Return value as a finite positive float (or non-negative if allowed)."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    v = float(value)
    if not math.isfinite(v):
        raise ValueError("%s must be finite" % label)
    if allow_zero:
        if v < 0.0:
            raise ValueError("%s must be non-negative, got %r" % (label, value))
    elif v <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return v


def validate_fraction(value, label, allow_one=True):
    """Return value as a finite fraction in [0, 1] (open at 1 if asked)."""
    v = validate_positive(value, label, allow_zero=True)
    if allow_one:
        if v > 1.0:
            raise ValueError("%s must not exceed 1, got %r" % (label, value))
    elif v >= 1.0:
        raise ValueError("%s must be below 1, got %r" % (label, value))
    return v


def temperature_factor(temperature_k, reference_k, activation_k):
    """Scale an emission rate from its measured temperature to the operating one.

    activation_k is the activation energy expressed as a temperature, so the
    factor is exp(activation_k * (1/reference - 1/temperature)) and rises with
    source temperature. Composing two steps equals the single step between the
    end temperatures, which is the property the caller can rely on.
    """
    t = validate_positive(temperature_k, "temperature_k")
    ref = validate_positive(reference_k, "reference_k")
    act = validate_positive(activation_k, "activation_k", allow_zero=True)
    return math.exp(act * (1.0 / ref - 1.0 / t))


def source_emission_per_s(specific_rate, area_m2, temp_factor=1.0):
    """Return the total emission rate of a source at its own temperature."""
    rate = validate_positive(specific_rate, "specific_rate", allow_zero=True)
    area = validate_positive(area_m2, "area_m2")
    factor = validate_positive(temp_factor, "temp_factor")
    return rate * area * factor


def deposited_contribution(emission_per_s, view_factor, capture_fraction,
                           duration_s, receiver_area_m2):
    """Return what an emission rate leaves on the receiving surface per unit area."""
    emission = validate_positive(emission_per_s, "emission_per_s", allow_zero=True)
    view = validate_fraction(view_factor, "view_factor")
    capture = validate_fraction(capture_fraction, "capture_fraction")
    duration = validate_positive(duration_s, "duration_s", allow_zero=True)
    receiver = validate_positive(receiver_area_m2, "receiver_area_m2")
    return emission * view * capture * duration / receiver


def control_retention_factor(source_kind, controls):
    """Return the share of a source's contribution that survives its controls.

    Each control: name, applies_to (sequence of source kinds), effectiveness in
    [0, 1), verified (bool). An unverified control earns no credit; the same
    control may not be credited twice against one source.
    """
    if source_kind not in SOURCE_KINDS:
        raise ValueError("source kind %r must be one of %s" % (source_kind, list(SOURCE_KINDS)))
    if controls is None:
        controls = []
    if not isinstance(controls, (list, tuple)):
        raise ValueError("controls must be a sequence")
    retention = 1.0
    credited = []
    findings = []
    seen = set()
    for i, control in enumerate(controls):
        if not isinstance(control, dict):
            raise ValueError("controls[%d] must be a mapping" % i)
        for key in ("name", "applies_to", "effectiveness", "verified"):
            if key not in control:
                raise ValueError("controls[%d] missing required key %r" % (i, key))
        name = control["name"]
        if not isinstance(name, str) or not name.strip():
            raise ValueError("controls[%d] name must be a non-empty string" % i)
        if name in seen:
            raise ValueError("control %r is credited twice against one source" % name)
        seen.add(name)
        applies_to = control["applies_to"]
        if not isinstance(applies_to, (list, tuple)) or not applies_to:
            raise ValueError("control %r must name the source kinds it applies to" % name)
        for kind in applies_to:
            if kind not in SOURCE_KINDS:
                raise ValueError("control %r names unknown source kind %r" % (name, kind))
        effectiveness = validate_fraction(
            control["effectiveness"], "effectiveness of %r" % name, allow_one=False
        )
        if not isinstance(control["verified"], bool):
            raise ValueError("control %r verified flag must be a boolean" % name)
        if source_kind not in applies_to:
            continue
        if not control["verified"]:
            findings.append(
                "control %r is claimed against a %s source with no verification "
                "basis; no credit taken" % (name, source_kind)
            )
            continue
        retention *= 1.0 - effectiveness
        credited.append(name)
    return {"retention": retention, "credited": credited, "findings": findings}


def evaluate_source(source, controls=None):
    """Return the controlled contribution of one contamination source.

    source keys: name, kind, currency, specific_rate, area_m2, view_factor,
    capture_fraction, duration_s, receiver_area_m2, and optionally
    temperature_k, reference_k, activation_k.
    """
    if not isinstance(source, dict):
        raise ValueError("source must be a mapping")
    required = ("name", "kind", "currency", "specific_rate", "area_m2",
                "view_factor", "capture_fraction", "duration_s", "receiver_area_m2")
    for key in required:
        if key not in source:
            raise ValueError("source missing required key %r" % key)
    name = source["name"]
    if not isinstance(name, str) or not name.strip():
        raise ValueError("source name must be a non-empty string")
    kind = source["kind"]
    if kind not in SOURCE_KINDS:
        raise ValueError("source %r has unknown kind %r" % (name, kind))
    currency = source["currency"]
    if currency not in CURRENCIES:
        raise ValueError("source %r has unknown currency %r" % (name, currency))
    temperature = source.get("temperature_k")
    reference = source.get("reference_k")
    activation = source.get("activation_k")
    if temperature is None and reference is None and activation is None:
        factor = 1.0
    else:
        if temperature is None or reference is None or activation is None:
            raise ValueError(
                "source %r gives a partial temperature scaling; supply "
                "temperature_k, reference_k and activation_k together" % name
            )
        factor = temperature_factor(temperature, reference, activation)
    emission = source_emission_per_s(source["specific_rate"], source["area_m2"], factor)
    uncontrolled = deposited_contribution(
        emission,
        source["view_factor"],
        source["capture_fraction"],
        source["duration_s"],
        source["receiver_area_m2"],
    )
    credit = control_retention_factor(kind, controls)
    return {
        "name": name,
        "kind": kind,
        "currency": currency,
        "temperature_factor": factor,
        "uncontrolled": uncontrolled,
        "retention": credit["retention"],
        "contribution": uncontrolled * credit["retention"],
        "credited_controls": credit["credited"],
        "findings": credit["findings"],
    }


def rank_sources(records):
    """Return the records ordered by contribution, largest first."""
    if not isinstance(records, (list, tuple)) or not records:
        raise ValueError("records must be a non-empty sequence")
    for record in records:
        if not isinstance(record, dict) or "contribution" not in record:
            raise ValueError("each record must carry a 'contribution'")
    return sorted(records, key=lambda r: (-r["contribution"], r["name"]))


def dominant_sources(records, share=0.8):
    """Return the smallest leading set accounting for the given share of the total."""
    ranked = rank_sources(records)
    target_share = validate_fraction(share, "share")
    total = math.fsum(r["contribution"] for r in ranked)
    if total <= 0.0:
        return []
    target = total * target_share
    running = 0.0
    chosen = []
    for record in ranked:
        chosen.append(record["name"])
        running += record["contribution"]
        if running > target or math.isclose(
            running, target, rel_tol=BUDGET_TOLERANCE, abs_tol=0.0
        ):
            break
    return chosen


def assess_source_control(spec):
    """Run the full source-control step for a design.

    spec keys: sources (sequence), optional controls (sequence), optional
    allocations (mapping currency -> allowed total), optional dominant_share.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    if "sources" not in spec:
        raise ValueError("spec missing required key 'sources'")
    sources = spec["sources"]
    if not isinstance(sources, (list, tuple)) or not sources:
        raise ValueError("spec['sources'] must be a non-empty sequence")
    controls = spec.get("controls")
    records = []
    seen = set()
    for source in sources:
        record = evaluate_source(source, controls)
        if record["name"] in seen:
            raise ValueError("source %r appears twice" % record["name"])
        seen.add(record["name"])
        records.append(record)
    findings = [f for r in records for f in r["findings"]]
    totals = {}
    for currency in CURRENCIES:
        in_currency = [r for r in records if r["currency"] == currency]
        totals[currency] = math.fsum(r["contribution"] for r in in_currency)
    allocations = spec.get("allocations") or {}
    if not isinstance(allocations, dict):
        raise ValueError("spec['allocations'] must be a mapping")
    compliant = True
    for currency, allowed in allocations.items():
        if currency not in CURRENCIES:
            raise ValueError("allocation names unknown currency %r" % (currency,))
        limit = validate_positive(allowed, "allocation for %r" % currency)
        total = totals[currency]
        within = total < limit or math.isclose(
            total, limit, rel_tol=BUDGET_TOLERANCE, abs_tol=0.0
        )
        if not within:
            compliant = False
            findings.append(
                "%s sources contribute %.6g against an allocation of %.6g"
                % (currency, total, limit)
            )
    dominant = {}
    for currency in CURRENCIES:
        in_currency = [r for r in records if r["currency"] == currency]
        dominant[currency] = (
            dominant_sources(in_currency, spec.get("dominant_share", 0.8))
            if in_currency
            else []
        )
    for currency in CURRENCIES:
        for name in dominant[currency]:
            record = [r for r in records if r["name"] == name][0]
            if not record["credited_controls"]:
                findings.append(
                    "source %r dominates the %s total with no credited control "
                    "against it" % (name, currency)
                )
    return {
        "records": records,
        "ranked": [r["name"] for r in rank_sources(records)],
        "totals": totals,
        "dominant": dominant,
        "compliant": compliant and not findings,
        "findings": findings,
    }
