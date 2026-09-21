# Leaf-to-clause fidelity

Every other check in this repository asks whether the corpus is consistent with
itself. This one asks the question the whole stack rests on and nothing else
touches: **does a leaf faithfully render the clause it cites?**

It cannot be answered from inside the repository, because the repository
deliberately does not contain the standards. It needs the source documents, and
it needs a reader. This directory holds the instrument; the reader is separate,
on purpose.

## Three layers, reported apart and never summed

| | what it measures | how |
|---|---|---|
| **L1** | does the cited clause exist at all | mechanical, census over every leaf |
| **L2** | do the clause's terms appear in the rendering | mechanical, a screen not a verdict |
| **L3** | does the rendering say what the clause says | judged, sampled, blind |

Summing them would be the mistake. L1 catches a citation pointing at nothing.
L3 catches a citation pointing at the right place and describing it wrongly.
A corpus can score perfectly on one and badly on the other, and this one does.

## The grader is graded first

Every worksheet carries **planted controls**: a real clause paired with a
rendering drawn from a different clause. The grader is not told which items
they are or how many. `score` measures the catch rate **before** it reports
anything, and below the floor (default 0.80) it prints VOID and reports no
fidelity number at all.

This is the negative-control doctrine applied one level up. A grader nobody has
seen fail would report *faithful* forever, and a fidelity number produced by
such a grader is worse than no number, because it would be quoted.

## Verdicts

- `faithful` — a practitioner following the rendering would satisfy the clause.
- `partial` — correct as far as it goes, omits a requirement the clause imposes.
  **Counted as a miss.** A rendering that drops a requirement is how a supplier
  ends up non-compliant while believing otherwise.
- `unfaithful` — asserts something the clause does not require, contradicts it,
  or is about a different subject.
- `unjudgeable` — the extracted clause text is unreadable. Excluded from the
  denominator and reported, never folded into a pass.
- `contested` — recorded by the scorer, not by a reader, when independent
  readers did not converge. Also excluded and reported.

## Running it

    tools/fidelity/fidelity_audit.py --now <iso> census \
        --sources <dir of standards> --cache <dir> --out <result.json>

    tools/fidelity/fidelity_audit.py --now <iso> worksheet \
        --sources <dir> --sample 100 --seed <n> --out <OUTSIDE the repo>

    tools/fidelity/fidelity_audit.py --now <iso> score \
        --worksheet <w.json> --key <w.key.json> --verdicts <v.json> \
        --grader "<who graded it>" --out tools/fidelity/results/run-<tag>.json

`--now` is passed in rather than read, so the tool has no clock and a rerun over
the same inputs is reproducible. The extractor in use is recorded in every
result: a different extractor is a different measurement.

## Source text never enters this repository

The worksheet contains clause text so a reader can judge. Write it **outside**
the repository, and delete it when grading is done. Only the result file —
counts, rates and opaque item ids — belongs here.

## Two defects this tool found in itself before it found anything else

Both are recorded because the first version of each produced a confident wrong
number, and a tool that hides its own false starts is not an instrument.

1. **The clause index required the number and title on one line.** In these
   PDFs the extractor puts the clause number alone on its line and the title on
   the next; only 2 to 41 headings per document carry both. The index found
   3.1% of cited clauses and that looked like a devastating finding about the
   corpus. It was a finding about the index. Fixed, the same census reports
   92.5%.

2. **Edition suffixes are written four ways.** `-Rev.1`, `_Rev.1`, ` Rev.1`,
   and omitted entirely. Eighty-four citations to one standard resolved to
   nothing because its filename used an underscore. Citing a standard *without*
   its edition letter is a real defect — it does not identify which edition the
   leaf was written against — but it is a different defect from citing a clause
   that does not exist, and the census now counts them separately.
