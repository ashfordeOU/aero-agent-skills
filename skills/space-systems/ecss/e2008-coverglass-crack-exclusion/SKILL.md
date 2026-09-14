---
name: e2008-coverglass-crack-exclusion
description: "Use when a coverglass visual record has to support a delivery decision. Assess a coverglass inspection record against clause 8.7.1.3.6 of ECSS-E-ST-20-08C, which permits no cracking at all: sort every recorded indication into a crack family, a non-crack family or neither, reject the glass on any crack of the surface, an edge or a corner whatever its length, route a non-crack mark to the clause that does bound it, refer one nobody has named, and certify absence only where the record shows all three zones were examined at or above the declared magnification and light. Trigger: ecss, e-st-20-08c, coverglass-crack-exclusion, coverglass-zero-crack-tolerance, coverglass-inspection-coverage, coverglass-surface-edge-corner-cracking, solar-cell-coverglass-crack-screen."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-coverglass-crack-exclusion, e-st-20-08c, coverglass-crack-exclusion, coverglass-zero-crack-tolerance, coverglass-inspection-coverage, coverglass-surface-edge-corner-cracking, solar-cell-coverglass-crack-screen]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic — Coverglass Crack Exclusion (space-systems/ecss/e2008-coverglass-crack-exclusion)

Use when the task is clause 8.7.1.3.6 of ECSS-E-ST-20-08C: cracking of the
surface, an edge or a corner of a delivered coverglass. This leaf reads one
inspection record and returns a disposition per indication, a judgement on
whether the look itself can support a statement of absence, and the glass
verdict that follows from both.

## Domain quick reference

- There is no allowance here. Every neighbouring coverglass clause is a
  dimension with a limit against it; this one is a prohibition, so no
  length exists below which a crack becomes acceptable and no zone exists
  in which one is tolerated.
- That changes the work. A clause with a limit is answered by measuring; a
  clause without one is answered by categorizing, and then by proving the
  look was good enough for an empty result to mean anything.
- Crack length is still recorded, for the nonconformance paperwork and for
  the failure analysis that follows. It is recorded and not graded, and a
  screen that lets a short crack through has misread the clause.
- A crack answers to several names. Fracture, fissure, hairline and star
  cracking are all the same finding for this clause, and a screen matching
  only the word crack passes glass that is cracked.
- A non-crack indication is not this clause's work. A chip belongs to the
  chip clauses and a scratch to the surface quality clauses, so it is
  routed on rather than absorbed here, where absorbing it would silently
  accept a feature this clause never graded.
- A mark nobody has named is neither. It is an open question, and an open
  question is not an absence, so it is referred for re-examination rather
  than defaulted into the harmless family.
- The inspection itself is graded. A record covering two zones cannot
  certify the third, and one taken below the declared magnification or
  under too little light is evidence that nothing was seen rather than
  that nothing was there.
- Weak evidence never softens a rejection. A crack found under a poor look
  is still a crack; thin evidence only blocks an acceptance.
- An indication recorded in a zone the same record says was not examined
  is a contradiction in the paperwork, and it is settled before any
  disposition is taken from that record.

## Workflow

1. Validate the record: glass identity, inspector, magnification,
   illumination, the zones examined and the indications listed. Reject a
   zone name or a repeat that the record should not contain.
2. Grade the evidence: compare the zones examined with the zones required,
   the magnification with its floor and the light with its floor, and
   record every shortfall separately.
3. Normalize each indication's kind and sort it into the crack family, the
   non-crack family or neither.
4. Reject the glass on any crack-family indication, in any zone, at any
   length; route each non-crack indication to its own clause; refer each
   unresolved one.
5. Refuse an indication whose zone the record says was not examined.
6. Escalate on unresolved marks beyond the allowance and on every evidence
   shortfall, and let a rejection stand above both.
7. Return the verdict with the cracked zones, the family counts, the
   longest recorded crack and the evidence judgement attached.

## Pitfalls

- Looking for a length threshold. There is none, and inventing a small one
  is the single failure this clause exists to prevent.
- Matching only the word crack. Fracture, fissure, hairline and star
  cracking are the same finding under other names.
- Reading an empty finding list as a pass. It is a pass only where the
  record also shows the look was complete and good enough to see a
  hairline.
- Certifying a zone nobody examined. Two zones out of three is an
  inconclusive record, not a clean one.
- Accepting an inspection taken at low power. A hairline crack is not
  resolved at four times magnification, so the record says only that it
  was not seen.
- Defaulting an unrecognised mark into the harmless family. Unresolved is
  its own answer and it blocks certification.
- Letting weak evidence soften a rejection. Evidence quality gates an
  acceptance and never a rejection.
- Absorbing a chip or a scratch into this screen. Each has its own clause
  with its own allowance, and grading it here accepts it against no limit
  at all.
- Comparing a magnification or an illumination reading with its floor by
  bare arithmetic. A decimal reading entered from a certificate can
  evaluate a few units in the last place below the figure it was meant to
  be; the comparison absorbs that representation error while the floor
  stays untouched.

## Behavior contract (gate 3)

The record validation, the evidence grading over zone coverage,
magnification and illumination, the kind normalization and the crack,
non-crack and unresolved families it feeds, the length-independent
rejection in every zone, the routing of non-crack marks to their own
clauses, the uninspected-zone contradiction, the unresolved allowance and
the verdict rollup that lets a rejection stand above thin evidence are
exercised by the gate 3 contract test:
scripts/test_e2008_coverglass_crack_exclusion.py against
scripts/e2008_coverglass_crack_exclusion_logic.py (stdlib unittest,
offline). Run: python3 scripts/test_e2008_coverglass_crack_exclusion.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
