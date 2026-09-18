#!/usr/bin/env python3
"""Photographic evidence set of an electromagnetic test report for
ECSS-E-ST-20-07C clause 5.2.13.

Paraphrased, implementable procedure (no verbatim standard text):

* A written description of a bench does not let a second laboratory rebuild
  it. The report therefore carries photographs of every setup arrangement,
  every test point and every calibration arrangement used during the
  campaign, and the photographs travel inside the report rather than beside
  it in a folder.
* Every subject that must be photographed is listed before the frames are
  audited, and each subject is categorized by what it documents: a setup
  arrangement, a test point, or a calibration arrangement.
* A setup arrangement needs more than one distinct view, because a single
  elevation hides the routing and the separations that make the arrangement
  reproducible. Repeating the same view does not add coverage.
* Every frame carries enough metadata to be usable evidence: resolution
  above a floor, a caption long enough to name what is shown, an
  identification label tying the frame to its subject, and a scale reference
  wherever the geometry is what is being shown.
* A frame captured long before or long after the arrangement it claims to
  document is evidence of a different bench and is rejected on its capture
  offset, not on its content.
* A frame that exists but was never placed in the report has not been
  delivered. Any open finding holds the report.

Stdlib only, offline, deterministic.
"""

import math

# Named tolerance absorbing binary representation error in megapixel and
# minute-offset comparisons. It is NOT an evidence allowance: the floors
# themselves are never lowered.
PHOTO_EPS = 1e-9

SETUP_ARRANGEMENT = "setup-arrangement"
TEST_POINT = "test-point"
CALIBRATION_ARRANGEMENT = "calibration-arrangement"

# Subject kind on the campaign record -> photographic subject category.
SUBJECT_CATEGORY = {
    "emission-setup": SETUP_ARRANGEMENT,
    "susceptibility-setup": SETUP_ARRANGEMENT,
    "harness-routing-setup": SETUP_ARRANGEMENT,
    "probe-test-point": TEST_POINT,
    "injection-test-point": TEST_POINT,
    "monitor-test-point": TEST_POINT,
    "antenna-calibration": CALIBRATION_ARRANGEMENT,
    "probe-calibration": CALIBRATION_ARRANGEMENT,
    "reference-level-calibration": CALIBRATION_ARRANGEMENT,
}

# Categories whose evidence is geometric, so a dimensional reference has to
# appear in the frame.
SCALE_REFERENCE_CATEGORIES = (SETUP_ARRANGEMENT, CALIBRATION_ARRANGEMENT)

DEFAULT_PHOTO_SPEC = {
    "min_megapixels": 2.0,
    "min_caption_characters": 20.0,
    "min_views_setup_arrangement": 2.0,
    "min_views_test_point": 1.0,
    "min_views_calibration_arrangement": 1.0,
    "max_capture_offset_minutes": 120.0,
}

_CATEGORY_VIEW_KEY = {
    SETUP_ARRANGEMENT: "min_views_setup_arrangement",
    TEST_POINT: "min_views_test_point",
    CALIBRATION_ARRANGEMENT: "min_views_calibration_arrangement",
}


