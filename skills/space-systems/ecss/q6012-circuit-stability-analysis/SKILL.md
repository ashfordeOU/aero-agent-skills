---
name: q6012-circuit-stability-analysis
description: "Verify that an MMIC gain stage cannot oscillate anywhere in its operating envelope. Use when an amplifier has to be shown stable over frequency, bias and termination before release, per ECSS-Q-ST-60-12C clause 7.2.8: build the determinant and Rollett factor from the two-port scattering parameters at every analysed frequency, derive the geometric mu factor, place the source and load stability circles, test whether the terminations the matching networks will really present fall in the stable region, and confirm the analysed span reaches decades below the band and a multiple above it. Trigger: ecss, q-st-60-12-mmic-scope, mmic-circuit-stability, rollett-stability-factor, geometric-mu-factor, load-stability-circle, source-stability-circle, out-of-band-stability-span, termination-envelope-stability."
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
  tags: [ecss, q-st-60-12-mmic-scope, q6012-circuit-stability-analysis, mmic-circuit-stability, rollett-stability-factor, geometric-mu-factor, load-stability-circle, source-stability-circle, out-of-band-stability-span, termination-envelope-stability]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS MMIC Die -- Circuit Stability Analysis (space-systems/ecss/q6012-circuit-stability-analysis)

Use when the task is the stability demonstration of ECSS-Q-ST-60-12C
clause 7.2.8: a monolithic microwave integrated circuit contains a gain
stage, and the question is whether anything the circuit will meet in
service -- a frequency outside its band, a bias excursion, a termination
the matching network was not designed for -- can turn that gain into a
sustained oscillation.

## Domain quick reference

- An oscillating amplifier is not a degraded amplifier. The output is a
  tone nobody asked for, the bias walks, the noise figure is
  meaningless, and the failure usually surfaces on the integrated unit,
  long after the die was accepted.
- The demonstration is built from the two-port scattering matrix at each
  analysed frequency. The determinant and the Rollett factor together
  answer the unconditional question: is there any passive termination
  at all that could sustain oscillation. A factor above one with a
  determinant magnitude below one says no.
- The geometric factor says the same thing with a distance attached. It
  is the gap from the centre of the reflection plane to the nearest
  point of the unstable region, so it ranks frequencies by how close
  the circuit came, which a pass or fail never does.
- Failing the unconditional test is not a verdict on the design. A
  conditionally stable stage is used all the time; what it owes is a
  demonstration that the terminations it will really see sit in the
  stable part of the plane, which the stability circle cuts off.
- Which side of the circle is stable is not fixed. The centre of the
  plane is a matched termination, stable whenever the port it faces is
  not already reflecting gain, and the stable region is whichever side
  of the circle that centre falls on. A circle that encircles the
  centre of the plane inverts the answer, and reading it the usual way
  round declares the dangerous half safe.
- Span carries as much weight as the numbers. A stage is usually most
  dangerous well below its band, where the device has far more gain
  than the design uses and the matching networks have stopped
  controlling the terminations, so the analysis reaches decades below
  the band edge and a multiple above it.

## Workflow

1. Take the scattering matrix at every frequency the analysis covers,
   accepting either complex entries or magnitude-and-angle pairs, and
   reject a matrix whose reverse path reads exactly zero -- a measured
   device never does, and a zero makes the stability factor undefined.
2. Compute the determinant, the Rollett factor and both geometric
   factors at each frequency, and group the point as unconditionally
   stable, marginal, or potentially unstable. Report a point sitting on
   the boundary as marginal rather than forcing it to one side.
3. Where a point is not unconditionally stable, place the source and
   load stability circles and establish which side of each one the
   centre of the plane falls on.
4. Test every termination the design will present against the circle in
   its plane. Reject a termination that reflects more than it receives,
   and treat a termination landing on the circle itself as not passing.
5. Check the analysed span against the requirement on both sides, and
   refuse to conclude anything from a sweep that did not reach far
   enough -- an unexamined decade is not a stable decade.
6. Close with the verdict, the frequency that came closest, and every
   termination that would oscillate there.

## Pitfalls

- Analysing the operating band and stopping. The band is where the
  design put its matching effort and its least surplus gain; the
  oscillation is two decades lower, where the device still has twenty
  decibels in hand and the networks are transparent.
- Reading the Rollett factor without the determinant. The factor alone
  is not sufficient for unconditional stability, and a matrix with a
  factor above one and a determinant magnitude above one is potentially
  unstable while looking safe.
- Taking the region outside the stability circle as the stable one by
  habit. Which side is stable depends on where the centre of the plane
  falls, and a circle that encircles it reverses the answer.
- Declaring a conditionally stable stage acceptable without an envelope.
  Conditional stability is a statement about terminations, so it means
  nothing until the terminations the networks really present -- over
  frequency, over bias, with the next stage attached -- are written
  down and tested.
- Grading a stability factor against one by bare arithmetic. The factor
  is built from complex products and a square root, so a device sitting
  exactly on the boundary can land a few units in the last place on
  either side; the boundary case is reported as marginal rather than
  resolved by the arithmetic.
- Treating a single-device result as covering a combined pair. Two
  devices in parallel carry an odd-mode loop the two-port matrix of one
  of them cannot see, and that loop is the classic power-stage
  oscillation.

## Behavior contract (gate 3)

The scattering-matrix validation, determinant and Rollett factor,
geometric mu factor, stability-circle placement, stable-side
resolution, termination envelope test, span coverage and overall
verdict are exercised by the gate 3 contract test:
scripts/test_q6012_circuit_stability_analysis.py against
scripts/q6012_circuit_stability_analysis_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6012_circuit_stability_analysis.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
