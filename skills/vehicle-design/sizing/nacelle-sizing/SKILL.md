---
name: nacelle-sizing
description: "Size the engine nacelle geometry for a turbofan: derive the fan face area and diameter from the fan mass flow, density, Mach number and temperature; enlarge the fan face to the inlet highlight area with the lip area ratio; compute the free stream capture area and the A0/A1 capture area ratio at the flight Mach number; scale the nacelle length from the fan diameter with a length to diameter ratio; set the cowl maximum thickness from a thickness to chord ratio; estimate the cowl wetted area with a shape factor; and bookkeep the nacelle drag into friction, form and interference components. Use when the task is nacelle geometric sizing, inlet capture and highlight sizing, cowl thickness, wetted area, or nacelle drag bookkeeping for a high bypass turbofan. Trigger: nacelle sizing, inlet highlight, fan face area, capture area ratio, cowl thickness, wetted area, nacelle drag."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
  - id: cs-25
    reference-only: true
gated: false
domain: vehicle-design
pack: vehicle-design
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: vehicle-design
  subdomain: sizing
  tags: [nacelle-sizing, inlet-highlight-area, fan-face-area, lip-area-ratio, capture-area-ratio, nacelle-length, cowl-thickness-ratio, wetted-area, nacelle-drag, pylon-integration, high-bypass-turbofan]
  version: 0.1.0
  author: AeroSkills
---

# Nacelle Sizing (vehicle-design/sizing/nacelle-sizing)

Use when the task is engine nacelle geometric sizing: the fan or
compressor face area and diameter from the mass flow and Mach number,
the inlet highlight area and lip area ratio, the free stream capture
area and the A0/A1 ratio, the nacelle length to diameter ratio, the
cowl thickness ratio, the wetted area estimate, and the friction, form
and interference bookkeeping of nacelle drag including the pylon
integration term. This leaf sizes the nacelle as a geometric and drag
entity; the sibling engine-sizing leaf sizes the thrust itself, and
fuselage-sizing and wing-planform-sizing set the aircraft reference
dimensions that the nacelle drag coefficient is bookkept against.

## Domain quick reference

- Fan face area: A1 = mdot / (rho * V1) from mass flow continuity, with
  the fan face velocity V1 = M1 * a1 and the local speed of sound
  a1 = sqrt(gamma * R * T1). Air at gamma 1.4 and R 287.0 J/(kg*K) at
  288.15 K gives a speed of sound of about 340 m/s; a 0.6 fan face Mach
  gives V1 = 204 m/s.
- Fan face diameter: D1 = sqrt(4 * A1 / pi). A 3.18 m^2 fan face is a
  2.01 m diameter fan, the sizing reference of the whole nacelle.
- Fan face Mach band: 0.5 to 0.65 for a high bypass turbofan at the
  design point; a higher face Mach shrinks the required area for the
  same mass flow.
- Inlet highlight (lip) area: A_hi = A1 * (1 + lip_area_ratio), with
  the lip area ratio typically 0.10 to 0.20 for a high bypass turbofan.
  A zero ratio is a flush lip; negative ratios are invalid because the
  highlight cannot be smaller than the fan face.
- Capture area: A0 = mdot / (rho_inf * V_inf), the area of the free
  stream stream tube the inlet ingests at the flight condition. The
  capture area ratio A0/A1 expresses how strongly the inlet diffuses
  the flow: at a 0.8 Mach cruise a high bypass turbofan typically runs
  A0/A1 near 2.3, well above 1, and the ratio approaches 1 as the inlet
  is sized closer to the flight stream tube.
- Nacelle length: L = (L/D) * D1 with the length to diameter ratio
  typically 1.5 to 2.2 for a high bypass turbofan nacelle (1.8 is a
  representative first cut). The length scales linearly with the fan
  diameter at a fixed ratio.
- Cowl thickness: t = (t/c) * chord, with the cowl thickness to chord
  ratio typically 0.08 to 0.12; the cowl chord is close to the nacelle
  length for a first order estimate.
- Wetted area: S_wet = pi * D_max * L * k, the axisymmetric cowl
  surface approximated from the maximum diameter, the length and a
  shape factor k in (0, 1], typically 0.80 to 0.90 (1.0 is a plain
  cylinder). The maximum diameter is close to the highlight diameter.
- Nacelle drag bookkeeping: friction drag q * S_wet * Cf; form drag the
  friction times (FF - 1) with the form factor FF near 1.1 to 1.3; and
  interference drag the friction times k_int with k_int near 0.03 to
  0.10 covering pylon and installation interference. The three sum to
  the installed nacelle drag, and the drag coefficient against the
  aircraft reference area folds it into the aircraft drag polar.
- Pylon integration: the pylon is treated as an additional friction
  surface plus an interference increment on the nacelle; first order
  bookkeeping folds both into the interference factor, finer bookkeeping
  adds the pylon wetted area to S_wet.
