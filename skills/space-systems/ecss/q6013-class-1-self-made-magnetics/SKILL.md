---
name: q6013-class-1-self-made-magnetics
description: "Assess whether an in-house wound magnetic part carries the design basis and screening a class 1 commercial part activity needs under ECSS-Q-ST-60-13C clause 4.6.8: refuse a part with no designation, core reference or released winding process, treat an unqualified winding operator as a finding, hold conductor current density and hot-case saturation utilization to their ceilings with equality admissible under a named tolerance, compare winding hot spot with the insulation system rating and demonstrated withstand with the required multiple of working voltage, and name every absent screening step. Use when a self made magnetic has to be judged flight worthy. Trigger: ecss, q-st-60-13c-clause-4-6-8, self-made-magnetic-design-basis, magnetic-saturation-utilization-ceiling, winding-current-density-limit, magnetic-insulation-temperature-rating, magnetic-dielectric-withstand-check, in-house-winding-process-qualification."
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
  tags: [ecss, q-st-60-13-commercial-eee-scope, q6013-class-1-self-made-magnetics, q-st-60-13c-clause-4-6-8, self-made-magnetic-design-basis, magnetic-saturation-utilization-ceiling, winding-current-density-limit, magnetic-insulation-temperature-rating, magnetic-dielectric-withstand-check, in-house-winding-process-qualification]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Class 1 Commercial Parts — Self-Made Magnetics (space-systems/ecss/q6013-class-1-self-made-magnetics)

Use when the task is the self-made magnetics provision of ECSS-Q-ST-60-13C
clause 4.6.8 — a transformer, inductor or choke wound in house rather than
bought as a catalogue item, the design basis that has to stand behind it, and
the screening it receives before it is fitted at the highest assurance level.

## Domain quick reference

- A self-made magnetic arrives with no manufacturer behind it. There is no
  datasheet to derate against and no maker's qualification to cite, so the
  released winding process document, its issue, and the qualification of the
  operator who wound the part take that place. A part wound to no released
  process is undocumented work, whatever it measures at.
- The design basis is arithmetic, not opinion. Conductor current density,
  worked in ampere per square millimetre, is what turns a winding into a heat
  source; the ceiling is a design decision the part is held to rather than a
  target it aims at.
- Core margin is stated as utilization: the peak working flux density over the
  saturation flux density at the hot case, not at room temperature. A core
  that has margin on the bench and none at the hot end of the mission is a
  core with no margin.
- Both of those are quotients of measured values, so a design landing exactly
  on its ceiling is admissible and the equality is absorbed by a named
  tolerance rather than by moving the ceiling. A tighter project ceiling is
  always allowed; a looser one is an input error.
- The insulation system carries two independent duties: it has to survive the
  winding hot spot, and it has to withstand a voltage well above the one it
  works at. One can pass while the other fails, so each is reported
  separately.
- Screening replaces the incoming inspection a bought part would have had. An
  unrun step is a coverage shortfall, not a step with no failures, and the
  steps that matter most are the ones that see an insulation defect before it
  becomes a short in orbit.

## Workflow

1. Validate the part identity — designation, core reference and winding shop —
   and the process basis: process document, its issue and the operator
   qualification flag. An unqualified operator is a finding, not an error.
2. Validate every winding: name, turns, conductor cross-section and
   root-mean-square current. Reject a winding declared twice.
3. Compute each winding's current density and hold it to the declared or
   default ceiling, taking an exactly-met ceiling as admissible.
4. Compute the core saturation utilization at the hot case against its own
   ceiling, rejecting a declared ceiling looser than the default.
5. Compare the hot-spot temperature with the insulation system rating, and the
   demonstrated withstand voltage with the required multiple of the working
   voltage, keeping both findings when both apply.
6. Compare the declared screening steps with the mandatory set and name each
   absent one.
7. Report the winding records, the core record, the insulation record, the
   absent screening steps and a verdict carrying every finding.

## Pitfalls

- Sizing a winding by wire gauge habit rather than by current density. A gauge
  that is comfortable in air is a different part in vacuum, where the only
  heat path out of the winding is conduction.
- Taking the saturation flux density from the room-temperature curve. Ferrite
  saturation falls with temperature, and a design checked cold can run into
  the knee exactly when the mission is hottest.
- Loosening a ceiling to make an existing build close. The ceilings are inputs
  here; the build closes by rewinding with more copper or a larger core.
- Proving the insulation thermally and stopping. A winding well inside its
  temperature rating can still have a turn-to-turn weakness that only a
  withstand measurement finds.
- Treating an unrun screening step as a clean step. A magnetic with no
  insulation resistance measurement has no insulation findings, which is a
  shortfall to be named rather than a result.
- Accepting a part wound by an unqualified operator because it measures well.
  The measurements cover the part on the bench; the process qualification is
  what covers the next part wound to the same drawing.

## Behavior contract (gate 3)

The identity and process-basis validation, per-winding current density,
saturation utilization at the hot case, insulation temperature and withstand
comparisons, screening-step coverage and the overall fitness verdict are
exercised by the gate 3 contract test:
scripts/test_q6013_class_1_self_made_magnetics.py against
scripts/q6013_class_1_self_made_magnetics_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_q6013_class_1_self_made_magnetics.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
