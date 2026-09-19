"""Specification check for a procured threaded fastener.

Anchor: ECSS-Q-ST-70-46 specifications clause (a fastener is procured against
a standard or specification that fixes its dimensions, its property class and
its material, not against a description). Paraphrased into an implementable
procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Check the purchase description against the fields a buyable specification
   needs, and report the gaps in the order the description is written in.
2. Parse the metric thread designation into its nominal diameter and pitch,
   taking the coarse pitch from a table when none is stated and refusing a
   diameter the table does not carry.
3. Read the strength out of the property class rather than a lookup: a carbon
   or alloy steel class encodes its nominal tensile strength in the first
   figure and the ratio of yield to tensile in the second, and an austenitic
   stainless class encodes its tensile strength directly.
4. Compute the tensile stress area from the diameter and pitch and turn the
   class into the proof load the fastener has to carry, so the description and
   the number a receiving inspection will check come from the same place.
5. Cross-check the class against the material family and the coating against
   the class, because a stainless class on an alloy-steel part and an
   embrittlement-prone coating on a high-strength class are both specifications
   that cannot be met.
"""

import math

__all__ = [
    "REQUIRED_FIELDS",
    "COARSE_PITCH_MM",
    "STRESS_AREA_PITCH_COEFFICIENT",
    "STAINLESS_CLASSES",
    "MATERIAL_FAMILIES",
    "COATINGS",
    "EMBRITTLEMENT_RISK_CLASS_MPA",
    "ELECTROPLATED_COATINGS",
    "coarse_pitch_for",
    "coarse_or_none",
    "parse_thread_designation",
    "parse_property_class",
    "tensile_stress_area_mm2",
    "proof_load_kn",
    "material_class_consistency",
    "coating_class_consistency",
    "missing_fields",
    "assess_specification",
]

# The fields a purchase description needs before anything can be bought.
REQUIRED_FIELDS = (
    "standard_reference",
    "thread_designation",
    "nominal_length_mm",
    "property_class",
    "material_family",
    "coating",
    "head_type",
    "locking_feature",
)

# ISO metric coarse pitches for the sizes a space fastener schedule uses.
COARSE_PITCH_MM = {
    1.6: 0.35,
    2.0: 0.4,
    2.5: 0.45,
    3.0: 0.5,
    4.0: 0.7,
    5.0: 0.8,
    6.0: 1.0,
    8.0: 1.25,
    10.0: 1.5,
    12.0: 1.75,
    14.0: 2.0,
    16.0: 2.0,
    20.0: 2.5,
    24.0: 3.0,
}

# The tensile stress area is taken on a diameter reduced by this multiple of
# the pitch, which is the standard basic-plus-minor mean construction.
STRESS_AREA_PITCH_COEFFICIENT = 0.9382

# Austenitic stainless classes: nominal tensile and yield strength in MPa.
STAINLESS_CLASSES = {
    "a2-50": (500.0, 210.0),
    "a2-70": (700.0, 450.0),
    "a2-80": (800.0, 600.0),
    "a4-50": (500.0, 210.0),
    "a4-70": (700.0, 450.0),
    "a4-80": (800.0, 600.0),
}

MATERIAL_FAMILIES = (
    "carbon-steel",
    "alloy-steel",
    "austenitic-stainless",
    "precipitation-hardening-stainless",
    "titanium",
    "nickel-alloy",
    "aluminium",
)

COATINGS = (
    "none",
    "passivated",
    "anodised",
    "dry-film-lubricant",
    "electroplated-cadmium",
    "electroplated-zinc",
    "ion-vapour-deposited-aluminium",
    "silver-plated",
)

# Above this nominal tensile strength an electroplated coating puts hydrogen
# into a part that is susceptible to it.
EMBRITTLEMENT_RISK_CLASS_MPA = 1000.0

ELECTROPLATED_COATINGS = ("electroplated-cadmium", "electroplated-zinc")

_STEEL_FAMILIES = ("carbon-steel", "alloy-steel")


def _clean_token(value, label):
    """Return a non-empty lowercase token, raising on anything else."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    token = value.strip().lower()
    if not token:
        raise ValueError("%s must not be blank" % label)
    return token


def _positive(value, label):
    """Return a strictly positive finite float, raising on anything else."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    if number <= 0.0:
        raise ValueError("%s must be positive, got %g" % (label, number))
    return number


