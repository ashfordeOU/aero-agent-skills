---
name: e2008-full-visual-inspection-purpose
description: "Use when establish whether a full visual examination of completed solar-array hardware met the detection purpose ECSS-E-ST-20-08C clause 5.5.3.2.1 sets: confirm every declared zone of the article was examined so the inspected area spans the complete hardware, derive from each zone's magnification the smallest feature it could have shown and compare that with the imperfection size the requirement has to detect, check the illuminance each zone was examined under and require an access means for any zone the inspector could not reach, group the imperfections found by severity to derive the article disposition, and withhold completeness from an examination that left a zone out or examined it below its conditions. Trigger: ecss, e-st-20-08c-clause-5-5-3-2-1, full-visual-examination, solar-array-imperfection-detection, visual-inspection-zone-coverage, inspection-magnification-resolvable-feature, inspection-illuminance-floor, imperfection-severity-disposition."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-full-visual-inspection-purpose, full-visual-examination, solar-array-imperfection-detection, visual-inspection-zone-coverage, inspection-magnification-resolvable-feature, imperfection-severity-disposition]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies -- Full Visual Inspection Purpose (space-systems/ecss/e2008-full-visual-inspection-purpose)

Use when the task is the clause 5.5.3.2.1 purpose of ECSS-E-ST-20-08C's full
visual inspection -- deciding whether an examination already carried out on
completed solar-array hardware actually did what the clause asks of it:
detect imperfections across the whole article, not across the part of it that
was convenient to look at.

## Domain quick reference

- The word doing the work in the clause is "full". The examination is a
  detection instrument aimed at the complete hardware, so its result is only
  as good as the fraction of the article it was pointed at. Coverage is
  therefore a property of the inspection, reported alongside what it found.
- Coverage is an area fraction, not a zone count. A rear harness run that is
  a tenth of the article's area is a tenth of the coverage, however many
  zones the inspection sheet happens to divide the front laydown into.
- What a zone examination can detect follows from the magnification used
  there: an unaided eye resolves roughly a tenth of a millimetre at working
  distance, and an aided view resolves that divided by its magnification. A
  zone examined at unity magnification cannot report the absence of a
  50 micrometre crack -- it can only report that none was seen.
- Illuminance is the second half of the optics. Below roughly a thousand lux
  a surface examination stops being a detection activity, whatever
  magnification is in front of it.
- A zone the inspector cannot reach directly is not excluded from the
  article; it needs a declared access means -- a mirror, a borescope, a
  removed panel -- and an examination that names none for such a zone has a
  gap in it that the coverage number alone will not show.
- The imperfections found are a separate output from whether the examination
  was complete. A clean sheet from a partial examination and a clean sheet
  from a whole one carry very different weight, so both are reported.

## Workflow

1. Validate the declared zones of the article: identifier, area,
   magnification, illuminance, whether each was examined, and whether each
   was reachable without an aid. Reject a duplicated zone identifier; two
   entries for one zone make the area sums ambiguous.
2. Sum the areas and compute the coverage fraction, treating a whole-article
   result as whole through a named tolerance rather than by ignoring a real
   gap.
3. Per zone, derive the smallest feature its magnification could have shown
   and compare it with the imperfection size the requirement has to detect;
   a zone that just reaches the target size passes through the tolerance.
4. Check each zone's illuminance against the floor, and require an access
   means to be declared for any zone flagged as not directly reachable.
5. Group the imperfections found by severity grade and derive the article
   disposition from the worst grade present: critical rejects, major sends
   the article to repair, minor alone accepts.
6. Report completeness only when the coverage is whole and every zone met
   its optical and access conditions; list every zone that was left out and
   every condition that was not met.

## Pitfalls

- Reading a clean inspection sheet as an absence of imperfections. The sheet
  records what was seen; without the coverage fraction and the per-zone
  resolvable feature size it does not support a statement about the article.
- Counting zones instead of area. Splitting the accessible face into many
  zones and the hidden face into one makes a partial examination look
  thorough on any count-based metric.
- Accepting a zone examined at a magnification too coarse for the target
  imperfection. The zone was examined, so it never appears as a coverage
  gap; it has to be caught by comparing the resolvable feature against the
  size the requirement names.
- Letting an unreachable zone pass on the inspector's word. A zone that is
  not directly accessible needs its access means written down, because the
  next inspection has to be able to repeat the examination.
- Merging the disposition into the completeness verdict. An article with a
  minor imperfection and a whole examination is accepted; an article with
  nothing found and a zone skipped is not -- and collapsing the two hides
  which one is in hand.

## Behavior contract (gate 3)

The zone validation, area-weighted coverage, resolvable-feature derivation,
illuminance and access checks, severity grouping, disposition rule and the
completeness verdict are exercised by the gate 3 contract test:
scripts/test_e2008_full_visual_inspection_purpose.py against
scripts/e2008_full_visual_inspection_purpose_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_full_visual_inspection_purpose.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
