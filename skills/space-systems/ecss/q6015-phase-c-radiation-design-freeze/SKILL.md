---
name: q6015-phase-c-radiation-design-freeze
description: "Determine whether the hardness assurance baseline of an equipment may be frozen at its critical design review. Use when the ECSS-Q-ST-60-15C clause 4.4.3 phase C work has to be produced or graded: reduce each characterization lot to a design capability through a one-sided tolerance limit that penalises a small sample, add the spot shield to the inherent thickness and read the dose-depth curve at the total, price that shield in mass against its allocation, take every part's radiation design margin against the specified level, and name each blocker that keeps the baseline open. Trigger: ecss, q-st-60-15c-clause-4-4-3, phase-c-radiation-design-freeze, radiation-characterization-testing, one-sided-tolerance-capability, equipment-spot-shielding-assessment, hardness-assurance-baseline-freeze."
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
  tags: [ecss, q-st-60-15-radiation-hardness-assurance-scope, q6015-phase-c-radiation-design-freeze, q-st-60-15c-clause-4-4-3, phase-c-radiation-design-freeze, radiation-characterization-testing, one-sided-tolerance-capability, equipment-spot-shielding-assessment, hardness-assurance-baseline-freeze]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Radiation Hardness Assurance — Phase C Design Freeze (space-systems/ecss/q6015-phase-c-radiation-design-freeze)

Use when the task is the detailed-design step of ECSS-Q-ST-60-15C clause
4.4.3 — reducing characterization test data into numbers a design can be
built on, settling the equipment shielding that goes with them, and deciding
whether the hardness assurance baseline is ready to be locked at the
critical design review.

## Domain quick reference

- A characterization lot is a sample, not the population. The design
  capability is the lower one-sided tolerance limit of that sample, so the
  penalty for testing few parts is carried in the number itself rather than
  argued about afterwards, and a three-part lot yields far less capability
  than its mean suggests.
- The tolerance factor is read at the sample size actually tested, and a size
  between two tabulated entries is read at the lower one. Reading it at the
  higher entry would credit the lot with evidence it does not have.
- A lot with a wide spread can drive the tolerance limit to zero or below.
  That is a real outcome, not an arithmetic accident: the data does not
  support any capability claim, and more parts have to be tested.
- Phase C shielding is local. The inherent thickness of the structure around
  the box is what the sector analysis gave, and the spot shield adds to it;
  the dose is read once at the total, never as two separate reductions.
- Spot shielding is bought with mass. A shield that closes a margin but
  overruns its mass allocation has not closed anything, so the mass is priced
  from footprint, thickness and density and graded against the allocation in
  the same pass as the margin.
- Freezing is a gate, not a milestone that arrives. The baseline locks only
  when every part has characterization behind it, every margin is met, the
  shielding is paid for and no waiver is still open. Anything else is a named
  blocker carried into the review.

## Workflow

1. Validate each characterization sample and reject one too small for the
   tolerance-factor table rather than falling back to the mean.
2. Reduce each sample to its design capability with the factor for its own
   size, and treat a non-positive limit as a blocker rather than clamping it.
3. Add the spot shield to the inherent thickness and interpolate the
   dose-depth curve in log-log at the total, refusing a total the curve does
   not span.
4. Apply the equipment design factor to that dose to obtain the specified
   level every part is graded against.
5. Take each part's margin, accepting an exact equality with the required
   margin through a named tolerance instead of relaxing the requirement, and
   order the part records by reference so two runs agree.
6. Price the spot shield in mass when a footprint is declared and grade it
   against the allocation; collect the part blockers, the mass overrun and
   every open waiver, and allow the freeze only when nothing remains.

## Pitfalls

- Reading the lot mean as the capability. Half the lot sits below the mean;
  the design number is the tolerance limit, and the gap between the two is
  the whole reason characterization sample size is negotiated.
- Interpolating the tolerance factor upward for an odd sample size. The
  factor table is stepped for a reason, and reading between entries credits
  evidence that was never gathered.
- Applying the dose reduction twice — once for the inherent thickness and
  again for the spot shield. The curve is read once, at the total thickness.
- Closing a margin with a spot shield and never pricing it. An unpriced
  shield migrates into the mass budget late, where it is most expensive to
  remove.
- Freezing with an open waiver on the grounds that the margin arithmetic
  passes. The waiver exists because something does not pass; leaving it open
  means the frozen baseline does not describe the hardware.

## Behavior contract (gate 3)

The tolerance-factor lookup, sample statistics, capability reduction, total
shielding and dose-depth interpolation, spot-shield mass, per-part margin
decision and the freeze verdict are exercised by the gate 3 contract test:
scripts/test_q6015_phase_c_radiation_design_freeze.py against
scripts/q6015_phase_c_radiation_design_freeze_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6015_phase_c_radiation_design_freeze.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
