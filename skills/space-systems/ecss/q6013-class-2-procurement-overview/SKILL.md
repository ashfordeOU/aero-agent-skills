---
name: q6013-class-2-procurement-overview
description: "Assess whether the purchasing controls around a commercial EEE buy deliver parts matching intermediate assurance expectations under ECSS-Q-ST-60-13C clause 5.3.1: refuse an undeclared or unrecognized supply channel, size the control register from that channel, credit a control delegated to the supplier only where a flow-down clause and a returned certificate are both cited, hold an assigned but unevidenced control open with its reason, report an assignment the register does not carry, and take the weighted coverage against the declared floor. Use when a purchasing route has to be graded before parts are ordered. Trigger: ecss, q-st-60-13c-clause-5-3-1, class-two-purchasing-control-register, commercial-part-supply-channel-register, supplier-delegated-control-credit, purchasing-control-evidence, purchasing-coverage-floor."
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
  tags: [ecss, q-st-60-13-commercial-eee-component-scope, q6013-class-2-procurement-overview, q-st-60-13c-clause-5-3-1, class-two-purchasing-control-register, commercial-part-supply-channel-register, supplier-delegated-control-credit, purchasing-control-evidence, purchasing-coverage-floor]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE Components -- Class 2 Procurement Overview (space-systems/ecss/q6013-class-2-procurement-overview)

Use when the task is the clause 5.3.1 purchasing question of ECSS-Q-ST-60-13C
at the intermediate assurance class: a buy of commercial electrical,
electronic and electromechanical parts is being set up or reviewed, and the
question is which controls have to sit around it so that what arrives matches
what the class expects, and who is answerable for each of them.

## Domain quick reference

- The buy is graded on the controls around it, not on the parts alone. Four
  controls ride on every purchase whatever the source: the part requirements
  are stated on the order, the supplier is approved for that supply, the
  delivery is verified against the order, and lot traceability is recorded.
- The supply channel sizes the rest of the register, because the channel
  decides how much of the manufacturer's own chain of custody the buy
  inherits. A direct purchase inherits all of it and adds nothing. A
  franchised distributor adds one control: the franchise status held at the
  order date, not at some earlier audit. An independent distributor inherits
  none of it and adds two: rebuild traceability back to the manufacturer, and
  screen against counterfeit supply. An open-market broker adds those two plus
  an authenticity test on receipt and an explicit acceptance of the source
  risk by the project.
- An undeclared channel cannot be graded at all. The register it has to meet
  is unknown, and defaulting it to the direct route grades the riskiest buy
  most leniently, so the correct response is to refuse rather than assume.
- This class permits a control to be delegated to the supplier, which the
  class above does not. Delegation counts only where both halves are present:
  the flow-down clause the control was imposed under, and the certificate that
  came back against it. A clause with no certificate is an instruction nobody
  answered; a certificate with no clause is a document nobody asked for.
- A delegated control is credited below one. The credit is what stops a buy
  assembled entirely out of supplier certificates reading the same as one the
  project verified itself, and the pair of figures — covered share and
  weighted coverage — is what a reviewer needs to see the difference.
- A control held by the project is discharged only when a named owner inside
  the arrangement cites evidence. Unassigned, owned by a party with no
  standing, and assigned with no evidence are three different repairs, so the
  reason travels with the open control.
- An assignment naming a control the register does not carry is a signal in
  its own right: either the channel was recorded wrongly, or the buy is
  working to a register other than the declared one.
- Coverage meeting its floor does not close the assessment, and an open
  control is a finding whether or not the remaining controls carry the buy
  over the declared share. A figure landing exactly on the floor is
  admissible, the tolerance being there to absorb representation error rather
  than to widen the floor.

## Workflow

1. Validate the coverage policy: the declared coverage floor and the credit a
   delegated control earns. A credit of nothing or of one is refused rather
   than used.
2. Validate the declared supply channel and refuse an undeclared or
   unrecognised one; do not default it to the direct route.
3. Build the control register for that channel: the base controls plus the
   controls the channel adds.
4. Validate each assignment: normalise the control and the owner, accept a
   string evidence reference, flow-down clause and supplier certificate, and
   reject a control assigned twice.
5. Grade every control in the register as held by the project, delegated to
   the supplier at the credited weight, or open carrying its reason —
   unassigned, owner without standing, no evidence cited, delegated under no
   flow-down clause, or delegated with no certificate returned.
6. Record any assignment naming a control outside the register as its own
   finding.
7. Take the covered share and the weighted coverage of the register and
   compare the weighted figure with the floor under a named tolerance.
8. Close on one verdict: purchasing controls not established, purchasing
   control open, purchasing coverage below the declared floor, or purchasing
   controls meet class 2 expectations — carrying every finding, not the first.

## Pitfalls

- Grading an open-market buy against the direct-purchase register. The four
  extra controls are exactly what the open route removes from the
  manufacturer's side, so omitting them grades the riskiest channel most
  leniently.
- Defaulting an undeclared channel. The channel is the input that sizes the
  register, so guessing it silently picks which controls will never be asked
  for.
- Treating a supplier certificate as a delegation. Without the flow-down
  clause behind it nobody can say what the certificate was issued against, and
  the scope of what the supplier actually accepted is unrecoverable at the
  delivery review.
- Crediting a delegated control in full. Delegation is permitted here and it
  is thinner than verifying the control, which is what the credit records;
  without it a buy of pure certificates scores as a controlled buy.
- Treating an assignment as a discharge. Naming an owner moves the control to
  somebody; it does not evidence that the control was exercised, and the
  unevidenced case is the one that survives to the delivery review.
- Reading a met coverage floor as a clean buy. The floor is an aggregate; a
  single open traceability control can sit under a comfortable figure and
  still be the defect that stops the delivery.
- Stopping at the first open control. The buyer needs the whole open list to
  close it in one pass rather than one review round each.

## Behavior contract (gate 3)

The coverage-policy validation, supply-channel validation, register
construction per channel, assignment validation, per-control grading with its
reason, the delegation credit, extraneous-assignment detection, the covered
share and weighted coverage, the floor comparison and the overall verdict are
exercised by the gate 3 contract test:
scripts/test_q6013_class_2_procurement_overview.py against
scripts/q6013_class_2_procurement_overview_logic.py (stdlib unittest,
offline). Run: python3 scripts/test_q6013_class_2_procurement_overview.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
