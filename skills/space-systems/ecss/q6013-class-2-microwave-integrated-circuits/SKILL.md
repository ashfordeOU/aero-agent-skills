---
name: q6013-class-2-microwave-integrated-circuits
description: "Use when an MMIC has to become an application verdict. Evaluate whether a microwave monolithic integrated circuit may be applied at the intermediate assurance class under ECSS-Q-ST-60-13C clause 5.6.5: refuse a part naming no technology or package form, compute the channel temperature from the baseplate, the dissipation and the thermal path, take the margin against the lower of the class ceiling and the part rating, derive an Arrhenius median life against the mission duration, compare the RF drive with the derating cap, demand a moisture barrier behind a non-hermetic package, and score the evaluation evidence, crediting a similarity claim below a direct record. Trigger: ecss, q-st-60-13c-clause-5-6-5, class-two-microwave-monolithic-integrated-circuit, mmic-channel-temperature-margin, mmic-arrhenius-median-life, non-hermetic-mmic-moisture-barrier, mmic-rf-drive-derating, mmic-wafer-lot-process-monitor-evidence."
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
  tags: [ecss, q-st-60-13-commercial-eee-component-scope, q6013-class-2-microwave-integrated-circuits, class-two-microwave-monolithic-integrated-circuit, mmic-channel-temperature-margin, mmic-arrhenius-median-life, non-hermetic-mmic-moisture-barrier, mmic-rf-drive-derating, mmic-wafer-lot-process-monitor-evidence]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE Components -- Class 2 Microwave Integrated Circuits (space-systems/ecss/q6013-class-2-microwave-integrated-circuits)

Use when the task is the clause 5.6.5 microwave question of
ECSS-Q-ST-60-13C at the intermediate assurance class: a monolithic
microwave integrated circuit in commercial form has been picked for an RF
chain, and the question is whether the way it is applied and the way it
was evaluated together keep it inside what the class allows.

## Domain quick reference

- An MMIC is not a catalogue part that can be judged on its datasheet
  line. The compound semiconductor channel runs hot under RF drive, the
  die is usually delivered bare into a module rather than in its own
  qualified package, and the wafer lot behind the die is the real unit
  of quality.
- The channel, not the case, ages the part. Channel temperature follows
  from the baseplate temperature, the dissipated power and the thermal
  resistance of the path out of the die, so a part reported at a
  comfortable case temperature may be running thirty or fifty degrees
  hotter where it matters.
- The margin is taken against the lower of the class ceiling and the
  part's own rated channel temperature. A part rated below the class
  ceiling is held to its own rating, because the class ceiling is a
  programme limit and the rating is a physical one.
- RF drive is read as a fraction of the rated drive. A microwave part run
  near its rated drive has no headroom for the gain drop that arrives
  with temperature and with life, and the derating cap is what reserves
  that headroom.
- Median life follows an Arrhenius model referred to a declared reference
  life at a reference channel temperature. That is the step that turns a
  channel temperature into a number the mission duration can be compared
  against, and the requirement is the greater of the policy floor and the
  mission itself.
- Package form decides the sealing condition. A hermetic package or a
  bare die in a sealed module carries its own moisture protection; a
  non-hermetic plastic package does not, and at this class it is
  admissible only where a moisture barrier is declared for the assembly
  around it.
- Evidence is scored, not ticked. A subject may be carried by similarity
  to an evaluated sibling part at this class, which the class above does
  not allow, and similarity is credited below a direct record so that a
  part evaluated entirely by analogy cannot read as an evaluated part.

## Workflow

1. Validate the application policy first: the channel ceiling, the margin
   floor, the RF drive cap, the median life floor, the evidence share and
   credited floors, the similarity credit and the marginal band. A margin
   floor at or above the ceiling, a zero drive cap or credit, or a
   credited floor above the plain one is refused rather than used.
2. Validate the Arrhenius reference: a reference channel temperature
   above absolute zero, a positive reference life and a positive
   activation energy.
3. Validate the part: a reference, a recognised technology, a recognised
   package form, temperatures above absolute zero, a non-negative
   dissipation and thermal resistance, a positive rated drive and a
   positive mission duration. A part naming no technology or no package
   form closes the assessment on part not identified.
4. Compute the channel temperature, the governing ceiling, the margin,
   the drive fraction and the median life, then compare each against its
   limit with a tolerance that absorbs representation error so a value
   landing on a bound is admissible.
5. Apply the sealing condition: a non-hermetic package with no declared
   moisture barrier closes the assessment, and the requirement may be
   waived only by an explicit policy decision.
6. Dispose each required evidence subject as held directly, held by
   similarity, declared without a record, or absent. Report every failing
   list in full rather than truncating at the first entry.
7. Report the channel temperature, the margin, the drive fraction, the
   median life, the evidence share and the credited evidence, name the
   absent, unrecorded and similarity-carried subjects, and raise an
   advisory for a margin inside the marginal band. Close on one verdict:
   part not identified, channel margin short, RF drive derating exceeded,
   median life below the mission need, non-hermetic part without a
   moisture barrier, evaluation evidence short, or application meets
   class two scope.

## Pitfalls

- Reading the case temperature and calling it the channel. The thermal
  path out of the die is the whole question, and a part comfortable at
  the baseplate can sit far above the ceiling where the gain is made.
- Taking the margin against the class ceiling when the part is rated
  below it. The rating is physical and the ceiling is a programme choice,
  so the lower of the two governs.
- Treating the median life floor as the requirement when the mission runs
  longer. A part good for fifteen years on a twenty year mission is short
  by five, and the greater of the two is what the part has to clear.
- Accepting a non-hermetic package because the module around it looks
  sealed. The barrier has to be declared for the assembly, not inferred
  from a photograph of it.
- Crediting a similarity claim in full. Similarity is permitted here and
  it is thinner than an evaluation of this die from this wafer lot, which
  is what the credit records; without it a part evaluated entirely by
  analogy scores as an evaluated part.
- Naming a sibling part that is not identified. A similarity claim with
  no sibling reference behind it is a declaration, and it is grouped with
  the subjects that hold no record at all.

## Behavior contract (gate 3)

The policy validation, the Arrhenius reference validation, the part
validation, the channel temperature, the governing ceiling, the margin,
the RF drive fraction, the median life, the sealing condition, the held,
similarity, unrecorded and absent evidence dispositions, the evidence
share, the credited evidence, the marginal advisories and the application
verdict are exercised by the gate 3 contract test:
scripts/test_q6013_class_2_microwave_integrated_circuits.py against
scripts/q6013_class_2_microwave_integrated_circuits_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_q6013_class_2_microwave_integrated_circuits.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
