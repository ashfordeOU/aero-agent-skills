"""Support of allowables derivation from metallic mechanical test data.

Anchor: ECSS-Q-ST-70-45 interface clause (the mechanical test data generated
under it is what ECSS-E-ST-32-08C design allowables and the metallic materials
properties assessment of the 32 series are derived from). Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Take the basis asked for -- an A-basis value that essentially all of the
   population is expected to exceed, a B-basis value that most of it is
   expected to exceed, or a specification minimum that is asserted rather
   than derived -- and read the preconditions that basis carries.
2. Check the population against those preconditions: how many valid
   specimens, how many distinct heats, and how many specimens the thinnest
   heat contributes, because a set dominated by one melt describes that melt.
3. Check that the heats may be pooled at all, by comparing the worst heat
   mean against the grand mean in units of the WITHIN-heat pooled scatter. The
   total scatter is the wrong yardstick here: an offset heat inflates it and
   then measures itself against its own inflation, so a heat far enough out to
   be a separate population reads as agreeing with the set.
4. Compute the one-sided tolerance-limit value as the mean less the basis
   factor times the sample standard deviation, the factor being interpolated
   from a tabulated curve against sample size and never extrapolated below it.
5. Return the supportable basis, downgrading when the preconditions of the
   requested basis are not met, together with every finding that drove it.
"""

import math

__all__ = [
    "BASIS_KINDS",
    "MIN_SPECIMENS",
    "MIN_HEATS",
    "MIN_SPECIMENS_PER_HEAT",
    "POOLING_LIMIT_SIGMA",
    "A_BASIS_FACTORS",
    "B_BASIS_FACTORS",
    "basis_kinds",
    "sample_statistics",
    "tolerance_factor",
    "heat_census",
    "within_heat_pooled_sd",
    "pooling_check",
    "basis_value",
    "supportable_basis",
    "assess_allowables_support",
]

# Bases in decreasing order of the evidence they demand.
BASIS_KINDS = ("a", "b", "s")

# Specimen, heat and per-heat minima each basis carries.
MIN_SPECIMENS = {"a": 15, "b": 10, "s": 1}
MIN_HEATS = {"a": 3, "b": 3, "s": 1}
MIN_SPECIMENS_PER_HEAT = {"a": 3, "b": 2, "s": 1}

# A heat mean further than this many pooled standard deviations from the grand
# mean is a separate population; the set may not be pooled into one allowable.
POOLING_LIMIT_SIGMA = 2.5

# One-sided normal tolerance-limit factors against sample size. Tabulated and
# interpolated rather than computed, so the same factor comes out on every
# platform instead of depending on how a library rounds its inverse normal.
A_BASIS_FACTORS = (
    (10, 3.981),
    (15, 3.520),
    (20, 3.295),
    (25, 3.158),
    (30, 3.064),
    (40, 2.941),
    (50, 2.863),
    (75, 2.754),
    (100, 2.684),
    (200, 2.570),
)

B_BASIS_FACTORS = (
    (10, 2.355),
    (15, 2.068),
    (20, 1.926),
    (25, 1.838),
    (30, 1.778),
    (40, 1.697),
    (50, 1.646),
    (75, 1.571),
    (100, 1.527),
    (200, 1.450),
)

_FACTOR_TABLES = {"a": A_BASIS_FACTORS, "b": B_BASIS_FACTORS}


def basis_kinds():
    """Return the bases this assessment knows, strongest first."""
    return tuple(BASIS_KINDS)


def _clean_basis(value):
    """Return a validated basis token."""
    if not isinstance(value, str):
        raise ValueError("basis must be a string, got %r" % (value,))
    token = value.strip().lower()
    if token not in BASIS_KINDS:
        raise ValueError(
            "unknown basis %r; known bases are %s" % (value, ", ".join(BASIS_KINDS))
        )
    return token


def _clean_token(value, label):
    """Return a non-empty lowercase token, raising on anything else."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    token = value.strip().lower()
    if not token:
        raise ValueError("%s must not be blank" % label)
    return token


def _finite(value, label):
    """Return a finite float, raising on anything else."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    return number


def sample_statistics(values):
    """Return the count, mean and sample standard deviation of a population."""
    if not isinstance(values, (list, tuple)) or len(values) < 2:
        raise ValueError("values must be a sequence of at least two measurements")
    cleaned = []
    for index, value in enumerate(values):
        number = _finite(value, "values[%d]" % index)
        if number <= 0.0:
            raise ValueError("values[%d] must be positive, got %g" % (index, number))
        cleaned.append(number)
    total = 0.0
    for value in cleaned:
        total += value
    mean = total / len(cleaned)
    squares = 0.0
    for value in cleaned:
        squares += (value - mean) ** 2
    return {
        "count": len(cleaned),
        "mean": mean,
        "standard_deviation": math.sqrt(squares / (len(cleaned) - 1)),
        "minimum": min(cleaned),
        "maximum": max(cleaned),
    }


