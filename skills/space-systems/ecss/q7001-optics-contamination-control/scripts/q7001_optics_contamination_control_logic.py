"""Molecular deposition budgeting for sensitive optical surfaces.

Anchor: ECSS-Q-ST-70-01C, the sensitive-hardware provisions that make optics
the most stringently controlled contamination receiver on a spacecraft.
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the optical receiver: its area, the end-of-life molecular
   deposition budget it was allocated, and the throughput loss its science or
   pointing performance can absorb.
2. Apportion that single end-of-life budget across the declared contributing
   sources (materials outgassing, thruster plume backflow, venting, handling
   residue) in proportion to a declared weight, so each source owns a number
   it can be verified against.
3. Predict what each source actually deposits: the fraction of its emitted
   mass that reaches the receiver is the geometric view factor, and the
   fraction of what arrives that stays is the sticking coefficient, which is a
   strong function of receiver temperature and is read from a tabulated curve.
4. Convert the accumulated areal mass into a condensed film thickness through
   the film density, and the thickness into a transmittance through an
   absorption coefficient, over the number of contaminated optical surfaces in
   the path.
5. Compare the accumulated deposition with the budget and the predicted
   throughput loss with the allowable loss, and report every source whose
   prediction overruns its own allocation.
"""

import math

__all__ = [
    "BUDGET_TOLERANCE_NG_CM2",
    "LOSS_TOLERANCE",
    "NG_CM2_TO_NM_UNIT_DENSITY",
    "apportion_budget",
    "accumulate_deposition",
    "assess_optics_contamination",
    "film_thickness_nm",
    "interpolate_table",
    "source_deposition_ng_cm2",
    "sticking_coefficient_at",
    "throughput_loss_fraction",
    "transmittance",
    "validate_receiver",
    "validate_source",
]

# A deposition total and its budget are built from the same multiplications in
# a different order; an exactly-on-budget case can land a few ULP either side.
BUDGET_TOLERANCE_NG_CM2 = 1e-9

# Same argument for the transmittance comparison, which runs through exp().
LOSS_TOLERANCE = 1e-12

# 1 ng/cm^2 spread at unit density is 1e-9 cm thick, i.e. 0.01 nm.
NG_CM2_TO_NM_UNIT_DENSITY = 0.01

_SOURCE_KEYS = (
    "name",
    "outgassing_rate_g_per_s",
    "view_factor",
    "duration_s",
)


def _positive(value, label):
    """Return value as a strictly positive finite float."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    if number <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return number


def _non_negative(value, label):
    """Return value as a non-negative finite float."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (label, value))
    return number


def _fraction(value, label):
    """Return value as a finite float in the closed interval [0, 1]."""
    number = _non_negative(value, label)
    if number > 1.0:
        raise ValueError("%s must not exceed 1, got %r" % (label, value))
    return number


def interpolate_table(table, x, name="table"):
    """Linearly interpolate a strictly increasing table at x; no extrapolation."""
    if not isinstance(table, (list, tuple)) or len(table) < 2:
        raise ValueError("%s needs at least two (x, y) points" % name)
    points = []
    for index, item in enumerate(table):
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            raise ValueError("%s[%d] must be an (x, y) pair" % (name, index))
        abscissa = _positive(item[0], "%s[%d] abscissa" % (name, index))
        ordinate = _fraction(item[1], "%s[%d] ordinate" % (name, index))
        points.append((abscissa, ordinate))
    for index in range(1, len(points)):
        if points[index][0] <= points[index - 1][0]:
            raise ValueError("%s abscissae must strictly increase (index %d)" % (name, index))
    query = _positive(x, "%s abscissa" % name)
    low, high = points[0][0], points[-1][0]
    if query < low or query > high:
        raise ValueError(
            "%s is tabulated over [%g, %g]; %g is outside it, extrapolation refused"
            % (name, low, high, query)
        )
    for index in range(1, len(points)):
        x0, y0 = points[index - 1]
        x1, y1 = points[index]
        if query <= x1:
            if query == x0:
                return y0
            if query == x1:
                return y1
            return y0 + (query - x0) / (x1 - x0) * (y1 - y0)
    return points[-1][1]


