# Wave-45 spec-engineer kit (ops manager, shared rules)

You are writing ONE engineering spec file for a new AeroSkills leaf at
~/AeroSkills. The file you produce becomes the BUILD CONTRACT for a builder
subagent, so it must pin equations, function signatures, worked-example
parameters, validation checks, corpus queries, and forbidden tokens exactly.

## Read order (do this FIRST, in this order)

1. Read the probe receipt named in your task (ops/automation/state/
   wave45-recon/task-N-receipt.md). The GO evidence block (a) zero-owner
   greps, (b) sibling fence quotes, (c) standards-map id, (d) published
   deterministic anchor, (e) wordable Hit@1 corpus queries, (f) tag
   discipline) is YOUR source of truth for what the leaf claims and what it
   must not touch.
2. Read the sibling SKILL.md files whose fences are quoted in the receipt
   (they are the nearest owners; your leaf must NOT duplicate their content).
3. Read the ONE format exemplar named in your task (ops/automation/state/
   wave44-specs/<exemplar>.md) and mirror its section structure exactly.

## Anchor script FIRST (mandatory, wave-44 lesson)

Before writing prose, write the anchor script:
- Path: /tmp/w45spec/anchor_<leaf>.py (create /tmp/w45spec first).
- Pure Python stdlib (math only), deterministic, no RNG. Small focused
  functions with docstrings, module constants for every fixed number.
- Implements the EXACT closed-form model your spec will describe, at the
  worked-example parameters from the receipt's published anchor.
- Run it: cd ~/AeroSkills && python3 /tmp/w45spec/anchor_<leaf>.py
  Capture the REAL numeric outputs. Every number in the spec's Worked
  example and Identities sections comes from THIS run - never invent or
  round-trip values from memory. If a receipt gives a target value (e.g. a
  known closed-form identity), verify your anchor reproduces it within
  tolerance before writing it into the spec.
- Sandbox note: python3 -c, heredocs, and sed pipes are blocked. Write the
  anchor with write_file, run it with python3 <file>. If an equation in the
  receipt is ambiguous, implement the standard published method, record the
  assumption in the spec, and note the deviation in your final summary.

## Spec structure (mirror the exemplar exactly)

- Title: "# Wave-45 leaf spec: <leaf> (<family>, <pack> pack)"
- Path, Pack (present siblings + adjacent fences), Claim fences (quoted
  from the sibling frontmatter/body with the receipt's quotes, plus any
  fresh fence lines you verify), Standards id (one id from the receipt that
  EXISTS in standards-map.yaml; Ledger Standard line), Family.
- ## Claim: one paragraph, what it computes/produces, explicit Does NOT do
  list (fence discipline).
- ## Model (implement exactly): module constants with values; defining
  relations pinned exactly; function-by-function list with signatures,
  return shapes, and ValueError rejections (no imports beyond math).
- Identities to test (closed-form checks that can be verified WITHOUT the
  builder's module - exact identities where possible, magnitude bounds
  where the physics allows).
- ## Worked example: concrete parameters from the receipt's anchor; ALL
  values below are REAL outputs of your /tmp/w45spec/anchor_<leaf>.py run
  (say so, name the file). Give 6-15 significant figures on the numbers the
  contract test will assert.
- ## Validation list (deterministic checks the contract test must run):
  numbered 1..9+, including the worked-example asserts within 1e-6 relative
  (or a tolerance you specify), boundary cases, all ValueErrors, determinism,
  and "Test passes under BOTH interpreters (/usr/bin/python3 3.9.6 and
  ~/.pyenv/versions/3.13.12/bin/python3). No exact-float equality on computed
  sums; use assertAlmostEqual/math.isclose everywhere."
- ## Corpus fragment (2 verbatim queries for eval/hit1-wave45-<leaf>.yaml):
  copy the EXACT query texts from the receipt's gate (e) - do not reword.
  Include the intent lines.
- ## Description/tag guidance for the builder: a draft description <=1000
  chars and <=148 words with an action verb, using the receipt's claim
  language; the metadata tags EXACTLY as the receipt's gate (f) lists them;
  FORBIDDEN tokens (sibling claims) from the receipt.
- ZERO em dashes in the spec (use commas or hyphens). Never the word
  "classified". Standards are reference-only, never reproduced verbatim.

## Deliverable

Write the spec to ops/automation/state/wave45-specs/<leaf>.md. Do NOT edit
any other file. Do NOT git add/commit/push. Do NOT touch skills/, eval/,
docs/, Makefile, scripts/ (harness), ops/automation briefs, or
standards-map.yaml. Your final summary: spec path, anchor path, worked
example headline numbers, any assumption/deviations, confirmation the spec
is em-dash-free.
