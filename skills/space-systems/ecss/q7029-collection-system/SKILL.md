---
name: q7029-collection-system
description: "Design the collection train that captures the products of an ECSS-Q-ST-70-29 offgassing run: order the stages so condensables meet a cold surface before they reach a sorbent, size each sorbent bed so the swept volume stays under its breakthrough volume with a safety factor, check every cold finger sits far enough below each compound's condensation point, then combine the stage efficiencies into the capture fraction actually delivered per compound. Use when a trap, sorbent or cold-finger arrangement must be sized before a run or defended after one, and the compound that escapes the train has to be named rather than assumed absent. Trigger: ecss, q-st-70-29, offgassing-collection-train, offgassing-sorbent-breakthrough, offgassing-cold-finger-margin, offgassing-stage-ordering, offgassing-capture-fraction, crew-compartment-offgassing."
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
  tags: [ecss, q-st-70-materials-scope, q7029-collection-system, offgassing-collection-train, offgassing-sorbent-breakthrough, offgassing-cold-finger-margin, offgassing-stage-ordering, offgassing-capture-fraction]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Offgassing — Collection System (space-systems/ecss/q7029-collection-system)

Use when the task is the apparatus step of ECSS-Q-ST-70-29: arranging and
sizing the traps, sorbent beds and cold fingers that stand between the
conditioned specimen and the analytical instrument, so that what the analysis
step reports is what the specimen actually released.

## Domain quick reference

- The train is a series, and capture compounds multiplicatively. A stage sees
  only what the stage in front of it let through, so the delivered capture
  fraction is one minus the product of the per-stage escape fractions, never
  the sum or the maximum of the stage efficiencies.
- Order matters physically. A condensable that meets a warm sorbent first can
  plug the bed, load it with a species that will not desorb cleanly, and
  displace the lighter compounds the bed was chosen for. A cold surface placed
  upstream removes that load before the sorbent sees it.
- A sorbent bed has a breakthrough volume for each compound, not one rating.
  Once the swept volume passes that figure the compound leaves the far end of
  the bed and the measured mass understates the release. The sizing question
  is therefore per compound, and the limiting compound is the weakest one.
- Breakthrough volume is quoted at a temperature. A bed warmed by a heated
  vessel line has a smaller breakthrough volume than its catalogue figure, so
  the safety factor is applied against the derated figure, not the catalogue
  one.
- A cold finger only captures a compound whose condensation temperature is
  comfortably above the finger surface. A finger a degree or two below the
  dew point of a species captures a fraction that depends on flow and on
  local supersaturation, so a stated margin is required rather than a bare
  inequality.
- A compound the train never captures does not appear in the chromatogram and
  is therefore not absent — it is unmeasured. The train report has to name
  those compounds, because the analysis step cannot infer them.

## Workflow

1. Validate the train: at least one stage, each stage of a known kind, each
   efficiency inside its open interval, each geometric and thermal figure
   positive.
2. Validate the compound list: a name, a condensation temperature and, for
   each sorbent stage, a breakthrough volume for that compound.
3. Validate the sampling conditions: a positive swept volume, a positive
   sampling duration and a safety factor of at least one.
4. Check the ordering rule — record a finding when a sorbent bed sits upstream
   of a cold surface, since the condensable load then reaches the bed first.
5. For each compound and each sorbent stage, derate the breakthrough volume to
   the stage operating temperature, divide by the safety factor and compare
   with the swept volume. A stage in breakthrough contributes no capture for
   that compound.
6. For each compound and each cold stage, require the surface to sit at least
   the declared margin below the compound's condensation temperature. A stage
   without that margin contributes no capture for that compound.
7. Combine the contributing stage efficiencies into the delivered capture
   fraction, and compare it with the minimum capture the analysis step needs,
   absorbing representation error at the boundary with a named tolerance.
8. Report the delivered fraction per compound, the limiting compound, and
   every finding: breakthrough, insufficient cold margin, ordering, and any
   compound the train cannot capture at all.

## Pitfalls

- Adding stage efficiencies, or quoting the best stage as the train figure.
  Two ninety-percent stages deliver ninety-nine percent, not one hundred and
  eighty, and a train whose first stage is in breakthrough delivers whatever
  the remaining stages manage on their own.
- Using the catalogue breakthrough volume for a heated bed. The figure falls
  with temperature, and applying the safety factor to the catalogue value
  quietly spends the margin twice over.
- Sizing the train on the compound of interest only. The limiting compound is
  usually a light one that nobody was looking for, and it is the one that
  breaks through first.
- Placing the sorbent ahead of the cold finger because it is the more
  sensitive instrument. It is also the one the condensable load ruins.
- Reading a blank chromatogram as a clean specimen when the train never had
  a stage able to capture that species. Unmeasured is not absent.
- Comparing a cold-finger surface with a condensation temperature by bare
  inequality. Capture at a one-degree margin is partial and flow dependent;
  the margin is part of the design, not a rounding allowance.

## Behavior contract (gate 3)

The train validation, ordering check, breakthrough derating and sizing, cold
finger margin check, series combination of stage efficiencies and the limiting
compound selection are exercised by the gate 3 contract test:
scripts/test_q7029_collection_system.py against
scripts/q7029_collection_system_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_q7029_collection_system.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
