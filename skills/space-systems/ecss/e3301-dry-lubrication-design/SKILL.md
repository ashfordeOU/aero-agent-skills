---
name: e3301-dry-lubrication-design
description: "Design a solid-lubricant film for a mechanism interface under ECSS-E-ST-33-01C clause 4.7.3.2. Use when the task is applying a dry lubricant such as molybdenum disulphide, tungsten disulphide, graphite or PTFE to a hot, slow or low-cycle duty: confirming the duty belongs in the dry domain rather than the fluid one, matching the solid to vacuum and to humid ground air, sizing the film by Archard wear over the sliding distance to a wear-through cycle count, and holding the deposition process to its controlled window of thickness, rate, substrate roughness and batch uniformity. Trigger: ecss, e-st-33-01-mechanisms-scope, mechanism-dry-lubrication, solid-lubricant-film-design, molybdenum-disulphide-film, dry-film-deposition-control, dry-film-wear-life, dry-lubricant-vacuum-compatibility."
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
  tags: [ecss, e-st-33-01-mechanisms-scope, e3301-dry-lubrication-design, mechanism-dry-lubrication, solid-lubricant-film-design, molybdenum-disulphide-film, dry-film-deposition-control, dry-film-wear-life, dry-lubricant-vacuum-compatibility]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Mechanisms — Dry Lubrication Design (space-systems/ecss/e3301-dry-lubrication-design)

Use when the task is the clause 4.7.3.2 dry-lubrication requirement of
ECSS-E-ST-33-01C — putting a solid lubricant film between two moving
surfaces, under a controlled deposition process, for a duty that is
too hot, too slow or too short in cycles for a fluid.

## Domain quick reference

- Dry lubrication has a domain, and the first question is whether the
  duty is in it. A hot limit beyond what a space-qualified fluid
  survives puts the duty there outright; otherwise it takes both a low
  sliding speed and a low cycle count. A fast, high-cycle, cool duty
  given a solid film is a design decision working against the
  material.
- The common solids do not behave the same way in the same place.
  Molybdenum and tungsten disulphide do their best work in vacuum and
  lose performance in humid air, so the ground phases need a dry purge
  or a controlled enclosure. Graphite is the inverse: it lubricates
  through adsorbed moisture and gives that up in vacuum. PTFE is
  tolerant of both and limited instead by temperature and load.
- A solid film has a finite amount of material and no reservoir. Life
  is a wear calculation: sliding distance from stroke and cycles, an
  Archard volume from the wear coefficient and load, that volume
  spread over the contact area as a depth, and the cycle count at
  which the usable thickness is gone.
- The film is made by its process. Thickness, deposition rate,
  substrate preparation and batch-to-batch uniformity each change what
  the film is, so a film produced outside the qualified window is a
  different film from the qualified one regardless of what the
  drawing calls it.
- Batch uniformity is graded as a fraction of the nominal thickness,
  not as an absolute spread. The same spread is negligible on a thick
  film and is most of a thin one.

## Workflow

1. Reduce the duty to a temperature range, a sliding speed and a
   required cycle count, and say whether dry lubrication is indicated;
   report a counter-indication rather than proceeding silently.
2. Look the chosen solid up in the material registry and grade it
   against both environments: the vacuum it operates in and the humid
   ground air it is handled and tested in.
3. Compute the sliding distance per cycle from the stroke, the Archard
   wear volume from the wear coefficient and load, and the wear depth
   over the contact area.
4. Divide the usable film thickness by the depth per cycle for the
   wear-through cycle count, and take the ratio against the required
   cycles as the wear margin.
5. Grade the deposition parameters against the controlled window:
   thickness and rate inside their bounds, substrate roughness under
   its limit, batch spread under its fraction of nominal.
6. Merge the duty, environment, wear and process findings into one
   report; a clean process with a consumed film is not a pass.

## Pitfalls

- Applying a dry film to a fast, high-cycle duty because the interface
  is inconvenient to oil. Speed and cycles are what the solid film is
  worst at, and the counter-indication is the finding.
- Treating all four solids as interchangeable. Graphite in vacuum and
  a disulphide left in humid air are the same mistake in opposite
  directions.
- Quoting a wear coefficient without the contact area. The wear volume
  becomes a depth only when it is spread over the contact, and it is
  the depth that consumes the film.
- Grading batch spread as an absolute number. On a thin film a spread
  that looks small is a large fraction of the deposit.
- Accepting a film deposited outside the qualified window because the
  measured thickness came out right. The process makes the film; a
  thickness reached by a different rate on a rougher substrate is not
  the qualified film.

## Behavior contract (gate 3)

The duty indication, material environment compatibility, sliding
distance, Archard wear volume, wear depth, wear-through life, the
deposition process window and the merged assessment are exercised by
the gate 3 contract test:
scripts/test_e3301_dry_lubrication_design.py against
scripts/e3301_dry_lubrication_design_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e3301_dry_lubrication_design.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