def sticking_coefficient_at(temperature_k, sticking_curve):
    """Return the receiver sticking coefficient at a surface temperature."""
    return interpolate_table(sticking_curve, temperature_k, name="sticking-curve")


def validate_source(source):
    """Return a normalised contributing-source record."""
    if not isinstance(source, dict):
        raise ValueError("each source must be a mapping")
    for key in _SOURCE_KEYS:
        if key not in source:
            raise ValueError("source missing required key '%s'" % key)
    name = source["name"]
    if not isinstance(name, str) or not name.strip():
        raise ValueError("source name must be a non-empty string")
    return {
        "name": name,
        "outgassing_rate_g_per_s": _non_negative(
            source["outgassing_rate_g_per_s"], "outgassing_rate_g_per_s"
        ),
        "view_factor": _fraction(source["view_factor"], "view_factor"),
        "duration_s": _positive(source["duration_s"], "duration_s"),
        "weight": _positive(source.get("weight", 1.0), "weight"),
        "sticking_coefficient": (
            None
            if source.get("sticking_coefficient") is None
            else _fraction(source["sticking_coefficient"], "sticking_coefficient")
        ),
    }


def validate_receiver(receiver):
    """Return a normalised optical-receiver record."""
    if not isinstance(receiver, dict):
        raise ValueError("receiver must be a mapping")
    for key in ("area_cm2", "budget_ng_cm2", "allowable_loss_fraction"):
        if key not in receiver:
            raise ValueError("receiver missing required key '%s'" % key)
    surfaces = receiver.get("surfaces_in_path", 1)
    if not isinstance(surfaces, int) or isinstance(surfaces, bool) or surfaces < 1:
        raise ValueError("surfaces_in_path must be an integer of at least 1")
    return {
        "area_cm2": _positive(receiver["area_cm2"], "area_cm2"),
        "budget_ng_cm2": _positive(receiver["budget_ng_cm2"], "budget_ng_cm2"),
        "allowable_loss_fraction": _fraction(
            receiver["allowable_loss_fraction"], "allowable_loss_fraction"
        ),
        "film_density_g_cm3": _positive(
            receiver.get("film_density_g_cm3", 1.0), "film_density_g_cm3"
        ),
        "absorption_per_nm": _non_negative(
            receiver.get("absorption_per_nm", 0.02), "absorption_per_nm"
        ),
        "temperature_k": (
            None
            if receiver.get("temperature_k") is None
            else _positive(receiver["temperature_k"], "temperature_k")
        ),
        "surfaces_in_path": surfaces,
    }


def apportion_budget(total_budget_ng_cm2, sources):
    """Split one end-of-life budget across sources in proportion to weight."""
    budget = _positive(total_budget_ng_cm2, "total_budget_ng_cm2")
    records = [validate_source(item) for item in sources or []]
    if not records:
        raise ValueError("apportionment needs at least one contributing source")
    names = [record["name"] for record in records]
    if len(set(names)) != len(names):
        raise ValueError("source names must be unique for a traceable allocation")
    total_weight = math.fsum(record["weight"] for record in records)
    return {
        record["name"]: budget * record["weight"] / total_weight for record in records
    }


def source_deposition_ng_cm2(source, receiver_area_cm2, sticking):
    """Return the areal deposition one source lays on the receiver."""
    record = validate_source(source)
    area = _positive(receiver_area_cm2, "receiver_area_cm2")
    retained = _fraction(sticking, "sticking")
    mass_g = (
        record["outgassing_rate_g_per_s"]
        * record["view_factor"]
        * record["duration_s"]
        * retained
    )
    return mass_g / area * 1.0e9


def film_thickness_nm(deposition_ng_cm2, film_density_g_cm3=1.0):
    """Convert an areal deposition into a condensed film thickness."""
    deposition = _non_negative(deposition_ng_cm2, "deposition_ng_cm2")
    density = _positive(film_density_g_cm3, "film_density_g_cm3")
    return deposition * NG_CM2_TO_NM_UNIT_DENSITY / density


