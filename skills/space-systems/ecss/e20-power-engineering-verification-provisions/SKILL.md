---
name: e20-power-engineering-verification-provisions
description: "Use when determine how each electrical power engineering requirement of ECSS-E-ST-20C clause 5.11.1 is verified: categorize the power verification item as a budget, sizing, dynamic or protection item, check the proposed method can actually produce closure evidence for that item, confirm the planned review point is not earlier than the method can mature, prove the evidence represents every mandatory worst-case power condition including end-of-life degradation, maximum eclipse, worst-case solar aspect and the thermal corners, compute the demonstrated power margin from available against demanded power, and show the provision set covers every required item with no orphan. Trigger: ecss, e-st-20-electrical-scope, power-engineering-verification-provisions, power-budget-verification-evidence, energy-balance-verification-case, worst-case-power-condition, end-of-life-power-margin, power-verification-review-point."
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
  tags: [ecss, e-st-20-electrical-scope, e20-power-engineering-verification-provisions, power-engineering-verification-provisions, power-budget-verification-evidence, energy-balance-verification-case, worst-case-power-condition, end-of-life-power-margin, power-verification-review-point]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical Engineering -- Power Engineering Verification Provisions (space-systems/ecss/e20-power-engineering-verification-provisions)

Use when the task is the clause 5.11.1 verification provision of
ECSS-E-ST-20C -- saying, for each electrical power engineering
requirement, by which method it is verified, at which programme review
the evidence is presented, and which worst case of the power system
that evidence has to represent.

## Domain quick reference

- A power verification item belongs to exactly one engineering family:
  budget (power budget, energy balance, harness drop), sizing (solar
  array, battery capacity), dynamic (bus voltage stability) or
  protection (protection coordination). The family is what makes the
  provision checkable -- it fixes which methods can produce evidence
  and which worst case the evidence must show.
- The method set is not free choice. An energy balance closes on a
  computed prediction and nothing else; a solar array size can also
  close on a qualified precedent; a harness drop can close on a
  measured build standard; a bus stability claim needs either a
  small-signal prediction or a transient measurement, never a
  document review. A method outside the item's set is a finding
  against the provision, not a tailoring decision.
- Each method carries an earliest review at which its evidence is
  mature. A design review and a precedent argument rest on documents
  that exist at the preliminary baseline; a prediction closes against
  the detailed design baseline; a build-standard check needs
  manufactured hardware; a measurement needs a qualification-
  configuration model. A provision that promises closure before its
  method can physically deliver is a schedule risk written into the
  verification matrix.
- The distinctive power engineering content is the worst case. Every
  item names the conditions its evidence must represent: end-of-life
  degradation, the longest eclipse, the worst solar aspect angle, the
  hot and cold thermal corners, the largest load step, the maximum
  source impedance case, the worst-case fault current. A prediction
  run at beginning of life, nominal aspect and nominal temperature is
  not evidence for a requirement that governs the end of the mission.
- A budget or sizing item closes against a number: the margin is the
  surplus of available power over demanded power, expressed as a
  fraction of the demand, and it is compared against the margin the
  requirement demands. Because that margin is a difference of floats
  divided by a float, an exactly-satisfied requirement can land a few
  units in the last place low; the comparison absorbs the
  representation error rather than moving the engineering limit.

## Workflow

1. Categorize each verification item into its family; reject an item
   that is not a clause 5.11.1 power engineering item before it enters
   the matrix.
2. Read the admissible method set for the item and flag a proposed
   method that cannot produce closure evidence for it.
3. Look up the earliest review at which the proposed method matures
   and flag a planned review point earlier than that.
4. Confirm the provision names an evidence artefact; a method with no
   named report, procedure or drawing closes nothing.
5. Compare the conditions the evidence covers against the mandatory
   worst-case set for the item, and list every condition the evidence
   does not represent.
6. For a budget or sizing item, compute the margin as available power
   less demanded power over demanded power, and flag a margin below
   the required value; flag the provision outright when the margin
   data is absent.
7. Aggregate over the whole required item set: report items with no
   provision, provisions pointing at items outside the required set,
   the coverage fraction and the collected findings. The provision set
   is compliant only when every list is empty and coverage is
   complete.

## Pitfalls

- Copying the verification method from the equipment specification
  without asking what it produces -- a design review closes an
  interface statement, but it cannot demonstrate that the array still
  supplies the demand after fifteen years of degradation.
- Promising closure of a measurement-based provision at the
  preliminary review because the schedule is tight; the model that
  would carry the measurement does not exist yet, and the matrix then
  hides a slip rather than showing it.
- Verifying a power budget at beginning of life and reading the
  positive margin as compliance -- the requirement governs the worst
  case, and end-of-life degradation with the longest eclipse is where
  the budget actually closes or fails.
- Treating a named method as evidence -- "by analysis" with no report
  number is an intention. The artefact is what a reviewer opens.
- Reading a complete-looking matrix as full coverage without checking
  the other direction: a provision that points at a requirement
  outside the agreed set inflates the count while leaving a real item
  unverified.
- Failing an exactly-met margin because the subtraction of two floats
  landed a fraction of a unit in the last place low, then widening the
  required margin to make it pass -- the fix belongs in the
  comparison, never in the requirement.

## Behavior contract (gate 3)

The item categorization, method admissibility, review-maturity,
worst-case-condition, power-margin and coverage logic is exercised by
the gate 3 contract test:
scripts/test_e20_power_engineering_verification_provisions.py against
scripts/e20_power_engineering_verification_provisions_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e20_power_engineering_verification_provisions.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
