---
name: q6012-design-principles-general-provisions
description: "Determine whether an MMIC design effort holds its baseline conditions at every stage. Use when ECSS-Q-ST-60-12C clause 7.1.2 general provisions are established or audited: validate the declared specification-to-freeze stage order, map each mandatory provision — process-kit currency, model validity band, thermal derating baseline, layout rule compliance, radiation baseline, lifetime baseline — onto the stage it applies from, build the provision-by-stage coverage matrix, name the first stage where one lapses or was never assessed, then check the operating band against the validated model span and the junction temperature against its derating limit. Refuses an unknown or out-of-order stage. Trigger: ecss, q-st-60-12c-clause-7-1-2, mmic-design-baseline-provisions, mmic-design-stage-coverage-matrix, process-design-kit-currency, mmic-model-validity-band, mmic-junction-derating-baseline, mmic-provision-lapse-stage."
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
  tags: [ecss, q-st-60-12-mmic-design-scope, q6012-design-principles-general-provisions, mmic-design-baseline-provisions, mmic-design-stage-coverage-matrix, process-design-kit-currency, mmic-model-validity-band, mmic-junction-derating-baseline, mmic-provision-lapse-stage]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS MMIC Design — Baseline General Provisions (space-systems/ecss/q6012-design-principles-general-provisions)

Use when the task is the general-provisions branch of ECSS-Q-ST-60-12C
clause 7.1.2 — establishing, or auditing, the baseline conditions that
have to hold across the whole of a microwave circuit design effort
rather than at one milestone, and saying where the baseline was lost
when it was not held.

## Domain quick reference

- The clause is about conditions that persist, not about a review item.
  A provision that held at the architecture review and was never
  re-established after a process-kit revision has lapsed, even though
  every review minute records it as met. The unit of assessment is
  therefore the provision-by-stage cell, not the provision.
- Six baseline provisions carry the effort. Process-design-kit currency,
  the radiation environment baseline and the lifetime baseline apply
  from specification onward, because they size the circuit before there
  is a circuit. Model validity band and the thermal derating baseline
  apply from architecture, when there is something to predict. Layout
  rule compliance applies from layout. A provision declared at a stage
  before the one it applies from is not evidence of anything; it is
  simply outside that provision's span.
- A cell has four possible states and the difference between two of them
  matters. Not-held is an assessed failure; undeclared is an applicable
  stage that was never assessed at all. Collapsing undeclared into
  not-held loses the fact that nobody looked, which is the finding a
  reviewer acts on.
- The first lapse, not the freeze milestone, is the reportable stage. A
  provision that fails from schematic design onward was lost there, and
  naming the freeze as the failure point sends the rework to the wrong
  place.
- Two of the baseline conditions are numeric and are graded rather than
  declared: the operating band has to sit inside the span the process
  models were validated over, and the predicted junction temperature has
  to sit inside the derating limit. A design sitting exactly on either
  bound is compliant; the equality is a representation question absorbed
  by a named tolerance, never by moving the limit.
- Optional provisions are carried and reported but do not decide the
  baseline. Only the mandatory set, plus the two numeric conditions,
  decide whether a baseline exists.

## Workflow

1. Validate the declared stage sequence against the canonical
   specification, architecture, schematic-design, layout, verification,
   design-freeze order. An unknown stage name, a duplicate, or a
   sequence out of order is an input error and stops the assessment; it
   is never silently sorted.
2. Validate each declared provision: its identifier, the stage it
   applies from, whether it is mandatory, its held or not-held status at
   each stage assessed, and an evidence reference. A known baseline
   provision infers its own entry stage; an extra provision has to
   declare one.
3. Build the coverage matrix, giving every provision-stage cell one of
   not-applicable, held, not-held or undeclared. Declarations that fall
   before a provision's entry stage are outside its span and do not
   become findings.
4. Take, per provision, the earliest applicable stage whose state is
   not-held or undeclared. That is the first lapse and it is the stage
   reported, whatever later stages say.
5. Grade the two numeric conditions: the operating band against the
   validated model span, and the junction temperature against the
   derating limit, each with the representation tolerance applied at the
   bound.
6. List the mandatory provisions that were never declared for any stage
   at all, and the mandatory provisions carrying no evidence reference.
7. Report the baseline as established only when no mandatory provision
   is missing, none has lapsed, the band is inside the model span and
   the junction temperature is inside the derating limit; otherwise
   return the findings that say which of those four failed.

## Pitfalls

- Grading a provision once and carrying the verdict forward. The clause
  puts the condition across the effort, so a provision is assessed at
  each applicable stage; a single early pass is not a baseline.
- Reading undeclared as held because nothing was reported against it.
  Silence is the undeclared state, and it is a finding in its own right,
  not an absence of one.
- Reporting the freeze milestone as the failure point. The lapse stage
  is where the rework belongs, and it is usually several stages earlier.
- Treating a status entered at a stage before the provision applies as
  evidence. Layout rule compliance at architecture says nothing, because
  there is no layout to comply; the cell is not-applicable.
- Letting a comfortable band or thermal number stand in for the
  provisions. The two numeric conditions are necessary, never
  sufficient; a design inside the model span with three undeclared
  provisions has no baseline.
- Widening the derating limit or the model span to clear an exact
  equality. The boundary case is absorbed by the named tolerance inside
  the comparison; the limits stay as specified.

## Behavior contract (gate 3)

The stage-sequence validation, provision validation, coverage matrix,
first-lapse selection, band-coverage and derating-margin grading,
missing-provision detection and the overall baseline verdict are
exercised by the gate 3 contract test:
scripts/test_q6012_design_principles_general_provisions.py against
scripts/q6012_design_principles_general_provisions_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_q6012_design_principles_general_provisions.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
