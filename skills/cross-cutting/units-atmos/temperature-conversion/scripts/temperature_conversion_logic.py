"""Temperature conversion logic (Kelvin, Celsius, Fahrenheit, Rankine).

Paraphrase of the standard temperature scale definitions. NACA
Report 824 is the pack's public-domain anchor (standards-map.yaml);
the four temperature scales are common engineering conventions, not
RTCA or SAE content.

Conventions: the Celsius scale sits 273.15 K above absolute zero, the
Fahrenheit degree is 5/9 of a Celsius degree with its zero at
-459.67 F, and the Rankine scale uses Fahrenheit-sized degrees with
its zero at absolute zero (0 R = 0 K). Absolute temperature
conversion keeps the physical temperature invariant across the
scales: celsius_to_kelvin adds 273.15, celsius_to_fahrenheit applies
the 9/5 ratio plus the 32 offset, and so on through the scale graph
that routes every scale through kelvin.

convert_temperature(value, from_unit, to_unit) accepts the unit
letters k, c, f, r (case-insensitive), converts the absolute
temperature, and raises ValueError for an unknown unit or for a value
below the absolute zero of its scale (0 K, 0 R, -273.15 C,
-459.67 F).

convert_delta(value, from_unit, to_unit) converts a temperature
difference, where only the degree sizes matter: one kelvin equals one
celsius degree, one rankine equals one fahrenheit degree, and one
kelvin equals 9/5 rankine. A difference is not an absolute
temperature, so no absolute-zero check applies. Raises ValueError for
an unknown unit.
"""


def celsius_to_kelvin(c):
    """Celsius to kelvin: add 273.15."""
    return c + 273.15


def kelvin_to_celsius(k):
    """Kelvin to celsius: subtract 273.15."""
    return k - 273.15


def celsius_to_fahrenheit(c):
    """Celsius to fahrenheit: 9/5 ratio plus 32."""
    return c * 9.0 / 5.0 + 32.0


def fahrenheit_to_celsius(f):
    """Fahrenheit to celsius: subtract 32, then 5/9 ratio."""
    return (f - 32.0) * 5.0 / 9.0


def kelvin_to_fahrenheit(k):
    """Kelvin to fahrenheit: route through celsius."""
    return celsius_to_fahrenheit(kelvin_to_celsius(k))


def fahrenheit_to_kelvin(f):
    """Fahrenheit to kelvin: route through celsius."""
    return celsius_to_kelvin(fahrenheit_to_celsius(f))


def kelvin_to_rankine(k):
    """Kelvin to rankine: 9/5 ratio from absolute zero."""
    return k * 9.0 / 5.0


def rankine_to_kelvin(r):
    """Rankine to kelvin: 5/9 ratio from absolute zero."""
    return r * 5.0 / 9.0


def celsius_to_rankine(c):
    """Celsius to rankine: route through kelvin."""
    return kelvin_to_rankine(celsius_to_kelvin(c))


def rankine_to_celsius(r):
    """Rankine to celsius: route through kelvin."""
    return kelvin_to_celsius(rankine_to_kelvin(r))


def fahrenheit_to_rankine(f):
    """Fahrenheit to rankine: add 459.67."""
    return f + 459.67


def rankine_to_fahrenheit(r):
    """Rankine to fahrenheit: subtract 459.67."""
    return r - 459.67


_ABSOLUTE_ZERO = {"k": 0.0, "r": 0.0, "c": -273.15, "f": -459.67}
_TO_KELVIN = {
    "k": lambda x: x,
    "c": celsius_to_kelvin,
    "f": fahrenheit_to_kelvin,
    "r": rankine_to_kelvin,
}
_FROM_KELVIN = {
    "k": lambda x: x,
    "c": kelvin_to_celsius,
    "f": kelvin_to_fahrenheit,
    "r": kelvin_to_rankine,
}
_DELTA_TO_KELVIN = {"k": 1.0, "c": 1.0, "f": 5.0 / 9.0, "r": 5.0 / 9.0}


def _normalize_unit(unit):
    u = str(unit).strip().lower()
    if u not in _ABSOLUTE_ZERO:
        raise ValueError("unknown temperature unit: %r (use k, c, f, or r)" % (unit,))
    return u


def convert_temperature(value, from_unit, to_unit):
    """Convert an absolute temperature between k, c, f, r.

    Raises ValueError for an unknown unit or a value below the
    absolute zero of its scale.
    """
    src = _normalize_unit(from_unit)
    dst = _normalize_unit(to_unit)
    if value < _ABSOLUTE_ZERO[src]:
        raise ValueError(
            "value %r is below absolute zero of unit %r (%r)"
            % (value, from_unit, _ABSOLUTE_ZERO[src])
        )
    return _FROM_KELVIN[dst](_TO_KELVIN[src](value))


def convert_delta(value, from_unit, to_unit):
    """Convert a temperature difference using degree sizes only.

    Raises ValueError for an unknown unit. No absolute-zero check
    applies because a difference is not an absolute temperature.
    """
    src = _normalize_unit(from_unit)
    dst = _normalize_unit(to_unit)
    return value * _DELTA_TO_KELVIN[src] / _DELTA_TO_KELVIN[dst]