def _require_number(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    if math.isnan(value) or math.isinf(value):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return float(value)


def _require_text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value


def _at_least(value, floor_value):
    """True when value reaches floor_value, absorbing representation error."""
    return value >= floor_value or math.isclose(
        value, floor_value, rel_tol=0.0, abs_tol=PHOTO_EPS
    )


def _not_above(value, limit):
    """True when value does not exceed limit, absorbing representation error."""
    return value <= limit or math.isclose(value, limit, rel_tol=0.0, abs_tol=PHOTO_EPS)


def resolve_spec(overrides=None):
    """Merge caller overrides onto the standard evidence specification."""
    spec = dict(DEFAULT_PHOTO_SPEC)
    if overrides is None:
        return spec
    if not isinstance(overrides, dict):
        raise ValueError("spec overrides must be a mapping, got %r" % (overrides,))
    for key, value in overrides.items():
        if key not in DEFAULT_PHOTO_SPEC:
            raise ValueError("unrecognized photographic specification key %r" % (key,))
        number = _require_number(value, "spec %r" % key)
        if number < 0.0:
            raise ValueError("spec %r must not be negative, got %r" % (key, value))
        spec[key] = number
    return spec


def categorize_subject(subject):
    """Map one campaign subject to its photographic category."""
    if not isinstance(subject, dict):
        raise ValueError("subject must be a mapping, got %r" % (subject,))
    name = _require_text(subject.get("name"), "subject 'name'")
    kind = subject.get("kind")
    if kind not in SUBJECT_CATEGORY:
        raise ValueError(
            "subject %r has unrecognized kind %r (expected one of %s)"
            % (name, kind, ", ".join(sorted(SUBJECT_CATEGORY)))
        )
    return SUBJECT_CATEGORY[kind]


def catalogue_subjects(subjects):
    """Build the list of subjects the report has to photograph."""
    if not isinstance(subjects, (list, tuple)) or not subjects:
        raise ValueError("subjects must be a non-empty sequence")
    catalogue = []
    names = []
    for subject in subjects:
        category = categorize_subject(subject)
        catalogue.append(
            {
                "name": subject["name"],
                "kind": subject["kind"],
                "category": category,
                "reference_time_minutes": _require_number(
                    subject.get("reference_time_minutes", 0.0),
                    "subject %r reference_time_minutes" % subject["name"],
                ),
            }
        )
        names.append(subject["name"])
    if len(set(names)) != len(names):
        raise ValueError("subject names must be unique, got %r" % (names,))
    if not any(item["category"] == SETUP_ARRANGEMENT for item in catalogue):
        raise ValueError("a campaign record holds at least one setup arrangement")
    return catalogue


def megapixels(width_px, height_px):
    """Frame resolution in megapixels from its pixel dimensions."""
    width = _require_number(width_px, "width_px")
    height = _require_number(height_px, "height_px")
    if width <= 0.0 or height <= 0.0:
        raise ValueError(
            "pixel dimensions must be positive, got %r x %r" % (width_px, height_px)
        )
    return (width * height) / 1.0e6


def required_views(category, spec=None):
    """Distinct views a subject of this category has to carry."""
    if category not in _CATEGORY_VIEW_KEY:
        raise ValueError("unrecognized photographic category %r" % (category,))
    spec = resolve_spec(spec)
    return spec[_CATEGORY_VIEW_KEY[category]]


def check_frame(frame, catalogue, spec=None):
    """Audit one photograph against the evidence specification."""
    spec = resolve_spec(spec)
    if not isinstance(frame, dict):
        raise ValueError("frame must be a mapping, got %r" % (frame,))
    frame_id = _require_text(frame.get("id"), "frame 'id'")
    subject_name = _require_text(frame.get("subject"), "frame %r subject" % frame_id)
    if not isinstance(catalogue, (list, tuple)):
        raise ValueError("catalogue must be a sequence")
    subject = None
    for item in catalogue:
        if item["name"] == subject_name:
            subject = item
            break
    if subject is None:
        raise ValueError(
            "frame %r names subject %r which is not on the campaign record"
            % (frame_id, subject_name)
        )
    view = _require_text(frame.get("view"), "frame %r view" % frame_id)
    resolution = megapixels(frame.get("width_px"), frame.get("height_px"))
    caption = frame.get("caption", "")
    if not isinstance(caption, str):
        raise ValueError("frame %r caption must be a string, got %r" % (frame_id, caption))
    capture_time = _require_number(
        frame.get("capture_time_minutes"), "frame %r capture_time_minutes" % frame_id
    )
    offset = abs(capture_time - subject["reference_time_minutes"])
    included = frame.get("in_report")
    if not isinstance(included, bool):
        raise ValueError("frame %r in_report must be a boolean, got %r" % (frame_id, included))
    labelled = frame.get("identification_label")
    if not isinstance(labelled, bool):
        raise ValueError(
            "frame %r identification_label must be a boolean, got %r" % (frame_id, labelled)
        )
    scale = frame.get("scale_reference")
    if not isinstance(scale, bool):
        raise ValueError(
            "frame %r scale_reference must be a boolean, got %r" % (frame_id, scale)
        )

    findings = []
    if not _at_least(resolution, spec["min_megapixels"]):
        findings.append("frame %s resolution below the evidence floor" % frame_id)
    if not _at_least(float(len(caption.strip())), spec["min_caption_characters"]):
        findings.append("frame %s caption too short to name its subject" % frame_id)
    if not labelled:
        findings.append("frame %s carries no identification label" % frame_id)
    if subject["category"] in SCALE_REFERENCE_CATEGORIES and not scale:
        findings.append("frame %s shows geometry without a scale reference" % frame_id)
    if not _not_above(offset, spec["max_capture_offset_minutes"]):
        findings.append("frame %s captured outside the arrangement validity window" % frame_id)
    if not included:
        findings.append("frame %s captured but absent from the report" % frame_id)

    return {
        "id": frame_id,
        "subject": subject_name,
        "category": subject["category"],
        "view": view,
        "megapixels": resolution,
        "capture_offset_minutes": offset,
        "in_report": included,
        "findings": findings,
        "usable": not findings,
    }


def view_coverage(audited):
    """Distinct usable views held per subject; a repeated view counts once."""
    if not isinstance(audited, (list, tuple)):
        raise ValueError("audited frames must be a sequence")
    coverage = {}
    for record in audited:
        if not isinstance(record, dict) or "subject" not in record:
            raise ValueError("audited frame record missing 'subject': %r" % (record,))
        if not record.get("usable"):
            continue
        coverage.setdefault(record["subject"], set()).add(record["view"])
    return {name: sorted(views) for name, views in coverage.items()}


def check_coverage(catalogue, coverage, spec=None):
    """Findings for every subject short of its distinct-view requirement."""
    spec = resolve_spec(spec)
    if not isinstance(coverage, dict):
        raise ValueError("coverage must be a mapping, got %r" % (coverage,))
    findings = []
    shortfalls = []
    for subject in catalogue:
        held = len(coverage.get(subject["name"], ()))
        needed = required_views(subject["category"], spec)
        if not _at_least(float(held), needed):
            findings.append(
                "subject %s holds %d usable view(s), the report needs %d"
                % (subject["name"], held, int(needed))
            )
            shortfalls.append(
                {"subject": subject["name"], "held": held, "needed": needed}
            )
    return {"findings": findings, "shortfalls": shortfalls}


def report_status(findings):
    """Gate token for the finding list of one report."""
    if not isinstance(findings, (list, tuple)):
        raise ValueError("findings must be a sequence, got %r" % (findings,))
    return "report-photographically-complete" if not findings else "hold-report"


def audit_photographic_record(record):
    """End-to-end clause 5.2.13 photographic evidence audit for one report."""
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping")
    for key in ("subjects", "frames"):
        if key not in record:
            raise ValueError("record missing required key %r" % (key,))
    spec = record.get("spec")
    catalogue = catalogue_subjects(record["subjects"])
    frames = record["frames"]
    if not isinstance(frames, (list, tuple)) or not frames:
        raise ValueError("frames must be a non-empty sequence")
    audited = [check_frame(frame, catalogue, spec) for frame in frames]
    ids = [item["id"] for item in audited]
    if len(set(ids)) != len(ids):
        raise ValueError("frame ids must be unique, got %r" % (ids,))
    coverage = view_coverage(audited)
    coverage_result = check_coverage(catalogue, coverage, spec)

    findings = []
    for item in audited:
        findings.extend(item["findings"])
    findings.extend(coverage_result["findings"])

    return {
        "catalogue": catalogue,
        "frames": audited,
        "coverage": coverage,
        "shortfalls": coverage_result["shortfalls"],
        "findings": findings,
        "status": report_status(findings),
        "complete": not findings,
    }
