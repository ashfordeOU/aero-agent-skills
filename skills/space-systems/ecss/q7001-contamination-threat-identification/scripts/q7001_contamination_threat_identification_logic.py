"""Life-cycle contamination source and threat identification for space hardware.

Anchor: ECSS-Q-ST-70-01C framework (identifying the contamination sources and
threats a hardware item is exposed to across its life cycle, so the control
plan addresses the ones that actually reach the sensitive surface).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate every declared source against the life-cycle phase list: a source
   with an unknown phase, a negative release rate, an exposure longer than the
   phase or a transport fraction outside zero-to-one is an input error.
2. Turn each source into the arrival it actually produces at the sensitive
   surface: release rate times exposure duration times the transport fraction
   that survives the barriers between them.
3. Total the arrivals per species (particulate, molecular) and per life-cycle
   phase, and rank the sources so the control plan can be written against the
   ones that dominate.
4. Check coverage: every phase the programme declares must carry either an
   identified source or an explicit statement that none exists. A phase with
   neither is a gap in the threat identification, not an absence of threat.
5. Report findings: uncovered phases, a species with no source identified at
   all, a source credited with no transport barrier, and the dominant source
   and phase per species.
"""

import math

__all__ = [
    "LIFE_CYCLE_PHASES",
    "SPECIES",
    "DOMINANCE_FRACTION",
    "validate_non_negative",
    "validate_fraction",
    "validate_phase",
    "validate_species",
    "validate_source",
    "source_arrival",
    "rank_sources",
    "totals_by_species",
    "totals_by_phase",
    "dominant_source",
    "phase_coverage",
    "identify_threats",
]

# The life-cycle phases a contamination threat register is written against,
# in the order hardware passes through them.
LIFE_CYCLE_PHASES = (
    "manufacture",
    "assembly",
    "integration",
    "test",
    "storage",
    "transport",
    "launch-site-processing",
    "ascent",
    "in-orbit",
)

# The two contamination species graded separately throughout.
SPECIES = ("particulate", "molecular")

# A source holding this share of its species total is named as the driver:
# controlling anything else cannot bring the species total down.
DOMINANCE_FRACTION = 0.5


