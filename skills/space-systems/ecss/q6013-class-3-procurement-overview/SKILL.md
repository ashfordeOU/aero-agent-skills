---
name: q6013-class-3-procurement-overview
description: "Use when a light commercial buy has to become a purchasing verdict before the order goes out. Assess whether the purchasing controls around a commercial EEE order reach the rigour the lowest assurance class asks for under ECSS-Q-ST-60-13C clause 6.3.1: refuse an undeclared supply channel, size the control register and each control's rigour minimum from that channel, demote an undocumented claim to a supplier declaration, separate a control below its minimum from one never performed, credit a short control by the rigour ratio, take the purchasing assurance index against the declared floor, and report a declaration the register does not carry. Trigger: ecss, q-st-60-13c-clause-6-3-1, class-three-purchasing-control-rigour, commercial-order-supply-channel-register, purchasing-claim-evidence-demotion, purchasing-assurance-index-floor, class-three-procurement-verdict."
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
  tags: [ecss, q-st-60-13-commercial-eee-component-scope, q-st-60-13c, q6013-class-3-procurement-overview, q-st-60-13c-clause-6-3-1, class-three-purchasing-control-rigour, commercial-order-supply-channel-register, purchasing-claim-evidence-demotion, purchasing-assurance-index-floor, class-three-procurement-verdict]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE -- Class 3 Procurement Overview (space-systems/ecss/q6013-class-3-procurement-overview)

Use when the task is clause 6.3.1 of ECSS-Q-ST-60-13C at the lowest assurance
class: commercial electrical, electronic and electromechanical parts are being
bought on an ordinary commercial order, and the question is which purchasing
controls have to ride on that order and how hard each of them has to have been
worked before the buy can be called controlled.

## Domain quick reference

- Nothing about a commercial transaction makes it a controlled buy. At the
  classes above, the supplier arrangement carries most of the chain of
  custody; here the order is the only instrument the project holds, so the
  grading runs on the rigour each control actually reached rather than on
  whether somebody was named against it.
- Rigour is a ladder of four positions: not performed, declared by the
  supplier, recorded by the project, verified by the project. Every control in
  the register carries a minimum position, and a control is met when it sits
  at or above that minimum. A control sitting below it is a different repair
  from one nobody performed, so the two are separated rather than pooled.
- The rigour minimum is not uniform. Fixing the part number and variant,
  holding one manufacturer per part type across the build, requesting a date
  code band and keeping a receipt record are recorded by the project; the
  packaging and electrostatic condition may rest on the supplier's own
  statement, because the maker is the party who knows how the reel was sealed.
- The supply channel sizes the register and sets the minima it adds, because
  the channel decides where the manufacturer's own custody stops. A direct
  order adds nothing. An authorized distributor adds the authorization check
  at the order date, not at some earlier audit. An independent distributor
  adds origin evidence and a counterfeit avoidance screen, the screen verified
  rather than recorded. An open-market broker adds those two plus an
  authenticity check on receipt and a recorded acceptance of the source risk.
- An undeclared channel cannot be graded at all, and defaulting it to the
  direct route grades the riskiest order most leniently, so the correct
  response is to refuse rather than assume.
- A claim of recorded or verified rigour that cites no evidence is an
  assertion, and an assertion is worth no more than a supplier declaration.
  The demotion is what stops a register filled in from memory reading like one
  a reviewer could walk. The demotion is reported in its own right, because
  the repair is a document reference rather than more work.
- A short control is credited by the ratio of the position reached to the
  position required, which is why an order two-thirds of the way up a verified
  control does not read the same as one that never started it.
- The index is an aggregate and does not close the assessment. A single
  unperformed traceability control can sit under a comfortable figure and
  still be the defect that stops the delivery. A figure landing exactly on the
  floor is admissible, the tolerance absorbing representation error rather
  than widening the floor.

## Workflow

1. Validate the assurance policy: the floor the purchasing assurance index has
   to reach. A floor of nothing is refused rather than used.
2. Validate the declared supply channel and refuse an undeclared or
   unrecognized one; do not default it to the direct route.
3. Build the register for that channel: the base controls at their class 3
   minima plus the controls and minima the channel adds.
4. Validate each declaration -- the control, a rigour position on the ladder,
   an optional evidence reference -- and reject a control declared twice.
5. Take the effective rigour of each declaration, demoting a recorded or
   verified claim with no evidence reference to a supplier declaration.
6. Grade every control in the register as met, short of its minimum carrying
   the position it reached, or not performed, crediting a short control by the
   rigour ratio and a met control at one.
7. Record any declaration naming a control outside the register as its own
   finding.
8. Take the met share and the purchasing assurance index, compare the index
   with the floor under a named tolerance, and close on one verdict --
   purchasing controls not declared, control not performed, control below its
   required rigour, assurance below the declared floor, or controls meet class
   3 expectations -- carrying every finding, not the first.

## Pitfalls

- Grading a broker order against the direct-order register. The four extra
  controls are exactly what the open route removes from the manufacturer's
  side, so omitting them grades the riskiest channel most leniently.
- Defaulting an undeclared channel. The channel is the input that sizes the
  register, so guessing it silently picks which controls are never asked for.
- Reading a named owner as a discharged control. At this class the question is
  how far the control was worked, not who it was allocated to, and an
  unevidenced claim is the one that survives to the delivery review.
- Treating every control as needing project verification. Holding the
  packaging statement to a verified standard spends the little effort this
  class has on the control the supplier was always going to answer best.
- Pooling a short control with an unperformed one. One needs a document, the
  other needs the work doing, and a single open list hides which.
- Crediting a control above its minimum as more than met. The extra rigour is
  free to give and must not buy down a control that is short elsewhere.
- Reading a met index as a clean order. The index is an aggregate; an
  unperformed origin control sits comfortably inside a good figure.
- Widening the floor to pass an exact-equality case. An equality at the floor
  is a representation question handled by the tolerance inside the comparison.

## Behavior contract (gate 3)

The assurance-policy validation, supply-channel validation, register and
rigour-minimum construction per channel, declaration validation, the
no-evidence demotion, per-control grading with its rigour ratio, the
extraneous-declaration finding, the met share and purchasing assurance index,
the floor comparison and the overall verdict are exercised by the gate 3
contract test: scripts/test_q6013_class_3_procurement_overview.py against
scripts/q6013_class_3_procurement_overview_logic.py (stdlib unittest,
offline). Run: python3 scripts/test_q6013_class_3_procurement_overview.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
