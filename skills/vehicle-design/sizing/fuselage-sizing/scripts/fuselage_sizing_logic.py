#!/usr/bin/env python3
"""Fuselage sizing logic for a transport aeroplane (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, far-25/cs-25: gated
false): conceptual fuselage sizing starts from the payload. The
cabin length is the row count times the seat pitch, L_cabin = rows
* pitch. The cabin width is the seats-abreast layout plus the
aisle, W_cabin = seats_abreast * seat_width + aisle_width. The
fuselage diameter adds a sidewall allowance to the cabin width,
D = W_cabin + sidewall_allowance (typical total 0.15-0.25 m for
trim, insulation, and structure; default 0.18 m). A sanity band on
the overall fuselage length to diameter ratio, L/D from 6 to 12, is
typical for transport jets. The cargo check compares the available
underfloor volume with the required baggage volume, about 0.12 m^3
per passenger (typical range 0.10-0.15 m^3 per passenger).

Units are SI throughout: lengths in m, volumes in m^3. Invalid
inputs raise ValueError throughout.
"""


def cabin_length(rows, pitch):
    """Cabin length (m) from the row count and the seat pitch (m).

    L_cabin = rows * pitch. Example: 30 rows at 0.81 m pitch give
    24.3 m.

    Raises ValueError if rows or pitch is not positive.
    """
    if rows <= 0:
        raise ValueError("rows must be positive, got %r" % (rows,))
    if pitch <= 0:
        raise ValueError("pitch must be positive, got %r" % (pitch,))
    return rows * pitch


def cabin_width(seats_abreast, seat_width, aisle_width):
    """Interior cabin width (m) from the cross-section layout.

    W_cabin = seats_abreast * seat_width + aisle_width. Example: 6
    abreast with 0.48 m seats and one 0.51 m aisle give 3.39 m.

    Raises ValueError if any input is not positive.
    """
    if seats_abreast < 1:
        raise ValueError("seats_abreast must be at least 1, got %r" % (seats_abreast,))
    if seat_width <= 0:
        raise ValueError("seat_width must be positive, got %r" % (seat_width,))
    if aisle_width <= 0:
        raise ValueError("aisle_width must be positive, got %r" % (aisle_width,))
    return seats_abreast * seat_width + aisle_width


def fuselage_diameter(seats_abreast, seat_width, aisle_width, sidewall_allowance=0.18):
    """Outer fuselage diameter (m) from the cross-section layout.

    D = seats_abreast * seat_width + aisle_width + sidewall_allowance,
    the cabin width plus a total allowance for trim, insulation, and
    structure on both sides (typical 0.15-0.25 m, default 0.18 m).
    Example: 6 abreast with 0.48 m seats and a 0.51 m aisle give a
    3.39 m cabin width and, with the default allowance, a 3.57 m
    diameter.

    Raises ValueError if the layout inputs are not positive or the
    sidewall allowance is negative.
    """
    if sidewall_allowance < 0:
        raise ValueError(
            "sidewall_allowance must be non-negative, got %r" % (sidewall_allowance,)
        )
    return cabin_width(seats_abreast, seat_width, aisle_width) + sidewall_allowance


def length_diameter_verdict(fuselage_length, diameter):
    """Verdict on the fuselage length to diameter ratio (dict).

    ratio = fuselage_length / diameter, both in m. The typical
    conceptual band for transport jets is 6 <= ratio <= 12, with
    boundaries inclusive. Returns {"ratio": float, "ok": bool,
    "verdict": str}; verdict strings name the band state (within,
    above, below).

    Raises ValueError if fuselage_length or diameter is not positive.
    """
    if fuselage_length <= 0:
        raise ValueError("fuselage_length must be positive, got %r" % (fuselage_length,))
    if diameter <= 0:
        raise ValueError("diameter must be positive, got %r" % (diameter,))
    ratio = fuselage_length / diameter
    if 6.0 <= ratio <= 12.0:
        return {"ratio": ratio, "ok": True, "verdict": "within typical band"}
    if ratio > 12.0:
        return {"ratio": ratio, "ok": False, "verdict": "above typical band (slender)"}
    return {"ratio": ratio, "ok": False, "verdict": "below typical band (stubby)"}


def required_baggage_volume(passengers, per_passenger=0.12):
    """Required baggage volume (m^3) for the passenger count.

    V_req = passengers * per_passenger, with a typical per-passenger
    baggage allowance of 0.10-0.15 m^3 (default 0.12 m^3). The
    available underfloor cargo volume must meet or exceed this.

    Raises ValueError if passengers or per_passenger is not positive.
    """
    if passengers <= 0:
        raise ValueError("passengers must be positive, got %r" % (passengers,))
    if per_passenger <= 0:
        raise ValueError("per_passenger must be positive, got %r" % (per_passenger,))
    return passengers * per_passenger


def cargo_volume_verdict(available_volume, required_volume):
    """Verdict on the cargo volume check (dict).

    Returns {"ok": bool, "verdict": str}: ok is True when the
    available underfloor volume is at least the required baggage
    volume; the verdict names the shortfall in m^3 when it is not.

    Raises ValueError if available_volume is negative or
    required_volume is not positive.
    """
    if available_volume < 0:
        raise ValueError(
            "available_volume must be non-negative, got %r" % (available_volume,)
        )
    if required_volume <= 0:
        raise ValueError("required_volume must be positive, got %r" % (required_volume,))
    if available_volume >= required_volume:
        return {"ok": True, "verdict": "cargo volume sufficient"}
    shortfall = required_volume - available_volume
    return {"ok": False, "verdict": "cargo volume short by %.2f m^3" % shortfall}
