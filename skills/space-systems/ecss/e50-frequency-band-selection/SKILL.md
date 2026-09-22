---
name: e50-frequency-band-selection
description: "Determine whether the frequency band proposed for a space link may actually be used, under ECSS-E-ST-50C clause 5.6.12.2: the band is allocated to the service the link performs, in the region it operates over, and the whole necessary bandwidth sits inside that allocation. Compute the occupied edges, test containment with a tolerance at the allocation boundary, separate a protected primary allocation from an unprotected secondary one from a band that spills out from a service with no allocation at all, and rank the allocations the link could move into. Use when choosing or reviewing a spacecraft link frequency. Trigger: ecss, e-st-50-communications, space-link-frequency-band-selection, itu-service-allocation-status, primary-versus-secondary-allocation, necessary-bandwidth-containment, space-link-region-applicability."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: space-systems
pack: space-systems
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
clauses:
  - standard: ECSS-E-ST-50C Rev.2
    clause: 5.6.12.2
    items: [a]
    relation: implements
metadata:
  domain: space-systems
  subdomain: ecss
  tags: [ecss, e-st-50-communications, e50-frequency-band-selection, space-link-frequency-band-selection, itu-service-allocation-status, primary-versus-secondary-allocation, necessary-bandwidth-containment, space-link-region-applicability]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Communications — Frequency Band Selection (space-systems/ecss/e50-frequency-band-selection)

Use when the frequency band a space link will operate in is being chosen or
reviewed, per ECSS-E-ST-50C clause 5.6.12.2 — whether that band is one the
link is entitled to use, and on what terms.

## Domain quick reference

- The clause's own obligation is an act, not an analysis: a request for
  assignment of the chosen frequencies goes to the ITU before the system
  requirements review. What decides whether that request is worth making
  is containment, not proximity — the band is allocated to the service
  this link performs, in the region it operates over, and the whole of
  the necessary bandwidth sits inside the allocation.
- A centre frequency is not a band. What is regulated is the bandwidth the
  emission necessarily occupies, so the edges are what must be tested and
  a centre comfortably inside an allocation can still spill out of it.
- Three coordinates select an allocation, not one. Service and region
  decide which allocations even apply; frequency decides whether the link
  fits in one of them. Skipping the region check is how a band legal at
  home turns out not to be over the ground station that will use it.
- Secondary is usable and unprotected, and that is a third outcome, not a
  pass with a footnote. The link must accept interference from the primary
  services sharing the band and cause none to them.
- A band that overlaps an allocation without sitting inside it is the
  worst finding to lose, because every eyeball check reads it as inside.
  Report the spill on each edge in hertz so the size of the move is known.
- Occupancy of the allocation is the number that governs the rest of the
  mission. A link consuming most of a narrow allocation has taken the band
  from whatever else was going to share it.

## Workflow

1. Declare the applicable allocations: service, edges, status and the
   regions each applies in. An allocation with no regions stated applies
   everywhere, which is a claim, so record it as all three.
2. Declare the request as a service, a centre, the necessary bandwidth and
   the region of operation. Bandwidth is what the emission occupies, not
   the symbol rate.
3. Derive the occupied edges from centre and bandwidth, and reject a
   bandwidth that would place the lower edge at or below zero hertz rather
   than returning a negative frequency.
4. Filter the allocations to those matching both service and region before
   any frequency comparison.
5. Test containment with a tolerance scaled by the frequency. A band edge
   landing exactly on an allocation boundary must be decided the same way
   on every platform.
6. Prefer a primary allocation where both statuses contain the band, and
   report the status either way rather than reducing it to usable.
7. Where the band does not fit, rank the allocations the link could move
   into by status, then by how little of each it would consume, and give
   the centre range that makes it fit.
8. Put the frequencies this selection settles on into a request for
   assignment addressed to the Radiocommunication Bureau of the ITU, and
   have it lodged before the system requirements review rather than
   after the band has been designed into the link.

## Obligations

| Item | Step |
|---|---|
| ECSS-E-ST-50C Rev.2 5.6.12.2a | 8 |

## Pitfalls

- Testing the centre frequency against the allocation edges. It passes for
  every band whose upper half spills out, which is exactly the case that
  reaches a coordination filing.
- Treating a secondary allocation as a pass. The link is entitled to
  transmit and entitled to nothing else, and the operations concept that
  assumed protection has to change.
- Comparing an edge to a boundary with a bare strict inequality. Two
  arithmetically identical edges can land either side of the boundary on
  different platforms, so the verdict changes with the machine.
- Ignoring the region because the mission is global. A spacecraft is
  global, the ground stations are not, and the allocation that matters is
  the one over the station taking the pass.
- Using the symbol rate as the necessary bandwidth. It understates the
  occupied band, and the understatement is on both edges at once.
- Reporting no-allocation and partially-outside as one failure. One needs
  a different band, the other needs a shift of a few megahertz, and the
  merged finding hides which.
- Choosing the band and stopping. The selection is the input to an
  assignment request, and a request lodged after the system requirements
  review arrives with the link already designed around frequencies
  nobody has yet been granted.

## Behavior contract (gate 3)

Frequency, bandwidth and region validation, allocation and request
normalisation, the occupied edges, allocation occupancy, the feasible
centre range, the four-way verdict with a tolerance at the allocation
boundary, primary preference over secondary, the spill quantification and
the ranking of candidate allocations are exercised by the gate 3 contract
test: scripts/test_e50_frequency_band_selection.py against
scripts/e50_frequency_band_selection_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_e50_frequency_band_selection.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
