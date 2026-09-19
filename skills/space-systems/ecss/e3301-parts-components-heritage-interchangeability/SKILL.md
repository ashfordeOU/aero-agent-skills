---
name: e3301-parts-components-heritage-interchangeability
description: "Assess a heritage parts claim and the interchangeability of replaceable mechanism items against ECSS-E-ST-33-01 clauses 4.2.4.2 and 4.2.4.3. Use when a mechanism reuses previously qualified parts whose application environment differs from the one they were qualified to, or when a group of replaceable items is declared interchangeable on the bench. Forms an exceedance per environmental and duty parameter, separates an accepted heritage from a delta qualification and from a full requalification, and proves interchangeability by worst-case tolerance stack so no unit needs selective fit, shimming or match marking. Trigger: ecss, e-st-33-01, mechanism-part-heritage-qualification, qualification-envelope-exceedance, delta-qualification-decision, replaceable-item-interchangeability, worst-case-tolerance-stack, selective-fit-detection."
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
  tags: [ecss, e-st-33-mechanisms-scope, e3301-parts-components-heritage-interchangeability, mechanism-part-heritage-qualification, qualification-envelope-exceedance, delta-qualification-decision, replaceable-item-interchangeability, worst-case-tolerance-stack]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Mechanisms — Parts Heritage and Interchangeability (space-systems/ecss/e3301-parts-components-heritage-interchangeability)

Use when the task is clauses 4.2.4.2 and 4.2.4.3 of ECSS-E-ST-33-01 —
deciding whether a previously qualified part can be reused as it
stands, and whether a set of replaceable items is genuinely
interchangeable rather than merely similar.

## Domain quick reference

- A qualification is an envelope, not a badge. The part is qualified to
  specific temperatures, cycles, durations, loads and doses, and the
  question is always whether the new application sits inside that
  envelope, parameter by parameter. One parameter outside it is enough
  to make the heritage claim incomplete.
- Each parameter has a sense. Hotter is worse for an upper temperature
  bound; colder is worse for a lower one; more cycles, more load, more
  dose and lower ambient pressure are all worse. A comparison that
  ignores the sense reads a colder application as a benign one.
- How far outside matters. A part run ten percent past its qualified
  cycle count is an extension of existing evidence; a part run at twice
  the cycles is being used somewhere the evidence does not reach, and
  those are a delta qualification and a full requalification
  respectively.
- A parameter the qualification never addressed is not a small
  exceedance — it is the absence of evidence. There is no bound to
  compare against, so no amount of margin arithmetic converts it into a
  heritage claim.
- Interchangeability is a property of a population, not of a pair. It
  means any item of the group fits any mating feature, so the proof is
  a worst-case stack of the tightest hole against the loosest shaft,
  repeated across every combination.
- A fit can fail in both directions. Interference stops the item going
  in; excessive clearance lets it go in and lose the function it was
  there to provide, so the stack is checked against a ceiling as well
  as against zero.
- Selective fit, shimming and match marking are the three ways a bench
  makes non-interchangeable hardware work. Each of them means the
  replacement item is not a replacement: it is the one item that was
  fitted to that position.

## Workflow

1. Validate both envelopes: every parameter known to the sense table,
   every value a positive magnitude, temperatures in kelvin and
   pressures in pascal so the normalisation has a physical origin.
2. Compare parameter by parameter, forming the exceedance in the severe
   direction and the exceedance relative to the qualified bound.
   Absorb representation error at the envelope boundary with a named
   tolerance rather than by widening the bound.
3. Name the parameters the application exceeds and, separately, the
   parameters the qualification never covered.
4. Decide the route: a changed configuration or an uncovered parameter
   goes to a full requalification, a relative exceedance past the delta
   limit goes to a full requalification, any remaining exceedance to a
   delta qualification, and nothing left to accepted heritage.
5. For each interchangeable group, stack every item against every
   mating feature: the tightest clearance must not go negative and the
   loosest must not pass the ceiling the function allows.
6. Refuse the group outright when any item is marked for selective fit
   or carries a match mark, regardless of how the stack came out.
7. Report per-part verdicts, per-pair clearances, the fraction of parts
   reusable as they stand, and every finding.

## Pitfalls

- Reading a qualification as a pass rather than as an envelope. The
  part passed a specific test campaign; the heritage claim is only as
  wide as the conditions that campaign covered.
- Comparing a lower bound the wrong way round. A minimum-temperature
  qualification is beaten by a colder application, and an arithmetic
  comparison that assumes bigger is worse reports the coldest
  application as the safest.
- Treating an unqualified parameter as a zero exceedance. There is no
  bound, so the difference is undefined, and defaulting it to zero
  turns missing evidence into a clean result.
- Calling everything a delta qualification. A delta extends existing
  evidence into an adjacent condition; past a certain exceedance the
  failure mechanisms change and the earlier campaign no longer bounds
  anything.
- Proving interchangeability on the units in hand. Two items that both
  fit the one bracket on the bench say nothing about the tolerance
  extremes the drawing permits, which is what the next build will
  contain.
- Checking only for interference. A stack that cannot bind can still be
  loose enough to lose alignment, backlash or preload, so the loosest
  case needs a ceiling of its own.
- Accepting a shimmed or match-marked installation as interchangeable.
  The shim makes that item work in that position, which is the precise
  opposite of what a replaceable item has to do.

## Behavior contract (gate 3)

The envelope validation, sense-aware exceedance, heritage route
decision, dimensional feature validation, worst-case clearance stack
and the selective-fit and match-marking refusals are exercised by the
gate 3 contract test:
scripts/test_e3301_parts_components_heritage_interchangeability.py
against
scripts/e3301_parts_components_heritage_interchangeability_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e3301_parts_components_heritage_interchangeability.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
