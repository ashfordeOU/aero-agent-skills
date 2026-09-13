---
name: e2008-reverse-bias-test-process
description: "Verify a photovoltaic assembly's reverse current-voltage record against ECSS-E-ST-20-08C clause 6.4.3.14.2. Use when an assembly has no cell-coupled protection diode and its reverse sweep has to be judged: confirm the diode placement really leaves the assembly in scope, confirm the sweep ran under illumination rather than in the dark, check the points advance monotonically in reverse voltage, reach the required extent and step finely enough to resolve the knee, derive the peak reverse dissipation, and reconcile the assemblies recorded against those that owe a record. Trigger: ecss, e-st-20-08c-clause-6-4-3-14-2, solar-cell-assembly-reverse-bias-process, reverse-current-voltage-sweep-under-illumination, cell-coupled-protection-diode-exemption, reverse-sweep-step-resolution, peak-reverse-dissipation, reverse-bias-record-reconciliation."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-reverse-bias-test-process, solar-cell-assembly-reverse-bias-process, reverse-current-voltage-sweep-under-illumination, cell-coupled-protection-diode-exemption, reverse-sweep-step-resolution, peak-reverse-dissipation]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies -- Reverse-Bias Test Process (space-systems/ecss/e2008-reverse-bias-test-process)

Use when the task is the clause 6.4.3.14.2 test process of ECSS-E-ST-20-08C
-- judging whether the reverse current-voltage behaviour of a cell assembly
was recorded the way the clause requires: on the assemblies that actually
owe a record, under illumination rather than in the dark, and as a curve
resolved finely enough and carried far enough to be read.

## Domain quick reference

- The exemption turns on where the protection diode sits, not on whether
  one exists. A diode coupled across the cell clamps the cell's own reverse
  voltage to a diode drop, so there is nothing to record. A diode at string
  or section level protects the string and leaves every assembly inside it
  in scope.
- The sweep has to be illuminated. In the dark an assembly is only a
  junction, and a junction's reverse curve is not the curve of a lit cell
  being pushed backwards by its neighbours -- the photocurrent the string
  forces through it is exactly the quantity of interest and is absent from
  a dark sweep.
- A record is a curve, so the reverse voltage magnitudes have to advance
  strictly. A sweep that revisits a voltage, or steps back, is a scatter of
  points that no knee can be located in.
- Step size is a resolution requirement, not housekeeping. A step wider
  than the requirement allows lets the breakdown knee fall inside one long
  chord, and a chord across a knee reports a curve that bends nowhere.
- Peak dissipation, the largest product of reverse voltage and reverse
  current on the sweep, is the number the downstream thermal case consumes.
  It does not have to occur at the deepest point of the sweep, so it is
  found rather than assumed.

## Workflow

1. Resolve the protection-diode placement of each assembly to a scope
   decision, refusing a placement the campaign has not defined rather than
   guessing whether it clamps the cell.
2. For an assembly in scope with no sweep, raise the shortfall against that
   assembly by name; an exempt assembly with no sweep is clean and an exempt
   assembly that was swept anyway is simply extra data.
3. Validate the sweep as a curve: at least two points, each a non-negative
   voltage and current magnitude, strictly advancing in reverse voltage.
4. Check the irradiance against the declared illumination floor, absorbing
   representation error at the boundary with a named tolerance rather than
   by lowering the floor.
5. Compute the extent reached and the widest step taken, and compare both
   against the requirement.
6. Locate the peak dissipation point by scanning the whole sweep.
7. Reconcile the campaign: which assemblies owed a record, which produced
   one, which were exempt, and report a pass only when no assembly raised a
   finding.

## Pitfalls

- Reading "the design has bypass diodes" as an exemption. The diodes are
  usually at string or section level, which is the case the clause is
  written for, not against.
- Sweeping in the dark because it is easier to set up. The dark curve is
  reproducible, cheap and about a different device than the one the string
  drives backwards.
- Stopping the sweep at the first sign of current. The extent requirement
  exists because the interesting region is past that point, and a sweep cut
  short reports an assembly that looks better behaved than it is.
- Taking coarse steps to save run time. The knee then sits inside a single
  chord and the record shows a gentle slope where the assembly actually
  turns over.
- Assuming peak dissipation is at the end of the sweep. A current that
  falls back after breakdown puts the peak mid-curve, and a thermal case
  built on the last point understates it.
- Counting records against the whole campaign instead of against the
  assemblies that owe one. A batch where the exempt assemblies were swept
  and two in-scope ones were not can still show a healthy total.

## Behavior contract (gate 3)

The diode-placement scope decision, illumination check, sweep validation,
extent and step metrics, peak-dissipation search and the campaign
reconciliation are exercised by the gate 3 contract test:
scripts/test_e2008_reverse_bias_test_process.py against
scripts/e2008_reverse_bias_test_process_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_e2008_reverse_bias_test_process.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
