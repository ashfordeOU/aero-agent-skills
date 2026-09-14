---
name: e2008-reflectance-cut-off-purpose
description: "Assess why a cut-off point is kept beside the peak of a high reflectance band. Use when a reflectance band is being documented and the peak alone is offered as the description, under ECSS-E-ST-20-08C clause 8.7.5.3.2: map the declared coating functions to what the edge feeds, derive the band width and centre from the two half-level edges, and separate a coating needing no edge from one whose edge was never kept or was taken off a scan that stopped inside the band. Trigger: ecss, e-st-20-08c-clause-8-7-5-3-2, coverglass-reflectance-cut-off-purpose, high-reflectance-band-description, coating-band-edge-drift-monitoring, solar-absorptance-integral-bounds, reflectance-scan-edge-coverage."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-reflectance-cut-off-purpose, coverglass-reflectance-cut-off-purpose, high-reflectance-band-description, coating-band-edge-drift-monitoring, solar-absorptance-integral-bounds, reflectance-scan-edge-coverage]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies -- Reflectance Cut-Off Purpose (space-systems/ecss/e2008-reflectance-cut-off-purpose)

Use when the task is to state and defend why the cut-off point is kept
with the description of a high reflectance band in a coverglass coating
under ECSS-E-ST-20-08C clause 8.7.5.3.2 -- which coating functions need
the edge, what the edge feeds each of them, and whether the number on
file was actually measured.

## Domain quick reference

- A band is not described by a peak. Two coatings can both read 92
  percent at their maximum and do different jobs, because one holds that
  level out to 1150 nm and the other has given it up by 900 nm. The
  cut-off is what turns a peak into a band.
- What the edge is wanted for follows the coating function. A solar
  reflector's edge decides how much of the spectrum is turned away; an
  ultraviolet rejection stack's edge position is the rejection itself;
  an absorptance budget integrates between the edges; a drift monitor
  watches the edge because it moves long before the peak does.
- A band edge is the earliest visible symptom of a deposition run going
  out. Layer thickness shifts the edge in nanometres while the peak is
  still sitting at its plateau, so an inventory of edges lot by lot
  catches drift a peak record never shows.
- The cut-off alone says where the band stops, not how wide it is. The
  cut-on is its partner, and only the two together give a width and a
  centre a specification can be written against.
- A scan that ends at the edge has not seen the edge. It needs to run
  past it by a margin, or the last point is a plateau that happens to be
  where the instrument stopped.
- An edge reported beyond the credible spectral range for a coverglass
  is an instrument or transcription result, not a coating property, and
  it is caught before it reaches a thermal budget.
- Coating with no declared high reflectance function, function declared
  with no edge kept, and edge kept on an inadequate scan are three
  outcomes with three different owners. None of them is a pass.

## Workflow

1. Validate the band-description policy first: peak floor, minimum
   described width, scan margin and credible-wavelength ceiling. A
   ceiling under the minimum width is refused rather than used.
2. Group the declared coating functions, rejecting an unrecognised one
   rather than ignoring it, and map each to the quantity the kept edge
   feeds it. Append the shared objective whenever any function is
   present.
3. Decide whether an edge needs keeping at all: a declared function
   present and a band peak at or above the high-reflectance floor. A
   peak landing exactly on the floor still earns the edge.
4. Where it is required, look for the edge. No measurement block, or a
   block carrying no cut-off, is a documentation gap and closes on its
   own verdict with the objectives still reported.
5. Check the scan ran past the edge by the policy margin and that the
   edge sits inside the credible spectral range, and take the cut-on
   partner where the record holds one.
6. Derive the band width and centre from the pair. Report a missing
   cut-on as a finding rather than assuming a width.
7. Close on one verdict: edge not required, edge not kept, record
   inadequate, band width shortfall, or high reflectance band described
   -- reporting every inadequacy found, not only the first.

## Pitfalls

- Offering the peak as the band description. It says how reflective the
  coating is at its best and nothing about where that best applies.
- Keeping the cut-off without the cut-on. Where the band stops is half a
  description; the width is what a specification and an absorptance
  integral both need.
- Accepting an edge from a scan that ends on it. The plateau at the last
  measured point is the instrument's limit, not the coating's.
- Reading a low-reflectance coating as needing the edge kept. Below the
  high-reflectance floor the half-level edges describe a slope, not a
  band, and the record buys nothing.
- Passing an edge sitting far outside the credible range. It reaches a
  thermal budget as a real number and moves an absorptance figure that
  nobody then questions.
- Treating a declared function as sufficient reason on its own. The band
  has to actually be a high reflectance band before its edges describe
  anything worth keeping.

## Behavior contract (gate 3)

The policy validation, coating function inventory and objective mapping,
high-reflectance floor, band width and centre, scan-margin coverage,
credible-range check, the required/not-required decision and the purpose
verdict are exercised by the gate 3 contract test:
scripts/test_e2008_reflectance_cut_off_purpose.py against
scripts/e2008_reflectance_cut_off_purpose_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_reflectance_cut_off_purpose.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
