---
name: q7005-solvent-control-and-blanks
description: "Evaluate a solvent blank and decide what an indirect contamination result is worth. Use when the ECSS-Q-ST-70-05C solvent purity and control clauses have to become an accept or reject: turn the solvent non-volatile residue specification and the volume used into an expected blank mass, compare it with the gross sample residue against a blank fraction ceiling, subtract it, propagate the blank scatter into a detection and a quantitation limit, and grade the net as quantifiable, detected only, or blank-limited. Trigger: ecss, q-st-70-05-ir-contamination-scope, solvent-blank-control, solvent-non-volatile-residue-purity, blank-fraction-ceiling, blank-corrected-net-residue, contamination-detection-and-quantitation-limit."
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
  tags: [ecss, q-st-70-05-ir-contamination-scope, q7005-solvent-control-and-blanks, solvent-blank-control, solvent-non-volatile-residue-purity, blank-fraction-ceiling, blank-corrected-net-residue, contamination-detection-and-quantitation-limit]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS IR Contamination Measurement — Solvent Control and Blanks (space-systems/ecss/q7005-solvent-control-and-blanks)

Use when the task is the solvent purity and blank-control side of the
indirect method of ECSS-Q-ST-70-05C — establishing how much of the
residue in the cell came out of the bottle rather than off the hardware,
and what the corrected number may honestly be reported as.

## Domain quick reference

- The cell weighs everything the solvent brought. Some of it came off the
  surface; the rest came from the solvent lot, the glassware, the gloves
  and the air of the room. The blank is what separates the two, and it is
  the measurement rather than a check on it.
- The solvent's own contribution is predictable before the run. A
  non-volatile residue specification in milligrams per litre times a
  volume in millilitres is a mass in micrograms directly, the two unit
  conversions cancelling, so the expected blank is known from the
  certificate and the volume used.
- A measured blank far from that prediction is information. It means
  something other than the solvent grade is contributing — glassware,
  handling, the room — and the gap is a finding whichever direction it
  goes in.
- Two kinds of blank answer two questions. The solvent blank measures the
  lot; the handling blank measures everything the procedure adds on top
  of it. Running only the first attributes the glassware and the gloves
  to the hardware.
- The blank fraction of the gross signal decides whether the result is
  about the surface at all. Past a declared ceiling the answer describes
  the solvent, and the correct response is a cleaner lot or a larger
  sampled area, not a subtraction with a shrug.
- The limits come from the blank's scatter, not its mean. Three standard
  deviations is the smallest net distinguishable from nothing; ten is the
  smallest that may be quoted as a figure. Between them the honest result
  is present-and-bounded. A single blank has no scatter and therefore
  sets no limit, which is why replicates are required.
- A run with no blank is not a run with a zero blank. It cannot be
  corrected and it cannot be graded, so it is refused rather than
  reported with a caveat.

## Workflow

1. Validate the blank policy: at least two replicates, a fraction ceiling
   strictly inside the unit interval, and a quantitation sigma above the
   detection sigma.
2. Refuse the case outright when it carries no blank at all, or no
   solvent blank; these are not findings to be weighed against others.
3. Predict the blank from the solvent specification and volume, check the
   grade against its ceiling, and compare the prediction with what was
   actually measured.
4. Take the blank fraction of the gross residue and test it against the
   ceiling before subtracting anything.
5. Subtract to get the net, clamping a negative difference to zero while
   keeping the raw difference and flagging that the blank exceeded the
   sample.
6. Build the detection and quantitation limits from the blank scatter,
   grade the net against both, combine the gross and blank scatters in
   quadrature for the uncertainty, and close with the findings and the
   duties the reported number carries.

## Pitfalls

- Reporting the gross residue as the surface loading. At a typical
  solvent grade and volume the blank is a real share of a clean article's
  signal, and the uncorrected number fails an article that passed.
- Running one blank. One value has no scatter, so the detection and
  quantitation limits cannot be formed and every net reads as a number.
- Treating a handling blank as optional because the solvent blank was
  clean. They measure different contributions, and only the handling
  blank sees what the procedure itself adds.
- Subtracting a blank that dominates the gross signal. The subtraction is
  arithmetically valid and physically meaningless; the blank fraction
  ceiling exists to stop the result being quoted at all in that case.
- Quoting a figure for a net between the detection and quantitation
  limits. It is present and bounded, and a number there implies a
  precision the blank scatter does not support.
- Comparing a net against a limit, or a fraction against a ceiling, with
  a bare strict inequality. A net built from a difference of two weighed
  masses can land a few units in the last place either side of a limit it
  should meet exactly; each comparison absorbs that while the limit
  itself stays as specified.
- Carrying a blank from a previous lot. The blank is a property of the
  lot, so the lot identity travels with the result.

## Behavior contract (gate 3)

The policy validation, the expected blank from the solvent specification,
the purity check, the blank fraction, the clamped blank-corrected net, the
detection and quantitation limits from the blank scatter, the combined
uncertainty and the grading are exercised by the gate 3 contract test:
scripts/test_q7005_solvent_control_and_blanks.py against
scripts/q7005_solvent_control_and_blanks_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7005_solvent_control_and_blanks.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
