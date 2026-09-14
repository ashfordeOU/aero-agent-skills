---
name: e2008-diode-characterization-pass-criteria
description: "Assess whether each characterised protection diode meets the limits its source control drawing fixes under ECSS-E-ST-20-08C clause 9.4.5.2.3: refuse a limit set carrying no drawing reference or issue, refer every measured forward voltage to the reference junction temperature with the declared coefficient, judge the referred drop and the reverse leakage against their own drawing limits with a tie admissible, report each margin and name every breach rather than the first, take the rejected share of the lot against the declared allowance, and flag an accepted part with almost nothing left for degradation. Use when characterised diode data has to become an acceptance verdict. Trigger: ecss, e-st-20-08c-clause-9-4-5-2-3, protection-diode-acceptance-sentencing, source-control-drawing-diode-limits, diode-forward-voltage-margin, diode-reverse-leakage-margin, acceptance-lot-diode-reject-allowance, marginal-diode-degradation-advisory."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-diode-characterization-pass-criteria, protection-diode-acceptance-sentencing, source-control-drawing-diode-limits, diode-forward-voltage-margin, diode-reverse-leakage-margin, acceptance-lot-diode-reject-allowance, marginal-diode-degradation-advisory]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies -- Protection Diode Pass Criteria (space-systems/ecss/e2008-diode-characterization-pass-criteria)

Use when the task is to turn a recorded protection diode
characterisation into an acceptance verdict under ECSS-E-ST-20-08C
clause 9.4.5.2.3 -- comparing the measured forward and reverse
behaviour against the limits the relevant source control drawing holds,
and saying what the part, and then the lot, has earned.

## Domain quick reference

- The clause names where the limits come from, and that is the load
  bearing part of it. The source control drawing governs the part. A
  datasheet, a handbook table or the bench operator's recollection is
  not a controlled document, so a limit set with no drawing reference
  and no issue is refused here rather than used.
- The drawing supplies the conditions as well as the ceilings. The
  forward drop is a limit at a stated test current and the leakage is a
  limit at a stated reverse voltage; either number quoted without its
  condition is a value nobody can reproduce.
- A forward drop has to be referred to the reference junction
  temperature before it is compared. The drop moves by millivolts per
  kelvin, so a warm bench flatters every part on it and a part measured
  hot can pass against a limit it would breach cold.
- The two limits fail independently and for different physical reasons.
  A high forward drop is a series or junction problem; high leakage is
  a junction or surface one. Grouping a part only as accept or reject
  discards which of those the lot has.
- A tie is admissible. A part landing exactly on a drawing limit meets
  it, and the comparison tolerance absorbs representation error so the
  limit itself does not move.
- Meeting a limit with nothing left over is not the same as meeting it
  comfortably. A part accepted on the line has spent its whole budget
  before launch, and the mission still has degradation to add, so it is
  accepted and flagged rather than quietly passed.
- The lot carries its own question. Individual rejects are expected and
  handled by replacement; a rejected share above the declared allowance
  says the lot, not the part, is what failed.

## Workflow

1. Validate the sentencing policy and then the limit set. Refuse a
   drawing reference or issue that is missing or blank before any
   measurement is touched, because an untraceable limit cannot carry an
   acceptance decision.
2. Refer each measured forward drop to the drawing's reference junction
   temperature using the declared coefficient. The referred value, not
   the raw reading, is what the limit applies to.
3. Judge the referred drop against the forward ceiling and the measured
   leakage against the reverse ceiling, independently, with a tie
   passing on either.
4. Report both margins for every part whatever the disposition, since a
   passing margin is the number a later degradation claim is measured
   against.
5. Group each part by which limit it breached: accept, accept with
   advisory, reject on forward voltage, reject on reverse leakage, or
   reject on both. Name every breach the part carries, not only the
   first one found.
6. Flag an accepted part whose tighter margin falls inside the advisory
   band. A margin landing exactly on the band is not marginal; a
   negative margin is a breach and is never reported as an advisory.
7. Take the rejected share of the characterised lot against the
   allowance and close on one lot verdict: lot accepted, accepted with
   advisory, contains rejects, or reject allowance exceeded.

## Pitfalls

- Sentencing against a datasheet. The drawing is what the procurement
  and the qualification were written to; a catalogue figure for the
  same part number can differ, and nothing traces the decision back.
- Comparing a raw forward reading. A bench at sixty degrees hands back
  drops tens of millivolts low, which is the width of the whole
  acceptance band on many parts, so an unreferred comparison passes
  parts the drawing rejects.
- Quoting a limit without its test condition. A forward voltage limit
  at an unstated current and a leakage limit at an unstated reverse
  voltage are both unreproducible, and the retest will not agree.
- Collapsing the two branches into one reject reason. Forward and
  reverse failures point at different mechanisms, and a lot showing one
  of each is a different problem from a lot showing five of one.
- Treating a part on the line as a comfortable pass. It met the limit
  with nothing left, and degradation has not started yet.
- Reading a negative margin as an advisory. A breach is a breach; the
  advisory band only ever describes a part that actually passed.
- Stopping at the first rejected part. The lot verdict needs the whole
  count, and a reject share above the allowance is a different finding
  with a different fix from one bad diode.

## Behavior contract (gate 3)

The policy validation, drawing provenance refusal, temperature
referral, margin arithmetic, the tie-admissible limit comparison, the
advisory band at its exact bound, per-part grouping across both
branches, lot reject share against its allowance, and the lot verdict
are exercised by the gate 3 contract test:
scripts/test_e2008_diode_characterization_pass_criteria.py against
scripts/e2008_diode_characterization_pass_criteria_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_diode_characterization_pass_criteria.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
