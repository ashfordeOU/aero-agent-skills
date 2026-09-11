"""
ECSS-E-ST-10C Annex C — International Standards Authorities Registry.

Deterministic, offline reference-data module (stdlib only).
Maps space-mission data products to their originating standards authority.
"""

# ---------------------------------------------------------------------------
# Authority registry
# ---------------------------------------------------------------------------

AUTHORITIES = {
    "IERS": {
        "full_name": "International Earth Rotation and Reference Systems Service",
        "products": [
            "ITRS",
            "ICRS",
            "EOP",
            "leap_seconds",
            "UT1_UTC",
            "polar_motion",
            "IERS_bulletins",
            "IERS_conventions",
        ],
        "domain": "earth_orientation",
        "notes": (
            "Primary source for Earth Orientation Parameters, ITRS realisation, "
            "and leap-second bulletins (IERS Bulletin C). Co-publisher of rapid "
            "EOP files with USNO."
        ),
    },
    "IAU": {
        "full_name": "International Astronomical Union",
        "products": [
            "ICRS",
            "astronomical_constants",
            "time_scale_definitions",
            "TDB",
            "TCB",
            "TCG",
            "IAU_resolutions",
        ],
        "domain": "astronomical_standards",
        "notes": (
            "Defines the ICRS and adopted astronomical constants; time-scale "
            "definitions (TDB, TCB, TCG); delegates planetary rotation standards "
            "to the WGCCRE."
        ),
    },
    "USNO": {
        "full_name": "United States Naval Observatory",
        "products": [
            "UTC",
            "astronomical_almanac",
            "IERS_A_rapid_files",
            "USNO_master_clock",
        ],
        "domain": "time_and_almanac",
        "notes": (
            "Operates a primary UTC master clock; co-publishes IERS Bulletin A "
            "(rapid EOP); joint publisher of the Astronomical Almanac."
        ),
    },
    "BIPM": {
        "full_name": "Bureau International des Poids et Mesures",
        "products": [
            "TAI",
            "UTC",
            "SI_units",
            "SI_second",
            "CIPM_MRA",
            "Circular_T",
        ],
        "domain": "time_and_units",
        "notes": (
            "Computes and disseminates TAI and coordinates UTC; custodian of SI "
            "unit definitions. Issues Circular T for UTC-TAI comparisons."
        ),
    },
    "IMCCE": {
        "full_name": (
            "Institut de Mecanique Celeste et de Calcul des Ephemerides"
        ),
        "products": [
            "planetary_ephemerides",
            "INPOP",
            "INPOP_series",
        ],
        "domain": "ephemerides",
        "notes": (
            "Produces the INPOP planetary and lunar ephemeris series; used as "
            "an independent alternative to JPL DE ephemerides."
        ),
    },
    "JPL": {
        "full_name": "Jet Propulsion Laboratory",
        "products": [
            "planetary_ephemerides",
            "DE_series",
            "DE440",
            "DE441",
            "SPICE",
            "NAIF",
        ],
        "domain": "ephemerides",
        "notes": (
            "Produces the DE planetary ephemeris series (DE440, DE441) and the "
            "SPICE/NAIF toolkit for astrodynamics kernel management."
        ),
    },
    "CCSDS": {
        "full_name": "Consultative Committee for Space Data Systems",
        "products": [
            "time_code_formats",
            "CCSDS_time_B1",
            "orbit_data_messages",
            "OEM",
            "AEM",
            "APM",
            "ADM",
            "cross_support_services",
        ],
        "domain": "space_data_standards",
        "notes": (
            "Defines time-code formats (CCSDS 301.0-B), orbit and attitude data "
            "message standards (OEM, AEM, APM, ADM), and cross-support service "
            "protocols for multi-agency ground networks."
        ),
    },
    "NIMA": {
        "full_name": "National Imagery and Mapping Agency",
        "products": [
            "WGS84",
            "EGM96",
            "EGM2008",
            "gravity_model",
            "geodetic_reference_ellipsoid",
        ],
        "domain": "geodesy",
        "notes": (
            "Now NGA; defined the WGS-84 geodetic reference ellipsoid and the "
            "EGM96/EGM2008 global gravity models used for GPS-referenced missions."
        ),
    },
    "WGCCRE": {
        "full_name": (
            "IAU Working Group for Cartographic Coordinates and "
            "Rotational Elements"
        ),
        "products": [
            "planet_orientation_models",
            "body_rotation_elements",
            "prime_meridian_definitions",
            "body_radii",
        ],
        "domain": "planetary_cartography",
        "notes": (
            "IAU working group; publishes rotation poles, prime meridians, and "
            "body radii for solar system bodies. Mandatory reference for any "
            "mission addressing a non-Earth body surface."
        ),
    },
}

