---
name: q6012-foundry-process-selection
description: "Evaluate a semiconductor process and the foundry operating it against ECSS-Q-ST-60-12 clause 5.2. Use when a microwave design has to commit to a process line: confirm the validation status, its reference document and whether it is still current, treat a process change since validation as a re-qualification trigger rather than a note, derive the usable frequency from the gate length and technology, weigh breakdown voltage and the offered passive elements against the circuit need, form the process-control capability index from monitor statistics, and compare the declared production horizon with the programme. Trigger: ecss, q-st-60-12, mmic-foundry-selection, semiconductor-process-validation, process-control-capability-index, foundry-line-certification, die-supply-continuity-horizon, gate-length-frequency-limit."
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
  tags: [ecss, q-st-60-microwave-die-scope, q6012-foundry-process-selection, mmic-foundry-selection, semiconductor-process-validation, process-control-capability-index, foundry-line-certification, die-supply-continuity-horizon]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Microwave Die — Foundry and Process Selection (space-systems/ecss/q6012-foundry-process-selection)

Use when the task is ECSS-Q-ST-60-12 clause 5.2 — choosing the semiconductor
process a monolithic microwave design will be fabricated on, together with the
foundry line that runs it. The process and the foundry are selected as one
pairing, because a validated process on an uncontrolled line and a certified
line running an unvalidated process fail for different reasons.

## Domain quick reference

- Validation is a state with a date, not a label. A process is usable when it
  holds a current validation, that validation names a reference document, and
  nothing about the process has changed since it was granted. Each of those can
  fail on its own, and they do not fail the same way.
- A process change after validation is a re-qualification trigger, not a note
  in the margin. The validation evidence describes the process as it was; a
  changed layer stack, a moved fab or a new passivation invalidates the link
  between that evidence and the wafers the programme will actually receive.
  A merely stale validation, by contrast, is recoverable by a refresh.
- Geometry sets the first-cut frequency ceiling. Usable frequency scales
  roughly inversely with gate length through a technology-specific
  proportionality, which is enough to screen a process line in or out before
  any model data is exchanged. It is a screen, never a substitute for the
  foundry's own model set.
- Statistical control is what makes a process repeatable across lots. The
  capability index of each monitored parameter compares the distance from its
  mean to the nearer specification limit with three standard deviations; the
  weakest monitored parameter is the one that governs, and a thin lot history
  is an evidence gap even when the indices look comfortable.
- Supply continuity is a selection criterion. A process whose declared
  production horizon expires inside the programme is not excluded, but it owes
  an obsolescence plan — a lifetime buy, a second source or a port — before the
  design is frozen on it.

## Workflow

1. Normalise the option: process and foundry identifiers, technology,
   validation status, reference and age, the process-change flag, gate length,
   breakdown voltage, offered passives, monitor evidence, production horizon
   and line certification. Refuse an unrecognised technology or status.
2. Normalise the design need: highest operating frequency, supply rail and the
   breakdown factor applied to it, the passive elements the topology needs, the
   programme horizon, and the acceptance thresholds for capability, monitored
   lots and validation validity.
3. Settle validation currency first, and route its outcome: no validation and a
   post-validation process change exclude, while an open validation, a stale
   one, an absent age and an absent reference raise actions.
4. Derive the usable frequency from gate length and technology and compare it
   with the need; compare breakdown voltage with the derated supply rail; and
   confirm every required passive element is in the design kit. All three
   exclude when they fail.
5. Form the capability index of each monitored parameter and take the weakest.
   Below the acceptance threshold excludes; absent monitor data or too few
   monitored lots raise actions.
6. Compare the declared production horizon with the programme horizon and raise
   an action when it falls short; raise one when the line carries no quality
   certification on record.
7. Group the option, score it on a reproducible composite of frequency,
   voltage, capability and continuity headroom, rank by category first and
   score second, and recommend only an option carrying no open action.

## Pitfalls

- Reading a validation certificate without checking what happened after it.
  The certificate is evidence about a process state; a change since then means
  the wafers the programme receives are not the wafers that were validated.
- Treating a stale validation and an invalidated one as the same finding. One
  needs a refresh and the option survives; the other needs the qualification
  redone and the option does not belong on the shortlist meanwhile.
- Averaging the capability indices across monitored parameters. The yield and
  the drift are governed by the weakest parameter, and an average hides exactly
  the one that will produce the out-of-family lot.
- Accepting comfortable capability indices computed from one or two lots. The
  index describes a distribution; a thin lot history has not yet observed the
  lot-to-lot spread that the index is supposed to summarise.
- Comparing a usable frequency, a breakdown voltage or a capability index
  against its acceptance value with a bare inequality. An exactly adequate
  option can land a unit in the last place short; absorb that in the
  comparison, never by lowering the acceptance value.

## Behavior contract (gate 3)

The option and need validation, the gate-length frequency screen, the
capability index and its weakest-parameter rollup, validation currency and the
process-change route, supply continuity, the exclusion-versus-action split,
grouping, scoring and ranking are exercised by the gate 3 contract test:
scripts/test_q6012_foundry_process_selection.py against
scripts/q6012_foundry_process_selection_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_q6012_foundry_process_selection.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
