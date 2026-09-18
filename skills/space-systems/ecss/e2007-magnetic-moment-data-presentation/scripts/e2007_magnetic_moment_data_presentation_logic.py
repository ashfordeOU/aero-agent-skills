#!/usr/bin/env python3
"""Magnetic moment data presentation, ECSS-E-ST-20-07C clause 5.4.5.4.

Paraphrased procedure, no verbatim standard text. Steady magnetic emission is
not a spectrum, so the general emission-presentation rules do not serve it.
This clause replaces them: the result is reported as a value for every
declared measurement distance and every axis, not as a plot and not as one
summary figure. This module turns that into a deterministic assessment:

  declared presentation form -> is the table being used at all
  rows vs declared distances -> is every distance reported
  rows vs axes               -> is every axis reported at each distance
  axis components            -> does the stated resultant match them
  field and distance         -> does each distance imply the same moment

The last check is the one a reader cannot do by eye: a steady dipole field
falls with the cube of distance, so the moment implied by each row should
agree across the table. A row filed against the wrong distance, or a near
row still inside the multipole region, breaks that agreement.

stdlib only, offline, deterministic.
"""

from __future__ import annotations

import math

# Fields, distances and derived moments are floats, so a value that agrees
# exactly can land a few units in the last place apart. These tolerances
# absorb representation error only.
FIELD_REL_TOL = 1e-12
FIELD_ABS_TOL = 1e-9
DISTANCE_REL_TOL = 1e-12
DISTANCE_ABS_TOL = 1e-12

# Axial dipole field in nanotesla at r metres from a moment m A*m^2:
# (mu0 / 4*pi) * 2m / r^3 expressed in nT.
MU0_OVER_4PI_T_M_PER_A = 1e-7
NT_PER_T = 1e9
AXIAL_DIPOLE_NT_COEFF = NT_PER_T * MU0_OVER_4PI_T_M_PER_A * 2.0

REQUIRED_AXES = ("x", "y", "z")
AXIS_RESULTANT = "resultant"
RECOGNIZED_AXES = REQUIRED_AXES + (AXIS_RESULTANT,)

FORM_TABLE = "per-distance-per-axis-table"
FORM_PLOT = "amplitude-versus-frequency-plot"
FORM_SUMMARY = "single-summary-value"
RECOGNIZED_FORMS = (FORM_TABLE, FORM_PLOT, FORM_SUMMARY)

# How far the resultant a report states may sit from the one its own axis
# components give before the row is treated as inconsistent.
DEFAULT_RESULTANT_REL_TOL = 0.02
# How far the moments implied by different distances may spread before the
# table stops describing one steady source.
DEFAULT_MOMENT_REL_TOL = 0.25

PRESENTATION_COMPLETE = "presentation-complete"
PRESENTATION_DEFICIENT = "presentation-deficient"


def _number(record, key, where):
    if key not in record:
        raise ValueError("%s: missing required field %r" % (where, key))
    value = record[key]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s: field %r must be numeric, got %r" % (where, key, value))
    value = float(value)
    if math.isnan(value) or math.isinf(value):
        raise ValueError("%s: field %r must be finite, got %r" % (where, key, value))
    return value


def _scalar(value, name):
    return _number({"v": value}, "v", name)


def _flag(record, key, where):
    if key not in record:
        raise ValueError("%s: missing required field %r" % (where, key))
    value = record[key]
    if not isinstance(value, bool):
        raise ValueError("%s: field %r must be a boolean, got %r" % (where, key, value))
    return value


def same_distance(a, b):
    """True when two reported distances are the same measurement point."""
    return math.isclose(a, b, rel_tol=DISTANCE_REL_TOL, abs_tol=DISTANCE_ABS_TOL)


def normalize_axis(token):
    """Normalize an axis label to x, y, z or the resultant."""
    if not isinstance(token, str):
        raise ValueError("axis must be a string, got %r" % (token,))
    value = token.strip().lower()
    if value not in RECOGNIZED_AXES:
        raise ValueError(
            "unrecognized axis %r; recognized: %s"
            % (token, ", ".join(RECOGNIZED_AXES))
        )
    return value


def normalize_form(token):
    """Normalize the declared presentation form."""
    if not isinstance(token, str):
        raise ValueError("presented_as must be a string, got %r" % (token,))
    value = token.strip().lower()
    if value not in RECOGNIZED_FORMS:
        raise ValueError(
            "unrecognized presented_as %r; recognized: %s"
            % (token, ", ".join(RECOGNIZED_FORMS))
        )
    return value


