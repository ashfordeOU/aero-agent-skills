"""
Mission Lifetime and Environment Specification logic.
ECSS-E-ST-32 clauses 4.2.1-4.2.2.

Implements: lifetime margin validation, environment-family categorization,
inventory completeness checking, and per-phase environment filtering.
stdlib only — no third-party dependencies.
"""

NATURAL_ENVIRONMENTS = frozenset([
    "thermal",
    "radiation",
    "debris",
    "micrometeoroid",
    "atomic_oxygen",
    "uv",
    "vacuum",
    "magnetic_field",
    "plasma",
    "gravity_gradient",
])

INDUCED_ENVIRONMENTS = frozenset([
    "acoustic",
    "vibration",
    "shock",
    "quasi_static",
    "pressure",
    "pyrotechnic",
    "thermal_induced",
])

MISSION_PHASES = frozenset(["launch", "transfer_orbit", "on_orbit", "disposal"])

# Minimum environment families that must appear in every complete inventory.
REQUIRED_ENVIRONMENT_FAMILIES = frozenset([
    "thermal",
    "radiation",
    "acoustic",
    "vibration",
    "shock",
])

# ECSS-E-ST-32 clause 4.2.1 minimum life factors.
MIN_QUALIFICATION_FACTOR = 1.5
MIN_ACCEPTANCE_FACTOR = 1.25


class EnvironmentEntry:
    """One environment family within the mission environment inventory."""

    def __init__(self, family: str, category: str, phases: list, quantified: bool):
        """
        family: environment family name, e.g. "thermal"
        category: "natural" or "induced"
        phases: list of mission phase strings from MISSION_PHASES
        quantified: True when a numeric level+duration spec exists for this family
        """
        if category not in ("natural", "induced"):
            raise ValueError(
                f"category must be 'natural' or 'induced', got {category!r}"
            )
        unknown = set(phases) - MISSION_PHASES
        if unknown:
            raise ValueError(f"unrecognized mission phases: {sorted(unknown)}")
        self.family = str(family)
        self.category = category
        self.phases = list(phases)
        self.quantified = bool(quantified)

    def __repr__(self) -> str:
        return (
            f"EnvironmentEntry(family={self.family!r}, category={self.category!r}, "
            f"phases={self.phases!r}, quantified={self.quantified})"
        )


class MissionLifetimeSpec:
    """
    Design lifetime declaration and environment inventory for a spacecraft
    structural programme (ECSS-E-ST-32 clauses 4.2.1-4.2.2).
    """

    def __init__(
        self,
        design_lifetime_years: float,
        qualification_factor: float = MIN_QUALIFICATION_FACTOR,
        acceptance_factor: float = MIN_ACCEPTANCE_FACTOR,
    ):
        """
        design_lifetime_years: required operational lifetime in years (> 0)
        qualification_factor: life factor for qualification testing (>= MIN_QUALIFICATION_FACTOR)
        acceptance_factor: life factor for acceptance testing (>= MIN_ACCEPTANCE_FACTOR)
        """
        if design_lifetime_years <= 0:
            raise ValueError("design_lifetime_years must be a positive number")
        if qualification_factor < 1.0:
            raise ValueError("qualification_factor must be >= 1.0")
        if acceptance_factor < 1.0:
            raise ValueError("acceptance_factor must be >= 1.0")
        self.design_lifetime_years = float(design_lifetime_years)
        self.qualification_factor = float(qualification_factor)
        self.acceptance_factor = float(acceptance_factor)
        self._inventory: list = []

    @property
    def qualification_lifetime_years(self) -> float:
        """Test duration required for qualification."""
        return self.design_lifetime_years * self.qualification_factor

    @property
    def acceptance_lifetime_years(self) -> float:
        """Test duration required for acceptance."""
        return self.design_lifetime_years * self.acceptance_factor

    def add_environment(self, entry: EnvironmentEntry) -> None:
        """Append an EnvironmentEntry to the inventory."""
        if not isinstance(entry, EnvironmentEntry):
            raise TypeError("entry must be an EnvironmentEntry instance")
        self._inventory.append(entry)

    def get_inventory(self) -> list:
        """Return a shallow copy of the environment inventory list."""
        return list(self._inventory)

    def categorize_by_type(self) -> dict:
        """Return {'natural': [...], 'induced': [...]} partitioning of the inventory."""
        return {
            "natural": [e for e in self._inventory if e.category == "natural"],
            "induced": [e for e in self._inventory if e.category == "induced"],
        }

    def families_by_phase(self, phase: str) -> list:
        """Return all EnvironmentEntry objects active in the given mission phase."""
        if phase not in MISSION_PHASES:
            raise ValueError(f"unrecognized phase {phase!r}")
        return [e for e in self._inventory if phase in e.phases]

    def unquantified_families(self) -> list:
        """Return EnvironmentEntry objects that have no quantified numeric spec."""
        return [e for e in self._inventory if not e.quantified]

    def check_completeness(self) -> list:
        """
        Verify required families are present and every family is quantified.
        Returns a list of finding strings; empty list means the inventory is complete.
        """
        findings = []
        present = {e.family for e in self._inventory}
        for family in sorted(REQUIRED_ENVIRONMENT_FAMILIES):
            if family not in present:
                findings.append(f"missing required environment family: {family}")
        for entry in self.unquantified_families():
            findings.append(f"environment family not quantified: {entry.family}")
        return findings


def validate_lifetime_margins(
    design_years: float,
    qualification_factor: float,
    acceptance_factor: float,
) -> list:
    """
    Check that lifetime factors meet ECSS-E-ST-32 clause 4.2.1 minimums.
    Returns a list of finding strings; empty list means all margins are compliant.
    """
    findings = []
    if design_years <= 0:
        findings.append("design lifetime must be a positive number of years")
    if qualification_factor < MIN_QUALIFICATION_FACTOR:
        findings.append(
            f"qualification factor {qualification_factor} is below the minimum "
            f"{MIN_QUALIFICATION_FACTOR} (ECSS-E-ST-32 clause 4.2.1)"
        )
    if acceptance_factor < MIN_ACCEPTANCE_FACTOR:
        findings.append(
            f"acceptance factor {acceptance_factor} is below the minimum "
            f"{MIN_ACCEPTANCE_FACTOR} (ECSS-E-ST-32 clause 4.2.1)"
        )
    return findings


def categorize_environment_family(family_name: str) -> str:
    """
    Return 'natural' or 'induced' for a recognised environment family name.
    Raises ValueError for an unrecognised family.
    Implements the two-category split of ECSS-E-ST-32 clause 4.2.2.
    """
    if family_name in NATURAL_ENVIRONMENTS:
        return "natural"
    if family_name in INDUCED_ENVIRONMENTS:
        return "induced"
    raise ValueError(
        f"unrecognized environment family: {family_name!r}. "
        f"Must be one of: {sorted(NATURAL_ENVIRONMENTS | INDUCED_ENVIRONMENTS)}"
    )
