---
name: solid-rivet-installation-quality
description: "Use when you must verify the installation quality of solid rivets during assembly: select the rivet length from the stack thickness plus a head-style allowance (protruding heads 1.5 diameters, countersunk heads 0.8 diameters), judge the driven shop head geometry against the workmanship bands (driven diameter 1.4 to 1.5 d, driven height 0.4 to 0.5 d), compute the squeeze force needed to upset the rivet against the material flow stress over the shank area, and check the hole fill clearance against the 0.1 mm limit. Produces the selected rivet length, the shop head verdict, the required squeeze force and the hole fill verdict that gate the assembly quality assessment. Trigger: solid rivet length selection, shop head dimensions, driven head formation, rivet squeeze force, hole fill check."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: as9100
    reference-only: true
gated: false
domain: manufacturing-quality
pack: assembly
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: manufacturing-quality
  subdomain: assembly
  tags: [solid-rivet-installation-quality, solid-rivet-installation, driven-head-formation, shop-head-dimension-check, rivet-squeeze-force, hole-fill-verification]
  version: 0.1.0
  author: Aero Agent Skills
---

# Solid Rivet Installation Quality (manufacturing-quality/assembly/solid-rivet-installation-quality)

Use when the task is verifying the installation quality of solid rivets
at assembly time. Solid rivets are deformation-driven permanent
fasteners: the installer selects a rivet long enough to fill the stack
and form a shop head, upsets the tail with a squeeze force against the
material flow stress, and the driven head must land inside workmanship
bands on diameter and height while the hole fill clearance stays within
the installation limit. This leaf implements the four checks in pure
Python, stdlib only: rivet length selection from the stack and the
head-style allowance, the driven shop head geometry verdict, the
squeeze force to upset, and the hole fill clearance check, plus a
combined installation verdict. It is the deformation-fastener complement
of manufacturing-quality/assembly/fastener-installation-quality, which
owns threaded and lock-bolt fastener mechanics; hole drilling process
control and rivet fatigue allowables are out of scope here.

## Domain quick reference

- Rivet length selection: length = stack + allowance, where the
  allowance is a head-style factor times the shank diameter. Typical
  practice: protruding heads 1.5 d, countersunk heads 0.8 d (documented
  workmanship allowance, confirm against the governing process
  specification for the program).
- Driven shop head geometry: after upsetting, the driven head diameter
  should fall between 1.4 d and 1.5 d and the driven height between
  0.4 d and 0.5 d, d being the nominal rivet shank diameter. A head
  below 1.4 d or 0.4 d is under-driven (insufficient fill), above
  1.5 d or 0.5 d is over-formed; the band is symmetric around 1.45 d
  and 0.45 d.
- Squeeze force: F = factor * sigma_flow * (pi d^2 / 4), with sigma_flow
  the flow stress in MPa (N/mm2) and a typical allowance factor of 1.5
  on the shank area upset force.
- Hole fill: clearance = hole diameter - rivet diameter; a driven rivet
  must fill its hole to within 0.1 mm of clearance (typical limit).
  Interference fits are out of scope for this check.
- Units: dimensions in mm, force in N, flow stress in MPa. The factors
  above are leaf-local typical values in the same epistemic class as
  the torque coefficient used by the threaded fastener sibling; they are
  workmanship practice, not standard data.
- AS9100 frames the process-control context (records, operator
  certification, traceability around the installation); the relations
  above are standard engineering methodology, summary-only.

## Workflow

1. Fix the installation: stack thickness, rivet shank diameter, head
   style ("protruding" or "countersunk").
2. Select the rivet length with select_rivet_length: allowance plus
   stack, 1.5 d protruding or 0.8 d countersunk.
3. Measure the driven shop head after upsetting and judge it with
   shop_head_verdict against the 1.4 to 1.5 d diameter and 0.4 to
   0.5 d height bands.
4. Compute the upset requirement with squeeze_force from the shank
   diameter, the material flow stress and the allowance factor.
5. Check the hole fill with hole_fill_check: the clearance between the
   drilled hole and the rivet must not exceed the 0.1 mm limit; a rivet
   larger than its hole (interference) is rejected as out of scope.
6. Combine the sub-checks with installation_verdict into one verdict
   with the overall ok flag when shop head and hole fill both pass.
7. Confirm the deterministic checks with the contract test
   scripts/test_solid_rivet_installation_quality.py.

## Worked example

A 4.0 mm protruding rivet over a 6.0 mm stack, driven head 5.8 mm
diameter by 1.8 mm height, flow stress 275 MPa, hole 4.08 mm.

- Length, protruding: allowance = 1.5 * 4.0 = 6.0 mm, so the rivet
  length is 6.0 + 6.0 = 12.0 mm (select_rivet_length real output).
