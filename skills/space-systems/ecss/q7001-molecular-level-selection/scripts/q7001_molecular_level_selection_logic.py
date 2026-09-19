"""Molecular (NVR) cleanliness level selection per hardware category.

Anchor: ECSS-Q-ST-70-01C, the cleanliness *levels* clause -- deciding which
molecular (non-volatile residue) surface cleanliness level each category of
hardware has to be built, delivered and maintained to. Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the level ladder the project works to: an ordered set of named
   molecular levels, each an areal residue density in mg/m^2.
2. For each hardware category, turn its allowed end-of-life performance
   degradation into an allowed residue density through the category's own
   sensitivity coefficient (degradation per mg/m^2 of residue).
3. Subtract what the category will accumulate after delivery -- ground phases
   plus on-orbit self-contamination -- to leave the residue density the
   category may carry at delivery.
4. Select the least demanding ladder level that still sits at or under that
   delivery allowance, so a category is not driven to a tighter level than its
   own performance requires.
5. Enforce consistency: a category may never be assigned a level looser than a
   contractually imposed floor, and an enclosure inherits the tightest level of
   everything it encloses.
"""

import math

__all__ = [
    "LEVEL_TOLERANCE",
    "validate_level_ladder",
    "validate_positive",
    "allowable_residue_mg_m2",
    "delivery_allowance_mg_m2",
    "select_level",
    "level_value",
    "tightest_level",
    "level_margin_fraction",
    "assess_category",
    "select_molecular_levels",
]

# A ladder value that the allowance lands on exactly is selectable. The
# allowance is a quotient of two measured quantities, so an exact equality can
# sit a few ULPs either side; absorb the representation error here rather than
# by loosening the ladder.
LEVEL_TOLERANCE = 1e-12


