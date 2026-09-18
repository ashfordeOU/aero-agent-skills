---
name: q20-gse-config
description: "Maintain configuration control over ground support equipment under ECSS-Q-ST-20C clause 5.8.2: assess whether each GSE item is identified well enough to be controlled as one unit, hold the set as a baseline, replay the change log against that baseline in order so an unapproved, out-of-sequence or version-jumping change is refused and named rather than silently absorbed, then compare the as-built result with the configuration the equipment is declared to be at. Use when GSE has drifted from its baseline and the real state has to be established. Trigger: ecss, q-st-20c-clause-5-8-2, gse-configuration-item-identification, gse-baseline, gse-change-control, gse-as-built-configuration, gse-version-sequence-break."
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
  tags: [ecss, q-st-20c-quality-assurance-scope, q20-gse-config, gse-configuration-item-identification, gse-baseline, gse-change-control, gse-as-built-configuration, gse-version-sequence-break]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS GSE Configuration Control (space-systems/ecss/q20-gse-config)

Use when the task is the clause 5.8.2 configuration control of ground support
equipment in ECSS-Q-ST-20C: a set of GSE items is held against a baseline,
changes have been raised against it, and the question is what configuration the
equipment is actually at.

## Domain quick reference

- Identification comes before control. A GSE item without an individual serial
  cannot be held as one unit: two nominally identical racks that have diverged
  are one entry in the register and two different machines on the floor.
- A baseline is a set, not a list. The same item entered twice makes the
  baseline unreadable, because a change against it has two starting points.
- Change control is a replay, not a tally. A change applies only when it is
  approved, when the item is at the version the change says it starts from, and
  when it advances that version by one step.
- A refused change does not move the item, and every change queued behind it
  now starts from the wrong version. That cascade is the normal way a GSE
  register drifts, and it shows up as a run of sequence findings rather than
  one.
- A change raised against an item that was never baselined is a different
  finding from an unapproved change: the first says the register is incomplete,
  the second says the process was bypassed.
- The declared configuration and the replayed one are two independent claims.
  Where they disagree, the change log is the evidence and the declaration is
  the assertion.

## Workflow

1. Validate each configuration item: an identifier and a whole version number
   are mandatory, and a missing part number and a missing serial are raised as
   two separate findings.
2. Validate the baseline as a set, refusing an item entered twice.
3. Validate the change log, refusing a duplicated change identifier and a
   version that is not a whole number.
4. Replay the log in its stated order against the baseline, refusing a change
   for the first reason that applies — target not baselined, not approved,
   wrong starting version, more than one increment — and naming the refusal.
5. Report the applied and refused identifiers and the fraction of the log that
   reached the configuration, comparing it with a required value through a
   named tolerance where one is set.
6. Compare the replayed as-built state with the declared configuration, naming
   a version mismatch, an unlisted item and a declared item that was never
   baselined as three different findings.
7. Return the combined finding set; the equipment is under control only when
   none of them stands.

## Pitfalls

- Controlling a type where the hardware is an individual. Two dollies to the
  same drawing diverge the first time one is modified, and only a serial keeps
  them apart in the register.
- Applying a change because it was approved. Approval is one of three
  conditions; the item still has to be at the version the change starts from.
- Allowing a change to jump versions to catch up with reality. A two-step jump
  hides an intermediate state the equipment really passed through, and the
  as-built trail stops being a trail.
- Reading a run of sequence findings as many independent errors. One refused
  change upstream is usually the cause, and the fix is to that change, not to
  the ones behind it.
- Taking the declared configuration as the answer. The declaration is what
  somebody wrote down; the replay is what the approved changes actually build.
- Treating an empty change log as a problem. A baseline with nothing raised
  against it is the equipment sitting exactly where it was put.

## Behavior contract (gate 3)

The item identification checks, baseline validation, change log validation,
ordered replay with its four refusal reasons, applied-change ratio and the
as-built against declared comparison are exercised by the gate 3 contract test:
scripts/test_q20_gse_config.py against scripts/q20_gse_config_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_q20_gse_config.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
