"""Collected volatile condensable material (CVCM) from a micro-VCM run.

Anchor: ECSS-Q-ST-70-02C, the measurement clause of the thermal-vacuum
outgassing screening test (paraphrased into an implementable procedure;
no standard text is reproduced).

Procedure implemented here:

1. Each specimen is weighed, baked in vacuum at the screening
   temperature, and the volatiles that leave it are condensed on a
   collector plate held far colder. The plate is weighed before and
   after the bake on a microbalance, and the difference is the
   condensed mass.
2. CVCM is that condensed mass expressed as a percentage of the
   specimen mass the run started from -- not of the mass that was lost,
   and not of the mass that came back. Normalising by the wrong mass
   moves the number by the whole water fraction of the specimen.
3. A gain only counts once it is several readability steps of the
   balance. Below that the plate difference is weighing scatter and the
   honest report is a bounded "below the quantification floor", not a
   small positive number carried into a budget.
4. A plate that reads lighter after the bake has lost mass. Inside the
   noise band that is scatter around a zero deposit; beyond it the
   plate was disturbed, contaminated before the tare, or swapped, and
   the specimen owes a re-run.
5. The run is replicated. The reported figure is the mean over the
   replicates, and a spread wider than the reproducibility band of the
   method is a finding against the run, not something the mean hides.

Stdlib only, offline, deterministic.
"""

# Readability of the microbalance the collector plates are weighed on,
# in grams.
BALANCE_READABILITY_G = 1.0e-6

# A plate gain is a quantified number only once it reaches this many
# readability steps; below it the difference is weighing scatter.
QUANTIFICATION_STEPS = 10
QUANTIFICATION_FLOOR_G = BALANCE_READABILITY_G * QUANTIFICATION_STEPS

# A plate reading lighter by no more than this is scatter around a zero
# deposit. Beyond it the plate lost material of its own.
COLLECTOR_LOSS_NOISE_G = 2.0 * BALANCE_READABILITY_G

# Specimen mass window the micro-VCM specimen holders are sized for.
MIN_SPECIMEN_MASS_G = 0.05
MAX_SPECIMEN_MASS_G = 1.0

# Replicates per material in a screening run.
REQUIRED_REPLICATES = 3

# Reproducibility band on the replicate spread, in percentage points of
# CVCM. A wider spread means the specimens were not the same material
# state, not that the mean needs more digits.
REPLICATE_SPREAD_LIMIT_PCT = 0.02

# CVCM is a quotient of two weighings scaled by 100, so a value sitting
# exactly on a band edge can land a few units in the last place past it.
# This tolerance absorbs that representation error only.
PERCENT_TOLERANCE = 1.0e-12

QUANTIFIED = "quantified"
BELOW_FLOOR = "below-quantification-floor"
PLATE_LOST_MASS = "collector-plate-lost-mass"


