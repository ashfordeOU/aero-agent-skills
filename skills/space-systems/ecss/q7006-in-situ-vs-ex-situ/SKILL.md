---
name: q7006-in-situ-vs-ex-situ
description: "Determine whether each property of a particle or UV irradiation is read out without breaking vacuum or after transfer, under ECSS-Q-ST-70-06C. Use when a bleaching or air-sensitive property must be measured and the handling between chamber and instrument can undo what the beam did. Converts the transfer time and the recovery half-time into the fraction that has already come back, forces an in-situ read-out once that fraction passes its ceiling or the surface meets air, humidity or repeated openings, derives the transfer-time ceiling, and mandates the sealed, dry, light-tight handling an ex-situ read-out has to carry. Trigger: ecss, q-st-70-06, in-situ-versus-ex-situ-read-out, radiation-induced-darkening-recovery, transfer-time-ceiling, specimen-handling-controls, air-sensitive-specimen-transfer, chamber-opening-count."
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
  tags: [ecss, q-st-70-06-particle-uv-radiation-testing-scope, q7006-in-situ-vs-ex-situ, in-situ-versus-ex-situ-read-out, radiation-induced-darkening-recovery, transfer-time-ceiling, radiation-specimen-handling-controls, chamber-opening-count]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Particle and UV Radiation Testing — In-Situ versus Ex-Situ Measurement (space-systems/ecss/q7006-in-situ-vs-ex-situ)

Use when the task is choosing, for each property of an ECSS-Q-ST-70-06C
particle or UV exposure, whether it is measured inside the chamber
without breaking vacuum or afterwards on a bench instrument — and what
handling the second choice obliges.

## Domain quick reference

- The choice is not about convenience. Radiation-induced darkening in
  glasses, white paints and polymers bleaches once the specimen is warm,
  lit and in air, so an ex-situ number can be a partly recovered number
  wearing the label of an irradiated one.
- Recovery is described by a half-time. The fraction already back when
  the instrument sees the specimen follows from the transfer time and
  that half-time alone, and it is the quantity the decision turns on —
  not the transfer time in isolation, which means nothing without the
  half-time beside it.
- Inverting that relation gives the transfer-time ceiling: the longest
  handling that still keeps the recovered fraction under its limit. It
  is a derived number, so it moves with the material and is not a house
  constant to be copied between campaigns.
- Air, moisture and light are separate drivers from recovery. An oxidising
  surface, a hygroscopic coating and a photo-bleaching glass each force
  their own control, and a specimen brought back to air more often than
  the handling ceiling allows accumulates all of them.
- An in-situ requirement the facility cannot meet is still a requirement.
  Recording it as a finding keeps it visible in the report; silently
  reading the property out ex-situ makes the shortfall disappear.

## Workflow

1. Normalize each property record: recovery half-time where the property
   recovers, the air, moisture and light sensitivities, whether an
   in-situ instrument exists, and the planned transfer time, atmosphere,
   humidity and number of chamber openings.
2. Convert the transfer time and the half-time into the recovered
   fraction and compare it with its ceiling.
3. Add the handling drivers: an air-sensitive surface carried through
   air, a moisture-sensitive surface above the humidity ceiling, more
   chamber openings than the handling ceiling allows.
4. Any driver that fires makes the read-out in-situ. Where no in-situ
   instrument exists, keep the ex-situ mode and raise the shortfall.
5. For every ex-situ read-out, derive the controls it has to carry and
   the transfer-time ceiling it has to respect.
6. Compare the mandated controls with the controls the plan actually
   lists, and report any that were never planned.
7. Emit the per-property decisions, the two mode lists, the required
   controls and every finding; the allocation is sound only when no
   finding stands.

## Pitfalls

- Copying a transfer-time ceiling from an earlier campaign. It is a
  function of the material's half-time and changes with the material.
- Reading the recovered fraction as small because the transfer was
  "quick". Two hours is nothing against a ten-day half-time and most of
  the change against a one-hour one.
- Treating a nitrogen-purged glovebag as covering photo-bleaching. It
  keeps air out and lets light in; they are different controls.
- Counting only the final chamber opening. Every intermediate read-out
  that brings the specimen back to air is another exposure to handling.
- Dropping the in-situ requirement because the facility has no in-vacuum
  instrument. The requirement is a property of the material; only the
  shortfall belongs to the facility.

## Behavior contract (gate 3)

The record validation, recovery arithmetic, transfer-time ceiling,
in-situ drivers, handling-control derivation, per-property decision and
allocation aggregation are exercised by the gate 3 contract test:
scripts/test_q7006_in_situ_vs_ex_situ.py against
scripts/q7006_in_situ_vs_ex_situ_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q7006_in_situ_vs_ex_situ.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
