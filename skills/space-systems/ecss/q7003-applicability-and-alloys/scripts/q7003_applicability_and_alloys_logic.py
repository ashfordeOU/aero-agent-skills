"""Applicability of black anodizing with inorganic dyes to a metal part.

Anchor: ECSS-Q-ST-70-03C, applicability clause (paraphrased into an
implementable decision; no standard text is reproduced).

Decision implemented here:

1. Categorize the base metal. The process is an anodic one, so it only
   has a substrate on aluminium and its alloys. Inside aluminium the
   family decides how well a dense, dyeable coating forms: the low
   alloyed, manganese and magnesium bearing wrought families take the
   coating readily; the copper bearing and the high silicon families
   grow a coating that is thinner, more porous and harder to dye
   evenly, so they are open only through a qualification programme on
   the actual alloy and temper.
2. Look at the condition the part arrives in. An existing organic or
   conversion coating has to come off first, a previously anodized
   surface has to be stripped, and a closed assembly that can trap
   process chemistry is outside the process until it is vented or the
   parts are treated loose.
3. Look at what the surface is for. A black anodic coating is an
   electrical insulator, so a face that has to stay conductive for
   bonding or grounding is either masked or the part is out.
4. Look at the tolerance. The coating grows outward as well as inward,
   so the specified thickness adds to every treated surface and twice
   that to an outside diameter. A part whose drawing allowance cannot
   take that growth is not a candidate at the specified thickness.
5. Report one verdict per part with the duties a conditional case
   carries, and one verdict for the batch.

Stdlib only, offline, deterministic.
"""

PERMITTED = "permitted"
QUALIFICATION_REQUIRED = "permitted-with-qualification"
NOT_PERMITTED = "not-permitted"

# Fraction of the anodic coating thickness that grows outward from the
# original surface; the remainder is consumed from the base metal.
OUTWARD_GROWTH_FRACTION = 0.5

# Wrought aluminium families keyed by the leading digit of the
# designation, with the applicability each family carries.
WROUGHT_FAMILY_APPLICABILITY = {
    "1": PERMITTED,
    "3": PERMITTED,
    "5": PERMITTED,
    "6": PERMITTED,
    "2": QUALIFICATION_REQUIRED,
    "4": QUALIFICATION_REQUIRED,
    "7": QUALIFICATION_REQUIRED,
    "8": QUALIFICATION_REQUIRED,
}

# Composition thresholds above which a cast or wrought alloy needs a
# qualification programme whatever its family digit says, in mass per
# cent.
COPPER_QUALIFICATION_PERCENT = 0.6
SILICON_QUALIFICATION_PERCENT = 7.0

VALID_PRODUCT_FORMS = ("wrought", "cast")

SURFACE_CONDITIONS = {
    "bare-machined": [],
    "bare-rolled": [],
    "chemical-conversion-coated": ["existing-conversion-coating-to-be-stripped"],
    "previously-anodized": ["existing-anodic-coating-to-be-stripped"],
    "painted": ["organic-coating-to-be-stripped"],
    "shot-peened": [],
}

ASSEMBLY_STATES = {
    "single-piece": [],
    "vented-assembly": ["vented-assembly-needs-a-drain-and-rinse-route"],
    "closed-assembly": None,  # entrapment, process closed
    "dissimilar-metal-assembly": None,
}

SURFACE_FUNCTIONS = {
    "thermal-optical-control": [],
    "stray-light-control": [],
    "decorative": [],
    "wear-surface": [],
    "electrical-bonding-face": ["bonding-face-to-be-masked-or-the-part-is-out"],
    "adhesive-bond-face": ["adhesive-bond-face-needs-a-qualified-primer-route"],
}

# A growth figure is a product of two floats, so a part sitting exactly
# on its allowance can land a few units in the last place above it. A
# picometre is far below any drawing tolerance and absorbs that
# representation error without relaxing the allowance itself.
GROWTH_TOLERANCE_UM = 1.0e-9

MIN_COATING_THICKNESS_UM = 2.0
MAX_COATING_THICKNESS_UM = 25.0


def _numeric(label, value, minimum=None, maximum=None):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be numeric, got %r" % (label, value))
    value = float(value)
    if minimum is not None and value < minimum:
        raise ValueError("%s must be >= %r, got %r" % (label, minimum, value))
    if maximum is not None and value > maximum:
        raise ValueError("%s must be <= %r, got %r" % (label, maximum, value))
    return value


def normalize_designation(alloy):
    """Strip the registry prefixes off an alloy designation."""
    if not isinstance(alloy, str) or not alloy.strip():
        raise ValueError("alloy designation must be a non-empty string")
    text = alloy.strip().upper()
    for prefix in ("EN AW-", "EN AC-", "AA", "AL "):
        if text.startswith(prefix):
            text = text[len(prefix):]
            break
    text = text.strip()
    if not text:
        raise ValueError("alloy designation is empty after the registry prefix")
    return text


