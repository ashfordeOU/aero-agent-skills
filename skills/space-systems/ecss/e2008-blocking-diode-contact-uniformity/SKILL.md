---
name: e2008-blocking-diode-contact-uniformity
description: "Evaluate whether the contact metallisation of a blocking diode is even enough that the interconnector weld made on it later comes out reproducible and adequate, under ECSS-E-ST-20-08C clause 12.6.13: refuse a contact with no declared weld footprint, leave a footprint the map never reached unjudged rather than averaging it into the contact, hold every reading inside the weldable band and each spread against the mean of its own footprint, and compare the footprint means against one another because a single weld schedule runs on all of them. Use when a blocking diode contact thickness map has to become a weld readiness verdict. Trigger: ecss, e-st-20-08c-clause-12-6-13, blocking-diode-weld-footprint-thickness, blocking-diode-interconnector-weld-readiness, blocking-diode-weldable-thickness-band, blocking-diode-footprint-spread-fraction, blocking-diode-weld-schedule-reproducibility, blocking-diode-contact-map-coverage."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-blocking-diode-contact-uniformity, blocking-diode-weld-footprint-thickness, blocking-diode-interconnector-weld-readiness, blocking-diode-weldable-thickness-band, blocking-diode-footprint-spread-fraction, blocking-diode-weld-schedule-reproducibility, blocking-diode-contact-map-coverage]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies -- Blocking Diode Contact Uniformity (space-systems/ecss/e2008-blocking-diode-contact-uniformity)

Use when the task is the clause 12.6.13 check of ECSS-E-ST-20-08C: the
contact of a blocking diode has been mapped for thickness, and the evenness
of that contact has to be turned into a statement about the interconnector
weld that will be made on it later.

## Domain quick reference

- The evenness is not checked for its own sake. An interconnector will be
  welded onto this contact, and a weld schedule is set once and then run on
  every joint. The question is whether one schedule will give the same,
  adequate weld everywhere it is applied, which is narrower than a general
  uniformity question and answers differently.
- Two different evennesses follow from that, and a map reduced to a single
  spread figure loses one of them. Inside one footprint the metal under the
  electrode has to stay inside the band the schedule was set for. Between
  footprints, the means have to agree, because the same schedule serves
  them all.
- The band is applied per reading, not to the footprint mean. A footprint
  whose readings straddle the band fails even when its mean sits in the
  middle of it, because the electrode lands on the metal that is actually
  there rather than on the average.
- Too thin and the weld burns through toward the semiconductor; too thick
  and the energy never reaches the interface. The failure modes are
  opposite, so the floor and the ceiling are both held and a part can
  breach either.
- Footprints that each pass their own band can still fail together. A
  contact whose first footprint sits near the floor and whose last sits
  near the ceiling welds reproducibly nowhere, and that finding is
  invisible to a per-footprint check.
- A footprint the map never reached is not a pass. Readings clustered away
  from the weld sites describe metal no electrode will touch, so a
  footprint carrying fewer readings than the policy asks for closes the
  assessment as incomplete rather than being averaged into the contact.
- A reading sitting exactly on a band edge or a spread exactly on its limit
  is admissible; the comparison tolerance exists to absorb representation
  error rather than to widen the band.

## Workflow

1. Validate the declared weld readiness policy first: the weldable
   thickness band, the largest spread admissible inside one footprint, the
   advisory band under it, the largest disagreement admissible between
   footprint means, and the readings a footprint needs before it can be
   judged. A band whose floor is not below its ceiling admits no thickness
   and is refused rather than used.
2. Confirm the contact declares its interconnector weld footprints. With
   none declared there is nowhere to apply an evenness figure, and the
   assessment closes on footprints not established.
3. Validate every mapped reading: a non-blank identifier, a finite
   position along the contact and a positive thickness. A contact carrying
   no reading is unknown rather than adequate.
4. Take the readings falling inside each footprint, edges included, and
   reduce them to count, mean, extremes and the spread against that
   footprint mean. Reject a duplicate footprint identifier rather than
   grading the same site twice.
5. Grade each footprint against the band per reading and against the spread
   limit, naming every reason it missed rather than the first: below the
   weld floor, above the weld ceiling, uneven across the footprint.
6. Close on contact map incomplete if any footprint was never mapped
   densely enough to grade. A contact part-judged on the footprints that
   happened to be covered is not a contact verdict.
7. Take the spread of the footprint means against their own average and
   hold it against the reproducibility limit, because one schedule runs on
   all of them.
8. Report the worst footprint and its spread beside the verdict, and raise
   an advisory for every weldable footprint already at or past the advisory
   band. Advisories are reported with the verdict and do not move it.
9. Close on one verdict: weld footprints not established, contact map
   incomplete, contact not weld ready, or contact ready for interconnector
   welding.

## Pitfalls

- Quoting one spread for the whole contact. It answers the within-footprint
  question and the between-footprint question at once and therefore answers
  neither, and the schedule that fails is usually the one the second
  question would have caught.
- Applying the weldable band to the footprint mean. A site running thin at
  one edge and thick at the other averages into the middle of the band and
  welds badly at both ends.
- Treating a sparse footprint as even. Three readings in one corner of a
  weld site say nothing about the corner the electrode will actually land
  on, so coverage is checked before any spread is quoted.
- Mapping the contact away from the weld sites because the probe reaches
  there more easily. Metal nobody will weld on is not evidence about the
  weld.
- Reporting weld readiness with no worst footprint and no mean spread. The
  verdict alone hides the difference between a contact that comfortably
  supports one schedule and one that barely does, and the next build has
  nothing to compare against.

## Behavior contract (gate 3)

The policy validation, the footprint and reading validation, the selection
of readings inside each footprint with the edges included, the per-reading
band and the spread against the footprint mean, the multi-reason grading,
the unmapped-footprint stop, the disagreement between footprint means, the
worst footprint, the marginal advisories and the closing verdict are
exercised by the gate 3 contract test:
scripts/test_e2008_blocking_diode_contact_uniformity.py against
scripts/e2008_blocking_diode_contact_uniformity_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_blocking_diode_contact_uniformity.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
