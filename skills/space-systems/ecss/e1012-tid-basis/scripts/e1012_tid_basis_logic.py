"""
ECSS-E-ST-10-12C §7.1–7.4  TID assessment-basis logic.

Determines the ionising-dose environments active for a given orbit,
categorizes device technologies by TID sensitivity per Table 7-1,
and derives the minimum TID qualification test level.

Stdlib only — offline, deterministic.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Tuple

# ── Orbit types ────────────────────────────────────────────────────────────────

VALID_ORBIT_TYPES: frozenset = frozenset({"LEO", "MEO", "GEO", "HEO", "interplanetary"})

# ── Environment contributors per orbit (§7.2 analogue) ────────────────────────
# Each value is a list of (contributor_key, description) pairs.
# Derived from ECSS-E-ST-10-12C §7.2; no verbatim standard text.

_ENV_MAP: Dict[str, List[Tuple[str, str]]] = {
    "LEO": [
        ("trapped_protons",   "Inner-belt protons — dominant TID source below ~3000 km"),
        ("trapped_electrons", "Outer-belt electrons — significant above ~600 km altitude"),
        ("bremsstrahlung",    "Secondary X-rays produced by trapped electrons in shielding"),
        ("gcr",               "Galactic cosmic rays — low TID fraction, always present"),
    ],
    "MEO": [
        ("trapped_protons",   "Inner-belt protons — peak flux at ~3000–9000 km altitude"),
        ("trapped_electrons", "Outer-belt electrons — most intense dose regime"),
        ("bremsstrahlung",    "Secondary X-rays from electron belt — substantial contribution"),
        ("gcr",               "Galactic cosmic rays"),
        ("sep",               "Solar energetic protons — reduced magnetospheric shielding"),
    ],
    "GEO": [
        ("trapped_electrons", "Outer-belt electrons — primary TID contributor at GEO"),
        ("bremsstrahlung",    "Secondary X-rays from outer-belt electrons"),
        ("sep",               "Solar energetic protons — dominant proton source beyond inner belt"),
        ("gcr",               "Galactic cosmic rays"),
    ],
    "HEO": [
        ("trapped_protons",   "Inner-belt proton dose during perigee passes"),
        ("trapped_electrons", "Outer-belt electrons during belt crossings"),
        ("bremsstrahlung",    "Secondary X-rays from trapped electrons during crossings"),
        ("sep",               "Solar energetic protons at high-altitude apogee"),
        ("gcr",               "Galactic cosmic rays"),
    ],
    "interplanetary": [
        ("sep",               "Solar energetic protons — primary TID source beyond magnetosphere"),
        ("gcr",               "Galactic cosmic rays — dominant for long deep-space missions"),
    ],
}

# ── Technology sensitivity table (§7.3 / Table 7-1 analogue) ──────────────────
# Levels: "high" | "moderate" | "low"
# Note: programme-specific part data overrides these generic family entries.

_TECH_SENSITIVITY: Dict[str, Tuple[str, str]] = {
    "bipolar_linear":    ("high",     "Low dose-rate ELDRS degradation possible — low-rate test required"),
    "bipolar_digital":   ("moderate", "Less ELDRS-prone than linear, but bipolar oxide still accumulates"),
    "cmos_bulk":         ("moderate", "Threshold shift from oxide trapping; dose-rate-dependent recovery"),
    "cmos_soi":          ("moderate", "Buried-oxide charge trapping — both SEE and TID relevant"),
    "bicmos":            ("high",     "Bipolar subcircuits may exhibit ELDRS — treat as bipolar_linear"),
    "power_mosfet":      ("moderate", "Gate-oxide and field-oxide charge trapping"),
    "opto_coupler":      ("high",     "Current-transfer ratio degrades rapidly with accumulated dose"),
    "ccd_imager":        ("high",     "Dark current and charge-transfer efficiency both degrade with dose"),
    "solar_cell_si":     ("moderate", "TID to passivation oxide; primary damage is displacement damage"),
    "fpga_sram":         ("moderate", "SRAM configuration cells susceptible to threshold shifts"),
    "adc_bipolar":       ("high",     "Input differential bipolar pair — ELDRS concern"),
    "gaas_mesfet":       ("low",      "Semi-insulating GaAs substrate — relatively TID-tolerant"),
    "hemt_iii_v":        ("low",      "Wide-bandgap channel — low TID sensitivity below ~1 Mrad"),
    "quartz_oscillator": ("low",      "Frequency shift minor; TID not normally the life-limiting failure"),
    "resistor":          ("low",      "Metal-film and thick-film types are TID-insensitive at mission levels"),
    "mlcc_capacitor":    ("low",      "Ceramic dielectrics remain TID-insensitive at typical mission doses"),
}

VALID_TECHNOLOGIES: frozenset = frozenset(_TECH_SENSITIVITY.keys())
VALID_SENSITIVITY_LEVELS: frozenset = frozenset({"high", "moderate", "low"})

MIN_MARGIN_FACTOR: float = 2.0  # §7.4 minimum


# ── Data structures ────────────────────────────────────────────────────────────

@dataclass
class EnvironmentContributor:
    key: str
    description: str


@dataclass
class TechnologyEntry:
    technology: str
    sensitivity: str   # "high" | "moderate" | "low"
    note: str


@dataclass
class TIDBasisRecord:
    orbit_type: str
    mission_duration_years: float
    environments: List[EnvironmentContributor]
    technologies: List[TechnologyEntry]
    minimum_tid_test_krad_si: float
    margin_factor: float
    findings: List[str]
    complete: bool


# ── Public API ─────────────────────────────────────────────────────────────────

def get_tid_environments(orbit_type: str) -> List[EnvironmentContributor]:
    """Return TID-contributing environments for the given orbit type.

    Raises ValueError for unrecognised orbit types.
    """
    orbit = orbit_type.strip()
    if orbit not in VALID_ORBIT_TYPES:
        raise ValueError(
            f"Unrecognised orbit type '{orbit}'. "
            f"Accepted values: {sorted(VALID_ORBIT_TYPES)}"
        )
    return [
        EnvironmentContributor(key=k, description=d)
        for k, d in _ENV_MAP[orbit]
    ]


def get_technology_sensitivity(technology: str) -> TechnologyEntry:
    """Return the TID sensitivity entry for a device technology family.

    Raises ValueError for technologies not in the programme database.
    """
    tech = technology.strip().lower()
    if tech not in _TECH_SENSITIVITY:
        raise ValueError(
            f"Technology '{technology}' not in TID sensitivity database. "
            f"Accepted types: {sorted(VALID_TECHNOLOGIES)}"
        )
    sensitivity, note = _TECH_SENSITIVITY[tech]
    return TechnologyEntry(technology=tech, sensitivity=sensitivity, note=note)


def compute_minimum_tid_test_level(
    design_dose_krad_si: float,
    margin_factor: float,
) -> float:
    """Derive the minimum TID qualification test level in krad(Si).

    Per ECSS-E-ST-10-12C §7.4, the test level is margin_factor × design_dose.
    margin_factor must be >= MIN_MARGIN_FACTOR (2.0).

    Raises ValueError if design_dose_krad_si <= 0 or margin_factor < 2.0.
    """
    if design_dose_krad_si <= 0.0:
        raise ValueError(
            f"design_dose_krad_si must be positive, got {design_dose_krad_si}"
        )
    if margin_factor < MIN_MARGIN_FACTOR:
        raise ValueError(
            f"margin_factor {margin_factor} is below the §7.4 minimum of "
            f"{MIN_MARGIN_FACTOR}. A formal tailoring request is required to "
            "use a reduced margin."
        )
    return design_dose_krad_si * margin_factor


def establish_tid_basis(
    orbit_type: str,
    mission_duration_years: float,
    technologies: List[str],
    design_dose_krad_si: float,
    margin_factor: float = 2.0,
) -> TIDBasisRecord:
    """Establish the complete TID assessment basis for a mission.

    Combines environment identification (§7.2), technology sensitivity
    grouping (§7.3), and minimum test-level derivation (§7.4) into a
    single TIDBasisRecord.  Populates findings for unknown technologies,
    ELDRS obligations, and margin violations.

    Raises ValueError for invalid orbit type, non-positive mission duration,
    or non-positive design dose.
    """
    if mission_duration_years <= 0.0:
        raise ValueError(
            f"mission_duration_years must be positive, got {mission_duration_years}"
        )

    findings: List[str] = []

    # §7.2 — environments
    envs = get_tid_environments(orbit_type)  # propagates ValueError on bad orbit

    # §7.3 — technology sensitivity grouping
    tech_entries: List[TechnologyEntry] = []
    for t in technologies:
        try:
            entry = get_technology_sensitivity(t)
            tech_entries.append(entry)
        except ValueError:
            findings.append(
                f"Unknown technology '{t}' — resolve against programme "
                "device database before accepting the basis"
            )

    if not technologies:
        findings.append(
            "Technology list is empty — at least one device technology "
            "must be recorded before the basis is complete"
        )

    # Flag bipolar high-sensitivity technologies for ELDRS testing
    for entry in tech_entries:
        if entry.sensitivity == "high" and "bipolar" in entry.technology:
            findings.append(
                f"'{entry.technology}' is a high-sensitivity bipolar device — "
                "low dose-rate (ELDRS) testing required per §7.3"
            )

    # §7.4 — minimum test level
    try:
        min_test = compute_minimum_tid_test_level(design_dose_krad_si, margin_factor)
    except ValueError as exc:
        findings.append(str(exc))
        min_test = 0.0

    # Completeness: no unknown-technology or empty-list findings, positive test level
    blocking = [
        f for f in findings
        if "Unknown technology" in f or "empty" in f
    ]
    complete = len(blocking) == 0 and len(tech_entries) > 0 and min_test > 0.0

    return TIDBasisRecord(
        orbit_type=orbit_type,
        mission_duration_years=mission_duration_years,
        environments=envs,
        technologies=tech_entries,
        minimum_tid_test_krad_si=min_test,
        margin_factor=margin_factor,
        findings=findings,
        complete=complete,
    )
