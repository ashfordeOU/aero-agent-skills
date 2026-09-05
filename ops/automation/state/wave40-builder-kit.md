# Wave-40 builder kit (AeroSkills) - shared rules for leaf subagents

You are building ONE new leaf skill for the AeroSkills library at
~/AeroSkills. Follow this kit exactly, then your task-specific engineering
spec (a file in ops/automation/state/wave40-specs/ named for your leaf; read
it FIRST, it is your contract). Commit your own leaf IMMEDIATELY when
complete. Do not delegate, do not ask questions.

## Deliverables (per-skill completeness standard, commit ALL of these)

1. skills/<family>/<pack>/<leaf>/SKILL.md
2. skills/<family>/<pack>/<leaf>/scripts/<leaf>_logic.py  (pure stdlib logic)
3. skills/<family>/<pack>/<leaf>/scripts/test_<leaf>.py    (stdlib unittest contract test, offline deterministic, runs via `python3 scripts/test_<leaf>.py` and exits 0)
4. eval/hit1-wave40-<leaf>.yaml  (2 corpus tasks, exact format below)
5. eval/skill-eval/<leaf>.json   (value-delta record, exact schema below)
6. Append ONE row to eval/skill-ratings.md (rate-at-creation, 9.5)

Create references/ only when the SKILL body inlines long external data that
belongs in a reference doc; create assets/ only for templates the body names.
Most leaves need neither. NO broken refs: every scripts/references/assets path
named in your SKILL.md body must exist.

## Read your spec FIRST

ops/automation/state/wave40-specs/<leaf>.md contains YOUR leaf's engineering
contract: exact equations, function signatures, worked-example parameters,
validation list, sibling leaves to cite, standards ids, corpus-query guidance,
and forbidden tokens. Follow it exactly. The spec gives magnitude bounds for
the worked example: your module outputs must fall INSIDE those bounds; take
your real module outputs as the unittest assert targets. NEVER invent extra
features that change the spec's outputs. If a formula in the spec is
ambiguous, implement the standard engineering method with the stated module
constants and record the assumption in the SKILL body.

## Anti-hang protocol (mandatory, wave-25..39 held)

Write your logic file in one pass with SMALL focused functions (each 5-25
lines, one job, docstring). Run the module import and a 3-line smoke check
immediately after writing the logic file, BEFORE writing the full unittest
file. Sandbox note: `python3 -c` and heredocs are blocked in single-query
mode; write a tiny /tmp smoke script and run it if you need a quick check.
Then write the compact unittest file (15-35 methods), run it, fix, and only
then write SKILL.md + fragment + JSON + ledger row and commit. No stalls: if
something does not converge in two attempts, implement the spec's fallback.

## VALUE-DELTA SAMPLER RULE (wave-38 lesson #3 - READ TWICE)

The value-delta gate sampler RECOMPUTES eval records from TERM PRESENCE in
your TEST FILE, not from the committed JSON. A pure-math contract test that
never mentions the SKILL.md workflow computes delta 0.0 and FAILS the gate
even when your committed JSON says 0.5. Your test module docstring and test
method docstrings MUST name the SKILL.md workflow steps they exercise
naturally (e.g. "step 2 of the SKILL.md workflow, the X traverse, is
exercised by test_..."). Fact terms and procedure terms from the workflow
must appear in the test file text. Write the SKILL.md Workflow section FIRST
(numbered steps), then make the test docstrings reference those exact step
names. Do NOT add fake terms; reference your real workflow steps.

## SKILL.md structure (copy the exemplar: skills/propulsion/electric/hall-thruster/SKILL.md)

Frontmatter (agentskills.io):
- name: <leaf>
- description: "Use when you must <determine|compute|assess|size|run|...> ...:
  <what it does, the methods, the outputs>. Produces <deliverables>. Trigger:
  <8-16 routing keywords, hyphenated compound terms preferred>."
  Constraints: 50-150 WORDS and <=1024 CHARS total (target 700-1000 chars);
  must contain an action verb. Gate 1 caps at 1024 chars, gate 2 wants
  50-150 words + an action verb. Count before you commit.
- license: Apache-2.0
- compliance: STANDARDS-REF
- standards: [ {id: <from your spec>, reference-only: true} ]  (ONLY ids that
  exist in standards-map.yaml; your spec gives the id)
- gated: false
- domain: <family>
- pack: <pack>
- compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
- metadata: {domain: <family>, subdomain: <pack>, tags: [<hyphenated tags>], version: 0.1.0, author: AeroSkills}

Body sections (mirror hall-thruster): intro paragraph + pairing leaves,
## Domain quick reference (the equations that matter),
## Workflow (numbered steps referencing your logic functions),
## Worked example (concrete numbers from your spec - your module's REAL
outputs),
## Verification (deterministic checks incl. ValueError rejection of
non-physical inputs; reference the contract test),
## Related leaves (real sibling paths only),
## Contract test (how to run; what it covers),
## Compliance (STANDARDS-REF, gated false; standards referenced not
reproduced).