def tolerance_factor(basis, sample_size):
    """Return the one-sided tolerance-limit factor for a basis and sample size."""
    token = _clean_basis(basis)
    if token == "s":
        raise ValueError("a specification-minimum basis is asserted, not derived from a factor")
    if not isinstance(sample_size, int) or isinstance(sample_size, bool):
        raise ValueError("sample_size must be an integer, got %r" % (sample_size,))
    table = _FACTOR_TABLES[token]
    low = table[0][0]
    high = table[-1][0]
    if sample_size < low:
        raise ValueError(
            "the %s-basis factor curve starts at %d specimens; %d is below it and the "
            "factor is not extrapolated" % (token.upper(), low, sample_size)
        )
    if sample_size >= high:
        return table[-1][1]
    for index in range(1, len(table)):
        n0, k0 = table[index - 1]
        n1, k1 = table[index]
        if sample_size <= n1:
            if sample_size == n0:
                return k0
            if sample_size == n1:
                return k1
            fraction = (sample_size - n0) / float(n1 - n0)
            return k0 + fraction * (k1 - k0)
    return table[-1][1]


def heat_census(records):
    """Return the per-heat specimen counts and values of a data set."""
    if not isinstance(records, (list, tuple)) or not records:
        raise ValueError("records must be a non-empty sequence of specimen records")
    per_heat = {}
    order = []
    values = []
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise ValueError("records[%d] must be a mapping" % index)
        for key in ("heat", "value"):
            if key not in record:
                raise ValueError("records[%d] missing required key '%s'" % (index, key))
        heat = _clean_token(record["heat"], "records[%d]['heat']" % index)
        value = _finite(record["value"], "records[%d]['value']" % index)
        if value <= 0.0:
            raise ValueError("records[%d]['value'] must be positive" % index)
        if heat not in per_heat:
            per_heat[heat] = []
            order.append(heat)
        per_heat[heat].append(value)
        values.append(value)
    counts = [(heat, len(per_heat[heat])) for heat in order]
    return {
        "heats": order,
        "heat_count": len(order),
        "per_heat_values": [(heat, per_heat[heat]) for heat in order],
        "per_heat_counts": counts,
        "thinnest_heat_count": min(count for _, count in counts),
        "values": values,
        "specimen_count": len(values),
    }


def within_heat_pooled_sd(census):
    """Return the scatter inside the heats, with the between-heat offsets removed.

    This is the yardstick a heat offset is measured against. The scatter of the
    whole set is not: an offset heat inflates it, and the offset is then
    compared with a spread it created itself.
    """
    if not isinstance(census, dict) or "per_heat_values" not in census:
        raise ValueError("census must be the mapping returned by heat_census")
    squares = 0.0
    degrees = 0
    for _, values in census["per_heat_values"]:
        if len(values) < 2:
            continue
        total = 0.0
        for value in values:
            total += value
        heat_mean = total / len(values)
        for value in values:
            squares += (value - heat_mean) ** 2
        degrees += len(values) - 1
    if degrees == 0:
        return None
    return math.sqrt(squares / degrees)


def pooling_check(census, limit_sigma=POOLING_LIMIT_SIGMA):
    """Return whether the heats may be pooled into one population."""
    if not isinstance(census, dict) or "per_heat_values" not in census:
        raise ValueError("census must be the mapping returned by heat_census")
    limit = _finite(limit_sigma, "limit_sigma")
    if limit <= 0.0:
        raise ValueError("limit_sigma must be positive, got %g" % limit)
    stats = sample_statistics(census["values"])
    spread = within_heat_pooled_sd(census)
    if spread is None:
        return {
            "poolable": False,
            "worst_heat": None,
            "worst_offset_sigma": None,
            "within_heat_sd": None,
            "limit_sigma": limit,
            "reason": "no heat contributes two specimens, so the within-heat scatter "
                      "the offsets would be judged against does not exist",
        }
    if spread == 0.0:
        offsets_present = any(
            not math.isclose(
                sum(values) / len(values), stats["mean"], rel_tol=0.0, abs_tol=1e-9
            )
            for _, values in census["per_heat_values"]
        )
        return {
            "poolable": not offsets_present,
            "worst_heat": None,
            "worst_offset_sigma": 0.0 if not offsets_present else None,
            "within_heat_sd": 0.0,
            "limit_sigma": limit,
            "reason": None
            if not offsets_present
            else "the heats have no internal scatter but different means",
        }
    worst_heat = None
    worst_offset = 0.0
    for heat, values in census["per_heat_values"]:
        total = 0.0
        for value in values:
            total += value
        heat_mean = total / len(values)
        offset = abs(heat_mean - stats["mean"]) / spread
        if offset > worst_offset:
            worst_offset = offset
            worst_heat = heat
    poolable = worst_offset < limit or math.isclose(
        worst_offset, limit, rel_tol=0.0, abs_tol=1e-9
    )
    return {
        "poolable": poolable,
        "worst_heat": worst_heat,
        "worst_offset_sigma": worst_offset,
        "within_heat_sd": spread,
        "limit_sigma": limit,
        "reason": None,
    }