def coarse_pitch_for(diameter_mm):
    """Return the ISO metric coarse pitch tabulated for a nominal diameter."""
    diameter = _positive(diameter_mm, "diameter_mm")
    for tabulated, pitch in sorted(COARSE_PITCH_MM.items()):
        if math.isclose(diameter, tabulated, rel_tol=0.0, abs_tol=1e-9):
            return pitch
    raise ValueError(
        "no coarse pitch is tabulated for M%g; the specification must state the pitch"
        % diameter
    )


def parse_thread_designation(designation):
    """Return the nominal diameter and pitch of a metric thread designation."""
    token = _clean_token(designation, "thread_designation").replace(" ", "")
    if not token.startswith("m"):
        raise ValueError(
            "thread designation %r is not metric; it must start with M" % (designation,)
        )
    body = token[1:].replace("*", "x")
    if not body:
        raise ValueError("thread designation %r carries no size" % (designation,))
    parts = body.split("x")
    if len(parts) > 2:
        raise ValueError("thread designation %r states more than one pitch" % (designation,))
    try:
        diameter = float(parts[0])
    except ValueError:
        raise ValueError("thread designation %r has a non-numeric diameter" % (designation,))
    if not math.isfinite(diameter) or diameter <= 0.0:
        raise ValueError("thread diameter in %r must be positive" % (designation,))
    if len(parts) == 1:
        pitch = coarse_pitch_for(diameter)
        stated = False
    else:
        try:
            pitch = float(parts[1])
        except ValueError:
            raise ValueError("thread designation %r has a non-numeric pitch" % (designation,))
        if not math.isfinite(pitch) or pitch <= 0.0:
            raise ValueError("thread pitch in %r must be positive" % (designation,))
        if pitch >= diameter:
            raise ValueError(
                "pitch %g mm is not smaller than the diameter %g mm in %r"
                % (pitch, diameter, designation)
            )
        stated = True
    return {
        "nominal_diameter_mm": diameter,
        "pitch_mm": pitch,
        "pitch_stated": stated,
        "series": "fine" if stated and pitch < coarse_or_none(diameter) else "coarse",
    }


def coarse_or_none(diameter):
    """Return the tabulated coarse pitch, or infinity when none is tabulated."""
    try:
        return coarse_pitch_for(diameter)
    except ValueError:
        return float("inf")


def parse_property_class(property_class):
    """Return the nominal tensile and yield strength a property class encodes."""
    token = _clean_token(property_class, "property_class")
    if token in STAINLESS_CLASSES:
        tensile, yield_strength = STAINLESS_CLASSES[token]
        return {
            "property_class": token,
            "family_group": "austenitic-stainless",
            "tensile_strength_mpa": tensile,
            "yield_strength_mpa": yield_strength,
        }
    if token.count(".") != 1:
        raise ValueError(
            "property class %r is neither a steel class such as 10.9 nor a tabulated "
            "stainless class" % (property_class,)
        )
    head, tail = token.split(".")
    if not head.isdigit() or not tail.isdigit():
        raise ValueError("property class %r has non-numeric figures" % (property_class,))
    first = int(head)
    second = int(tail)
    if first < 3 or first > 14:
        raise ValueError(
            "property class %r has an out-of-range strength figure" % (property_class,)
        )
    if second < 1 or second > 9:
        raise ValueError(
            "property class %r has an out-of-range ratio figure" % (property_class,)
        )
    tensile = first * 100.0
    return {
        "property_class": token,
        "family_group": "steel",
        "tensile_strength_mpa": tensile,
        "yield_strength_mpa": tensile * second / 10.0,
    }


def tensile_stress_area_mm2(diameter_mm, pitch_mm):
    """Return the tensile stress area of a metric thread."""
    diameter = _positive(diameter_mm, "diameter_mm")
    pitch = _positive(pitch_mm, "pitch_mm")
    if pitch >= diameter:
        raise ValueError(
            "pitch %g mm is not smaller than the diameter %g mm" % (pitch, diameter)
        )
    effective = diameter - STRESS_AREA_PITCH_COEFFICIENT * pitch
    return math.pi * effective * effective / 4.0


def proof_load_kn(property_class, diameter_mm, pitch_mm, proof_ratio=0.9):
    """Return the proof load a fastener of this class and size has to carry."""
    strengths = parse_property_class(property_class)
    if not isinstance(proof_ratio, (int, float)) or isinstance(proof_ratio, bool):
        raise ValueError("proof_ratio must be a real number")
    ratio = float(proof_ratio)
    if not math.isfinite(ratio) or ratio <= 0.0 or ratio > 1.0:
        raise ValueError("proof_ratio must lie in (0, 1], got %r" % (proof_ratio,))
    area = tensile_stress_area_mm2(diameter_mm, pitch_mm)
    proof_stress = strengths["yield_strength_mpa"] * ratio
    return {
        "stress_area_mm2": area,
        "proof_stress_mpa": proof_stress,
        "proof_load_kn": area * proof_stress / 1000.0,
        "tensile_load_kn": area * strengths["tensile_strength_mpa"] / 1000.0,
    }


