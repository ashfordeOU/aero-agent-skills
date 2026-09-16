---
name: e2008-solar-array-standard-objectives
description: "Use when a solar-array requirement set must be shown to serve the aims of the standard rather than merely to exist. Trace the aims of the solar array standard of ECSS-E-ST-20-08C clause 4.1.1 into the project requirement tree and grade how the flow down is organised: confirm every objective area the standard declares owns a requirement at the system tier, follow each lower requirement to a live parent one tier above it in the same area, report each broken link by kind, name the aims stated at system level but never flowed to hardware, check every terminal requirement carries analysis, test, inspection or review-of-design, and roll the ratios into an organisation index. Trigger: ecss, e-st-20-electrical-scope, e-st-20-08c, solar-array-standard-objectives, solar-array-requirement-flow-down, solar-array-objective-coverage, photovoltaic-assembly-requirement-tier, solar-array-verification-method-assignment, solar-array-orphan-requirement-check."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-08c, e2008-solar-array-standard-objectives, solar-array-standard-objectives, solar-array-requirement-flow-down, solar-array-objective-coverage, photovoltaic-assembly-requirement-tier, solar-array-verification-method-assignment, solar-array-orphan-requirement-check]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Solar Array — Standard Objectives And Requirement Flow-Down (space-systems/ecss/e2008-solar-array-standard-objectives)

Use when the task is the opening clause of the solar array standard,
ECSS-E-ST-20-08C clause 4.1.1 -- what the standard is for, and how the
requirements that carry those aims are meant to be organised down the
project tree. The check is not whether a requirement set is large, but
whether each aim reaches hardware and each terminal requirement can be
traced back to the aim it serves.

## Domain quick reference

- The standard organises its requirements around five aims:
  performance-definition (what the array delivers, end of life
  included), design-and-interface (the array as a designed item and
  its interfaces to the spacecraft), verification-and-test (how the
  above is shown to be met), product-assurance (materials, processes,
  parts and the evidence behind them), and documentation-and-data (the
  package the customer receives). An aim with no system-tier
  requirement is an aim the project has silently dropped.
- The flow-down tiers run system, assembly, component, material. A
  requirement below the system tier names a parent exactly one tier
  above it: the intermediate tier is where the aim is turned into
  something an assembly or a part can be built and measured against,
  so a jump from system straight to material loses that translation.
- A parent also has to serve the same aim as its child. A thermal-cycle
  test requirement hung under a documentation requirement has no
  traceable reason to exist, and the aim it appears to serve is not the
  one the tree says it serves.
- The requirements with nothing below them are where verification
  actually happens, so each one carries a method -- analysis, test,
  inspection or review-of-design. An intermediate requirement does not
  need one; its children carry it.
- An aim stated only at the system tier is a distinct defect from an
  aim not stated at all. Coverage looks whole in the first case, which
  is exactly why it has to be reported separately: the aim exists on
  paper and touches no hardware.
- The organisation index is a weighted roll-up of objective coverage,
  link integrity and verification assignment. It is a reporting number
  and a project may reweight it; the verdict is not taken from the
  index but from all three ratios being whole at once.

## Workflow

1. Normalise the requirement set. Every record declares an identifier,
   an objective area and a tier; reject an uncategorized area or tier
   rather than defaulting it, and reject a duplicated identifier,
   because every downstream trace is keyed on it.
2. Check objective coverage. For each of the five aims, find whether a
   system-tier requirement exists and how deep that aim reaches. Report
   the aims with no system-tier requirement and, separately, the aims
   that never go below the system tier.
3. Walk every parent link. A system-tier record carries no parent; a
   lower record names one that exists, sits exactly one tier above and
   serves the same aim. Report each break by kind rather than as a
   single count, because the repair differs: a missing parent is an
   authoring gap, a skipped tier is a missing translation, and a
   cross-area parent is a mis-stated aim.
4. Identify the terminal requirements -- the ones no other requirement
   names as parent -- and check each carries a verification method.
5. Trace any requirement of interest up its chain to the aim it serves,
   and refuse to report a trace that runs through a missing parent or
   closes on itself rather than returning a partial chain.
6. Roll the three ratios into the organisation index and withhold the
   organised verdict unless coverage, link integrity and verification
   assignment are all whole and no aim is left unflowed.

## Pitfalls

- Reading a full coverage ratio as an organised tree. Coverage only
  asks whether each aim owns a system-tier requirement; an aim that
  owns one and nothing else scores the same as an aim flowed to
  material level, which is why the unflowed aims are reported on their
  own line.
- Counting broken links instead of naming them. A tier skip and a
  missing parent both lower the same ratio, but one is repaired by
  writing the intermediate requirement and the other by fixing a
  reference, so a bare count sends the repair to the wrong place.
- Allowing a parent that sits at the same tier as its child. It reads
  as a flow-down and is really a cross-reference, so the chain gains a
  step without gaining a translation and the depth reported for that
  aim is overstated.
- Demanding a verification method on every requirement. Intermediate
  requirements are met through their children; forcing a method onto
  them produces duplicated verification and hides which level the
  evidence actually comes from.
- Walking a parent chain without a cycle guard. Two requirements that
  name each other terminate no walk, and a trace that silently returns
  a truncated chain is worse than one that refuses.
- Comparing the organisation index against a whole-number threshold by
  bare arithmetic. The index is a weighted sum of exact ratios and can
  land a few units in the last place below one, so the comparison
  absorbs that representation error while the ratios stay untouched.

## Behavior contract (gate 3)

The record normalisation, objective coverage, unflowed-aim detection,
parent-link defect walk, terminal verification assignment, chain trace
and organisation index are exercised by the gate 3 contract test:
scripts/test_e2008_solar_array_standard_objectives.py against
scripts/e2008_solar_array_standard_objectives_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_solar_array_standard_objectives.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
