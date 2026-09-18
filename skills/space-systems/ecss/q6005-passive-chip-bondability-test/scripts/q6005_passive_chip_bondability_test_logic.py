"""Bondability of passive chip terminations, judged by destructive wire pull.

Anchor: ECSS-Q-ST-60-05C clause 8.2.2 (bondability verification -- proving
that wires attached to the terminations of a bare passive chip reach the
strength the assembly needs, on a sample taken before the lot is used).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Read the minimum pull force for the wire actually used from a per-material
   table indexed on wire diameter, interpolating between tabulated diameters
   and refusing a diameter the table does not span.
2. Size the pull sample from the lot: a floor on the number of bonds and on
   the number of distinct chips they are spread over, so one good chip cannot
   carry the lot.
3. Categorize the separation of each pulled bond. A break in the wire says the
   wire gave way before the joint did; a lift at the termination, or the
   termination coming off the chip body, is an interface failure and is not
   redeemed by a high reading.
4. Judge each reading on both counts: force at or above the minimum, and a
   separation that is not an interface failure.
5. Reduce the readings to a mean, a sample standard deviation and a minimum,
   then decide whether the lot is bondable and name what stopped it.
"""

import math

__all__ = [
    "FORCE_TOLERANCE_GF",
    "MIN_BONDS_PULLED",
    "MIN_CHIPS_SAMPLED",
    "MINIMUM_PULL_TABLES",
    "SEPARATION_MODES",
    "INTERFACE_MODES",
    "normalize_wire_material",
    "minimum_pull_force_gf",
    "required_sample",
    "normalize_separation_mode",
    "is_interface_failure",
    "evaluate_pull",
    "pull_statistics",
    "assess_bondability",
]

# Pull forces are read off an interpolated table: a reading sitting exactly on
# the minimum must not be failed by representation error in the interpolation.
FORCE_TOLERANCE_GF = 1e-9

# Floors on the destructive sample, whatever the lot size.
MIN_BONDS_PULLED = 10
MIN_CHIPS_SAMPLED = 4

# (wire diameter in micrometres, minimum pull force in gram-force) per wire
# material. Strictly increasing in diameter; interpolated, never extrapolated.
MINIMUM_PULL_TABLES = {
    "gold": ((18.0, 1.5), (25.0, 3.0), (33.0, 4.5), (50.0, 8.0)),
    "aluminium": ((18.0, 1.2), (25.0, 2.5), (33.0, 3.8), (50.0, 6.5)),
}

SEPARATION_MODES = (
    "wire-break",
    "heel-break",
    "neck-break",
    "bond-lift-at-termination",
    "termination-lift-from-chip",
)

# Modes that condemn the joint or the termination no matter what force was read.
INTERFACE_MODES = ("bond-lift-at-termination", "termination-lift-from-chip")


def _require_text(value, label):
    """Return a lowercased, stripped token, raising on anything else."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    token = value.strip().lower()
    if not token:
        raise ValueError("%s must not be empty" % label)
    return token.replace("_", "-").replace(" ", "-")


def _require_positive(value, label):
    """Return a finite positive float, raising on anything else."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    if number <= 0.0:
        raise ValueError("%s must be positive, got %g" % (label, number))
    return number


def normalize_wire_material(material):
    """Return the canonical bonding wire material."""
    token = _require_text(material, "wire_material")
    aliases = {"au": "gold", "al": "aluminium", "aluminum": "aluminium"}
    token = aliases.get(token, token)
    if token not in MINIMUM_PULL_TABLES:
        raise ValueError(
            "wire material %r has no pull table here (%s)"
            % (material, ", ".join(sorted(MINIMUM_PULL_TABLES)))
        )
    return token


def minimum_pull_force_gf(wire_material, wire_diameter_um):
    """Return the minimum acceptable pull force in gram-force for this wire."""
    material = normalize_wire_material(wire_material)
    diameter = _require_positive(wire_diameter_um, "wire_diameter_um")
    table = MINIMUM_PULL_TABLES[material]
    low, high = table[0][0], table[-1][0]
    if diameter < low or diameter > high:
        raise ValueError(
            "%s wire is tabulated over %g..%g um; %g is outside it, extrapolation refused"
            % (material, low, high, diameter)
        )
    for index in range(1, len(table)):
        d0, f0 = table[index - 1]
        d1, f1 = table[index]
        if diameter <= d1:
            if diameter == d0:
                return f0
            if diameter == d1:
                return f1
            fraction = (diameter - d0) / (d1 - d0)
            return f0 + fraction * (f1 - f0)
    return table[-1][1]


