---
name: q7003-anodizing-process-parameters
description: "Compute and grade the anodizing parameters of a black-anodizing-with-inorganic-dyes line under the ECSS-Q-ST-70-03C process clause. Use when an electrolyte, a current density, a bath temperature, an immersion time or an agitation arrangement has to be set or defended for a coating that will later be dyed: place free acid, dissolved aluminium and chloride inside their windows, derive the net growth rate from the current density and the dissolution the temperature drives, turn it into the thickness a run achieves and the time a target needs, size the rectifier from the racked area, and report one verdict per run. Trigger: ecss, q-st-70-03-black-anodizing-scope, sulphuric-anodizing-current-density, anodizing-bath-temperature-window, anodic-coating-growth-rate, dissolved-aluminium-bath-limit, anodizing-tank-agitation."
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
  tags: [ecss, q-st-70-03-black-anodizing-scope, q7003-anodizing-process-parameters, sulphuric-anodizing-current-density, anodizing-bath-temperature-window, anodic-coating-growth-rate, dissolved-aluminium-bath-limit, anodizing-tank-agitation, anodizing-rectifier-sizing]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Black Anodizing — Anodizing Process Parameters (space-systems/ecss/q7003-anodizing-process-parameters)

Use when the task is the anodizing step of the ECSS-Q-ST-70-03C
process clause -- fixing or defending the electrolyte, the current
density, the bath temperature, the immersion time and the agitation
that together decide whether the coating a part leaves the tank with
can take an inorganic dye at all.

## Domain quick reference

- Two opposing reactions run at once. Current grows the coating from
  the metal outward, and the electrolyte dissolves it back from the
  outside in. Every parameter in the clause acts on one of those two,
  and a parameter set that is defended one variable at a time usually
  has them fighting.
- Current density sets the growth. Below the window the coating takes
  so long that dissolution wins on the outer pores; above it the
  coating heats in its own pores, goes powdery and takes dye unevenly.
- Temperature sets the dissolution. Below the reference point the
  growth is essentially the electrical one; above it a linear fraction
  of the growth is given back, and there is a limiting temperature at
  which nothing accumulates however long the part stays in. That is
  not an error to report as a thin coating, it is a different failure
  and is reported as one.
- Free acid, dissolved aluminium and chloride each carry their own
  window and each fails differently. Acid outside its window changes
  the pore structure the dye has to fill, dissolved aluminium raises
  the bath resistance and softens the coating, and chloride pits the
  part outright at a concentration far below the other two.
- Agitation is not housekeeping. The dissolution that fights the
  growth is driven by heat generated inside the pores, so a stagnant
  bath is hotter where it matters than the thermocouple says, and the
  coating thins exactly where the flow was worst.
- The process sheet needs a time, not a rate. Inverting the growth
  relation at the declared current density and temperature gives the
  immersion time a target thickness actually needs, and the difference
  between that and the scheduled time is the honest margin.
- The rectifier is sized from the racked area, not the part. Current
  density multiplied by the total area on the rack is the current the
  supply has to hold at the end of the run, when the coating
  resistance is highest.

## Workflow

1. Validate the run record and reject an unknown agitation mode or a
   negative quantity rather than defaulting it.
2. Grade the electrolyte: free acid against both bounds, dissolved
   aluminium and chloride against their ceilings.
3. Grade the electrical and thermal parameters against their windows,
   and treat a declared absence of agitation as a finding in its own
   right.
4. Derive the surviving fraction of the growth at the declared bath
   temperature, and stop with a distinct finding when the bath is at
   or past the limiting temperature.
5. Compute the net growth rate, the thickness the scheduled time
   achieves, and the time the target thickness would need.
6. Compare achieved against target, treating a run that lands exactly
   on the target as acceptable rather than short.
7. Size the rectifier from the racked area, then report the findings,
   the two thickness numbers and one verdict per run.

## Pitfalls

- Reading a thin coating as a short run. The same thickness comes from
  a cool bath run briefly and a hot bath run long, and only the second
  has a coating whose outer pores have already been opened up by
  dissolution. Time alone cannot repair that one.
- Holding the current density constant while the rack changes. The
  density is current divided by the area actually on the rack, so a
  half-loaded rack at yesterday's current setting is running at twice
  the intended density.
- Treating the temperature window as a comfort band. It is the term
  that decides how much of the electrical growth survives, and a bath
  two degrees warm gives back a measurable fraction of the coating on
  every run, silently, with no other symptom until the dye goes on.
- Watching only the acid concentration. Dissolved aluminium climbs
  quietly with every load and changes the bath long before the acid
  titration notices, and chloride from a rinse water change can pit a
  part at a concentration three orders below the acid figure.
- Quoting agitation as present because a sparge pipe exists. What
  matters is flow across the part faces, and a rack that shadows its
  own inner parts has no agitation where the coating is thinnest.

## Behavior contract (gate 3)

The electrolyte windows, current-density and temperature windows,
agitation rule, dissolution term, growth and required-time arithmetic,
rectifier sizing and run verdict are exercised by the gate 3 contract
test: scripts/test_q7003_anodizing_process_parameters.py against
scripts/q7003_anodizing_process_parameters_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7003_anodizing_process_parameters.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