# ---------------------------------------------------------------------------
# Domain → authority mapping (primary authorities listed first)
# ---------------------------------------------------------------------------

DOMAIN_PRIMARY = {
    "earth_orientation": ["IERS"],
    "time_scales": ["BIPM", "IERS", "USNO"],
    "celestial_reference": ["IAU", "IERS"],
    "terrestrial_reference": ["IERS", "NIMA"],
    "ephemerides": ["JPL", "IMCCE"],
    "geodesy": ["NIMA"],
    "space_data_formats": ["CCSDS"],
    "planetary_cartography": ["WGCCRE", "IAU"],
    "si_units": ["BIPM"],
    "astronomical_constants": ["IAU"],
}

# ---------------------------------------------------------------------------
# Coverage-status constants
# ---------------------------------------------------------------------------

COVERED = "COVERED"
GAP = "GAP"
CITATION_ERROR = "CITATION_ERROR"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_authority_info(authority_id: str) -> dict:
    """Return the info dict for a known authority.

    Raises KeyError for an unrecognised authority identifier.
    """
    key = authority_id.strip().upper()
    if key not in AUTHORITIES:
        raise KeyError(
            f"Unknown authority: {authority_id!r}. "
            f"Known identifiers: {sorted(AUTHORITIES)}"
        )
    return AUTHORITIES[key]


def resolve_authority(product: str) -> list:
    """Return authority IDs that produce the named data product.

    Matching is case-insensitive against the canonical product token.
    Returns an empty list when no authority covers the product.
    """
    needle = product.strip().lower()
    matches = []
    for auth_id, info in AUTHORITIES.items():
        products_lower = [p.lower() for p in info["products"]]
        if needle in products_lower:
            matches.append(auth_id)
    return matches


def list_authorities_by_domain(domain: str) -> list:
    """Return authority IDs responsible for the given domain keyword.

    Returns an empty list for an unrecognised domain.
    """
    key = domain.strip().lower()
    return list(DOMAIN_PRIMARY.get(key, []))


def validate_citation(authority_id: str, product: str) -> bool:
    """Return True if the authority produces the named product.

    Returns False for an unrecognised authority or a product mismatch.
    """
    try:
        info = get_authority_info(authority_id)
    except KeyError:
        return False
    products_lower = [p.lower() for p in info["products"]]
    return product.strip().lower() in products_lower


def audit_authority_coverage(required_products: list) -> dict:
    """Map each required product to its coverage status and resolving authorities.

    Returns a dict keyed by product with values:
        {"status": COVERED | GAP, "authorities": [list-of-auth-ids]}
    """
    result = {}
    for product in required_products:
        auths = resolve_authority(product)
        result[product] = {
            "status": COVERED if auths else GAP,
            "authorities": auths,
        }
    return result


def check_citation(authority_id: str, product: str) -> str:
    """Return a citation-check status string for a (authority, product) pair.

    Returns COVERED if the authority produces the product, GAP if the
    authority is unknown, or CITATION_ERROR if the authority is known but
    does not produce that product.
    """
    key = authority_id.strip().upper()
    if key not in AUTHORITIES:
        return GAP
    if validate_citation(authority_id, product):
        return COVERED
    return CITATION_ERROR
