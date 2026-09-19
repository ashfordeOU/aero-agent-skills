"""Calibration and sensitivity control of cleanliness measurement equipment.

Anchor: ECSS-Q-ST-70-01C, verification clause -- keeping the instruments that
produce cleanliness evidence calibrated, traceable and sensitive enough for
the tightest requirement each of them polices. Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Walk each instrument's calibration forward from its last certificate by
   whole calendar months, clamping a day that does not exist in the month it
   lands in, and report the days left on the day the measurement is taken.
2. Compare the detection floor the instrument achieves in service with the
   tightest cleanliness value it has to resolve, through a sensitivity ratio
   rather than a bare comparison.
3. Combine the independent uncertainty contributions in quadrature and form
   the ratio of the tolerance the instrument polices to that combined
   uncertainty.
4. Grade a particle counter's sizing error against the smallest bin it
   reports, since a sizing error comparable with the bin width moves counts
   between bins.
5. Summarise an instrument set into a status per instrument, the blocking
   findings, and whether the set as a whole may be used for the campaign.
"""

import datetime
import math

__all__ = [
    "MIN_SENSITIVITY_RATIO",
    "MIN_TOLERANCE_UNCERTAINTY_RATIO",
    "DUE_SOON_DAYS",
    "RATIO_TOLERANCE",
    "add_calendar_months",
    "calibration_due_date",
    "days_until_due",
    "calibration_status",
    "sensitivity_ratio",
    "sensitivity_is_adequate",
    "combine_uncertainty",
    "tolerance_uncertainty_ratio",
    "sizing_error_is_acceptable",
    "assess_instrument",
    "assess_equipment_set",
]

# An instrument has to resolve the value it polices several times over before
# a reading near that value means anything.
MIN_SENSITIVITY_RATIO = 3.0

# The tolerance an instrument polices has to stand well clear of the
# uncertainty it carries.
MIN_TOLERANCE_UNCERTAINTY_RATIO = 4.0

# Inside this many days a certificate is reported as due soon so the campaign
# can be planned around it.
DUE_SOON_DAYS = 30

# Ratios of measured quantities land on their bound inexactly; absorb the
# representation error here rather than by lowering the bound.
RATIO_TOLERANCE = 1e-9

_MAX_SIZING_ERROR_FRACTION = 0.10


def _finite(label, value):
    """Return value as a finite float or raise."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    return number


def _positive(label, value):
    """Return value as a strictly positive finite float or raise."""
    number = _finite(label, value)
    if number <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return number


def _as_date(label, value):
    """Return value as a datetime.date, accepting an ISO yyyy-mm-dd string."""
    if isinstance(value, datetime.datetime):
        return value.date()
    if isinstance(value, datetime.date):
        return value
    if isinstance(value, str):
        try:
            return datetime.date.fromisoformat(value.strip())
        except ValueError:
            raise ValueError("%s must be an ISO yyyy-mm-dd date, got %r" % (label, value))
    raise ValueError("%s must be a date or an ISO yyyy-mm-dd string" % label)


def add_calendar_months(start, months):
    """Return the date whole calendar months after start, clamping the day."""
    base = _as_date("start", start)
    if not isinstance(months, int) or isinstance(months, bool):
        raise ValueError("months must be an integer")
    if months <= 0:
        raise ValueError("months must be positive, got %d" % months)
    total = base.month - 1 + months
    year = base.year + total // 12
    month = total % 12 + 1
    if month == 12:
        next_month_start = datetime.date(year + 1, 1, 1)
    else:
        next_month_start = datetime.date(year, month + 1, 1)
    last_day = (next_month_start - datetime.timedelta(days=1)).day
    return datetime.date(year, month, min(base.day, last_day))


def calibration_due_date(last_calibration, interval_months):
    """Return the day the certificate stops covering the instrument."""
    return add_calendar_months(last_calibration, interval_months)


def days_until_due(last_calibration, interval_months, reference_date):
    """Return the days left on the certificate at the reference date."""
    due = calibration_due_date(last_calibration, interval_months)
    reference = _as_date("reference_date", reference_date)
    return (due - reference).days


def calibration_status(last_calibration, interval_months, reference_date):
    """Return 'in-date', 'due-soon' or 'overdue' at the reference date."""
    remaining = days_until_due(last_calibration, interval_months, reference_date)
    if remaining < 0:
        return "overdue"
    if remaining <= DUE_SOON_DAYS:
        return "due-soon"
    return "in-date"


def sensitivity_ratio(required_value, detection_floor):
    """Return how many times over the instrument resolves the value it polices."""
    required = _positive("required_value", required_value)
    floor = _positive("detection_floor", detection_floor)
    return required / floor


def sensitivity_is_adequate(required_value, detection_floor,
                            minimum_ratio=MIN_SENSITIVITY_RATIO):
    """Return True when the detection floor clears the required value with margin."""
    ratio = sensitivity_ratio(required_value, detection_floor)
    minimum = _positive("minimum_ratio", minimum_ratio)
    return ratio > minimum or math.isclose(
        ratio, minimum, rel_tol=RATIO_TOLERANCE, abs_tol=0.0
    )


def combine_uncertainty(components):
    """Return the root-sum-square of independent uncertainty contributions."""
    if not isinstance(components, (list, tuple)) or not components:
        raise ValueError("components must be a non-empty sequence")
    total = 0.0
    for index, item in enumerate(components):
        value = _finite("components[%d]" % index, item)
        if value < 0.0:
            raise ValueError("components[%d] must not be negative" % index)
        total += value * value
    return math.sqrt(total)


def tolerance_uncertainty_ratio(tolerance, combined_uncertainty):
    """Return the ratio of the policed tolerance to the combined uncertainty."""
    span = _positive("tolerance", tolerance)
    uncertainty = _positive("combined_uncertainty", combined_uncertainty)
    return span / uncertainty


def sizing_error_is_acceptable(sizing_error_um, smallest_bin_um):
    """Return True when the counter's sizing error stays small against its bin."""
    error = _finite("sizing_error_um", sizing_error_um)
    if error < 0.0:
        raise ValueError("sizing_error_um must not be negative")
    bin_width = _positive("smallest_bin_um", smallest_bin_um)
    fraction = error / bin_width
    return fraction < _MAX_SIZING_ERROR_FRACTION or math.isclose(
        fraction, _MAX_SIZING_ERROR_FRACTION, rel_tol=RATIO_TOLERANCE, abs_tol=0.0
    )