- FAR-25 (14 CFR Part 25) and CS-25 set the certification context: the
  inlet and cowl must survive the icing, hail and bird strike
  conditions of the airworthiness rules, and the nacelle drag enters
  the performance substantiation; the geometric formulas above are
  common conceptual sizing practice, summary-only.

## Workflow

1. Set the fan face design point: mass flow mdot, density rho, Mach
   number M1 and temperature T1 at the fan face; compute the fan face
   area with fan_face_area and the diameter with fan_face_diameter.
2. Choose the lip area ratio and compute the highlight area with
   highlight_area_from_massflow and the highlight diameter with
   highlight_diameter_from_massflow; sanity check the choice with
   lip_area_ratio on the two areas.
3. At the cruise flight condition, compute the free stream capture
   area with capture_area and the A0/A1 ratio with capture_area_ratio
   against the fan face area; a ratio far above the typical band
   signals an oversized stream tube or an off-design point.
4. Scale the nacelle length with nacelle_length from the fan diameter
   and the length to diameter ratio; set the cowl maximum thickness
   with cowl_thickness from the cowl chord and the thickness to chord
   ratio.
5. Estimate the wetted area with wetted_area from the maximum
   diameter, the length and the shape factor.
6. At the cruise dynamic pressure and a turbulent skin friction
   coefficient, bookkeep the drag with nacelle_drag_bookkeeping into
   the friction, form and interference components and the total.
7. Fold the total into the aircraft drag with drag_coefficient against
   the aircraft reference area; add the pylon contribution through the
   interference factor or an explicit pylon wetted area.
8. Close the loop: the nacelle weight and drag feed the engine
   selection (engine-sizing) and the takeoff gross weight; re-run the
   sizing until the fan face Mach and the A0/A1 ratio both sit in their
   typical bands.

## Worked example

A high bypass turbofan with 650 kg/s fan mass flow, 1.0 kg/m^3 fan face
density, 0.6 fan face Mach and 288.15 K fan face temperature:

- Speed of sound a1 = sqrt(1.4 * 287 * 288.15) = 340.3 m/s; fan face
  velocity V1 = 0.6 * 340.3 = 204.2 m/s.
- Fan face area A1 = 650 / (1.0 * 204.2) = 3.18 m^2; fan face diameter
  D1 = sqrt(4 * 3.18 / pi) = 2.01 m.
- With a 0.15 lip area ratio, the highlight area is 3.18 * 1.15 =
  3.66 m^2 and the highlight diameter is 2.16 m.
- At a 0.8 Mach cruise at 10668 m (density 0.3804 kg/m^3, temperature
  218.81 K): V_inf = 0.8 * sqrt(1.4 * 287 * 218.81) = 237.2 m/s, so the
  capture area A0 = 650 / (0.3804 * 237.2) = 7.20 m^2 and A0/A1 = 2.26.
- Nacelle length at L/D 1.8: 1.8 * 2.01 = 3.62 m; cowl thickness at
  0.10 t/c: 0.10 * 3.62 = 0.36 m.
- Wetted area at shape factor 0.85: pi * 2.16 * 3.62 * 0.85 = 20.9 m^2.
- Cruise dynamic pressure q = 0.5 * 0.3804 * 237.2^2 = 10702 Pa; at a
  0.0025 skin friction coefficient the bookkeeping gives 559 N friction,
  112 N form drag (FF 1.2) and 28 N interference (k_int 0.05), 699 N
  total, which is a drag coefficient of about 0.00053 against a 122.6
  m^2 reference area.

All of these numbers are reproduced exactly by the contract test.

## Related leaves

- engine-sizing: turns the nacelle around its thrust, lapse, SFC and
  weight; this leaf sizes the nacelle geometry and drag for that
  engine.
- fuselage-sizing and wing-planform-sizing: provide the aircraft
  reference area and geometry that the nacelle drag coefficient and
  pylon integration are bookkept against.
- propeller-sizing: the propeller counterpart, where the spinner and
  cowl replace the fan face and inlet highlight sizing.

## Contract test

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_nacelle_sizing.py

The test covers the fan face area and diameter from mass flow and Mach,
the highlight area and lip area ratio round trip, the capture area and
A0/A1 ratio, nacelle length scaling including an extreme length to
diameter ratio, cowl thickness bands, wetted area with the shape factor
bounds, the drag bookkeeping components and their sum, the drag
coefficient, and invalid-input edge cases such as zero mass flow,
non-positive Mach, and out of range factors.

## Compliance

- Standards referenced, not reproduced: far-25 and cs-25 resolve in
  standards-map.yaml, both reference-only; the airworthiness context
  (inlet and cowl survivability, performance substantiation) is named
  and paraphrased, and the geometric formulas are common conceptual
  sizing practice.
- compliance: STANDARDS-REF, gated: false.
