---
name: q7046-coating-and-corrosion-tests
description: "Assess the coating evidence a threaded fastener lot owes: deposit thickness against its band, adhesion by the method that coating calls for, corrosion exposure scaled to the environment, and the durability tests the companion coatings standard adds. Use when a plated or conversion-coated fastener lot comes back from the coating shop and someone has to say whether the finish is acceptable: judge every thickness reading rather than the mean, separate base-metal attack from a cosmetic bloom, confirm the embrittlement relief bake happened inside its window, and name the durability tests still outstanding. Trigger: ecss, q-st-70-46-threaded-fasteners, fastener-coating-thickness-band, fastener-coating-adhesion-test, fastener-salt-spray-duration, fastener-coating-durability-link, fastener-embrittlement-relief-bake."
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
  tags: [ecss, q-st-70-46-threaded-fasteners, q7046-coating-and-corrosion-tests, fastener-coating-thickness-band, fastener-coating-adhesion-test, fastener-salt-spray-duration, fastener-coating-durability-link, fastener-embrittlement-relief-bake]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Threaded Fasteners — Coating and Corrosion Tests (space-systems/ecss/q7046-coating-and-corrosion-tests)

Use when the task is the coating part of the testing clause of
ECSS-Q-ST-70-46: what a plated, conversion-coated or dry-film-lubricated
fastener lot owes in thickness, adhesion and corrosion evidence, and
which durability tests the companion coatings standard ECSS-Q-ST-70-17
adds on top.

## Domain quick reference

- Coating thickness has a ceiling as well as a floor, and on a threaded
  part the ceiling is the harder one. Too thin is short protection; too
  thick fouls the thread fit, so a lot that gauges correctly bare can
  fail the go gauge once coated, and the extra deposit changes the
  torque-tension relation the joint was designed around.
- The thickness verdict is per reading, not per mean. The thinnest spot
  is where corrosion starts, and an average over a well-covered shank
  hides a bare thread root.
- The adhesion method belongs to the coating. A bend or tape test that
  suits one deposit says nothing about another, so a result recorded
  against the wrong method is an invalid test rather than a pass.
- Corrosion exposure scales with where the hardware lives before
  launch. A fastener that spends months at a coastal launch site owes
  more exposure hours than one that goes from a clean room into a
  vacuum, and the multiplier belongs in the requirement rather than in
  a reviewer's judgement.
- Two kinds of corrosion product mean two different things. A white or
  grey bloom is the sacrificial coating doing its job and is tolerated
  after a fraction of the exposure; red rust is attack on the base
  metal underneath and is a failure whenever it appears.
- An electrodeposited coating on a high-strength fastener carries a
  hydrogen risk that testing cannot see. The relief bake has to start
  inside a short window after plating and run for its full duration; a
  bake that started late is not recoverable by baking longer.
- Durability evidence comes from the companion standard, not from this
  one. Thermal cycling, humidity and, for a lubricated finish, wear
  through repeated installation are named here and graded there.

## Workflow

1. Take the coating specification: thickness band, adhesion method,
   base corrosion exposure, whether the deposit is electrodeposited.
   Refuse an unlisted coating rather than assuming a generic band.
2. Judge every thickness reading against the band; report the thinnest
   and the thickest with the count outside, and flag a thread-fit risk
   separately from a protection shortfall.
3. Confirm the adhesion test used the method the coating calls for,
   then read its result; a mismatched method invalidates the test.
4. Scale the base exposure by the environment factor to get the hours
   required, and compare the hours actually run.
5. Judge the corrosion result: any base-metal attack fails outright; a
   sacrificial bloom is tolerated only after its allowed fraction of
   the exposure has elapsed.
6. Where the deposit is electrodeposited, check the relief bake
   happened, started inside its window and ran its full duration.
7. List the durability tests the companion standard adds for this
   coating and environment, and report the ones with no record.

## Pitfalls

- Judging thickness on the mean. The mean passes a lot whose thinnest
  reading is bare, which is precisely the reading corrosion finds.
- Treating a thick deposit as harmless. On a thread it is a fit problem
  and a torque-tension problem, and it is the failure mode that reaches
  assembly rather than the lab.
- Reading white bloom as a failure. The sacrificial layer is meant to
  corrode; calling it a failure rejects coatings that are working.
- Reading red rust as a late-stage nuisance. It is base-metal attack and
  it fails the test at whatever hour it appears.
- Applying one exposure requirement to every programme. A coastal
  launch campaign and a clean-room-to-vacuum path are different duty,
  and the factor belongs in the requirement.
- Baking longer to make up for baking late. The window exists because
  hydrogen redistributes; a late bake is a non-conformance, not a
  schedule slip.
- Assuming the durability tests are covered by this standard. They are
  graded against the companion coatings standard and have to be named
  as outstanding when no record exists.

## Behavior contract (gate 3)

The coating specifications, per-reading thickness verdict, adhesion
method matching, the environment-scaled exposure requirement, the split
between sacrificial bloom and base-metal attack, the relief-bake window
and the companion durability list are exercised by the gate 3 contract
test: scripts/test_q7046_coating_and_corrosion_tests.py against
scripts/q7046_coating_and_corrosion_tests_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7046_coating_and_corrosion_tests.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
