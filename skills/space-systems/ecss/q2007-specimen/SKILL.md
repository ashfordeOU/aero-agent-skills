---
name: q2007-specimen
description: "Assess the control a test centre keeps over a customer's test item under ECSS-Q-ST-20-07C clause 5.7.4.3: work the receipt inspection, confirm the item carries a marking unique inside the centre's register, compare the as-received build against the configuration the customer declared, weigh it against the declared mass within its allowance, list the accompanying documents that did not arrive, walk the custody chain for a handover whose receiving holder does not match the next holder, and return accept, accept against a nonconformance, or quarantine. Use when a customer item arrives at a test centre or its intake record is being audited. Trigger: ecss, q-st-20-07c-clause-5-7-4-3, test-specimen-receipt-inspection, test-specimen-unique-identification, as-received-configuration-recording, test-specimen-custody-chain, test-specimen-disposition."
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
  tags: [ecss, q-st-20-07-test-centre-scope, q2007-specimen, test-specimen-receipt-inspection, test-specimen-unique-identification, as-received-configuration-recording, test-specimen-custody-chain, test-specimen-disposition]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Test Centres -- Control of the Test Specimen (space-systems/ecss/q2007-specimen)

Use when the task is the specimen-control clause of ECSS-Q-ST-20-07C
clause 5.7.4.3 -- what a test centre does the moment a customer's item
crosses its door: inspect it on receipt, give it an identity that cannot
be confused with anything else in the building, record the state it
arrived in, and keep custody of it until it leaves.

## Domain quick reference

- The item belongs to the customer throughout. The centre's obligation
  is custody and evidence, not ownership, so anything found on receipt
  is reported rather than absorbed, and the receipt record is what the
  customer is later shown.
- Identification has to be unique inside the centre, not just present.
  Two items marked with the same customer part number are one mix-up
  away from a test report about the wrong object, so the register the
  centre keeps is what makes a marking an identity.
- The as-received configuration is recorded because it is not
  necessarily the declared one. A late modification, a substituted
  bracket or a different harness dress can all reach the centre without
  reaching the paperwork, and recording the build found is what makes
  the difference visible before the specimen is loaded.
- Mass is the cheapest independent check on configuration there is. An
  item inside its declared mass allowance is weak evidence that the
  build matches; one outside it is strong evidence that something was
  added or left off, and either way the figure costs a minute.
- Accompanying documents are part of the item. A specimen without its
  handling instruction or its declared-configuration list can be stored
  but not tested, because nothing says how it may be held or what it is
  supposed to be.
- Custody is a chain and a chain is only as good as its joins. Every
  handover names who released and who received; a join where the
  receiving name does not reappear as the next releasing name is a
  period the centre cannot account for.
- Disposition is graded. Damage or a broken chain quarantines the item;
  a paperwork or configuration discrepancy is accepted against a raised
  nonconformance so the work can proceed with the gap recorded.

## Workflow

1. Validate the intake record: a non-empty marking, declared and
   as-received configuration strings, real booleans for inspection,
   damage and packaging, and strictly positive masses and allowance.
2. Check the marking against the centre's register and report a
   duplicate or a placeholder marking.
3. Compare the as-received configuration with the declared one on
   normalised text so spacing and case do not manufacture a difference.
4. Compare the weighed mass with the declared mass against its
   allowance, absorbing float representation error at the allowance
   with a named tolerance.
5. List the required accompanying documents that did not arrive.
6. Walk the custody events in time order, refusing an out-of-order
   event, and report every join where the receiving holder is not the
   next releasing holder.
7. Grade the findings into accepted, accepted against a nonconformance,
   or quarantined, and return the raised nonconformances separately.

## Pitfalls

- Treating the customer's part number as an identity. It names a type;
  the centre's own register entry names the object on the bench.
- Recording the declared configuration as the as-received one because
  they are expected to match. That is exactly the check being skipped,
  and it is the check that catches an undeclared modification.
- Accepting an item with broken packaging but no visible damage as
  undamaged. The packaging is the evidence that nothing happened in
  transit, so its loss is a finding in its own right.
- Letting a custody gap pass because the item is accounted for at both
  ends. The gap is the period nobody can speak for, and the ends say
  nothing about it.
- Reading a mass exactly on the allowance as out of tolerance. That is
  the allowance being met; the comparison absorbs float representation
  error rather than tightening the allowance.

## Behavior contract (gate 3)

The intake validation, register-based identification check,
configuration comparison, mass check, missing-document list, custody
chain walk and the graded disposition are exercised by the gate 3
contract test: scripts/test_q2007_specimen.py against
scripts/q2007_specimen_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q2007_specimen.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
