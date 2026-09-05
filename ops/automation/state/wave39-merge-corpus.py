#!/usr/bin/env python3
"""Wave-39 corpus merge: append 2 tasks per wave-39 fragment into
hit1-corpus.yaml.

- Reads eval/hit1-wave39-*.yaml fragments (2 tasks each).
- Verifies id uniqueness against the existing corpus (tasks + future_pins).
- Inserts new tasks at the END of the tasks list (before future_pins: block).
- Updates the header with a wave-39 note; keeps all historical notes.
- Deletes the standalone fragments after a successful merge.
- Prints the new task count.

Run by the ops manager at wave close (subagents must never run merge
helpers against the live corpus - wave-15 lesson).
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
CORPUS = ROOT / "eval" / "hit1-corpus.yaml"
BASE_LEAVES = 521   # wave-38 close
BASE_SKILL = 533    # 12 routers + 521 leaves
BASE_TASKS = 1058


def main():
    text = CORPUS.read_text(encoding="utf-8")

    tasks_m = re.search(r"(?m)^tasks:\s*$", text)
    pins_m = re.search(r"(?m)^future_pins:\s*$", text)
    if not tasks_m or not pins_m:
        print("FAIL: cannot find tasks:/future_pins: blocks", file=sys.stderr)
        sys.exit(1)
    header = text[: tasks_m.start()]
    tasks_block = text[tasks_m.start() : pins_m.start()]
    pins_block = text[pins_m.start():]

    existing_ids = set(re.findall(r"(?m)^\s*- id:\s*(\S+)\s*$", tasks_block + pins_block))

    fragments = sorted(ROOT.glob("eval/hit1-wave39-*.yaml"))
    if not fragments:
        print("FAIL: no eval/hit1-wave39-*.yaml fragments found", file=sys.stderr)
        sys.exit(1)

    new_entries = []
    leaf_names = []
    for frag in fragments:
        ft = frag.read_text(encoding="utf-8")
        items = re.findall(
            r"(?ms)^  - id: (\S+)\n(.*?)(?=^  - id:|\Z)", ft
        )
        frag_ids = [i[0] for i in items]
        if len(frag_ids) != 2:
            print(f"FAIL: {frag.name} has {len(frag_ids)} tasks, expected 2", file=sys.stderr)
            sys.exit(1)
        for i, (tid, body) in enumerate(items):
            if tid in existing_ids:
                print(f"FAIL: id '{tid}' from {frag.name} already exists in corpus", file=sys.stderr)
                sys.exit(1)
            existing_ids.add(tid)
            entry = f"  - id: {tid}\n{body.rstrip()}\n"
            new_entries.append(entry)
        exp = re.search(r"(?m)^\s*expected_skill:\s*(\S+)", ft)
        leaf_names.append(exp.group(1) if exp else frag.stem)

    n_new = len(new_entries)
    n_leaf = BASE_LEAVES + len(fragments)
    n_skill = BASE_SKILL + len(fragments)
    n_tasks = BASE_TASKS + n_new
    new_tasks_block = tasks_block.rstrip() + "\n" + "".join(new_entries) + "\n"

    note = (
        "# P5.2 / Wave 39 (2026-09-05): fan-out continues on the public\n"
        f"# v1.0.0 model to {n_leaf} verified skills ({n_skill} SKILL.md under gate 1: 12 routers + {n_leaf}\n"
        "# leaves). Wave-39 new leaves: " + ", ".join(leaf_names) + ".\n"
        f"# Corpus: {n_tasks} tasks ({BASE_TASKS} prior plus {n_new} domain tasks). Owner: Ops\n"
        "# Manager, Wave 39 build.\n"
    )

    new_text = header.rstrip() + "\n" + note + new_tasks_block + pins_block
    CORPUS.write_text(new_text, encoding="utf-8")

    for frag in fragments:
        frag.unlink()

    print(f"Merged {n_new} tasks from {len(fragments)} fragments; corpus now {n_tasks} tasks; fragments deleted")
    return 0


if __name__ == "__main__":
    sys.exit(main())
