---
name: e2040-database-update-after-implementation
description: "Validate the as-built repository deposit that closes the device implementation phase under ECSS-E-ST-20-40C clause 5.7.3. Use when the task is confirming the final outputs of implementation reached the repository, that the digest recorded for each deposited configuration file matches the one read back from the device or lot it was loaded into, that every deposit carries a frozen baseline label rather than a moving branch, that the tool chain and seed needed to regenerate it are recorded, and that superseded versions are retired instead of left active. Trigger: ecss, e-st-20-40c, device-implementation-database-update, as-built-bitstream-digest-match, implementation-baseline-freeze, regeneration-environment-record, superseded-deposit-still-active, final-programming-file-deposit."
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
  tags: [ecss, e-st-20-electrical-scope, e2040-database-update-after-implementation, device-implementation-database-update, as-built-bitstream-digest-match, implementation-baseline-freeze, regeneration-environment-record, superseded-deposit-still-active]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Device Engineering — Database Update After Implementation (space-systems/ecss/e2040-database-update-after-implementation)

Use when the task is the repository update of ECSS-E-ST-20-40C clause
5.7.3 -- depositing what implementation actually produced, and proving
that what is in the repository is what is in the delivered device.

## Domain quick reference

- This deposit is an as-built record, not a design input. The earlier
  layout deposit fed the next phase; this one has to still describe the
  hardware years later, when the only thing available is the
  repository and a part in a bag.
- Identity is proved by digest, not by file name. A final programming
  file is deposited with the digest read back from the device or the
  lot it was loaded into, and a mismatch means either the deposit or
  the delivery is not the article that was tested. Neither possibility
  is resolved by renaming the file.
- A deposit has to be frozen. A baseline label names an immutable
  point; a branch name names whatever that branch holds today, so a
  deposit pointing at a branch has no fixed content and cannot be
  reconstructed as delivered.
- Regeneration is part of the deposit. The output alone does not
  survive a tool upgrade: the tool chain version and the run parameters
  that fix a non-deterministic implementation have to be recorded with
  it, or the repository holds a result nobody can reproduce.
- Superseded versions are retired explicitly. An old programming file
  left marked active is the one somebody loads at a board repair three
  years later, and the digest match that would have caught it was never
  run against the retired copy.
- Completeness is a fraction of the owed as-built set, with the missing
  items named, and a device using several technologies owes the
  technology-dependent items once per technology.

## Workflow

1. Validate the device record: identifier, device kind and a non-empty
   technology list. Reject an unknown kind rather than assuming the
   default implementation route.
2. Build the owed as-built set: the final netlist, the production test
   program and the implementation report per technology, plus the final
   programming file per technology for a device whose implementation is
   loaded rather than fabricated.
3. Validate every deposit: known kind, a technology that the device
   declares when the kind is technology-dependent, a non-empty baseline
   label, a lifecycle state of active or retired, and, when present, a
   digest and a recorded tool-chain version.
4. Match deposits to the owed set, taking the active deposit for each
   entry. Two active deposits for one entry is a finding in itself:
   the repository does not say which one was delivered.
5. Check identity: the deposit digest has to equal the digest read back
   from the device or lot. A deposit with no read-back digest recorded
   is unproven rather than matched, and is reported as such.
6. Check the freeze and the regeneration record: a baseline label that
   names a moving branch, an absent tool-chain version, or an absent
   run parameter set for a non-deterministic implementation are each
   their own finding.
7. Report the owed set, the completeness fraction, the digest results,
   the retired items and whether the implementation phase may close.

## Pitfalls

- Depositing the programming file without the read-back digest. The
  repository then holds a file that resembles the delivered one, and
  nothing in it says the device was loaded from that file.
- Pointing a deposit at a branch. The content moves after the phase
  closes, and the as-built record silently becomes an as-maintained
  one.
- Recording the output and not the tool chain. A rebuild on a later
  tool version produces a different file, and without the recorded
  version there is no way to tell whether the difference matters.
- Leaving the superseded file active alongside its replacement. The
  repository offers two answers to one question, and the wrong one is
  as reachable as the right one.
- Reusing the layout deposit as the implementation deposit. They are
  different obligations: one is the input the phase consumed, the other
  is what the phase produced and what the delivered device contains.

## Behavior contract (gate 3)

The owed as-built set, deposit validation, active-version selection,
digest read-back comparison, baseline freeze and regeneration-record
checks and completeness computation are exercised by the gate 3
contract test:
scripts/test_e2040_database_update_after_implementation.py against
scripts/e2040_database_update_after_implementation_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2040_database_update_after_implementation.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
