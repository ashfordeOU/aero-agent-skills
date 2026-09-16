---
name: e2008-diode-contact-area-inspection
description: "Use when a protection diode mark list has to become a contact area verdict. Assess the contact areas of a protection diode for digs, scratches and probe marks under ECSS-E-ST-20-08C clause 9.6.2.5.1: place every recorded mark against the anode and cathode geometry before dispositioning it, charge a straddling mark only the part that overlaps, reject a mark that has bared the semiconductor under a weld land, send thinned metal to review, track the probe witnesses and the clear weld-land fraction left on each contact, and hold a diode unsentenced while either polarity carries no record. Trigger: ecss, e-st-20-08-photovoltaic-assembly-scope, protection-diode-contact-area-marks, diode-weld-land-clear-fraction, diode-probe-witness-count, diode-contact-polarity-completeness, diode-contact-metallisation-state."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-diode-contact-area-inspection, protection-diode-contact-area-marks, diode-weld-land-clear-fraction, diode-probe-witness-count, diode-contact-polarity-completeness, diode-contact-metallisation-state, diode-contact-mark-containment]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic -- Diode Contact Area Inspection (space-systems/ecss/e2008-diode-contact-area-inspection)

Use when the task is the contact-area screen of ECSS-E-ST-20-08C
clause 9.6.2.5.1 -- digs, scratches and probe marks have been recorded
on a protection diode, and each of them has to be placed against the
anode and cathode geometry and dispositioned on the state of the
metallisation underneath it.

## Domain quick reference

- A protection diode has two contact areas, one per polarity, and both
  are weld lands: the interconnect that carries the string current is
  welded or bonded onto them. That is what makes this a contact clause
  rather than a cosmetic one.
- Location comes first and it is a containment test, not a judgement. A
  mark sits inside a contact, straddles its edge or misses it, and only
  a mark with some overlap is this clause's business at all.
- A straddling mark contributes the overlapping part and nothing else.
  Charging its whole footprint to the contact inflates every area
  figure that follows.
- A mark touching the boundary without crossing it has no overlap, so
  it is outside. The edge itself is not contact area.
- The metallisation state decides the disposition and the mark's own
  size does not. A dig that displaced metal and left a continuous
  conductor has exposed nothing; the same dig that went through has
  bared semiconductor on the surface a weld is about to be made on.
- Thinned metal is the middle case that gets waved through. It is not
  bare and it is not sound, and a contact thinned past a working
  fraction of its deposit is one probe landing or one weld pulse from
  being bare, so it goes to review rather than being accepted because
  nothing shows through yet.
- A mark on the diode body away from either land is a real finding
  under other clauses and is not a rejection here. It is carried as an
  advisory so it reaches the clause that does own it.
- The diode has two polarities and a verdict needs both. A contact with
  no record is not a clean contact, and a diode accepted on its anode
  while the cathode was never looked at has been shown nothing.
- Two effects survive a contact on which every individual mark was
  admissible. Probe witnesses accumulate because the fixture lands on
  the same sites, so they are counted per contact. And the weld land
  gets used up: a contact can be fully metallised everywhere and still
  have too little untouched surface left to put a sound weld on.
- Overlapping marks are summed rather than unioned for the disturbed
  figure. A site worked twice has taken twice the working, which is the
  quantity the allowance is about.

## Workflow

1. Normalise each polarity contact into a footprint in the diode
   coordinate frame, rejecting a duplicate identifier on the same part.
2. Place every recorded mark against every contact and set aside the
   ones that overlap nothing; carry those as advisories rather than
   losing them.
3. Disposition each mark that overlaps: absent metallisation rejects,
   thinned metal is compared against the working fraction, intact metal
   is accepted with the mark recorded.
4. Total the bared footprint, the clear weld-land fraction and the
   probe witnesses for each contact.
5. Apply the contact-level allowances -- the clear fraction and the
   witness count -- which can send a contact to review on marks that
   each passed on their own.
6. Check both polarities carry a record and refuse to sentence the
   diode on one of them alone.
7. Roll up by severity rather than record order: the governing verdict
   per contact, then the diode verdict, the contacts not accepted, the
   total bared footprint and the marks that belong to another clause.

## Pitfalls

- Dispositioning a mark before placing it. A scratch on the diode body
  is somebody else's clause and rejecting the part on it here scraps a
  good diode for the wrong reason.
- Charging a straddling mark's full footprint to the contact.
- Treating a boundary touch as contained.
- Grading on the mark's size. The size drives the area totals; the
  metallisation state drives the disposition.
- Accepting thinned metal because nothing is showing through. The next
  probe landing is what the working fraction is protecting against.
- Losing an off-contact mark entirely because this clause does not
  reject on it.
- Accepting a diode on one polarity. The clause covers the contact
  areas, plural, and an uninspected land is not a clean land.
- Accepting a contact because every mark passed. The clear fraction and
  the witness count exist for exactly that case.
- Unioning overlapping marks and so hiding a site worked repeatedly.
- Comparing a fraction with its allowance by bare arithmetic. The
  fraction is a quotient of summed footprints, so a value that should
  sit exactly on the allowance can evaluate a few units in the last
  place off it; the comparison absorbs that representation error while
  the allowance stays untouched.

## Behavior contract (gate 3)

The containment test, the straddling overlap, the metallisation-state
dispositioning, the working-fraction review rule, the bared footprint,
the clear weld-land fraction, the probe witness count, the two-polarity
completeness rule and the severity rollup are exercised by the gate 3
contract test: scripts/test_e2008_diode_contact_area_inspection.py
against scripts/e2008_diode_contact_area_inspection_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_diode_contact_area_inspection.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
