---
name: fastener-installation-quality
description: "Use when you must verify the installation quality of aerospace structural fasteners during assembly: select the grip length for the clamped stack from the available grip increments, check the thread protrusion against the typical protrusion band, compute the clamp load from the applied torque with the torque coefficient, verify the clamp load and the torque scatter band against the joint allowables, check the countersink flushness for flush head fasteners, confirm the swage collar engagement for lock-bolt fasteners, and classify the installation verdict as pass, rework, or scrap with the specific defect. Produces the selected grip, the protrusion check, the clamp-load estimate, the flushness and engagement checks, and the installation verdict that gate the assembly quality assessment. Trigger: fastener installation quality, grip length selection, thread protrusion, clamp load from torque, countersink flushness, collar engagement, Hi-Lok installation check."
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
  tags: [fastener-installation-quality, grip-length-selection, thread-protrusion, clamp-load-from-torque, countersink-flushness, collar-engagement, hi-lok-installation-check, structural-fastener-verification, swage-collar]
  version: 0.1.0
  author: Aero Agent Skills
---

# Fastener Installation Quality (manufacturing-quality/assembly/fastener-installation-quality)

Use when the task is verifying the installation quality of aerospace
structural fasteners (bolts, Hi-Loks, rivets) at assembly time:
selecting the correct grip length for the clamped stack from the
available grip increments, checking the thread protrusion after
installation, computing the clamp load from the applied torque with
the torque coefficient, verifying the clamp load and the torque
scatter band against the joint allowables, checking the countersink
flushness for flush head fasteners, confirming swage collar
engagement for lock-bolt fasteners, and classifying the installation
verdict as pass, rework, or scrap with the specific defect. This leaf
implements the checks in pure Python, stdlib only. It is the first
leaf of the assembly pack and pairs with
structures/composites/composite-bolted-joints, which analyzes the
bearing and bypass stresses of the same bolted joint, and with the
as9100 process-control leaves that govern the tooling and records
around the installation. Fastener hole fatigue screening and fastener
pattern design are out of scope here.

## Domain quick reference

- Grip selection: the installed grip must cover the clamped stack.
  Grip = the smallest available grip increment at least the stack
  total; when no increment reaches the total, no grip fits the stack.
  Protrusion = grip minus stack total, the thread extending past the
  nut or collar.
- Thread protrusion band: a typical structural bolt protrusion of
  0.5 to 3.0 mm past the nut (documented typical values, confirm
  against the fastener manufacturer data and the governing code).
  Negative protrusion (a grip shorter than the stack) is out of band.
- Clamp load from torque: F = T / (k * D), with T the applied torque
  in N m, k the torque coefficient (typical 0.2 lubricated) and D the
  nominal fastener diameter in m.
- Clamp verdict: the estimated clamp load must sit between the joint
  minimum required clamp and the joint allowable clamp (embedment or
  pull-out limit). Below the minimum is under-clamp, above the
  allowable is over-clamp.
- Countersink flushness: for flush head fasteners the measured
  flushness (positive proud, negative recessed) must stay within the
  tolerance, typically 0.13 mm.
- Swage collar engagement: for lock-bolt fasteners the collar must
  engage at least 2 full threads (typical practice).
- Torque scatter: when the actual applied torque is recorded,
  scatter = abs(actual minus applied) / applied * 100 percent; a
  typical scatter band of 15 percent is acceptable (informational
  note, confirm against the program control plan).
- AS9100 frames the assembly process control context; the relations
  above are standard engineering methodology, summary-only.

## Workflow

1. Collect the clamped stack thicknesses, the available grip
   increments, the fastener diameter, the applied torque and the joint
   clamp limits (min_clamp_N, max_clamp_N) from the installation
   record and the joint drawing.
2. Select the grip with select_grip(stack_thicknesses_mm,
   available_grips_mm) and read the stack total, grip and protrusion.
3. Check the protrusion with protrusion_ok(protrusion_mm) against the
   typical 0.5 to 3.0 mm band.
4. Estimate the clamp load with clamp_load_N(applied_torque_Nm,
   k_factor, fastener_diameter_m) and classify it with
   clamp_verdict(clamp_N, min_clamp_N, max_clamp_N).
5. For flush head fasteners, check flushness_ok(measured_mm,
   tolerance_mm) with the countersink measurement. For lock-bolts,
   confirm collar_engagement_ok(engaged_threads) reaches the minimum
   thread count.
6. Run installation_verdict with the full input set to get the
   verdict (pass, rework, scrap), the specific defect, the clamp
   values and the torque scatter note.
7. Confirm the deterministic checks with the contract test
   scripts/test_fastener_installation_quality.py.

## Worked example

1/4 inch bolt-nut joint, protruding head: stack [4.0, 6.0, 4.0] mm
(total 14.0 mm), available grips [12.7, 15.875, 19.05] mm,
D = 0.00635 m, torque 24 N m, k = 0.2, min clamp 12000 N, max clamp
25000 N.

- select_grip: total 14.0 mm; the smallest available grip at least
  14.0 is 15.875 mm; grip 15.875 mm, protrusion 1.875 mm.
  protrusion_ok True (inside [0.5, 3.0]).
- clamp_load_N: 24 / (0.2 * 0.00635) = 18897.6 N (within 0.5);
  clamp_verdict "clamp-ok" (12000 <= 18897.6 <= 25000).
- installation_verdict: "pass", defect None, clamp verdict clamp-ok.
- No grip fits: stack [10.0, 8.0] mm = 18.0 mm against grips [12.7,
  15.875] mm gives grip None, verdict "rework", defect
  "no-grip-fits". With grips [12.7, 15.875, 19.05, 22.0] mm the same
  stack selects 19.05 mm (protrusion 1.05 mm) and passes.