def wrought_family(alloy):
    """Leading family digit of a wrought aluminium designation."""
    text = normalize_designation(alloy)
    digits = "".join(ch for ch in text if ch.isdigit())
    if len(digits) < 4:
        raise ValueError(
            "wrought designation %r does not carry a four-digit number" % (alloy,)
        )
    family = digits[0]
    if family not in WROUGHT_FAMILY_APPLICABILITY:
        raise ValueError("unknown wrought aluminium family %r" % (family,))
    return family


def alloy_applicability(alloy, product_form, copper_percent=0.0,
                        silicon_percent=0.0):
    """Applicability the base metal alone carries, plus its reasons."""
    if product_form not in VALID_PRODUCT_FORMS:
        raise ValueError(
            "product_form must be one of %s, got %r"
            % (", ".join(VALID_PRODUCT_FORMS), product_form)
        )
    copper = _numeric("copper_percent", copper_percent, 0.0, 100.0)
    silicon = _numeric("silicon_percent", silicon_percent, 0.0, 100.0)
    reasons = []
    if product_form == "wrought":
        verdict = WROUGHT_FAMILY_APPLICABILITY[wrought_family(alloy)]
        if verdict == QUALIFICATION_REQUIRED:
            reasons.append("wrought-family-grows-a-poorly-dyeable-coating")
    else:
        normalize_designation(alloy)
        verdict = QUALIFICATION_REQUIRED
        reasons.append("cast-alloy-porosity-needs-a-qualification-programme")
    if copper > COPPER_QUALIFICATION_PERCENT:
        verdict = QUALIFICATION_REQUIRED
        reasons.append("copper-content-above-the-qualification-threshold")
    if silicon > SILICON_QUALIFICATION_PERCENT:
        verdict = QUALIFICATION_REQUIRED
        reasons.append("silicon-content-above-the-qualification-threshold")
    return verdict, reasons


def outward_growth_um(coating_thickness_um):
    """Growth added to one treated surface by the coating, in micrometres."""
    thickness = _numeric("coating_thickness_um", coating_thickness_um, 0.0)
    return OUTWARD_GROWTH_FRACTION * thickness


def feature_growth_um(coating_thickness_um, feature):
    """Growth the coating adds to a named feature, in micrometres."""
    per_surface = outward_growth_um(coating_thickness_um)
    if feature == "surface":
        return per_surface
    if feature == "outside-diameter":
        return 2.0 * per_surface
    if feature == "bore-diameter":
        return -2.0 * per_surface
    if feature == "slot-width":
        return -2.0 * per_surface
    raise ValueError("unknown feature %r" % (feature,))


def validate_part(part):
    """Validate one candidate part record and return a normalized copy."""
    if not isinstance(part, dict):
        raise ValueError("part must be a mapping")
    part_id = part.get("id")
    if not isinstance(part_id, str) or not part_id.strip():
        raise ValueError("part needs a non-empty string id")
    base_metal = part.get("base_metal", "aluminium")
    if not isinstance(base_metal, str) or not base_metal.strip():
        raise ValueError("part %s needs a non-empty base_metal" % part_id)
    product_form = part.get("product_form", "wrought")
    if product_form not in VALID_PRODUCT_FORMS:
        raise ValueError(
            "part %s has unknown product_form %r" % (part_id, product_form)
        )
    surface_condition = part.get("surface_condition", "bare-machined")
    if surface_condition not in SURFACE_CONDITIONS:
        raise ValueError(
            "part %s has unknown surface_condition %r" % (part_id, surface_condition)
        )
    assembly_state = part.get("assembly_state", "single-piece")
    if assembly_state not in ASSEMBLY_STATES:
        raise ValueError(
            "part %s has unknown assembly_state %r" % (part_id, assembly_state)
        )
    surface_function = part.get("surface_function", "thermal-optical-control")
    if surface_function not in SURFACE_FUNCTIONS:
        raise ValueError(
            "part %s has unknown surface_function %r" % (part_id, surface_function)
        )
    feature = part.get("feature", "surface")
    thickness = _numeric(
        "part %s coating_thickness_um" % part_id,
        part.get("coating_thickness_um", 10.0),
        0.0,
    )
    allowance = _numeric(
        "part %s dimensional_allowance_um" % part_id,
        part.get("dimensional_allowance_um", 0.0),
        0.0,
    )
    masked = part.get("bonding_face_masked", False)
    if not isinstance(masked, bool):
        raise ValueError("part %s bonding_face_masked must be a boolean" % part_id)
    return {
        "id": part_id.strip(),
        "base_metal": base_metal.strip().lower(),
        "alloy": part.get("alloy", "6061-T6"),
        "product_form": product_form,
        "copper_percent": _numeric(
            "part %s copper_percent" % part_id, part.get("copper_percent", 0.0), 0.0
        ),
        "silicon_percent": _numeric(
            "part %s silicon_percent" % part_id, part.get("silicon_percent", 0.0), 0.0
        ),
        "surface_condition": surface_condition,
        "assembly_state": assembly_state,
        "surface_function": surface_function,
        "feature": feature,
        "coating_thickness_um": thickness,
        "dimensional_allowance_um": allowance,
        "bonding_face_masked": masked,
    }


