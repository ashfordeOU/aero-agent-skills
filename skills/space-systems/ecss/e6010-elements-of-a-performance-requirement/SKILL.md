---
name: e6010-elements-of-a-performance-requirement
description: "Audit a control performance requirement for the elements ECSS-E-ST-60-10C clause 4.1.2 asks it to carry: the parameter, the statistical index, the value and its unit, the evaluation window, the reference frame, the operating condition, and a probability level where, and only where, the index is a statistical one. Report what is absent, what is stated but does not hold together, a completeness score, and a canonical restatement once the statement is whole. Use when reviewing a pointing or control performance specification before its verification cases are written. Trigger: ecss, e-st-60-10-control-performance, performance-requirement-element-completeness, performance-index-statistical-interpretation, pointing-requirement-confidence-level, performance-evaluation-window, control-performance-requirement-coherence."
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
  tags: [ecss, e-st-60-10-control-performance, e6010-elements-of-a-performance-requirement, performance-requirement-element-completeness, performance-index-statistical-interpretation, pointing-requirement-confidence-level, performance-evaluation-window, control-performance-requirement-coherence]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Control Performance — Elements of a Performance Requirement (space-systems/ecss/e6010-elements-of-a-performance-requirement)

Use when a control or pointing performance requirement is being written or
reviewed under ECSS-E-ST-60-10C clause 4.1.2 — deciding whether the statement
carries everything a verification case will need, before the campaign that
needs it is planned.

## Domain quick reference

- A number and a unit are not a requirement. "Pointing error below
  0.1 degrees" is at least four different obligations depending on
  whether the bound is a mean, a root-mean-square, a peak or a
  99.7 percent value, and they differ by a factor of several.
- The statistical index is the element most often left out and the one
  that moves the answer most. It is what turns a bound into something a
  simulation or a test can be scored against.
- The evaluation window belongs with the index. An average has to be an
  average of something over some interval, and a bound quoted without
  one can be met or missed by choosing the interval afterwards.
- The reference frame is not decoration. The same error expressed in a
  body frame, a line-of-sight frame and an inertial frame are different
  numbers, and a requirement silent on the frame is met in whichever one
  is convenient.
- The operating condition scopes the claim. A pointing bound that holds
  during quiet science pointing and not during a slew recovery is a
  useful requirement; one that does not say which is an argument
  deferred to the review.
- A probability level goes with a statistical index and nowhere else.
  An ensemble or percentile bound without one is incomplete; an absolute
  or peak bound carrying one is incoherent, because a bound that is
  never to be exceeded has no confidence attached.
- Completeness is checkable and coherence is not the same check. A
  statement can name every element and still contradict itself, and a
  checklist that only counts fields passes it.

## Workflow

1. Read the requirement as a record of elements rather than a sentence:
   parameter, index, value, unit, evaluation window, reference frame,
   operating condition, and probability level.
2. Take the absent elements first. A statement missing any of them
   cannot have a verification case written for it, and that is the
   finding, not the low score.
3. Normalise the index against the known set before anything else. An
   index nobody can name is not a strict reading of a loose one; it is
   an unstated element.
4. Apply the coherence rule between index and probability level in both
   directions: statistical indices need one, deterministic ones must not
   carry one.
5. Validate the stated values in their own right — a bound on an error
   magnitude is non-negative, an evaluation window is positive, and a
   probability level lies strictly inside zero and one.
6. Score completeness against the denominator the index implies, so a
   peak requirement is not marked down for the confidence level it is
   right not to have.
7. Restate a whole requirement in one canonical line carrying every
   element, and refuse to restate one that is not whole rather than
   filling a gap with a default.

## Pitfalls

- Treating a statistical index as a rounding detail. Mean, root-mean-
  square, peak and percentile bounds on the same parameter differ by
  factors that decide whether a design passes.
- Accepting a bound with no evaluation window. Whoever runs the
  verification then picks the window, and picks one that passes.
- Attaching a confidence level to an absolute bound. It reads as rigour
  and means the opposite: a never-exceed bound with a 99.7 percent
  qualifier is a percentile bound nobody agreed to.
- Reading a probability level of exactly one as a very strict
  requirement. It is an absolute bound labelled as a statistical one,
  and the verification method for the two is different.
- Counting fields and calling it a review. Completeness and coherence
  are separate checks, and only the second catches a requirement that
  names every element and still contradicts itself.
- Filling a missing element with a project default during review. The
  default may be right, but it is a decision, and silently adopting it
  moves the decision out of the document that records it.
- Leaving the reference frame to context. The number changes with the
  frame, and context is not a frame.

## Behavior contract (gate 3)

Index, value, window, probability-level and text-element validation,
detection of every absent required element, the index-dependent
denominator for the completeness score, the coherence rule between
index and probability level in both directions, refusal to normalise or
restate an incomplete or incoherent statement, and grouping a set of
requirements by verdict are exercised by the gate 3 contract test:
scripts/test_e6010_elements_of_a_performance_requirement.py against
scripts/e6010_elements_of_a_performance_requirement_logic.py (stdlib
unittest, offline).
Run:
python3 scripts/test_e6010_elements_of_a_performance_requirement.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
