# RD4 State Note — rescue-first re-dispatch #4 (2026-08-31 23:5x -> 00:0x)

Committed by parent during re-dispatch #4 so a reaped parent leaves a clean
rescue trail. Read BEFORE acting; supersede with a new note on the next kill.

## What landed so far (committed, survives)
- a6bd27c ops: keep wave-6 merge/inventory/desc helpers, drop stale prep scratch
  (state/: wave6-merge-corpus.py, wave6-inventory.sh, wave6-desc-lengths.py kept;
  check-env.sh / wave6-locate-skills.sh / wave6-template-inventory.sh /
  scratch_corpus_inspect.py swept to /tmp/aeroskills-sweep-rd4/)
- 94c9af0 ops: refresh baseline counts to 113 after fuselage-sizing rescue
  (README badge/prose/roadmap 112 -> 113; run-tests P2 fixture skills=112 -> 113)

## Fan-out (STEP 1)
- 9 locked leaves dispatched 23:58:38 via delegate_task (deleg_ac36fcf8),
  one subagent each: airfoil-geometry, oblique-shock, dynamic-stability,
  descent-performance, pursuit-guidance, inertial-navigation,
  load-spectrum-counting, material-selection, life-cycle-cost.
- Children COMMIT THEIR OWN LEAF + eval/hit1-wave6-<leaf>.yaml fragment.
- Steering sent: repo-wide count gates (numbers.yaml / run-tests P2 / README
  badge / routers) are PARENT-owned; children commit on make validate 5/5 +
  gate-pytest-contract.sh, noting baseline-count-only failures.
- As of note: 0 leaf dirs, 0 fragments on disk; all 9 children running.

## Parent steps still open
- STEP 2 merge: run ops/automation/state/wave6-merge-corpus.py when fragments
  exist (merges ALL eval/hit1-wave6-*.yaml, deletes them, inserts note).
  NOTE: helper note hardcodes re-dispatch #3 / 122 / 134 / 258 — patch note to
  re-dispatch #4 and to ACTUAL landed count before running if not all 9 land.
- STEP 3 routers: rewrite 5 family tables to list only built leaves. All 5 read
  into parent context. structures table is MANGLED (broken pipes, missing
  crack-growth / miner-damage / laminate-stiffness rows — they EXIST on disk).
  vehicle-design router is MISSING the fuselage-sizing row (9522676 landed
  without router update) — add it. Desc budget: gnc-autonomy 1026 chars
  (OVER 1024, trim ~100+ while adding 2 leaves), vehicle-design 1024 (at
  limit, trim while adding 2 rows), flight-mechanics 1015, aerodynamics 964,
  structures 525 (full rewrite).
- STEP 4 badge: README badge 113 -> 113+leaves landed; add new stale-number
  guard patterns for the 112-class ('112 skills', '112 leaf skills',
  '112 verified', '124 SKILL.md', '240/240', '240 tasks') ONLY AFTER README
  is updated (README line 355 currently says '113 verified skills'; a
  '113 verified' pattern must not be added until README moves to the new
  count); N23/N24 fixtures.
- STEP 5 gates: baseline make validate 5/5 + make attest 3/3 + stale guard
  verified GREEN at 113 (rd4). run-tests P2 fixed to 113.
- STEP 6 push: GITHUB_TOKEN_ARJUN explicit (never Ashforde). ls-remote verify.
- STEP 7 post GROUP 160.

## Reaper lesson (13 kills)
Parent ~8-10 min life; delegate children die with it. Surviving work =
committed work only. Next dispatch: rescue-first, fan out first, keep lean.