HARD TEXT RULES:
- ZERO em dashes (the character - is banned; use commas or hyphens) in every
  file you write.
- NEVER use the word "classified" (content-policy sweep). Use
  categorized/rated/sensitive-marking instead.
- Tags: hyphenated compound terms only, EXACTLY the tags your spec lists.
  NEVER single generic words (analysis, design, report, method, optimization,
  estimation, testing, inspection, sizing, loads, dynamics, power,
  performance, statistics, heating, buckling, control alone) as tags: single
  generic tags steal corpus tasks from existing leaves and break routing.
  Your first tag is the leaf name itself; add only the spec-listed compound
  terms.
- FORBIDDEN TOKENS: your spec lists tokens that belong to a sibling leaf's
  claim. Do NOT put them in your description, tags, or corpus queries.
- Do not reproduce proprietary standard text (no verbatim tables/sections
  from RTCA/SAE/FAA/standards). Name + paraphrase only. Standards are
  reference-only: never reproduce their text verbatim.

## Logic + contract test

- Pure Python stdlib. No numpy/scipy/pandas, no network, no external
  processes. Deterministic: no RNG (or seed any RNG with a fixed integer).
- Logic file: small focused functions with docstrings, no magic numbers
  (module constants), ValueError on non-physical inputs per your spec.
- Test file: `import unittest` + `unittest.main()` under `if __name__ ==
  "__main__":`; 15-35 test methods; assert your worked-example module outputs
  (run your module first, put the real values in the test within a tolerance
  you choose, and the magnitude bounds from the spec), boundary cases,
  ValueError rejections, and a round-trip or closed-form identity where the
  spec lists one. Must pass offline in <20s. Test file MUST be named
  test_<leaf>.py with UNDERSCORES (never hyphens - wave-37 kit lesson).
- Logic file MUST be named <leaf>_logic.py with UNDERSCORES (wave-37 kit
  lesson: 3 of 10 builders defaulted to hyphenated logic filenames - do not).
  Logic files NEVER start with test_.
- Run it: `cd ~/AeroSkills && python3 skills/<family>/<pack>/<leaf>/scripts/test_<leaf>.py`
  -> all tests pass, exit 0.

## eval fragment (eval/hit1-wave40-<leaf>.yaml)

# Hit@1 wave-40 fragment: <leaf> (<family>)
# Two tasks per new leaf skill. <id1> routes on <...>; <id2> routes on <...>.
tasks:
  - id: w40-<leaf>-1
    query: "<EXACT query text from your spec, copy verbatim>"
    intent: "<family>; <what the task routes on>"
    expected_skill: "<family>/<pack>/<leaf>"
  - id: w40-<leaf>-2
    query: "<EXACT query text from your spec, copy verbatim>"
    intent: "<family>; <what the task routes on>"
    expected_skill: "<family>/<pack>/<leaf>"

Use EXACTLY the two query texts given in your spec (copy them; they were
written to route to your leaf and only your leaf). The router scores tags
(x3) over name (x2) over description (x1) over body (x0.5).

## eval/skill-eval/<leaf>.json (exact schema)

