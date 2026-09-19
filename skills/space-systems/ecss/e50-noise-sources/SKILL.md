---
name: e50-noise-sources
description: "Assess whether the noise sources acting on a receiving chain have been identified, then add them at one reference plane, per ECSS-E-ST-50C Rev.2 clause 5.6.6. Use when a link budget needs a system noise temperature that can be defended: check that sky, atmosphere, ground spillover, feed loss and front end are each named, refer every source through the loss between its own plane and the reference plane, credit a lossy run with the noise it generates as well as the noise it attenuates, and report the group that dominates the total so a reduction is spent where it pays. Trigger: ecss, e-st-50c-clause-5-6-6, link-noise-source-identification, system-noise-temperature-budget, feed-loss-noise-contribution, antenna-figure-of-merit-g-over-t, noise-reference-plane-referral."
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
  tags: [ecss, e-st-50-communications-scope, e50-noise-sources, e-st-50c-clause-5-6-6, link-noise-source-identification, system-noise-temperature-budget, feed-loss-noise-contribution, antenna-figure-of-merit-g-over-t, noise-reference-plane-referral]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Communications — Link Noise Sources (space-systems/ecss/e50-noise-sources)

Use when the task is clause 5.6.6 of ECSS-E-ST-50C Rev.2: identifying the
noise sources that act on a space link, and turning that identification into
a system noise temperature a link budget can stand on.

## Domain quick reference

- Identification is the obligation; the total is what makes it useful. A
  list of sources nobody added is not a budget, and a total with a group
  missing from the list is not a total, so both are graded.
- A missing group is not a zero contribution. A chain with no atmospheric
  source named has not proved the atmosphere is quiet; it has an
  identification gap, and reporting it as a satisfied zero is how a budget
  goes optimistic without a single wrong number in it.
- Temperatures only add at a common plane. A sky temperature stated at the
  antenna and a receiver temperature stated at its input are different
  quantities, and adding them straight overstates the sky contribution by
  the whole feed loss.
- A lossy element does two things and both belong in the budget. It
  attenuates what passes through it and it generates noise of its own,
  proportional to its physical temperature and to how lossy it is. A budget
  that only attenuates is optimistic by exactly the term it dropped.
- Which group dominates is the actionable output. A total set by feed loss
  is fixed with a shorter or better run, one set by the front end with a
  better amplifier, and the total alone points at neither.
- The figure of merit is the number the other end cares about. G/T folds
  antenna gain and system noise into one term, and a chain can sit inside
  its noise allocation and still miss the G/T the link needs.
- A budget written to land exactly on its allocation is inside it. That is a
  normal way to specify one, so the comparison carries a relative tolerance
  rather than being decided by the last bit.

## Workflow

1. State each source as a category plus either a noise temperature at its
   own plane or, for a lossy element, a loss and a physical temperature.
   Refuse an entry carrying both: that double counts the element.
2. Check the identification against the groups a receiving chain always has,
   and name any group that is absent.
3. Refer every source to the reference plane by dividing it by the loss
   between its plane and that one.
4. Convert each lossy element into the noise it generates at its own output
   before referring it onward.
5. Add the referred contributions into the system noise temperature, and
   find the single largest contributor with a deterministic tie-break.
6. Where an antenna gain is available, derive G/T and compare it against
   what the link requires.
7. Compare the total against the allocation with a relative tolerance and
   close with a ranked disposition: an identification gap first, an
   allocation or G/T breach second.

## Pitfalls

- Adding an antenna-plane temperature to a receiver-input temperature. The
  feed loss between them is exactly the error, and it is largest on the
  chains where the sky contribution matters most.
- Modelling a lossy run as attenuation only. The noise it generates is often
  the largest single term in the whole budget, and omitting it makes the
  quietest possible chain look achievable.
- Treating an unlisted group as contributing nothing. It contributes
  whatever it contributes; the list is the only thing that changed.
- Reporting the total without the dominant group. Two chains with the same
  total need completely different work, and the total cannot tell them
  apart.
- Passing the noise allocation and assuming the link closes. G/T also
  carries the antenna gain, and a small antenna with a quiet receiver can
  satisfy one and fail the other.
- Deciding an on-the-bound allocation with a bare inequality. Budgets are
  routinely written to their allocation exactly, and the verdict must not
  depend on which machine evaluated the sum.

## Behavior contract (gate 3)

Temperature, loss and source validation including the refusal of an entry
declaring both a temperature and a loss, the loss factor, referral through a
loss, the noise a lossy element generates, category completeness, the total
at the reference plane, the deterministic dominant group, G/T, the margin and
the ranked disposition at the exact allocation bound are exercised by the
gate 3 contract test: scripts/test_e50_noise_sources.py against
scripts/e50_noise_sources_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e50_noise_sources.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
