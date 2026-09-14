#!/usr/bin/env python3
"""Identifying which face of a coverglass carries the coating.

Anchor: ECSS-E-ST-20-08C clause 8.3.3. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A coverglass is a thin, near-symmetric plate whose two faces do
completely different jobs. One face goes outboard and carries the
optical coating; the other goes inboard and is bonded to the cell. The
piece looks the same either way up, so the delivery has to say which
face is which in a way that still works at the moment somebody picks the
piece out of a tray with tweezers.

Indicator means
    edge-bevel-notch        a bevel ground into one face at the edge
    corner-cut              a cut corner in the outline
    engraved-edge-arrow     an arrow cut into the edge, pointing at a face
    printed-face-arrow      ink printed on a face
    adhesive-face-label     a label stuck to a face
    packaging-orientation-only  the tray is the only thing that knows
    none                    nothing identifies either face

Where the indicator sits
    coated-face     inside the clear aperture, so it costs transmission
    uncoated-face   inside the adhesive bond line
    coverglass-edge on the rim, outside the aperture and outside the bond
    packaging-carrier not on the glass at all

Cleaning before bonding
    none, solvent-wipe, ultrasonic-bath, plasma-clean

Three properties are graded separately because they fail separately.
Admissibility asks whether the means may sit where it is declared at
all. Face resolution asks whether the indicator still says which face is
which after the piece has been turned over -- a single cut corner
mirrors under a flip and fixes only the rotation. Survival asks whether
the indicator is still there after the clean the glass sees before
bonding.

A cue counts toward orientation only when it is admissible, resolves the
faces and survives preparation. The lot is then checked for one further
thing no single piece can show: whether one convention holds across the
whole lot, because half a lot marking the coated face and half marking
the uncoated face is ambiguous even though every piece is marked.

The aperture cap, the cue count and the tables below are declared
project policy, not physical constants; a project may substitute its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

INDICATOR_MEANS = (
    "edge-bevel-notch",
    "corner-cut",
    "engraved-edge-arrow",
    "printed-face-arrow",
    "adhesive-face-label",
    "packaging-orientation-only",
    "none",
)

INDICATOR_LOCATIONS = (
    "coated-face",
    "uncoated-face",
    "coverglass-edge",
    "packaging-carrier",
)

CLEANING_PROCESSES = ("none", "solvent-wipe", "ultrasonic-bath", "plasma-clean")

MARKED_FACES = ("coated-face", "uncoated-face")

ORIENTATION_UNAMBIGUOUS = "coated-face-unambiguous"
ORIENTATION_AMBIGUOUS = "coated-face-ambiguous"
ORIENTATION_NOT_ESTABLISHED = "coated-face-not-established"

ORIENTATION_RANK = {
    ORIENTATION_NOT_ESTABLISHED: 0,
    ORIENTATION_AMBIGUOUS: 1,
    ORIENTATION_UNAMBIGUOUS: 2,
}

DEFAULT_ORIENTATION_POLICY = {
    "max_aperture_loss_fraction": 0.0015,
    "min_usable_cues": 1,
}

_GEOMETRIC_MEANS = ("edge-bevel-notch", "corner-cut", "engraved-edge-arrow")

_RESOLVES_FACES = {
    "edge-bevel-notch": True,
    "corner-cut": False,
    "engraved-edge-arrow": True,
    "printed-face-arrow": True,
    "adhesive-face-label": True,
    "packaging-orientation-only": False,
    "none": False,
}

_SURVIVES = {
    "edge-bevel-notch": {
        "none": True,
        "solvent-wipe": True,
        "ultrasonic-bath": True,
        "plasma-clean": True,
    },
    "corner-cut": {
        "none": True,
        "solvent-wipe": True,
        "ultrasonic-bath": True,
        "plasma-clean": True,
    },
    "engraved-edge-arrow": {
        "none": True,
        "solvent-wipe": True,
        "ultrasonic-bath": True,
        "plasma-clean": True,
    },
    "printed-face-arrow": {
        "none": True,
        "solvent-wipe": False,
        "ultrasonic-bath": False,
        "plasma-clean": False,
    },
    "adhesive-face-label": {
        "none": True,
        "solvent-wipe": True,
        "ultrasonic-bath": False,
        "plasma-clean": False,
    },
    "packaging-orientation-only": {
        "none": False,
        "solvent-wipe": False,
        "ultrasonic-bath": False,
        "plasma-clean": False,
    },
    "none": {
        "none": False,
        "solvent-wipe": False,
        "ultrasonic-bath": False,
        "plasma-clean": False,
    },
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _require_label(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _require_positive(name, value):
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not math.isfinite(value)
    ):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return float(value)


def _require_non_negative(name, value):
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not math.isfinite(value)
    ):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return float(value)


def _require_mapping(name, value):
    if not isinstance(value, dict):
        raise ValueError("%s must be a mapping, got %r" % (name, value))
    return value


def _require_count(name, value, minimum=0):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be a whole number, got %r" % (name, value))
    if value < minimum:
        raise ValueError("%s must be at least %d, got %r" % (name, minimum, value))
    return value


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error.

    The aperture loss is a quotient of two measured areas and the cap is
    a round fraction, so an indicator cut exactly to the cap can evaluate
    a unit in the last place above it. The comparison absorbs that; the
    cap itself stays as declared.
    """
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _policy(policy):
    settings = dict(DEFAULT_ORIENTATION_POLICY)
    if policy is not None:
        settings.update(_require_mapping("policy", policy))
    return settings