def validate_positive(value, label, allow_zero=False):
    """Return value as a finite positive float (or non-negative if allowed)."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    v = float(value)
    if not math.isfinite(v):
        raise ValueError("%s must be finite" % label)
    if allow_zero:
        if v < 0.0:
            raise ValueError("%s must be non-negative, got %r" % (label, value))
    elif v <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return v


def validate_level_ladder(ladder):
    """Return the ladder as ordered (name, mg_per_m2) pairs, tightest first."""
    if not isinstance(ladder, (list, tuple)) or len(ladder) < 2:
        raise ValueError("level ladder needs at least two named levels")
    entries = []
    seen = set()
    for i, item in enumerate(ladder):
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            raise ValueError("ladder[%d] must be a (name, mg_per_m2) pair" % i)
        name, value = item
        if not isinstance(name, str) or not name.strip():
            raise ValueError("ladder[%d] name must be a non-empty string" % i)
        if name in seen:
            raise ValueError("ladder level name %r appears twice" % name)
        seen.add(name)
        entries.append((name, validate_positive(value, "ladder[%d] mg_per_m2" % i)))
    for i in range(1, len(entries)):
        if entries[i][1] <= entries[i - 1][1]:
            raise ValueError(
                "ladder must increase strictly in residue density (index %d, %r)"
                % (i, entries[i][0])
            )
    return entries


def allowable_residue_mg_m2(degradation_budget, sensitivity_per_mg_m2):
    """Invert the linear degradation model to an allowed residue density.

    degradation_budget is the end-of-life performance change the category may
    absorb (absorptance rise, transmittance loss, ...); sensitivity is the
    change produced per mg/m^2 of deposited residue on that surface.
    """
    budget = validate_positive(degradation_budget, "degradation_budget")
    sens = validate_positive(sensitivity_per_mg_m2, "sensitivity_per_mg_m2")
    return budget / sens


def delivery_allowance_mg_m2(allowable_eol, post_delivery_accumulation):
    """Return the residue density the category may carry at delivery."""
    eol = validate_positive(allowable_eol, "allowable_eol")
    later = validate_positive(
        post_delivery_accumulation, "post_delivery_accumulation", allow_zero=True
    )
    if later >= eol:
        raise ValueError(
            "post-delivery accumulation %g mg/m^2 consumes the whole end-of-life "
            "allowance %g mg/m^2; no delivery allowance remains" % (later, eol)
        )
    return eol - later


def level_value(ladder, name):
    """Return the residue density of a named ladder level."""
    entries = validate_level_ladder(ladder)
    for entry_name, value in entries:
        if entry_name == name:
            return value
    raise ValueError("level %r is not on the ladder" % (name,))


def select_level(ladder, allowance_mg_m2):
    """Return the least demanding ladder level at or under the allowance."""
    entries = validate_level_ladder(ladder)
    allowance = validate_positive(allowance_mg_m2, "allowance_mg_m2")
    chosen = None
    for name, value in entries:
        if value < allowance or math.isclose(
            value, allowance, rel_tol=LEVEL_TOLERANCE, abs_tol=0.0
        ):
            chosen = (name, value)
        else:
            break
    if chosen is None:
        raise ValueError(
            "allowance %g mg/m^2 is tighter than the tightest ladder level %r "
            "(%g mg/m^2); the ladder cannot meet this category"
            % (allowance, entries[0][0], entries[0][1])
        )
    return chosen


def tightest_level(ladder, names):
    """Return the tightest of several named levels, for an enclosing item."""
    entries = validate_level_ladder(ladder)
    order = {name: i for i, (name, _value) in enumerate(entries)}
    if not isinstance(names, (list, tuple)) or not names:
        raise ValueError("names must be a non-empty sequence of level names")
    best = None
    for name in names:
        if name not in order:
            raise ValueError("level %r is not on the ladder" % (name,))
        if best is None or order[name] < order[best]:
            best = name
    return (best, entries[order[best]][1])


def level_margin_fraction(level_mg_m2, allowance_mg_m2):
    """Return the unused fraction of the allowance at the selected level."""
    level = validate_positive(level_mg_m2, "level_mg_m2")
    allowance = validate_positive(allowance_mg_m2, "allowance_mg_m2")
    return (allowance - level) / allowance


def assess_category(category, ladder):
    """Select and grade the molecular level for one hardware category.

    category keys: name, degradation_budget, sensitivity_per_mg_m2,
    post_delivery_accumulation (optional, default 0), imposed_floor_level
    (optional ladder level name the category may not be looser than).
    """
    if not isinstance(category, dict):
        raise ValueError("category must be a mapping")
    for key in ("name", "degradation_budget", "sensitivity_per_mg_m2"):
        if key not in category:
            raise ValueError("category missing required key %r" % key)
    name = category["name"]
    if not isinstance(name, str) or not name.strip():
        raise ValueError("category name must be a non-empty string")
    entries = validate_level_ladder(ladder)
    allowable_eol = allowable_residue_mg_m2(
        category["degradation_budget"], category["sensitivity_per_mg_m2"]
    )
    allowance = delivery_allowance_mg_m2(
        allowable_eol, category.get("post_delivery_accumulation", 0.0)
    )
    selected_name, selected_value = select_level(entries, allowance)
    findings = []
    floor = category.get("imposed_floor_level")
    if floor is not None:
        order = {n: i for i, (n, _v) in enumerate(entries)}
        if floor not in order:
            raise ValueError("imposed_floor_level %r is not on the ladder" % (floor,))
        if order[selected_name] > order[floor]:
            findings.append(
                "performance allows %s but the imposed floor %s is tighter; "
                "the floor governs" % (selected_name, floor)
            )
            selected_name = floor
            selected_value = entries[order[floor]][1]
    return {
        "category": name,
        "allowable_eol_mg_m2": allowable_eol,
        "delivery_allowance_mg_m2": allowance,
        "selected_level": selected_name,
        "selected_mg_m2": selected_value,
        "margin_fraction": level_margin_fraction(selected_value, allowance),
        "findings": findings,
    }


def select_molecular_levels(spec):
    """Run the full level-selection step for a set of hardware categories.

    spec keys: ladder, categories (sequence of category mappings), optional
    enclosures mapping an enclosure name to the category names it encloses.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("ladder", "categories"):
        if key not in spec:
            raise ValueError("spec missing required key %r" % key)
    entries = validate_level_ladder(spec["ladder"])
    categories = spec["categories"]
    if not isinstance(categories, (list, tuple)) or not categories:
        raise ValueError("spec['categories'] must be a non-empty sequence")
    records = []
    by_name = {}
    for category in categories:
        record = assess_category(category, entries)
        if record["category"] in by_name:
            raise ValueError("category %r appears twice" % record["category"])
        by_name[record["category"]] = record
        records.append(record)
    enclosure_records = []
    for enclosure, contained in (spec.get("enclosures") or {}).items():
        if not isinstance(contained, (list, tuple)) or not contained:
            raise ValueError("enclosure %r must list at least one category" % enclosure)
        missing = [c for c in contained if c not in by_name]
        if missing:
            raise ValueError(
                "enclosure %r references unknown categories %s" % (enclosure, missing)
            )
        name, value = tightest_level(
            entries, [by_name[c]["selected_level"] for c in contained]
        )
        enclosure_records.append(
            {
                "enclosure": enclosure,
                "encloses": list(contained),
                "inherited_level": name,
                "inherited_mg_m2": value,
            }
        )
    driving = min(records, key=lambda r: (r["selected_mg_m2"], r["category"]))
    return {
        "records": records,
        "enclosures": enclosure_records,
        "driving_category": driving["category"],
        "driving_level": driving["selected_level"],
        "findings": [f for r in records for f in r["findings"]],
    }
