"""Thermal-control to structure mechanical interface requirements.

Anchor: ECSS-E-ST-31C clause 4.3.2 (interface requirements towards the
structure subsystem). Paraphrased into an implementable procedure; no
standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate each mounting interface: bolt pattern, preload, nominal contact
   area and the interface filler declared for it.
2. Turn the bolt preload and the contact area into a contact pressure, and
   read the interface conductance coefficient of the declared filler off its
   tabulated pressure curve; multiply by the effective area to get the
   conductance the joint actually offers, in W/K.
3. Form the conductance the thermal design demands from the unit dissipation
   and the baseplate temperature rise the requirement allows, and compare the
   two with a named tolerance at the boundary.
4. Take the coefficient-of-thermal-expansion mismatch between the mounted
   item and its host panel over the qualification temperature swing, turn it
   into a differential expansion at the outermost fastener, and express that
   both as an interface slip against the allowable and as an angular
   alignment contribution in arcseconds against the alignment allocation.
5. Roll the interface hardware mass (brackets, shims, fillers, fasteners)
   up with its contingency and compare it with the mass allocation the
   structure subsystem holds for thermal-control interface hardware.
"""

import math

__all__ = [
    "ARCSEC_PER_RADIAN",
    "CONDUCTANCE_TOLERANCE_W_PER_K",
    "FILLER_PRESSURE_CURVES",
    "validate_positive",
    "contact_pressure_pa",
    "filler_coefficient_w_per_m2k",
    "interface_conductance_w_per_k",
    "required_conductance_w_per_k",
    "conductance_margin_fraction",
    "differential_expansion_m",
    "alignment_contribution_arcsec",
    "interface_hardware_mass_kg",
    "assess_mount",
    "assess_mechanical_interfaces",
]

# Conductance comparisons are a ratio of two floated quantities; an interface
# sized exactly on its requirement can land a few ULPs on the wrong side.
# Absorb the representation error here instead of relaxing the requirement.
CONDUCTANCE_TOLERANCE_W_PER_K = 1e-9

# Interface conductance coefficient (W/m^2K) against contact pressure (Pa) for
# the filler options a thermal design normally offers the structure subsystem.
# Representative shapes only: a real project substitutes measured data.
FILLER_PRESSURE_CURVES = {
    "bare-metal-to-metal": [
        (1.0e5, 300.0),
        (5.0e5, 900.0),
        (2.0e6, 2200.0),
        (1.0e7, 5200.0),
    ],
    "thermal-filler-pad": [
        (1.0e5, 1400.0),
        (5.0e5, 2600.0),
        (2.0e6, 4300.0),
        (1.0e7, 7000.0),
    ],
    "thermal-grease": [
        (1.0e5, 2600.0),
        (5.0e5, 4800.0),
        (2.0e6, 7600.0),
        (1.0e7, 11000.0),
    ],
    "insulating-washer-stack": [
        (1.0e5, 40.0),
        (5.0e5, 75.0),
        (2.0e6, 130.0),
        (1.0e7, 240.0),
    ],
}

ARCSEC_PER_RADIAN = 180.0 * 3600.0 / math.pi