def indicator_admissibility(indicator_means, indicator_location):
    """Decide whether this indicator may sit where it is declared.

    The pairing is what matters, never the means alone. Ink inside the
    clear aperture is an optical defect for the life of the mission, a
    label on the cell-facing face sits inside the adhesive bond line,
    and a feature of the outline declared on a face is a record that
    does not say where the feature is.
    """
    means = _require_choice("indicator_means", indicator_means, INDICATOR_MEANS)
    location = _require_choice(
        "indicator_location", indicator_location, INDICATOR_LOCATIONS
    )
    findings = []
    admissible = True

    if means == "none":
        admissible = False
        findings.append(
            "nothing on the piece says which face carries the coating; "
            "orientation rests on whoever unpacked the tray"
        )
    elif means == "packaging-orientation-only" and location != "packaging-carrier":
        admissible = False
        findings.append(
            "a packaging-only scheme is declared on the glass itself; the "
            "record does not describe the article it is about"
        )
    elif means in _GEOMETRIC_MEANS and location != "coverglass-edge":
        admissible = False
        findings.append(
            "%s is a feature of the outline or the rim and is declared on %s, "
            "so the record does not say where the feature is" % (means, location)
        )
    elif means == "adhesive-face-label" and location == "uncoated-face":
        admissible = False
        findings.append(
            "an adhesive label on the cell-facing face sits inside the bond "
            "line the coverglass is later attached through"
        )
    elif means == "printed-face-arrow" and location == "coated-face":
        admissible = False
        findings.append(
            "ink printed inside the clear aperture is an optical defect over "
            "the cell for the life of the mission"
        )
    elif location == "coated-face":
        findings.append(
            "the indicator sits inside the clear aperture, so its footprint is "
            "transmission the assembly will never get back"
        )
    elif location == "packaging-carrier":
        findings.append(
            "the indicator is on the carrier and not on the glass, so it stops "
            "working the moment the piece is picked out of the tray"
        )
    return {
        "indicator_means": means,
        "indicator_location": location,
        "admissible": admissible,
        "findings": findings,
    }


def indicator_resolves_faces(indicator_means):
    """Decide whether the indicator still names a face after a flip.

    This is the property a reviewer skips. A cut corner is cut through
    the full thickness, so turning the piece over mirrors it: it fixes
    the rotation of the piece in its tray and says nothing at all about
    which way up it is.
    """
    means = _require_choice("indicator_means", indicator_means, INDICATOR_MEANS)
    resolves = _RESOLVES_FACES[means]
    findings = []
    if means == "corner-cut":
        findings.append(
            "a cut corner mirrors when the piece is turned over; it fixes the "
            "rotation and never says which face is up"
        )
    elif means == "packaging-orientation-only":
        findings.append(
            "the tray knows which way up the piece was packed and the piece "
            "does not; the knowledge is lost at the first handling step"
        )
    return {
        "indicator_means": means,
        "resolves_faces": resolves,
        "findings": findings,
    }


def indicator_survives_preparation(indicator_means, cleaning_process):
    """Decide whether the indicator is still there after the pre-bond clean."""
    means = _require_choice("indicator_means", indicator_means, INDICATOR_MEANS)
    cleaning = _require_choice(
        "cleaning_process", cleaning_process, CLEANING_PROCESSES
    )
    survives = _SURVIVES[means][cleaning]
    findings = []
    if means not in ("none", "packaging-orientation-only") and not survives:
        findings.append(
            "a %s indicator does not survive %s, so the piece arrives at the "
            "bond station with nothing on it" % (means, cleaning)
        )
    return {
        "indicator_means": means,
        "cleaning_process": cleaning,
        "survives_preparation": survives,
        "findings": findings,
    }


