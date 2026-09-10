#!/usr/bin/env python3
"""ECSS-E-ST-10-04C §9.2.5 atmospheric albedo neutrons logic (paraphrase).

Pure stdlib, no network. Unit conventions: altitude in km, inclination
in degrees (0-180), neutron energy in eV. Orbit regimes are one of LEO,
MEO, GEO, GTO, HEO, L2, interplanetary. Unknown regimes, out-of-range
altitude/inclination, or negative energy raise ValueError.

This module is a deterministic paraphrase of ECSS-E-ST-10-04C clause
9.2.5 practice: atmospheric albedo neutrons are a secondary radiation
environment produced by cosmic-ray interaction with the atmosphere,
relevant only near Earth in LEO, with a spectrum spanning thermal to
high-energy bands and a flux that grows with the geomagnetic latitude
the orbit reaches.
"""

ORBIT_REGIMES = {"LEO", "MEO", "GEO", "GTO", "HEO", "L2", "INTERPLANETARY"}

LEO_MIN_ALTITUDE_KM = 0
LEO_MAX_ALTITUDE_KM = 2000

# (band name, lower bound eV inclusive, upper bound eV exclusive)
NEUTRON_ENERGY_BANDS = [
    ("thermal", 0.0, 0.5),
    ("epithermal", 0.5, 1.0e5),
    ("fast", 1.0e5, 2.0e7),
    ("high-energy", 2.0e7, float("inf")),
]

GEOMAGNETIC_EXPOSURE_CLASSES = {
    "equatorial-shielded": (0.0, 20.0),
    "mid-latitude": (20.0, 60.0),
    "polar-unshielded": (60.0, 180.0),
}

REQUIRED_RES_FIELDS = ("included", "regime", "energy_bands", "geomagnetic_exposure", "note")


def albedo_neutrons_applicable(regime, altitude_km=None):
    """Return whether the albedo neutron environment belongs in the RES.

    regime must be one of ORBIT_REGIMES (case-insensitive). For LEO,
    altitude_km is required and must fall within
    [LEO_MIN_ALTITUDE_KM, LEO_MAX_ALTITUDE_KM]; outside that band
    raises ValueError. For any other regime the environment does not
    apply and altitude_km is ignored. Returns a bool.
    """
    if not isinstance(regime, str):
        raise ValueError("regime must be a string, got %r" % (regime,))
    key = regime.strip().upper()
    if key not in ORBIT_REGIMES:
        raise ValueError(
            "unknown orbit regime %r; expected one of %s"
            % (regime, ", ".join(sorted(ORBIT_REGIMES)))
        )
    if key != "LEO":
        return False
    if altitude_km is None:
        raise ValueError("altitude_km is required when regime is LEO")
    if not isinstance(altitude_km, (int, float)) or isinstance(altitude_km, bool):
        raise ValueError("altitude_km must be numeric, got %r" % (altitude_km,))
    if not (LEO_MIN_ALTITUDE_KM <= altitude_km <= LEO_MAX_ALTITUDE_KM):
        raise ValueError(
            "altitude_km %r outside LEO range [%s, %s]"
            % (altitude_km, LEO_MIN_ALTITUDE_KM, LEO_MAX_ALTITUDE_KM)
        )
    return True


def neutron_energy_band(energy_ev):
    """Classify a neutron energy (eV) into its spectral band.

    Returns one of 'thermal', 'epithermal', 'fast', 'high-energy'.
    Negative energy raises ValueError.
    """
    if not isinstance(energy_ev, (int, float)) or isinstance(energy_ev, bool):
        raise ValueError("energy_ev must be numeric, got %r" % (energy_ev,))
    if energy_ev < 0:
        raise ValueError("energy_ev must be non-negative, got %r" % (energy_ev,))
    for name, lower, upper in NEUTRON_ENERGY_BANDS:
        if lower <= energy_ev < upper:
            return name
    raise ValueError("energy_ev %r did not match any band" % (energy_ev,))


def geomagnetic_exposure_class(inclination_deg):
    """Classify the geomagnetic-latitude exposure driving neutron flux.

    inclination_deg must be in [0, 180]. Returns one of
    'equatorial-shielded', 'mid-latitude', 'polar-unshielded'. Higher
    inclination reaches higher geomagnetic latitude, where the weaker
    cutoff-rigidity shield admits more of the primary cosmic-ray flux
    that generates albedo neutrons.
    """
    if not isinstance(inclination_deg, (int, float)) or isinstance(inclination_deg, bool):
        raise ValueError("inclination_deg must be numeric, got %r" % (inclination_deg,))
    if not (0.0 <= inclination_deg <= 180.0):
        raise ValueError("inclination_deg %r outside [0, 180]" % (inclination_deg,))
    for name, (lower, upper) in GEOMAGNETIC_EXPOSURE_CLASSES.items():
        if name == "polar-unshielded":
            if lower <= inclination_deg <= upper:
                return name
        elif lower <= inclination_deg < upper:
            return name
    raise ValueError("inclination_deg %r did not match any exposure class" % (inclination_deg,))


def build_res_entry(regime, altitude_km=None, inclination_deg=None, energies_ev=None):
    """Assemble the RES entry for the atmospheric albedo neutron environment.

    regime and altitude_km are passed to albedo_neutrons_applicable.
    When the environment applies, inclination_deg is required and
    energies_ev is an optional non-empty list of neutron energies (eV)
    of interest; each is categorized into its band. Returns a dict with
    'included', 'regime', 'energy_bands' (sorted unique band names,
    empty list when energies_ev is omitted), 'geomagnetic_exposure',
    and 'note'. When the environment does not apply, 'energy_bands' is
    an empty list and 'geomagnetic_exposure' is None.
    """
    included = albedo_neutrons_applicable(regime, altitude_km)
    key = regime.strip().upper()
    if not included:
        return {
            "included": False,
            "regime": key,
            "energy_bands": [],
            "geomagnetic_exposure": None,
            "note": "atmospheric albedo neutrons not applicable outside LEO",
        }
    if inclination_deg is None:
        raise ValueError("inclination_deg is required when the environment applies")
    exposure = geomagnetic_exposure_class(inclination_deg)
    bands = []
    if energies_ev is not None:
        if not isinstance(energies_ev, list) or not energies_ev:
            raise ValueError("energies_ev must be a non-empty list when provided")
        bands = sorted({neutron_energy_band(e) for e in energies_ev})
    return {
        "included": True,
        "regime": key,
        "energy_bands": bands,
        "geomagnetic_exposure": exposure,
        "note": "LEO atmospheric albedo neutrons at %s exposure" % exposure,
    }


def res_entry_is_complete(entry):
    """Return the list of missing required fields in a RES entry.

    entry must be a dict. An empty list means the entry carries every
    field REQUIRED_RES_FIELDS lists. When entry['included'] is True,
    'energy_bands' and 'geomagnetic_exposure' must additionally be
    non-empty/non-None. Malformed entries raise ValueError.
    """
    if not isinstance(entry, dict):
        raise ValueError("entry must be a dict, got %r" % (entry,))
    missing = [field for field in REQUIRED_RES_FIELDS if field not in entry]
    if missing:
        return missing
    if entry["included"]:
        if not entry["energy_bands"]:
            missing.append("energy_bands")
        if entry["geomagnetic_exposure"] is None:
            missing.append("geomagnetic_exposure")
    return missing


if __name__ == "__main__":
    import doctest

    doctest.testmod()
