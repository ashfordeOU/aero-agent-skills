---
name: cargo-compartment-sizing
description: "Use when you must size a freight cargo compartment and its cargo door around standard unit load devices: look up public ULD envelope dimensions from the module catalog, check whether a ULD cross-section passes through a cargo door with the rotated orientation tried, pick the largest-volume ULD that fits a door, lay out ULD positions with a deterministic 2D strip layout and aisle allowance, compute the required cargo volume from payload mass and density, and report the adequacy verdict. Produces the ULD count, the volume utilization, the unused length and width, the door opening width and height with clearance, and the volume adequacy verdict. Trigger: cargo door opening, unit load device, ULD layout, freight hold."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
gated: false
domain: vehicle-design
pack: sizing
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: vehicle-design
  subdomain: sizing
  tags: [cargo-compartment-sizing, cargo-door-opening, uld-layout, unit-load-device-fit, uld-position-layout, freight-hold-utilization]
  version: 0.1.0
  author: AeroSkills
---

# Cargo Compartment Sizing (vehicle-design/sizing/cargo-compartment-sizing)

Use when the task is sizing a freight cargo compartment and its cargo
door around standard unit load devices (ULDs) for a transport
aeroplane: the ULD envelope catalog lookup, the door cross-section fit
check with rotation, the largest ULD that fits a door, the 2D strip
layout of ULD positions in the hold, the required cargo volume from the
payload mass and density, and the end-to-end volume adequacy verdict.
This leaf implements the layout in pure Python, stdlib only. It pairs
with sizing/fuselage-sizing (passenger cabin layout and its underfloor
volume budget at the whole-cabin scale) and sizing/fire-protection-sizing
(which consumes the compartment volume sized here). It does not cover
passenger baggage budgeting, compartment detection-zone rules, ULD
restraint and loading system mechanics, or structural sizing of the
shell around the door cutout.

## Domain quick reference

- ULD catalog convention: a ULD is tabulated as (length_along,
  width_across, height) in meters, length along the fuselage axis and
  width across the hold. The catalog paraphrases standard public IATA
  container and pallet envelope data with 1 in = 0.0254 m exactly, so a
  60.4 in wide unit carries width 1.53416 m; pallets carry the nominal
  64 in net build height (1.6256 m) used for volume accounting.
- Container volume: the envelope product of the tabulated dimensions.
  The corner cutouts of contoured containers mean the net usable volume
  sits below the envelope product; this leaf discloses that
  approximation and applies no correction constant.
- Door fit: a ULD cross-section (width_across, height) fits an opening
  (W, H) when width_across <= W and height <= H, or with the rotated
  cross-section when height <= W and width_across <= H.
- Largest ULD for the door: the catalog entry with the largest envelope
  volume whose cross-section fits, visited sorted by catalog key so a
  volume tie resolves to the earliest key.
- Strip layout: n_along = floor(length / uld_length) ULDs in a row;
  n_across = floor(width / (uld_width + aisle_allowance)) rows across
  the hold, floored to 1 when the width alone admits one row; positions
  = n_along * n_across. The aisle allowance is 0.10 m and only separates
  two-abreast rows.
- Utilization: utilized_volume = positions * uld envelope volume over
  the compartment volume length * width * usable height. The unused
  length and width remain after the laid-out rows.
- Required cargo volume: V_req = payload_mass / payload_density.
- Door opening geometry: required width = uld_width + 2 * 0.05 m side
  margin, required height = uld_height + 0.05 m top margin. The corner
  radii are the distances from the fuselage centerline axis to the
  opening corners at the sill height (negative for lower-lobe doors);
  the opening is inside the fuselage when both corner radii are within
  the fuselage radius.
- Adequacy verdict: needed_ulds = ceil(V_req / per-ULD volume); the
  layout is volume-adequate when the utilized volume meets or exceeds
  the required volume.
- FAR-25 (14 CFR Part 25) frames the transport-category context for
  cargo compartment design; the geometric relations above are common
  conceptual sizing practice, summary-only.

## Workflow

1. Fix the hold envelope and payload: compartment length, width and
   usable height, and the payload mass and density.
2. Choose the candidate ULD from the module catalog (ULD_CATALOG in
   cargo_compartment_sizing_logic.py).
3. Check the ULD cross-section through the cargo door with
   uld_fits_door, with the rotated orientation tried.
4. Pick the largest ULD that fits the door with max_uld_for_door.
5. Lay out ULD positions in the compartment with
   compartment_uld_layout, the strip layout with the aisle allowance;
   rework the envelope if positions fall short.
6. Compute the required cargo volume with cargo_volume_required from
   the payload mass and density.
7. Size the cargo door opening with door_opening_geometry: side and top
   margins, and the corner radii checked within the fuselage.
8. Assemble the adequacy verdict with layout_summary and iterate:
   lengthen the hold or take a denser load until volume_adequate is
   True.

## Worked example

