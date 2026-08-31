#!/usr/bin/env python3
"""ECSS-E-ST-40C software verification planning logic (paraphrase).

Pure stdlib, no network. Unit conventions: this module carries no
physical units; its inputs are string enums. Requirement categories are
one of functional, performance, interface, resource, safety, data.
Criticality levels are one of catastrophic, critical, major, minor,
no-effect. Unknown categories or criticality levels raise ValueError.

This module is a deterministic paraphrase of ECSS-E-ST-40C verification
practice: each requirement category maps to a primary verification
method set (test, analysis, inspection, review), each criticality maps
to a verification depth, an independence flag, and the records the
depth demands, and the plan verdict confirms that every requirement in
a set received a method.
"""

VERIFICATION_METHODS = {
    "functional": ["test", "review"],
    "performance": ["test", "analysis"],
    "interface": ["test", "inspection"],
    "resource": ["analysis", "test"],
    "safety": ["test", "analysis", "review"],
    "data": ["inspection", "review"],
}

CRITICALITY_DEPTH = {
    "catastrophic": {
        "depth": "full independent verification, all methods, formal records",
        "independent": True,
        "records": "formal verification records for every requirement",
    },
    "critical": {
        "depth": "independent review plus analysis and test records",
        "independent": True,
        "records": "analysis and test records with independent review",
    },
    "major": {
        "depth": "analysis and test records",
        "independent": False,
        "records": "analysis and test records",
    },
    "minor": {
        "depth": "review records",
        "independent": False,
        "records": "review records",
    },
    "no-effect": {
        "depth": "inspection",
        "independent": False,
        "records": "inspection records",
    },
}


def verify_method(requirement_category):
    """Return the verification method list for a requirement category.

    Accepts the ECSS-E-ST-40C requirement categories (functional,
    performance, interface, resource, safety, data), case-insensitive.
    Unknown categories raise ValueError. Returns a fresh list of method
    names in the standard order.
    """
    if not isinstance(requirement_category, str):
        raise ValueError(
            "requirement_category must be a string, got %r" % (requirement_category,)
        )
    key = requirement_category.strip().lower()
    if key not in VERIFICATION_METHODS:
        raise ValueError(
            "unknown requirement category %r; expected one of %s"
            % (requirement_category, ", ".join(sorted(VERIFICATION_METHODS)))
        )
    return list(VERIFICATION_METHODS[key])


def verification_depth(criticality):
    """Return the verification depth verdict for a criticality level.

    Accepts catastrophic, critical, major, minor, no-effect
    (case-insensitive). Unknown levels raise ValueError. Returns a dict
    with 'depth' (str), 'independent' (bool), and 'records' (str).
    """
    if not isinstance(criticality, str):
        raise ValueError("criticality must be a string, got %r" % (criticality,))
    key = criticality.strip().lower()
    if key not in CRITICALITY_DEPTH:
        raise ValueError(
            "unknown criticality %r; expected one of %s"
            % (criticality, ", ".join(sorted(CRITICALITY_DEPTH)))
        )
    return dict(CRITICALITY_DEPTH[key])


def plan_verdict(requirements):
    """Build the verification plan verdict for a list of requirements.

    Each entry is a (requirement_category, criticality) pair. Returns a
    dict with 'requirements', a list of per-requirement verdicts holding
    the category, criticality, methods, independence flag, depth, and
    records, and 'status', which is 'verification-plan-complete' when
    every requirement received at least one method. Empty or malformed
    input raises ValueError.
    """
    if not isinstance(requirements, list) or not requirements:
        raise ValueError(
            "requirements must be a non-empty list of (category, criticality) pairs"
        )
    verdicts = []
    for req in requirements:
        if not isinstance(req, (tuple, list)) or len(req) != 2:
            raise ValueError(
                "each requirement must be a (category, criticality) pair, got %r"
                % (req,)
            )
        category, criticality = req
        methods = verify_method(category)
        depth = verification_depth(criticality)
        verdicts.append(
            {
                "category": category,
                "criticality": criticality,
                "methods": methods,
                "independent": depth["independent"],
                "depth": depth["depth"],
                "records": depth["records"],
            }
        )
    complete = all(v["methods"] for v in verdicts)
    return {
        "requirements": verdicts,
        "status": (
            "verification-plan-complete" if complete else "verification-plan-incomplete"
        ),
    }


if __name__ == "__main__":
    import doctest

    doctest.testmod()
