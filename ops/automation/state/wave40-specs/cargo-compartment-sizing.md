# Wave-40 leaf spec: cargo-compartment-sizing (vehicle-design, sizing pack)

- Path: skills/vehicle-design/sizing/cargo-compartment-sizing/
- Pack: sizing. Closest siblings: fuselage-sizing (its quick reference ends
  at "Cargo volume check: required baggage volume V_req = passengers *
  0.12 m^3 per passenger (typical range 0.10 to 0.15 m^3 per passenger);
  the available underfloor cargo volume must meet or exceed it", a
  passenger-baggage VOLUME budget over the whole cabin, with cabin
  length/width/diameter relations; no ULD footprint, no cargo door, no
  container layout content), fire-protection-sizing (extinguishing agent
  for a protected zone: "fix the protected zone (Class C cargo compartment
  or powerplant fire zone), take zone free volume and agent concentration
  by volume"; it CONSUMES the compartment volume this leaf sizes and owns
  no compartment geometry), environmental-control-sizing, weight-estimation,
  structures-integration/fuselage-skin-stringer. Whole-tree greps at prep:
  "ULD", "unit-load", "cargo door", "cargo-door" = 0 owning hits in
  skills/vehicle-design; no leaf anywhere lays out standard unit load
  devices in a freight hold or sizes the cargo door opening around them.
  GENUINE VEHICLE gap (fresh probe).
- Standards id: far-25 (reference-only; sizing pack convention). Ledger Standard: far-25.
- Family: vehicle-design

## Claim

Size a freight cargo compartment and its cargo door around standard unit
load devices (ULDs): look up public ULD envelope dimensions from a module
catalog, check whether a ULD cross-section passes through a cargo door
(with the rotated orientation tried), pick the largest-volume ULD that fits
a door, lay out ULD positions in the compartment with a deterministic 2D
strip layout (ULD length along the compartment, width across, a documented
aisle/gap allowance for two-abreast rows), compute the required volume from
payload mass and density, and report the end-to-end adequacy verdict.
Produces the ULD count, the volume utilization, the unused length and
width, the door-opening width and height with clearance, and the volume
adequacy verdict that gate the freight hold layout. Does NOT do:
passenger cabin layout and passenger baggage VOLUME budgeting
(fuselage-sizing); extinguishing agent sizing for a Class C zone
(fire-protection-sizing, which consumes the volume produced here); the
compartment fire/smoke detection zone rules; ULD restraint and loading
system mechanics (latches, power drive units); structural sizing of the
fuselage shell around the door cutout (fuselage-skin-stringer).

## Model (implement exactly)

Conventions: all dimensions in meters. A ULD is tabulated as (length_along,
width_across, height), length along the fuselage axis and width across the
hold; the catalog is standard public ULD data (IATA container/pallet
envelope dimensions, 1 in = 0.0254 m exactly), paraphrased, with the
orientation as tabulated, and pallets carry the nominal 64 in net build
height used for volume accounting. Container volume is the envelope product
of the tabulated dims; the corner cutouts of contoured containers mean the
net usable volume sits below the envelope (disclosed approximation, no
correction constant).

Module constants: ULD_CATALOG dict id -> (length_along, width_across,
height) in m: "LD1" (2.3368, 1.5342, 1.6256), "LD11" (1.5342, 3.1750,
1.6256), "LD3-46" (1.5621, 1.5342, 1.6256), "LD6" (1.5621, 3.1750, 1.6256),
"LD9" (2.2352, 3.1750, 1.6256), "PMC-88x125" (3.1750, 2.2352, 1.6256),
"P6P-96x125" (3.1750, 2.4384, 1.6256); AISLE_ALLOWANCE_M = 0.10;
DOOR_SIDE_MARGIN_M = 0.05; DOOR_TOP_MARGIN_M = 0.05.

Functions (pure stdlib):
- uld_fits_door(uld_width, uld_height, door_width, door_height) -> bool:
  True when the cross-section fits in the opening, also with the rotated
  cross-section (width and height swapped).
- max_uld_for_door(door_width, door_height, catalog=None) -> (uld_id,
  volume_m3) or None: the catalog entry with the largest envelope volume
  whose cross-section fits the door, sorted by catalog key for
  determinism.
- compartment_uld_layout(compartment_length, compartment_width,
  usable_height, uld_id, aisle_allowance=AISLE_ALLOWANCE_M) -> dict with
  keys uld_id, positions, rows (ULD rows across the width), per_row (ULD
  count along the length), utilized_volume_m3, compartment_volume_m3,
  volume_utilization, unused_length_m, unused_width_m. Layout: n_along =
  floor(length / uld_len); n_across = floor(width / (uld_width +
  aisle_allowance)), floored to 1 when the width alone admits one row;
  positions = n_along * n_across. ValueErrors: non-positive compartment
  dimensions, unknown uld_id, ULD height above the usable height.
- cargo_volume_required(payload_mass_kg, payload_density_kg_m3) -> float
  mass / density; ValueError if density <= 0 or mass < 0.
