---
name: e2006-material-assembly-qualification-testing
description: "Use when verify that a spacecraft-charging qualification campaign exercises every material and every assembly under both the normal-gradient and the inverted-gradient potential condition of ECSS-E-ST-20-06C clause 6.6.3: derive the gradient polarity from the measured dielectric-surface and structure potentials, compute the qualification stress from the worst-case predicted differential-potential and the qualification factor, categorize each run as qualifying or non-qualifying against campaign level, applied differential-potential, dwell-duration and discharge-detection instrumentation, and report the polarity conditions still unqualified per item. Trigger: ecss, e-st-20-electrical-scope, e-st-20-06c, inverted-potential-gradient, normal-potential-gradient, qualification-stress-factor, differential-potential, discharge-detection, polarity-coverage-gap, dielectric-polarity-reversal."
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
  tags: [ecss, e-st-20-electrical-scope, e2006-material-assembly-qualification-testing, e-st-20-06c, inverted-potential-gradient, normal-potential-gradient, qualification-stress-factor, differential-potential, discharge-detection, polarity-coverage-gap]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Spacecraft Charging — Both-Polarity Qualification of Materials and Assemblies (space-systems/ecss/e2006-material-assembly-qualification-testing)

Use when the task is the clause 6.6.3 qualification rule of
ECSS-E-ST-20-06C: a dielectric material, and the assembly it is built
into, has to be qualified under the normal-gradient potential
condition and again under the inverted-gradient condition, because the
two polarities fail by different mechanisms and a campaign that
exercises only one of them leaves half the flight envelope
unqualified.

## Domain quick reference

- The gradient polarity is defined by the sign of the dielectric
  surface potential relative to the potential of the conductor behind
  it. Surface below structure is the normal-gradient case — the
  eclipse-side, electron-dominated condition where the exposed
  dielectric charges negative against a structure held nearer plasma
  potential. Surface above structure is the inverted-gradient case —
  the sunlit condition where photoemission drives the illuminated
  dielectric positive while the structure floats negative, and it is
  the condition most often omitted from a campaign.
- The two polarities are not interchangeable evidence. A
  normal-gradient breakdown propagates as a surface flashover of the
  charged dielectric; an inverted-gradient breakdown starts at the
  triple-junction between dielectric, conductor and vacuum and can
  proceed at a markedly lower differential-potential. Qualifying only
  the normal case therefore proves nothing about the inverted case,
  and the opposite substitution is equally invalid.
- A run qualifies a polarity condition for an item only when four
  things hold together: the campaign level is qualification-grade; the
  applied differential-potential reaches the qualification stress
  (worst-case predicted differential-potential multiplied by the
  qualification factor); the dwell-duration reaches the required
  dwell; and a discharge-detection channel was actually recording, so
  a quiet run is evidence rather than an absence of measurement.
- The pass criterion on a qualifying run is severity-based. Zero
  detected events is a pass; isolated low-energy events may be
  accepted where the programme declares a non-zero allowance; a
  sustained or high-energy event is a failure of that polarity
  condition regardless of count.
- Coverage is tracked per item and per polarity. An assembly and the
  materials inside it are separate items: qualifying the assembly in
  both polarities does not close a material-level obligation the
  programme raised, and vice versa. The deliverable is the list of
  (item, polarity) pairs still open.

## Workflow

1. Normalize each item: identifier, kind (material or assembly),
   worst-case predicted differential-potential, required dwell, and
   the event allowance the programme permits. Reject a non-positive
   predicted potential and an unrecognized item kind.
2. Compute the qualification stress for the item: predicted
   differential-potential times the qualification factor, with the
   factor rejected below unity — a factor under one would qualify to
   less than the flight case.
3. Normalize each run: item reference, campaign level, measured
   dielectric-surface and structure potentials, applied dwell,
   instrumentation channels and the detected-event record.
4. Derive the polarity of the run from the two measured potentials
   rather than trusting a label: surface below structure is
   normal-gradient, surface above structure is inverted-gradient, and
   an equal pair is a no-gradient run that qualifies neither
   condition.
5. Categorize the run: non-qualifying if the level is not
   qualification-grade, if the applied differential-potential falls
   short of the qualification stress, if the dwell falls short, or if
   no discharge-detection channel was present. Treat an exact match on
   stress or dwell as compliant — the comparison runs on stored
   floating-point values and an equality case is absorbed by a named
   tolerance, not by relaxing the limit.
6. Grade the detected-event record of every qualifying run against the
   allowance and the severity rule, and mark the polarity condition
   qualified only on a passing run.
7. Aggregate per item: an item is qualified only when both polarity
   conditions carry a passing qualifying run. Report every open
   (item, polarity) pair as the residual qualification programme.

## Pitfalls

- Accepting the run's own polarity label instead of deriving it from
  the measured potentials — a mis-wired bias supply that reverses the
  sign silently re-tests the polarity already covered and leaves the
  other one open.
- Treating a quiet run with no discharge-detection channel as a pass:
  nothing was watching, so the run is uninstrumented, not clean.
- Qualifying the assembly and closing the material obligation with it,
  or the reverse — the two items are tracked separately.
- Applying a qualification factor below unity, or applying the factor
  to the measured rather than the worst-case predicted
  differential-potential, which silently qualifies to less than the
  flight condition.
- Counting isolated low-energy events and a sustained event as the
  same finding: the severity rule fails the sustained event even when
  the count sits inside the programme allowance.

## Behavior contract (gate 3)

The polarity derivation, qualification-stress computation, run
categorization, event-severity grading and per-item coverage logic is
exercised by the gate 3 contract test:
`scripts/test_e2006_material_assembly_qualification_testing.py`
against
`scripts/e2006_material_assembly_qualification_testing_logic.py`
(stdlib unittest, offline). Run:
python3 scripts/test_e2006_material_assembly_qualification_testing.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
