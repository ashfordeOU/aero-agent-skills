---
name: e2008-cell-coating-adherence-test
description: "Use when a coating and contact adherence run has to be sentenced. Assess the durability of a bare solar cell's antireflection coating together with its cell and diode contact metallisation under the adherence method of ECSS-E-ST-20-08C clause 7.5.8: refuse a run that reached only one of the surfaces the specimen carries, take the removed area of each against the allowance that belongs to it, turn the stripped coating share into the current the cell gives up where bare semiconductor now reflects, group every surface as intact, inside its allowance or past it, and fail a lot on lifted metallisation however small the share. Trigger: ecss, e-st-20-08c-clause-7-5-8, bare-cell-antireflection-coating-adherence, cell-contact-metallisation-lift, diode-contact-adherence-surface, coating-removed-area-allowance, stripped-coating-current-loss."
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
  tags: [ecss, e-st-20-08-solar-cell-scope, e2008-cell-coating-adherence-test, bare-cell-antireflection-coating-adherence, cell-contact-metallisation-lift, diode-contact-adherence-surface, coating-removed-area-allowance, stripped-coating-current-loss, bare-cell-adherence-surface-coverage]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Solar Cells -- Cell Coating Adherence Test (space-systems/ecss/e2008-cell-coating-adherence-test)

Use when the task is clause 7.5.8 of ECSS-E-ST-20-08C: one adherence
method applied to three surfaces of a bare cell -- the antireflection
coating, the cell contact metallisation and, where the cell carries a
bypass diode, the diode contact metallisation -- to show that none of
them comes away from the cell in service.

## Domain quick reference

- The method is shared and the failure modes are not. Coating that
  lifts costs current for the life of the mission; cell metallisation
  that lifts is an interconnect joint nobody will be able to make; diode
  metallisation that lifts takes the shadow protection of a whole string
  with it.
- So the surfaces carry different allowances. A coating may lose a
  little area and still do its job, while metallisation is held to a
  much tighter number -- a surface that gives way under a tape is a
  surface that will give way under a weld.
- A run that reached one surface is not a lenient version of this check;
  it is a different check. The surfaces the specimen carries are the
  surfaces the method has to reach, and a missing one stops the
  assessment rather than passing quietly.
- Which surfaces are required is a property of the specimen. A cell
  without a bypass diode is not failed for a diode surface it does not
  have, and a diode surface reported on such a cell is a record that
  does not describe the hardware in front of the operator.
- Coating loss is not a cosmetic fraction. The stripped patch reverts to
  the reflectance of bare semiconductor, so the current given up is the
  stripped share times the relative fall in absorbed light, referred to
  the coated cell rather than to an ideal one.
- A bare reflectance that does not exceed the coated one is a sign error
  in the optical record. Taken at face value it turns coating loss into
  a current gain, so it is refused rather than computed through.
- Removal is graded in three steps, not two. Nothing came away; some
  did and stayed inside the allowance; more did than the allowance
  covers. The middle step is an ordinary outcome for a coating and a
  standing warning for metallisation.
- The allowances, the current-loss cap, the lot reject share and the
  specimen floor are declared project policy rather than physical
  constants, so they are stated with the result.

## Workflow

1. Take the run: one record per specimen, each with the surfaces the
   method was applied to, their areas, the area that came away, and for
   the coating the coated and bare reflectance.
2. Work out which surfaces the specimen was required to present, from
   whether it carries a bypass diode, and compare that with what the run
   actually exercised.
3. Stop on any specimen that is short a surface or reports one it does
   not have. The run is repeated rather than sentenced, because the
   missing surface carries no evidence at all.
4. Reduce each surface to the fraction of its area that came away and
   group it against the allowance that belongs to that surface, not
   against a single house number.
5. Turn the stripped coating share into the current the cell gives up,
   and hold it against its own cap -- a coating loss can sit inside the
   area allowance and still cost more current than the budget carries.
6. Sentence each specimen, then roll the lot up: the rejected share
   against its allowance, and any lifted metallisation named on its own
   because no lot allowance covers it.

## Pitfalls

- Applying the method to the coating alone and reporting the cell as
  adherent. The two metallisations are the surfaces a later joining
  process depends on, and they were never touched.
- Holding metallisation to the coating allowance. A few percent of a
  coating is a durability observation; a few percent of a contact is a
  weld that will not hold.
- Reading removed coating area as a cosmetic number. The patch reflects
  like bare semiconductor from then on, so the honest unit is current
  given up, not square millimetres.
- Trusting an optical record whose bare reflectance sits at or under the
  coated one. The arithmetic still runs and reports coating loss as a
  benefit, which is exactly the kind of pass nobody re-reads.
- Failing a diodeless cell for a diode surface, or crediting a diode
  surface reported on one. Both mean the record and the hardware
  disagree, and the disagreement is the finding.
- Collapsing removal into pass and fail. Losing nothing and losing
  almost the whole allowance are both passes, and only one of them is
  worth a second look on the next lot.
- Comparing a removed-area fraction, a current loss or a rejected share
  against its limit by bare arithmetic. All three are quotients of
  measured quantities, so a specimen cut exactly to an allowance can
  evaluate a unit in the last place over it and read as a reject on one
  platform and as compliant on another.

## Behavior contract (gate 3)

The per-specimen required-surface set, the coverage refusal and its
unexpected-surface case, the per-surface allowances, the removed-area
fractions, the stripped-coating current loss with its reflectance sign
refusal, the three-step removal grouping, the specimen verdict, the lot
reject allowance and the metallisation rule are exercised by the gate 3
contract test: scripts/test_e2008_cell_coating_adherence_test.py against
scripts/e2008_cell_coating_adherence_test_logic.py (stdlib unittest,
offline). Run: python3 scripts/test_e2008_cell_coating_adherence_test.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
