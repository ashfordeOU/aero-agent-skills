"""Whisker risk assessment for pure tin terminations on commercial EEE parts.

Anchor: ECSS-Q-ST-60-13C clause 9.2 (assessing whisker risk, and deciding the
controls, where a part carries pure tin terminations). Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Decide from the lead content by mass whether the termination finish counts
   as pure tin at all. A finish carrying enough lead is outside the provision
   and gets no controls from it.
2. Bound the whisker length the termination can reach over the mission from
   the finish type, the underplate, the substrate under the plating, the
   plating thickness and whether the assembly is conformally coated. The
   model is multiplicative on named factors so the result is reproducible and
   every factor is arguable on its own.
3. Divide the minimum conductor spacing by that bounding length to get a
   bridging margin: the number of whisker lengths of clearance the design has.
4. Raise the margin the design has to meet where the circuit could sustain a
   metal vapour arc once a whisker bridges, because there the bridge does not
   clear itself.
5. Place the outcome in a risk category from the margin against the margin
   required, judged at the boundary under a named tolerance.
6. Name the controls the outcome demands — refinish, barrier underplate,
   coating, spacing, current limiting and the declared-component-list entry.
"""

import math

__all__ = [
    "PURE_TIN_LEAD_THRESHOLD_PERCENT",
    "BASE_GROWTH_UM_PER_YEAR",
    "FINISH_FACTORS",
    "UNDERPLATE_FACTORS",
    "SUBSTRATE_FACTORS",
    "CONFORMAL_COATING_FACTOR",
    "THIN_PLATING_UM",
    "THICK_PLATING_UM",
    "BASE_REQUIRED_BRIDGING_MARGIN",
    "ARC_SUSTAINING_REQUIRED_MARGIN",
    "ARC_SUSTAINING_VOLTAGE_V",
    "ARC_SUSTAINING_CURRENT_A",
    "CONTROLLABLE_RATIO_FLOOR",
    "MARGIN_TOLERANCE",
    "RISK_CATEGORIES",
    "normalize_token",
    "is_pure_tin",
    "validate_finish",
    "validate_circuit",
    "plating_thickness_factor",
    "arc_can_be_sustained",
    "required_bridging_margin",
    "bounding_whisker_length",
    "bridging_margin",
    "risk_category",
    "required_controls",
    "assess_pure_tin_risk",
]

# A tin finish carrying less lead than this by mass is treated as pure tin.
PURE_TIN_LEAD_THRESHOLD_PERCENT = 3.0

# Bounding growth for an untreated bright tin finish, per mission year, before
# the finish, underplate, substrate, thickness and coating factors apply.
BASE_GROWTH_UM_PER_YEAR = 40.0

# How the deposited finish itself changes the bound. Bright tin carries the
# most internal compressive stress and sets the reference.
FINISH_FACTORS = {
    "bright-tin": 1.0,
    "matte-tin": 0.4,
    "reflowed-tin": 0.25,
    "fused-tin": 0.2,
}

# A barrier under the tin keeps substrate diffusion out of the plating.
UNDERPLATE_FACTORS = {
    "none": 1.0,
    "nickel": 0.3,
    "silver": 0.8,
    "copper": 1.1,
}

# What sits under the plating. Zinc out of brass is the classic driver.
SUBSTRATE_FACTORS = {
    "brass": 1.5,
    "copper": 1.0,
    "phosphor-bronze": 1.0,
    "alloy-42": 0.8,
    "kovar": 0.8,
}

# A conformal coat does not stop a whisker growing; it makes a bridge far
# less likely, which is what the margin measures.
CONFORMAL_COATING_FACTOR = 0.2

# Plating thickness bands, in micrometres.
THIN_PLATING_UM = 2.0
THICK_PLATING_UM = 10.0

# Clearance, in whisker lengths, the design has to hold.
BASE_REQUIRED_BRIDGING_MARGIN = 1.0

# Where a bridge can strike and hold an arc, the bridge does not clear itself,
# so the clearance required doubles.
ARC_SUSTAINING_REQUIRED_MARGIN = 2.0
ARC_SUSTAINING_VOLTAGE_V = 6.0
ARC_SUSTAINING_CURRENT_A = 0.3

# Below this share of the margin required, controls no longer recover the
# design and the termination has to be reworked out of pure tin.
CONTROLLABLE_RATIO_FLOOR = 0.25

# The margin ratio is a quotient of floats; a design sitting exactly on the
# boundary must not fail on representation alone.
MARGIN_TOLERANCE = 1e-9

RISK_CATEGORIES = (
    "not-applicable",
    "acceptable",
    "controls-required",
    "not-acceptable",
)


def _require_text(value, label):
    """Return a non-blank text field, raising on anything else."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, type(value).__name__))
    text = value.strip()
    if not text:
        raise ValueError("%s must not be blank" % label)
    return text


def _positive_number(value, label):
    """Return a strictly positive real quantity."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if number <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (label, value))
    return number


