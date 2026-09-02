# Wave-23 builder kit (AeroSkills) — shared rules for leaf subagents

You are building ONE new leaf skill for the AeroSkills library at
/Users/enterprisehq/AeroSkills. Follow this kit exactly, then your
task-specific engineering spec (sent in your goal). Commit your own
leaf IMMEDIATELY when complete. Do not delegate, do not ask questions.

## Deliverables (per-skill completeness standard, commit ALL of these)

1. skills/<family>/<pack>/<leaf>/SKILL.md
2. skills/<family>/<pack>/<leaf>/scripts/<leaf>_logic.py  (pure stdlib logic)
3. skills/<family>/<pack>/<leaf>/scripts/test_<leaf>.py    (stdlib unittest contract test, offline deterministic, runs via `python3 scripts/test_<leaf>.py` and exits 0)
4. eval/hit1-wave23-<leaf>.yaml  (2 corpus tasks, exact format below)
5. eval/skill-eval/<leaf>.json   (value-delta record, exact schema below)
6. Append ONE row to eval/skill-ratings.md (rate-at-creation, 9.5)

Create references/ only when the SKILL body inlines long external data
that belongs in a reference doc; create assets/ only for templates the
body names. Most leaves need neither. NO broken refs: every
scripts/references/assets path named in your SKILL.md body must exist.

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
- standards: [ {id: <from your spec>, reference-only: true} ]  (ONLY ids that exist in standards-map.yaml; your spec gives the id)
- gated: false
- domain: <family>
- pack: <pack>            (the parent dir name, e.g. loads, electric, fsw, mdo)
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
- Tags: hyphenated compound terms only. NEVER single generic words like analysis, design, report, method, optimization, estimation, testing, inspection, sizing, loads, dynamics alone as tags — single generic tags steal corpus tasks from existing leaves and break routing. Your first tag should be the leaf name itself; add specific compound terms from the Trigger list.
- Do not reproduce proprietary standard text (no verbatim tables/sections from SAE/RTCA/IAQG/standards). Name + paraphrase only.

## Logic + contract test

- Pure Python stdlib. No numpy/scipy/pandas, no network, no external processes. Deterministic: seed any RNG with a fixed integer.
- Logic file: small focused functions with docstrings, no magic numbers (module constants), ValueError on non-physical inputs (negative mass/speed, out-of-range efficiency, etc.).
- Test file: `import unittest` + `unittest.main()` under `if __name__ == "__main__":`; 15-35 test methods; assert the worked-example numbers, boundary cases, ValueError rejections, and a round-trip identity where one exists. Must pass offline in <20s.
- Run it: `cd ~/AeroSkills && python3 skills/<family>/<pack>/<leaf>/scripts/test_<leaf>.py` -> all tests pass, exit 0.

## eval fragment (eval/hit1-wave23-<leaf>.yaml)

# Hit@1 wave-23 fragment: <leaf> (<family>)
# Two tasks per new leaf skill. <id1> routes on <...>; <id2> routes on <...>.
tasks:
  - id: w23-<leaf>-1
    query: "<realistic user question; include the leaf's distinctive hyphenated vocabulary; mirror phrasing style of existing corpus tasks in eval/hit1-corpus.yaml for your family>"
    intent: "<family>; <what the task routes on>"
    expected_skill: "<family>/<pack>/<leaf>"
  - id: w23-<leaf>-2
    query: "..."
    intent: "..."
    expected_skill: "<family>/<pack>/<leaf>"

Look at existing task phrasing: grep w22 entries at the end of
eval/hit1-corpus.yaml for your family. Write queries an engineer would
actually type. Make sure the two tasks do NOT overlap an existing leaf's
claim (read the sibling SKILL.md descriptions in your pack first).

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

- Read eval/skill-ratings.md. Find the current last numbered row (should be 318 at wave start; another builder may append concurrently, so always re-read).
- Append ONE row at the end of the table with the next number:
  | <n> | <family>/<pack>/<leaf> | PASS | ✓ | <standard-id> | <family> | 9.5 | PASS |
  (standard-id = the one id from your frontmatter standards list)
- Do NOT edit the "Total skills rated:" header line (the ops manager updates it at close).
- Self-check after appending: your leaf path appears exactly once in the file.
- If your appended number duplicates an existing row number (another builder appended between your read and write), edit your own row's number to max+1 with a targeted patch of just that line. Never touch another leaf's row.

## Local verification before commit (required)

1. `cd ~/AeroSkills && python3 skills/<family>/<pack>/<leaf>/scripts/test_<leaf>.py` PASS.
2. Description within limits (target <=1000 chars, <=148 words; no em dash in your files; no "classified").
3. `make completeness` (whole tree; if it FAILs only on OTHER in-flight leaves that are mid-write, rerun once after your commit; if it names YOUR leaf, fix and rerun until your leaf is clean).
4. `make value-delta` (sample proof; it rewrites records for the sampled leaves - harmless. It does not usually sample your leaf; your own JSON from the schema above is the record).
5. Confirm fragment YAML parses: `python3 -c` is blocked in this sandbox; instead validate by eyeballing indentation against the template (or write a tiny validator to /tmp and run it).

## Commit (EXPLICIT PATHS ONLY — never git add -A / git add . / git reset)

cd ~/AeroSkills
git add skills/<family>/<pack>/<leaf>/SKILL.md \
        skills/<family>/<pack>/<leaf>/scripts/<leaf>_logic.py \
        skills/<family>/<pack>/<leaf>/scripts/test_<leaf>.py \
        eval/hit1-wave23-<leaf>.yaml \
        eval/skill-eval/<leaf>.json \
        eval/skill-ratings.md
git diff --cached --name-only
# MUST show ONLY your six paths above (ledger is shared, expected). If anything else is staged, unstage it with: git restore --staged <that-path>  (never git reset).
git commit -m "skills(<family>): add <leaf> (wave-23)"
git log -1 --format='%H %an <%ae> %s'
# identity MUST be ashfordeOU <contact@ashforde.org> (repo-local config; never run git config yourself)

If you hit "index.lock" / "Unable to create .../.git/index.lock": wait 3 seconds and retry the add+commit up to 6 times.
If a concurrent builder's commit swept some of your files in (shared git index race, known wave-16 class): do NOT revert anything. Verify your leaf files still exist on disk; if your leaf is incomplete at HEAD after your commit, add the missing own paths and commit again with message "skills(<family>): add <leaf> (wave-23 remainder)". Never fight design files, ops files, or other leaves.

NEVER touch (read-only ok, no edits): ops/automation/**, scripts/** (harness), Makefile, README.md, docs/**, standards-map.yaml, eval/hit1-corpus.yaml (the big file — write only your fragment), skills/<family>/SKILL.md (router), any other leaf.

## When done

Reply with a short summary (3-5 lines): leaf path, commit hash, files committed, unittest count, delta, make completeness result for your leaf, any deviations. Honesty required: if a gate could not be verified, say so.