def basis_value(values, basis):
    """Return the one-sided tolerance-limit value for a basis."""
    token = _clean_basis(basis)
    if token == "s":
        raise ValueError("a specification-minimum basis carries no computed value here")
    stats = sample_statistics(values)
    factor = tolerance_factor(token, stats["count"])
    return {
        "basis": token,
        "count": stats["count"],
        "mean": stats["mean"],
        "standard_deviation": stats["standard_deviation"],
        "factor": factor,
        "value": stats["mean"] - factor * stats["standard_deviation"],
    }


def supportable_basis(census, requested):
    """Return the strongest basis the population supports, at or below the request."""
    token = _clean_basis(requested)
    if not isinstance(census, dict) or "specimen_count" not in census:
        raise ValueError("census must be the mapping returned by heat_census")
    start = BASIS_KINDS.index(token)
    for candidate in BASIS_KINDS[start:]:
        if (
            census["specimen_count"] >= MIN_SPECIMENS[candidate]
            and census["heat_count"] >= MIN_HEATS[candidate]
            and census["thinnest_heat_count"] >= MIN_SPECIMENS_PER_HEAT[candidate]
        ):
            return candidate
    return "s"


def assess_allowables_support(request):
    """Run the full allowables-support assessment on one data set.

    request keys: records (heat/value mappings), requested_basis, optional
    specification_minimum and pooling_limit_sigma.
    """
    if not isinstance(request, dict):
        raise ValueError("request must be a mapping")
    for key in ("records", "requested_basis"):
        if key not in request:
            raise ValueError("request missing required key '%s'" % key)
    requested = _clean_basis(request["requested_basis"])
    census = heat_census(request["records"])
    pooling = pooling_check(census, request.get("pooling_limit_sigma", POOLING_LIMIT_SIGMA))
    findings = []
    if census["specimen_count"] < MIN_SPECIMENS[requested]:
        findings.append(
            "%s-basis needs %d specimens; the set carries %d"
            % (requested.upper(), MIN_SPECIMENS[requested], census["specimen_count"])
        )
    if census["heat_count"] < MIN_HEATS[requested]:
        findings.append(
            "%s-basis needs %d distinct heats; the set carries %d"
            % (requested.upper(), MIN_HEATS[requested], census["heat_count"])
        )
    if census["thinnest_heat_count"] < MIN_SPECIMENS_PER_HEAT[requested]:
        findings.append(
            "%s-basis needs %d specimens from every heat; the thinnest heat contributes %d"
            % (
                requested.upper(),
                MIN_SPECIMENS_PER_HEAT[requested],
                census["thinnest_heat_count"],
            )
        )
    granted = supportable_basis(census, requested)
    if not pooling["poolable"]:
        if pooling["worst_heat"] is None:
            findings.append(
                "the heats cannot be pooled: %s" % pooling["reason"]
            )
        else:
            findings.append(
                "heat %s sits %.2f within-heat standard deviations from the grand mean, "
                "past the %.2f limit; the heats are not one population"
                % (
                    pooling["worst_heat"],
                    pooling["worst_offset_sigma"],
                    pooling["limit_sigma"],
                )
            )
        granted = "s"
    derived = None
    if granted in ("a", "b"):
        derived = basis_value(census["values"], granted)
    elif "specification_minimum" in request:
        minimum = _finite(request["specification_minimum"], "specification_minimum")
        if minimum <= 0.0:
            raise ValueError("specification_minimum must be positive, got %g" % minimum)
        derived = {
            "basis": "s",
            "count": census["specimen_count"],
            "mean": sample_statistics(census["values"])["mean"],
            "standard_deviation": None,
            "factor": None,
            "value": minimum,
        }
    return {
        "requested_basis": requested,
        "granted_basis": granted,
        "downgraded": granted != requested,
        "census": census,
        "pooling": pooling,
        "allowable": derived,
        "findings": findings,
        "supports_request": granted == requested and not findings,
    }
