---
name: e2008-ultraviolet-exposure-test-criteria
description: "Use when post-ultraviolet measurements are judged against the accepted loss. Verify that a photovoltaic specimen still respects its short circuit current limit once the ultraviolet exposure sequence has ended, per ECSS-E-ST-20-08C clause 6.4.3.15.3: confirm the accumulated dose completed the sequence, correct the pre-exposure and post-exposure illuminated readings back to reference irradiance and cell temperature so the comparison is between specimen states rather than measurement conditions, derive the short circuit current loss fraction and retention ratio for every specimen, and aggregate the worst case and the mean into one acceptance verdict. Trigger: ecss, e-st-20-08c-clause-6-4-3-15-3, post-ultraviolet-short-circuit-current-loss, ultraviolet-exposure-acceptance-limit, short-circuit-current-reference-correction, ultraviolet-exposure-sequence-completeness, solar-array-coupon-ultraviolet-acceptance."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-ultraviolet-exposure-test-criteria, post-ultraviolet-short-circuit-current-loss, ultraviolet-exposure-acceptance-limit, short-circuit-current-reference-correction, ultraviolet-exposure-sequence-completeness, solar-array-coupon-ultraviolet-acceptance]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies -- Ultraviolet Exposure Pass Criteria (space-systems/ecss/e2008-ultraviolet-exposure-test-criteria)

Use when the task is the clause 6.4.3.15.3 acceptance decision of
ECSS-E-ST-20-08C: a photovoltaic specimen has come out of its
ultraviolet exposure sequence, and it is admissible only if the short
circuit current it delivers has not fallen past the accepted fraction of
its pre-exposure value.

## Domain quick reference

- Ultraviolet damage is an optical loss, not an electrical one. The
  junction is unchanged; what changed is how much light reaches it,
  because the coverglass adhesive darkened, the front-surface silicone
  yellowed or a filter cutoff moved. Short circuit current is very
  nearly proportional to the photon flux arriving at the junction and
  almost independent of the junction's own health, which is exactly why
  it is the measurand and why open circuit voltage is not.
- The criterion is a pre-versus-post comparison of one specimen, not a
  reading against a datasheet. Two specimens from the same lot differ by
  more than the accepted loss, so an absolute post-exposure current
  says nothing on its own.
- Raw illuminated readings are not comparable. Short circuit current
  moves almost linearly with irradiance and slowly with cell temperature
  through its own small positive coefficient, so both readings are
  reported back to reference irradiance and reference cell temperature
  before the loss fraction is formed. Uncorrected, a lamp that drifted
  between the two sessions manufactures or masks the whole loss.
- The exposure sequence has to have finished. A criterion applied after
  a partial dose passes a specimen that never met the exposure it was
  supposed to survive, and the resulting record looks identical to a
  real pass.
- A post-exposure reading that comes back higher is a negative loss.
  That is admissible against a one-sided limit and it is reported as
  what it is rather than clamped to zero, because a large apparent gain
  usually points at a measurement or correction error worth chasing.
- A set is judged specimen by specimen, and the aggregate is reported
  alongside. The worst case is what the limit bites on; the mean is what
  says whether one specimen is an outlier or the lot is drifting.

## Workflow

1. Check the sequence first: compare the dose accumulated over the
   exposure against the dose the sequence required. An unrecorded
   accumulated dose is a finding, and so is a short one; an exact
   equality is compliant.
2. Correct the pre-exposure and post-exposure illuminated readings to
   reference irradiance and reference cell temperature, using the
   specimen's own measured temperature coefficient when it carries one.
   Refuse a correction whose temperature factor is not positive rather
   than returning a sign-inverted current.
3. Form the short circuit current loss fraction and the retention ratio
   from the two corrected currents for every specimen, and compare the
   loss with the accepted value, absorbing representation error at the
   boundary with a named tolerance instead of relaxing the limit.
4. Reject a duplicate specimen identifier, a blank one, a missing
   reading or a non-positive current as an input error rather than
   quietly grouping two specimens into one record.
5. Aggregate: the worst case loss, the mean loss across the set, and the
   identifiers of every specimen past the limit.
6. Close on one verdict. The set is accepted only when the finding list
   is empty -- sequence findings and specimen findings together -- and
   every finding is reported, not only the first.

## Pitfalls

- Comparing raw amperes across the exposure. An irradiance difference
  between the two measurement sessions goes straight into the loss
  fraction, and the correction to reference conditions is what makes the
  comparison mean anything.
- Judging the post-exposure current against a datasheet figure. The
  criterion is a loss fraction against the specimen's own pre-exposure
  value; lot-to-lot spread is larger than the accepted loss.
- Applying the criterion after a partial exposure. The numbers look
  exactly like a pass, and nothing in the resulting record says the
  specimen only saw part of the dose it was qualified against.
- Reading open circuit voltage as the ultraviolet indicator. The damage
  is a transmission loss, and voltage barely moves for a loss that takes
  a visible bite out of the current.
- Reporting only the mean loss of a set. The limit bites on the worst
  specimen, and a mean comfortably inside the limit can hide one
  specimen well past it.
- Clamping a measured gain to zero. It hides the one signal that says
  the correction or the measurement is wrong, and it costs nothing to
  report the negative loss as measured.
- Widening the accepted loss to let an exactly-compliant specimen
  through. An equality at the limit is a representation question,
  handled by the tolerance inside the comparison; the accepted value
  stays as specified.

## Behavior contract (gate 3)

The exposure-sequence completeness check, the irradiance and temperature
correction of both illuminated readings, the short circuit current loss
fraction and retention ratio, the per-specimen screening with duplicate
and blank identifier rejection, the worst-case and mean aggregation and
the acceptance verdict are exercised by the gate 3 contract test:
scripts/test_e2008_ultraviolet_exposure_test_criteria.py against
scripts/e2008_ultraviolet_exposure_test_criteria_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_ultraviolet_exposure_test_criteria.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
