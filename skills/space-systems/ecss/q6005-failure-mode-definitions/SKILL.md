---
name: q6005-failure-mode-definitions
description: "Identify which observed failures count against a hybrid microcircuit lot when rejection thresholds are tallied under ECSS-Q-ST-60-05C clause 10.4.1: look every observed mode up in the defect catalogue, separate modes intrinsic to the delivered product from modes arising in the test setup or in handling after the process, charge an extrinsic mode unless a completed failure analysis evidences the attribution, charge an uncatalogued mode and report it, and return the charged total by defect group and by mode. Use when a screening failure tally has to be defensible. Trigger: ecss, q-st-60-05c, hybrid-chargeable-failure-modes, failure-mode-attribution-evidence, hybrid-defect-mode-catalogue, non-chargeable-test-environment-failure, chargeable-failure-tally."
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
  tags: [ecss, q-st-60-05-hybrid-procurement, q6005-failure-mode-definitions, hybrid-chargeable-failure-modes, failure-mode-attribution-evidence, hybrid-defect-mode-catalogue, non-chargeable-test-environment-failure, chargeable-failure-tally]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Hybrids — Failure Modes That Count Against a Lot (space-systems/ecss/q6005-failure-mode-definitions)

Use when the task is deciding which of the failures seen during screening or
lot acceptance belong in the number that ECSS-Q-ST-60-05C clause 10.4.1
thresholds are applied to — naming the defect types, grouping them, and
settling which observations are charged to the batch and which are not.

## Domain quick reference

- The rejection threshold is a fraction, and the numerator is defined by this
  clause. Every argument about whether a lot passes is really an argument
  about which failures went into that numerator, so the mode catalogue is the
  load-bearing part, not the arithmetic that follows it.
- The dividing line is intrinsic versus extrinsic. An intrinsic mode is a
  property of the hardware that was built — a lifted bond, a die-attach void,
  a cracked die, a leaking seal, a drifted thick-film resistor, an electrical
  parameter outside its limit. An extrinsic mode arises from the measurement
  or from what happened to the unit after it left the process — a faulty
  tester, a worn socket contact, a wrong test program, transit damage.
- Extrinsic does not mean uncharged. It means excusable, and the excuse has to
  be earned by a completed failure analysis that evidences the attribution.
  Until that analysis exists, the failure is charged, because a mode name is
  an assertion and the tally cannot be built on assertions.
- An uncatalogued mode is charged and reported, never dropped. A name nobody
  recognises is the one case where silence changes the answer most: dropping
  it shrinks the numerator and can turn a rejected lot into an accepted one
  with no record of how.
- Defect groups exist so a pattern is visible. Five separate interconnection
  modes in one lot are one systematic interconnection problem, and the grouped
  tally is what makes that legible to the failure review board even when no
  single mode exceeds anything.
- The same physical failure can be described by different names by different
  operators. Names are matched with case and separator folded together so a
  differently punctuated entry accumulates into the same mode rather than
  splitting the count across two rows.

## Workflow

1. Normalise each observed mode name, folding case and separators, and refuse
   a blank or non-string name — an unnamed failure cannot be graded.
2. Validate each observation: a positive integer unit count, and a boolean
   saying whether a completed failure analysis evidenced the attribution.
   A count defaults to one unit; zero or negative is an input error.
3. Look the mode up in the catalogue. A hit yields its defect group and its
   intrinsic flag; a miss groups it as unattributed and records the name.
4. Charge every intrinsic mode. Charge an extrinsic mode too, unless its
   attribution is evidenced. Charge every uncatalogued mode.
5. Accumulate the charged counts by defect group and by mode, largest first,
   so a systematic group is visible before any threshold is applied.
6. Return the observed total, the charged total, the excused observations and
   the findings — the uncatalogued names, and the extrinsic modes charged only
   because the failure analysis has not been done yet.

## Pitfalls

- Excusing a failure on the mode name alone. "Tester fault" written on a
  reject tag is a hypothesis; without the analysis behind it, the unit is a
  failure of unknown cause and belongs in the numerator.
- Dropping a mode the catalogue does not know. An unrecognised name silently
  removed from the tally is the quietest way a lot passes a threshold it
  should have exceeded.
- Tallying observations instead of units. One reject tag covering eight units
  is eight failures against the threshold, and a per-tag count understates the
  lot by whatever the tag batching happened to be.
- Splitting one mode across two spellings. Two rows of three, where one row of
  six was meant, hides a systematic mode under a per-mode review limit.
- Treating the group as decorative. The group is how a review board sees that
  the lot has an interconnection problem rather than six unrelated defects,
  and it drives which corrective action is asked for.
- Re-grading an intrinsic mode as extrinsic because the unit was also handled.
  Handling after screening explains transit damage, not a void that formed at
  die attach; the analysis has to reach the mechanism, not merely find a later
  opportunity for damage.

## Behavior contract (gate 3)

The mode catalogue, the intrinsic versus extrinsic split, the evidenced-
attribution rule, the uncatalogued-mode handling and the grouped charged tally
are exercised by the gate 3 contract test:
scripts/test_q6005_failure_mode_definitions.py against
scripts/q6005_failure_mode_definitions_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q6005_failure_mode_definitions.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
