---
name: e2008-ionising-irradiation-pass-criteria
description: "Assess a blocking diode's post-irradiation and post-anneal behaviour against its control drawing limits under ECSS-E-ST-20-08C clause 12.6.11.1.2: refuse an untraceable limit set, judge both readings against the same bound with a tie admissible, split the total-dose shift into what the soak gave back and the residual the mission carries, catch a part the anneal left worse than the exposure, and take the lot reject share against its allowance. Use when irradiated and annealed diode data must become a verdict. Trigger: ecss, e-st-20-08c-clause-12-6-11-1-2, blocking-diode-total-ionising-dose-sentencing, control-drawing-post-irradiation-limits, post-anneal-recovery-fraction, reverse-annealing-advisory, irradiated-diode-residual-shift, irradiated-lot-reject-allowance."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-08c, e2008-ionising-irradiation-pass-criteria, blocking-diode-total-ionising-dose-sentencing, control-drawing-post-irradiation-limits, post-anneal-recovery-fraction, reverse-annealing-advisory, irradiated-diode-residual-shift, irradiated-lot-reject-allowance]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Blocking Diodes -- Ionising Irradiation Pass Criteria (space-systems/ecss/e2008-ionising-irradiation-pass-criteria)

Use when the task is clause 12.6.11.1.2 of ECSS-E-ST-20-08C -- closing a
total-dose campaign on a blocking diode. The exposure is over, the soak
is over, and what the clause asks for is a comparison: the
characteristics the part shows after irradiation and after annealing,
against the limits its control drawing fixes.

## Domain quick reference

- The clause names two readings, not one. Post-irradiation and
  post-annealing are both compared, and a rule that looks at only one of
  them is blind to whichever state that part happened to be worse in.
- The control drawing is where the limits come from, and that is the
  load-bearing part of the clause. A catalogue page, a handbook table or
  the bench operator's recollection is not a controlled document, so a
  limit set with no drawing reference and no issue is refused here
  rather than used.
- A limit without its test condition is unreproducible. A forward drop
  is a ceiling at a stated current and a leakage is a ceiling at a
  stated reverse voltage; either number quoted bare is one nobody can
  repeat.
- Annealing usually recovers. Trapped oxide charge detraps during the
  soak and the parameter walks back toward the baseline, which is why
  the annealed reading is normally the better of the two.
- Annealing does not always recover. Interface-state build-up at a
  bipolar junction surface can continue through the soak, leaving the
  annealed reading further off baseline than the irradiated one. That
  direction is a finding in its own right, not merely a small recovery.
- The recovery fraction and the residual shift answer different
  questions. Recovery says how much the soak gave back; the residual
  says what the mission still has to live with, and only the second one
  enters a degradation budget.
- A tie is admissible. A reading landing exactly on a drawing bound
  meets it, and the comparison tolerance absorbs representation error so
  the bound itself never moves.
- Meeting a bound with nothing left over is not the same as meeting it
  comfortably. A part accepted on the line has spent its whole budget
  before launch and has flight degradation still to add, so it is
  accepted and flagged rather than quietly passed.
- The lot carries its own question. Individual rejects are expected and
  handled by replacement; a rejected share above the declared allowance
  says the lot, not the part, is what failed.

## Workflow

1. Validate the sentencing policy, then the limit set. Refuse a drawing
   reference, issue or test condition that is missing or blank before
   any measurement is touched, because an untraceable limit cannot carry
   an acceptance decision.
2. Refuse a readout missing any of the three states. Pre-irradiation is
   the baseline the shift is measured from; an absent state is not a
   repeated one.
3. Judge the irradiated reading and the annealed reading against the
   same drawing bound, independently, with a tie passing on either, and
   in the direction the drawing declares -- a ceiling for a drop or a
   leakage, a floor for a breakdown voltage.
4. Report both margins whatever the disposition, since a passing margin
   is the number a later degradation claim is measured against.
5. Take the irradiation shift, the residual shift and the recovery
   fraction. Refuse a recovery fraction for a parameter the irradiation
   never moved rather than returning a fabricated zero.
6. Flag a part whose annealed state sits further off baseline than its
   irradiated state, separately from a part that merely recovered
   little, because the two point at different mechanisms.
7. Group each parameter by which reading breached: accepted, accepted
   with advisory, rejected on the irradiated reading, rejected on the
   annealed reading, or rejected on both. Name every breach the part
   carries, not only the first one found.
8. Close on one lot verdict -- accepted, accepted with advisory,
   contains rejects, or reject allowance exceeded -- with every finding
   listed against the serial that earned it.

## Pitfalls

- Sentencing on the annealed reading alone because it is the last one
  taken. The part flew through the irradiated state too, and for a
  recovering parameter that state is the worse of the two.
- Sentencing on the irradiated reading alone. The soak is part of the
  qualification, and a part rejected before it has been given the
  recovery the clause allows for.
- Comparing against a datasheet. The drawing is what the procurement and
  the qualification were written to, and a catalogue figure for the same
  part number can differ with nothing tracing the decision back.
- Reading a small recovery and a reverse anneal as the same finding.
  One says the soak was short or cool; the other says the damage
  mechanism is still running, and only the second one gets worse with
  time on orbit.
- Deriving a recovery fraction from a parameter that never shifted. The
  denominator is zero, and whatever the arithmetic returns is not a
  recovery.
- Treating a part on the line as a comfortable pass. It met the bound
  with nothing left, and flight degradation has not started yet.
- Reading a negative margin as an advisory. A breach is a breach; the
  advisory band only ever describes a part that actually passed.
- Stopping at the first rejected part. The lot verdict needs the whole
  count, and a reject share above the allowance is a different finding
  with a different fix from one bad diode.

## Behavior contract (gate 3)

The policy validation, drawing provenance and test-condition refusal,
three-state readout validation, tie-admissible comparison in both limit
directions, margin arithmetic, irradiation and residual shift, recovery
fraction with its zero-denominator refusal, the reverse-anneal flag, the
advisory band at its exact bound, per-parameter and per-part grouping,
lot reject share against its allowance and the lot verdict are exercised
by the gate 3 contract test:
scripts/test_e2008_ionising_irradiation_pass_criteria.py against
scripts/e2008_ionising_irradiation_pass_criteria_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_ionising_irradiation_pass_criteria.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