def required_sample(lot_size):
    """Return the bond count and chip count the destructive sample owes."""
    if not isinstance(lot_size, int) or isinstance(lot_size, bool):
        raise ValueError("lot_size must be an integer, got %r" % (lot_size,))
    if lot_size <= 0:
        raise ValueError("lot_size must be positive, got %d" % lot_size)
    chips = min(MIN_CHIPS_SAMPLED, lot_size)
    bonds = max(MIN_BONDS_PULLED, 2 * chips)
    return {"bonds": bonds, "chips": chips}


def normalize_separation_mode(mode):
    """Return the canonical separation mode of a pulled bond."""
    token = _require_text(mode, "separation mode")
    if token not in SEPARATION_MODES:
        raise ValueError(
            "separation mode %r is not one of %s" % (mode, ", ".join(SEPARATION_MODES))
        )
    return token


def is_interface_failure(mode):
    """Return True when the separation happened at an interface, not in the wire."""
    return normalize_separation_mode(mode) in INTERFACE_MODES


def evaluate_pull(force_gf, mode, minimum_gf):
    """Judge one pulled bond on its force and on where it separated."""
    force = _require_positive(force_gf, "force_gf")
    minimum = _require_positive(minimum_gf, "minimum_gf")
    canonical = normalize_separation_mode(mode)
    interface = canonical in INTERFACE_MODES
    strong = force > minimum or math.isclose(
        force, minimum, rel_tol=0.0, abs_tol=FORCE_TOLERANCE_GF
    )
    reasons = []
    if not strong:
        reasons.append("pull force %.3f gf is below the %.3f gf minimum" % (force, minimum))
    if interface:
        reasons.append("separation at %s is an interface failure" % canonical)
    return {
        "force_gf": force,
        "minimum_gf": minimum,
        "mode": canonical,
        "interface_failure": interface,
        "strong_enough": strong,
        "passed": strong and not interface,
        "reasons": tuple(reasons),
    }


def pull_statistics(forces):
    """Return count, mean, sample standard deviation and minimum of the readings."""
    if not isinstance(forces, (list, tuple)) or not forces:
        raise ValueError("forces must be a non-empty sequence of readings")
    values = [_require_positive(value, "pull reading") for value in forces]
    count = len(values)
    mean = sum(values) / count
    if count == 1:
        deviation = 0.0
    else:
        variance = sum((value - mean) ** 2 for value in values) / (count - 1)
        deviation = math.sqrt(variance)
    return {
        "count": count,
        "mean_gf": mean,
        "std_dev_gf": deviation,
        "minimum_gf": min(values),
        "maximum_gf": max(values),
    }


def assess_bondability(spec):
    """Decide whether a passive chip lot is bondable from its pull sample.

    spec keys: lot_size, wire_material, wire_diameter_um, chips_sampled,
    readings (a sequence of {force_gf, mode} mappings).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("lot_size", "wire_material", "wire_diameter_um", "chips_sampled", "readings"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    minimum = minimum_pull_force_gf(spec["wire_material"], spec["wire_diameter_um"])
    plan = required_sample(spec["lot_size"])
    chips = spec["chips_sampled"]
    if not isinstance(chips, int) or isinstance(chips, bool):
        raise ValueError("chips_sampled must be an integer, got %r" % (chips,))
    if chips <= 0:
        raise ValueError("chips_sampled must be positive, got %d" % chips)
    readings = spec["readings"]
    if not isinstance(readings, (list, tuple)) or not readings:
        raise ValueError("readings must be a non-empty sequence")

    results = []
    for index, reading in enumerate(readings):
        if not isinstance(reading, dict):
            raise ValueError("readings[%d] must be a mapping" % index)
        for key in ("force_gf", "mode"):
            if key not in reading:
                raise ValueError("readings[%d] missing '%s'" % (index, key))
        results.append(evaluate_pull(reading["force_gf"], reading["mode"], minimum))

    statistics = pull_statistics([result["force_gf"] for result in results])
    weak = tuple(index for index, result in enumerate(results) if not result["strong_enough"])
    interfaces = tuple(index for index, result in enumerate(results) if result["interface_failure"])

    findings = []
    if len(results) < plan["bonds"]:
        findings.append(
            "sample pulled %d bonds; the plan for this lot is %d"
            % (len(results), plan["bonds"])
        )
    if chips < plan["chips"]:
        findings.append(
            "sample came from %d chips; the plan for this lot is %d" % (chips, plan["chips"])
        )
    if interfaces:
        findings.append(
            "%d of %d pulls separated at an interface" % (len(interfaces), len(results))
        )
    if weak:
        findings.append(
            "%d of %d pulls fell below the %.3f gf minimum" % (len(weak), len(results), minimum)
        )
    return {
        "minimum_gf": minimum,
        "plan": plan,
        "chips_sampled": chips,
        "results": tuple(results),
        "statistics": statistics,
        "weak_indices": weak,
        "interface_indices": interfaces,
        "bondable": not findings,
        "findings": tuple(findings),
        "governing_finding": findings[0] if findings else None,
    }
