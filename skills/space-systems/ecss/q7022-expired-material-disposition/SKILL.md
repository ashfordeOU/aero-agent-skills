---
name: q7022-expired-material-disposition
description: "Determine the disposition of a limited-shelf-life material lot found past its expiry date under ECSS-Q-ST-70-22C: measure the overrun in days and as a fraction of the original shelf life, screen the lot for re-validation eligibility against family, storage history, extension budget and overrun limit, grade any re-validation measurements against their acceptance windows, and close with re-test, extend, reject or scrap plus a sized new expiry date. Use when an expired drum, batch or reel is found in stores, on a kitting list or at a work station. Trigger: ecss, q-st-70-22c, expired-material-disposition, shelf-life-extension-sizing, shelf-life-revalidation-grading, shelf-life-overrun-fraction, expired-lot-scrap-decision."
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
  tags: [ecss, q-st-70-22c-limited-shelf-life-control, q-st-70-22c, q7022-expired-material-disposition, expired-material-disposition, shelf-life-extension-sizing, shelf-life-revalidation-grading, shelf-life-overrun-fraction]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Limited Shelf Life — Expired Material Disposition (space-systems/ecss/q7022-expired-material-disposition)

Use when the task is the use-control clause of ECSS-Q-ST-70-22C applied to a
lot that is already past its expiry date: whether it is re-tested, extended,
refused for the intended use, or physically scrapped.

## Domain quick reference

- An expiry date is a statement about a lot that has been stored as specified.
  Once it is passed, the lot has no status at all until a disposition gives it
  one; leaving it on the shelf with a sticker is not a disposition, because
  nothing stops it being picked for the next kit.
- The overrun matters as a fraction of the original shelf life, not in days.
  Thirty days past a 90-day primer is a third of its life; the same thirty days
  on a three-year elastomer is noise. One fraction covers both, which is why
  the eligibility rule is written against the fraction.
- Re-validation is only meaningful where a measurable property tracks the
  ageing mechanism. Where the mechanism is internal and progressive — an
  initiated pyrotechnic composition, a cast propellant grain, a getter that has
  been quietly absorbing since it was packed — no bench measurement reads it
  back, and the only honest disposition is scrap.
- A storage excursion is worse than an overrun. An overrun is a known amount of
  ageing at a known condition; an excursion is an unknown amount at an unknown
  condition, and there is no baseline left to extrapolate a re-test result
  over. Eligibility is removed, not merely tightened.
- The extension budget is finite and shrinking. Each granted extension buys a
  smaller one next time, because the measurable properties are the last to move
  and a lot that has been re-validated twice is being read by an instrument
  that no longer resolves what is happening inside it.
- A property that was not measured is not a property that passed. An incomplete
  re-validation is a failed one, otherwise the acceptance set quietly shrinks
  to whatever the laboratory found convenient.

## Workflow

1. Compute days past expiry from the assessment date, and the overrun as a
   fraction of the lot's original shelf life. A lot not actually past its
   expiry is returned to normal use control rather than dispositioned here.
2. Screen eligibility before booking any test: a family with no defined
   re-validation route, a storage history carrying an unquantified excursion,
   an exhausted extension budget, or an overrun past the allowed fraction each
   end the lot at scrap on their own.
3. Where the lot is eligible and no re-validation results exist, disposition it
   to re-test and hold it in quarantine; do not let an eligible lot read as an
   accepted one.
4. Grade every acceptance property against its window, treating an unmeasured
   property as a failure and absorbing an exactly-on-limit measurement with a
   named tolerance rather than widening the window.
5. On a failed re-validation, scrap a flight-critical lot and reject a
   non-flight one, so that material with a residual non-flight use is not
   destroyed and flight material never survives a failure.
6. On a clean re-validation, size the extension as a bounded fraction of the
   original shelf life that halves with each extension already granted, issue
   the new expiry from the assessment date, and report it with the overrun and
   the graded results that justified it.

## Pitfalls

- Extending a lot on the strength of its appearance. Viscosity and colour are
  the properties that move last; the acceptance window set exists so that the
  decision does not rest on what the drum looks like when it is opened.
- Sizing the extension from the time already used rather than from the
  original shelf life. Extensions granted that way grow as the lot ages, which
  is the opposite of the intended direction.
- Reading a storage excursion as an overrun to be added to the days past
  expiry. The two are different kinds of ignorance: an excursion removes the
  baseline, so it removes eligibility outright.
- Scrapping every failed lot. Material with a genuine non-flight use is
  refused for the intended application and retained; destroying it early costs
  the programme its trial and rework stock.
- Letting a partially measured re-validation pass. If a property in the
  acceptance set was not measured, the result is incomplete, and incomplete is
  a failure, not a smaller pass.
- Granting an extension on a lot whose budget is spent. The budget is the point
  at which measurement stops resolving the ageing, and moving it turns the
  whole re-validation route into paperwork.

## Behavior contract (gate 3)

The overrun arithmetic, family and storage eligibility screen, extension
budget, acceptance-window grading, extension sizing, new-expiry issue and the
four dispositions are exercised by the gate 3 contract test:
scripts/test_q7022_expired_material_disposition.py against
scripts/q7022_expired_material_disposition_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7022_expired_material_disposition.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
