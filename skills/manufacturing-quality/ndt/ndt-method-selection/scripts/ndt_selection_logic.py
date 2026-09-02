"""NDT method selection for aerospace parts.

Select a non-destructive testing (NDT) method from the defect class
(surface, near-surface, internal) and the material class
(ferromagnetic, non-ferromagnetic, non-conductive). The decision
table, sensitivity ranking, and cost ranking below are the module
contract exercised by scripts/test_ndt_selection.py.

Methods: RT radiography, UT ultrasonic, ET eddy current, PT liquid
penetrant, MT magnetic particle.
"""

DEFECT_CLASSES = ("surface", "near-surface", "internal")
MATERIAL_CLASSES = ("ferromagnetic", "non-ferromagnetic", "non-conductive")

# Decision table: defect class -> applicable methods. Surface defects
# also depend on the material class. Internal and near-surface
# defects do not depend on the material class.
DECISION_TABLE = {
    "internal": ("RT", "UT"),
    "near-surface": ("ET", "UT"),
    "surface": {
        "ferromagnetic": ("MT", "PT"),
        "non-ferromagnetic": ("ET", "PT"),
        "non-conductive": ("PT",),
    },
}

# Sensitivity rank per method, 5 highest. UT 5, RT 4, ET 4, MT 3, PT 3.
SENSITIVITY_RANK = {"UT": 5, "RT": 4, "ET": 4, "MT": 3, "PT": 3}

# Cost rank per method, 1 cheapest. Reporting only, never overrides
# sensitivity: RT 4, UT 3, ET 2, MT 2, PT 1.
COST_RANK = {"RT": 4, "UT": 3, "ET": 2, "MT": 2, "PT": 1}

# Tie-break order for equal sensitivity: the later method in this
# order wins. The only reachable tie is MT vs PT, where the later
# method (PT) is also the alphabetically-later method, per the skill
# spec.
TIE_ORDER = ("RT", "UT", "ET", "MT", "PT")


def applicable_methods(defect_class, material):
    """Return the sorted list of NDT methods valid for the combination.

    Raises ValueError for an unknown defect class or material class.
    """
    if defect_class not in DEFECT_CLASSES:
        raise ValueError("unknown defect class: %r" % (defect_class,))
    if material not in MATERIAL_CLASSES:
        raise ValueError("unknown material class: %r" % (material,))
    if defect_class == "surface":
        return sorted(DECISION_TABLE["surface"][material])
    return sorted(DECISION_TABLE[defect_class])


def sensitivity_rank(method):
    """Return the sensitivity rank of a method, 5 highest."""
    if method not in SENSITIVITY_RANK:
        raise ValueError("unknown method: %r" % (method,))
    return SENSITIVITY_RANK[method]


def cost_rank(method):
    """Return the cost rank of a method, 1 cheapest. Reporting only."""
    if method not in COST_RANK:
        raise ValueError("unknown method: %r" % (method,))
    return COST_RANK[method]


def select_method(defect_class, material):
    """Pick the highest-sensitivity applicable method.

    Returns {'method': top, 'alternates': [...], 'rationale': '...'}.
    Ties are broken by TIE_ORDER (later wins). The rationale names the
    defect class, the material class, and the selected method.
    """
    applicable = applicable_methods(defect_class, material)
    top = max(
        applicable,
        key=lambda m: (SENSITIVITY_RANK[m], TIE_ORDER.index(m)),
    )
    alternates = [m for m in applicable if m != top]
    rationale = (
        "%s defect in %s material: %s is the highest-sensitivity "
        "applicable method" % (defect_class, material, top)
    )
    return {
        "method": top,
        "alternates": alternates,
        "rationale": rationale,
    }
