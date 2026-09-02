---
name: layup-cure
description: "Use when you must engineer a composite laminate layup and cure process: build the ply book with orientation, material, and thickness per ply, verify the laminate is symmetric and balanced, design the cure cycle (vacuum application, heat ramp, cure dwell, cool-down, autoclave vs out-of-autoclave vs press pressure), predict degree of cure with an Arrhenius kinetics model integrated over the temperature profile, relate glass transition temperature to degree of cure, and disposition C-scan porosity against the acceptance limit. Produces the ply book, symmetry and balance verdicts, the cure cycle timeline with pressures, the predicted degree of cure, Tg, and the C-scan acceptance verdict. Trigger: composite layup, ply book, laminate, symmetric, balanced, cure cycle, autoclave, out-of-autoclave, OOA, degree of cure, epoxy, 350F, glass transition, Tg, C-scan, porosity."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: cmh-17
    reference-only: true
gated: false
domain: manufacturing-quality
pack: composites
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: manufacturing-quality
  subdomain: composites
  tags: [cure-cycle, degree-of-cure, arrhenius, kinetics, ply-book, autoclave, out-of-autoclave, glass-transition, c-scan, porosity, epoxy]
  version: 0.1.0
  author: Aero Agent Skills
---

# Composite Laminate Layup and Cure (manufacturing-quality/composites/layup-cure)

Use when the task is composite laminate layup and cure process
engineering: defining the ply book, proving the laminate is symmetric
and balanced, designing the autoclave, out-of-autoclave (OOA), or
press cure cycle, predicting degree of cure from the temperature
history, relating glass transition temperature to cure state, and
dispositioning C-scan porosity results.

## Domain quick reference

- Ply book: an ordered list of plies from tool side to bag side. Each
  ply carries an orientation in degrees (0, 45, -45, 90 are the
  standard aerospace set), a material, and a cured ply thickness.
  Typical carbon-epoxy prepreg cures to about 0.19 mm (0.0075 in) per
  ply; laminate thickness is the sum. Build it with ply_book().
- Symmetric laminate: the sequence mirrors around the midplane, index
  i equals index n-1-i for every ply. Mirroring does NOT flip the
  orientation sign, so a +45 at position i mirrors to a +45 at
  position n-1-i. Symmetry zeroes the bending-stretching coupling
  terms, so a symmetric laminate does not warp or twist out of the
  tool when it cures and cools. Check with symmetric_check().
- Balanced laminate: for every nonzero angle, the count of +theta
  plies equals the count of -theta plies. Zero and 90 degree plies are
  self-balancing (90 and -90 are the same in-plane direction).
  Balance zeroes the shear-extension coupling, so the laminate does
  not twist under in-plane load. An odd ply count is allowed, the
  center ply sits on the midplane. Check with balanced_check().
- Cure cycle: (1) vacuum-stabilize at start temperature, the bag leak
  check and debulk hold; (2) heat ramp at a controlled rate to the
  cure temperature; (3) dwell at cure temperature for the resin cure;
  (4) cool-down to demold temperature, then vent vacuum and release
  pressure. Consolidation method: autoclave (vacuum bag plus applied
  gas pressure, typically 45-100 psi), out-of-autoclave (vacuum bag
  only, atmospheric pressure consolidation), or press (matched metal
  dies, hydraulic pressure, no vacuum bag). Design with
  cure_cycle_timeline().
- Degree of cure: the resin cures by an Arrhenius reaction,
  d(alpha)/dt = A * exp(-Ea/(R*T)) * (1-alpha)^n, with R = 8.314
  J/(mol*K), A in 1/min, Ea in J/mol, T in Kelvin. Integrate the rate
  over the piecewise-linear temperature profile with small time steps
  (0.5 min works for 2 F/min ramps). Representative 350F-cure epoxy
  kinetics: A = 5.0e5 1/min, Ea = 60 kJ/mol, n = 1. For the standard
  cycle (2 F/min ramp, 350 F for 120 min) this model gives alpha ~
  0.9998, while the ramp alone reaches only ~0.70, so hold time drives
  final cure. Predict with degree_of_cure().
- Glass transition vs cure: Tg rises with degree of cure
  (DiBenedetto form): Tg = Tg0 + (Tg_inf - Tg0) * (lambda*alpha) /
  (1 - (1-lambda)*alpha). Example: Tg0 = -10 C, Tg_inf = 200 C,
  lambda = 0.4 gives Tg = 50 C at alpha 0.5 and Tg = 176 C at alpha
  0.95. Rule of thumb: cure so the part Tg exceeds the maximum service
  temperature by at least 25-30 C; undercure leaves Tg too low and the
  part creeps in service. Compute with glass_transition_tg().
- C-scan verification: through-transmission or pulse-echo ultrasonic
  attenuation mapping over the cured part. High attenuation zones
  correlate with porosity. Acceptance is typically 1% porosity by area
  for primary structure and up to 2% for secondary structure, per
  CMH-17 and the part specification. Common porosity causes: air
  trapped between plies (poor debulk, bridging), vacuum leaks or
  insufficient vacuum, moisture in prepreg or core outgassing, ramp
  too fast so volatiles trap before gel, low consolidation pressure,
  and resin-rich or resin-starved zones from uneven bleed. Disposition
  with c_scan_verdict().

## Workflow

1. Define the ply sequence from the design and build the ply book with
   ply_book(sequence, materials, thicknesses_mm). Confirm total cured
   thickness against the drawing tolerance.