- door_opening_geometry(uld_id, sill_height_from_center_m,
  fuselage_radius_m, side_margin=DOOR_SIDE_MARGIN_M,
  top_margin=DOOR_TOP_MARGIN_M) -> dict with keys required_door_width_m
  (uld_width + 2 * side_margin), required_door_height_m (uld_height +
  top_margin), top_corner_radius_m and bottom_corner_radius_m (radii of the
  opening corners from the fuselage centerline axis at the given sill
  height), within_fuselage (bool: both corner radii within the fuselage
  radius). The sill height is measured from the fuselage centerline axis
  (negative for lower-lobe doors). ValueError if uld_id unknown or radius
  <= 0.
- layout_summary(payload_mass, density, compartment_length, width, height,
  door_width, door_height, uld_id) -> dict with keys payload_mass_kg,
  payload_density_kg_m3, required_volume_m3, uld_id, positions,
  needed_ulds (ceil of required volume / per-ULD envelope volume),
  volume_adequate (bool: utilized volume >= required volume),
  utilized_volume_m3, volume_utilization, shortfall_volume_m3,
  door_fits (bool).
Module constants as above; no other magic numbers.

Identities to test: doubling the compartment length doubles per_row and
positions at fixed width; a ULD that fits a door in one orientation also
passes the swapped check when the opening is large enough; the required
volume halves when the payload density doubles.

## Worked example

Narrowbody lower-lobe freight hold: usable length 12.0 m, width 2.2 m,
usable height 1.70 m; payload 4000 kg at 120 kg/m3; door 1.80 m wide x
1.68 m high. Real module outputs (anchor script run at prep):

- LD3-46 volume 3.895769 m3; LD1 5.827817 m3; LD9 11.536493 m3.
- compartment_uld_layout(12.0, 2.2, 1.70, "LD3-46"): positions 7
  (rows 1, per_row 7); utilized_volume_m3 27.270382; compartment_volume_m3
  44.880000; volume_utilization 0.607629; unused_length_m 1.065300;
  unused_width_m 0.665840.
- cargo_volume_required(4000, 120) = 33.333333 m3; needed_ulds = 9.
- Door checks at 1.80 x 1.68: LD3-46 fits True, LD6 fits False;
  max_uld_for_door returns ("LD1", 5.827817) (LD1 is the largest catalog
  ULD whose cross-section passes the opening).
- door_opening_geometry("LD3-46", -0.75, 1.975): required_door_width_m
  1.634160; required_door_height_m 1.675600; top_corner_radius_m 1.234648;
  bottom_corner_radius_m 1.109108; within_fuselage True.
- layout_summary verdict: volume_adequate False; utilized 27.270382 m3
  vs 33.333333 m3 required; shortfall_volume_m3 6.062952; door_fits True;
  the 4000 kg at 120 kg/m3 payload needs 9 LD3-46 containers against 7
  positions, so the hold must lengthen or take a denser load.
Run your module and take the real outputs as assert targets; the anchors
above are prep-verified bounds (reproduced at prep with stdlib math).

## Validation list (contract test must include)

- compartment_uld_layout worked example: positions 7, per_row 7, rows 1,
  volume_utilization 0.607629 within 1e-5, unused_length 1.065300 within
  1e-4, unused_width 0.665840 within 1e-4.
- cargo_volume_required(4000, 120) = 33.333333 within 1e-5.
- uld_fits_door: LD3-46 in the 1.80 x 1.68 door True (both orientations);
  LD6 False; P6P-96x125 False.
- max_uld_for_door(1.80, 1.68) returns ("LD1", 5.827817 within 1e-4).
- door_opening_geometry anchors above within 1e-4; within_fuselage True at
  sill -0.75 m and radius 1.975 m.
- layout_summary: volume_adequate False, shortfall 6.062952 within 1e-4,
  needed_ulds 9, door_fits True.
- ValueErrors: density 0 or negative, negative mass, non-positive
  compartment dims, unknown uld_id, ULD taller than the usable height,
  door geometry with unknown id or non-positive radius.
- Determinism; layout dict keys exactly as documented.

## Corpus fragment (eval/hit1-wave40-cargo-compartment-sizing.yaml)

Query 1 (copy verbatim):
  "size the cargo-compartment-sizing uld-layout for the ld3-46 containers in the lower-lobe freight hold and check the required cargo volume against the payload density"
  intent: "vehicle-design; freight compartment ULD layout and volume check"
  expected_skill: "vehicle-design/sizing/cargo-compartment-sizing"
Query 2 (copy verbatim):
  "verify the cargo-door-opening clearance and pick the largest unit-load-device that fits the door of the freight compartment"
  intent: "vehicle-design; cargo door opening geometry against standard ULDs"
  expected_skill: "vehicle-design/sizing/cargo-compartment-sizing"
Task ids: w40-cargo-compartment-sizing-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must size a freight cargo compartment
and its cargo door around standard unit load devices:" and include the
outputs in the Claim. First tag: cargo-compartment-sizing. Additional tags
ONLY: cargo-door-opening, uld-layout, unit-load-device-fit,
uld-position-layout, freight-hold-utilization. NEVER single generic words
(cargo, freight, door, container, pallet, volume, payload, compartment,
layout). 50-150 words, <=1000 chars, no em dash, no "classified", action
verb present.

FORBIDDEN TOKENS (belong to siblings): seats-abreast, seat-pitch,
cabin-length, baggage-volume, cargo-volume per passenger (fuselage-sizing);
extinguishing-agent, total-flooding, class-c, discharge-nozzle
(fire-protection-sizing); hoop-stress, skin-thickness, stringer-spacing
(fuselage-skin-stringer).
