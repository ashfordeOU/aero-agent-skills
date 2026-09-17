---
name: q60-class-3-lot-homogeneity-sampling
description: "Size the specimen set offered for class 3 radiation verification testing so that it stands for the flight parts, under ECSS-Q-ST-60C clause 6.5.5, where the set is composed in line with the radiation standard: group the flight population on date code because the delivery is rarely one diffusion lot, size the irradiated, control and spare roles in integer arithmetic from the test method, the bias conditions and the number of groups, measure every specimen against the flight reference on part number, manufacturer and package, and limit the population the result may be written to. Use when a class 3 radiation result is about to be extended to parts nobody irradiated. Trigger: ecss, q-st-60c-clause-6-5-5, class-3-radiation-sample-composition, class-3-date-code-group-coverage, class-3-irradiated-control-spare-roles, class-3-radiation-result-population-limit, class-3-bias-condition-specimen-consumption."
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
  tags: [ecss, q-st-60-eee-scope, q60-class-3-lot-homogeneity-sampling, class-3-radiation-sample-composition, class-3-date-code-group-coverage, class-3-irradiated-control-spare-roles, class-3-radiation-result-population-limit, class-3-bias-condition-specimen-consumption]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EEE Components — Class 3 Radiation Test Sample Composition (space-systems/ecss/q60-class-3-lot-homogeneity-sampling)

Use when the task is the clause 6.5.5 question of ECSS-Q-ST-60C: a set of
parts bought at the lowest assurance class has been offered for radiation
verification testing, and the set has to be composed the way the radiation
standard composes one before anything goes in a beam. The question is not
whether the parts will survive. It is whether this set can carry an answer for
the flight parts at all, and which of those parts the answer reaches.

## Domain quick reference

- At the higher classes the flight parts can usually be held to one diffusion
  lot, and the sample stands for that lot. At this class they usually cannot,
  so the population is grouped on the only axis the records honestly support:
  the date code. Everything downstream is sized against that grouping.
- Uniformity and grouping are different questions. Part number, manufacturer
  and package are uniformity axes, and a specimen failing any of them cannot
  stand for the flight parts at all. The date code is not a uniformity axis;
  it is the axis the population is split on.
- The specimen count is the larger of two numbers: what the method costs
  across its bias conditions, and the per-group floor across the whole
  population. A population spread over more date codes costs more specimens.
  Spreading the same specimens thinner buys nothing.
- Bias conditions consume specimens only where the method says they do. A
  total-dose run repeats the irradiated set per condition; a displacement
  damage run does not.
- One control is owed per group once the groups outnumber the method's base,
  so a shift seen after irradiation can be separated from a difference that
  was already there between groups.
- Both ends of the date-code window matter more than the middle. The ends are
  where the process spread shows, and a set that skipped the newest group has
  measured the part the programme is least likely to have in stock.
- The result is written to the units whose group was actually represented in
  the beam, and no further. Everything else is an extrapolation, and calling
  it a verification does not make it one.

## Workflow

1. Validate the flight population and the flight reference, and group the
   population on date code.
2. Size the set from the method, the bias conditions and the group count:
   irradiated, control and spare counts, in integer arithmetic.
3. Count the roles the offered specimens actually fill, rejecting a duplicate
   specimen and an unknown role.
4. Measure every specimen against the flight reference on the uniformity axes
   and name any that cannot stand for the flight parts.
5. Compare offered against owed per role and record the shortfall.
6. Find the date-code groups that reached the beam with fewer irradiated
   specimens than the per-group floor.
7. Check the oldest and the newest group are both in the beam.
8. Derive the population the result may be written to, report it as an exact
   pair and a fraction, set the result scope from it, and report every
   finding. The set is composed only when nothing is outstanding.

## Pitfalls

- Treating a class 3 delivery as one lot because it arrived in one box. The
  grouping is what the date codes say it is, and the sizing follows it.
- Sizing the set from the method alone and then spreading those specimens
  across five date codes. The per-group floor exists exactly to stop that.
- Repeating the irradiated set per bias condition on a method that does not
  ask for it, or failing to repeat it on one that does.
- Holding one control for a population split over several groups, then
  reading a group difference as a radiation-induced shift.
- Drawing specimens from the middle of the date-code window because that is
  where the stock is. The ends are where the spread shows.
- Letting a specimen with a different package or a second-source manufacturer
  into the set because the part number matches. Those axes are pass or fail.
- Reusing one specimen for two roles so the counts add up on paper.
- Writing the result across the whole flight population when only some of the
  groups were represented. The scope is bounded by what was irradiated.

## Behavior contract (gate 3)

The population grouping, date-code parsing and ordering, method and bias
sizing with the per-group floor, per-group control rule, role counting and
duplicate rejection, uniformity axis measurement, group gap detection, window
endpoint checking, supported population derivation and result scope selection
are exercised by the gate 3 contract test:
scripts/test_q60_class_3_lot_homogeneity_sampling.py against
scripts/q60_class_3_lot_homogeneity_sampling_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q60_class_3_lot_homogeneity_sampling.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
