---
name: q7001-contamination-threat-identification
description: "Identify the contamination sources a hardware item meets across its life cycle and rank the threats that actually reach its sensitive surfaces, per the ECSS-Q-ST-70-01C framework. Use when a contamination control plan is being written and the source register must be shown complete from manufacture through storage, transport and launch-site processing to orbit: converts each source into the arrival it delivers through its transport fraction, totals arrivals per species and per phase, names the driving source and phase, and reports a phase carrying neither a source nor a statement that none exists. Trigger: ecss, q-st-70-01-cleanliness-contamination-scope, contamination-source-register, life-cycle-phase-coverage-gap, contamination-transport-fraction, particulate-molecular-arrival-split, dominant-contamination-threat, uncredited-transport-barrier."
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
  tags: [ecss, q-st-70-01-cleanliness-contamination-scope, q7001-contamination-threat-identification, contamination-source-register, life-cycle-phase-coverage-gap, contamination-transport-fraction, dominant-contamination-threat, uncredited-transport-barrier]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Cleanliness and Contamination Control — Threat Identification (space-systems/ecss/q7001-contamination-threat-identification)

Use when the task is the source-and-threat identification step of
ECSS-Q-ST-70-01C — building the register of what can contaminate an
item at each point of its life, and deciding which of those sources the
control plan actually has to be written against.

## Domain quick reference

- A source is not a threat until it arrives. What matters at the
  sensitive surface is the release rate multiplied by the time the
  hardware is exposed to it and by the fraction that survives the
  barriers in between. A large release behind a cover and a small
  release with a direct line of sight can deliver the same arrival.
- The register spans the whole life cycle, not the clean phases.
  Manufacture, assembly, integration, test, storage, transport,
  launch-site processing, ascent and orbit each release something, and
  the phases most often left out — storage and transport — are the ones
  where hardware sits longest with the least supervision.
- Particulate and molecular species are totalled separately because
  they are controlled separately and they degrade different functions.
  A register that reports one number has hidden which of the two
  control routes needs the work.
- A phase with nothing written against it is ambiguous: it can mean no
  source was found or that nobody looked. The register resolves that by
  requiring an explicit statement when a phase genuinely carries no
  source, so silence always reads as a gap.
- A transport fraction of one with no barrier named is an assumption
  about geometry, not a conservative choice. It is reported, because a
  plan that credits no barrier anywhere cannot show where its margin
  came from.
- When one source holds more than half a species total, it is the
  driver. Tightening anything else cannot bring the total down, so the
  plan is written against the driver first.

## Workflow

1. Validate each source: a name, a recognised life-cycle phase, a
   species, a non-negative release rate and exposure, and a transport
   fraction inside the closed unit interval. Refuse a positive release
   over zero exposure and refuse duplicate source names.
2. Convert each source into its arrival at the sensitive surface, and
   keep the arrival alongside the source rather than replacing it.
3. Total arrivals per species and per life-cycle phase, and rank the
   sources largest first with ties broken by name so the order is
   reproducible.
4. Compare the phases carrying sources with the phases the programme
   declares, treating an explicit nil statement as coverage and refusing
   a nil statement contradicted by an identified source.
5. Name the driving source per species and the driving phase overall.
6. Report the findings: an uncovered phase, a species with no source
   identified, a source crediting no transport barrier, and a dominant
   source.

## Pitfalls

- Ranking sources by release rate. Release rate ignores exposure time
  and transport, so it promotes a short, well-shielded process over a
  long, open one and sends the control effort to the wrong place.
- Writing the register only for the phases in the cleanroom. Storage and
  transport are usually the longest exposures in the life cycle and are
  the most common gap in an otherwise complete plan.
- Merging particulate and molecular arrivals into one figure. The two
  are controlled by different means, so a merged total cannot be acted
  on.
- Leaving a phase blank to mean "nothing here". Blank is
  indistinguishable from unexamined; an explicit statement that a phase
  carries no source is what closes it.
- Setting every transport fraction to one and calling it conservative.
  With no barrier named anywhere the plan cannot show where its margin
  is, and the result is reported as an uncredited barrier rather than as
  a conservative case.

## Behavior contract (gate 3)

The source validation, phase and species vocabulary, arrival conversion,
per-species and per-phase totals, ranking, coverage comparison with nil
statements, dominance detection and finding assembly are exercised by
the gate 3 contract test:
scripts/test_q7001_contamination_threat_identification.py against
scripts/q7001_contamination_threat_identification_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_q7001_contamination_threat_identification.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
