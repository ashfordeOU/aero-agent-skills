"""
Design allowables selection and margin-of-safety computation for spacecraft structures.

ECSS-E-ST-32C clause 4.5.8 — Application of A-/B-basis design allowables.

A-basis: lower one-sided tolerance bound exceeded by 99 % of the material
         population at 95 % statistical confidence.
B-basis: lower one-sided tolerance bound exceeded by 90 % of the material
         population at 95 % statistical confidence.

Single load-path members require A-basis.
Redundant (multiple load-path) members may use B-basis.
"""

# Valid load-path types and their required basis
_LOAD_PATH_TO_BASIS = {
    "single": "A",
    "multiple": "B",
}

# Material classes and the reference source document for allowable values
_MATERIAL_SOURCE = {
    "metal": "MMPDS",
    "composite": "CMH-17",
    "non-metal": "supplier-data-sheet",
    "adhesive": "supplier-data-sheet",
}

VALID_LOAD_PATH_TYPES = tuple(_LOAD_PATH_TO_BASIS.keys())
VALID_MATERIAL_CLASSES = tuple(_MATERIAL_SOURCE.keys())
VALID_BASES = ("A", "B")


class AllowablesError(ValueError):
    """Raised when an allowables input is invalid or a finding is detected."""


def select_basis(load_path_type: str) -> str:
    """Return 'A' for single load path, 'B' for multiple (redundant) load path."""
    if load_path_type not in _LOAD_PATH_TO_BASIS:
        raise AllowablesError(
            f"Unknown load_path_type '{load_path_type}'; "
            f"expected one of {VALID_LOAD_PATH_TYPES}"
        )
    return _LOAD_PATH_TO_BASIS[load_path_type]


def source_for_material(material_class: str) -> str:
    """Return the reference document name for the given material class."""
    if material_class not in _MATERIAL_SOURCE:
        raise AllowablesError(
            f"Unknown material_class '{material_class}'; "
            f"expected one of {VALID_MATERIAL_CLASSES}"
        )
    return _MATERIAL_SOURCE[material_class]


def compute_margin_of_safety(allowable: float, applied_stress: float) -> float:
    """
    Compute margin of safety: MoS = (allowable / applied_stress) - 1.

    Both allowable and applied_stress must be positive (same sign convention;
    pass absolute magnitudes for compressive cases).
    """
    if applied_stress <= 0.0:
        raise AllowablesError(
            f"applied_stress must be > 0, got {applied_stress}"
        )
    if allowable <= 0.0:
        raise AllowablesError(
            f"allowable must be > 0, got {allowable}"
        )
    return (allowable / applied_stress) - 1.0


def is_margin_acceptable(margin_of_safety: float) -> bool:
    """Return True when MoS >= 0 (allowable not exceeded)."""
    return margin_of_safety >= 0.0


def check_basis_match(required_basis: str, retrieved_basis: str) -> bool:
    """
    Return True when the retrieved allowable basis matches the required basis.

    A B-basis value on a required-A member is a non-conformance; this function
    returns False in that case.
    """
    if required_basis not in VALID_BASES:
        raise AllowablesError(
            f"required_basis must be one of {VALID_BASES}, got '{required_basis}'"
        )
    if retrieved_basis not in VALID_BASES:
        raise AllowablesError(
            f"retrieved_basis must be one of {VALID_BASES}, got '{retrieved_basis}'"
        )
    return required_basis == retrieved_basis


def assess_member(
    load_path_type: str,
    material_class: str,
    allowable_value: float,
    applied_stress: float,
    retrieved_basis: str = None,
) -> dict:
    """
    Full allowables assessment for one structural member.

    Parameters
    ----------
    load_path_type  : "single" or "multiple"
    material_class  : "metal", "composite", "non-metal", or "adhesive"
    allowable_value : positive float (MPa or ksi, consistent units)
    applied_stress  : positive float (same units as allowable_value)
    retrieved_basis : "A" or "B" — the basis label on the retrieved value;
                      if omitted the basis-match check is skipped.

    Returns
    -------
    dict with keys:
        required_basis    : str  — basis required by load-path type
        source            : str  — reference document for material class
        margin_of_safety  : float
        acceptable        : bool — True only when MoS >= 0 and basis matches
        basis_match       : bool or None  — None when retrieved_basis not given
        findings          : list[str]  — empty when fully compliant
    """
    required_basis = select_basis(load_path_type)
    source = source_for_material(material_class)
    mos = compute_margin_of_safety(allowable_value, applied_stress)
    mos_ok = is_margin_acceptable(mos)

    if retrieved_basis is not None:
        basis_match = check_basis_match(required_basis, retrieved_basis)
    else:
        basis_match = None

    findings = []
    if not mos_ok:
        findings.append(
            f"MoS = {mos:.4f} < 0 (allowable {allowable_value}, "
            f"applied {applied_stress})"
        )
    if basis_match is False:
        findings.append(
            f"Basis mismatch: required {required_basis}, "
            f"retrieved {retrieved_basis}"
        )

    acceptable = mos_ok and (basis_match is not False)

    return {
        "required_basis": required_basis,
        "source": source,
        "margin_of_safety": mos,
        "acceptable": acceptable,
        "basis_match": basis_match,
        "findings": findings,
    }


def batch_assess(members: list) -> list:
    """
    Assess a list of structural members.

    Each entry is a dict with keys matching the assess_member signature:
        load_path_type, material_class, allowable_value, applied_stress,
        and optionally retrieved_basis.

    Returns a list of result dicts (same schema as assess_member) with an
    additional "error" key set to a string on failure or None on success.
    """
    results = []
    for m in members:
        try:
            result = assess_member(
                load_path_type=m["load_path_type"],
                material_class=m["material_class"],
                allowable_value=m["allowable_value"],
                applied_stress=m["applied_stress"],
                retrieved_basis=m.get("retrieved_basis"),
            )
            result["error"] = None
        except (AllowablesError, KeyError, TypeError) as exc:
            result = {
                "required_basis": None,
                "source": None,
                "margin_of_safety": None,
                "acceptable": False,
                "basis_match": None,
                "findings": [str(exc)],
                "error": str(exc),
            }
        results.append(result)
    return results
