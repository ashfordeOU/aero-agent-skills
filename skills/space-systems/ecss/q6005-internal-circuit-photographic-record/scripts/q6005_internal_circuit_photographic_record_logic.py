"""The photographic record of a hybrid interior, taken before the package closes.

Anchor: ECSS-Q-ST-60-05 clause 10.3.4 (the images of the assembled internal
circuit, captured while the package is still open and kept as permanent
evidence of the configuration that was actually built).

Offline, deterministic, python3 standard library only.

Procedure implemented here (paraphrased, no standard text reproduced):

* The record exists to be read years later by somebody who cannot open the
  package. Its value is entirely in what a future reader can resolve, not in
  how many frames were taken.
* Resolution is the first question. If the smallest feature that matters
  does not span enough pixels, the frame shows that the feature is there and
  nothing about its condition, which is the question that will be asked.
* Coverage is by subject, not by frame count. Every die, every interconnect
  region and every attach area declared for the assembly has to appear in
  some frame, and forty frames of the same corner cover one subject.
* A frame nobody can read covers nothing. An unreadable frame is excluded
  from coverage before the coverage is counted, or the record claims
  evidence it does not hold.
* The frames have to say which unit they belong to. A perfect image of an
  unidentified interior is evidence about some hybrid, which is no evidence
  at all.
* The images are taken before the package is sealed, because afterwards the
  interior cannot be photographed without destroying the unit whose record
  it would be.
* Storage is part of the record. A format nobody will be able to open, a
  retention shorter than the hardware's life, or an archive that can be
  quietly edited all turn permanent evidence back into a photograph.
* The adequacy index is weighted credit over total weight. It ranks what is
  outstanding; an uncovered subject, a missing required view, inadequate
  resolution or a record made after the seal decides the outcome on its own,
  at any index.
"""

from __future__ import annotations

import math

# Pixels the smallest feature of interest has to span before a frame says
# anything about that feature's condition.
MINIMUM_PIXELS_ACROSS_FEATURE = 5.0

# Views the record has to contain, and the share of it each supplies.
REQUIRED_VIEWS = {
    "overall-interior-view": 1.0,
    "die-detail-view": 1.0,
    "interconnect-detail-view": 1.0,
    "substrate-attach-detail-view": 0.8,
    "identification-marking-view": 0.7,
}

# Views without which there is no record of the as-built interior.
MANDATORY_VIEWS = (
    "overall-interior-view",
    "die-detail-view",
    "interconnect-detail-view",
)

# What a frame is worth once a future reader tries to use it.
FRAME_QUALITY_CREDIT = {
    "sharp-and-evenly-lit": 1.0,
    "readable-with-local-glare": 0.7,
    "soft-focus": 0.3,
    "unreadable": 0.0,
}

# A frame at or below this credit carries no subject and no view.
UNUSABLE_QUALITY_CREDIT = 0.0

# Archive provisions and the share of the record argument each supplies.
ARCHIVE_PROVISIONS = {
    "images-carry-the-unit-identification": 1.0,
    "record-captured-before-the-package-was-sealed": 1.0,
    "archive-format-openly-readable": 0.7,
    "archive-retention-covers-the-hardware-life": 0.9,
    "archive-entries-cannot-be-silently-replaced": 0.8,
}

MANDATORY_ARCHIVE_PROVISIONS = (
    "images-carry-the-unit-identification",
    "record-captured-before-the-package-was-sealed",
    "archive-retention-covers-the-hardware-life",
)

PROVISION_STATE_CREDIT = {
    "met-and-evidenced": 1.0,
    "met-not-evidenced": 0.6,
    "not-met": 0.0,
}

# Years an archive has to hold the record for.
MINIMUM_RETENTION_YEARS = 10

# Adequacy index an acceptable photographic record has to reach.
ACCEPTANCE_INDEX = 0.85

# Indices are ratios of sums of weights; a case meant to sit on a bound can
# land a few units in the last place away from it.
RECORD_TOLERANCE = 1e-9

