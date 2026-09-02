#!/usr/bin/env python3
"""AS9100-style calibration control logic (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, as9100: gated): AS9100
requires monitoring and measuring resources to be controlled and
calibrated or verified at specified intervals, with traceability to
national or international measurement standards (paraphrase of clause
7.1.5 practice). The organization decides who calibrates (internal
metrology lab or accredited external provider), keeps calibration
records with status labels, and withdraws equipment whose calibration
has lapsed or drifted out of tolerance.

Decision rules implemented here:

1. tar_verdict(standard_accuracy, unit_accuracy): test accuracy ratio
   (TAR) = standard_accuracy / unit_accuracy. Both accuracies must use
   the same unit or the same fraction convention (e.g. both as
   fractions of reading, or both in the same engineering unit). The
   widely used 4:1 guidance is the floor: ratio >= 4.0 -> 'ok', below
   4.0 -> 'insufficient'.

2. calibration_due_verdict(days_until_due): days_until_due >= 0 ->
   'ok' (due today is still within the interval); negative -> 'overdue'
   (withdraw the instrument until recalibrated).

3. tolerance_check(measured, nominal, tolerance): |measured - nominal|
   <= tolerance -> 'in-tolerance', otherwise 'out'. A tiny relative
   epsilon (1e-12 of the largest of 1.0, |measured|, |nominal|)
   absorbs binary floating-point rounding at the exact boundary, so a
   deviation equal to tolerance within float precision counts as
   in-tolerance.

4. oot_impact_verdict(affected_period): the number of product items
   released during the affected period (from the last good calibration
   to detection of the drift). Any released item -> 'recall' (contain
   and assess suspect product); zero -> 'review' (records only, no
   shipped product affected).
"""

MIN_TAR = 4.0


def _validate_number(value, name, positive=False, non_negative=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (name, value))
    if positive and value <= 0:
        raise ValueError("%s must be positive, got %r" % (name, value))
    if non_negative and value < 0:
        raise ValueError("%s must be non-negative, got %r" % (name, value))


def _validate_int(value, name, non_negative=False):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer, got %r" % (name, value))
    if non_negative and value < 0:
        raise ValueError("%s must be non-negative, got %r" % (name, value))


def tar_verdict(standard_accuracy, unit_accuracy):
    """Verdict on the test accuracy ratio between standard and unit.

    TAR = standard_accuracy / unit_accuracy. Both accuracies must be
    positive numbers in the same unit or the same fraction convention.
    Returns 'ok' when TAR >= 4.0 (4:1 guidance), 'insufficient'
    otherwise. The ratio is unitless because both inputs share units.
    """
    _validate_number(standard_accuracy, "standard_accuracy", positive=True)
    _validate_number(unit_accuracy, "unit_accuracy", positive=True)
    ratio = standard_accuracy / unit_accuracy
    return "ok" if ratio >= MIN_TAR else "insufficient"


def calibration_due_verdict(days_until_due):
    """Verdict on a calibration due date from days until it is due.

    days_until_due is an integer: 0 or positive means the instrument is
    still within its calibration interval ('ok'); negative means the
    due date has passed ('overdue').
    """
    _validate_int(days_until_due, "days_until_due")
    return "ok" if days_until_due >= 0 else "overdue"


def tolerance_check(measured, nominal, tolerance):
    """Check a measured value against nominal plus tolerance.

    Returns 'in-tolerance' when |measured - nominal| <= tolerance,
    'out' otherwise. measured, nominal, and tolerance share the same
    unit; tolerance must be non-negative.
    """
    _validate_number(measured, "measured")
    _validate_number(nominal, "nominal")
    _validate_number(tolerance, "tolerance", non_negative=True)
    deviation = abs(measured - nominal)
    # Relative epsilon: absorbs float rounding so an exact-boundary
    # deviation (e.g. 10.005 - 10.0 = 0.005000000000000284) is not
    # misjudged as out of tolerance.
    eps = 1e-12 * max(1.0, abs(measured), abs(nominal))
    return "in-tolerance" if deviation <= tolerance + eps else "out"


def oot_impact_verdict(affected_period):
    """Verdict on out-of-tolerance impact from the affected period.

    affected_period is the integer count of product items released
    during the period from the last good calibration to detection of
    the drift. Any released item ('> 0') -> 'recall' (contain and
    assess suspect product); zero -> 'review' (no shipped product
    affected, records review only).
    """
    _validate_int(affected_period, "affected_period", non_negative=True)
    return "recall" if affected_period > 0 else "review"
