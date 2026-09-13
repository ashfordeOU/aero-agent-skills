---
name: e2007-antenna-port-spurious-emissions
description: "Use when verify that the supplier-declared spurious-emission limits at a spacecraft antenna-port actually protect every co-located receiver under ECSS-E-ST-20-07C clause 4.2.6: normalise each declared emission-mask into ordered non-overlapping frequency-segments, confirm the mask covers every victim-receiver passband and every carrier harmonic-emission that lands in one, propagate the worst declared limit through the antenna-to-antenna-isolation to the victim antenna-port, compare that coupled level against the receiver-susceptibility-threshold with the required intersystem-compatibility margin, and back out the isolation a failing antenna-pair needs, treating an undeclared mask-gap as a finding rather than a silent pass. Trigger: ecss, e-st-20-electrical-scope, antenna-port, spurious-emission-limit, emission-mask, harmonic-emission, antenna-to-antenna-isolation, receiver-susceptibility-threshold, intersystem-rf-compatibility."
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
  tags: [ecss, e-st-20-electrical-scope, e2007-antenna-port-spurious-emissions, antenna-port, spurious-emission-limit, emission-mask, harmonic-emission, antenna-to-antenna-isolation, receiver-susceptibility-threshold]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electromagnetic Compatibility — Antenna-Port Spurious Emissions (space-systems/ecss/e2007-antenna-port-spurious-emissions)

Use when the task is the clause 4.2.6 obligation of ECSS-E-ST-20-07C: the
supplier states, port by port, how much unwanted radio-frequency energy is
allowed to leave a transmitter antenna-port outside its assigned channel.
That statement is only worth something if it is complete over the frequencies
that matter and low enough for every receiver sharing the same vehicle.

## Domain quick reference

- A declared limit is a mask, not a single number: an ordered set of
  frequency-segments, each carrying the highest unwanted level permitted at
  the antenna-port inside it. Segments may abut but must not overlap -- where
  two declarations disagree over the same frequency neither one is the limit,
  and the declaration is malformed rather than conservative.
- Coverage is the first half of the clause. The mask has to say something
  over each victim-receiver passband and at each carrier harmonic-emission
  that falls inside one. A frequency the mask never reaches is not "permitted
  zero" and not "no risk" -- it is an undeclared limit, which is a clause
  4.2.6 finding in its own right and cannot be closed by computation.
- Compatibility is the second half. The level arriving at a victim
  antenna-port is the declared limit reduced by the antenna-to-antenna
  isolation between the two ports; that coupled level is compared against the
  victim's susceptibility-threshold and the difference is the intersystem
  compatibility margin. A pair meets the clause only when that margin reaches
  the programme-required value.
- Inside a victim passband the governing number is the worst (highest)
  declared limit of any segment overlapping that passband, not the limit at
  the band centre -- a mask that steps up near a band edge still has to be
  read at its step.
- Working the comparison backwards gives the isolation the layout owes:
  declared limit minus susceptibility-threshold plus required margin. That
  number is the useful output of a failing antenna-pair, because it is what
  drives antenna placement, decoupling structure or a tighter declared limit.
- Isolation is a non-negative decibel quantity between two passive ports. A
  negative value would mean the victim port collects more than the emitter
  port radiated, which no passive coupling path delivers, so it is rejected
  as bad input rather than carried through as a worst case.

## Workflow

1. Normalise each emitter's declared mask into ordered frequency-segments.
   Reject a mask that is empty, that carries a non-positive or inverted
   frequency-segment, or whose segments overlap; an overlapping declaration
   has no single limit and cannot be evaluated.
2. Enumerate the carrier harmonic-emission frequencies up to the programme
   harmonic order and record every one that falls inside a victim passband
   but outside the declared mask. Each is an undeclared-limit finding.
3. For every emitter-victim antenna-pair, intersect the mask with the victim
   passband. Any part of the passband the mask does not cover is a coverage
   gap and the pair is reported as undeclared, never as compliant.
4. Where the passband is fully covered, take the worst declared limit across
   the overlapping segments and reduce it by the antenna-to-antenna isolation
   declared for that pair to obtain the coupled level at the victim port.
5. Subtract the coupled level from the victim susceptibility-threshold to get
   the intersystem compatibility margin, and compare it against the required
   margin, absorbing decibel round-off at the equality point instead of
   moving the limit.
6. For a pair that does not reach the required margin, compute the isolation
   the pair needs and report the shortfall against the isolation on record.
7. Aggregate: the emitter set is compatible only when no pair carries a
   coverage gap, no harmonic-emission is undeclared inside a victim passband,
   and every pair reaches the required margin.

## Pitfalls

- Reading a mask gap as a pass. A frequency with no declared limit has not
  been shown to be low; clause 4.2.6 asks the supplier to define the limit,
  so absence of a limit is the defect being looked for.
- Evaluating the mask only at the victim band centre. The governing value is
  the worst overlapping segment, and a mask that relaxes toward a band edge
  will look compliant at the centre and fail at the edge.
- Letting overlapping mask segments through because the tool can still take
  a maximum. Two contradictory declarations for one frequency mean the
  declaration itself is unusable, and silently picking the harsher of the two
  hides a document defect.
- Comparing the declared limit straight against the susceptibility-threshold
  and forgetting the antenna-to-antenna isolation, which understates every
  margin on the vehicle and condemns pairs that are physically fine.
- Widening the required margin to make an exactly-equal pair pass. A pair
  that lands precisely on the required margin is compliant; the fix is to
  absorb decibel representation error at the comparison, not to lower the
  requirement.
- Treating the harmonic-emission check as covered by the passband sweep. A
  harmonic can sit inside a victim passband that the mask covers elsewhere
  but not at the harmonic frequency, so the two checks are separate.

## Behavior contract (gate 3)

The mask normalisation, coverage-gap, harmonic-emission, coupling, margin and
required-isolation logic is exercised by the gate 3 contract test:
scripts/test_e2007_antenna_port_spurious_emissions.py against
scripts/e2007_antenna_port_spurious_emissions_logic.py (stdlib unittest,
offline, deterministic). Run:
python3 scripts/test_e2007_antenna_port_spurious_emissions.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
