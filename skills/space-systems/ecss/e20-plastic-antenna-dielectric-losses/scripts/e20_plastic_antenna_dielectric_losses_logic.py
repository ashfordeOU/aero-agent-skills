#!/usr/bin/env python3
"""Dielectric loss of plastic parts sitting in the radio-frequency path.

Anchor: ECSS-E-ST-20C clause 7.2.2.4.3 (paraphrased into an implementable
procedure; no verbatim standard text).

The module turns the clause into a cascaded chain walk:

1. categorize each plastic part and drop the ones that sit outside the
   radiating field;
2. derive the attenuation constant of the material from its relative
   permittivity and loss-tangent at the operating frequency;
3. stretch the geometric thickness into a refracted path by the incidence
   angle and turn it into an absorption loss;
4. add the interface mismatch of an untuned slab, which is reflected rather
   than dissipated;
5. cascade the surviving level down the chain, convert what each part
   absorbs into a temperature rise through its thermal-resistance, and check
   the chain loss and every part temperature against their limits.

Deterministic, offline, python3 standard library only.
"""

import math

SPEED_OF_LIGHT_M_PER_S = 299792458.0
NEPER_TO_DECIBEL = 20.0 * math.log10(math.e)

# Absorb the representation error of a decibel sum and of a temperature that
# is a sum of products. They never move an engineering limit.
DECIBEL_TOLERANCE_DB = 1e-9
TEMPERATURE_TOLERANCE_K = 1e-9

# Plastic part families and whether the radiating field passes through them.
PLASTIC_PART_FAMILIES = {
    "radome": True,
    "lens": True,
    "matching-layer": True,
    "waveguide-window": True,
    "feed-support-insulator": True,
    "structural-bracket-outside-field": False,
    "harness-standoff-outside-field": False,
}


def _finite(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return out


def _positive(value, label):
    out = _finite(value, label)
    if out <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (label, value))
    return out


def _non_negative(value, label):
    out = _finite(value, label)
    if out < 0.0:
        raise ValueError("%s cannot be negative, got %r" % (label, value))
    return out


def _permittivity(value):
    out = _finite(value, "relative_permittivity")
    if out < 1.0:
        raise ValueError("relative_permittivity must be at least 1.0, got %r" % (value,))
    return out


def _loss_tangent(value):
    out = _non_negative(value, "loss_tangent")
    if out >= 1.0:
        raise ValueError(
            "loss_tangent %r is not a low-loss plastic; the part has to be treated "
            "as a lossy medium in its own right" % (value,)
        )
    return out


def categorize_plastic_part(part_type):
    """Categorize a plastic part and say whether the field passes through it."""
    if not isinstance(part_type, str) or not part_type.strip():
        raise ValueError("part_type must be a non-empty string, got %r" % (part_type,))
    key = part_type.strip().lower()
    if key not in PLASTIC_PART_FAMILIES:
        raise ValueError(
            "uncategorized plastic part %r; known families: %s"
            % (part_type, ", ".join(sorted(PLASTIC_PART_FAMILIES)))
        )
    return {"part_type": key, "in_rf_path": PLASTIC_PART_FAMILIES[key]}


def attenuation_np_per_m(frequency_hz, relative_permittivity, loss_tangent):
    """Attenuation constant of a low-loss dielectric, in nepers per metre."""
    frequency = _positive(frequency_hz, "frequency_hz")
    permittivity = _permittivity(relative_permittivity)
    tangent = _loss_tangent(loss_tangent)
    free_space_wavelength = SPEED_OF_LIGHT_M_PER_S / frequency
    return math.pi * math.sqrt(permittivity) * tangent / free_space_wavelength


def refracted_path_length_m(thickness_m, relative_permittivity, incidence_angle_deg=0.0):
    """Path the wave actually travels inside a slab of the given thickness."""
    thickness = _non_negative(thickness_m, "thickness_m")
    permittivity = _permittivity(relative_permittivity)
    angle = _finite(incidence_angle_deg, "incidence_angle_deg")
    if not 0.0 <= angle < 90.0:
        raise ValueError(
            "incidence_angle_deg must sit in [0, 90), got %r" % (incidence_angle_deg,)
        )
    sine_refracted = math.sin(math.radians(angle)) / math.sqrt(permittivity)
    cosine_refracted = math.sqrt(1.0 - sine_refracted * sine_refracted)
    return thickness / cosine_refracted


def absorption_loss_db(
    thickness_m,
    relative_permittivity,
    loss_tangent,
    frequency_hz,
    incidence_angle_deg=0.0,
):
    """Loss the part dissipates as heat over its refracted path."""
    path = refracted_path_length_m(
        thickness_m, relative_permittivity, incidence_angle_deg
    )
    if path == 0.0:
        return 0.0
    alpha = attenuation_np_per_m(frequency_hz, relative_permittivity, loss_tangent)
    return NEPER_TO_DECIBEL * alpha * path


def interface_mismatch_loss_db(relative_permittivity):
    """Loss an untuned slab reflects at its two air interfaces.

    This part of the budget is returned towards the source, not turned into
    heat, so it never feeds the thermal check.
    """
    permittivity = _permittivity(relative_permittivity)
    index = math.sqrt(permittivity)
    reflection = (1.0 - index) / (1.0 + index)
    transmitted_fraction = (1.0 - reflection * reflection) ** 2
    if transmitted_fraction <= 0.0:
        raise ValueError(
            "relative_permittivity %r leaves no transmitted field" % (relative_permittivity,)
        )
    return -10.0 * math.log10(transmitted_fraction)


