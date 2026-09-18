---
name: q40-12-fta-tools
description: "Evaluate a software tool offered to support fault tree analysis under ECSS-Q-ST-40-12C: match what the tool computes against what the analysis actually needs, grade its results against reference cases inside a declared tolerance, compare two runs of one model for repeatability, verify that the model survives an export and re-import in the required exchange formats, derive the qualification effort the result consequence demands, and close with an acceptance verdict plus the restrictions that ride with it. Use when a tool is being chosen, requalified after a version change, or challenged in review. Trigger: ecss, q-st-40-12c, fta-tool-qualification, fta-tool-benchmark-grading, fta-tool-repeatability-check, fault-tree-model-exchange-round-trip, fta-tool-capability-gap."
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
  tags: [ecss, q-st-40-12c-fault-tree-analysis, q-st-40-12c, q40-12-fta-tools, fta-tool-qualification, fta-tool-benchmark-grading, fta-tool-repeatability-check, fault-tree-model-exchange-round-trip, fta-tool-capability-gap]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Fault Tree Analysis — Tool Acceptance (space-systems/ecss/q40-12-fta-tools)

Use when the task is the software tool clause of ECSS-Q-ST-40-12C: deciding
whether a tool offered to support the adopted IEC 61025 method may produce
evidence, how much qualification effort stands behind it, and what the project
has to do by hand because the tool does not.

## Domain quick reference

- A tool is accepted against four questions asked in order, and the order
  matters because a later answer is worthless if an earlier one failed. Does
  it compute what this analysis needs; does it reproduce reference results
  inside a declared tolerance; does it give the same answer twice on the same
  model; and does the model survive leaving the tool and coming back.
- Capability is matched against the need, not against the brochure. A tool
  without voting gate support cannot expand a two-of-three vote, and a tool
  without uncertainty propagation cannot carry a distribution on a basic
  event. An uncovered need is a blocking gap, because the missing computation
  does not become optional by being unavailable.
- Benchmark grading is a relative error against a reference value, so a case
  whose reference is zero has to fall back to the absolute deviation rather
  than divide by it. A result that sits exactly on the tolerance is inside it.
- Repeatability is not a formality. An unordered product, an unseeded sampler
  or a parallel reduction can move the last digits between runs, and a value
  that will be quoted in a report has to be the same value tomorrow.
- Round-trip fidelity is where models are silently damaged. A neutral exchange
  file that loses the house-keeping fields, or rounds a probability, produces
  a tree that still opens and no longer means what it meant.
- Qualification effort follows the consequence of the result, not the size of
  the tool. Where a catastrophic or critical result rests on the output, the
  tool needs a qualification record unless the result is independently
  reproduced; below that, a clean benchmark can carry it.
- A restriction is not a rejection. A missing export format, a version outside
  configuration control or an undeclared determinism each leave the tool
  usable with a written compensating action attached to the result.

## Workflow

1. Declare the tool: name, version, what it computes, what it writes, whether
   its version is under configuration control and whether it is deterministic.
   Reject an undeclared field rather than assuming it.
2. Derive the required capability set from the analysis that will be run, and
   take the difference. Any gap is blocking until the need is withdrawn.
3. Run the reference cases and grade each against its tolerance, keeping the
   worst relative error and every case that failed.
4. Run the same model twice and compare every reported quantity, naming the
   quantity that moved the most.
5. Export the model, re-import it, and compare the two summaries field by
   field for lost, added and changed values.
6. Derive the qualification level from the result consequence and whether the
   result has been independently reproduced.
7. Close with a verdict: blocking on a capability gap, a failed benchmark or a
   lossy round trip; restricted where a compensating action is needed; clean
   otherwise. Write the restrictions next to the verdict, never after it.

## Pitfalls

- Accepting a tool because it reproduces one textbook example. One case
  exercises one path; a benchmark set has to reach the gate types, the
  quantification method and the importance measures the project will actually
  use.
- Comparing a relative error with a tolerance by bare arithmetic. The error is
  a quotient of differences, so a result that sits exactly on its tolerance can
  land a few units in the last place above it; the comparison absorbs that
  representation error while the tolerance stays untouched.
- Treating a version change as a non-event. The acceptance was granted to a
  build, so a new version restarts the benchmark and the round trip, and a
  version outside configuration control cannot be tied to the result it
  produced.
- Reading a faithful export as a faithful round trip. The export has to be
  re-imported and compared; a file that writes cleanly and reads back with a
  rounded probability is exactly the failure this step exists to catch.
- Letting a restriction live in a separate note. A restricted tool produces
  results that are only valid with the compensating action, so the action
  travels with the verdict or it is not performed.

## Behavior contract (gate 3)

The tool declaration validation, capability and format gaps, benchmark
grading, repeatability comparison, export round trip, qualification level and
acceptance verdict are exercised by the gate 3 contract test:
scripts/test_q40_12_fta_tools.py against scripts/q40_12_fta_tools_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_q40_12_fta_tools.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