- Length, countersunk: allowance = 0.8 * 4.0 = 3.2 mm, length 9.2 mm.
- Shop head: d_over_d = 5.8 / 4.0 = 1.45, h_over_d = 1.8 / 4.0 = 0.45,
  both mid-band, ok True.
- Under-driven head 5.0 x 1.2 mm: d_over_d 1.25, h_over_d 0.30, ok
  False (under the 1.4 d and 0.4 d edges).
- Squeeze force: area = pi * 4.0^2 / 4 = 12.566 mm2; F = 1.5 * 275 *
  12.566 = 5183.6 N (real module output 5183.63 N).
- Hole fill: 4.08 - 4.0 = 0.08 mm clearance, within 0.1 mm, ok True;
  a 4.15 mm hole gives 0.15 mm, ok False.
- Combined: installation_verdict on the good head and 4.08 mm hole
  returns overall_ok True.

## Verification

- Confirm select_rivet_length(6.0, 4.0, "protruding") returns
  allowance 6.0 mm and length 12.0 mm, and the countersunk case 3.2 and
  9.2 mm; doubling the stack adds exactly the stack increment.
- Confirm shop_head_verdict(5.8, 1.8, 4.0) returns 1.45 / 0.45 ok True
  and (5.0, 1.2, 4.0) returns 1.25 / 0.30 ok False; band edges 1.4 d /
  0.4 d and 1.5 d / 0.5 d pass inclusively, and 1.6 d or 0.55 h fail.
- Confirm squeeze_force(4.0, 275) returns 5183.6 N within 0.1 N, and
  that the force scales with the diameter squared, linearly with flow
  stress and linearly with the factor.
- Confirm hole_fill_check(4.08, 4.0) passes at 0.08 mm, (4.15, 4.0)
  fails at 0.15 mm, and the exact 0.1 mm boundary passes (clearance
  limit is <=).
- Confirm every non-positive stack, diameter, dimension, flow stress or
  factor, every unknown head style, every hole at or below the rivet
  diameter (interference), and every negative max clearance raises
  ValueError.
- Run the contract test offline: python3
  scripts/test_solid_rivet_installation_quality.py (30 tests,
  deterministic).

## Related leaves

- manufacturing-quality/assembly/fastener-installation-quality: the
  threaded and lock-bolt sibling (grip, thread protrusion and clamp
  load checks); boundary is torque mechanics versus deformation
  fasteners, this leaf never applies torque-tension relations.
- manufacturing-quality/assembly/ewis-installation-quality: the wiring
  installation sibling in the same assembly pack.

## Pitfalls

- Sizing with the wrong head-style allowance: protruding heads take
  1.5 d and countersunk heads 0.8 d, so a countersunk rivet sized at
  1.5 d is 0.7 d too long and its shop head will not form to band.
- Judging a driven head on diameter alone: the shop head verdict needs
  both the diameter (1.4 to 1.5 d) and the height (0.4 to 0.5 d) in
  band — an over-formed diameter with an under-driven height is still
  a fail, and a head below either low edge is under-driven rather than
  acceptable.
- Treating the workmanship values as standard data: the 1.5 d / 0.8 d
  allowances, 1.4-1.5 d and 0.4-0.5 d bands, 1.5 flow-stress factor
  and 0.1 mm hole fill limit are documented typical practice in the
  same epistemic class as the threaded sibling's torque coefficient —
  confirm them against the governing process specification.
- Feeding an interference fit: a hole at or below the rivet diameter
  raises ValueError — interference fits are out of scope for this
  check, not something to score with a negative clearance.
- Applying torque-tension mechanics here: this leaf is the deformation
  fastener complement of fastener-installation-quality and never
  applies the F = T / (k * D) relation used for threaded and lock-bolt
  fasteners.
- Passing on one sub-check: the combined installation verdict requires
  the shop head and the hole fill to pass together, so a mid-band head
  with a 0.15 mm hole clearance is still an overall fail.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_solid_rivet_installation_quality.py

The test covers the worked-example anchors (12.0 mm protruding and
9.2 mm countersunk lengths, 1.45/0.45 ok and 1.25/0.30 fail shop head
verdicts, 5183.6 N squeeze force to 0.1 N, 0.08 mm pass and 0.15 mm
fail hole fill), the inclusive band edges and band symmetry identity,
the d^2, flow stress and factor scaling laws, the exact 0.1 mm hole
fill boundary, the combined installation verdict and its keys, run to
run determinism, and ValueError rejection of every non-physical input
listed in Verification.

## Compliance

- Standards referenced, not reproduced: AS9100 is cited as the process
  control frame (reference-only per standards-map.yaml); the workmanship
  factors and relations above are typical engineering practice,
  summary-only.
- compliance: STANDARDS-REF, gated: false.