{
  "skill": "<leaf>",
  "with_skill": 1.0,
  "without_estimate": 0.5,
  "delta": 0.5,
  "passed": <number of test methods that ran>,
  "failed": 0,
  "evidence": "contract test PASS; without-baseline 0.5 (fact terms N, procedure terms M)"
}
(without_estimate 0.5 with fact terms N>=1 and procedure terms M>=1 keeps
delta 0.5 >= 0.2 threshold. Set passed to the real unittest count from your run.)

## Ratings row (rate-at-creation, 9.5)

- Read eval/skill-ratings.md. The last numbered row is 536 at wave start;
  another builder may append concurrently, so ALWAYS re-read and use max+1.
- Append ONE row at the end of the table with the next number:
  | <n> | <family>/<pack>/<leaf> | PASS | ✓ | <standard-id> | <family> | 9.5 | PASS |
  (standard-id = the id from your spec's Ledger Standard line)
- Do NOT edit the "Total skills rated:" header line (the ops manager updates
  it at close).
- Self-check after appending: your leaf path appears exactly once in the file.
- If your appended number duplicates an existing row number (another builder
  appended between your read and write), edit your own row's number to max+1
  with a targeted patch of just that line. Never touch another leaf's row.

## Local verification before commit (required)

1. `cd ~/AeroSkills && python3 skills/<family>/<pack>/<leaf>/scripts/test_<leaf>.py` PASS.
2. Description within limits (<=1000 chars, <=148 words; no em dash in your
   files; no "classified"; no forbidden tokens from your spec).
3. `make completeness` (whole tree; if it FAILs only on OTHER in-flight
   leaves that are mid-write, rerun once after your commit; if it names YOUR
   leaf, fix and rerun until your leaf is clean).
4. Skip `make value-delta-all` (full-tree record rewrite - wave-38/39
   lesson: never run it; your own JSON from the schema above is the record).
5. Confirm fragment YAML parses: validate by eyeballing indentation against
   the template or write a tiny validator to /tmp and run it.
6. Run the CREATION GATE (founder 2026-09-04):
   `cd ~/AeroSkills && bash scripts/leaf-create-gate.sh skills/<family>/<pack>/<leaf>`
   -> exit 0 required. FAIL -> fix in-turn, re-run, then commit.

## Commit (EXPLICIT PATHS ONLY - never git add -A / git add . / git reset)

cd ~/AeroSkills
git add skills/<family>/<pack>/<leaf>/SKILL.md \
        skills/<family>/<pack>/<leaf>/scripts/<leaf>_logic.py \
        skills/<family>/<pack>/<leaf>/scripts/test_<leaf>.py \
        eval/hit1-wave40-<leaf>.yaml \
        eval/skill-eval/<leaf>.json \
        eval/skill-ratings.md
git diff --cached --name-only
# MUST show ONLY your six paths above (ledger is shared, expected). If
# anything else is staged, unstage it with: git restore --staged <that-path>
# (never git reset).
git commit -m "skills(<family>): add <leaf> (wave-40)"
git log -1 --format='%H %an <%ae> %s'
# identity MUST be ashfordeOU <contact@ashforde.org> (repo-local config; never
# run git config yourself)

If you hit "index.lock": wait 3 seconds and retry the add+commit up to 6
times. If a concurrent builder's commit swept some of your files in (shared
git index race, known wave-16/31/38/39 class): do NOT revert anything. Verify
your leaf files still exist on disk and are complete at HEAD after your
commit; if anything of yours is missing from the HEAD chain, add the missing
own paths and commit again with message
"skills(<family>): add <leaf> (wave-40 remainder)". Never fight design files,
ops files, or other leaves.

NEVER touch (read-only ok, no edits): ops/automation/**, scripts/** (harness),
Makefile, README.md, docs/**, standards-map.yaml, eval/hit1-corpus.yaml (the
big file - write only your fragment), skills/<family>/SKILL.md (router), any
other leaf. Read your spec under ops/automation/state/wave40-specs/ - do not
edit it.

## When done

Reply with a short summary (3-5 lines): leaf path, commit hash, files
committed, unittest count, delta, make completeness result for your leaf, any
deviations. Honesty required: if a gate could not be verified, say so.
