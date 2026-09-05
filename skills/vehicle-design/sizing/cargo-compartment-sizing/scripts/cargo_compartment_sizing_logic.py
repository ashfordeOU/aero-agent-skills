"""Cargo compartment sizing logic for the cargo-compartment-sizing skill.

Pure Python stdlib. Sizes a freight cargo compartment and its cargo door
around standard unit load devices (ULDs): public ULD envelope dimensions
from a module catalog, ULD cross-section fit through a cargo door (rotated
orientation tried), the largest-volume ULD that fits a door, a deterministic
2D strip layout of ULD positions in the compartment, the required cargo
volume from payload mass and density, and the end-to-end adequacy verdict.

Catalog convention: dimensions in meters. A ULD is tabulated as
(length_along, width_across, height), length along the fuselage axis and
width across the hold. The catalog paraphrases standard public ULD envelope
data with 1 in = 0.0254 m exactly, so the 60.4 in wide units carry width
1.53416 m; container volume is the envelope product of the tabulated dims,
and the corner cutouts of contoured containers mean the net usable volume
sits below the envelope (disclosed approximation, no correction constant).
"""

import math

# Public ULD envelope catalog, id -> (length_along_m, width_across_m,
# height_m). Derived from standard IATA container and pallet envelope
# dimensions at exactly 0.0254 m per inch; pallets carry the nominal 64 in
# net build height used for volume accounting.
ULD_CATALOG = {
    "LD1": (2.3368, 1.53416, 1.6256),      # 92 x 60.4 x 64 in
    "LD11": (1.53416, 3.1750, 1.6256),     # 60.4 x 125 x 64 in
    "LD3-46": (1.5621, 1.53416, 1.6256),   # 61.5 x 60.4 x 64 in
    "LD6": (1.5621, 3.1750, 1.6256),       # 61.5 x 125 x 64 in
    "LD9": (2.2352, 3.1750, 1.6256),       # 88 x 125 x 64 in
    "PMC-88x125": (3.1750, 2.2352, 1.6256),  # 125 x 88 in pallet, 64 in build
    "P6P-96x125": (3.1750, 2.4384, 1.6256),  # 125 x 96 in pallet, 64 in build
}

AISLE_ALLOWANCE_M = 0.10
DOOR_SIDE_MARGIN_M = 0.05
DOOR_TOP_MARGIN_M = 0.05


def _uld_dims(uld_id, catalog=None):
    """Look up (length_along, width_across, height) for a ULD id.

    Raises ValueError for an id that is absent from the catalog.
    """
    table = ULD_CATALOG if catalog is None else catalog
    if uld_id not in table:
        raise ValueError("unknown uld_id: %r" % (uld_id,))
    return table[uld_id]


def uld_fits_door(uld_width, uld_height, door_width, door_height):
    """Return True when the ULD cross-section fits the door opening.

    The cross-section is tried as tabulated and with the width and height
    swapped, i.e. the rotated orientation. Returns False when neither
    orientation passes through the opening.
    """
    straight = uld_width <= door_width and uld_height <= door_height
    rotated = uld_height <= door_width and uld_width <= door_height
    return straight or rotated


def max_uld_for_door(door_width, door_height, catalog=None):
    """Return (uld_id, envelope_volume_m3) of the largest ULD that fits.

    Considers every catalog entry whose cross-section passes the door
    opening, with the rotated orientation tried, and keeps the entry with
    the largest envelope volume. Candidates are visited sorted by catalog
    key, so a volume tie deterministically resolves to the earliest key.
    Returns None when no catalog ULD fits the opening.
    """
    table = ULD_CATALOG if catalog is None else catalog
    best_id = None
    best_volume = None
    for uld_id in sorted(table):
        length_along, width_across, height = table[uld_id]
        if uld_fits_door(width_across, height, door_width, door_height):
            volume = length_along * width_across * height
            if best_volume is None or volume > best_volume:
                best_id = uld_id
                best_volume = volume
    if best_id is None:
        return None
    return best_id, best_volume


