---
name: e2008-electrical-health-check-purpose
description: "Use when an assembly has been checked electrically and the health statement needs its coverage and its resolution made explicit. Evaluate whether a set of continuity, insulation, polarity, bypass diode and bonding checks amounts to the electrical health assessment ECSS-E-ST-20-08C clause 5.5.3.3.1 asks for: cover every declared current-carrying path and isolation barrier, derive each instrument's discrimination against the band it has to judge, return indeterminate where a reading inside the band says more about the instrument than about the assembly, and keep an unmeasured path apart from a healthy one. Trigger: ecss, e-st-20-08c, clause-5-5-3-3-1, photovoltaic-assembly-electrical-health, continuity-path-coverage, insulation-barrier-proof-voltage, measurement-discrimination-ratio, indeterminate-electrical-check."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-electrical-health-check-purpose, photovoltaic-assembly-electrical-health, continuity-path-coverage, insulation-barrier-proof-voltage, measurement-discrimination-ratio, indeterminate-electrical-check, solar-array-bypass-diode-function-check]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic -- Electrical Health Check Purpose (space-systems/ecss/e2008-electrical-health-check-purpose)

Use when the task is the clause 5.5.3.3.1 purpose of the electrical checks in
ECSS-E-ST-20-08C -- explaining, or grading, why continuity, insulation and the
checks beside them are one assessment of the assembly's electrical health
rather than a list of unrelated measurements.

## Domain quick reference

- A photovoltaic assembly has two electrical failure modes and no third.
  Current fails to go where it should -- a cracked interconnector joint, a
  lifted bus bar, a diode that stopped conducting -- or it goes where it
  should not, across an isolation barrier bridged by a solder ball, a swarf
  particle or damaged insulation. Continuity looks for the first and
  insulation for the second, and together they span the space. That is the
  reason they are grouped, and it is also the reason neither alone is a health
  assessment.
- Polarity, bypass diode function and structure bonding are the same two
  questions asked about the parts that only misbehave in a particular
  direction or a particular condition: a string wired the wrong way round, a
  diode that will not take current when a cell shades, a strap that leaves
  charge with nowhere to go.
- The assessment is a statement about the whole assembly, so it is bounded by
  coverage. Every declared current-carrying path needs a continuity check and
  every declared isolation barrier needs an insulation check; a path nobody
  measured is unmeasured, not healthy, and the two have to read differently in
  the output.
- The assessment is also bounded by discrimination. A check can only report a
  defect its instrument could have resolved, so the number that matters beside
  every reading is how many instrument steps fit inside the band the check has
  to judge. An instrument too coarse for the band turns a reading inside it
  into a statement about the instrument.
- An insulation measurement taken below the barrier's rated voltage never
  stressed the barrier it existed to prove. A defect that only opens under
  voltage would not have shown, so the result is indeterminate whatever
  resistance came back.
- Indeterminate is a real outcome, not a polite failure. It did not pass and
  it did not fail, and collapsing it into either one is the defect this
  reasoning exists to prevent.
- A defect large enough to show through a coarse instrument is still a real
  defect. Poor discrimination withholds a healthy verdict; it does not excuse
  a degraded or failed one.

## Workflow

1. Take the assembly's declared current-carrying paths and isolation barriers.
   Reject a duplicated identifier and reject a check aimed at a target the
   assembly does not declare -- both make the coverage arithmetic meaningless.
2. Route each check to its own rule: continuity against the expected path
   resistance, insulation against the resistance floor and the barrier rating,
   polarity against the wiring intent, diode against its forward window and
   reverse leakage, bond against its resistance limit.
3. For each measurement with a band, derive the discrimination ratio from the
   band and the instrument resolution, and downgrade a healthy reading to
   indeterminate when the ratio is short.
4. Compute coverage over the declared paths and barriers, and name the ones
   nothing reached.
5. Take the worst check outcome, then apply the coverage rule: an incomplete
   assessment is at best indeterminate, however clean the checks that were run.
6. Report the outcome, the coverage fraction, the uncovered paths and
   barriers, the indeterminate check identifiers and the unhealthy ones as
   separate fields, so a reader can see which of the three limits is in play.

## Pitfalls

- Reading a set of passed checks as a healthy assembly. The checks cover what
  they were pointed at, and coverage is the first thing the verdict rests on.
- Recording an unmeasured path as a pass. Nothing was measured, so there is
  nothing to pass; the output has to carry an unmeasured state of its own.
- Judging a continuity reading without its instrument resolution. A one ohm
  resolution cannot find a joint that added two hundred milliohms, and the
  reading inside the band then describes the meter.
- Taking an insulation reading below the barrier's rating and calling it a
  proof. The barrier was never taken to the level it has to survive.
- Treating indeterminate as a fail. It is a gap in the evidence, and it is
  closed by re-measuring with a better instrument, not by a repair.
- Treating indeterminate as a pass. That is the same gap, closed by nobody.
- Letting a coarse instrument excuse a clear defect. Poor discrimination
  withholds a healthy verdict only; a reading far outside the band is real.
- Comparing a measurement with a derived band by bare arithmetic. Every band
  here is a product of a criteria fraction and an expected value, so a
  measurement exactly on a band edge can evaluate a few units in the last
  place outside it; the comparison absorbs that representation error while the
  band stays untouched.

## Behavior contract (gate 3)

The per-kind check assessors, the discrimination ratio, the indeterminate
downgrade, the proof-voltage rule, path and barrier coverage, the coverage
fraction and the assembly outcome rollup are exercised by the gate 3 contract
test: scripts/test_e2008_electrical_health_check_purpose.py against
scripts/e2008_electrical_health_check_purpose_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_electrical_health_check_purpose.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