VERDICTS = (
    "photographic-record-accepted",
    "photographic-record-accepted-with-open-actions",
    "photographic-record-not-accepted",
    "photographic-record-incomplete",
)


def _real(value, label):
    """Return ``value`` as a finite float or raise for anything else."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return number


def _positive(value, label):
    """Return ``value`` as a strictly positive finite float or raise."""
    number = _real(value, label)
    if number <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return number


def _count(value, label, minimum=1):
    """Return ``value`` as a whole count at or above ``minimum`` or raise."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be a whole number, got %r" % (label, value))
    if value < minimum:
        raise ValueError("%s must be at least %d, got %r" % (label, minimum, value))
    return value


def pixels_across_feature(feature_size_um, pixels_per_um):
    """How many pixels the smallest feature of interest spans in a frame."""
    feature = _positive(feature_size_um, "feature_size_um")
    density = _positive(pixels_per_um, "pixels_per_um")
    return feature * density


def resolution_is_adequate(feature_size_um, pixels_per_um):
    """True when a frame can show the condition of the smallest feature."""
    spanned = pixels_across_feature(feature_size_um, pixels_per_um)
    return spanned >= MINIMUM_PIXELS_ACROSS_FEATURE - RECORD_TOLERANCE


def frame_quality_credit(grade):
    """What one frame is worth to a future reader."""
    if grade not in FRAME_QUALITY_CREDIT:
        raise ValueError(
            "unknown frame quality %r (known: %s)"
            % (grade, ", ".join(sorted(FRAME_QUALITY_CREDIT)))
        )
    return FRAME_QUALITY_CREDIT[grade]


def frame_is_usable(grade):
    """True when a frame carries evidence rather than merely existing."""
    return frame_quality_credit(grade) > UNUSABLE_QUALITY_CREDIT + RECORD_TOLERANCE


def view_weight(view):
    """Share of the record one required view supplies."""
    if view not in REQUIRED_VIEWS:
        raise ValueError(
            "unknown view %r (known: %s)" % (view, ", ".join(sorted(REQUIRED_VIEWS)))
        )
    return REQUIRED_VIEWS[view]


def normalize_frames(frames):
    """Validate the frame set and reject a repeated frame identifier."""
    if not isinstance(frames, (list, tuple)) or len(frames) == 0:
        raise ValueError("a photographic record must carry at least one frame")
    seen = set()
    normalized = []
    for raw in frames:
        if not isinstance(raw, dict):
            raise ValueError("frame must be a mapping, got %r" % (type(raw).__name__,))
        frame_id = raw.get("frame_id")
        if not isinstance(frame_id, str) or not frame_id.strip():
            raise ValueError("frame_id must be a non-empty string, got %r" % (frame_id,))
        if frame_id in seen:
            raise ValueError("duplicate frame identifier %r" % (frame_id,))
        seen.add(frame_id)
        view = raw.get("view")
        view_weight(view)  # validation only
        grade = raw.get("quality")
        frame_quality_credit(grade)  # validation only
        subjects = raw.get("subjects", ())
        if not isinstance(subjects, (list, tuple)):
            raise ValueError(
                "frame %r subjects must be a list or tuple" % (frame_id,)
            )
        for subject in subjects:
            if not isinstance(subject, str) or not subject.strip():
                raise ValueError("frame %r names an empty subject" % (frame_id,))
        density = raw.get("pixels_per_um")
        if density is not None:
            _positive(density, "pixels_per_um")
        normalized.append(
            {
                "frame_id": frame_id,
                "view": view,
                "quality": grade,
                "subjects": tuple(subjects),
                "pixels_per_um": density,
                "usable": frame_is_usable(grade),
            }
        )
    return normalized


def usable_frames(frames):
    """The frames a future reader could actually take evidence from."""
    return [record for record in normalize_frames(frames) if record["usable"]]


def covered_subjects(frames):
    """Subjects that appear in at least one readable frame."""
    covered = set()
    for record in usable_frames(frames):
        covered.update(record["subjects"])
    return sorted(covered)


