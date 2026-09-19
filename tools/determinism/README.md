# Determinism under perturbation

The corpus makes one central promise: a verdict reproduces. Until now that
promise was asserted, not measured, and the evidence behind it was "it ran
twice here". Running twice holds every hidden input still. It cannot tell a
deterministic pipeline apart from one that happens to agree with itself as
long as nothing moves.

This directory measures the promise instead. It runs a real pipeline many
times, moves exactly one environmental thing per run, and **byte-diffs the
artefacts**. Not the summary line — the per-case verdict record.

```
python3 tools/determinism/perturb.py --tasks 64 --ramdisk --report - \
    --scan packages/aero-agent-skills/manifest.json \
    --scan docs/metrics.json
```

Exit status: `0` every perturbation run was byte-identical · `1` at least one
moved · `2` the baseline itself failed · `3` the negative control did not go
red, so the measurement is void.

## What is measured

The pipeline is gate 5, the offline router, resolved over a sample of its
case set (`scripts/router_eval.py` against `eval/hit1-corpus.yaml`). It was
chosen because it is the deterministic job whose output a reviewer would
actually check.

Four artefacts are compared byte for byte on every run:

| artefact | what it is |
| --- | --- |
| `verdict.txt` | one line per routed case: winning skill and score |
| `stdout.txt` | the raw stream, unedited |
| `stderr.txt` | warnings a changed environment provokes show up here |
| `exit_code.txt` | the status the gate would report |

`verdict.txt` deliberately excludes the trailing `N/N tasks Hit@1` line. A
summary is precisely the part of an output that holds still while the
results move underneath it; diffing it would be the reassurance this tool
exists to replace.

## The axes

| axis | what moves |
| --- | --- |
| `instrument` | a leaf is deleted from a copy of the input — a negative control |
| `repeat` | nothing; the noise floor |
| `cwd` | the directory the process starts in, including `/` and `$HOME` |
| `locale` | `LC_ALL` and `LANG`, including a decimal-comma locale, a dotless-i locale, a non-Latin locale and a non-UTF-8 codec |
| `tz` | `TZ`, including offsets that are not whole hours and one past the date line |
| `hostname` | the name the process believes the machine has (see limits) |
| `umask` | the file-creation mask the process inherits |
| `hashseed` | `PYTHONHASHSEED`, fixed values and `random` |
| `fileorder` | the order the filesystem hands back directory entries |
| `interpreter` | every Python minor version installed on the host |
| `env` | `HOME`, `TMPDIR`, `TERM`, `COLUMNS`, `USER`, `SOURCE_DATE_EPOCH`, `PYTHONUTF8`, `PYTHONDONTWRITEBYTECODE`, and an unrelated bulk variable |

Each variant differs from the baseline in one declared way. The baseline
environment is written out in full rather than inherited, so no variable the
parent shell happened to carry can act as an unmeasured input;
`check_one_thing_moved` is the guard, and the unit suite asserts it.

## The instrument check

A page of green rows is also what a broken comparator produces. Before any
row is worth reading, the comparison has to be shown capable of going red.
The `instrument` row removes the winning skill for the first sampled case
from a copy of the input; the verdict has to change. If it does not, the
harness says **BLIND INSTRUMENT** at the top of the report and exits `3`.

## Inputs are frozen first

The corpus sample and a SKILL.md-only copy of the tree are written into the
run root before the first run, and every run — baseline included — reads
that copy. Without this, an edit to the working tree part-way through the
matrix would arrive as a determinism failure that is really a race. The
report prints the digest of exactly what was read.

## Hermeticity

Byte-stability on one machine is necessary, not sufficient. `hermeticity.py`
scans artefact bytes for the traces that make an artefact machine- or
moment-specific even when it happens to reproduce here: embedded timestamps,
absolute paths, build ids and UUIDs, host and account names, locale-shaped
numbers and dates, and Python container reprs, which leak iteration order.
It runs standalone too:

```
python3 tools/determinism/hermeticity.py <artefact> [...]
```

Exit `1` if any high-severity finding is present. Point `--scan` at the
artefacts the repository generates, not only at the ones this harness
produces — a generated manifest is where a build id or a timestamp actually
tends to live.

Set and dict ordering is the one violation no pattern can see. The test for
it is the `hashseed` axis, not the scanner.

## Limits, stated rather than implied

An axis this host could not move is printed in an **Untested axes** table
and is never scored as a pass. On a single macOS host that table always
contains at least:

- **a second operating system** — no Linux or Windows run was performed;
- **a second CPU architecture** — none was available;
- **the kernel host name** — changing it needs administrator rights and
  macOS offers no user-level UTS namespace, so only an environment-variable
  proxy was moved. The artefacts are scanned for the machine's real name
  instead, which is the useful half of the question;
- **a wall-clock jump** — the system clock was not moved; the scanner looks
  for embedded timestamps instead.

Two further honest notes:

- **Creation order does not move readdir order on APFS.** That is measured,
  not assumed: the harness builds a reverse-order copy and compares the raw
  `os.scandir` sequence. When it matches, the variant is dropped and the
  value is listed as untested, because running it would have proved nothing.
  `--ramdisk` supplies a real second ordering by formatting a small,
  temporary HFS+ ram disk, which returns entries in catalog order; it is
  unmounted and detached when the run ends.
- **`umask` has low power over this pipeline**, which writes no files of its
  own. The artefact files are created by the child shell so the child's mask
  really does reach them, and the report shows the mode bits changing — but
  the content cannot move by that route. The row is reported for
  completeness, labelled for what it is.

## Cost

Roughly seven seconds of fixed cost per run to index the tree, plus about a
third of a second per sampled case. `--tasks 64` is the default and keeps a
full matrix near half an hour. `--tasks 0` runs the whole case set and takes
hours; use it when a release is being cut, not in a loop.

## Suggested `make` wiring

Not wired here — the Makefile is owned centrally.

```make
# Determinism measurement (not a gate): run the offline router under
# systematically perturbed environments and byte-diff the artefacts.
.PHONY: determinism determinism-test
determinism:
	@python3 tools/determinism/perturb.py --tasks 64 --ramdisk --report - \
	    --scan packages/aero-agent-skills/manifest.json \
	    --scan docs/metrics.json

determinism-test:
	@python3 -m unittest discover -s tools/determinism -p 'test_*.py'
```

`determinism-test` is the fast one: it exercises the harness against a tiny
built-in pipeline and needs neither the skills tree nor a ram disk.

## Tests

```
python3 -m unittest discover -s tools/determinism -p 'test_*.py' -v
```

`unittest` writes its `OK` line on stderr. Capture both streams or a pass
will read as a failure.

Standard library only, no network, nothing written inside the repository.
