---
name: q6003-device-configuration-system-implementation
description: "Audit a device configuration system for its ability to reproduce any baseline it has already released. Use when clause 8.2.1 of ECSS-Q-ST-60-03 is in front of you and the question is whether the regeneration claim survives contact with the archive: resolve every artefact and tool a released baseline cites, separate an artefact that was rewritten under its own name from one that was purged and from one with no recorded integrity value, refuse a tool reference that floats to whatever version is current, require an artefact a device can actually be rebuilt from, and weight coverage by units built. Trigger: ecss, q-st-60-03, q6003-device-baseline-regeneration, q6003-config-artefact-retention, q6003-config-artefact-integrity, q6003-production-tool-version-pinning, q6003-units-built-weighted-coverage."
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
  tags: [ecss, q-st-60-03-device-scope, q-st-60-03, q6003-device-configuration-system-implementation, q6003-device-baseline-regeneration, q6003-config-artefact-retention, q6003-config-artefact-integrity, q6003-production-tool-version-pinning, q6003-units-built-weighted-coverage]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Space Devices — Configuration System Able to Regenerate a Released Baseline (space-systems/ecss/q6003-device-configuration-system-implementation)

Use when the task is clause 8.2.1 of ECSS-Q-ST-60-03: operating a configuration
system under which any device baseline already released can be produced again.
The obligation is not that records exist. It is that a specific released
baseline can be rebuilt from what the system still holds, which is a claim an
index of filenames can satisfy on paper and fail in practice.

## Domain quick reference

- Retention and retrievability are different properties. An artefact kept
  under its original name but rewritten in place resolves, opens, and is not
  what the baseline was produced from. That case looks healthier in an
  inventory than a purged file does, and it is worse, because nothing signals
  the substitution to whoever fetches it.
- An artefact with no recorded integrity value cannot be shown to be the one
  the baseline used, even when it genuinely is. The regeneration claim rests on
  demonstrable sameness, and an unhashed file offers none.
- A tool reference that floats pins nothing. A recorded dependency on the
  current release of a synthesis or layout tool resolves to a different
  program every year, and the baseline it helped produce quietly stops being
  reproducible without any record changing.
- A withdrawn tool is a harder failure than an unpinned one. The version can be
  recorded perfectly and the program still cannot be executed, so pinning
  discipline alone never surfaces it.
- Not every retained artefact regenerates a device. Process records and test
  programmes describe a build; a design source or a mask set reproduces one. A
  baseline holding only the former is fully archived and not regenerable.
- Exposure is weighted by units built. A baseline behind a hundred flight units
  and one behind a single engineering model are the same single entry in a
  baseline count and nothing like the same risk.

## Workflow

1. Index the stored artefacts and the recorded tools, refusing a repeated
   identifier: two artefacts under one name make every reference ambiguous.
2. Validate each released baseline record — identifier, device, units built,
   and non-empty artefact and tool reference lists — and stop there when a
   field is absent, because an unjudgeable record is not a regeneration
   failure.
3. Resolve every reference before grading anything. A citation the system does
   not hold is a defect in the system's own index and outranks the state of
   the artefacts that did resolve.
4. Grade each resolved artefact: separate a rewrite in place from a purge, and
   both from a retained copy carrying no integrity value, so the finding names
   the correction the archive actually needs.
5. Grade each resolved tool: a withdrawn program first, then a version that
   names no fixed release.
6. Require at least one artefact of a kind a device can be rebuilt from, so a
   complete set of descriptive records cannot pass as a regenerable baseline.
7. Weight the regenerable baselines by units built, compare that coverage with
   the required level, absorbing floating-point representation error at the
   boundary with a named tolerance rather than by lowering the level, and
   return one verdict with findings ranked worst first.

## Pitfalls

- Reading presence in the archive as retrievability. The in-place rewrite is
  the defect this clause exists to catch and the one an inventory count is
  blindest to.
- Accepting an unhashed artefact because it is obviously the right file. The
  obligation is to be able to demonstrate it, not to believe it.
- Treating a pinned-but-withdrawn tool as a pinning problem. The version is
  already recorded; the program is gone, and the fix is an executable archive,
  not a stricter reference.
- Counting a baseline as regenerable because every artefact it cites is
  retained. Retained process records regenerate nothing.
- Reporting several defects for one baseline at once. The first blocking
  finding is the one to fix; the rest may not survive fixing it.
- Counting baselines instead of weighting them by units built, and widening
  the required coverage so an exactly-met case passes. An equality at the
  boundary is a representation question, handled by the tolerance inside the
  comparison; the required level stays as agreed.

## Behavior contract (gate 3)

The artefact and tool indexing, baseline record validation, reference
resolution, retention and integrity grading, tool availability and version
pinning checks, regenerating-artefact requirement, units-built-weighted
coverage and ranked findings are exercised by the gate 3 contract test:
`scripts/test_q6003_device_configuration_system_implementation.py` against
`scripts/q6003_device_configuration_system_implementation_logic.py` (stdlib
unittest, offline). Run:
`python3 scripts/test_q6003_device_configuration_system_implementation.py`

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