def validate_non_negative(value, label):
    """Return value as a non-negative finite float, or raise ValueError."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    if number < 0.0:
        raise ValueError("%s must be non-negative, got %r" % (label, value))
    return number


def validate_fraction(value, label):
    """Return value as a fraction in the closed unit interval."""
    number = validate_non_negative(value, label)
    if number > 1.0:
        raise ValueError("%s must not exceed unity, got %r" % (label, value))
    return number


def validate_phase(phase):
    """Return a recognised life-cycle phase name, or raise ValueError."""
    if not isinstance(phase, str):
        raise ValueError("phase must be a string")
    name = phase.strip().lower()
    if name not in LIFE_CYCLE_PHASES:
        raise ValueError(
            "unknown life-cycle phase %r; expected one of %s"
            % (phase, ", ".join(LIFE_CYCLE_PHASES))
        )
    return name


def validate_species(species):
    """Return a recognised contamination species, or raise ValueError."""
    if not isinstance(species, str):
        raise ValueError("species must be a string")
    name = species.strip().lower()
    if name not in SPECIES:
        raise ValueError(
            "unknown contamination species %r; expected one of %s"
            % (species, ", ".join(SPECIES))
        )
    return name


def validate_source(source, index=0):
    """Return a validated contamination source record."""
    if not isinstance(source, dict):
        raise ValueError("sources[%d] must be a mapping" % index)
    for key in ("name", "phase", "species", "release_rate", "exposure_duration"):
        if key not in source:
            raise ValueError("sources[%d] missing key '%s'" % (index, key))
    name = source["name"]
    if not isinstance(name, str) or not name.strip():
        raise ValueError("sources[%d] name must be a non-empty string" % index)
    record = {
        "name": name.strip(),
        "phase": validate_phase(source["phase"]),
        "species": validate_species(source["species"]),
        "release_rate": validate_non_negative(
            source["release_rate"], "sources[%d] release_rate" % index
        ),
        "exposure_duration": validate_non_negative(
            source["exposure_duration"], "sources[%d] exposure_duration" % index
        ),
        "transport_fraction": validate_fraction(
            source.get("transport_fraction", 1.0),
            "sources[%d] transport_fraction" % index,
        ),
        "barrier": source.get("barrier"),
    }
    if record["exposure_duration"] == 0.0 and record["release_rate"] > 0.0:
        raise ValueError(
            "sources[%d] releases at a positive rate for zero time; give it a "
            "duration or remove it" % index
        )
    return record


def source_arrival(source):
    """Return what one source actually delivers to the sensitive surface."""
    record = validate_source(source)
    return (
        record["release_rate"]
        * record["exposure_duration"]
        * record["transport_fraction"]
    )


def _validated_sources(sources):
    """Return the validated source list, refusing duplicate names."""
    if not isinstance(sources, (list, tuple)) or not sources:
        raise ValueError("sources must be a non-empty sequence of source mappings")
    records = []
    seen = set()
    for index, source in enumerate(sources):
        record = validate_source(source, index)
        if record["name"] in seen:
            raise ValueError("duplicate source name %r" % record["name"])
        seen.add(record["name"])
        record["arrival"] = source_arrival(record)
        records.append(record)
    return records


def rank_sources(sources, species=None):
    """Return the sources ordered by arrival, largest first, ties by name."""
    records = _validated_sources(sources)
    if species is not None:
        wanted = validate_species(species)
        records = [r for r in records if r["species"] == wanted]
    return sorted(records, key=lambda r: (-r["arrival"], r["name"]))


def totals_by_species(sources):
    """Return the total arrival per contamination species."""
    records = _validated_sources(sources)
    totals = {name: 0.0 for name in SPECIES}
    for record in records:
        totals[record["species"]] += record["arrival"]
    return totals


def totals_by_phase(sources):
    """Return the total arrival per life-cycle phase, over both species."""
    records = _validated_sources(sources)
    totals = {}
    for record in records:
        totals[record["phase"]] = totals.get(record["phase"], 0.0) + record["arrival"]
    return totals


def dominant_source(sources, species):
    """Return the largest source of one species and the share it holds."""
    ranked = rank_sources(sources, species)
    if not ranked:
        return None
    total = math.fsum(record["arrival"] for record in ranked)
    leader = ranked[0]
    fraction = 0.0 if total == 0.0 else leader["arrival"] / total
    return {
        "name": leader["name"],
        "phase": leader["phase"],
        "arrival": leader["arrival"],
        "fraction": fraction,
        "dominant": fraction > DOMINANCE_FRACTION,
    }


def phase_coverage(sources, declared_phases=None, phases_without_sources=None):
    """Return which declared life-cycle phases carry no identified source."""
    records = _validated_sources(sources)
    if declared_phases is None:
        declared = list(LIFE_CYCLE_PHASES)
    else:
        if not isinstance(declared_phases, (list, tuple)) or not declared_phases:
            raise ValueError("declared_phases must be a non-empty sequence")
        declared = [validate_phase(phase) for phase in declared_phases]
    stated_empty = set()
    for phase in phases_without_sources or []:
        stated_empty.add(validate_phase(phase))
    covered = {record["phase"] for record in records}
    unknown = stated_empty & covered
    if unknown:
        raise ValueError(
            "phase(s) %s are declared free of sources but carry identified sources"
            % ", ".join(sorted(unknown))
        )
    uncovered = [p for p in declared if p not in covered and p not in stated_empty]
    return {
        "declared": declared,
        "covered": sorted(covered),
        "stated_without_sources": sorted(stated_empty),
        "uncovered": uncovered,
    }


def identify_threats(spec):
    """Run the full life-cycle contamination threat identification.

    spec keys: sources (sequence of source mappings), optional declared_phases
    and phases_without_sources.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    if "sources" not in spec:
        raise ValueError("spec missing required key 'sources'")
    records = _validated_sources(spec["sources"])
    coverage = phase_coverage(
        spec["sources"],
        spec.get("declared_phases"),
        spec.get("phases_without_sources"),
    )
    species_totals = totals_by_species(spec["sources"])
    phase_totals = totals_by_phase(spec["sources"])
    drivers = {}
    findings = []
    for species in SPECIES:
        driver = dominant_source(spec["sources"], species)
        drivers[species] = driver
        if driver is None:
            findings.append(
                "no %s source identified anywhere in the life cycle; the register "
                "is incomplete rather than the threat absent" % species
            )
        elif driver["dominant"]:
            findings.append(
                "%s arrivals are dominated by %r in the %s phase, holding %.1f%% of "
                "the species total"
                % (species, driver["name"], driver["phase"], 100.0 * driver["fraction"])
            )
    for phase in coverage["uncovered"]:
        findings.append(
            "life-cycle phase %r carries neither an identified source nor a "
            "statement that none exists" % phase
        )
    for record in records:
        if record["transport_fraction"] == 1.0 and not record["barrier"]:
            findings.append(
                "source %r credits no transport barrier between release and the "
                "sensitive surface" % record["name"]
            )
    worst_phase = None
    if phase_totals:
        worst_phase = sorted(
            phase_totals.items(), key=lambda pair: (-pair[1], pair[0])
        )[0][0]
    return {
        "sources": records,
        "ranked": sorted(records, key=lambda r: (-r["arrival"], r["name"])),
        "species_totals": species_totals,
        "phase_totals": phase_totals,
        "driving_phase": worst_phase,
        "drivers": drivers,
        "coverage": coverage,
        "complete": not findings,
        "findings": findings,
    }
