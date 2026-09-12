"""ECSS-E-ST-20C clause 5.5.4 -- solar array drive current capability logic.

Deterministic, offline, stdlib-only helpers that check the current rating of
every conductor between a solar array section and the power bus: harness
wires, connector pins and slip-ring contacts. The procedure is a paraphrase
of the clause intent; no standard text is reproduced here.

Chain in one line: derive the worst-case applied current from the hot,
near-sun short-circuit condition, categorize each element of the path,
derate its catalogue rating for bundle, temperature and vacuum (and for
imperfect sharing on a paralleled slip ring), then grade each element's
current margin and name the weakest link.
"""

import math

REFERENCE_TEMPERATURE_C = 28.0
DERATING_REFERENCE_TEMPERATURE_C = 20.0
VACUUM_DERATING_FACTOR = 0.80
DEFAULT_SHARING_FACTOR = 0.80
DEFAULT_REQUIRED_MARGIN = 0.20

HARNESS_WIRE = "harness-wire"
CONNECTOR_PIN = "connector-pin"
SLIP_RING_CONTACT = "slip-ring-contact"

PATH_ELEMENT_FAMILIES = (HARNESS_WIRE, CONNECTOR_PIN, SLIP_RING_CONTACT)

_ELEMENT_ALIASES = {
    "wire": HARNESS_WIRE,
    "cable": HARNESS_WIRE,
    "harness": HARNESS_WIRE,
    "harness-wire": HARNESS_WIRE,
    "pin": CONNECTOR_PIN,
    "contact-pin": CONNECTOR_PIN,
    "connector": CONNECTOR_PIN,
    "connector-pin": CONNECTOR_PIN,
    "slip-ring": SLIP_RING_CONTACT,
    "slip-ring-contact": SLIP_RING_CONTACT,
    "sadm-slip-ring": SLIP_RING_CONTACT,
}

# Representative free-air single-conductor ratings (A) for spacecraft harness
# wire. Replace with the project wire table before any real verification.
AWG_BASE_RATING_A = {
    26: 2.2,
    24: 3.3,
    22: 4.5,
    20: 6.5,
    18: 9.2,
    16: 13.0,
    14: 19.0,
    12: 25.0,
    10: 33.0,
}

# Conductor count in the loom -> multiplicative bundle derating factor.
_BUNDLE_DERATING_BANDS = (
    (1, 1.00),
    (3, 0.85),
    (6, 0.75),
    (15, 0.65),
    (30, 0.55),
)
_BUNDLE_DERATING_FLOOR = 0.45