def aperture_loss_fraction(
    indicator_area_mm2, clear_aperture_mm2, indicator_location
):
    """Share of the clear aperture the indicator takes away.

    An indicator outside the aperture costs nothing, however large it
    is; one inside it costs its own footprint.
    """
    footprint = _require_non_negative("indicator_area_mm2", indicator_area_mm2)
    aperture = _require_positive("clear_aperture_mm2", clear_aperture_mm2)
    location = _require_choice(
        "indicator_location", indicator_location, INDICATOR_LOCATIONS
    )
    if location != "coated-face":
        return 0.0
    if footprint >= aperture:
        raise ValueError(
            "an indicator footprint of %r mm2 is not smaller than the %r mm2 "
            "clear aperture it is placed in" % (footprint, aperture)
        )
    return footprint / aperture


def usable_orientation_cues(cues, cleaning_process):
    """Count the cues that still name the coated face at the point of use.

    A cue counts only when all three hold at once: it may sit where it
    is declared, it survives the pre-bond clean, and it still resolves
    the two faces once the piece has been turned over.
    """
    if not isinstance(cues, (list, tuple)):
        raise ValueError("cues must be a sequence of indicator records")
    cleaning = _require_choice(
        "cleaning_process", cleaning_process, CLEANING_PROCESSES
    )

    graded = []
    findings = []
    seen = []
    for cue in cues:
        _require_mapping("cue", cue)
        placement = indicator_admissibility(
            cue.get("indicator_means"), cue.get("indicator_location")
        )
        key = (placement["indicator_means"], placement["indicator_location"])
        if key in seen:
            raise ValueError(
                "cue %s on %s is declared twice; a repeated cue is not a "
                "second independent one" % key
            )
        seen.append(key)
        resolution = indicator_resolves_faces(cue.get("indicator_means"))
        permanence = indicator_survives_preparation(
            cue.get("indicator_means"), cleaning
        )
        usable = (
            placement["admissible"]
            and resolution["resolves_faces"]
            and permanence["survives_preparation"]
        )
        findings.extend(placement["findings"])
        findings.extend(resolution["findings"])
        findings.extend(permanence["findings"])
        graded.append(
            {
                "indicator_means": placement["indicator_means"],
                "indicator_location": placement["indicator_location"],
                "admissible": placement["admissible"],
                "resolves_faces": resolution["resolves_faces"],
                "survives_preparation": permanence["survives_preparation"],
                "usable": usable,
            }
        )
    return {
        "cues": graded,
        "usable_cues": sum(1 for g in graded if g["usable"]),
        "declared_cues": len(graded),
        "findings": findings,
    }


def assess_coverglass_orientation(piece, policy=None):
    """Grade the coating-face identification of one delivered coverglass."""
    _require_mapping("piece", piece)
    settings = _policy(policy)
    cap = _require_non_negative(
        "max_aperture_loss_fraction", settings.get("max_aperture_loss_fraction")
    )
    needed = _require_count(
        "min_usable_cues", settings.get("min_usable_cues"), minimum=1
    )

    piece_id = _require_label("piece_id", piece.get("piece_id"))
    marked_face = _require_choice(
        "marked_face", piece.get("marked_face"), MARKED_FACES
    )
    aperture = _require_positive(
        "clear_aperture_mm2", piece.get("clear_aperture_mm2")
    )
    cleaning = _require_choice(
        "cleaning_process", piece.get("cleaning_process"), CLEANING_PROCESSES
    )
    cues = piece.get("cues")
    if not isinstance(cues, (list, tuple)) or not cues:
        raise ValueError("piece must carry a non-empty cues sequence")

    graded = usable_orientation_cues(cues, cleaning)

    loss = 0.0
    for cue in cues:
        loss += aperture_loss_fraction(
            cue.get("indicator_area_mm2", 0.0),
            aperture,
            cue.get("indicator_location"),
        )

    findings = ["%s: %s" % (piece_id, f) for f in graded["findings"]]
    within_cap = _at_most(loss, cap)
    if not within_cap:
        findings.append(
            "%s: the indicators take %.4g of the clear aperture against a %.4g "
            "cap" % (piece_id, loss, cap)
        )

    usable = graded["usable_cues"]
    if usable == 0:
        verdict = ORIENTATION_NOT_ESTABLISHED
        findings.append(
            "%s: no cue on the piece names the coated face at the point of "
            "use, so the coverglass can be bonded either way up" % piece_id
        )
    elif usable < needed or not within_cap:
        verdict = ORIENTATION_AMBIGUOUS
        if usable < needed:
            findings.append(
                "%s: %d usable cue(s) against the %d the policy asks for"
                % (piece_id, usable, needed)
            )
    else:
        verdict = ORIENTATION_UNAMBIGUOUS

    return {
        "piece_id": piece_id,
        "marked_face": marked_face,
        "cleaning_process": cleaning,
        "cues": graded["cues"],
        "usable_cues": usable,
        "declared_cues": graded["declared_cues"],
        "aperture_loss_fraction": loss,
        "within_aperture_cap": within_cap,
        "verdict": verdict,
        "findings": findings,
    }


