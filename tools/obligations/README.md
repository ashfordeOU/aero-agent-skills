# Clause obligations: the tools

The contract these tools enforce, the measurement and the published schedule
are in [`docs/OBLIGATIONS.md`](../../docs/OBLIGATIONS.md). This page is the
map of the directory.

| File | What it does |
|---|---|
| `obligation_binding.py` | The rules for the `clauses:` front-matter key, and a narrow stdlib reader for it. Gate 1 (`scripts/spec_lint.py`) and gate 19 both call `validate()`, so the rule exists once. |
| `obligations_gate.py` | Gate 19, `make obligations`: every declared item has a row in `## Obligations` pointing at a step that exists in the leaf's numbered procedure. |
| `earm_items.py` | Reads an ESA EARM export handed in by path. `items` prints one clause's items to the terminal for a writer to read; `--ids` prints no text; `coverage` screens every binding against the export; `standards` lists the editions. A retired item is left out of the screens, and the export retires one two ways — the change status, or a withdrawal marker in place of the whole text. It never writes text to a file. |
| `test_obligations.py` | The gate and the binding rules, including a cross-check of the stdlib reader against PyYAML and the repository's two other front-matter readers. |
| `test_earm_items.py` | The export reader, against a small workbook built in a temporary directory from placeholder text. |

```
make obligations
python3 tools/obligations/obligations_gate.py [SKILL.md ...]
python3 tools/obligations/earm_items.py items --export <EARM.xlsx> --standard "<edition>" --clause <n> [--ids]
python3 tools/obligations/earm_items.py coverage --export <EARM.xlsx>
python3 tools/negative_controls/run_negative_controls.py --only obligations
```

No ECSS text is kept here, in the tests or anywhere else in this repository.
The export is read where it lies; the tests build their own.