def material_class_consistency(material_family, property_class):
    """Return the findings raised by pairing this class with this material."""
    family = _clean_token(material_family, "material_family")
    if family not in MATERIAL_FAMILIES:
        raise ValueError(
            "unknown material family %r; recognised families are %s"
            % (material_family, ", ".join(MATERIAL_FAMILIES))
        )
    strengths = parse_property_class(property_class)
    findings = []
    if strengths["family_group"] == "austenitic-stainless" and family != "austenitic-stainless":
        findings.append(
            "property class %s is an austenitic stainless class and the material is %s"
            % (strengths["property_class"], family)
        )
    if strengths["family_group"] == "steel" and family not in _STEEL_FAMILIES:
        findings.append(
            "property class %s is a carbon or alloy steel class and the material is %s"
            % (strengths["property_class"], family)
        )
    if (
        family == "carbon-steel"
        and strengths["tensile_strength_mpa"] > 800.0
    ):
        findings.append(
            "property class %s asks %g MPa, beyond what plain carbon steel reaches"
            % (strengths["property_class"], strengths["tensile_strength_mpa"])
        )
    return findings


def coating_class_consistency(coating, property_class):
    """Return the findings raised by pairing this coating with this class."""
    token = _clean_token(coating, "coating")
    if token not in COATINGS:
        raise ValueError(
            "unknown coating %r; recognised coatings are %s"
            % (coating, ", ".join(COATINGS))
        )
    strengths = parse_property_class(property_class)
    findings = []
    tensile = strengths["tensile_strength_mpa"]
    at_or_above = tensile > EMBRITTLEMENT_RISK_CLASS_MPA or math.isclose(
        tensile, EMBRITTLEMENT_RISK_CLASS_MPA, rel_tol=0.0, abs_tol=1e-9
    )
    if token in ELECTROPLATED_COATINGS and at_or_above:
        findings.append(
            "%s on property class %s puts hydrogen into a part at %g MPa; specify a "
            "non-electroplated finish or an embrittlement relief bake with its own test"
            % (token, strengths["property_class"], tensile)
        )
    if token == "electroplated-cadmium":
        findings.append(
            "cadmium is restricted on space hardware for outgassing and substance reasons; "
            "state the justification or specify an alternative"
        )
    if token == "anodised" and strengths["family_group"] == "steel":
        findings.append(
            "anodising is an aluminium finish and property class %s is a steel class"
            % strengths["property_class"]
        )
    return findings


def missing_fields(specification):
    """Return the required fields the purchase description does not carry."""
    if not isinstance(specification, dict):
        raise ValueError("specification must be a mapping")
    gaps = []
    for field in REQUIRED_FIELDS:
        value = specification.get(field)
        if value is None:
            gaps.append(field)
            continue
        if isinstance(value, str) and not value.strip():
            gaps.append(field)
    return gaps


def assess_specification(specification):
    """Run the full specifications-clause check on one purchase description."""
    gaps = missing_fields(specification)
    findings = ["purchase description does not state '%s'" % field for field in gaps]
    if gaps:
        return {
            "missing_fields": gaps,
            "thread": None,
            "strengths": None,
            "loads": None,
            "findings": findings,
            "buyable": False,
        }
    thread = parse_thread_designation(specification["thread_designation"])
    strengths = parse_property_class(specification["property_class"])
    loads = proof_load_kn(
        specification["property_class"],
        thread["nominal_diameter_mm"],
        thread["pitch_mm"],
        specification.get("proof_ratio", 0.9),
    )
    length = _positive(specification["nominal_length_mm"], "nominal_length_mm")
    if length < thread["nominal_diameter_mm"]:
        findings.append(
            "nominal length %g mm is shorter than the nominal diameter %g mm"
            % (length, thread["nominal_diameter_mm"])
        )
    findings.extend(
        material_class_consistency(
            specification["material_family"], specification["property_class"]
        )
    )
    findings.extend(
        coating_class_consistency(
            specification["coating"], specification["property_class"]
        )
    )
    return {
        "missing_fields": gaps,
        "thread": thread,
        "strengths": strengths,
        "loads": loads,
        "nominal_length_mm": length,
        "findings": findings,
        "buyable": not findings,
    }
