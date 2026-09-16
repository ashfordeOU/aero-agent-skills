---
name: e2008-sca-coverglass-adhesive-defects
description: "Use when a coverglassed cell has been examined and the adhesive record needs a disposition. Assess the coverglass adhesive of a solar cell assembly for delamination and discolouration under ECSS-E-ST-20-08C clause 6.4.3.1.6, where the zones behind the rear welds are carved out: intersect every indication footprint with the exempt zones, credit only the single zone that covers the most of it so two overlapping welds cannot exempt the same area twice, charge the part that overhangs, weight a discoloured patch by its grade into a transmission loss, and return accept, refer-for-review or reject with the straddling indications and any unmapped weld named apart. Trigger: ecss, e-st-20-08c, clause-6-4-3-1-6, sca-adhesive-weld-zone-exemption, rear-weld-exempt-zone-geometry, adhesive-delamination-containment-check, straddling-indication-credit, sca-adhesive-discolouration-grading."
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
  tags: [ecss, e-st-20-electrical-scope, e2008-sca-coverglass-adhesive-defects, e-st-20-08c, sca-adhesive-weld-zone-exemption, rear-weld-exempt-zone-geometry, adhesive-delamination-containment-check, straddling-indication-credit, sca-adhesive-discolouration-grading]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Solar Cell Assemblies — Coverglass Adhesive Defects (space-systems/ecss/e2008-sca-coverglass-adhesive-defects)

Use when the task is clause 6.4.3.1.6 of ECSS-E-ST-20-08C: the adhesive under
a coverglass is asked to be free of delamination and of discolouration, with
the zones behind the rear welds carved out of that demand. This leaf turns
that carve-out into a containment test and grades what falls outside it.

## Domain quick reference

- The carve-out is positional, not a size allowance. It does not say that a
  certain area of delamination is tolerated; it says the area behind a weld is
  not the adhesive's fault, because the welding heat went into the cell from
  the other face and the design asked for it.
- That makes the screen a geometry problem. Each indication footprint is
  intersected with the exempt zones, and only the part falling outside them is
  charged against the bond line.
- Centre position is not containment. An indication whose centre sits behind a
  weld can still overhang the zone, and crediting it whole because of where
  its middle is exempts adhesive the weld never touched.
- A straddling indication is charged for its overhang and credited for the
  rest, and it is reported as straddling so a reviewer sees the split rather
  than a bare number.
- Overlapping exempt zones are never summed. The credit is taken from the
  single zone that covers the most of the indication, because adding the
  overlaps exempts the shared area twice and turns two adjacent welds into a
  licence for a delamination neither of them caused. A single-zone credit can
  only understate the exemption; it can never invent one.
- Delamination and discolouration are not the same failure. Delamination is a
  separation in the load and heat path, so its allowance is the tighter one.
  Discolouration is an optical loss, so it is weighted by grade into a
  transmission cost against the bonded area.
- Nothing here is reworkable. The adhesive is under a bonded glass, so a
  recovery means taking the glass off, which is a new build rather than a
  rework; the dispositions stop at accept, refer-for-review and reject.
- A weld with no exempt zone declared is worse than a weld with a large one.
  Without the map, an indication behind that weld is charged to the adhesive,
  so the screen is held open rather than run on a partial exemption map.

## Workflow

1. Take the bonded area, the declared rear weld count and the exempt zone for
   each weld. Refuse more zones than there are welds, and hold the screen open
   when a weld carries no zone.
2. Per indication, take its footprint and, for a discolouration, its grade.
3. Intersect the footprint with every exempt zone and keep the largest single
   credit, naming the zone it came from. Never add two zones together.
4. Charge the counted area as the footprint less that credit, floored at zero,
   and mark the indication as straddling when the credit was partial.
5. Weight a discolouration by its grade into an effective area; a delamination
   carries its counted area unweighted.
6. Grade the effective area: at or under the examination floor it accepts,
   under the kind's limit it refers, past that limit it rejects.
7. Close with the cell verdict, the counted and exempt totals, the cumulative
   counted fraction, the transmission loss, the wholly exempt and straddling
   identifiers, and any weld left unmapped.

## Pitfalls

- Reading the weld carve-out as an area budget. It exempts a place, not a
  quantity, and a screen that spends it as a budget accepts delamination
  nowhere near a weld.
- Crediting an indication in full because its centre sits behind a weld.
  Containment is about the footprint, and the overhang is exactly the part
  that was never welded over.
- Summing the exemption from two overlapping zones. The shared area is
  credited twice and a real delamination between two welds disappears.
- Applying the discolouration allowance to a delamination. One is an optical
  loss and the other is a separation in the load path; the same area means
  very different things.
- Grading discolouration on area alone. A faint haze and an opaque brown
  patch of equal size cost the cell completely different current, which is
  what the grade weighting is for.
- Offering a rework. Reaching the adhesive means removing the glass, so a
  rework line on this record means the disposition was never made.
- Running the screen on a partial exemption map. The missing zone does not
  read as an absent exemption; it reads as adhesive damage, and the cell is
  scrapped for a weld nobody recorded.
- Comparing an area with a limit by bare arithmetic. The exempt area comes out
  of an inverse-cosine geometry and every limit is a product of a criteria
  fraction and a measured area, so a value exactly on a limit can evaluate a
  few units in the last place above it; the comparison absorbs that
  representation error while the limit stays untouched.

## Behavior contract (gate 3)

The circle intersection geometry, the single-zone exemption credit, the
straddle split, the tighter delamination limit, the grade-weighted
transmission loss, the cumulative counted fraction and the unmapped-weld
completeness rule are exercised by the gate 3 contract test:
scripts/test_e2008_sca_coverglass_adhesive_defects.py against
scripts/e2008_sca_coverglass_adhesive_defects_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_sca_coverglass_adhesive_defects.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
