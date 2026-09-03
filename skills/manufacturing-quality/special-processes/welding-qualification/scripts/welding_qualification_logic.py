"""Weld procedure qualification record checks (aerospace, AS9100 context).

Pure stdlib helpers to build and check the engineering content of an
aerospace weld procedure qualification record (WPS/PQR): weld heat input
in kJ per mm from voltage, current, travel speed and process efficiency,
preheat and interpass verification against the qualified procedure
values, thickness coverage of the production weld by the qualified
coupon, variable coverage verdicts, and the qualification test coupon
matrix for the process and joint type.

The coupon matrix, the arc efficiencies and the thickness range
fractions are documented typical aerospace engineering practices, not
reproductions of AWS D17.1 or AS9100 text; confirm them against the
governing code for the program. AS9100 is cited reference-only for
special process control context.
"""

HEAT_INPUT_UNITS = "kJ/mm"

# Supported fusion processes and joint configurations.
PROCESSES = ("gtaw", "gmaw", "gma-pulse")
JOINT_TYPES = ("butt", "fillet", "pipe")

# Documented typical arc efficiencies (heat input actually delivered to
# the joint as a fraction of the electrical power): gtaw 1.0, gmaw 0.8,
# gma-pulse 0.85. Typical practice values, confirm against the governing
# code.
DEFAULT_PROCESS_EFFICIENCY = {"gtaw": 1.0, "gmaw": 0.8, "gma-pulse": 0.85}

# Default thickness coverage window as fractions of the qualified coupon
# thickness that a production thickness must fall inside. Typical
# practice (0.75x to 2.0x), confirm against the governing code.
THICKNESS_RANGE_DEFAULT = (0.75, 2.0)

# Documented typical aerospace weld qualification coupon test sets per
# process and joint. Butt joints carry tensile, guided bend and a
# volumetric acceptance (radiography at 100 percent); fillet joints
# carry macro etch and fillet break; pipe joints carry tensile, guided
# bend and macro etch. Macro etch may substitute for radiography on
# butt joints where the governing code permits. Typical practice set,
# not a standard reproduction.
_BUTT_COUPONS = ("tensile-x2", "guided-bend-x4", "radiography-100pct")
_FILLET_COUPONS = ("macro-etch-x2", "fillet-break-x2")
_PIPE_COUPONS = ("tensile-x2", "guided-bend-x4", "macro-etch")

TYPICAL_COUPON_MATRIX = {
    "gtaw": {
        "butt": list(_BUTT_COUPONS),
        "fillet": list(_FILLET_COUPONS),
        "pipe": list(_PIPE_COUPONS),
    },
    "gmaw": {
        "butt": list(_BUTT_COUPONS),
        "fillet": list(_FILLET_COUPONS),
        "pipe": list(_PIPE_COUPONS),
    },
    "gma-pulse": {
        "butt": list(_BUTT_COUPONS),
        "fillet": list(_FILLET_COUPONS),
        "pipe": list(_PIPE_COUPONS),
    },
}


def heat_input_kj_mm(voltage_V, current_A, travel_speed_mm_s, process_efficiency):
    """Return the weld heat input in kJ per mm.

    Heat input = voltage * current * efficiency / (travel speed * 1000)
    converts J per mm into kJ per mm. Raises ValueError on non-physical
    electricals, travel speed or efficiency.
    """
    if voltage_V <= 0:
        raise ValueError("voltage must be positive")
    if current_A <= 0:
        raise ValueError("current must be positive")
    if travel_speed_mm_s <= 0:
        raise ValueError("travel speed must be positive")
    if process_efficiency <= 0 or process_efficiency > 1.0:
        raise ValueError("process efficiency must be in (0, 1]")
    return (
        voltage_V * current_A * process_efficiency
        / (travel_speed_mm_s * 1000.0)
    )


def coverage_verdict(value, qrange):
    """Return 'in-range' or 'out-of-range' for value against qrange.

    A None qrange means no qualified range was stated, so the check
    passes ('in-range'). Boundaries are inclusive. Raises ValueError on
    a qrange with lo greater than hi.
    """
    if qrange is None:
        return "in-range"
    lo, hi = qrange
    if lo > hi:
        raise ValueError("qualified range lo must not exceed hi")
    return "in-range" if lo <= value <= hi else "out-of-range"


def thickness_coverage(qualified_thickness_mm, production_thickness_mm,
                       range_fractions=None):
    """Return the production thickness coverage dict for the qualified coupon.

    With the default fractions (0.75, 2.0) the production thickness is
    covered when 0.75 * qualified <= production <= 2.0 * qualified.
    Returns {covered, lo_mm, hi_mm, verdict}. Raises ValueError on
    non-positive thicknesses or invalid range fractions.
    """
    if qualified_thickness_mm <= 0:
        raise ValueError("qualified thickness must be positive")
    if production_thickness_mm <= 0:
        raise ValueError("production thickness must be positive")
    lo_f, hi_f = THICKNESS_RANGE_DEFAULT if range_fractions is None else range_fractions
    if lo_f <= 0 or hi_f <= 0 or lo_f > hi_f:
        raise ValueError("range fractions must be positive with lo <= hi")
    lo_mm = lo_f * qualified_thickness_mm
    hi_mm = hi_f * qualified_thickness_mm
    covered = lo_mm <= production_thickness_mm <= hi_mm
    return {
        "covered": covered,
        "lo_mm": lo_mm,
        "hi_mm": hi_mm,
        "verdict": "in-range" if covered else "out-of-range",
    }


