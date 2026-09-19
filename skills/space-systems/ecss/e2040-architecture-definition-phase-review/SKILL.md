---
name: e2040-architecture-definition-phase-review
description: "Determine whether architecture definition may close and detailed design plus verification work start, the gate ECSS-E-ST-20-40C clause 5.3.4 places there: grade each of the six exit criteria met, partially met or not met, refuse a criterion asserted with no evidence reference, treat a partial as carryable only while an action actually references it, and hold the gate when an action carried from the previous review is open past its due date. Use when an architecture review board is prepared or reconstructed. Trigger: ecss, e-st-20-electrical-scope, architecture-definition-phase-review, architecture-gate-exit-criteria, partial-criterion-without-action, carried-action-overdue, architecture-gate-authorisation."
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
  tags: [ecss, e-st-20-electrical-scope, e2040-architecture-definition-phase-review, architecture-definition-phase-review, architecture-gate-exit-criteria, partial-criterion-without-action, carried-action-overdue, architecture-gate-authorisation]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Device Requirements — Architecture Definition Phase Review (space-systems/ecss/e2040-architecture-definition-phase-review)

Use when the task is the gate duty of ECSS-E-ST-20-40C clause 5.3.4 --
deciding whether architecture definition is closed and detailed design,
with the verification work that runs beside it, may be authorised.

## Domain quick reference

- This gate is driven by exit criteria, not by a data-item package. Six
  of them are owed: the architecture documented, the partitioning
  justified, the verification plan updated, the validation plan updated,
  the budgets allocated and the interfaces agreed.
- A criterion the review never addressed is not a pass by omission. The
  minutes read identically either way, which is exactly why it has to be
  surfaced as a gap rather than inferred.
- A criterion asserted met with no evidence reference is a claim. It
  costs nothing to write and reads the same as a satisfied one at every
  later review.
- A partially met criterion is carryable only while an action actually
  references it. A partial with no action attached is a not-met with a
  softer word on it, and it converts into schedule debt silently.
- Actions do not vanish between gates. One carried from the definition
  review and still open past its due date says the previous gate's
  conditions were never honoured; authorising on top of it stacks two
  phases of debt into detailed design.
- An action raised at this gate already past its due date, or with no
  due date at all, is not an action.
- Satisfaction is a weighted count -- met one, partially met a half --
  over the six criteria owed, so it lands on a threshold only by
  arithmetic accident and the comparison absorbs that.

## Workflow

1. Fold every criterion entry onto one of the six owed and onto one of
   the three states, refusing a repeat or an unknown key.
2. Report each criterion the review did not address, and treat it as
   blocking rather than as a gap to note.
3. Report each not-met criterion as blocking, and each partially met one
   as carryable only when an action references that same criterion.
4. Report any criterion, at any state, carrying no evidence reference.
5. Check the actions raised here: an open action needs a due date, and
   that date has to fall after the gate.
6. Check the actions carried in from the previous review: one still open
   is carried forward, one open past its due date holds the gate.
7. Compute weighted satisfaction over the six criteria, compare it
   against any threshold absorbing representation error, and return the
   verdict: not-authorized on any blocking finding,
   authorized-with-actions when something is carried, otherwise
   authorized-to-proceed.

## Pitfalls

- Counting criteria that were addressed and calling that the
  satisfaction. The four criteria nobody discussed are the ones the gate
  exists to catch, and omitting them from the denominator makes an
  incomplete review score perfectly.
- Accepting a met criterion with no evidence. It survives every
  downstream review because nothing above it ever asks what it rested
  on.
- Reading a partial as a soft pass. Without an action against that
  specific criterion it is a not-met, and the phase closes over it.
- Ignoring actions carried from the previous gate. Each review then
  judges only its own phase, and the debt compounds invisibly across
  two of them.
- Comparing weighted satisfaction against its threshold with a strict
  inequality. A five-and-a-half over six division can sit a unit in the
  last place below the same figure written as a threshold and red a
  review that met its target.

## Behavior contract (gate 3)

The criterion and state folding, unaddressed-criterion detection,
evidence check, partial-versus-action rule, new and carried action
handling, open-action counting and the weighted satisfaction threshold
are exercised by the gate 3 contract test:
scripts/test_e2040_architecture_definition_phase_review.py against
scripts/e2040_architecture_definition_phase_review_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2040_architecture_definition_phase_review.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