def convention_consistency(assessments):
    """Check one marking convention holds across the whole lot.

    No single piece can show this. A lot in which half the pieces mark
    the coated face and half mark the uncoated face is ambiguous even
    though every piece is individually marked, because the operator has
    to know which piece follows which rule before reading either.
    """
    if not isinstance(assessments, (list, tuple)) or not assessments:
        raise ValueError("assessments must be a non-empty sequence")

    faces = []
    means = []
    for assessment in assessments:
        _require_mapping("assessment", assessment)
        face = _require_choice(
            "marked_face", assessment.get("marked_face"), MARKED_FACES
        )
        if face not in faces:
            faces.append(face)
        usable = [c for c in assessment.get("cues", []) if c.get("usable")]
        for cue in usable:
            name = _require_choice(
                "indicator_means", cue.get("indicator_means"), INDICATOR_MEANS
            )
            if name not in means:
                means.append(name)

    findings = []
    if len(faces) > 1:
        findings.append(
            "the lot marks %s on some pieces and %s on others; the convention "
            "has to be read before the indicator can be"
            % (faces[0], faces[1])
        )
    if len(means) > 1:
        findings.append(
            "the lot carries %d different usable indicator means (%s); an "
            "operator has to recognise all of them to orient any piece"
            % (len(means), ", ".join(sorted(means)))
        )
    return {
        "marked_faces": sorted(faces),
        "indicator_means": sorted(means),
        "consistent": len(faces) <= 1 and len(means) <= 1,
        "findings": findings,
    }


def assess_coverglass_lot_orientation(case):
    """Full clause 8.3.3 roll-up over a delivered lot of coverglasses."""
    _require_mapping("case", case)
    lot_id = _require_label("lot_id", case.get("lot_id"))
    pieces = case.get("pieces")
    if not isinstance(pieces, (list, tuple)) or not pieces:
        raise ValueError("case must carry a non-empty pieces sequence")
    policy = case.get("policy")

    assessments = [assess_coverglass_orientation(p, policy) for p in pieces]
    seen = set()
    for assessment in assessments:
        if assessment["piece_id"] in seen:
            raise ValueError(
                "piece %r appears twice in the lot" % assessment["piece_id"]
            )
        seen.add(assessment["piece_id"])

    findings = []
    for assessment in assessments:
        findings.extend(assessment["findings"])

    convention = convention_consistency(assessments)
    findings.extend("%s: %s" % (lot_id, f) for f in convention["findings"])

    unambiguous = [
        a for a in assessments if a["verdict"] == ORIENTATION_UNAMBIGUOUS
    ]
    not_established = sorted(
        a["piece_id"]
        for a in assessments
        if a["verdict"] == ORIENTATION_NOT_ESTABLISHED
    )
    share = len(unambiguous) / len(assessments)

    worst = min(ORIENTATION_RANK[a["verdict"]] for a in assessments)
    verdict = next(k for k, v in ORIENTATION_RANK.items() if v == worst)
    if not convention["consistent"] and verdict == ORIENTATION_UNAMBIGUOUS:
        verdict = ORIENTATION_AMBIGUOUS

    weakest = min(
        assessments,
        key=lambda a: (
            ORIENTATION_RANK[a["verdict"]],
            a["usable_cues"],
            a["piece_id"],
        ),
    )
    return {
        "lot_id": lot_id,
        "assessments": assessments,
        "convention": convention,
        "verdict": verdict,
        "weakest_piece": weakest["piece_id"],
        "not_established": not_established,
        "unambiguous_share": share,
        "lot_orientation_secure": _at_least(share, 1.0)
        and convention["consistent"],
        "findings": findings,
    }