def dimensional_check(part):
    """Growth, allowance and findings for the tolerance of one part."""
    norm = validate_part(part)
    growth = abs(
        feature_growth_um(norm["coating_thickness_um"], norm["feature"])
    )
    allowance = norm["dimensional_allowance_um"]
    findings = []
    if growth > allowance + GROWTH_TOLERANCE_UM:
        findings.append("coating-growth-exceeds-the-drawing-allowance")
    return {"growth_um": growth, "allowance_um": allowance, "findings": findings}


def thickness_findings(coating_thickness_um):
    """Findings about a specified coating thickness."""
    thickness = _numeric("coating_thickness_um", coating_thickness_um, 0.0)
    findings = []
    if thickness < MIN_COATING_THICKNESS_UM:
        findings.append("specified-thickness-below-the-dyeable-band")
    if thickness > MAX_COATING_THICKNESS_UM:
        findings.append("specified-thickness-above-the-process-band")
    return findings


def _worst(a, b):
    order = {PERMITTED: 0, QUALIFICATION_REQUIRED: 1, NOT_PERMITTED: 2}
    return a if order[a] >= order[b] else b


def assess_part(part):
    """Assess one part against the applicability clause."""
    norm = validate_part(part)
    reasons = []
    duties = []
    if norm["base_metal"] != "aluminium":
        return {
            "id": norm["id"],
            "verdict": NOT_PERMITTED,
            "reasons": ["base-metal-is-not-aluminium"],
            "duties": [],
            "growth_um": 0.0,
            "allowance_um": norm["dimensional_allowance_um"],
        }
    verdict, alloy_reasons = alloy_applicability(
        norm["alloy"],
        norm["product_form"],
        norm["copper_percent"],
        norm["silicon_percent"],
    )
    reasons.extend(alloy_reasons)

    condition_duties = SURFACE_CONDITIONS[norm["surface_condition"]]
    duties.extend(condition_duties)

    assembly_duties = ASSEMBLY_STATES[norm["assembly_state"]]
    if assembly_duties is None:
        verdict = NOT_PERMITTED
        if norm["assembly_state"] == "closed-assembly":
            reasons.append("closed-assembly-traps-process-chemistry")
        else:
            reasons.append("dissimilar-metal-assembly-attacked-by-the-bath")
    else:
        duties.extend(assembly_duties)

    function_duties = SURFACE_FUNCTIONS[norm["surface_function"]]
    if norm["surface_function"] == "electrical-bonding-face":
        if norm["bonding_face_masked"]:
            duties.extend(function_duties)
        else:
            verdict = NOT_PERMITTED
            reasons.append("unmasked-bonding-face-would-be-insulated")
    else:
        duties.extend(function_duties)

    dim = dimensional_check(norm)
    if dim["findings"]:
        verdict = NOT_PERMITTED
        reasons.extend(dim["findings"])

    band = thickness_findings(norm["coating_thickness_um"])
    if band:
        verdict = _worst(verdict, QUALIFICATION_REQUIRED)
        reasons.extend(band)

    return {
        "id": norm["id"],
        "verdict": verdict,
        "reasons": reasons,
        "duties": duties,
        "growth_um": dim["growth_um"],
        "allowance_um": dim["allowance_um"],
    }


def assess_applicability(parts):
    """Run the applicability assessment over a list of candidate parts."""
    if not isinstance(parts, list) or not parts:
        raise ValueError("parts must be a non-empty list")
    results = []
    seen = set()
    for part in parts:
        result = assess_part(part)
        if result["id"] in seen:
            raise ValueError("duplicate part id %r" % (result["id"],))
        seen.add(result["id"])
        results.append(result)
    return {
        "parts": results,
        "permitted_ids": [r["id"] for r in results if r["verdict"] == PERMITTED],
        "qualification_ids": [
            r["id"] for r in results if r["verdict"] == QUALIFICATION_REQUIRED
        ],
        "rejected_ids": [r["id"] for r in results if r["verdict"] == NOT_PERMITTED],
        "batch_clear": all(r["verdict"] == PERMITTED for r in results),
    }