- Protrusion fail: stack 15.9 mm against the extended grip list
  selects 19.05 mm with protrusion 3.15 mm, above the 3.0 mm band,
  verdict "rework", defect "protrusion-out-of-band". A misfitted
  grip shorter than the stack gives a negative protrusion, for
  example protrusion_ok(-0.025) is False, the same defect path.
- Over-clamp: torque 40 N m gives 31496 N, above the 25000 N
  allowable, verdict "scrap", defect "over-clamp". Under-clamp:
  torque 10 N m gives 7874 N, below the 12000 N minimum, verdict
  "rework", defect "under-clamp".
- Flushness fail: flush head with measured +0.22 mm against the 0.13
  mm tolerance gives verdict "rework", defect
  "flushness-out-of-tolerance".
- Collar fail: lock-bolt with 1 engaged collar thread gives verdict
  "rework", defect "collar-engagement"; 2 threads pass.
- Scatter note: actual torque 26.4 N m gives scatter 10.0 percent
  (scatter_ok True); actual 30 N m gives 25 percent (scatter_ok
  False, informational only).

## Verification

- Confirm select_grip([4.0, 6.0, 4.0], [12.7, 15.875, 19.05]) returns
  stack total 14.0 mm, grip 15.875 mm, protrusion 1.875 mm, and that
  protrusion_ok(1.875) is True while protrusion_ok(-0.025) is False.
- Confirm clamp_load_N(24, 0.2, 0.00635) returns 18897.6 N within
  0.5, and clamp_verdict(18897.6, 12000, 25000) is "clamp-ok".
- Confirm the worked example installation_verdict result is "pass"
  with defect None, and each fail case (no-grip-fits,
  protrusion-out-of-band, over-clamp scrap, under-clamp rework,
  flushness-out-of-tolerance, collar-engagement) maps to the expected
  verdict and defect.
- Confirm the scatter note: actual 26.4 N m gives 10.0 percent with
  scatter_ok True, actual 30 N m gives 25 percent with scatter_ok
  False, and no actual torque gives None for both fields.
- Confirm ValueError rejection of non-physical inputs: empty stack,
  negative stack thickness, empty or unsorted grips, torque 0 or
  negative, k factor 0 or negative, diameter 0 or negative, minimum
  clamp 0 or a maximum below the minimum, negative engaged threads, a
  flush head without a measured flushness, fastener_type "screw" and
  an unknown head_style.
- Run the contract test offline: python3
  scripts/test_fastener_installation_quality.py (35 tests,
  deterministic).

## Related leaves

- structures/composites/composite-bolted-joints: the stress analysis
  of the same bolted joint (bearing and bypass loads); this leaf
  verifies the physical installation, that leaf verifies the joint
  strength allowables.
- manufacturing-quality/as9100/calibration-control: the torque tools
  and measuring equipment used for the installation must sit inside
  calibration control.
- manufacturing-quality/as9100/nonconformance-control: disposition of
  the rework and scrap installations this leaf classifies.

## Pitfalls

- Releasing a joint whose grip selection found no fit: when no
  available grip increment reaches the stack total the verdict is
  rework with defect no-grip-fits — and a grip shorter than the stack
  produces negative protrusion, which is always out of band, never a
  pass.
- Confusing clamp verdict direction: below the joint minimum clamp is
  under-clamp (rework) while above the joint allowable is over-clamp
  (scrap) — the two failure modes have different dispositions and must
  not be merged into one defect.
- Checking the protrusion band without the fastener data: the 0.5 to
  3.0 mm band is a documented typical value that must be confirmed
  against the fastener manufacturer data and the governing code for
  the program, and the 0.13 mm flushness tolerance and 15 percent
  scatter band carry the same confirm-first status.
- Reading torque scatter as a verdict input: the scatter note is
  informational only (scatter_ok False never changes pass, rework or
  scrap), so a 25 percent scatter flags a process-control problem
  without silently failing an otherwise sound installation.
- Forgetting the head and fastener type gates: a flush head without a
  measured flushness, a lock-bolt checked without engaged threads, a
  fastener_type of "screw", and an unknown head_style all raise
  ValueError — the check set must match the fastener being verified.
- Assuming this leaf verifies joint strength: it checks the physical
  installation (grip, protrusion, clamp load, flushness, engagement);
  bearing and bypass stress allowables of the same bolted joint belong
  to structures/composites/composite-bolted-joints.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_fastener_installation_quality.py

The test covers the worked example anchors (stack 14.0 mm, grip
15.875 mm, protrusion 1.875 mm, clamp load 18897.6 N, clamp verdict
clamp-ok, verdict pass), grip selection boundaries (exact match, next
increment, no grip fits), the protrusion band with inclusive
boundaries and negative values, clamp load scaling with torque and k,
clamp verdict branches with inclusive boundaries, flushness checks in
both proud and recessed directions, collar engagement at and below
the minimum with the None input, every verdict and defect path
including the lock-bolt and rivet type paths, the torque scatter note
in and out of band, and ValueError rejection of every non-physical
input class.

## Compliance

- AS9100 is referenced for assembly process control context only, not
  reproduced; standards-map.yaml governs the citation form.
- The protrusion band, minimum engaged threads, torque coefficient,
  flushness tolerance and torque scatter band are documented typical
  aerospace practice values, paraphrased, not reproductions of
  standard text. Confirm each against the fastener manufacturer data
  and the governing code for the program before releasing an
  installation.
- compliance: STANDARDS-REF, gated: false.
