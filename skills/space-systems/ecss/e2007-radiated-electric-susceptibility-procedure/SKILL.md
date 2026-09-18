---
name: e2007-radiated-electric-susceptibility-procedure
description: "Execute and audit one ECSS-E-ST-20-07C clause 5.4.11.4 radiated electric susceptibility run: confirm every radiation-safety provision is in place before the amplifier is keyed, compute the hazard clearance distance the forward power and antenna gain demand against the permissible exposure density, build the geometric step ladder across the declared test frequency range, compare the recorded exposure steps against it to expose skipped stretches and oversized jumps, grade each step dwell against the response time of the unit under test, and separate findings that stop the run from margins worth carrying. Use when running or reviewing a stepped radiated susceptibility exposure. Trigger: ecss, e-st-20-07c, radiated-electric-susceptibility-procedure, rf-hazard-clearance-distance, stepped-exposure-frequency-ladder, susceptibility-step-dwell-adequacy, radiated-exposure-step-coverage, radiation-safety-provision-check."
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
  tags: [ecss, e-st-20-electrical-scope, e2007-radiated-electric-susceptibility-procedure, rf-hazard-clearance-distance, stepped-exposure-frequency-ladder, susceptibility-step-dwell-adequacy, radiated-exposure-step-coverage, radiation-safety-provision-check]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EMC — Radiated Electric Susceptibility Procedure (space-systems/ecss/e2007-radiated-electric-susceptibility-procedure)

Use when the task is the run sequence of ECSS-E-ST-20-07C clause
5.4.11.4 -- the safety state the chamber has to be in before any power
reaches the antenna, and the stepped walk across the declared frequency
range that follows once it is.

## Domain quick reference

- This is the one EMC method where the hazard is to people rather than
  to hardware. The amplifier drives kilowatts into a directional antenna
  inside a sealed room, and the field on boresight close in is far above
  anything an occupied area may carry. The safety provisions are not
  paperwork ahead of the real procedure; they are the first steps of it.
- The hazard clearance distance follows from the drive, not from the
  chamber layout. The antenna concentrates the forward power into its
  beam, so the density on boresight is the isotropic spread P/(4*pi*d^2)
  raised by the gain, and the clearance is the distance at which that
  density falls to the permissible exposure limit. Raising the drive by
  four pushes the clearance out by two.
- Susceptibility is a fractional-bandwidth effect, so the walk is
  geometric: each step sits a fixed fraction above the one below it. A
  fixed hertz increment crawls at the bottom of the range and strides
  over resonances at the top, which is the opposite of what is wanted.
- The ladder is built by repeated multiplication rather than from a
  logarithm count. Library powers and logarithms are not correctly
  rounded and disagree in the last bits between hosts, so a ladder
  derived from a count can carry a different number of rungs on the
  machine that reviews the run than on the one that produced it.
- A pair of neighbouring steps further apart than the allowed fraction
  leaves a stretch of the range that was never driven. Nothing in the
  record marks that stretch, so it reads as a band the unit survived.
- Dwell is bounded below by what the unit does, not by what the operator
  finds tolerable. A fault that takes two seconds to show is invisible to
  a one-second step, and the step then records an immunity the unit does
  not have.
- A walk finer than the ladder costs chamber time and finds nothing the
  ladder misses. It is carried as a limitation, never as a defect.

## Workflow

1. Validate the safety provisions: every one declared, every value a
   boolean, no invented provision accepted. An absent provision stops the
   run before any frequency is set.
2. Compute the hazard clearance from the forward power, the antenna gain
   and the permissible exposure limit, and compare it with the nearest
   position that stays occupied while the amplifier is keyed.
3. Validate the declared range: positive start, stop above start, and a
   maximum fractional step strictly between nothing and one.
4. Build the step ladder by repeated multiplication, closing it on the
   declared stop frequency without duplicating a rung that lands there.
5. Normalize the recorded steps, rejecting a repeated frequency, a
   non-positive dwell and a step missing a field, then sort by frequency.
6. Reduce the recorded frequencies against the allowed ratio to expose
   oversized jumps and a walk that starts above or stops below the range.
7. Derive the dwell floor from the response time of the unit and the
   named minimum, and grade every step dwell against it.
8. Aggregate findings and limitations. The run stands only when no
   finding stands.

## Pitfalls

- Treating the safety provisions as a checklist signed before the run
  rather than a state held throughout it. The interlock that was armed at
  nine o'clock is not evidence about the door at eleven.
- Computing the clearance from the amplifier nameplate rather than the
  forward power actually delivered, which is the figure the density
  follows.
- Stepping in fixed hertz increments across a wide range, so the bottom
  decade is walked pointlessly slowly and the top decade is stepped over.
- Deriving the number of steps from a logarithm and trusting it to match
  across hosts. The count is where the rounding difference lands.
- Choosing a dwell from the time budget instead of the response time of
  the unit, then reading a quiet step as immunity.
- Rescanning because the walk was finer than the ladder. Redundant steps
  cost time; they never lose a stretch of the range.

## Behavior contract (gate 3)

The safety-provision validation, gain conversion, power-density and
hazard-clearance computation, span validation, step-ladder construction,
step-record normalization, coverage reduction, dwell-floor derivation and
run aggregation are exercised by the gate 3 contract test:
scripts/test_e2007_radiated_electric_susceptibility_procedure.py against
scripts/e2007_radiated_electric_susceptibility_procedure_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2007_radiated_electric_susceptibility_procedure.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