2. Check the laminate with symmetric_check(sequence) and
   balanced_check(sequence). A symmetric and balanced quasi-isotropic
   layup such as [0,45,-45,90,90,-45,45,0] passes both; an asymmetric
   or unbalanced sequence must be corrected in the design before
   tooling.
3. Select the consolidation method: autoclave for thick or porosity-
   critical parts, out-of-autoclave for OOA-qualified materials and
   tooling with low capital cost, press for flat or low-curvature
   parts with tight thickness control.
4. Design the cure cycle with cure_cycle_timeline(): set ramp rate,
   cure temperature, dwell time, cool rate, vacuum, and pressure. A
   standard 350F epoxy cycle is 2 F/min ramp from 70 F, 120 min dwell
   at 350 F, 5 F/min cool to 140 F, with vacuum from the stabilize
   step through the cool.
5. Predict degree of cure with degree_of_cure(profile, A, Ea, n, dt)
   using the material kinetic constants. Confirm alpha >= 0.95 at the
   end of dwell; if not, lengthen the dwell or raise the cure
   temperature, never raise the ramp rate to compensate.
6. Compute Tg with glass_transition_tg(alpha) and confirm it exceeds
   the maximum service temperature plus 25-30 C.
7. After cure, run C-scan verification and disposition the porosity
   reading with c_scan_verdict(porosity_pct) against the acceptance
   limit. On FAIL, cite the porosity causes in the nonconformance
   record and route to repair assessment or reject.

## Worked example

Laminate [0,45,-45,90,90,-45,45,0], 8 plies of carbon-epoxy prepreg at
0.19 mm each, cured by the standard 350F autoclave cycle.

- ply_book([0,45,-45,90,90,-45,45,0], thicknesses_mm=[0.19]*8) gives
  8 plies, total thickness 1.52 mm.
- symmetric_check and balanced_check both return True: the sequence
  mirrors around the midplane and the 45/-45 counts match.
- cure_cycle_timeline() returns phases vacuum-stabilize (0-15 min at
  70 F), ramp (15-155 min, 70 to 350 F at 2 F/min), dwell (155-275 min
  at 350 F), cool (275-317 min, 350 to 140 F at 5 F/min), total 317
  min, autoclave at 85 psi with -28 inHg vacuum.
- degree_of_cure(profile, A=5.0e5, Ea=60000, n=1.0, dt=0.5) gives
  alpha = 0.9998, above the 0.95 acceptance. The same ramp with no
  dwell gives only 0.70, showing the hold is what completes the cure.
- glass_transition_tg(0.9998) is about 199 C, far above a 160 C
  maximum service temperature.
- c_scan_verdict(0.8) returns PASS at the 1% primary-structure limit;
  c_scan_verdict(1.6) returns FAIL with the porosity causes listed.

## Pitfalls

- Mirroring flips nothing: a symmetric laminate pairs +45 with +45
  across the midplane, not +45 with -45. Confusing this fails real
  laminates that should pass and passes designs that will warp.
- 90 and -90 are the same direction for balance purposes; a
  [0,90,90,0] laminate is balanced even though it has no negative
  angles.
- Balance is a ply-count property, symmetry is a position property; a
  laminate can be balanced but asymmetric (or the reverse), check both
  separately.
- Cure kinetics are strongly temperature sensitive: rate doubles
  roughly every 10 C near cure temperature, so a few degrees of oven
  error change final alpha noticeably. Thermocouple placement and oven
  survey matter as much as the cycle math.
- Shortening the ramp to save time does not compensate for a short
  dwell: the dwell sets final alpha, the ramp mostly sets peak
  exotherm risk.
- Releasing autoclave pressure or vacuum before the part is below
  about 150 F allows porosity to grow as trapped volatiles expand.
- C-scan attenuation is a screening measure, not a direct porosity
  meter; calibrate the gate on a known-porosity reference panel before
  accepting or rejecting production parts.

## Verification checklist

- Ply book: orientations valid (-90..90 degrees), material and
  thickness lists match ply count, total thickness within drawing
  tolerance.
- Symmetric check returns True and balanced check returns True before
  tooling is committed.
- Cure cycle: cure temperature above start temperature, positive ramp
  and cool rates, dwell long enough for alpha >= 0.95 with the real
  kinetic constants.
- Degree of cure: alpha in [0.95, 1.0] for the full cycle and below
  0.95 for the ramp alone (sanity that the model discriminates).
- Tg at predicted alpha exceeds maximum service temperature plus
  25-30 C.
- C-scan verdict matches the porosity reading against the correct
  acceptance limit for primary vs secondary structure.

## Behavior contract (gate 3)

The engineering logic is exercised by the contract test
scripts/test_layup_cure.py against scripts/layup_cure_logic.py
(stdlib unittest, offline, deterministic, 25 cases). Run:

python3 skills/manufacturing-quality/composites/layup-cure/scripts/test_layup_cure.py

Contract assertions include: the symmetric sequence
[0,45,-45,90,90,-45,45,0] passes symmetric_check() while an
asymmetric sequence fails; the standard 350F cycle (2 F/min ramp,
350 F hold 120 min) reaches degree of cure >= 0.95; invalid ply
orientation (99 deg) raises ValueError; balanced and unbalanced
laminates are categorized correctly; C-scan verdicts PASS and FAIL at
the right thresholds.

## Compliance

- Standards referenced, not reproduced: CMH-17 (Composite Materials
  Handbook) frames ply design, cure process control, and C-scan
  acceptance practice; the models here are simplified engineering
  summaries, reference-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
- Related skills: manufacturing-quality/ndt/ultrasonic-inspection for
  the C-scan measurement math, manufacturing-quality/special-processes/
  special-process-qualification for process qualification records.