def compartment_uld_layout(compartment_length, compartment_width,
                           usable_height, uld_id,
                           aisle_allowance=AISLE_ALLOWANCE_M):
    """Lay out ULD positions in the compartment as a 2D strip layout.

    The ULD length runs along the compartment axis and the width across
    the hold; a documented aisle/gap allowance separates columns so that
    two-abreast rows keep a service gap. n_along is the floor of the
    length over the ULD length; n_across is the floor of the width over
    the ULD width plus the aisle allowance, floored to 1 when the width
    alone admits one row. Returns a dict with keys uld_id, positions,
    rows (ULD rows across the width), per_row (ULD count along the
    length), utilized_volume_m3, compartment_volume_m3,
    volume_utilization, unused_length_m, unused_width_m.
    """
    if compartment_length <= 0 or compartment_width <= 0 or usable_height <= 0:
        raise ValueError("compartment dimensions must be positive")
    length_along, width_across, height = _uld_dims(uld_id)
    if height > usable_height:
        raise ValueError("ULD height above the usable height")
    n_along = int(compartment_length // length_along)
    raw_across = int(compartment_width // (width_across + aisle_allowance))
    n_across = max(1, raw_across) if width_across <= compartment_width else raw_across
    positions = n_along * n_across
    uld_volume = length_along * width_across * height
    utilized_volume = positions * uld_volume
    compartment_volume = compartment_length * compartment_width * usable_height
    aisle_space = max(n_across - 1, 0) * aisle_allowance
    unused_width = compartment_width - n_across * width_across - aisle_space
    unused_length = compartment_length - n_along * length_along
    utilization = utilized_volume / compartment_volume
    return {
        "uld_id": uld_id,
        "positions": positions,
        "rows": n_across,
        "per_row": n_along,
        "utilized_volume_m3": utilized_volume,
        "compartment_volume_m3": compartment_volume,
        "volume_utilization": utilization,
        "unused_length_m": unused_length,
        "unused_width_m": unused_width,
    }


def cargo_volume_required(payload_mass_kg, payload_density_kg_m3):
    """Return the cargo volume required by a payload, mass over density.

    Raises ValueError when the density is not positive or the mass is
    negative.
    """
    if payload_density_kg_m3 <= 0:
        raise ValueError("payload density must be positive")
    if payload_mass_kg < 0:
        raise ValueError("payload mass must not be negative")
    return payload_mass_kg / payload_density_kg_m3


def door_opening_geometry(uld_id, sill_height_from_center_m,
                          fuselage_radius_m,
                          side_margin=DOOR_SIDE_MARGIN_M,
                          top_margin=DOOR_TOP_MARGIN_M):
    """Return the cargo door opening geometry for a ULD.

    The sill height is measured from the fuselage centerline axis
    (negative for lower-lobe doors). required_door_width_m is the ULD
    width plus twice the side margin; required_door_height_m is the ULD
    height plus the top margin. The top and bottom corner radii are the
    distances from the fuselage centerline axis to the corners of the
    opening rectangle centered on the axis at the given sill height;
    within_fuselage reports whether both corner radii fall inside the
    fuselage radius.
    """
    length_along, width_across, height = _uld_dims(uld_id)
    if fuselage_radius_m <= 0:
        raise ValueError("fuselage radius must be positive")
    required_width = width_across + 2 * side_margin
    required_height = height + top_margin
    half_width = required_width / 2.0
    top_corner_radius = math.hypot(half_width,
                                   sill_height_from_center_m + required_height)
    bottom_corner_radius = math.hypot(half_width, sill_height_from_center_m)
    within_fuselage = (top_corner_radius <= fuselage_radius_m and
                       bottom_corner_radius <= fuselage_radius_m)
    return {
        "required_door_width_m": required_width,
        "required_door_height_m": required_height,
        "top_corner_radius_m": top_corner_radius,
        "bottom_corner_radius_m": bottom_corner_radius,
        "within_fuselage": within_fuselage,
    }


def layout_summary(payload_mass, density, compartment_length,
                   compartment_width, usable_height, door_width,
                   door_height, uld_id):
    """Return the end-to-end adequacy verdict for a freight hold layout.

    Combines the required volume from the payload mass and density with
    the strip layout of the given ULD and the door fit check. Keys:
    payload_mass_kg, payload_density_kg_m3, required_volume_m3, uld_id,
    positions, needed_ulds (ceil of required volume over the per-ULD
    envelope volume), volume_adequate (utilized volume meets or exceeds
    the required volume), utilized_volume_m3, volume_utilization,
    shortfall_volume_m3 (required minus utilized, floored at zero) and
    door_fits.
    """
    required_volume = cargo_volume_required(payload_mass, density)
    layout = compartment_uld_layout(compartment_length, compartment_width,
                                    usable_height, uld_id)
    length_along, width_across, height = _uld_dims(uld_id)
    uld_volume = length_along * width_across * height
    needed_ulds = int(math.ceil(required_volume / uld_volume))
    utilized_volume = layout["utilized_volume_m3"]
    volume_adequate = utilized_volume >= required_volume
    shortfall = max(0.0, required_volume - utilized_volume)
    door_fits = uld_fits_door(width_across, height, door_width, door_height)
    return {
        "payload_mass_kg": payload_mass,
        "payload_density_kg_m3": density,
        "required_volume_m3": required_volume,
        "uld_id": uld_id,
        "positions": layout["positions"],
        "needed_ulds": needed_ulds,
        "volume_adequate": volume_adequate,
        "utilized_volume_m3": utilized_volume,
        "volume_utilization": layout["volume_utilization"],
        "shortfall_volume_m3": shortfall,
        "door_fits": door_fits,
    }