def validate_positive(label, value, allow_zero=False):
    """Return value as a positive finite float, raising on anything else."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if allow_zero:
        if out < 0.0:
            raise ValueError("%s must not be negative, got %g" % (label, out))
    elif out <= 0.0:
        raise ValueError("%s must be strictly positive, got %g" % (label, out))
    return out


def contact_pressure_pa(preload_per_bolt_n, bolt_count, contact_area_m2):
    """Return the mean contact pressure the bolt pattern develops, in Pa."""
    preload = validate_positive("preload_per_bolt_n", preload_per_bolt_n)
    area = validate_positive("contact_area_m2", contact_area_m2)
    if not isinstance(bolt_count, int) or isinstance(bolt_count, bool):
        raise ValueError("bolt_count must be an integer, got %r" % (bolt_count,))
    if bolt_count < 1:
        raise ValueError("bolt_count must be at least one, got %d" % bolt_count)
    return preload * bolt_count / area


def filler_coefficient_w_per_m2k(filler, pressure_pa):
    """Interpolate the filler conductance coefficient; refuse to extrapolate."""
    if filler not in FILLER_PRESSURE_CURVES:
        raise ValueError(
            "unknown interface filler %r; declared options are %s"
            % (filler, ", ".join(sorted(FILLER_PRESSURE_CURVES)))
        )
    pressure = validate_positive("pressure_pa", pressure_pa)
    curve = FILLER_PRESSURE_CURVES[filler]
    lo_p, hi_p = curve[0][0], curve[-1][0]
    if pressure < lo_p or pressure > hi_p:
        raise ValueError(
            "filler %r is characterized over [%g, %g] Pa; %g is outside it, "
            "extrapolation refused" % (filler, lo_p, hi_p, pressure)
        )
    for index in range(1, len(curve)):
        p0, h0 = curve[index - 1]
        p1, h1 = curve[index]
        if pressure <= p1:
            if pressure == p0:
                return h0
            if pressure == p1:
                return h1
            fraction = (pressure - p0) / (p1 - p0)
            return h0 + fraction * (h1 - h0)
    return curve[-1][1]


def interface_conductance_w_per_k(coefficient_w_per_m2k, effective_area_m2):
    """Return the conductance of one mounting interface, in W/K."""
    coefficient = validate_positive("coefficient_w_per_m2k", coefficient_w_per_m2k)
    area = validate_positive("effective_area_m2", effective_area_m2)
    return coefficient * area


def required_conductance_w_per_k(dissipation_w, allowed_rise_k):
    """Return the conductance the dissipation and the allowed rise demand."""
    heat = validate_positive("dissipation_w", dissipation_w)
    rise = validate_positive("allowed_rise_k", allowed_rise_k)
    return heat / rise


def conductance_margin_fraction(achieved_w_per_k, required_w_per_k):
    """Return the fractional conductance margin of a mounting interface."""
    achieved = validate_positive("achieved_w_per_k", achieved_w_per_k)
    required = validate_positive("required_w_per_k", required_w_per_k)
    return (achieved - required) / required


def differential_expansion_m(alpha_item_per_k, alpha_panel_per_k,
                             delta_temperature_k, footprint_m):
    """Return the differential growth at the outermost fastener, in metres."""
    for label, value in (("alpha_item_per_k", alpha_item_per_k),
                         ("alpha_panel_per_k", alpha_panel_per_k)):
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError("%s must be a real number, got %r" % (label, value))
        if not math.isfinite(float(value)):
            raise ValueError("%s must be finite" % label)
    swing = validate_positive("delta_temperature_k", delta_temperature_k)
    footprint = validate_positive("footprint_m", footprint_m)
    mismatch = abs(float(alpha_item_per_k) - float(alpha_panel_per_k))
    return mismatch * swing * footprint


def alignment_contribution_arcsec(expansion_m, lever_arm_m):
    """Return the angular alignment contribution of a slip, in arcseconds."""
    growth = validate_positive("expansion_m", expansion_m, allow_zero=True)
    lever = validate_positive("lever_arm_m", lever_arm_m)
    return math.atan(growth / lever) * ARCSEC_PER_RADIAN


def interface_hardware_mass_kg(mounts, contingency_fraction=0.0):
    """Return the interface hardware mass with its contingency applied."""
    if not isinstance(mounts, (list, tuple)) or not mounts:
        raise ValueError("mounts must be a non-empty sequence of interface records")
    contingency = validate_positive(
        "contingency_fraction", contingency_fraction, allow_zero=True
    )
    total = 0.0
    for index, mount in enumerate(mounts):
        if not isinstance(mount, dict):
            raise ValueError("mounts[%d] must be a mapping" % index)
        if "hardware_mass_kg" not in mount:
            raise ValueError(
                "mounts[%d] (%s) declares no hardware_mass_kg; an undeclared "
                "interface mass is unknown, not zero"
                % (index, mount.get("name", "unnamed"))
            )
        total += validate_positive(
            "mounts[%d].hardware_mass_kg" % index, mount["hardware_mass_kg"],
            allow_zero=True,
        )
    return total * (1.0 + contingency)


def assess_mount(mount):
    """Assess one mounting interface and return its record."""
    if not isinstance(mount, dict):
        raise ValueError("mount must be a mapping")
    for key in ("name", "filler", "preload_per_bolt_n", "bolt_count",
                "contact_area_m2", "effective_area_m2", "dissipation_w",
                "allowed_rise_k", "alpha_item_per_k", "alpha_panel_per_k",
                "delta_temperature_k", "footprint_m", "allowable_slip_m",
                "lever_arm_m", "alignment_allocation_arcsec"):
        if key not in mount:
            raise ValueError("mount record missing required key %r" % key)
    pressure = contact_pressure_pa(
        mount["preload_per_bolt_n"], mount["bolt_count"], mount["contact_area_m2"]
    )
    coefficient = filler_coefficient_w_per_m2k(mount["filler"], pressure)
    achieved = interface_conductance_w_per_k(coefficient, mount["effective_area_m2"])
    required = required_conductance_w_per_k(
        mount["dissipation_w"], mount["allowed_rise_k"]
    )
    conductance_ok = achieved > required or math.isclose(
        achieved, required, rel_tol=0.0, abs_tol=CONDUCTANCE_TOLERANCE_W_PER_K
    )
    slip = differential_expansion_m(
        mount["alpha_item_per_k"], mount["alpha_panel_per_k"],
        mount["delta_temperature_k"], mount["footprint_m"],
    )
    allowable = validate_positive("allowable_slip_m", mount["allowable_slip_m"])
    slip_ok = slip < allowable or math.isclose(
        slip, allowable, rel_tol=1e-12, abs_tol=0.0
    )
    tilt = alignment_contribution_arcsec(slip, mount["lever_arm_m"])
    allocation = validate_positive(
        "alignment_allocation_arcsec", mount["alignment_allocation_arcsec"]
    )
    alignment_ok = tilt < allocation or math.isclose(
        tilt, allocation, rel_tol=1e-12, abs_tol=0.0
    )
    findings = []
    if not conductance_ok:
        findings.append(
            "%s: interface conductance %.4f W/K is below the %.4f W/K the "
            "dissipation and the allowed baseplate rise demand"
            % (mount["name"], achieved, required)
        )
    if not slip_ok:
        findings.append(
            "%s: differential expansion %.6g m exceeds the allowable interface "
            "slip %.6g m" % (mount["name"], slip, allowable)
        )
    if not alignment_ok:
        findings.append(
            "%s: alignment contribution %.3f arcsec exceeds the %.3f arcsec "
            "allocated to the thermal interface"
            % (mount["name"], tilt, allocation)
        )
    return {
        "name": mount["name"],
        "contact_pressure_pa": pressure,
        "filler_coefficient_w_per_m2k": coefficient,
        "conductance_w_per_k": achieved,
        "required_conductance_w_per_k": required,
        "conductance_margin_fraction": conductance_margin_fraction(achieved, required),
        "differential_expansion_m": slip,
        "alignment_contribution_arcsec": tilt,
        "compliant": conductance_ok and slip_ok and alignment_ok,
        "findings": findings,
    }


def assess_mechanical_interfaces(spec):
    """Run the full clause 4.3.2 mechanical interface assessment.

    spec keys: mounts (sequence of mount records), mass_allocation_kg,
    optional mass_contingency_fraction.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("mounts", "mass_allocation_kg"):
        if key not in spec:
            raise ValueError("spec missing required key %r" % key)
    mounts = spec["mounts"]
    if not isinstance(mounts, (list, tuple)) or not mounts:
        raise ValueError("spec['mounts'] must be a non-empty sequence")
    records = [assess_mount(mount) for mount in mounts]
    mass = interface_hardware_mass_kg(
        mounts, spec.get("mass_contingency_fraction", 0.0)
    )
    allocation = validate_positive("mass_allocation_kg", spec["mass_allocation_kg"])
    mass_ok = mass < allocation or math.isclose(
        mass, allocation, rel_tol=1e-12, abs_tol=0.0
    )
    findings = []
    for record in records:
        findings.extend(record["findings"])
    if not mass_ok:
        findings.append(
            "interface hardware mass %.4f kg exceeds the %.4f kg allocated by "
            "the structure subsystem" % (mass, allocation)
        )
    names = [record["name"] for record in records]
    if len(set(names)) != len(names):
        findings.append("two mounting interfaces share a name; records cannot be traced")
    return {
        "mounts": records,
        "interface_hardware_mass_kg": mass,
        "mass_allocation_kg": allocation,
        "mass_margin_fraction": (allocation - mass) / allocation,
        "compliant": all(record["compliant"] for record in records) and mass_ok
        and len(set(names)) == len(names),
        "findings": findings,
    }
