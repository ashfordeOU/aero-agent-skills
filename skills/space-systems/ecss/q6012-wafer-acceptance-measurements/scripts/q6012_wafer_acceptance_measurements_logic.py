"""Electrical acceptance measurements on wafer process monitor structures.

Anchor: ECSS-Q-ST-60-12C clause 10.2.4 (the electrical measurements taken on
the process monitor structures that ride along with the product dies, and the
comparison of those measurements against the foundry's own parameter limits
that decides whether the wafer is accepted).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the foundry parameter limits: each parameter is one-sided or
   two-sided, and it is given exactly the bounds its sidedness needs. A
   maximum-only parameter handed a lower bound is a specification defect, not
   extra information.
2. Validate the per-site measurement set: enough sites to be a wafer map
   rather than an anecdote, no duplicate site, no unknown parameter, and every
   limited parameter measured at every site.
3. Grade each site reading against its bound, inclusively: a reading landing
   exactly on a foundry limit is within the limit, and it is reported as being
   on the limit so the margin is visible.
4. Summarise each parameter across the wafer: the extremes, the median, the
   count of sites within limits and that count as a fraction.
5. Decide the wafer against two independent conditions per parameter - the
   median has to sit within limits, and the within-limit site fraction has to
   reach the required fraction. A wafer can meet one and fail the other.
6. Name the parameters that drove a rejection, so the wafer is not returned
   with a bare verdict the foundry cannot act on.
"""

__all__ = [
    "SIDEDNESS",
    "PARAMETER_KEYS",
    "LIMIT_TOLERANCE",
    "FRACTION_TOLERANCE",
    "DEFAULT_SITE_FRACTION",
    "DEFAULT_MINIMUM_SITES",
    "parameter_titles",
    "parameter_units",
    "parameter_sidedness",
    "validate_limits",
    "validate_sites",
    "site_verdict",
    "median",
    "worst_margin",
    "parameter_summary",
    "wafer_summary",
    "rejecting_parameters",
    "assess_wafer_acceptance",
]

SIDEDNESS = ("two-sided", "minimum", "maximum")

# key, title, unit, sidedness.
_PARAMETER_REGISTRY = (
    ("pinch-off-voltage", "Pinch-off voltage", "V", "two-sided"),
    ("saturated-drain-current", "Saturated drain current", "mA/mm", "minimum"),
    ("peak-transconductance", "Peak transconductance", "mS/mm", "minimum"),
    ("gate-leakage-current", "Gate leakage current", "uA/mm", "maximum"),
    ("gate-drain-breakdown", "Gate to drain breakdown voltage", "V", "minimum"),
    ("sheet-resistance", "Channel sheet resistance", "ohm/sq", "two-sided"),
    ("contact-resistance", "Ohmic contact resistance", "ohm.mm", "maximum"),
)

PARAMETER_KEYS = tuple(entry[0] for entry in _PARAMETER_REGISTRY)
_PARAMETER_INDEX = {key: i for i, key in enumerate(PARAMETER_KEYS)}

# Relative slack applied when deciding whether a reading has crossed a bound.
# A reading landing on the bound is inside it, on either platform.
LIMIT_TOLERANCE = 1e-9

# Absolute slack on the within-limit site fraction, which is a ratio of two
# small integers and can land exactly on the required fraction.
FRACTION_TOLERANCE = 1e-9

DEFAULT_SITE_FRACTION = 0.90
DEFAULT_MINIMUM_SITES = 5


def parameter_titles():
    """Return the parameter registry as an ordered key to title mapping."""
    return {entry[0]: entry[1] for entry in _PARAMETER_REGISTRY}


def parameter_units():
    """Return the unit each registry parameter is measured in."""
    return {entry[0]: entry[2] for entry in _PARAMETER_REGISTRY}


def parameter_sidedness():
    """Return whether each registry parameter is two-sided, minimum or maximum."""
    return {entry[0]: entry[3] for entry in _PARAMETER_REGISTRY}