def validate_row(row, where="row"):
    """Validate one reported result and return it normalized."""
    if not isinstance(row, dict):
        raise ValueError("%s: row must be a mapping" % where)
    distance = _number(row, "distance_m", where)
    if distance <= 0.0:
        raise ValueError("%s: distance_m must be > 0, got %g" % (where, distance))
    field = _number(row, "field_nt", where)
    if field < 0.0:
        raise ValueError("%s: field_nt must be >= 0, got %g" % (where, field))
    if "axis" not in row:
        raise ValueError("%s: missing required field 'axis'" % where)
    try:
        axis = normalize_axis(row["axis"])
    except ValueError as exc:
        raise ValueError("%s: %s" % (where, exc))
    return {"distance_m": distance, "axis": axis, "field_nt": field}


def validate_rows(rows):
    """Validate the reported table and return it normalized."""
    if not isinstance(rows, (list, tuple)):
        raise ValueError("rows must be a list")
    if not rows:
        raise ValueError("rows must hold at least one reported result")
    out = []
    for index, row in enumerate(rows):
        normalized = validate_row(row, "row %d" % (index + 1))
        for earlier in out:
            if earlier["axis"] == normalized["axis"] and same_distance(
                earlier["distance_m"], normalized["distance_m"]
            ):
                raise ValueError(
                    "row %d: axis %s at %g m is reported twice"
                    % (index + 1, normalized["axis"], normalized["distance_m"])
                )
        out.append(normalized)
    return out


def reported_distances(rows):
    """Distinct measurement distances the table reports, nearest first."""
    out = []
    for row in rows:
        if not any(same_distance(row["distance_m"], d) for d in out):
            out.append(row["distance_m"])
    return sorted(out)


def rows_at_distance(rows, distance_m):
    """Rows belonging to one measurement distance."""
    distance = _scalar(distance_m, "distance_m")
    return [r for r in rows if same_distance(r["distance_m"], distance)]


def resultant_nt(bx_nt, by_nt, bz_nt):
    """Resultant steady field from its three axis components."""
    bx = _scalar(bx_nt, "bx_nt")
    by = _scalar(by_nt, "by_nt")
    bz = _scalar(bz_nt, "bz_nt")
    return math.sqrt(bx * bx + by * by + bz * bz)


def implied_dipole_moment_am2(field_nt, distance_m):
    """Moment a steady field at a given distance implies for a point dipole."""
    field = _scalar(field_nt, "field_nt")
    distance = _scalar(distance_m, "distance_m")
    if field < 0.0:
        raise ValueError("field_nt must be >= 0, got %g" % field)
    if distance <= 0.0:
        raise ValueError("distance_m must be > 0, got %g" % distance)
    return field * distance * distance * distance / AXIAL_DIPOLE_NT_COEFF


def missing_distances(rows, required_distances_m):
    """Declared measurement distances the table never reports."""
    if not isinstance(required_distances_m, (list, tuple)):
        raise ValueError("required_distances_m must be a list")
    if not required_distances_m:
        raise ValueError("required_distances_m must name at least one distance")
    present = reported_distances(rows)
    out = []
    for index, value in enumerate(required_distances_m):
        distance = _scalar(value, "required_distances_m[%d]" % index)
        if distance <= 0.0:
            raise ValueError(
                "required_distances_m[%d] must be > 0, got %g" % (index, distance)
            )
        if not any(same_distance(distance, d) for d in present):
            out.append(distance)
    return out


def missing_axes(rows, distance_m):
    """Axes not reported at one measurement distance."""
    here = {r["axis"] for r in rows_at_distance(rows, distance_m)}
    return [axis for axis in REQUIRED_AXES if axis not in here]


def resultant_at_distance(rows, distance_m):
    """Resultant at a distance: the reported one, else built from the axes."""
    here = rows_at_distance(rows, distance_m)
    for row in here:
        if row["axis"] == AXIS_RESULTANT:
            return row["field_nt"]
    values = {}
    for row in here:
        values[row["axis"]] = row["field_nt"]
    if any(axis not in values for axis in REQUIRED_AXES):
        return None
    return resultant_nt(values["x"], values["y"], values["z"])


def resultant_consistency_findings(rows, rel_tol=DEFAULT_RESULTANT_REL_TOL):
    """Report a stated resultant that its own axis components contradict."""
    tolerance = _scalar(rel_tol, "rel_tol")
    if tolerance <= 0.0:
        raise ValueError("rel_tol must be > 0, got %g" % tolerance)
    out = []
    for distance in reported_distances(rows):
        here = rows_at_distance(rows, distance)
        stated = None
        values = {}
        for row in here:
            if row["axis"] == AXIS_RESULTANT:
                stated = row["field_nt"]
            else:
                values[row["axis"]] = row["field_nt"]
        if stated is None or any(axis not in values for axis in REQUIRED_AXES):
            continue
        built = resultant_nt(values["x"], values["y"], values["z"])
        if math.isclose(stated, built, rel_tol=tolerance, abs_tol=FIELD_ABS_TOL):
            continue
        out.append(
            "at %g m the reported resultant %g nT does not follow from the axis "
            "components, which give %g nT" % (distance, stated, built)
        )
    return out