def _numeric(label, value, minimum=None):
    """Return value as a float, raising on anything that is not a number."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be numeric, got %r" % (label, value))
    if minimum is not None and value < minimum:
        raise ValueError("%s must be >= %r, got %r" % (label, minimum, value))
    return float(value)


def validate_specimen(specimen):
    """Validate one specimen record and return a normalized copy."""
    if not isinstance(specimen, dict):
        raise ValueError("specimen must be a mapping")
    sid = specimen.get("id")
    if not isinstance(sid, str) or not sid.strip():
        raise ValueError("specimen needs a non-empty string id")
    initial = _numeric("specimen %s initial_mass_g" % sid, specimen.get("initial_mass_g"))
    if initial <= 0:
        raise ValueError("specimen %s initial_mass_g must be positive" % sid)
    if initial < MIN_SPECIMEN_MASS_G or initial > MAX_SPECIMEN_MASS_G:
        raise ValueError(
            "specimen %s initial_mass_g %r is outside the holder window "
            "%r..%r g" % (sid, initial, MIN_SPECIMEN_MASS_G, MAX_SPECIMEN_MASS_G)
        )
    before = _numeric("specimen %s collector_before_g" % sid,
                      specimen.get("collector_before_g"), 0.0)
    after = _numeric("specimen %s collector_after_g" % sid,
                     specimen.get("collector_after_g"), 0.0)
    return {
        "id": sid,
        "initial_mass_g": initial,
        "collector_before_g": before,
        "collector_after_g": after,
    }


def collector_gain_g(collector_before_g, collector_after_g):
    """Mass condensed on the collector plate, in grams (may be negative)."""
    before = _numeric("collector_before_g", collector_before_g, 0.0)
    after = _numeric("collector_after_g", collector_after_g, 0.0)
    return after - before


def quantification_floor_percent(specimen_initial_mass_g):
    """Smallest CVCM percentage this balance can quantify for a specimen."""
    initial = _numeric("specimen_initial_mass_g", specimen_initial_mass_g)
    if initial <= 0:
        raise ValueError("specimen_initial_mass_g must be positive")
    return QUANTIFICATION_FLOOR_G / initial * 100.0


def cvcm_percent(collector_before_g, collector_after_g, specimen_initial_mass_g):
    """CVCM as a percentage of the mass the specimen started the run with."""
    initial = _numeric("specimen_initial_mass_g", specimen_initial_mass_g)
    if initial <= 0:
        raise ValueError("specimen_initial_mass_g must be positive")
    gain = collector_gain_g(collector_before_g, collector_after_g)
    return gain / initial * 100.0


def gain_status(collector_gain):
    """Categorize a plate difference as quantified, sub-floor or a loss."""
    gain = _numeric("collector_gain", collector_gain)
    if gain < -COLLECTOR_LOSS_NOISE_G:
        return PLATE_LOST_MASS
    if gain < QUANTIFICATION_FLOOR_G:
        return BELOW_FLOOR
    return QUANTIFIED


def assess_specimen(specimen):
    """CVCM result and findings for one replicate specimen."""
    norm = validate_specimen(specimen)
    gain = collector_gain_g(norm["collector_before_g"], norm["collector_after_g"])
    status = gain_status(gain)
    value = cvcm_percent(
        norm["collector_before_g"], norm["collector_after_g"], norm["initial_mass_g"]
    )
    floor = quantification_floor_percent(norm["initial_mass_g"])
    findings = []
    reported = value
    if status == PLATE_LOST_MASS:
        findings.append("collector-plate-lost-mass-beyond-weighing-noise")
        reported = None
    elif status == BELOW_FLOOR:
        reported = None
    return {
        "id": norm["id"],
        "initial_mass_g": norm["initial_mass_g"],
        "collector_gain_g": gain,
        "gain_status": status,
        "cvcm_percent": value,
        "reported_cvcm_percent": reported,
        "quantification_floor_percent": floor,
        "findings": findings,
        "usable": not findings,
    }


def replicate_spread_percent(values):
    """Spread of the replicate CVCM values, in percentage points."""
    if not isinstance(values, (list, tuple)) or not values:
        raise ValueError("values must be a non-empty sequence")
    numbers = [_numeric("replicate value", v) for v in values]
    return max(numbers) - min(numbers)


def mean_percent(values):
    """Arithmetic mean of the replicate CVCM values."""
    if not isinstance(values, (list, tuple)) or not values:
        raise ValueError("values must be a non-empty sequence")
    numbers = [_numeric("replicate value", v) for v in values]
    return sum(numbers) / len(numbers)


def assess_cvcm_run(specimens):
    """Run the CVCM measurement assessment over one material's replicates."""
    if not isinstance(specimens, list) or not specimens:
        raise ValueError("specimens must be a non-empty list")
    results = []
    seen = set()
    for specimen in specimens:
        result = assess_specimen(specimen)
        if result["id"] in seen:
            raise ValueError("duplicate specimen id %r" % (result["id"],))
        seen.add(result["id"])
        results.append(result)

    findings = []
    if len(results) < REQUIRED_REPLICATES:
        findings.append("fewer-replicates-than-the-method-requires")

    usable = [r for r in results if r["usable"]]
    if not usable:
        findings.append("no-usable-replicate-in-the-run")
        return {
            "specimens": results,
            "mean_cvcm_percent": None,
            "replicate_spread_percent": None,
            "gain_status": None,
            "findings": findings,
            "acceptable": False,
        }

    values = [r["cvcm_percent"] for r in usable]
    spread = replicate_spread_percent(values)
    if spread > REPLICATE_SPREAD_LIMIT_PCT + PERCENT_TOLERANCE:
        findings.append("replicate-spread-beyond-the-reproducibility-band")
    if any(r["gain_status"] == PLATE_LOST_MASS for r in results):
        findings.append("run-contains-a-plate-that-lost-mass")

    all_below = all(r["gain_status"] == BELOW_FLOOR for r in usable)
    return {
        "specimens": results,
        "mean_cvcm_percent": mean_percent(values),
        "replicate_spread_percent": spread,
        "gain_status": BELOW_FLOOR if all_below else QUANTIFIED,
        "findings": findings,
        "acceptable": not findings,
    }
