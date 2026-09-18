---
name: e2007-system-verification-entry-condition
description: "Verify that every unit and subsystem has cleared functional acceptance before system-level electromagnetic compatibility work starts, per ECSS-E-ST-20-07C clause 5.3.1. Use when a system EMC campaign is being authorized: validate the unit and subsystem inventory, roll unit acceptance up to the parent subsystem, treat an open major or critical non-conformance as blocking, admit a waiver only when it names an authority and has not aged out, flag acceptance evidence older than its validity window, and hold the system test while an entry condition stays open. Trigger: ecss, e-st-20-electrical-scope, system-emc-entry-condition, unit-functional-acceptance, subsystem-acceptance-rollup, emc-test-readiness-gate, acceptance-waiver-admissibility, system-test-authorization-hold."
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
  tags: [ecss, e-st-20-electrical-scope, e2007-system-verification-entry-condition, system-emc-entry-condition, unit-functional-acceptance, subsystem-acceptance-rollup, emc-test-readiness-gate, acceptance-waiver-admissibility]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical Verification — Entry Condition for System-Level Compatibility Work (space-systems/ecss/e2007-system-verification-entry-condition)

Use when the task is the ECSS-E-ST-20-07C clause 5.3.1 entry condition for
system-level electromagnetic verification -- confirming that every unit and
every subsystem has passed its own functional acceptance, rolling that
acceptance up the inventory, judging waivers and open non-conformances, and
holding the system campaign while any entry condition is open.

## Domain quick reference

- A system-level compatibility finding is only interpretable when the
  articles under test already work. Run the system test over an unaccepted
  unit and an interaction defect and a latent unit defect produce the same
  symptom, with no way to separate them afterwards.
- The entry condition is evaluated on an inventory, not on one article.
  Each unit names the subsystem that holds it, each subsystem holds at
  least one unit, and a unit naming a subsystem that is not in the
  inventory has no place in the roll-up.
- Acceptance rolls upward and never downward. A subsystem whose own record
  says accepted is still held while a unit inside it is unaccepted,
  because the subsystem is only as accepted as its contents.
- Severity decides what blocks. An open non-conformance at or above the
  blocking rank holds the entry; minor findings are carried into the
  campaign and tracked rather than used to stop it.
- A waiver is a disposition, not an assertion. It admits an article only
  when it names an approving authority and has not aged past its validity
  window; a waiver with neither is an unaccepted article in other words.
- Acceptance evidence ages. Evidence older than the validity window is
  re-confirmed before it authorizes a campaign, because the article has had
  time to be reworked, re-harnessed or re-tuned since.
- Day counters are whole days, so every age in the entry decision is an
  exact integer and no rounding can move an article across a window edge.

## Workflow

1. Validate each article: level, acceptance status, parent subsystem for a
   unit, non-conformance severities and waiver record. Reject an
   unrecognized level or status, a unit that parents itself, a subsystem
   carrying a parent, and an accepted article with no acceptance day.
2. Build the inventory: reject duplicate names, an orphan unit, a subsystem
   holding no unit, and an inventory with no subsystem or no unit at all.
3. Raise the per-article findings: failed or unrun acceptance, an
   inadmissible or missing waiver, blocking-severity non-conformances, and
   acceptance evidence beyond the validity window.
4. Roll the unit results up to the parent subsystem and record every
   subsystem held by an unadmitted unit beneath it.
5. Report the admitted fraction of the inventory so a partially ready
   campaign can be described without implying it may proceed.
6. Aggregate the findings and emit the gate token. Only an empty finding
   list authorizes the system-level campaign.

## Pitfalls

- Reading the subsystem acceptance record and stopping there. That record
  was written before the last unit-level rework; the roll-up, not the
  record, decides whether the subsystem may enter.
- Treating any open non-conformance as blocking. A campaign that waits for
  every cosmetic finding never starts, which is why the blocking rank is
  explicit and adjustable rather than implied.
- Accepting a waiver because a waiver exists. Authority reference and age
  are the two things that make it a disposition, and both are checked.
- Counting an article as accepted because it once was. Evidence beyond the
  validity window is re-confirmed; the article has had time to change.
- Letting an acceptance date sit after the campaign decision date. That is
  a data-entry error, not a fresh acceptance, and it is rejected outright
  rather than folded into a negative age.
- Running the system campaign with a subsystem that holds no unit in the
  inventory. The inventory is then incomplete, and an entry decision taken
  on an incomplete inventory is not an entry decision.

## Behavior contract (gate 3)

The article validation, inventory structure, waiver admissibility,
non-conformance severity, acceptance ageing, subsystem roll-up and
gate-token logic is exercised by the gate 3 contract test:
`scripts/test_e2007_system_verification_entry_condition.py` against
`scripts/e2007_system_verification_entry_condition_logic.py` (stdlib
unittest, offline).
Run: python3 scripts/test_e2007_system_verification_entry_condition.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
