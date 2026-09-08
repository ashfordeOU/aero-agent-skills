# WAVE-47 BUILD: smith-predictor
REPO=skills
TASK=skill_build
TURNS=40
BUDGET=10

You are the Claude Code builder for ONE AeroSkills leaf in wave-47 at ~/AeroSkills (HEAD has wave-47 specs committed). Build the leaf named in TASK below to the full per-skill completeness standard.

READ FIRST, in order:
1. ops/automation/state/wave47-builder-kit.md — the shared builder kit (deliverables, anti-hang protocol, value-delta sampler rule, exact-float lesson, SKILL.md structure, six-artifact gate). Follow it EXACTLY.
2. Your engineering spec: ops/automation/state/wave47-specs/<LEAF>.md — this is YOUR CONTRACT. It pins equations, function signatures, worked-example parameters (REAL anchor outputs), validation list, Hit@1 corpus queries, and forbidden tokens. Follow it exactly; take your real module outputs as the unittest assert targets inside the spec's magnitude bounds.
3. The format exemplar skills/<FAMILY>/<PACK>/<SIBLING_REF>/SKILL.md if the spec names one.

DELIVERABLES (commit ALL six, then run leaf-create-gate):
1. skills/<FAMILY>/<PACK>/<LEAF>/SKILL.md (house 8-section structure, desc <= 1000 chars / 148 words, em-dash-free, Behavior contract section)
2. skills/<FAMILY>/<PACK>/<LEAF>/scripts/<LEAF>_logic.py (pure stdlib, small focused functions)
3. skills/<FAMILY>/<PACK>/<LEAF>/scripts/test_<LEAF>.py (stdlib unittest, deterministic offline, runs via python3 scripts/test_<LEAF>.py exit 0; tolerant asserts ONLY — no exact-float equality; test docstrings name the SKILL.md workflow steps for the value-delta sampler; NO machine-local sys.path — portable import)
4. eval/hit1-wave47-<LEAF>.yaml (2 corpus tasks from the spec's queries, exact format per builder kit)
5. eval/skill-eval/<LEAF>.json (value-delta record, exact schema per builder kit)
6. Append ONE row to eval/skill-ratings.md (rate-at-creation >= 9.5, ledger row per the spec's leaf-plan entry)

GATES BEFORE COMMIT: run the logic + tests under BOTH interpreters (python3 = 3.9/3.11 and the pyenv 3.13 — the kit explains), purge __pycache__, then run bash scripts/leaf-create-gate.sh (or the make target per kit) until PASS. Commit your OWN leaf immediately when complete with message: skills(<pack>): add <LEAF> (wave-47). Do NOT push. Do NOT touch any other leaf or ops/automation files. Do NOT delegate, do NOT ask questions.

TASK: build leaf skills/gnc-autonomy/control/smith-predictor/ per spec ops/automation/state/wave47-specs/smith-predictor.md
