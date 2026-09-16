---
name: q6013-class-3-incoming-inspection
description: "Use when a delegated receipt has to become a disposition. Determine whether the receiving inspection of a lowest assurance commercial EEE delivery may rest on a source inspection at the supplier premises under ECSS-Q-ST-60-13C clause 6.3.7: test the delegation claim against surveillance audit currency, a signed source report and the criteria that report actually covers, refuse delegation for a part family this category keeps at the dock, size the source sample in exact integer arithmetic, run the residual dock duties no delegation removes, and return released, dock inspection required or quarantined with every reason named. Trigger: ecss, q-st-60-13c-clause-6-3-7, class-three-incoming-inspection, supplier-premises-source-inspection, surveillance-audit-currency, source-report-criteria-coverage, residual-dock-verification, class-three-receipt-disposition."
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
  tags: [ecss, q-st-60-13-commercial-eee-component-scope, q-st-60-13c, q6013-class-3-incoming-inspection, class-three-incoming-inspection, supplier-premises-source-inspection, surveillance-audit-currency, source-report-criteria-coverage, residual-dock-verification, class-three-receipt-disposition]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE -- Class 3 Incoming Inspection (space-systems/ecss/q6013-class-3-incoming-inspection)

Use when the task is the clause 6.3.7 receiving inspection of
ECSS-Q-ST-60-13C at the lowest assurance category: a delivery of
commercial parts has arrived, the inspection behind it may have been
performed at the supplier's own premises rather than at the receiving
dock, and the question is whether that stands, what still has to be done
on arrival, and where the delivery goes.

## Domain quick reference

- The relaxation this category grants is where the inspection happens,
  not whether it happens. A source inspection at the supplier premises
  can stand in for the receiving organisation's own look at the parts,
  and everything turns on whether the claim behind that substitution
  holds.
- A delegation claim rests on four separate things and fails on any one.
  The surveillance audit behind the supplier has to still be current, a
  source inspection report has to actually exist, it has to be signed by
  someone accountable, and it has to speak to every criterion the
  delivery is judged on.
- Coverage is per criterion, not per report. A report that examined the
  external visual condition and the marking but never looked at the lead
  condition leaves that criterion unexamined, and a delivery cannot be
  released on an inspection that did not take place.
- Some families never leave the dock. A hybrid, a high-voltage part or a
  custom device has failure modes a supplier's routine inspection does
  not look for, so the category keeps them for the receiving
  organisation whatever report is offered.
- Four duties survive every delegation: the package arrives intact, the
  identity matches, the quantity matches, and the documents travelled
  with the parts. These are about the box that arrived, not the parts a
  supplier inspected weeks earlier, and nobody else can do them.
- Sample size is a percentage of the delivered quantity, rounded up,
  raised to a floor for small lots and capped for large ones. Integer
  arithmetic throughout, so the same delivery gives the same sample on
  every machine that runs it.
- There are three destinations, not two. A refused delegation is not a
  rejected delivery: it means the receiving organisation now owes the
  full dock inspection it thought it had been spared. Only a residual
  failure or a sample beyond its accept number holds the parts.

## Workflow

1. Decide the delegation claim first: family, audit currency, report
   presence, report signature and criterion coverage, keeping every
   refusal reason rather than stopping at the first.
2. Size the source sample from the delivered quantity with the integer
   percentage plan, applying the declared floor and cap and clamping to
   the lot.
3. Judge the defects the source report records against the sample's
   accept number; accept-on-zero is the default and a higher accept
   number is declared rather than assumed.
4. Run the residual dock duties on the delivery as it actually arrived,
   treating an omitted duty as an unsatisfied one and refusing a duty
   name outside the register.
5. Dispose on the three outcomes: quarantine when a residual duty failed
   or the source sample was beyond its accept number, dock inspection
   required when the delegation did not stand, release to stores only
   when nothing was found.

## Pitfalls

- Reading the source report as proof and stopping there. The report is
  the claim under test, not the evidence that settles it; an unsigned
  report for a supplier whose audit lapsed is a piece of paper.
- Treating a refused delegation as a rejected delivery. The parts may be
  perfectly good; what failed is the substitution, and the answer is an
  inspection at the dock rather than a return to the supplier.
- Letting delegation absorb the residual duties. A supplier cannot
  inspect the crate that a courier dropped, and identity and quantity
  are reconciled against the order at the point the boxes are opened.
- Sizing the sample from the ordered quantity. The sample is drawn from
  what arrived, so a short delivery is sampled as the smaller lot it is.
- Accepting partial criterion coverage because most of the report looks
  thorough. The criterion nobody examined is the one that ships.
- Moving the audit validity limit so an audit sitting exactly on it
  passes. A value on its limit is inside it, and the representation
  error at that boundary is absorbed by the tolerance inside the
  comparison rather than by widening the limit.

## Behavior contract (gate 3)

The surveillance currency check, source-report criterion coverage, the
non-delegable family register, the delegation decision, integer sample
sizing, the source accept-number verdict, the residual dock duties and
the three-way disposition are exercised by the gate 3 contract test:
scripts/test_q6013_class_3_incoming_inspection.py against
scripts/q6013_class_3_incoming_inspection_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6013_class_3_incoming_inspection.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
