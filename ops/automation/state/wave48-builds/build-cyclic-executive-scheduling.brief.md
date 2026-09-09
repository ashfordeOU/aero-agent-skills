# WAVE-48 BUILD: cyclic-executive-scheduling
REPO=skills
TASK=skill_build
TURNS=40
BUDGET=10

You are the Claude Code builder for ONE AeroSkills leaf in wave-48 at ~/AeroSkills (HEAD has wave-48 specs committed, commit b48ef346). Build the leaf named in TASK below to the full per-skill completeness standard.

READ FIRST, in order:
1. ops/automation/state/wave48-builder-kit.md - the shared builder kit (deliverables, anti-hang protocol, value-delta sampler rule, exact-float lesson, SKILL.md structure, six-artifact gate, commit rules). Follow it EXACTLY.
2. Your engineering spec: ops/automation/state/wave48-specs/cyclic-executive-scheduling.md - this is YOUR CONTRACT. It pins equations, function signatures, worked-example parameters (REAL anchor outputs), validation list, Hit@1 corpus queries, and forbidden tokens. Follow it exactly; take your real module outputs as the unittest assert targets inside the spec's magnitude bounds. Spec prose and anchor outputs match - do not re-derive from memory.
3. The format exemplar sibling SKILL.md files named in your spec/kit if any.

DELIVERABLES (commit ALL six, then run leaf-create-gate):
1. skills/avionics/fsw/cyclic-executive-scheduling/SKILL.md (house 8-section structure, desc <= 1000 chars / 148 words, em-dash-free, Behavior contract section)
2. skills/avionics/fsw/cyclic-executive-scheduling/scripts/cyclic-executive-scheduling_logic.py (pure stdlib, small focused functions)
3. skills/avionics/fsw/cyclic-executive-scheduling/scripts/test_cyclic-executive-scheduling.py (stdlib unittest, deterministic offline, runs via python3 scripts/test_cyclic-executive-scheduling.py exit 0; tolerant asserts ONLY - no exact-float equality; test docstrings name the SKILL.md workflow steps for the value-delta sampler; NO machine-local sys.path - portable import)
4. eval/hit1-wave48-cyclic-executive-scheduling.yaml (2 corpus tasks from the spec's queries, exact format per builder kit)
5. eval/skill-eval/cyclic-executive-scheduling.json (value-delta record, exact schema per builder kit)
6. Append ONE row to eval/skill-ratings.md (rate-at-creation >= 9.5; ledger row number 646+ per wave-48 leaf plan)

GATES BEFORE COMMIT: run the logic + tests under BOTH interpreters (python3 and the pyenv 3.13 interpreter - the kit explains), purge __pycache__, then run bash scripts/leaf-create-gate.sh until PASS. Commit your OWN leaf immediately when complete with message: skills(fsw): add cyclic-executive-scheduling (wave-48). Do NOT push. Do NOT touch any other leaf or ops/automation files. Do NOT delegate, do NOT ask questions. If you hit index.lock, wait 3s and retry up to 6 times; if a concurrent builder's commit swept your files in, verify your leaf files exist and are complete at HEAD, re-add your own missing paths and commit again with message "skills(avionics/fsw): add cyclic-executive-scheduling (wave-48 remainder)". NEVER touch: ops/automation/**, scripts/** (harness), Makefile, README.md, docs/**, standards-map.yaml, eval/hit1-corpus.yaml (big file - write only your fragment), skills/<family>/SKILL.md (router), any other leaf.

TASK: build leaf skills/avionics/fsw/cyclic-executive-scheduling/ per spec ops/automation/state/wave48-specs/cyclic-executive-scheduling.md
