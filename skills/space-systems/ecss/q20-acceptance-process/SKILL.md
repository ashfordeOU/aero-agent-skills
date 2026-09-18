---
name: q20-acceptance-process
description: "Execute the acceptance and delivery decision of ECSS-Q-ST-20C clause 5.7.1 from the evidence rather than from the delivery date: grade the verification register so a requirement called verified carries evidence and anything short of verified rests on an approved, attributed deviation or waiver, block on an open critical nonconformance and on lesser ones whose disposition is unapproved, check every mandatory acceptance hold point is signed by the party that owns it, and return accept, conditional accept against named concessions, or reject. Use when a product is presented for acceptance or a delivery is being contested. Trigger: ecss, q-st-20c-clause-5-7-1, product-acceptance-criteria, acceptance-hold-point-signature, requirement-verification-register, deviation-waiver-concession, delivery-compliance-fraction."
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
  tags: [ecss, q-st-20-quality-assurance-scope, q20-acceptance-process, product-acceptance-criteria, acceptance-hold-point-signature, requirement-verification-register, deviation-waiver-concession, delivery-compliance-fraction]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Quality Assurance -- Acceptance and Delivery (space-systems/ecss/q20-acceptance-process)

Use when the task is the acceptance and delivery process of
ECSS-Q-ST-20C clause 5.7.1: a product is offered for acceptance and the
question is whether the evidence in front of the acceptance authority
actually supports handing it over, holding it, or handing it over
against named concessions.

## Domain quick reference

- Acceptance rests on the verification register, not on the schedule.
  Each requirement carries the method it was verified by, the state that
  verification reached, and the reference to the evidence. A requirement
  marked verified with no evidence reference is the most common defect
  in an acceptance package, because it reads as green in every summary.
- Anything short of full verification needs a concession, and a
  concession is three things: it exists, it is approved, and the
  approver is named. Any one of the three missing turns the shortfall
  back into an open requirement. A concession cited by a requirement but
  absent from the concession register is a bookkeeping failure that
  usually means two documents were maintained separately.
- Severity decides what an open nonconformance does to the delivery. An
  open critical nonconformance blocks whatever paperwork accompanies it;
  a lesser one is survivable only with a disposition that has actually
  been approved. An open nonconformance with no disposition at all is
  the same as no answer.
- Acceptance hold points have owners. The physical configuration audit
  and the pre-delivery review belong to product assurance; the
  acceptance review belongs to the customer. A signature by the wrong
  party is not a signature, because the point of the gate is who agreed,
  not that somebody did.
- The outcome has three values, not two. Conditional acceptance exists
  precisely so that a product delivered against approved concessions is
  distinguishable from one delivered clean, and the carried concessions
  are named in the decision so they follow the product.

## Workflow

1. Normalise the verification register, rejecting a duplicate
   requirement, an unrecognised verification method or an unrecognised
   verification state before anything is graded.
2. Normalise the concession register and refuse a duplicate reference.
3. Grade each requirement: evidence behind a verified state; an
   approved, attributed concession behind anything else. Collect the
   concessions the delivery would carry.
4. Grade the open nonconformances by severity, blocking outright on an
   open critical one and on any lesser one whose disposition is absent
   or unapproved.
5. Grade the mandatory acceptance hold points for signature and for
   signature by the owning party.
6. Compute the compliance fraction over the register and decide:
   rejected when anything blocks, conditionally accepted when nothing
   blocks but concessions are carried, accepted otherwise.

## Pitfalls

- Reading a full compliance fraction as an acceptance. The fraction says
  how much of the register reached verification; an unsigned hold point
  or an open critical nonconformance rejects a delivery whose register
  is complete.
- Accepting a waiver because it is in the file. Approved and attributed
  are separate checks, and an unattributed approval cannot be traced to
  anybody who could have given it.
- Treating conditional acceptance as acceptance with a note. The carried
  concessions travel with the product and constrain how it may be used,
  so they belong in the decision record itself.
- Letting a delivery signature stand in for the hold point it did not
  cover. The owning party is part of the gate; a supplier signature on a
  customer acceptance review records that nobody from the customer
  agreed.
- Closing an open minor nonconformance by writing a disposition. The
  disposition also has to be approved, otherwise it is a proposal.

## Behavior contract (gate 3)

The register normalisation, the evidence rule on verified requirements,
the three-part concession rule, the severity-driven nonconformance
blocking, the hold-point ownership check, the compliance fraction and
the three-valued acceptance decision are exercised by the gate 3
contract test: scripts/test_q20_acceptance_process.py against
scripts/q20_acceptance_process_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q20_acceptance_process.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
