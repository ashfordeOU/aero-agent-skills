"""
Single Event Effects (SEE) margin analysis logic.
Implements the margin-rule procedure of ECSS-E-ST-10C §5.5.3.
Offline, deterministic, stdlib only.
"""

from __future__ import annotations

# Recognised SEE event types and their hazard category.
# soft       : non-destructive, recoverable by reset or ECC.
# destructive: can cause permanent device damage if unprotected.
_EVENT_CATEGORY: dict[str, str] = {
    "SEU":  "soft",         # Single Event Upset
    "SET":  "soft",         # Single Event Transient
    "SEFI": "soft",         # Single Event Functional Interrupt
    "MBU":  "soft",         # Multiple Bit Upset
    "SEL":  "destructive",  # Single Event Latch-up
    "SEB":  "destructive",  # Single Event Burnout
    "SEGR": "destructive",  # Single Event Gate Rupture
}


class SEEMarginError(ValueError):
    """Raised when input values are outside the allowed range."""


def categorize_see_event(event_type: str) -> str:
    """Return the hazard category for a recognised SEE event type.

    Parameters
    ----------
    event_type : str
        A SEE event-type label (case-insensitive, e.g. 'SEU', 'sel').

    Returns
    -------
    str
        'soft' or 'destructive'.

    Raises
    ------
    SEEMarginError
        If the event type is not in the recognised set.
    """
    key = event_type.strip().upper()
    if key not in _EVENT_CATEGORY:
        recognised = ", ".join(sorted(_EVENT_CATEGORY))
        raise SEEMarginError(
            f"Unknown SEE event type: {event_type!r}. "
            f"Recognised types: {recognised}"
        )
    return _EVENT_CATEGORY[key]


def compute_see_margin(
    predicted_rate_per_day: float,
    mission_duration_days: float,
    margin_factor: float,
    allowable_events: float,
) -> dict:
    """Compute the margined SEE event count and pass/fail status.

    Parameters
    ----------
    predicted_rate_per_day : float
        Model-predicted event rate in events/device/day (must be >= 0).
    mission_duration_days : float
        Mission exposure duration in days (must be > 0).
    margin_factor : float
        Analysis margin applied to the predicted rate (must be >= 1.0).
    allowable_events : float
        Maximum number of events permitted over the full mission (must be > 0).

    Returns
    -------
    dict with keys:
        predicted_events  – predicted count without margin applied
        margined_events   – predicted count with margin factor applied
        margin_ratio      – allowable / margined_events (>= 1.0 means PASS)
        status            – 'PASS' or 'FAIL'
        finding           – human-readable summary string
    """
    if predicted_rate_per_day < 0:
        raise SEEMarginError("predicted_rate_per_day must be >= 0")
    if mission_duration_days <= 0:
        raise SEEMarginError("mission_duration_days must be > 0")
    if margin_factor < 1.0:
        raise SEEMarginError("margin_factor must be >= 1.0")
    if allowable_events <= 0:
        raise SEEMarginError("allowable_events must be > 0")

    predicted_events = predicted_rate_per_day * mission_duration_days
    margined_events = predicted_events * margin_factor

    if margined_events == 0.0:
        margin_ratio = float("inf")
        status = "PASS"
        finding = (
            "Predicted rate is zero; margined event count is zero. "
            "Margin requirement satisfied (record the physical basis for zero rate)."
        )
    else:
        margin_ratio = allowable_events / margined_events
        if margin_ratio >= 1.0:
            status = "PASS"
            finding = (
                f"Margined event count {margined_events:.4g} <= allowable "
                f"{allowable_events:.4g}. Margin ratio {margin_ratio:.3f} >= 1.0."
            )
        else:
            status = "FAIL"
            finding = (
                f"Margined event count {margined_events:.4g} exceeds allowable "
                f"{allowable_events:.4g}. Margin ratio {margin_ratio:.3f} < 1.0."
            )

    return {
        "predicted_events": predicted_events,
        "margined_events": margined_events,
        "margin_ratio": margin_ratio,
        "status": status,
        "finding": finding,
    }


def check_sel_protection(
    has_current_limiting: bool,
    has_power_cycling: bool,
) -> dict:
    """Verify that a device with a destructive SEE exposure has protective measures.

    A device exposed to SEL, SEB, or SEGR risk must have at least one of:
    - Hardware current-limiting: prevents destructive current flow during latch-up.
    - Power-cycling recovery: clears a latched state within the device's
      survival time limit.

    Parameters
    ----------
    has_current_limiting : bool
        True if hardware current-limiting protection is in place.
    has_power_cycling : bool
        True if a power-cycling recovery scheme is in place.

    Returns
    -------
    dict with keys:
        protected – True if at least one protection measure is present
        finding   – description of the protection status
    """
    if has_current_limiting or has_power_cycling:
        measures = []
        if has_current_limiting:
            measures.append("current-limiting")
        if has_power_cycling:
            measures.append("power-cycling recovery")
        return {
            "protected": True,
            "finding": (
                f"Destructive SEE protection confirmed: {', '.join(measures)} in place."
            ),
        }
    return {
        "protected": False,
        "finding": (
            "Destructive SEE protection MISSING: neither current-limiting nor "
            "power-cycling recovery is on record. Device cannot be used in this "
            "orbit without mitigation against destructive latch-up."
        ),
    }


def evaluate_device_see_compliance(
    device_name: str,
    event_type: str,
    predicted_rate_per_day: float,
    mission_duration_days: float,
    margin_factor: float,
    allowable_events: float,
    has_current_limiting: bool = False,
    has_power_cycling: bool = False,
) -> dict:
    """Full per-device SEE margin assessment per ECSS-E-ST-10C §5.5.3.

    Parameters
    ----------
    device_name : str
        Non-empty identifier for the device being assessed.
    event_type : str
        SEE event type label (e.g. 'SEU', 'SEL').
    predicted_rate_per_day : float
        Predicted event rate in events/device/day.
    mission_duration_days : float
        Mission exposure duration in days.
    margin_factor : float
        Analysis margin factor (>= 1.0).
    allowable_events : float
        Maximum allowable events over the mission.
    has_current_limiting : bool
        Hardware current-limiting protection present (relevant for destructive types).
    has_power_cycling : bool
        Power-cycling recovery capability present (relevant for destructive types).

    Returns
    -------
    dict with keys:
        device        – device_name as supplied
        event_type    – canonical event type (uppercased)
        category      – 'soft' or 'destructive'
        margin_result – output of compute_see_margin(...)
        protection    – output of check_sel_protection(...) for destructive types, else None
        compliant     – True only if margin is PASS and (soft OR protected)
        findings      – list of finding strings from margin and protection checks
    """
    if not device_name or not device_name.strip():
        raise SEEMarginError("device_name must not be empty")

    event_key = event_type.strip().upper()
    category = categorize_see_event(event_key)

    margin_result = compute_see_margin(
        predicted_rate_per_day,
        mission_duration_days,
        margin_factor,
        allowable_events,
    )

    findings: list[str] = [margin_result["finding"]]
    protection = None
    compliant = margin_result["status"] == "PASS"

    if category == "destructive":
        protection = check_sel_protection(has_current_limiting, has_power_cycling)
        findings.append(protection["finding"])
        if not protection["protected"]:
            compliant = False

    return {
        "device": device_name,
        "event_type": event_key,
        "category": category,
        "margin_result": margin_result,
        "protection": protection,
        "compliant": compliant,
        "findings": findings,
    }
