---
name: e2008-diode-surface-finish-test
description: "Assess the finish quality shown by the contact surfaces of a protection diode under ECSS-E-ST-20-08C clause 9.6.9: refuse an examination carried out below the declared magnification, take the measured roughness against both the working ceiling and the unweldable ceiling, disposition every finish anomaly on its kind, depth and coverage rather than on how it looks, reject a blister outright, send oxidation and residue past their coverage allowances to review, and leave a diode unsentenced while either polarity carries no examination. Use when a protection diode contact surface finish record has to become a verdict. Trigger: ecss, e-st-20-08c-clause-9-6-9, diode-contact-surface-finish, diode-contact-roughness-ceiling, diode-finish-anomaly-coverage, diode-examination-magnification-floor, diode-contact-blister-rejection."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-diode-surface-finish-test, diode-contact-surface-finish, diode-contact-roughness-ceiling, diode-finish-anomaly-coverage, diode-examination-magnification-floor, diode-contact-blister-rejection, diode-finish-accumulated-coverage]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic -- Diode Surface Finish Test (space-systems/ecss/e2008-diode-surface-finish-test)

Use when the task is the examination of ECSS-E-ST-20-08C clause 9.6.9 --
what finish the contact surfaces of a protection diode show, and how a
list of finish observations becomes a verdict on a surface an
interconnect is about to be welded onto.

## Domain quick reference

- It reads like a cosmetic clause and it is not one. The finish is the
  surface the weld is made on, so every attribute the clause names is a
  weldability attribute wearing an appearance word.
- The examination is established before the finish is. A finish is
  described at a magnification and over an area, and a record naming
  neither describes whatever the operator happened to notice.
- An examination below the declared magnification has not looked hard
  enough to see the things the clause lists, and one covering part of
  the land has described that part. Both close the contact as not
  established rather than clean: a clean page can be a missing page.
- Roughness is taken against two ceilings. Past the working ceiling the
  surface is rougher than the process was qualified for and the weld
  may still be sound, so that is a review. Past the second the
  asperities are deeper than the weld can consume and the joint would
  sit on the peaks, so that is a rejection. One ceiling alone either
  fills a review queue or accepts a process that has visibly drifted.
- An anomaly is dispositioned on what it is, how deep it goes and how
  much it covers, never on how bad it looks.
- A blister is the clearest case. The finish above it is intact and the
  adhesion under it is already gone, so it rejects at any coverage, and
  a rule written on coverage alone waves a small one through.
- A pit is a depth question before it is a coverage question, because a
  pit through the deposit has reached what the deposit was protecting.
  Only a pit inside the depth allowance falls through to its coverage.
- Oxidation and residue are coverage questions with different
  allowances: neither hurts a weld in a small patch and both starve one
  when they spread. A nodule is a height question, because a protrusion
  holds the weld head off the surface around it.
- Accumulation is carried separately. A contact on which every single
  anomaly was admissible can still be mostly covered in admissible
  anomalies, and the total is summed rather than unioned because
  overlapping findings describe a surface worked twice.
- A diode has two contact surfaces. A polarity with no examination is
  not a clean polarity.

## Workflow

1. Validate the criteria set first: magnification floor, examined
   fraction floor, both roughness ceilings, the per-kind depth, height
   and coverage allowances and the total coverage allowance. Two
   roughness ceilings sitting on top of each other are refused, because
   that criteria set has no review band and scraps every rough land.
2. Normalise each polarity contact, its examination and its anomaly
   list, refusing a contact with no examination recorded.
3. Take the examination shortfalls first -- magnification and examined
   fraction -- and report both rather than the first. Either one closes
   the contact as not established.
4. Disposition the measured roughness against the working ceiling and
   then the unweldable ceiling.
5. Disposition each anomaly by kind: a blister rejects, a pit on its
   depth and then its coverage, a nodule on its height, oxidation and
   residue on their own coverage allowances. A value landing exactly on
   a bound passes; the comparison tolerance absorbs representation
   error and the bound itself does not move.
6. Total the coverage across every anomaly and apply the accumulation
   allowance, which can send a contact to review on a record whose
   every entry passed.
7. Roll up by severity rather than record order, name the attribute
   that governed each contact, and refuse to sentence a diode while
   either polarity carries no examination.

## Pitfalls

- Accepting a contact on a record that lists nothing. An examination at
  the wrong magnification lists nothing either, and the two look
  identical in the file.
- Taking an examined fraction as a formality. A land examined over half
  its area has a verdict about half its area.
- Carrying one roughness ceiling. The working ceiling alone turns
  process drift into scrap; the far one alone accepts a surface the
  process was never qualified to produce.
- Dispositioning a blister on its coverage. The coverage of a blister
  describes how much adhesion is visibly gone, not how much is gone.
- Dispositioning a pit on its coverage first. A single pit through the
  deposit covers almost nothing and has reached the substrate.
- Giving oxidation and residue the same allowance because both look
  like discolouration. They load a weld differently and the criteria
  hold them apart.
- Accepting a contact because every anomaly passed. The accumulation
  allowance exists for exactly that record.
- Unioning overlapping findings and hiding a surface worked twice.
- Sentencing a diode on one polarity.
- Comparing a roughness, a depth or a coverage against its allowance by
  bare arithmetic. These are measured values and summed fractions, so a
  figure that should sit exactly on a bound can evaluate a few units in
  the last place off it; the comparison absorbs that representation
  error while the allowance stays untouched.

## Behavior contract (gate 3)

The criteria validation, the magnification and examined-fraction
shortfalls, the two-ceiling roughness rule, the per-kind anomaly
dispositioning, the blister rejection, the pit depth-before-coverage
order, the nodule height rule, the oxidation and residue allowances, the
accumulated coverage rule, the governing-attribute report and the
two-polarity completeness rule are exercised by the gate 3 contract
test: scripts/test_e2008_diode_surface_finish_test.py against
scripts/e2008_diode_surface_finish_test_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_diode_surface_finish_test.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
