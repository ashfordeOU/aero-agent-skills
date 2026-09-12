#!/usr/bin/env python3
"""ECSS-E-ST-20C clause 6.3.2.3 protected frequency band emissions
(paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
electrical engineering standard requires spacecraft emissions to
respect the limits that protect radiometric and communication bands,
with the limits themselves set by the applicable radio standard. This
module implements the checkable part of that clause: a registry of
protected bands and the service each one carries, the per-service
limit, the spectral overlap between an emission and a band, the
in-band power that follows from a uniform power spectral density, the
harmonic series of a carrier with its suppression law, the summation
of every contribution falling in one band, the comparison against the
limit, and the harmonic-sweep depth check. The band edges and limits
shipped here are project-configurable defaults: a mission replaces
them with the values its own radio standard and frequency filing
impose. It does not perform a spectrum measurement, does not design a
filter, and does not run a frequency coordination process.
"""

import math

# Default registry of bands that emissions must protect. Edges are the
# well-known allocations; a project overrides both edges and limits
# from its own radio standard.
PROTECTED_BANDS = (
    {
        "name": "radio_astronomy_1400_1427",
        "f_min_hz": 1.400e9,
        "f_max_hz": 1.427e9,
        "service": "radio_astronomy",
    },
    {
        "name": "radio_astronomy_1610_1614",
        "f_min_hz": 1.6106e9,
        "f_max_hz": 1.6138e9,
        "service": "radio_astronomy",
    },
    {
        "name": "radio_astronomy_2690_2700",
        "f_min_hz": 2.690e9,
        "f_max_hz": 2.700e9,
        "service": "radio_astronomy",
    },
    {
        "name": "passive_radiometry_23600_24000",
        "f_min_hz": 23.600e9,
        "f_max_hz": 24.000e9,
        "service": "passive_radiometry",
    },
    {
        "name": "distress_406_0_406_1",
        "f_min_hz": 406.0e6,
        "f_max_hz": 406.1e6,
        "service": "distress_and_safety",
    },
    {
        "name": "gnss_l1_1559_1610",
        "f_min_hz": 1.559e9,
        "f_max_hz": 1.610e9,
        "service": "gnss_navigation",
    },
    {
        "name": "spacecraft_receive_s_band_2025_2110",
        "f_min_hz": 2.025e9,
        "f_max_hz": 2.110e9,
        "service": "spacecraft_receive",
    },
)

SERVICE_LIMIT_DBM = {
    "radio_astronomy": -80.0,
    "passive_radiometry": -75.0,
    "distress_and_safety": -90.0,
    "gnss_navigation": -85.0,
    "spacecraft_receive": -60.0,
}

REQUIRED_EMISSION_FIELDS = frozenset(
    {"emission_id", "center_hz", "bandwidth_hz", "power_w"}
)

# Default harmonic suppression law, in decibels of power below the
# carrier: a fixed floor plus a term that grows with the order.
HARMONIC_BASE_SUPPRESSION_DB = 40.0

# The sweep has to reach at least this harmonic order before the
# emission case is considered to have looked far enough up the series.
MIN_HARMONIC_ORDER = 5

MILLIWATT_W = 1.0e-3

# Absorbs the representation error of a summed power that is
# mathematically on the limit: a total built from a suppression ratio
# and a sum of contributions can land a few units in the last place
# over. It sits on the comparison only and never relaxes the limit.
POWER_TOLERANCE_DB = 1.0e-9


def categorize_protected_band(band_name, bands=PROTECTED_BANDS):
    """Service a protected band carries: "radio_astronomy",
    "passive_radiometry", "distress_and_safety", "gnss_navigation" or
    "spacecraft_receive". Raises ValueError for a band that is not in
    the registry."""
    for band in bands:
        if band["name"] == band_name:
            return band["service"]
    raise ValueError(
        "unrecognized protected band %r under "
        "E-ST-20C clause 6.3.2.3" % (band_name,)
    )