Narrowbody lower-lobe freight hold: usable length 12.0 m, width 2.2 m,
usable height 1.70 m; payload 4000 kg at 120 kg/m3; cargo door 1.80 m
wide x 1.68 m high. Module outputs:

- LD3-46 envelope volume 3.895769 m3, LD1 5.827817 m3, LD9 11.536493 m3.
- compartment_uld_layout(12.0, 2.2, 1.70, "LD3-46"): 7 positions in 1
  row of 7, utilized 27.270382 m3 against a 44.880000 m3 compartment,
  volume utilization 0.607629, unused length 1.065300 m, unused width
  0.665840 m.
- cargo_volume_required(4000, 120) = 33.333333 m3, so 9 LD3-46
  containers are needed (ceil).
- Door checks at 1.80 x 1.68: LD3-46 fits in both orientations, LD6 and
  P6P-96x125 do not; max_uld_for_door returns LD1 at 5.827817 m3 as the
  largest catalog ULD whose cross-section passes the opening.
- door_opening_geometry("LD3-46", sill -0.75 m, fuselage radius 1.975
  m): required door width 1.634160 m, height 1.675600 m, top corner
  radius 1.234648 m, bottom corner radius 1.109108 m, both within the
  fuselage.
- layout_summary verdict: volume_adequate False, utilized 27.270382 m3
  against 33.333333 m3 required, shortfall 6.062952 m3, needed_ulds 9,
  door_fits True. The payload needs 9 LD3-46 containers against 7
  positions, so the hold must lengthen or take a denser load.

## Verification

- Confirm compartment_uld_layout(12.0, 2.2, 1.70, "LD3-46") returns 7
  positions with volume utilization 0.607629, unused length 1.065300 m
  and unused width 0.665840 m.
- Confirm cargo_volume_required(4000, 120) = 33.333333 m3.
- Confirm LD3-46 passes the 1.80 x 1.68 m door in both orientations,
  LD6 and P6P-96x125 do not, and max_uld_for_door(1.80, 1.68) returns
  LD1 at 5.827817 m3.
- Confirm the door geometry anchors: width 1.634160 m, height 1.675600
  m, corner radii 1.234648 m and 1.109108 m, within the 1.975 m
  fuselage at a -0.75 m sill.
- Confirm the verdict: volume_adequate False with shortfall 6.062952
  m3, needed_ulds 9, door_fits True.
- Confirm the identities: doubling an exact-multiple compartment length
  doubles per_row and positions; a ULD that fits in one orientation
  also passes the swapped check on a large enough opening; doubling the
  payload density halves the required volume.
- Confirm ValueError rejection of non-physical inputs: non-positive
  compartment dimensions, an unknown uld_id, a ULD taller than the
  usable height, non-positive payload density, negative mass, and a
  non-positive fuselage radius.
- Run the contract test offline: python3
  scripts/test_cargo_compartment_sizing.py (30 tests, deterministic).

## Related leaves

- vehicle-design/sizing/fuselage-sizing: passenger cabin layout and the
  whole-cabin underfloor volume budget that bounds this hold.
- vehicle-design/sizing/fire-protection-sizing: consumes the
  compartment volume sized here when it fixes the protected zone and
  agent concentration.
- vehicle-design/sizing/weight-estimation: payload mass feeding the
  cargo volume requirement.
- vehicle-design/structures-integration/fuselage-skin-stringer:
  structural sizing of the fuselage shell around the door cutout.

## Pitfalls

- Sizing the door on the ULD height alone: the required door height
  adds the top margin and the width adds both side margins, so the
  opening exceeds the ULD cross-section.
- Forgetting the rotated orientation: a ULD that fails the straight
  cross-section check can still pass the door turned on its side, so
  both orientations must be tried before declaring a no-fit.
- Charging the aisle allowance to a single row: the 0.10 m aisle only
  separates two-abreast rows, so one row keeps the full unused width.
- Treating the envelope volume as usable volume: contoured container
  corner cutouts push the net usable volume below the envelope product,
  so the layout check is optimistic by a disclosed approximation.
- Comparing required volume against per-position volume: needed_ulds
  is the ceiling of the ratio, and positions must meet it before the
  hold is volume-adequate.
- Passing zero or negative inputs; the module raises ValueError instead
  of returning a nonsense dimension.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_cargo_compartment_sizing.py

The test covers the worked-example layout contract (7 positions, volume
utilization 0.607629, unused length and width anchors), the door
cross-section checks with both orientations, the largest-ULD-for-door
pick, the strip layout identities (doubling length doubles positions,
two-abreast rows with the aisle allowance), the required volume from
the payload, the door opening geometry anchors and corner-radius
hypotenuse relation, the adequacy verdict (volume_adequate, shortfall,
needed_ulds, door_fits) and ValueError rejection of every non-physical
input listed in Verification.

## Compliance

- Standards referenced, not reproduced: FAR-25 is US government work
  (public domain); the ULD catalog is paraphrased standard public
  envelope data and the layout relations are common conceptual sizing
  methodology, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