def _non_negative_number(value, label):
    """Return a real quantity that may be zero but never negative."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (label, value))
    return number


def _percent(value, label):
    """Return a percentage by mass in the closed range zero to one hundred."""
    number = _non_negative_number(value, label)
    if number > 100.0:
        raise ValueError("%s must not exceed 100, got %r" % (label, value))
    return number


def _flag(value, label):
    """Return a strict boolean flag."""
    if not isinstance(value, bool):
        raise ValueError("%s must be true or false, got %r" % (label, value))
    return value


def normalize_token(value, label="token"):
    """Return a normalized lower-case hyphenated token."""
    text = _require_text(value, label)
    return "-".join(text.lower().replace("_", " ").replace("-", " ").split())


def _lookup(table, value, label):
    """Return the factor a recognized token names in a factor table."""
    token = normalize_token(value, label)
    if token not in table:
        raise ValueError(
            "%s '%s' is not recognized; expected one of %s"
            % (label, token, ", ".join(sorted(table)))
        )
    return token, table[token]


def is_pure_tin(lead_mass_percent):
    """Return whether a tin finish counts as pure tin for this provision."""
    lead = _percent(lead_mass_percent, "lead_mass_percent")
    return lead < PURE_TIN_LEAD_THRESHOLD_PERCENT


def validate_finish(finish):
    """Return one validated termination finish description."""
    if not isinstance(finish, dict):
        raise ValueError("finish must be a mapping")
    for key in (
        "finish_type",
        "lead_mass_percent",
        "plating_thickness_um",
        "underplate",
        "substrate",
    ):
        if key not in finish:
            raise ValueError("finish missing required key '%s'" % key)
    finish_token, finish_factor = _lookup(
        FINISH_FACTORS, finish["finish_type"], "finish_type"
    )
    underplate_token, underplate_factor = _lookup(
        UNDERPLATE_FACTORS, finish["underplate"], "underplate"
    )
    substrate_token, substrate_factor = _lookup(
        SUBSTRATE_FACTORS, finish["substrate"], "substrate"
    )
    thickness = _positive_number(
        finish["plating_thickness_um"], "plating_thickness_um"
    )
    lead = _percent(finish["lead_mass_percent"], "lead_mass_percent")
    return {
        "finish_type": finish_token,
        "finish_factor": finish_factor,
        "underplate": underplate_token,
        "underplate_factor": underplate_factor,
        "substrate": substrate_token,
        "substrate_factor": substrate_factor,
        "plating_thickness_um": thickness,
        "lead_mass_percent": lead,
        "pure_tin": lead < PURE_TIN_LEAD_THRESHOLD_PERCENT,
    }


def validate_circuit(circuit):
    """Return one validated description of the circuit around the termination."""
    if not isinstance(circuit, dict):
        raise ValueError("circuit must be a mapping")
    for key in (
        "min_conductor_spacing_um",
        "operating_voltage_v",
        "available_current_a",
    ):
        if key not in circuit:
            raise ValueError("circuit missing required key '%s'" % key)
    return {
        "min_conductor_spacing_um": _positive_number(
            circuit["min_conductor_spacing_um"], "min_conductor_spacing_um"
        ),
        "operating_voltage_v": _non_negative_number(
            circuit["operating_voltage_v"], "operating_voltage_v"
        ),
        "available_current_a": _non_negative_number(
            circuit["available_current_a"], "available_current_a"
        ),
    }


def plating_thickness_factor(thickness_um):
    """Return the factor a plating thickness contributes to the bound.

    Very thin plating over a diffusing substrate is the worst case; a thick
    deposit relieves stress over a longer path and grows less.
    """
    thickness = _positive_number(thickness_um, "plating_thickness_um")
    if thickness < THIN_PLATING_UM:
        return 1.4
    if thickness < THICK_PLATING_UM:
        return 1.0
    return 0.7


def arc_can_be_sustained(operating_voltage_v, available_current_a):
    """Return whether a bridged whisker could strike and hold an arc."""
    voltage = _non_negative_number(operating_voltage_v, "operating_voltage_v")
    current = _non_negative_number(available_current_a, "available_current_a")
    return (
        voltage >= ARC_SUSTAINING_VOLTAGE_V
        and current >= ARC_SUSTAINING_CURRENT_A
    )


def required_bridging_margin(operating_voltage_v, available_current_a):
    """Return the clearance, in whisker lengths, the design has to hold."""
    if arc_can_be_sustained(operating_voltage_v, available_current_a):
        return ARC_SUSTAINING_REQUIRED_MARGIN
    return BASE_REQUIRED_BRIDGING_MARGIN


def bounding_whisker_length(finish, mission_years, conformal_coated=False):
    """Return the bounding whisker length, in micrometres, over the mission.

    Multiplicative on named factors: every term is separately arguable, and
    the product is reproducible wherever it is evaluated.
    """
    entry = finish if "finish_factor" in finish else validate_finish(finish)
    years = _positive_number(mission_years, "mission_years")
    coated = _flag(conformal_coated, "conformal_coated")
    length = BASE_GROWTH_UM_PER_YEAR * years
    length = length * entry["finish_factor"]
    length = length * entry["underplate_factor"]
    length = length * entry["substrate_factor"]
    length = length * plating_thickness_factor(entry["plating_thickness_um"])
    if coated:
        length = length * CONFORMAL_COATING_FACTOR
    return length


def bridging_margin(min_conductor_spacing_um, bounding_length_um):
    """Return the clearance expressed in bounding whisker lengths."""
    spacing = _positive_number(
        min_conductor_spacing_um, "min_conductor_spacing_um"
    )
    length = _positive_number(bounding_length_um, "bounding_length_um")
    return spacing / length


def risk_category(margin, margin_required):
    """Return the risk category a margin earns against the margin required."""
    achieved = _positive_number(margin, "margin")
    required = _positive_number(margin_required, "margin_required")
    ratio = achieved / required
    if ratio > 1.0 or math.isclose(
        ratio, 1.0, rel_tol=0.0, abs_tol=MARGIN_TOLERANCE
    ):
        return "acceptable"
    if ratio > CONTROLLABLE_RATIO_FLOOR or math.isclose(
        ratio, CONTROLLABLE_RATIO_FLOOR, rel_tol=0.0, abs_tol=MARGIN_TOLERANCE
    ):
        return "controls-required"
    return "not-acceptable"


def required_controls(finish, category, arc_capable, conformal_coated):
    """Return the controls the outcome demands, in the order they are applied."""
    entry = finish if "finish_factor" in finish else validate_finish(finish)
    if not entry["pure_tin"]:
        return []
    controls = ["pure-tin-entry-in-declared-component-list"]
    if entry["finish_type"] == "bright-tin":
        controls.append("matte-or-reflowed-tin-refinish")
    if entry["underplate"] == "none":
        controls.append("nickel-underplate-barrier")
    if category in ("controls-required", "not-acceptable"):
        if not conformal_coated:
            controls.append("conformal-coating-over-the-termination")
        controls.append("increase-minimum-conductor-spacing")
    if arc_capable:
        controls.append("series-impedance-or-current-limit-against-sustained-arc")
    if category == "not-acceptable":
        controls.append("hot-solder-dip-or-re-tin-with-a-lead-bearing-alloy")
    return controls


def assess_pure_tin_risk(part):
    """Run the full clause 9.2 whisker assessment of one termination finish.

    part keys: part_number, finish, circuit, mission_years, and optionally
    conformal_coated.
    """
    if not isinstance(part, dict):
        raise ValueError("part must be a mapping")
    for key in ("part_number", "finish", "circuit", "mission_years"):
        if key not in part:
            raise ValueError("part missing required key '%s'" % key)

    part_number = _require_text(part["part_number"], "part_number")
    finish = validate_finish(part["finish"])
    circuit = validate_circuit(part["circuit"])
    years = _positive_number(part["mission_years"], "mission_years")
    coated = _flag(part.get("conformal_coated", False), "conformal_coated")

    arc_capable = arc_can_be_sustained(
        circuit["operating_voltage_v"], circuit["available_current_a"]
    )
    margin_required = required_bridging_margin(
        circuit["operating_voltage_v"], circuit["available_current_a"]
    )

    if not finish["pure_tin"]:
        return {
            "part_number": part_number,
            "finish": finish,
            "circuit": circuit,
            "mission_years": years,
            "conformal_coated": coated,
            "pure_tin": False,
            "arc_can_be_sustained": arc_capable,
            "bounding_whisker_length_um": None,
            "bridging_margin": None,
            "margin_required": margin_required,
            "margin_ratio": None,
            "risk_category": "not-applicable",
            "controls": [],
            "acceptable_as_built": True,
            "findings": [],
        }

    length = bounding_whisker_length(finish, years, coated)
    margin = bridging_margin(circuit["min_conductor_spacing_um"], length)
    ratio = margin / margin_required
    category = risk_category(margin, margin_required)
    controls = required_controls(finish, category, arc_capable, coated)

    findings = []
    if category != "acceptable":
        findings.append(
            "part '%s' holds %.3f whisker lengths of clearance against the "
            "%.3f required" % (part_number, margin, margin_required)
        )
    if arc_capable:
        findings.append(
            "the circuit around part '%s' can sustain a metal vapour arc, so a "
            "bridge would not clear itself" % part_number
        )
    if finish["underplate"] == "none":
        findings.append(
            "part '%s' plates tin straight onto %s with no barrier underplate"
            % (part_number, finish["substrate"])
        )
    if finish["finish_type"] == "bright-tin":
        findings.append(
            "part '%s' carries a bright tin deposit, the highest stress finish"
            % part_number
        )
    if category == "not-acceptable":
        findings.append(
            "part '%s' cannot be recovered by coating and spacing alone and "
            "has to be taken out of pure tin" % part_number
        )

    return {
        "part_number": part_number,
        "finish": finish,
        "circuit": circuit,
        "mission_years": years,
        "conformal_coated": coated,
        "pure_tin": True,
        "arc_can_be_sustained": arc_capable,
        "bounding_whisker_length_um": length,
        "bridging_margin": margin,
        "margin_required": margin_required,
        "margin_ratio": ratio,
        "risk_category": category,
        "controls": controls,
        "acceptable_as_built": category == "acceptable",
        "findings": findings,
    }