def service_limit_dbm(service):
    """Emission limit in dBm for a protected service. Raises
    ValueError for a service outside the registry."""
    if service not in SERVICE_LIMIT_DBM:
        raise ValueError("unrecognized protected service %r" % (service,))
    return SERVICE_LIMIT_DBM[service]


def dbm_to_watts(power_dbm):
    """Linear watts for a power in dBm. Any real input is valid."""
    return MILLIWATT_W * (10.0 ** (power_dbm / 10.0))


def watts_to_dbm(power_w):
    """Power in dBm for a linear power in watts. Raises ValueError for
    a non-positive power, which has no decibel representation."""
    if power_w <= 0:
        raise ValueError("power_w must be > 0 to express a power in dBm")
    return 10.0 * math.log10(power_w / MILLIWATT_W)


def service_limit_w(service):
    """Emission limit in watts for a protected service. Raises
    ValueError through service_limit_dbm for an unknown service."""
    return dbm_to_watts(service_limit_dbm(service))


def emission_edges(center_hz, bandwidth_hz):
    """(lower, upper) edge of an emission in hertz. Raises ValueError
    for a non-positive centre frequency or bandwidth, or when the
    lower edge would fall at or below zero."""
    if center_hz <= 0:
        raise ValueError("center_hz must be > 0")
    if bandwidth_hz <= 0:
        raise ValueError("bandwidth_hz must be > 0")
    lower = center_hz - bandwidth_hz / 2.0
    if lower <= 0:
        raise ValueError(
            "emission bandwidth %r is too wide for centre frequency %r"
            % (bandwidth_hz, center_hz)
        )
    return (lower, center_hz + bandwidth_hz / 2.0)


def band_overlap_hz(lower_hz, upper_hz, band):
    """Width in hertz of the intersection between an emission and a
    protected band; zero when they do not meet. Raises ValueError when
    either the emission or the band has inverted edges."""
    if lower_hz > upper_hz:
        raise ValueError("emission edges inverted: %r > %r" % (lower_hz, upper_hz))
    if band["f_min_hz"] > band["f_max_hz"]:
        raise ValueError(
            "protected band %r has inverted edges" % (band.get("name"),)
        )
    overlap = min(upper_hz, band["f_max_hz"]) - max(lower_hz, band["f_min_hz"])
    return overlap if overlap > 0 else 0.0


def in_band_power_w(total_power_w, emission_bw_hz, overlap_hz):
    """Power of an emission that falls inside a protected band, on a
    uniform power spectral density model. An emission wholly inside the
    band contributes all of its power, with no scaling arithmetic to
    round. Raises ValueError for a negative power, a non-positive
    emission bandwidth, a negative overlap, or an overlap wider than
    the emission itself."""
    if total_power_w < 0:
        raise ValueError("total_power_w must be >= 0")
    if emission_bw_hz <= 0:
        raise ValueError("emission_bw_hz must be > 0")
    if overlap_hz < 0:
        raise ValueError("overlap_hz must be >= 0")
    if overlap_hz > emission_bw_hz:
        raise ValueError("overlap_hz cannot exceed the emission bandwidth")
    if overlap_hz == 0:
        return 0.0
    if overlap_hz == emission_bw_hz:
        return total_power_w
    return total_power_w * overlap_hz / emission_bw_hz


def harmonic_frequencies_hz(fundamental_hz, max_order):
    """[(order, frequency), ...] for orders two through max_order.
    Raises ValueError for a non-positive fundamental or an order below
    two, since the first harmonic is the carrier itself."""
    if fundamental_hz <= 0:
        raise ValueError("fundamental_hz must be > 0")
    if max_order < 2:
        raise ValueError("max_order must be >= 2")
    return [(order, order * fundamental_hz) for order in range(2, int(max_order) + 1)]