def _as_number(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number" % label)
    return float(value)


def _bounds_for(sidedness):
    if sidedness == "two-sided":
        return ("lower", "upper")
    if sidedness == "minimum":
        return ("lower",)
    return ("upper",)


def validate_limits(raw):
    """Return the normalised foundry limit set built from raw.

    Each parameter is given exactly the bounds its sidedness calls for; a bound
    the sidedness does not use is refused rather than quietly dropped, because
    a dropped bound turns a real rejection into a pass.
    """
    if not isinstance(raw, dict) or not raw:
        raise ValueError("limits must be a non-empty mapping of parameter to bounds")
    sides = parameter_sidedness()
    limits = {}
    for key, entry in raw.items():
        if not isinstance(key, str):
            raise ValueError("parameter key must be a string")
        token = key.strip().lower()
        if token not in _PARAMETER_INDEX:
            raise ValueError("unknown monitor parameter '%s'" % key)
        if token in limits:
            raise ValueError("parameter '%s' is given limits more than once" % token)
        if not isinstance(entry, dict):
            raise ValueError("limits for '%s' must be a mapping" % token)
        needed = _bounds_for(sides[token])
        for field in entry:
            if field not in ("lower", "upper"):
                raise ValueError(
                    "limits for '%s' carry unknown bound '%s'" % (token, field)
                )
            if field not in needed:
                raise ValueError(
                    "'%s' is a %s parameter and must not be given a '%s' bound"
                    % (token, sides[token], field)
                )
        bounds = {}
        for field in needed:
            if field not in entry:
                raise ValueError(
                    "'%s' is a %s parameter and needs a '%s' bound"
                    % (token, sides[token], field)
                )
            bounds[field] = _as_number(entry[field], "%s %s bound" % (token, field))
        if sides[token] == "two-sided" and not bounds["lower"] < bounds["upper"]:
            raise ValueError("limits for '%s' are inverted or empty" % token)
        bounds["sidedness"] = sides[token]
        limits[token] = bounds
    return limits


def validate_sites(raw, limits, minimum_sites=DEFAULT_MINIMUM_SITES):
    """Return the normalised per-site measurement set built from raw."""
    if not isinstance(limits, dict) or not limits:
        raise ValueError("limits must be a normalised non-empty limit set")
    if isinstance(minimum_sites, bool) or not isinstance(minimum_sites, int):
        raise ValueError("minimum_sites must be an integer")
    if minimum_sites < 1:
        raise ValueError("minimum_sites must be at least 1")
    if not isinstance(raw, (list, tuple)):
        raise ValueError("sites must be a sequence of site measurement records")
    sites = []
    seen = set()
    for entry in raw:
        if not isinstance(entry, dict):
            raise ValueError("each site record must be a mapping")
        for field in entry:
            if field not in ("site", "values"):
                raise ValueError("site record carries unknown field '%s'" % field)
        for field in ("site", "values"):
            if field not in entry:
                raise ValueError("site record missing field '%s'" % field)
        name = entry["site"]
        if not isinstance(name, str) or not name.strip():
            raise ValueError("site name must be a non-empty string")
        name = name.strip()
        if name in seen:
            raise ValueError("site '%s' is measured more than once" % name)
        seen.add(name)
        values = entry["values"]
        if not isinstance(values, dict):
            raise ValueError("site '%s' values must be a mapping" % name)
        normalised = {}
        for key, value in values.items():
            if not isinstance(key, str):
                raise ValueError("parameter key must be a string")
            token = key.strip().lower()
            if token not in _PARAMETER_INDEX:
                raise ValueError("unknown monitor parameter '%s'" % key)
            if token not in limits:
                raise ValueError(
                    "site '%s' measures '%s', which the limit set does not bound"
                    % (name, token)
                )
            normalised[token] = _as_number(value, "%s at site %s" % (token, name))
        for token in limits:
            if token not in normalised:
                raise ValueError(
                    "site '%s' is missing limited parameter '%s'" % (name, token)
                )
        sites.append({"site": name, "values": normalised})
    if len(sites) < minimum_sites:
        raise ValueError(
            "wafer carries %d measured sites, below the minimum of %d"
            % (len(sites), minimum_sites)
        )
    return sites


def site_verdict(value, limit):
    """Return where a single site reading sits against its bound.

    A reading landing on a bound is inside it and is reported as on-limit.
    """
    if not isinstance(limit, dict) or "sidedness" not in limit:
        raise ValueError("limit must be a normalised bound mapping")
    value = _as_number(value, "site reading")
    scale = max(abs(value), 1.0)
    slack = scale * LIMIT_TOLERANCE
    lower = limit.get("lower")
    upper = limit.get("upper")
    if lower is not None and value < lower - slack:
        return "below-minimum"
    if upper is not None and value > upper + slack:
        return "above-maximum"
    if lower is not None and abs(value - lower) <= slack:
        return "on-lower-limit"
    if upper is not None and abs(value - upper) <= slack:
        return "on-upper-limit"
    return "within"


def _is_within(verdict):
    return verdict in ("within", "on-lower-limit", "on-upper-limit")


def median(values):
    """Return the median of a non-empty sequence of numbers."""
    if not isinstance(values, (list, tuple)):
        raise ValueError("values must be a sequence of numbers")
    if not values:
        raise ValueError("median of an empty sample is undefined")
    ordered = sorted(_as_number(v, "sample value") for v in values)
    count = len(ordered)
    middle = count // 2
    if count % 2 == 1:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2.0


def worst_margin(values, limit):
    """Return the smallest distance from any reading to its nearest bound.

    Negative when at least one reading has crossed a bound.
    """
    if not isinstance(values, (list, tuple)) or not values:
        raise ValueError("values must be a non-empty sequence of numbers")
    if not isinstance(limit, dict) or "sidedness" not in limit:
        raise ValueError("limit must be a normalised bound mapping")
    lower = limit.get("lower")
    upper = limit.get("upper")
    margins = []
    for raw in values:
        value = _as_number(raw, "site reading")
        per_reading = []
        if lower is not None:
            per_reading.append(value - lower)
        if upper is not None:
            per_reading.append(upper - value)
        margins.append(min(per_reading))
    return min(margins)


def parameter_summary(key, sites, limits):
    """Return the across-wafer summary for one limited parameter."""
    if key not in limits:
        raise ValueError("parameter '%s' is not in the limit set" % (key,))
    if not isinstance(sites, (list, tuple)) or not sites:
        raise ValueError("sites must be a non-empty normalised site sequence")
    limit = limits[key]
    values = [site["values"][key] for site in sites]
    verdicts = [site_verdict(value, limit) for value in values]
    within = sum(1 for verdict in verdicts if _is_within(verdict))
    mid = median(values)
    return {
        "parameter": key,
        "title": parameter_titles()[key],
        "unit": parameter_units()[key],
        "sidedness": limit["sidedness"],
        "sites": len(values),
        "minimum": min(values),
        "maximum": max(values),
        "median": mid,
        "median_verdict": site_verdict(mid, limit),
        "within_sites": within,
        "within_fraction": within / float(len(values)),
        "worst_margin": worst_margin(values, limit),
        "outlier_sites": [
            site["site"]
            for site, verdict in zip(sites, verdicts)
            if not _is_within(verdict)
        ],
    }


def wafer_summary(sites, limits):
    """Return one summary per limited parameter, in registry order."""
    keys = sorted(limits, key=lambda k: _PARAMETER_INDEX[k])
    return [parameter_summary(key, sites, limits) for key in keys]


def rejecting_parameters(summaries, required_fraction=DEFAULT_SITE_FRACTION):
    """Return the parameters that fail either acceptance condition, with reasons."""
    required_fraction = _as_number(required_fraction, "required_fraction")
    if not 0.0 < required_fraction <= 1.0:
        raise ValueError("required_fraction must sit in (0, 1]")
    if not isinstance(summaries, (list, tuple)):
        raise ValueError("summaries must be a sequence of parameter summaries")
    drivers = []
    for summary in summaries:
        if not isinstance(summary, dict) or "parameter" not in summary:
            raise ValueError("each summary must be a mapping carrying 'parameter'")
        reasons = []
        if not _is_within(summary["median_verdict"]):
            reasons.append(
                "wafer median %s is %s"
                % (summary["median_verdict"].replace("-", " "), summary["unit"])
            )
        if summary["within_fraction"] < required_fraction - FRACTION_TOLERANCE:
            reasons.append(
                "only %d of %d sites sit within limits"
                % (summary["within_sites"], summary["sites"])
            )
        if reasons:
            drivers.append(
                {
                    "parameter": summary["parameter"],
                    "title": summary["title"],
                    "reasons": reasons,
                }
            )
    return drivers


def assess_wafer_acceptance(spec):
    """Run the full clause 10.2.4 wafer acceptance measurement assessment."""
    if not isinstance(spec, dict):
        raise ValueError("acceptance spec must be a mapping")
    required = ("wafer_id", "limits", "sites")
    optional = ("required_site_fraction", "minimum_sites")
    for key in required:
        if key not in spec:
            raise ValueError("acceptance spec missing required key '%s'" % key)
    for key in spec:
        if key not in required + optional:
            raise ValueError("acceptance spec carries unknown key '%s'" % key)
    wafer_id = spec["wafer_id"]
    if not isinstance(wafer_id, str) or not wafer_id.strip():
        raise ValueError("wafer_id must be a non-empty string")
    fraction = _as_number(
        spec.get("required_site_fraction", DEFAULT_SITE_FRACTION),
        "required_site_fraction",
    )
    if not 0.0 < fraction <= 1.0:
        raise ValueError("required_site_fraction must sit in (0, 1]")
    minimum_sites = spec.get("minimum_sites", DEFAULT_MINIMUM_SITES)
    limits = validate_limits(spec["limits"])
    sites = validate_sites(spec["sites"], limits, minimum_sites)
    summaries = wafer_summary(sites, limits)
    drivers = rejecting_parameters(summaries, fraction)
    total_readings = len(sites) * len(limits)
    within_readings = sum(summary["within_sites"] for summary in summaries)
    return {
        "wafer_id": wafer_id.strip(),
        "required_site_fraction": fraction,
        "site_count": len(sites),
        "parameters": summaries,
        "rejecting_parameters": drivers,
        "overall_within_fraction": within_readings / float(total_readings),
        "accepted": not drivers,
        "verdict": "reject" if drivers else "accept",
    }
