---
name: e20-array-element-mutual-coupling
description: "Use when compute the element-to-element mutual-coupling of a spacecraft phased-array antenna under ECSS-E-ST-20C clause 7.2.2.2.3: build the pair coupling matrix from the lattice spacing in wavelengths and the E-plane, H-plane or diagonal pair orientation, categorize every pair as strong, moderate, weak or negligible, combine the commanded element excitations with that matrix into the active-reflection-coefficient and active-standing-wave-ratio of each radiator, sweep the scan volume for a scan-blindness angle, turn the coupling-induced excitation departure into an aperture-efficiency-loss and a sidelobe-level-penalty, and grade every result against the coupling allocation while keeping edge radiators separate from the lattice interior. Trigger: ecss, e-st-20c-clause-7-2-2-2-3, array-element-mutual-coupling, element-coupling-matrix, active-reflection-coefficient, active-standing-wave-ratio, scan-blindness-screening, embedded-element-pattern, coupling-induced-excitation-error."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: space-systems
pack: space-systems
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: space-systems
  subdomain: ecss
  tags: [ecss, e-st-20-electrical-scope, e20-array-element-mutual-coupling, array-element-mutual-coupling, element-coupling-matrix, active-reflection-coefficient, active-standing-wave-ratio, scan-blindness-screening, embedded-element-pattern, coupling-induced-excitation-error]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical Engineering -- Array Element Mutual-Coupling (space-systems/ecss/e20-array-element-mutual-coupling)

Use when the task is the clause 7.2.2.2.3 case of ECSS-E-ST-20C --
quantifying how the radiation of one array element reaches the other
elements of the same lattice, and what that traffic does to the
impedance each radiator presents, to the excitation it actually
radiates, and to the beam the array forms. The isolated-element
pattern and the isolated-element match are not the quantities the
array works with; this leaf replaces both with their in-lattice,
coupled equivalents.

## Domain quick reference

- Mutual-coupling is a pair property. Each ordered pair of radiators
  carries a complex coupling term whose magnitude falls with the pair
  spacing measured in wavelengths and whose phase follows the path
  between them. The pair orientation matters: for an aperture radiator
  the E-plane pair couples measurably harder than the H-plane pair at
  the same spacing, and the diagonal pair of a rectangular lattice
  couples least. A surface-wave decay term reduces the far pairs
  further when the radiating layer supports one.
- A pair is categorized by its coupling magnitude so that the
  assessment effort lands where it pays: strong pairs drive the active
  impedance, moderate pairs drive the excitation departure, weak pairs
  only move the sidelobe floor, and negligible pairs are carried for
  completeness. An uncategorized pair means the lattice geometry was
  never resolved, which is a finding rather than a pass.
- Active reflection is the quantity the beam-forming-network actually
  sees. With the whole lattice driven, the reflection at one radiator
  is its own match plus the sum, over every other radiator, of the
  coupling term times the ratio of that radiator's excitation to its
  own. Because the ratio carries the steering phase, the active
  reflection is a function of scan angle: an angle at which the terms
  add in phase and the active reflection magnitude approaches unity is
  a scan-blindness angle, and the array delivers no useful beam there
  even though every isolated radiator measured well.
- Coupling also changes what is radiated. The realized excitation of a
  radiator is its commanded excitation plus everything coupled into it
  from its neighbours, so a lattice commanded uniform radiates a
  slightly rippled taper. That ripple costs aperture-efficiency-loss
  against the commanded taper and lifts the sidelobe floor by the
  mean-square excitation departure spread over the element count.
- Edge radiators see an incomplete neighbourhood, so their active
  impedance departs from the interior value. Averaging an edge radiator
  into an interior population hides the worst active
  standing-wave-ratio in the array.

## Workflow

1. Resolve the lattice geometry: for every ordered pair, derive the
   spacing in wavelengths and the pair orientation plane. Reject a
   lattice with fewer than two radiators, with a duplicate radiator
   identity, or with two radiators at the same position.
2. Build the coupling matrix: convert each pair spacing and plane into
   a coupling magnitude in dB and a complex coupling term, and
   categorize each pair into its coupling regime.
3. Form the commanded excitations for the scan angle under assessment
   (amplitude taper times the progressive steering phase), then form
   the realized excitations by adding the coupled contribution of every
   neighbour.
4. Compute, per radiator, the active-reflection-coefficient and the
   active-standing-wave-ratio; keep the per-radiator values and the
   worst case, and mark which radiators sit on the lattice edge.
5. Sweep the scan volume: repeat step 4 at each commanded scan angle
   and flag any angle whose worst active reflection magnitude reaches
   the scan-blindness threshold.
6. Convert the commanded-to-realized excitation departure into the
   aperture-efficiency-loss and, through the RMS excitation error and
   the element count, into the sidelobe-level-penalty against the
   design sidelobe level.
7. Grade each quantity against its allocation. The lattice is not
   coupling-compliant until the worst pair coupling, the worst active
   standing-wave-ratio, the aperture-efficiency-loss, the
   sidelobe-level-penalty and the scan sweep are all clear.

## Pitfalls

- Using the isolated-element match as the array match. The number that
  gates the beam-forming-network design is the active reflection with
  every radiator driven, and it can be several times larger than the
  isolated value even when no single pair looks alarming.
- Screening only broadside. Coupling terms that cancel at broadside can
  add in phase at a steered angle, so a lattice that measures well on
  boresight can still carry a scan-blindness angle inside its required
  coverage; the sweep is the check, not the single-angle result.
- Treating coupling as a loss term to be subtracted once. Coupling
  redistributes excitation rather than removing it: the same mechanism
  shows up as an active impedance change, as a taper ripple, and as a
  sidelobe floor, and charging it only once understates two of the
  three.
- Averaging edge radiators into the interior population. The edge is
  where the active standing-wave-ratio peaks, so an array-mean figure
  can report compliance while individual radiators sit outside their
  allocation.
- Reading a small nearest-neighbour coupling as sufficient evidence.
  The active reflection sums every pair, so a lattice with many weak
  neighbours can exceed the allocation that a two-element measurement
  said was comfortable.

## Behavior contract (gate 3)

The coupling-matrix construction, regime categorisation, active
reflection and standing-wave-ratio, scan-blindness screening,
aperture-efficiency-loss, sidelobe-level-penalty and the aggregate
allocation grading are exercised by the gate 3 contract test:
scripts/test_e20_array_element_mutual_coupling.py against
scripts/e20_array_element_mutual_coupling_logic.py (stdlib unittest,
offline, deterministic). Run:
python3 scripts/test_e20_array_element_mutual_coupling.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