def uncovered_subjects(frames, declared_subjects):
    """Declared subjects no readable frame shows."""
    if not isinstance(declared_subjects, (list, tuple)) or len(declared_subjects) == 0:
        raise ValueError("declared_subjects must be a non-empty list")
    covered = set(covered_subjects(frames))
    missing = []
    for subject in declared_subjects:
        if not isinstance(subject, str) or not subject.strip():
            raise ValueError("declared subjects must be non-empty strings")
        if subject not in covered:
            missing.append(subject)
    return sorted(missing)


def missing_views(frames):
    """Required views no readable frame supplies."""
    present = {record["view"] for record in usable_frames(frames)}
    return sorted(view for view in REQUIRED_VIEWS if view not in present)


def under_resolved_frames(frames, feature_size_um):
    """Readable frames that cannot show the smallest feature's condition."""
    feature = _positive(feature_size_um, "feature_size_um")
    short = []
    for record in usable_frames(frames):
        density = record["pixels_per_um"]
        if density is None:
            short.append(record["frame_id"])
        elif not resolution_is_adequate(feature, density):
            short.append(record["frame_id"])
    return sorted(short)


def retention_is_sufficient(retention_years, minimum_years=None):
    """True while an archive holds the record long enough to be useful."""
    held = _count(retention_years, "retention_years", minimum=0)
    floor = _count(
        MINIMUM_RETENTION_YEARS if minimum_years is None else minimum_years,
        "minimum_years",
        minimum=1,
    )
    return held >= floor


def provision_weight(name):
    """Share of the record argument one archive provision supplies."""
    if name not in ARCHIVE_PROVISIONS:
        raise ValueError(
            "unknown archive provision %r (known: %s)"
            % (name, ", ".join(sorted(ARCHIVE_PROVISIONS)))
        )
    return ARCHIVE_PROVISIONS[name]


def provision_state_credit(state):
    """Credit an archive-provision state earns."""
    if state not in PROVISION_STATE_CREDIT:
        raise ValueError(
            "unknown provision state %r (known: %s)"
            % (state, ", ".join(sorted(PROVISION_STATE_CREDIT)))
        )
    return PROVISION_STATE_CREDIT[state]


def assess_provision(name, state):
    """Grade one archive provision into a credit and its findings."""
    weight = provision_weight(name)
    credit = provision_state_credit(state)
    mandatory = name in MANDATORY_ARCHIVE_PROVISIONS
    findings = []
    if state == "not-met":
        findings.append("archive-provision-not-met")
    elif state == "met-not-evidenced":
        findings.append("archive-provision-not-evidenced")
    mandatory_missing = mandatory and state == "not-met"
    if mandatory_missing:
        findings.append("mandatory-archive-provision-not-met")
    return {
        "provision": name,
        "state": state,
        "mandatory": mandatory,
        "weight": weight,
        "credit": credit,
        "weighted_credit": weight * credit,
        "mandatory_missing": mandatory_missing,
        "findings": findings,
    }


def assess_view(view, frames):
    """Grade one required view from the best readable frame that supplies it."""
    weight = view_weight(view)
    best = 0.0
    for record in normalize_frames(frames):
        if record["view"] == view:
            best = max(best, frame_quality_credit(record["quality"]))
    findings = []
    if best <= UNUSABLE_QUALITY_CREDIT + RECORD_TOLERANCE:
        findings.append("required-view-not-supplied")
        if view in MANDATORY_VIEWS:
            findings.append("mandatory-view-not-supplied")
    elif best < 1.0 - RECORD_TOLERANCE:
        findings.append("required-view-supplied-below-full-quality")
    return {
        "view": view,
        "best_frame_credit": best,
        "weight": weight,
        "credit": best,
        "weighted_credit": weight * best,
        "mandatory_missing": view in MANDATORY_VIEWS
        and best <= UNUSABLE_QUALITY_CREDIT + RECORD_TOLERANCE,
        "findings": findings,
    }


