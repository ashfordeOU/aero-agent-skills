#!/usr/bin/env python3
"""AS9102 first article inspection logic (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, as9102/as9100: gated):
AS9102 is the aerospace first article inspection (FAI) standard. The
FAI report carries three forms: form 1 part accountability, form 2
material and special processes, form 3 characteristic accountability.
An FAI is complete only when all three forms are present and
acceptable and all nonconformances are closed. A delta FAI is
required when the production article changes: design change affecting
form, fit, or function; manufacturing source change; process change;
tooling change; material change; or a two-year lapse since the last
FAI. Characteristic accountability requires every design
characteristic to be measured and accounted for.
"""

FORM_NAMES = {
    1: "part accountability",
    2: "material and special processes",
    3: "characteristic accountability",
}

DELTA_FAI_TRIGGERS = [
    "design change affecting form fit or function",
    "manufacturing source change",
    "process change",
    "tooling change",
    "material change",
    "two year lapse",
]

REQUIRED_FORMS = (1, 2, 3)


def completeness(forms_present, form1_ok, form2_ok, form3_ok,
                 all_nonconformances_closed):
    """FAI completeness: (complete, missing) where complete is True only
    when forms 1, 2, and 3 are all present, each is acceptable, and all
    nonconformances are closed. missing is the sorted list of problems
    (missing form N, form N not ok, open nonconformances). forms_present
    may be a set or list of form numbers."""
    present = set(forms_present)
    form_ok = {1: form1_ok, 2: form2_ok, 3: form3_ok}
    problems = []
    for form in REQUIRED_FORMS:
        if form not in present:
            problems.append("missing form %d" % form)
        elif not form_ok[form]:
            problems.append("form %d not ok" % form)
    if not all_nonconformances_closed:
        problems.append("open nonconformances")
    return (not problems, sorted(problems))


def fai_status(forms_present, form1_ok, form2_ok, form3_ok,
               all_nonconformances_closed):
    """'complete' when the FAI completeness check passes, else
    'not complete'."""
    complete, _ = completeness(
        forms_present, form1_ok, form2_ok, form3_ok, all_nonconformances_closed
    )
    return "complete" if complete else "not complete"


def delta_fai_required(changes):
    """True when any entry in changes matches a delta FAI trigger
    keyword (case-insensitive substring match against the trigger list
    in either direction)."""
    for entry in changes:
        text = entry.lower()
        for trigger in DELTA_FAI_TRIGGERS:
            if trigger in text or text in trigger:
                return True
    return False


def characteristics_accounted(measured, total):
    """Characteristic accountability: True when the measured
    characteristic count covers the total population. Invalid inputs
    (total <= 0 or measured < 0) raise ValueError."""
    if total <= 0:
        raise ValueError("total must be positive, got %r" % (total,))
    if measured < 0:
        raise ValueError("measured must be non-negative, got %r" % (measured,))
    return measured >= total