def transmittance(thickness_nm, absorption_per_nm, surfaces_in_path=1):
    """Return the transmittance of a contaminated optical path."""
    thickness = _non_negative(thickness_nm, "thickness_nm")
    absorption = _non_negative(absorption_per_nm, "absorption_per_nm")
    if not isinstance(surfaces_in_path, int) or isinstance(surfaces_in_path, bool):
        raise ValueError("surfaces_in_path must be an integer")
    if surfaces_in_path < 1:
        raise ValueError("surfaces_in_path must be at least 1")
    return math.exp(-absorption * thickness * surfaces_in_path)


def throughput_loss_fraction(thickness_nm, absorption_per_nm, surfaces_in_path=1):
    """Return the fractional optical throughput lost to the condensed film."""
    return 1.0 - transmittance(thickness_nm, absorption_per_nm, surfaces_in_path)


def accumulate_deposition(sources, receiver):
    """Return per-source deposition records plus the accumulated total."""
    spec = validate_receiver(receiver)
    records = []
    for item in sources or []:
        source = validate_source(item)
        if source["sticking_coefficient"] is not None:
            retained = source["sticking_coefficient"]
        elif spec["temperature_k"] is not None and receiver.get("sticking_curve"):
            retained = sticking_coefficient_at(
                spec["temperature_k"], receiver["sticking_curve"]
            )
        else:
            raise ValueError(
                "source '%s' has no sticking_coefficient and the receiver declares "
                "no temperature plus sticking_curve to derive one" % source["name"]
            )
        deposition = source_deposition_ng_cm2(item, spec["area_cm2"], retained)
        records.append(
            {
                "name": source["name"],
                "sticking_coefficient": retained,
                "deposition_ng_cm2": deposition,
            }
        )
    if not records:
        raise ValueError("accumulation needs at least one contributing source")
    total = math.fsum(record["deposition_ng_cm2"] for record in records)
    return {"sources": records, "total_ng_cm2": total}


def assess_optics_contamination(spec):
    """Run the full sensitive-optics molecular deposition assessment.

    spec keys: receiver (mapping), sources (sequence of mappings).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("receiver", "sources"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    receiver = validate_receiver(spec["receiver"])
    accumulation = accumulate_deposition(spec["sources"], spec["receiver"])
    allocation = apportion_budget(receiver["budget_ng_cm2"], spec["sources"])
    total = accumulation["total_ng_cm2"]
    thickness = film_thickness_nm(total, receiver["film_density_g_cm3"])
    loss = throughput_loss_fraction(
        thickness, receiver["absorption_per_nm"], receiver["surfaces_in_path"]
    )
    findings = []
    within_budget = total < receiver["budget_ng_cm2"] or math.isclose(
        total, receiver["budget_ng_cm2"], rel_tol=0.0, abs_tol=BUDGET_TOLERANCE_NG_CM2
    )
    if not within_budget:
        findings.append(
            "accumulated deposition %.4f ng/cm2 overruns the end-of-life budget "
            "%.4f ng/cm2" % (total, receiver["budget_ng_cm2"])
        )
    within_loss = loss < receiver["allowable_loss_fraction"] or math.isclose(
        loss, receiver["allowable_loss_fraction"], rel_tol=0.0, abs_tol=LOSS_TOLERANCE
    )
    if not within_loss:
        findings.append(
            "predicted throughput loss %.6f exceeds the allowable %.6f"
            % (loss, receiver["allowable_loss_fraction"])
        )
    overruns = []
    for record in accumulation["sources"]:
        share = allocation[record["name"]]
        if record["deposition_ng_cm2"] > share + BUDGET_TOLERANCE_NG_CM2:
            overruns.append(record["name"])
            findings.append(
                "source '%s' deposits %.4f ng/cm2 against an allocation of %.4f ng/cm2"
                % (record["name"], record["deposition_ng_cm2"], share)
            )
    return {
        "sources": accumulation["sources"],
        "allocation_ng_cm2": allocation,
        "total_deposition_ng_cm2": total,
        "film_thickness_nm": thickness,
        "throughput_loss_fraction": loss,
        "allowable_loss_fraction": receiver["allowable_loss_fraction"],
        "budget_ng_cm2": receiver["budget_ng_cm2"],
        "overrunning_sources": overruns,
        "compliant": within_budget and within_loss and not overruns,
        "findings": findings,
    }