def moment_consistency_findings(rows, rel_tol=DEFAULT_MOMENT_REL_TOL):
    """Report distances whose implied moments do not agree with each other."""
    tolerance = _scalar(rel_tol, "rel_tol")
    if tolerance <= 0.0:
        raise ValueError("rel_tol must be > 0, got %g" % tolerance)
    moments = implied_moments(rows)
    usable = [(d, m) for d, m in moments if m is not None and m > 0.0]
    if len(usable) < 2:
        return []
    lowest = min(m for _, m in usable)
    highest = max(m for _, m in usable)
    spread = (highest - lowest) / lowest
    if spread <= tolerance or math.isclose(
        spread, tolerance, rel_tol=FIELD_REL_TOL, abs_tol=FIELD_ABS_TOL
    ):
        return []
    return [
        "implied moments run from %g to %g A*m2 across the reported distances, a "
        "spread of %g against a %g allowance; at least one row is filed against "
        "the wrong distance or sits inside the multipole region"
        % (lowest, highest, spread, tolerance)
    ]


def implied_moments(rows):
    """Moment implied at each reported distance, nearest first."""
    out = []
    for distance in reported_distances(rows):
        field = resultant_at_distance(rows, distance)
        if field is None:
            out.append((distance, None))
        else:
            out.append((distance, implied_dipole_moment_am2(field, distance)))
    return out


def presentation_form_findings(presented_as):
    """Report a report that keeps the general rules instead of this clause."""
    form = normalize_form(presented_as)
    if form == FORM_TABLE:
        return []
    if form == FORM_PLOT:
        return [
            "results are carried as an amplitude-against-frequency plot; a steady "
            "field has no spectrum to plot, and this clause replaces that general "
            "presentation with a value per distance and per axis"
        ]
    return [
        "results are carried as one summary figure; the clause needs a value per "
        "distance and per axis so the distance behaviour stays visible"
    ]


def assess_magnetic_moment_data_presentation(
    report,
    resultant_rel_tol=DEFAULT_RESULTANT_REL_TOL,
    moment_rel_tol=DEFAULT_MOMENT_REL_TOL,
):
    """Full clause 5.4.5.4 assessment of a steady magnetic emission report."""
    where = "report"
    if not isinstance(report, dict):
        raise ValueError("%s: record must be a mapping" % where)
    if "presented_as" not in report:
        raise ValueError("%s: missing required field 'presented_as'" % where)
    if "rows" not in report:
        raise ValueError("%s: missing required field 'rows'" % where)
    if "required_distances_m" not in report:
        raise ValueError("%s: missing required field 'required_distances_m'" % where)

    form = normalize_form(report["presented_as"])
    rows = validate_rows(report["rows"])
    uncertainty = _flag(report, "uncertainty_stated", where)

    findings = list(presentation_form_findings(form))

    absent = missing_distances(rows, report["required_distances_m"])
    for distance in absent:
        findings.append(
            "no result is reported at the declared distance %g m" % distance
        )

    gaps = {}
    for distance in reported_distances(rows):
        gap = missing_axes(rows, distance)
        gaps[distance] = gap
        if gap:
            findings.append(
                "at %g m the table is missing the %s axis result"
                % (distance, ", ".join(gap))
            )

    findings.extend(resultant_consistency_findings(rows, resultant_rel_tol))
    findings.extend(moment_consistency_findings(rows, moment_rel_tol))

    moments = implied_moments(rows)
    limitations = []
    if not uncertainty:
        limitations.append(
            "no measurement uncertainty is stated, so the margin against a moment "
            "budget cannot be taken from the table alone"
        )
    if len(reported_distances(rows)) < 2:
        limitations.append(
            "only one distance is reported, so the distance behaviour that would "
            "confirm a single dipole source cannot be checked"
        )

    return {
        "presented_as": form,
        "rows": rows,
        "reported_distances_m": reported_distances(rows),
        "missing_distances_m": absent,
        "missing_axes": gaps,
        "implied_moments_am2": moments,
        "findings": findings,
        "limitations": limitations,
        "verdict": PRESENTATION_COMPLETE if not findings else PRESENTATION_DEFICIENT,
    }
