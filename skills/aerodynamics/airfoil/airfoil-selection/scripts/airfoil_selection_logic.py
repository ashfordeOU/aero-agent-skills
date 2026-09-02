#!/usr/bin/env python3
"""Airfoil section selection logic (paraphrase, common knowledge).

Common-knowledge summary (standards-map.yaml, naca-tr-824: public
domain): classic airfoil section data (NACA 4/5-digit and 6-series)
supplies lift and drag coefficients used for section selection. A
wing design picks a section that meets a minimum thickness while
maximizing the lift-to-drag ratio at the design condition. Scoring
and thresholds here are project-defined sanity bands.
"""


def ld_ratio(cl, cd):
    """Lift-to-drag ratio at a section condition."""
    if cl < 0:
        raise ValueError("cl must be >= 0, got %r" % (cl,))
    if cd <= 0:
        raise ValueError("cd must be > 0, got %r" % (cd,))
    return cl / cd


def thickness_ok(thickness, min_thickness):
    """True when the section thickness ratio meets the requirement."""
    if thickness <= 0:
        raise ValueError("thickness must be > 0, got %r" % (thickness,))
    return thickness >= min_thickness


def select_airfoil(candidates, min_thickness):
    """Best candidate id by lift-to-drag ratio among those meeting the
    minimum thickness; raises when no candidate qualifies."""
    if not candidates:
        raise ValueError("candidates must not be empty")
    qualified = [c for c in candidates if thickness_ok(c["thickness"], min_thickness)]
    if not qualified:
        raise ValueError("no candidate meets min_thickness %r" % (min_thickness,))
    best = max(qualified, key=lambda c: ld_ratio(c["cl"], c["cd"]))
    return best["id"]