def dissipated_power_w(input_power_w, absorption_loss_value_db):
    """Power a part turns into heat for a given absorption loss."""
    power = _positive(input_power_w, "input_power_w")
    loss = _non_negative(absorption_loss_value_db, "absorption_loss_db")
    return power * (1.0 - 10.0 ** (-loss / 10.0))


def temperature_rise_k(dissipated_power_value_w, thermal_resistance_k_per_w):
    """Steady-state rise of the part above its mounting interface."""
    dissipated = _non_negative(dissipated_power_value_w, "dissipated_power_w")
    resistance = _non_negative(thermal_resistance_k_per_w, "thermal_resistance_k_per_w")
    return dissipated * resistance


def _validate_part(part):
    if not isinstance(part, dict):
        raise ValueError("each part must be a mapping, got %r" % (part,))
    label = part.get("label")
    if not isinstance(label, str) or not label.strip():
        raise ValueError("each part needs a non-empty label, got %r" % (label,))
    return label.strip()


def assess_plastic_dielectric_losses(
    parts,
    frequency_hz,
    input_power_w,
    allocated_path_loss_db,
    baseline_temperature_k=293.15,
):
    """Run the whole clause 7.2.2.4.3 assessment and return the findings."""
    if not isinstance(parts, (list, tuple)) or not parts:
        raise ValueError("parts must be a non-empty list of part mappings")
    frequency = _positive(frequency_hz, "frequency_hz")
    allocation = _positive(allocated_path_loss_db, "allocated_path_loss_db")
    baseline = _positive(baseline_temperature_k, "baseline_temperature_k")
    level_w = _positive(input_power_w, "input_power_w")

    findings = []
    reports = []
    total_loss_db = 0.0

    for part in parts:
        label = _validate_part(part)
        family = categorize_plastic_part(part.get("part_type"))
        if not family["in_rf_path"]:
            reports.append(
                {
                    "label": label,
                    "part_type": family["part_type"],
                    "in_rf_path": False,
                    "mismatch_loss_db": 0.0,
                    "absorption_loss_db": 0.0,
                    "dissipated_power_w": 0.0,
                    "temperature_k": baseline,
                }
            )
            continue

        thickness = _positive(part.get("thickness_m"), "thickness_m")
        permittivity = _permittivity(part.get("relative_permittivity"))
        tangent = _loss_tangent(part.get("loss_tangent"))
        angle = _finite(part.get("incidence_angle_deg", 0.0), "incidence_angle_deg")
        matched = part.get("impedance_matched", False)
        if not isinstance(matched, bool):
            raise ValueError("impedance_matched must be a boolean, got %r" % (matched,))
        resistance = _non_negative(
            part.get("thermal_resistance_k_per_w", 0.0), "thermal_resistance_k_per_w"
        )
        maximum_use_temperature = _positive(
            part.get("maximum_use_temperature_k"), "maximum_use_temperature_k"
        )

        mismatch_db = 0.0 if matched else interface_mismatch_loss_db(permittivity)
        absorption_db = absorption_loss_db(
            thickness, permittivity, tangent, frequency, angle
        )

        after_mismatch_w = level_w * 10.0 ** (-mismatch_db / 10.0)
        dissipated_w = dissipated_power_w(after_mismatch_w, absorption_db)
        rise_k = temperature_rise_k(dissipated_w, resistance)
        temperature_k = baseline + rise_k
        thermally_compliant = temperature_k <= maximum_use_temperature or math.isclose(
            temperature_k,
            maximum_use_temperature,
            rel_tol=0.0,
            abs_tol=TEMPERATURE_TOLERANCE_K,
        )
        if not thermally_compliant:
            findings.append(
                "part %s reaches %.3f K against a maximum-use-temperature of %.3f K"
                % (label, temperature_k, maximum_use_temperature)
            )

        part_loss_db = mismatch_db + absorption_db
        total_loss_db += part_loss_db
        level_w = level_w * 10.0 ** (-part_loss_db / 10.0)

        reports.append(
            {
                "label": label,
                "part_type": family["part_type"],
                "in_rf_path": True,
                "mismatch_loss_db": mismatch_db,
                "absorption_loss_db": absorption_db,
                "part_loss_db": part_loss_db,
                "dissipated_power_w": dissipated_w,
                "temperature_rise_k": rise_k,
                "temperature_k": temperature_k,
                "maximum_use_temperature_k": maximum_use_temperature,
                "thermally_compliant": thermally_compliant,
                "power_leaving_w": level_w,
            }
        )

    within_allocation = total_loss_db <= allocation or math.isclose(
        total_loss_db, allocation, rel_tol=0.0, abs_tol=DECIBEL_TOLERANCE_DB
    )
    if not within_allocation:
        findings.append(
            "chain costs %.4f dB against an allocation of %.4f dB"
            % (total_loss_db, allocation)
        )

    return {
        "frequency_hz": frequency,
        "parts": reports,
        "total_loss_db": total_loss_db,
        "allocated_path_loss_db": allocation,
        "within_allocation": within_allocation,
        "power_delivered_w": level_w,
        "findings": findings,
        "compliant": not findings,
    }
