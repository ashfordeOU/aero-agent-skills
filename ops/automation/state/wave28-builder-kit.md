# Wave-27 builder kit (AeroSkills) - shared rules for leaf subagents

You are building ONE new leaf skill for the AeroSkills library at
~/AeroSkills. Follow this kit exactly, then your task-specific
engineering spec (a file in ops/automation/state/wave28-specs/ named
for your leaf; read it first). Commit your own leaf IMMEDIATELY when
complete. Do not delegate, do not ask questions.

## Deliverables (per-skill completeness standard, commit ALL of these)

1. skills/<family>/<pack>/<leaf>/SKILL.md
2. skills/<family>/<pack>/<leaf>/scripts/<leaf>_logic.py  (pure stdlib logic)
3. skills/<family>/<pack>/<leaf>/scripts/test_<leaf>.py    (stdlib unittest contract test, offline deterministic, runs via `python3 scripts/test_<leaf>.py` and exits 0)
4. eval/hit1-wave28-<leaf>.yaml  (2 corpus tasks, exact format below)
5. eval/skill-eval/<leaf>.json   (value-delta record, exact schema below)
6. Append ONE row to eval/skill-ratings.md (rate-at-creation, 9.5)

Create references/ only when the SKILL body inlines long external data
that belongs in a reference doc; create assets/ only for templates the
body names. Most leaves need neither. NO broken refs: every
scripts/references/assets path named in your SKILL.md body must exist.

## Read your spec FIRST

ops/automation/state/wave28-specs/<leaf>.md contains YOUR leaf's
engineering contract: exact equations, function names, worked-example
parameters, validation list, sibling leaves to cite, standards ids, and
the exact corpus-query guidance for your two tasks. Follow it exactly.
If a formula or value in the spec is ambiguous, implement the standard
engineering method with the stated module constants and record the
assumption in the SKILL body. NEVER invent extra features that change
the spec's outputs.

## Anti-hang protocol (mandatory, wave-26 held)

Write your logic file in one pass with SMALL focused functions (each
5-25 lines, one job, docstring). Run the module import and a 3-line
smoke check immediately after writing the logic file, BEFORE writing
the full unittest file. Then write the compact unittest file (15-35
methods), run it, fix, and only then write SKILL.md + fragment + JSON +
ledger row and commit. No stalls: if something does not converge in two
attempts, implement the spec's fallback documented in your spec.

## SKILL.md structure (copy the exemplar: skills/propulsion/electric/hall-thruster/SKILL.md)

Frontmatter (agentskills.io):
- name: <leaf>
- description: "Use when you must <determine|compute|assess|size|run|...> ... :
  <what it does, the methods, the outputs>. Produces <deliverables>. Trigger:
  <8-16 routing keywords, hyphenated compound terms preferred>."
  Constraints: 50-150 WORDS and <=1024 CHARS total (target 700-1000 chars);
  must contain an action verb. Gate 1 caps at 1024 chars, gate 2 wants
  50-150 words + an action verb. Count before you commit.
- license: Apache-2.0
- compliance: STANDARDS-REF
- standards: [ {id: <from your spec>, reference-only: true} ]  (ONLY ids that exist in standards-map.yaml; your spec gives the ids)
- gated: false
- domain: <family>
- pack: <pack>            (the parent dir name, e.g. guidance, navigation, gas-turbine-cycle, orbit-mechanics, loads, composites, flight-management)
- compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
- metadata: {domain: <family>, subdomain: <pack>, tags: [<hyphenated tags>], version: 0.1.0, author: AeroSkills}

Body sections (mirror hall-thruster): intro paragraph + pairing leaves,
## Domain quick reference (the 5-10 equations that matter),
## Workflow (numbered steps referencing your logic functions),
## Worked example (concrete numbers),
## Verification (deterministic checks incl. ValueError rejection of
non-physical inputs; reference the contract test),
## Related leaves (real sibling paths only),
## Contract test (how to run; what it covers),
## Compliance (STANDARDS-REF, gated false; standards referenced not
reproduced).

HARD TEXT RULES:
- ZERO em dashes (the character - is banned; use commas or hyphens) in every file you write.
- NEVER use the word "classified" (content-policy sweep). Use categorized/rated/sensitive-marking instead.
- Tags: hyphenated compound terms only. NEVER single generic words like analysis, design, report, method, optimization, estimation, testing, inspection, sizing, loads, dynamics alone as tags - single generic tags steal corpus tasks from existing leaves and break routing. Your first tag should be the leaf name itself; add specific compound terms from your spec's Trigger list.
- FORBIDDEN TOKENS in your description/tags/tasks: your spec lists tokens that belong to a sibling leaf's claim. Do NOT put them in your description, tags, or corpus queries.
- Do not reproduce proprietary standard text (no verbatim tables/sections from SAE/RTCA/IAQG/FAA/standards). Name + paraphrase only.

## Logic + contract test