def preheat_margin_degC(measured_preheat_degC, required_min_preheat_degC):
    """Return the preheat margin in degC: measured minus required minimum.

    A non-negative margin means the measured preheat met the required
    minimum. Raises ValueError on a required minimum below absolute
    zero.
    """
    if required_min_preheat_degC < -273.15:
        raise ValueError("required minimum preheat below absolute zero")
    return measured_preheat_degC - required_min_preheat_degC


def interpass_ok(measured_interpass_degC, max_interpass_degC):
    """Return True when the measured interpass temperature is within the cap.

    Interpass temperature must stay at or below the qualified maximum.
    Raises ValueError on a non-positive maximum.
    """
    if max_interpass_degC <= 0:
        raise ValueError("max interpass temperature must be positive")
    return measured_interpass_degC <= max_interpass_degC


def qualification_summary(inputs):
    """Build the weld procedure qualification record check summary.

    inputs keys: process, joint_type, voltage_V, current_A,
    travel_speed_mm_s, process_efficiency (optional, defaults per
    process), qualified_thickness_mm, production_thickness_mm,
    required_min_preheat_degC, measured_preheat_degC,
    max_interpass_degC, measured_interpass_degC,
    qualified_heat_input_range_kj_mm (tuple or None),
    qualified_current_range_A (tuple or None),
    qualified_voltage_range_V (tuple or None).

    Returns a dict with the heat input, the current, voltage and heat
    input coverage verdicts, the preheat margin, interpass ok, the
    thickness coverage dict, the coupon matrix test list, all_ok and the
    findings list. Raises ValueError on an unknown process or joint, on
    non-positive electricals, travel speed or thicknesses, and on any
    other non-physical input handled by the helpers.
    """
    process = inputs["process"]
    joint_type = inputs["joint_type"]
    if process not in PROCESSES:
        raise ValueError("process must be one of gtaw, gmaw, gma-pulse")
    if joint_type not in JOINT_TYPES:
        raise ValueError("joint_type must be one of butt, fillet, pipe")

    voltage_V = inputs["voltage_V"]
    current_A = inputs["current_A"]
    travel_speed_mm_s = inputs["travel_speed_mm_s"]
    qualified_thickness_mm = inputs["qualified_thickness_mm"]
    production_thickness_mm = inputs["production_thickness_mm"]

    efficiency = inputs.get("process_efficiency",
                            DEFAULT_PROCESS_EFFICIENCY[process])
    heat_input = heat_input_kj_mm(voltage_V, current_A,
                                  travel_speed_mm_s, efficiency)

    heat_input_cov = coverage_verdict(
        heat_input, inputs.get("qualified_heat_input_range_kj_mm"))
    current_cov = coverage_verdict(
        current_A, inputs.get("qualified_current_range_A"))
    voltage_cov = coverage_verdict(
        voltage_V, inputs.get("qualified_voltage_range_V"))

    margin = preheat_margin_degC(inputs["measured_preheat_degC"],
                                 inputs["required_min_preheat_degC"])
    interpass = interpass_ok(inputs["measured_interpass_degC"],
                             inputs["max_interpass_degC"])
    thick = thickness_coverage(qualified_thickness_mm,
                               production_thickness_mm)

    findings = []
    if not thick["covered"]:
        findings.append("thickness-coverage")
    if heat_input_cov == "out-of-range":
        findings.append("heat-input")
    if current_cov == "out-of-range":
        findings.append("current-range")
    if voltage_cov == "out-of-range":
        findings.append("voltage-range")
    if not interpass:
        findings.append("interpass")

    # all_ok: thickness covered AND heat input in range (or none stated)
    # AND current and voltage in range (or none stated) AND interpass ok.
    # A stated range that is None reports in-range, so the verdicts can
    # be combined directly.
    all_ok = (
        thick["covered"]
        and heat_input_cov == "in-range"
        and current_cov == "in-range"
        and voltage_cov == "in-range"
        and interpass
    )

    return {
        "process": process,
        "joint_type": joint_type,
        "heat_input_kj_mm": heat_input,
        "heat_input_coverage": heat_input_cov,
        "current_coverage": current_cov,
        "voltage_coverage": voltage_cov,
        "preheat_margin_degC": margin,
        "interpass_ok": interpass,
        "thickness_coverage": thick,
        "coupon_matrix": list(TYPICAL_COUPON_MATRIX[process][joint_type]),
        "all_ok": all_ok,
        "findings": findings,
    }
