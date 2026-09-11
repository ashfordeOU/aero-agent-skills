"""
ECSS-E-ST-10-12C §6.3 radiation shielding geometry model — paraphrased logic.

Builds the three-tier shielding hierarchy (parts packaging, equipment,
spacecraft structure), computes the areal-density contribution of each layer
and tier, sums them into a total effective shielding value, inventories the
interfaces (connectors, feed-throughs, apertures, cutouts) that interrupt
shielding continuity, and reports deficiency / gap findings against
programme-level minimum thresholds.

The standard is cited as an anchor only; no verbatim ECSS text is reproduced.
Stdlib only, offline, deterministic.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

# ─── Tier identifiers ─────────────────────────────────────────────────────────
# Inner-to-outer shielding hierarchy of ECSS-E-ST-10-12C §6.3 (paraphrased).

TIER_PARTS_PACKAGING = "parts_packaging"
TIER_EQUIPMENT = "equipment"
TIER_SPACECRAFT = "spacecraft"

TIERS: Tuple[str, str, str] = (
    TIER_PARTS_PACKAGING,
    TIER_EQUIPMENT,
    TIER_SPACECRAFT,
)


class ShieldingError(ValueError):
    """Raised for invalid shielding geometry input or configuration."""


# ─── Data model ───────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ShieldLayer:
    """One material layer interposed between a sensitive part and space."""

    name: str
    material: str
    thickness_cm: float
    density_g_cm3: float
    tier: str

    def __post_init__(self) -> None:
        if not self.name:
            raise ShieldingError("layer name must not be empty")
        if not self.material:
            raise ShieldingError(f"layer '{self.name}': material must not be empty")
        if self.thickness_cm < 0:
            raise ShieldingError(
                f"layer '{self.name}': thickness_cm must be >= 0, "
                f"got {self.thickness_cm}"
            )
        if self.density_g_cm3 <= 0:
            raise ShieldingError(
                f"layer '{self.name}': density_g_cm3 must be > 0, "
                f"got {self.density_g_cm3}"
            )
        if self.tier not in TIERS:
            raise ShieldingError(
                f"layer '{self.name}': unknown tier '{self.tier}'; "
                f"expected one of {list(TIERS)}"
            )

    @property
    def areal_density_g_cm2(self) -> float:
        """Areal density (g/cm²) = thickness (cm) × bulk density (g/cm³)."""
        return self.thickness_cm * self.density_g_cm3


@dataclass(frozen=True)
class ShieldInterface:
    """A discontinuity (connector, feed-through, aperture, cutout) in a tier."""

    name: str
    tier: str
    effective_areal_density_g_cm2: float

    def __post_init__(self) -> None:
        if not self.name:
            raise ShieldingError("interface name must not be empty")
        if self.tier not in TIERS:
            raise ShieldingError(
                f"interface '{self.name}': unknown tier '{self.tier}'; "
                f"expected one of {list(TIERS)}"
            )
        if self.effective_areal_density_g_cm2 < 0:
            raise ShieldingError(
                f"interface '{self.name}': effective_areal_density_g_cm2 "
                f"must be >= 0, got {self.effective_areal_density_g_cm2}"
            )


# ─── Layer creation ───────────────────────────────────────────────────────────

def make_layer(
    name: str,
    material: str,
    thickness_cm: float,
    density_g_cm3: float,
    tier: str,
) -> ShieldLayer:
    """Construct and validate one shielding layer."""
    return ShieldLayer(name, material, thickness_cm, density_g_cm3, tier)


def layer_areal_density(layer: ShieldLayer) -> float:
    """Return the areal density (g/cm²) of a single validated layer."""
    if not isinstance(layer, ShieldLayer):
        raise ShieldingError("layer must be a ShieldLayer instance")
    return layer.areal_density_g_cm2


# ─── Areal-density summation ──────────────────────────────────────────────────

def _sum_layers(layers: Sequence[ShieldLayer]) -> float:
    total = 0.0
    for layer in layers:
        if not isinstance(layer, ShieldLayer):
            raise ShieldingError("all layers must be ShieldLayer instances")
        if layer.areal_density_g_cm2 < 0:  # defensive; __post_init__ forbids this
            raise ShieldingError(f"layer '{layer.name}' has negative areal density")
        total += layer.areal_density_g_cm2
    return total


def tier_areal_density(layers: Sequence[ShieldLayer], tier: str) -> float:
    """Summed areal density of every layer belonging to one tier."""
    if tier not in TIERS:
        raise ShieldingError(f"unknown tier '{tier}'; expected one of {list(TIERS)}")
    return _sum_layers([layer for layer in layers if layer.tier == tier])


def total_effective_shielding(layers: Sequence[ShieldLayer]) -> float:
    """Total effective shielding (g/cm²) summed across all three tiers."""
    if not layers:
        raise ShieldingError("layers must not be empty")
    return _sum_layers(layers)


# ─── Geometry-model assembly ──────────────────────────────────────────────────

def build_geometry_model(
    part_id: str,
    layers: Sequence[ShieldLayer],
    interfaces: Optional[Sequence[ShieldInterface]] = None,
) -> Dict[str, object]:
    """
    Assemble the shielding geometry model for one sensitive part.

    Returns a dict carrying the per-tier areal densities, the total effective
    shielding, the contributing layers and the inventoried interfaces.
    """
    if not part_id:
        raise ShieldingError("part_id must not be empty")
    if not layers:
        raise ShieldingError("at least one shielding layer is required")

    model: Dict[str, object] = {
        "part_id": part_id,
        "tiers": {tier: tier_areal_density(layers, tier) for tier in TIERS},
        "total_effective_shielding_g_cm2": total_effective_shielding(layers),
        "layers": list(layers),
        "interfaces": list(interfaces or []),
    }
    return model


# ─── Interface check ──────────────────────────────────────────────────────────

def check_interfaces(
    interfaces: Sequence[ShieldInterface],
    min_interface_g_cm2: float,
) -> List[Dict[str, object]]:
    """
    Flag every interface whose effective areal density falls below the
    programme-level minimum interface threshold as a shielding gap.
    """
    if min_interface_g_cm2 < 0:
        raise ShieldingError(
            f"min_interface_g_cm2 must be >= 0, got {min_interface_g_cm2}"
        )
    findings: List[Dict[str, object]] = []
    for iface in interfaces:
        if not isinstance(iface, ShieldInterface):
            raise ShieldingError("all interfaces must be ShieldInterface instances")
        if iface.effective_areal_density_g_cm2 < min_interface_g_cm2:
            findings.append(
                {
                    "interface": iface.name,
                    "tier": iface.tier,
                    "effective_areal_density_g_cm2": (
                        iface.effective_areal_density_g_cm2
                    ),
                    "required_g_cm2": min_interface_g_cm2,
                    "shortfall_g_cm2": (
                        min_interface_g_cm2 - iface.effective_areal_density_g_cm2
                    ),
                }
            )
    return findings


# ─── Evaluation ───────────────────────────────────────────────────────────────

def evaluate_shielding(
    model: Dict[str, object],
    min_total_g_cm2: float,
    min_interface_g_cm2: float,
) -> Dict[str, object]:
    """
    Compare a geometry model against the total-shielding and interface minima
    and return the deficiency and gap findings. Compliant only when both
    finding lists are empty.
    """
    errors = validate_geometry_model(model)
    if errors:
        raise ShieldingError("invalid geometry model: " + "; ".join(errors))
    if min_total_g_cm2 < 0:
        raise ShieldingError(f"min_total_g_cm2 must be >= 0, got {min_total_g_cm2}")
    if min_interface_g_cm2 < 0:
        raise ShieldingError(
            f"min_interface_g_cm2 must be >= 0, got {min_interface_g_cm2}"
        )

    total = float(model["total_effective_shielding_g_cm2"])
    deficiency: List[Dict[str, object]] = []
    if total < min_total_g_cm2:
        deficiency.append(
            {
                "part_id": model["part_id"],
                "total_effective_shielding_g_cm2": total,
                "required_g_cm2": min_total_g_cm2,
                "shortfall_g_cm2": min_total_g_cm2 - total,
            }
        )

    gap_findings = check_interfaces(model["interfaces"], min_interface_g_cm2)

    return {
        "part_id": model["part_id"],
        "total_effective_shielding_g_cm2": total,
        "min_total_g_cm2": min_total_g_cm2,
        "deficiency_findings": deficiency,
        "gap_findings": gap_findings,
        "compliant": not deficiency and not gap_findings,
    }


# ─── Validation ───────────────────────────────────────────────────────────────

def validate_geometry_model(model: Dict[str, object]) -> List[str]:
    """
    Validate the internal consistency of an assembled geometry model.

    Returns a list of human-readable error strings; an empty list means the
    model is well-formed. Raises ShieldingError if the argument is not a dict.
    """
    if not isinstance(model, dict):
        raise ShieldingError("geometry model must be a dict")

    errors: List[str] = []

    part_id = model.get("part_id")
    if not part_id or not isinstance(part_id, str):
        errors.append("part_id must be a non-empty string")

    tiers = model.get("tiers")
    if not isinstance(tiers, dict):
        errors.append("tiers must be a dict")
        tier_total = None
    else:
        missing = [t for t in TIERS if t not in tiers]
        if missing:
            errors.append(f"tiers missing: {sorted(missing)}")
        tier_total = 0.0
        for tier in TIERS:
            value = tiers.get(tier)
            if not isinstance(value, (int, float)):
                errors.append(f"tier '{tier}' value must be numeric")
                continue
            if value < 0:
                errors.append(f"tier '{tier}' must be >= 0, got {value}")
            tier_total += float(value)

    layers = model.get("layers")
    if not isinstance(layers, list) or not layers:
        errors.append("layers must be a non-empty list")
    elif not all(isinstance(layer, ShieldLayer) for layer in layers):
        errors.append("every layer must be a ShieldLayer instance")

    total = model.get("total_effective_shielding_g_cm2")
    if not isinstance(total, (int, float)):
        errors.append("total_effective_shielding_g_cm2 must be numeric")
    else:
        if total < 0:
            errors.append(
                f"total_effective_shielding_g_cm2 must be >= 0, got {total}"
            )
        if tier_total is not None and abs(float(total) - tier_total) > 1e-9:
            errors.append(
                "total_effective_shielding_g_cm2 does not equal the sum of the "
                f"tier contributions ({total} != {tier_total})"
            )

    interfaces = model.get("interfaces")
    if not isinstance(interfaces, list):
        errors.append("interfaces must be a list")
    elif not all(isinstance(i, ShieldInterface) for i in interfaces):
        errors.append("every interface must be a ShieldInterface instance")

    return errors