def assess_instrument(instrument, reference_date):
    """Return the control status of one cleanliness measurement instrument.

    instrument keys: id, last_calibration, interval_months, required_value,
    detection_floor; optional tolerance, uncertainty_components, traceable,
    sizing_error_um, smallest_bin_um, minimum_ratio.
    """
    if not isinstance(instrument, dict):
        raise ValueError("instrument must be a mapping")
    for key in ("id", "last_calibration", "interval_months", "required_value",
                "detection_floor"):
        if key not in instrument:
            raise ValueError("instrument missing required key '%s'" % key)
    identifier = instrument["id"]
    if not isinstance(identifier, str) or not identifier.strip():
        raise ValueError("instrument['id'] must be a non-empty string")
    identifier = identifier.strip()
    status = calibration_status(
        instrument["last_calibration"], instrument["interval_months"], reference_date
    )
    remaining = days_until_due(
        instrument["last_calibration"], instrument["interval_months"], reference_date
    )
    ratio = sensitivity_ratio(
        instrument["required_value"], instrument["detection_floor"]
    )
    minimum_ratio = _positive(
        "minimum_ratio", instrument.get("minimum_ratio", MIN_SENSITIVITY_RATIO)
    )
    adequate = sensitivity_is_adequate(
        instrument["required_value"], instrument["detection_floor"], minimum_ratio
    )
    findings = []
    if status == "overdue":
        findings.append(
            "%s calibration expired %d days before the measurement date"
            % (identifier, -remaining)
        )
    elif status == "due-soon":
        findings.append(
            "%s has %d days of calibration left; plan the campaign around it"
            % (identifier, remaining)
        )
    if not adequate:
        findings.append(
            "%s resolves the policed value only %.4g times over, below the "
            "minimum ratio of %.4g" % (identifier, ratio, minimum_ratio)
        )
    entry = {
        "id": identifier,
        "calibration_status": status,
        "days_until_due": remaining,
        "sensitivity_ratio": ratio,
        "sensitivity_adequate": adequate,
        "findings": findings,
    }
    components = instrument.get("uncertainty_components")
    if components is not None:
        combined = combine_uncertainty(components)
        entry["combined_uncertainty"] = combined
        if instrument.get("tolerance") is not None:
            tur = tolerance_uncertainty_ratio(instrument["tolerance"], combined)
            entry["tolerance_uncertainty_ratio"] = tur
            adequate_tur = tur > MIN_TOLERANCE_UNCERTAINTY_RATIO or math.isclose(
                tur, MIN_TOLERANCE_UNCERTAINTY_RATIO, rel_tol=RATIO_TOLERANCE,
                abs_tol=0.0
            )
            if not adequate_tur:
                findings.append(
                    "%s polices a tolerance only %.4g times its combined "
                    "uncertainty, below %.4g"
                    % (identifier, tur, MIN_TOLERANCE_UNCERTAINTY_RATIO)
                )
    if instrument.get("sizing_error_um") is not None:
        if instrument.get("smallest_bin_um") is None:
            raise ValueError(
                "a declared sizing_error_um needs smallest_bin_um beside it"
            )
        sizing_ok = sizing_error_is_acceptable(
            instrument["sizing_error_um"], instrument["smallest_bin_um"]
        )
        entry["sizing_acceptable"] = sizing_ok
        if not sizing_ok:
            findings.append(
                "%s sizing error %.4g um is large against its %.4g um bin; counts "
                "move between bins"
                % (identifier, float(instrument["sizing_error_um"]),
                   float(instrument["smallest_bin_um"]))
            )
    if not bool(instrument.get("traceable", True)):
        findings.append(
            "%s carries no traceable calibration chain; its readings cannot "
            "support a verification claim" % identifier
        )
    entry["usable"] = not findings
    return entry


def assess_equipment_set(spec):
    """Return the control state of the instrument set for a campaign.

    spec keys: instruments (sequence of instrument mappings), reference_date.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("instruments", "reference_date"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    instruments = spec["instruments"]
    if not isinstance(instruments, (list, tuple)) or not instruments:
        raise ValueError("spec['instruments'] must be a non-empty sequence")
    entries = [assess_instrument(item, spec["reference_date"]) for item in instruments]
    seen = []
    for entry in entries:
        if entry["id"] in seen:
            raise ValueError("duplicate instrument id %r" % entry["id"])
        seen.append(entry["id"])
    findings = []
    for entry in entries:
        findings.extend(entry["findings"])
    blocked = [entry["id"] for entry in entries if not entry["usable"]]
    return {
        "entries": entries,
        "blocked": blocked,
        "usable_fraction": (len(entries) - len(blocked)) / float(len(entries)),
        "findings": findings,
        "set_usable": not blocked,
    }
