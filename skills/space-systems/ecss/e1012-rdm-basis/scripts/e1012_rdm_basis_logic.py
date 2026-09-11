"""
ECSS-E-ST-10-12C §5.1.1 — Radiation Design Margin (RDM) requirement basis.

Derives the component radiation withstand requirement by applying the RDM
factor to the mission radiation environment specification, then checks
compliance of a given component tolerance against each derived level.
"""

MINIMUM_RDM_FACTOR = 2.0

REQUIRED_PARAMETERS = frozenset(
    {"total_ionising_dose", "proton_fluence", "electron_fluence"}
)


class RdmError(ValueError):
    """Raised when inputs are invalid or the RDM basis cannot be formed."""


def validate_environment_spec(env_spec):
    """
    Validate and return a cleaned copy of the radiation environment specification.

    Expected keys (all required, all positive):
      total_ionising_dose  — cumulative TID, krad
      proton_fluence       — integral proton fluence, cm^-2
      electron_fluence     — integral electron fluence, cm^-2

    Returns dict with float-cast values.
    Raises RdmError on any missing, non-numeric, or non-positive value.
    """
    if not isinstance(env_spec, dict):
        raise RdmError(
            f"env_spec must be a dict, got {type(env_spec).__name__}"
        )
    result = {}
    for key in REQUIRED_PARAMETERS:
        if key not in env_spec:
            raise RdmError(f"Missing required parameter in env_spec: '{key}'")
        raw = env_spec[key]
        try:
            val = float(raw)
        except (TypeError, ValueError):
            raise RdmError(
                f"env_spec['{key}'] must be numeric, got {raw!r}"
            )
        if val <= 0.0:
            raise RdmError(
                f"env_spec['{key}'] must be positive (> 0), got {val}"
            )
        result[key] = val
    return result


def validate_rdm_factor(rdm_factor):
    """
    Validate and return float(rdm_factor).

    The factor must be numeric and >= MINIMUM_RDM_FACTOR (2.0) per
    ECSS-E-ST-10-12C §5.1.1.  A factor below this threshold is not
    admissible and raises RdmError.
    """
    try:
        factor = float(rdm_factor)
    except (TypeError, ValueError):
        raise RdmError(
            f"rdm_factor must be numeric, got {rdm_factor!r}"
        )
    if factor < MINIMUM_RDM_FACTOR:
        raise RdmError(
            f"rdm_factor {factor} is below the ECSS minimum "
            f"({MINIMUM_RDM_FACTOR}); rejected"
        )
    return factor


def compute_required_levels(env_spec, rdm_factor):
    """
    Apply rdm_factor to every parameter in env_spec.

    Returns dict mapping parameter name -> required withstand level in
    the same unit as the corresponding input value.
    """
    spec = validate_environment_spec(env_spec)
    factor = validate_rdm_factor(rdm_factor)
    return {param: value * factor for param, value in spec.items()}


def check_component_compliance(component_withstand, required_levels):
    """
    Compare component tolerance values against the required withstand levels.

    Parameters
    ----------
    component_withstand : dict
        Mapping of parameter name -> component radiation tolerance.
        A parameter absent from this dict is treated as an open finding.
    required_levels : dict
        Output of compute_required_levels.

    Returns
    -------
    list of finding dicts, one per parameter in required_levels:
        parameter    — parameter name
        required     — required withstand level
        withstand    — component tolerance (None if absent)
        compliant    — True / False
        margin_ratio — withstand / required (None if withstand absent)
        note         — short status string
    """
    findings = []
    for param, required in required_levels.items():
        if param not in component_withstand:
            findings.append(
                {
                    "parameter": param,
                    "required": required,
                    "withstand": None,
                    "compliant": False,
                    "margin_ratio": None,
                    "note": "no withstand value on record",
                }
            )
            continue

        raw = component_withstand[param]
        try:
            withstand = float(raw)
        except (TypeError, ValueError):
            raise RdmError(
                f"component_withstand['{param}'] must be numeric, got {raw!r}"
            )
        if withstand <= 0.0:
            raise RdmError(
                f"component_withstand['{param}'] must be positive, got {withstand}"
            )

        compliant = withstand >= required
        margin_ratio = withstand / required
        note = "pass" if compliant else "withstand below required level"
        findings.append(
            {
                "parameter": param,
                "required": required,
                "withstand": withstand,
                "compliant": compliant,
                "margin_ratio": margin_ratio,
                "note": note,
            }
        )
    return findings


def build_rdm_basis(env_spec, rdm_factor, component_withstand=None):
    """
    Full RDM basis derivation for a single component.

    Parameters
    ----------
    env_spec : dict
        Radiation environment specification (TID krad, fluences cm^-2).
    rdm_factor : float
        Design margin factor; must be >= 2.0.
    component_withstand : dict or None
        Component radiation tolerance per parameter.  When None, only the
        required levels are returned and no compliance assessment is made.

    Returns
    -------
    dict:
        required_levels   — derived withstand requirements per parameter
        findings          — list of compliance findings (empty when
                            component_withstand is None)
        overall_compliant — True if all findings pass; False if any fail;
                            None when component_withstand is None
    """
    required_levels = compute_required_levels(env_spec, rdm_factor)

    if component_withstand is None:
        return {
            "required_levels": required_levels,
            "findings": [],
            "overall_compliant": None,
        }

    findings = check_component_compliance(component_withstand, required_levels)
    overall_compliant = all(f["compliant"] for f in findings)
    return {
        "required_levels": required_levels,
        "findings": findings,
        "overall_compliant": overall_compliant,
    }