def harmonic_suppression_db(order, declared_suppression_db=None):
    """Suppression in decibels of power below the carrier for one
    harmonic order. A declared value from the transmitter datasheet
    wins; otherwise the default law is used. Raises ValueError for an
    order below two or a negative declared suppression, which would
    make the harmonic stronger than the carrier."""
    if order < 2:
        raise ValueError("order must be >= 2")
    if declared_suppression_db is not None:
        if declared_suppression_db < 0:
            raise ValueError("declared_suppression_db must be >= 0")
        return float(declared_suppression_db)
    return HARMONIC_BASE_SUPPRESSION_DB + 20.0 * math.log10(order)


def harmonic_power_w(fundamental_power_w, suppression_db):
    """Power in watts of a harmonic, the carrier power reduced by a
    suppression in decibels of power. Raises ValueError for a negative
    carrier power or a negative suppression."""
    if fundamental_power_w < 0:
        raise ValueError("fundamental_power_w must be >= 0")
    if suppression_db < 0:
        raise ValueError("suppression_db must be >= 0")
    return fundamental_power_w / (10.0 ** (suppression_db / 10.0))


def missing_emission_fields(emission):
    """Sorted list of required emission fields that are absent or left
    as None. A named but unfilled row is not a declaration."""
    return sorted(
        field
        for field in REQUIRED_EMISSION_FIELDS
        if field not in emission or emission[field] is None
    )


def emission_contributions(emission, bands=PROTECTED_BANDS):
    """[(band_name, power_w), ...] for every protected band this
    emission reaches. Raises ValueError through the helpers for a bad
    emission or a band with inverted edges."""
    lower, upper = emission_edges(emission["center_hz"], emission["bandwidth_hz"])
    contributions = []
    for band in bands:
        overlap = band_overlap_hz(lower, upper, band)
        if overlap <= 0:
            continue
        contributions.append(
            (
                band["name"],
                in_band_power_w(
                    emission["power_w"], emission["bandwidth_hz"], overlap
                ),
            )
        )
    return contributions


def transmitter_emissions(transmitter):
    """Every emission the transmitter puts on the spectrum: the
    carrier, each harmonic up to the declared sweep order, and each
    well-formed declared spurious product. Raises ValueError through
    the helpers for a bad carrier or sweep order."""
    fundamental_hz = transmitter["fundamental_hz"]
    fundamental_power_w = transmitter["fundamental_power_w"]
    fundamental_bw_hz = transmitter["fundamental_bandwidth_hz"]
    max_order = transmitter["max_harmonic_order"]
    declared = transmitter.get("harmonic_suppression_db", {})
    emissions = [
        {
            "emission_id": "fundamental",
            "center_hz": fundamental_hz,
            "bandwidth_hz": fundamental_bw_hz,
            "power_w": fundamental_power_w,
        }
    ]
    for order, frequency_hz in harmonic_frequencies_hz(fundamental_hz, max_order):
        suppression_db = harmonic_suppression_db(order, declared.get(order))
        emissions.append(
            {
                "emission_id": "harmonic_%d" % order,
                "center_hz": frequency_hz,
                # A harmonic of a modulated carrier is widened by its
                # order, so the occupied bandwidth scales with it.
                "bandwidth_hz": order * fundamental_bw_hz,
                "power_w": harmonic_power_w(fundamental_power_w, suppression_db),
            }
        )
    for spurious in transmitter.get("spurious_emissions", []):
        if not missing_emission_fields(spurious):
            emissions.append(dict(spurious))
    return emissions


def declaration_findings(transmitter):
    """Findings (empty when every declared spurious emission is
    complete) for spurious products missing a required field. An
    incomplete emission carries no power into the summation, so the
    gap has to be reported rather than silently dropped."""
    findings = []
    for index, spurious in enumerate(transmitter.get("spurious_emissions", [])):
        for field in missing_emission_fields(spurious):
            findings.append(
                {
                    "issue": "incomplete_spurious_emission_declaration",
                    "transmitter": transmitter["transmitter_id"],
                    "emission": spurious.get("emission_id", "index_%d" % index),
                    "field": field,
                }
            )
    return findings


