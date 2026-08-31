#!/usr/bin/env python3
"""XFOIL airfoil polar analysis logic (paraphrase, common knowledge).

Common-knowledge summary (standards-map.yaml, naca-tr-824: public
domain): NACA Report 824 (Abbott, von Doenhoff, Stivers) is the classic
airfoil section data reference and the validation anchor for airfoil
analysis tools such as XFOIL. Its wind-tunnel polars, e.g. NACA 0012 at
Reynolds number 6 million (lift coefficient about 0.82 at 10 degrees
angle of attack, zero-lift drag coefficient about 0.0079), are used here
as the sanity band for XFOIL-style polar runs. XFOIL inviscid mode
produces no meaningful drag; viscous analysis with transition is
required for drag results.
"""

ALPHA_MIN = -25.0
ALPHA_MAX = 30.0
CL_MIN = -2.5
CL_MAX = 2.5
CD_MIN = 0.0
CD_MAX = 0.2

# NACA 0012 at Re = 6e6 anchor bands (NACA TR-824, brief 05 item 7).
NACA0012_CL_10DEG_MIN = 0.77
NACA0012_CL_10DEG_MAX = 0.87
NACA0012_CD0_MIN = 0.0069
NACA0012_CD0_MAX = 0.0089


def plausible_alpha(alpha_deg):
    """True if the angle of attack (deg) is within the polar band."""
    return ALPHA_MIN <= alpha_deg <= ALPHA_MAX


def validate_polar_point(alpha_deg, cl, cd, re):
    """Structurally validate one polar point; True when plausible.

    Raises ValueError for nonsense inputs: angle of attack outside the
    polar band, lift coefficient outside [-2.5, 2.5], drag coefficient
    outside [0, 0.2], or Reynolds number <= 0.
    """
    if not plausible_alpha(alpha_deg):
        raise ValueError(
            "alpha %r deg outside polar band [%g, %g]" % (alpha_deg, ALPHA_MIN, ALPHA_MAX)
        )
    if not (CL_MIN <= cl <= CL_MAX):
        raise ValueError("cl %r outside plausible band [%g, %g]" % (cl, CL_MIN, CL_MAX))
    if not (CD_MIN <= cd <= CD_MAX):
        raise ValueError("cd %r outside plausible band [%g, %g]" % (cd, CD_MIN, CD_MAX))
    if re <= 0:
        raise ValueError("Reynolds number must be > 0, got %r" % (re,))
    return True


def naca0012_sanity(cl_at_10deg, cd0):
    """Check a polar against the NACA 0012 (Re = 6e6) anchor.

    Returns a dict with cl_ok (0.77 <= cl <= 0.87), cd0_ok
    (0.0069 <= cd0 <= 0.0089), is_sane (both ok), and a note string.
    """
    cl_ok = NACA0012_CL_10DEG_MIN <= cl_at_10deg <= NACA0012_CL_10DEG_MAX
    cd0_ok = NACA0012_CD0_MIN <= cd0 <= NACA0012_CD0_MAX
    if cl_ok and cd0_ok:
        note = "polar inside the NACA 0012 Re = 6e6 anchor band"
    elif cl_ok:
        note = "cl ok, but cd0 outside the NACA 0012 Re = 6e6 anchor band"
    elif cd0_ok:
        note = "cd0 ok, but cl at 10 deg outside the NACA 0012 Re = 6e6 anchor band"
    else:
        note = "cl at 10 deg and cd0 both outside the NACA 0012 Re = 6e6 anchor band"
    return {"cl_ok": cl_ok, "cd0_ok": cd0_ok, "is_sane": cl_ok and cd0_ok, "note": note}


def cd0_hint(cd0):
    """Diagnostic hint for a zero-lift drag coefficient.

    Near-zero cd0 suggests an inviscid run (XFOIL inviscid drag is
    meaningless); high cd0 suggests transition or mesh-density problems.
    Returns None when the value is unremarkable.
    """
    if 0 < cd0 < 0.005:
        return "likely inviscid run: XFOIL inviscid drag is meaningless; rerun viscous"
    if cd0 > 0.02:
        return "high drag: check transition and mesh density"
    return None