- Pure Python stdlib. No numpy/scipy/pandas, no network, no external processes. Deterministic: seed any RNG with a fixed integer.
- Logic file: small focused functions with docstrings, no magic numbers (module constants), ValueError on non-physical inputs (negative mass/speed, out-of-range efficiency, etc.).
- Test file: `import unittest` + `unittest.main()` under `if __name__ == "__main__":`; 15-35 test methods; assert the worked-example numbers from your spec (run your own module to get exact values, then assert within a tolerance), boundary cases, ValueError rejections, and a round-trip identity where one exists. Must pass offline in <20s.
- Run it: `cd ~/AeroSkills && python3 skills/<family>/<pack>/<leaf>/scripts/test_<leaf>.py` -> all tests pass, exit 0.

## eval fragment (eval/hit1-wave28-<leaf>.yaml)

# Hit@1 wave-28 fragment: <leaf> (<family>)
# Two tasks per new leaf skill. <id1> routes on <...>; <id2> routes on <...>.
tasks:
  - id: w27-<leaf>-1
    query: "<realistic user question; use EXACTLY the distinctive tokens listed in your spec; mirror phrasing style of existing corpus tasks in eval/hit1-corpus.yaml for your family>"
    intent: "<family>; <what the task routes on>"
    expected_skill: "<family>/<pack>/<leaf>"
  - id: w27-<leaf>-2
    query: "..."
    intent: "..."
    expected_skill: "<family>/<pack>/<leaf>"

Look at existing task phrasing: grep w26 entries at the end of
eval/hit1-corpus.yaml for your family. Write queries an engineer would
actually type. Make sure the two tasks do NOT overlap an existing leaf's
claim (read the sibling SKILL.md descriptions in your pack first). The
router scores tags (x3) over name (x2) over description (x1) over body
(x0.5), so your tasks MUST carry the leaf-name or spec-listed hyphenated
tokens, and your tags must carry them too.

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

- Read eval/skill-ratings.md. The last numbered row is 379 at wave
  start; another builder may append concurrently, so ALWAYS re-read and
  use max+1.
- Append ONE row at the end of the table with the next number:
  | <n> | <family>/<pack>/<leaf> | PASS | ✓ | <standard-id> | <family> | 9.5 | PASS |
  (standard-id = the id(s) from your spec's Ledger Standard line)
- Do NOT edit the "Total skills rated:" header line (the ops manager updates it at close).
- Self-check after appending: your leaf path appears exactly once in the file.
- If your appended number duplicates an existing row number (another builder appended between your read and write), edit your own row's number to max+1 with a targeted patch of just that line. Never touch another leaf's row.

## Local verification before commit (required)

1. `cd ~/AeroSkills && python3 skills/<family>/<pack>/<leaf>/scripts/test_<leaf>.py` PASS.
2. Description within limits (<=1000 chars, <=148 words; no em dash in your files; no "classified"; no forbidden tokens from your spec).
3. `make completeness` (whole tree; if it FAILs only on OTHER in-flight leaves that are mid-write, rerun once after your commit; if it names YOUR leaf, fix and rerun until your leaf is clean).
4. `make value-delta` (sample proof; it rewrites records for the sampled leaves - harmless. It does not usually sample your leaf; your own JSON from the schema above is the record).
5. Confirm fragment YAML parses: python3 -c is blocked in this sandbox; validate by eyeballing indentation against the template or write a tiny validator to /tmp and run it.

## Commit (EXPLICIT PATHS ONLY - never git add -A / git add . / git reset)

cd ~/AeroSkills
git add skills/<family>/<pack>/<leaf>/SKILL.md \
        skills/<family>/<pack>/<leaf>/scripts/<leaf>_logic.py \
        skills/<family>/<pack>/<leaf>/scripts/test_<leaf>.py \
        eval/hit1-wave28-<leaf>.yaml \
        eval/skill-eval/<leaf>.json \
        eval/skill-ratings.md
git diff --cached --name-only
# MUST show ONLY your six paths above (ledger is shared, expected). If anything else is staged, unstage it with: git restore --staged <that-path>  (never git reset).
git commit -m "skills(<family>): add <leaf> (wave-28)"
git log -1 --format='%H %an <%ae> %s'
# identity MUST be ashfordeOU <contact@ashforde.org> (repo-local config; never run git config yourself)

If you hit "index.lock" / "Unable to create .../.git/index.lock": wait 3 seconds and retry the add+commit up to 6 times.
If a concurrent builder's commit swept some of your files in (shared git index race, known wave-16 class): do NOT revert anything. Verify your leaf files still exist on disk; if your leaf is incomplete at HEAD after your commit, add the missing own paths and commit again with message "skills(<family>): add <leaf> (wave-28 remainder)". Never fight design files, ops files, or other leaves.

NEVER touch (read-only ok, no edits): ops/automation/**, scripts/** (harness), Makefile, README.md, docs/**, standards-map.yaml, eval/hit1-corpus.yaml (the big file - write only your fragment), skills/<family>/SKILL.md (router), any other leaf. Read your spec under ops/automation/state/wave28-specs/ - do not edit it.

## When done

Reply with a short summary (3-5 lines): leaf path, commit hash, files committed, unittest count, delta, make completeness result for your leaf, any deviations. Honesty required: if a gate could not be verified, say so.