def band_totals_w(emissions, bands=PROTECTED_BANDS):
    """{band_name: total power in watts} summed over every emission
    that reaches that band. Bands nothing reaches are absent. Emissions
    are summed in the order given, so the result is deterministic."""
    totals = {}
    for emission in emissions:
        for band_name, power_w in emission_contributions(emission, bands):
            totals[band_name] = totals.get(band_name, 0.0) + power_w
    return totals


def band_limit_findings(
    transmitter_id, totals, bands=PROTECTED_BANDS, tolerance_db=POWER_TOLERANCE_DB
):
    """Findings (empty when every band is respected) for protected
    bands whose summed in-band power exceeds the limit of the service
    they carry. The comparison is made in dBm, the units the limit is
    stated in, and a total that sits on the limit to within the named
    tolerance is on the limit rather than over it. A band with no power
    in it at all is skipped. Findings are sorted by band name. Raises
    ValueError for a negative tolerance, a negative total, or through
    categorize_protected_band for an unknown band."""
    if tolerance_db < 0:
        raise ValueError("tolerance_db must be >= 0")
    findings = []
    for band_name in sorted(totals):
        total_w = totals[band_name]
        if total_w < 0:
            raise ValueError("in-band total for %r must be >= 0" % (band_name,))
        if total_w == 0:
            continue
        service = categorize_protected_band(band_name, bands)
        limit_dbm = service_limit_dbm(service)
        total_dbm = watts_to_dbm(total_w)
        if total_dbm > limit_dbm and not math.isclose(
            total_dbm, limit_dbm, rel_tol=0.0, abs_tol=tolerance_db
        ):
            findings.append(
                {
                    "issue": "protected_band_emission_above_limit",
                    "transmitter": transmitter_id,
                    "band": band_name,
                    "service": service,
                    "total_dbm": total_dbm,
                    "limit_dbm": limit_dbm,
                }
            )
    return findings


def harmonic_coverage_findings(transmitter, minimum_order=MIN_HARMONIC_ORDER):
    """Findings (empty when the sweep is deep enough) for a harmonic
    series that was not followed to the minimum order. Raises
    ValueError for a minimum order below two."""
    if minimum_order < 2:
        raise ValueError("minimum_order must be >= 2")
    max_order = transmitter["max_harmonic_order"]
    if max_order < minimum_order:
        return [
            {
                "issue": "harmonic_sweep_below_minimum_order",
                "transmitter": transmitter["transmitter_id"],
                "max_harmonic_order": max_order,
                "minimum_order": minimum_order,
            }
        ]
    return []


def transmitter_emission_review(transmitter):
    """Full clause 6.3.2.3 review for one transmitter.

    transmitter: {"transmitter_id": str, "fundamental_hz": float,
    "fundamental_power_w": float, "fundamental_bandwidth_hz": float,
    "max_harmonic_order": int, "harmonic_suppression_db": {order: db}
    (optional), "spurious_emissions": [emission, ...] (optional),
    "bands": registry (optional), "minimum_order": int (optional),
    "tolerance_db": float (optional)}.

    Returns {"declaration": [...], "band_limit": [...],
    "harmonic_coverage": [...]}. Raises ValueError through the helpers
    for a bad carrier, sweep order or band registry. Does not mutate
    transmitter."""
    bands = transmitter.get("bands", PROTECTED_BANDS)
    emissions = transmitter_emissions(transmitter)
    totals = band_totals_w(emissions, bands)
    return {
        "declaration": declaration_findings(transmitter),
        "band_limit": band_limit_findings(
            transmitter["transmitter_id"],
            totals,
            bands,
            transmitter.get("tolerance_db", POWER_TOLERANCE_DB),
        ),
        "harmonic_coverage": harmonic_coverage_findings(
            transmitter, transmitter.get("minimum_order", MIN_HARMONIC_ORDER)
        ),
    }


def is_transmitter_compliant(review):
    """True when every finding list in a transmitter_emission_review
    result is empty -- every spurious product is declared, the sweep
    reached the required order, and no protected band is over its
    limit."""
    return all(len(findings) == 0 for findings in review.values())