def _require_number(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    if math.isnan(value) or math.isinf(value):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return float(value)


def _require_count(value, label):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value < 1:
        raise ValueError("%s must be >= 1, got %d" % (label, value))
    return value


def categorize_path_element(kind):
    """Map an element description onto one of the three path families."""
    if not isinstance(kind, str) or not kind.strip():
        raise ValueError("element kind must be a non-empty string")
    token = kind.strip().lower().replace(" ", "-").replace("_", "-")
    if token in _ELEMENT_ALIASES:
        return _ELEMENT_ALIASES[token]
    raise ValueError(
        "unknown path element family %r; expected a harness wire, a connector "
        "pin or a slip-ring contact" % (kind,)
    )


def wire_base_rating(gauge_awg):
    """Free-air catalogue current rating (A) for a harness wire gauge."""
    if isinstance(gauge_awg, bool) or not isinstance(gauge_awg, int):
        raise ValueError("gauge_awg must be an integer AWG size")
    if gauge_awg not in AWG_BASE_RATING_A:
        raise ValueError(
            "gauge %r is not in the wire table; add the project rating first"
            % (gauge_awg,)
        )
    return AWG_BASE_RATING_A[gauge_awg]


def bundle_derating_factor(bundle_count):
    """Derating for conductors sharing a loom (self-heating)."""
    count = _require_count(bundle_count, "bundle_count")
    for limit, factor in _BUNDLE_DERATING_BANDS:
        if count <= limit:
            return factor
    return _BUNDLE_DERATING_FLOOR


def temperature_derating_factor(
    conductor_temperature_c,
    insulation_rating_c,
    reference_temperature_c=DERATING_REFERENCE_TEMPERATURE_C,
):
    """Derating as the conductor temperature approaches the insulation rating."""
    conductor = _require_number(conductor_temperature_c, "conductor_temperature_c")
    rating = _require_number(insulation_rating_c, "insulation_rating_c")
    reference = _require_number(reference_temperature_c, "reference_temperature_c")
    if conductor <= -273.15:
        raise ValueError("conductor_temperature_c is at or below absolute zero")
    if rating <= reference:
        raise ValueError("insulation_rating_c must exceed the derating reference")
    if conductor >= rating:
        raise ValueError(
            "conductor temperature %.1f C is at or above the insulation rating "
            "%.1f C; the element has no capability left" % (conductor, rating)
        )
    if conductor <= reference:
        return 1.0
    return math.sqrt((rating - conductor) / (rating - reference))


def vacuum_derating_factor(in_vacuum):
    """Derating for operation outside atmosphere (no convective heat path)."""
    if not isinstance(in_vacuum, bool):
        raise ValueError("in_vacuum must be a boolean")
    return VACUUM_DERATING_FACTOR if in_vacuum else 1.0


def slip_ring_capability(
    rated_current_per_contact_a,
    contact_count,
    sharing_factor=DEFAULT_SHARING_FACTOR,
    single_contact_failure=False,
):
    """Capability (A) of a paralleled slip-ring contact set."""
    rated = _require_number(rated_current_per_contact_a, "rated_current_per_contact_a")
    if rated <= 0.0:
        raise ValueError("rated_current_per_contact_a must be > 0")
    count = _require_count(contact_count, "contact_count")
    sharing = _require_number(sharing_factor, "sharing_factor")
    if not 0.0 < sharing <= 1.0:
        raise ValueError("sharing_factor must be in (0, 1], got %r" % sharing)
    if not isinstance(single_contact_failure, bool):
        raise ValueError("single_contact_failure must be a boolean")
    usable = count - 1 if single_contact_failure else count
    if usable < 1:
        raise ValueError(
            "a single-contact failure leaves no usable contact; the circuit "
            "needs at least two installed contacts to claim redundancy"
        )
    return rated * usable * sharing


def worst_case_section_current(
    isc_reference_a,
    short_circuit_temp_coeff_per_c=4.6e-4,
    max_operating_temperature_c=REFERENCE_TEMPERATURE_C,
    min_solar_distance_au=1.0,
    sun_incidence_deg=0.0,
    parallel_strings=1,
    reference_temperature_c=REFERENCE_TEMPERATURE_C,
):
    """Applied current (A): hot, near-sun short-circuit output of the section."""
    isc = _require_number(isc_reference_a, "isc_reference_a")
    if isc <= 0.0:
        raise ValueError("isc_reference_a must be > 0")
    coeff = _require_number(short_circuit_temp_coeff_per_c, "short_circuit_temp_coeff_per_c")
    if coeff < 0.0:
        raise ValueError(
            "short_circuit_temp_coeff_per_c must be >= 0; short-circuit current "
            "rises with temperature, so the hot case is the worst case"
        )
    temp = _require_number(max_operating_temperature_c, "max_operating_temperature_c")
    if temp <= -273.15:
        raise ValueError("max_operating_temperature_c is at or below absolute zero")
    distance = _require_number(min_solar_distance_au, "min_solar_distance_au")
    if distance <= 0.0:
        raise ValueError("min_solar_distance_au must be > 0")
    incidence = _require_number(sun_incidence_deg, "sun_incidence_deg")
    if not 0.0 <= incidence < 90.0:
        raise ValueError("sun_incidence_deg must be in [0, 90)")
    strings = _require_count(parallel_strings, "parallel_strings")
    reference = _require_number(reference_temperature_c, "reference_temperature_c")
    intensity = (1.0 / distance) ** 2 * math.cos(math.radians(incidence))
    current = isc * intensity * (1.0 + coeff * (temp - reference)) * strings
    if current <= 0.0:
        raise ValueError("applied current collapsed to zero; check the inputs")
    return current


def element_capability(element):
    """Derated current capability (A) of one path element, with its factors."""
    if not isinstance(element, dict):
        raise ValueError("element must be a mapping, got %r" % (type(element).__name__,))
    element_id = element.get("element_id")
    if not isinstance(element_id, str) or not element_id.strip():
        raise ValueError("element_id must be a non-empty string")
    family = categorize_path_element(element.get("kind", ""))
    conductor_temp = _require_number(
        element.get("conductor_temperature_c", DERATING_REFERENCE_TEMPERATURE_C),
        "conductor_temperature_c",
    )
    insulation = _require_number(
        element.get("insulation_rating_c", 200.0), "insulation_rating_c"
    )
    temp_factor = temperature_derating_factor(conductor_temp, insulation)
    detail = {
        "element_id": element_id,
        "family": family,
        "temperature_factor": temp_factor,
    }
    if family == SLIP_RING_CONTACT:
        base = slip_ring_capability(
            element.get("rated_current_per_contact_a", 0.0),
            element.get("contact_count", 1),
            element.get("sharing_factor", DEFAULT_SHARING_FACTOR),
            element.get("single_contact_failure", False),
        )
        detail["base_capability_a"] = base
        detail["bundle_factor"] = 1.0
        detail["vacuum_factor"] = 1.0
        detail["capability_a"] = base * temp_factor
        return detail
    bundle_factor = bundle_derating_factor(element.get("bundle_count", 1))
    vacuum_factor = vacuum_derating_factor(element.get("in_vacuum", False))
    if family == HARNESS_WIRE:
        base = wire_base_rating(element.get("gauge_awg"))
    else:
        base = _require_number(element.get("rated_current_a", 0.0), "rated_current_a")
        if base <= 0.0:
            raise ValueError(
                "element %r: rated_current_a must be > 0 for a connector pin"
                % element_id
            )
    detail["base_capability_a"] = base
    detail["bundle_factor"] = bundle_factor
    detail["vacuum_factor"] = vacuum_factor
    detail["capability_a"] = base * bundle_factor * temp_factor * vacuum_factor
    return detail


def element_margin(capability_a, applied_current_a, required_margin=DEFAULT_REQUIRED_MARGIN):
    """Current margin of one element and its pass/fail verdict."""
    capability = _require_number(capability_a, "capability_a")
    if capability <= 0.0:
        raise ValueError("capability_a must be > 0")
    applied = _require_number(applied_current_a, "applied_current_a")
    if applied <= 0.0:
        raise ValueError("applied_current_a must be > 0")
    floor = _require_number(required_margin, "required_margin")
    if floor < 0.0:
        raise ValueError("required_margin must be >= 0")
    margin = capability / applied - 1.0
    return {
        "margin": margin,
        "required_margin": floor,
        "verdict": "pass" if margin >= floor else "fail",
    }


def assess_power_path(
    elements, applied_current_a, required_margin=DEFAULT_REQUIRED_MARGIN
):
    """Grade every element of a section's power path and name the weakest link."""
    if not isinstance(elements, (list, tuple)) or not elements:
        raise ValueError("elements must be a non-empty list of path elements")
    applied = _require_number(applied_current_a, "applied_current_a")
    if applied <= 0.0:
        raise ValueError("applied_current_a must be > 0")
    table = []
    findings = []
    for element in elements:
        detail = element_capability(element)
        graded = element_margin(detail["capability_a"], applied, required_margin)
        detail.update(graded)
        detail["applied_current_a"] = applied
        table.append(detail)
        if graded["verdict"] == "fail":
            findings.append(
                "element %r (%s) carries %.3f A against a derated capability of "
                "%.3f A: margin %.3f below the required %.3f"
                % (
                    detail["element_id"],
                    detail["family"],
                    applied,
                    detail["capability_a"],
                    graded["margin"],
                    required_margin,
                )
            )
    weakest = min(table, key=lambda d: d["margin"])
    return {
        "applied_current_a": applied,
        "required_margin": required_margin,
        "elements": table,
        "weakest_element": weakest["element_id"],
        "weakest_margin": weakest["margin"],
        "findings": findings,
        "compliant": not findings,
    }
