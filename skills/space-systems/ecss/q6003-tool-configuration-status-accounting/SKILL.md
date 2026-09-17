---
name: q6003-tool-configuration-status-accounting
description: "Audit the configuration status records kept for the software tools that built a device under ECSS-Q-ST-60-03C clause 8.2.3. Use when a build has to stay reproducible and every tool in the declared flow needs its version, patch level, option-set digest, host platform, qualification state and date of use pinned in a record. Reports build-flow roles with no record, records for roles the flow never used, floating version tokens that name whatever was installed, drift between the recorded baseline and what actually ran, and unqualified or advisory-bearing tools with no mitigation, then scores the accounting index. Trigger: ecss, q-st-60-03, device-build-tool-chain, tool-configuration-status-accounting, tool-version-pinning, tool-option-set-digest, build-flow-role-coverage, tool-qualification-state."
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
  tags: [ecss, q-st-60-device-assurance-scope, q6003-tool-configuration-status-accounting, device-build-tool-chain, tool-version-pinning, tool-option-set-digest, build-flow-role-coverage, tool-qualification-state]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Device Assurance — Build Tool Status Accounting (space-systems/ecss/q6003-tool-configuration-status-accounting)

Use when the task is the tool-side accounting of ECSS-Q-ST-60-03C clause
8.2.3 — establishing whether the configuration status recorded for the
software tools that produced a device is enough to rebuild that device
and get the same thing back.

## Domain quick reference

- A tool status record is not a tool inventory. The inventory says which
  tools exist; the record says which tool state produced this device.
  That takes the tool identity, the exact version, the patch or build
  level under it, a digest of the option set it was driven with, the
  host platform it ran on, the qualification state it held and the date
  it was used. Any of those missing leaves a rebuild guessing.
- Coverage is judged against the declared build flow, not against the
  record set. A role the flow uses with no record is the gap that stops
  a rebuild; a record for a role the flow never used is stale bookkeeping
  that misleads a later reviewer. They are different findings and are
  reported separately.
- A floating version token defeats the record. "latest", "current",
  "nightly" or a wildcard names whatever the machine happened to hold
  that day, which is the one thing a status record exists to prevent, so
  a floating token is refused even when every other field is complete.
- Drift is the difference between the recorded baseline and what
  actually ran, per field. Version drift, patch drift and option-set
  drift are three separate statements about the same build and are named
  individually, because the repair differs: one is a re-run, one is a
  re-baseline, one is an option review.
- Qualification state carries an obligation. A tool that is unqualified,
  qualified only with restrictions, or carrying an open advisory can
  still be used, but only against a named mitigation reference; the
  state alone is not a finding and the absence of the mitigation is.

## Workflow

1. Validate every status record against the demanded fields, normalising
   names and digests so padding and letter case cannot hide a mismatch,
   and refuse a second record for a role already recorded.
2. Reduce the declared build flow to its distinct roles; an empty flow
   is an input error rather than a trivially clean result.
3. Compare flow against records in both directions to produce the
   missing-record list and the stale-record list.
4. Mark every record whose version is a floating token, keeping the
   token in the finding so the repair is obvious.
5. Compare the recorded state field by field with the as-run state for
   each role that has both, and report each differing field with its
   recorded and as-run values.
6. Apply the mitigation obligation to every record that is not plainly
   qualified or that carries an open advisory.
7. Score the accounting index as the fraction of used roles with a
   complete, pinned, drift-free record, compare it with its floor under
   a named tolerance, and declare the build reproducible only when no
   record is missing, no version floats, nothing drifted and the index
   holds.

## Pitfalls

- Recording the tool name and version and stopping there. Two runs of
  the same version with different option sets are different builds; the
  option-set digest is what makes the record a reproduction instruction.
- Counting records instead of covering the flow. A full-looking record
  set can leave the one role the flow actually used unrecorded while
  carrying three roles it never touched.
- Accepting a floating version because the build worked. It worked with
  whatever was installed that day; the record then documents a moving
  target and the next rebuild silently differs.
- Collapsing drift into a single pass or fail. Naming which field moved
  is what tells a reviewer whether to re-run the tool, correct the
  baseline or review the options.
- Treating an unqualified tool as automatically unacceptable. The clause
  route is the mitigation: the finding is the missing mitigation
  reference, not the state itself.
- Relaxing the index floor for a flow that lands exactly on it. The
  equality is a representation question, handled by the tolerance inside
  the comparison; the floor stays where the assurance plan set it.

## Behavior contract (gate 3)

The record validation, floating-version detection, date parsing,
flow-versus-record coverage, per-field drift comparison, mitigation
obligation and the accounting-index comparison are exercised by the gate
3 contract test:
scripts/test_q6003_tool_configuration_status_accounting.py against
scripts/q6003_tool_configuration_status_accounting_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_q6003_tool_configuration_status_accounting.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