def record_adequacy_index(records):
    """Weighted credit of a set of graded views and provisions over total weight."""
    if not isinstance(records, (list, tuple)):
        raise ValueError(
            "records must be a list or tuple, got %r" % (type(records).__name__,)
        )
    if len(records) == 0:
        raise ValueError("a record must carry at least one graded item")
    total_weight = 0.0
    earned = 0.0
    for record in records:
        total_weight += _real(record["weight"], "weight")
        earned += _real(record["weighted_credit"], "weighted_credit")
    if total_weight <= 0.0:
        raise ValueError("total record weight must be positive")
    return earned / total_weight


def assess_photographic_record(
    unit_id,
    declared_subjects,
    frames,
    smallest_feature_um,
    retention_years,
    provisions=None,
    minimum_retention_years=None,
):
    """Grade one internal-circuit photographic record and name a verdict."""
    if not isinstance(unit_id, str) or not unit_id.strip():
        raise ValueError("unit_id must be a non-empty string, got %r" % (unit_id,))
    if provisions is None:
        provisions = {}
    if not isinstance(provisions, dict):
        raise ValueError(
            "provisions must be a mapping, got %r" % (type(provisions).__name__,)
        )
    for name in provisions:
        provision_weight(name)  # validation only

    normalized = normalize_frames(frames)
    missing_subjects = uncovered_subjects(normalized, declared_subjects)
    absent_views = missing_views(normalized)
    under_resolved = under_resolved_frames(normalized, smallest_feature_um)
    retained = retention_is_sufficient(retention_years, minimum_retention_years)

    states = dict(provisions)
    if not retained:
        states["archive-retention-covers-the-hardware-life"] = "not-met"
    elif "archive-retention-covers-the-hardware-life" not in states:
        states["archive-retention-covers-the-hardware-life"] = "met-and-evidenced"

    view_records = [assess_view(view, normalized) for view in sorted(REQUIRED_VIEWS)]
    provision_records = []
    for name in sorted(ARCHIVE_PROVISIONS):
        state = states.get(name, "not-met")
        if not isinstance(state, str):
            raise ValueError("provision state must be a string, got %r" % (state,))
        provision_records.append(assess_provision(name, state))

    index = record_adequacy_index(view_records + provision_records)

    findings = []
    for record in view_records:
        for finding in record["findings"]:
            findings.append(
                {"item": record["view"], "finding": finding, "detail": "view"}
            )
    for record in provision_records:
        for finding in record["findings"]:
            findings.append(
                {"item": record["provision"], "finding": finding, "detail": record["state"]}
            )
    for subject in missing_subjects:
        findings.append(
            {"item": subject, "finding": "subject-not-covered", "detail": "no readable frame"}
        )
    for frame_id in under_resolved:
        findings.append(
            {
                "item": frame_id,
                "finding": "frame-resolution-below-the-feature-floor",
                "detail": "%r um feature" % (smallest_feature_um,),
            }
        )
    if not retained:
        findings.append(
            {
                "item": "archive",
                "finding": "retention-shorter-than-required",
                "detail": "%r years" % (retention_years,),
            }
        )

    mandatory_view_missing = any(r["mandatory_missing"] for r in view_records)
    mandatory_provision_missing = any(r["mandatory_missing"] for r in provision_records)

    if mandatory_view_missing or missing_subjects:
        verdict = "photographic-record-incomplete"
    elif (
        mandatory_provision_missing
        or under_resolved
        or index < ACCEPTANCE_INDEX - RECORD_TOLERANCE
    ):
        verdict = "photographic-record-not-accepted"
    elif findings:
        verdict = "photographic-record-accepted-with-open-actions"
    else:
        verdict = "photographic-record-accepted"

    return {
        "unit_id": unit_id,
        "frame_count": len(normalized),
        "usable_frame_count": len(usable_frames(normalized)),
        "covered_subjects": covered_subjects(normalized),
        "uncovered_subjects": missing_subjects,
        "missing_views": absent_views,
        "under_resolved_frames": under_resolved,
        "retention_sufficient": retained,
        "view_records": view_records,
        "provision_records": provision_records,
        "record_adequacy_index": index,
        "findings": findings,
        "verdict": verdict,
        "record_accepted": verdict
        in (
            "photographic-record-accepted",
            "photographic-record-accepted-with-open-actions",
        ),
    }
