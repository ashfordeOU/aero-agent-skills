---
name: e2008-diode-contact-void-limits
description: "Use when a protection diode void survey has to be sentenced. Evaluate the voids and bubbles recorded on either polarity contact of a protection diode against the quarter-millimetre ceiling of ECSS-E-ST-20-08C clause 9.6.2.5.2: govern each cavity by its maximum extent rather than an area-equivalent diameter that hides an elongated bubble, merge cavities whose edges have closed to within the coalescence gap and re-measure the span across the pair, keep a cavity landing exactly on the ceiling inside it, total the voided fraction of each land, and refuse a diode whose anode or cathode was never surveyed. Trigger: ecss, e-st-20-08-photovoltaic-assembly-scope, protection-diode-contact-voids, diode-void-maximum-extent, diode-void-coalescence-merge, diode-contact-voided-fraction, diode-quarter-millimetre-void-ceiling."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-diode-contact-void-limits, protection-diode-contact-voids, diode-void-maximum-extent, diode-void-coalescence-merge, diode-contact-voided-fraction, diode-quarter-millimetre-void-ceiling, diode-void-equivalent-diameter-trap]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic -- Diode Contact Void Limits (space-systems/ecss/e2008-diode-contact-void-limits)

Use when the task is the void screen of ECSS-E-ST-20-08C clause
9.6.2.5.2 -- voids and bubbles have been surveyed on the contacts of a
protection diode, and each of them has to be measured against a
quarter-millimetre ceiling that applies on either polarity.

## Domain quick reference

- Diameter has two meanings for a cavity that is not round, and only
  one of them is the clause's. The area-equivalent diameter is what a
  spreadsheet reaches for and it is the wrong one.
- An elongated bubble is exactly where the two part company. A cavity
  four tenths of a millimetre long and one tenth wide returns an
  equivalent diameter of two tenths and passes, while running past the
  ceiling along the direction the weld has to bridge.
- The governing figure is therefore the maximum extent. The equivalent
  diameter is still worth computing, because the gap between the two is
  how the elongated ones are found and named.
- Cavities do not stay separate. Two bubbles whose edges have closed to
  within a coalescence gap behave as one cavity under a weld pulse, so
  the span across the pair is what the ceiling applies to.
- Sentencing a closed pair one at a time is how a group plainly over
  the ceiling gets through as two passes. Each one alone would have
  been accepted; that is the point of merging them first.
- Coalescence is per polarity. A cavity on the anode does not merge
  with one on the cathode whatever the coordinates say, because they
  are not the same surface.
- Either polarity means both of them have a record. A contact nobody
  surveyed is not a contact without cavities, and a diode accepted on
  its anode survey alone has been shown nothing about the cathode.
- A cavity recorded against a polarity the diode does not declare was
  never sentenced by anybody, so it is named rather than dropped.
- A cavity exactly on the ceiling is inside it. The ceiling is a limit
  the cavity stays within, so the comparison absorbs the representation
  error a computed span carries instead of scrapping a part on a
  difference in the last place of a float.
- Many small cavities use a land up even when every one of them is
  inside the ceiling, so the voided area fraction is tracked alongside
  the individual extents.

## Workflow

1. Normalise each polarity contact and each cavity, refusing a minor
   extent longer than the major one -- the major is by definition the
   longest dimension measured.
2. Take only the cavities of the contact's own polarity; cavities never
   merge across polarities.
3. Group cavities that have closed on one another, following the chain
   so three in a row become one group rather than two pairs.
4. Measure each group's span: a lone cavity spans its own major extent,
   a group spans the widest centre distance plus both radii.
5. Sentence each group against the ceiling, with a review band below it
   for a cavity that will go over on the next survey.
6. Total the voided area of the contact and apply the area allowance,
   which can send a land to review on cavities that each passed.
7. Name the cavities an equivalent diameter would have let through, so
   the elongated ones are visible in the record.
8. Check both polarities were surveyed, name any cavity on an undeclared
   polarity, and roll up by severity rather than record order.

## Pitfalls

- Comparing the area-equivalent diameter with the ceiling. It is the
  single defect this clause is most often implemented with.
- Recording a minor extent longer than the major and carrying it
  through as if the labels were interchangeable.
- Sentencing cavities one at a time when they have closed on one
  another, so a group over the ceiling passes as two accepts.
- Merging cavities across polarities on coordinates alone.
- Accepting a diode on one polarity survey, or dropping a cavity
  recorded against a contact the part does not declare.
- Rejecting a cavity that sits exactly on the ceiling. It is within the
  limit, and a strict comparison against a computed span scraps parts on
  the last place of a float; the comparison has to absorb that error
  while the ceiling itself stays untouched.
- Accepting a land because every cavity was small. The area fraction
  exists for exactly that case.
- Reporting a group verdict without the span that produced it, so the
  reviewer cannot see which cavities were merged.

## Behavior contract (gate 3)

The maximum-extent rule, the equivalent-diameter trap, the elliptical
cavity area, the per-polarity coalescence with chain following, the
group span, the ceiling and review band including the exactly-on-the-
ceiling case, the voided area allowance, the two-polarity survey
completeness rule, the undeclared-polarity cavities and the severity
rollup are exercised by the gate 3 contract test:
scripts/test_e2008_diode_contact_void_limits.py against
scripts/e2008_diode_contact_void_limits_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_diode_contact_void_limits.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
