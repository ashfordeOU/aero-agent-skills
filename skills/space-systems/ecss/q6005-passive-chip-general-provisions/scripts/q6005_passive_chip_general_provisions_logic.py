"""Baseline delivery conditions for any purchase of bare passive chips.

Anchor: ECSS-Q-ST-60-05C clause 8.2.1 (general provisions -- the conditions
that hold for every passive chip delivery, whatever the element type on the
order line). Paraphrased into an implementable procedure; no standard text is
reproduced.

Procedure implemented here
--------------------------
1. Decide whether the supply route is acceptable on its own terms: a source
   the procurement authority has approved, or a distributor that carries an
   unbroken traceability chain back to the manufacturer.
2. Size the visual examination from the delivered lot size through a banded
   sample plan with a zero accept number, and confirm the sample actually
   examined was not smaller than the plan.
3. Convert the date code and the delivery date into an age in months and
   compare it with the age limit the delivery carries.
4. Judge the packaging against what a bare chip needs -- individual cavity
   carriage, static protection, and a dry pack when the element is moisture
   sensitive.
5. Confirm the delivery documents the baseline calls for arrived with it.
6. Combine the five into a lot disposition -- accept, conditional or reject --
   and name the finding that governs it.
"""

import math

__all__ = [
    "AGE_TOLERANCE_MONTHS",
    "WEEKS_PER_YEAR",
    "MONTHS_PER_YEAR",
    "SAMPLE_PLAN",
    "REQUIRED_DOCUMENTS",
    "ACCEPTABLE_CARRIERS",
    "DISPOSITION_ORDER",
    "parse_date_code",
    "date_code_age_months",
    "sample_size",
    "assess_examination",
    "assess_source",
    "assess_age",
    "assess_packaging",
    "assess_documents",
    "assess_general_provisions",
]

# Ages are a week difference scaled by 12/52: a delivery sitting exactly on a
# 24-month limit must not be pushed past it by representation error.
AGE_TOLERANCE_MONTHS = 1e-9

WEEKS_PER_YEAR = 52.0
MONTHS_PER_YEAR = 12.0

# (inclusive upper bound of the lot size band, elements examined). None means the
# band has no upper bound. Accept number is zero throughout.
SAMPLE_PLAN = (
    (15, None),
    (50, 13),
    (150, 20),
    (500, 32),
    (1200, 50),
    (None, 80),
)

REQUIRED_DOCUMENTS = (
    "certificate-of-conformity",
    "lot-traceability-record",
    "inspection-data",
)

# Carriage that keeps an unencapsulated chip from rubbing against its neighbours.
ACCEPTABLE_CARRIERS = ("waffle-pack", "tape-and-reel", "gel-pack")

DISPOSITION_ORDER = ("accept", "conditional", "reject")


def _require_text(value, label):
    """Return a lowercased, stripped token, raising on anything else."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    token = value.strip().lower()
    if not token:
        raise ValueError("%s must not be empty" % label)
    return token


def _require_int(value, label):
    """Return an int, raising on a bool, a float or anything non-integral."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    return value


def parse_date_code(code):
    """Return (year, week) from a four-digit year-week manufacturing date code."""
    if isinstance(code, int) and not isinstance(code, bool):
        text = "%04d" % code
    elif isinstance(code, str):
        text = code.strip()
    else:
        raise ValueError("date code must be a string or an integer, got %r" % (code,))
    if len(text) != 4 or not text.isdigit():
        raise ValueError("date code %r must be four digits of the form yyww" % (code,))
    year = int(text[:2])
    week = int(text[2:])
    if week < 1 or week > 53:
        raise ValueError("date code %r carries week %d, outside 1..53" % (code, week))
    return (year, week)


def date_code_age_months(date_code, delivery_code):
    """Return the age in months between a date code and the delivery week."""
    made_year, made_week = parse_date_code(date_code)
    delivered_year, delivered_week = parse_date_code(delivery_code)
    year_gap = delivered_year - made_year
    if year_gap < -50:
        year_gap += 100
    weeks = year_gap * WEEKS_PER_YEAR + (delivered_week - made_week)
    if weeks < 0.0:
        raise ValueError(
            "delivery week %s precedes the date code %s" % (delivery_code, date_code)
        )
    return weeks * MONTHS_PER_YEAR / WEEKS_PER_YEAR


def sample_size(lot_size):
    """Return the number of elements the visual examination covers."""
    size = _require_int(lot_size, "lot_size")
    if size <= 0:
        raise ValueError("lot_size must be positive, got %d" % size)
    for upper, sample in SAMPLE_PLAN:
        if upper is None or size <= upper:
            return size if sample is None else min(sample, size)
    raise ValueError("sample plan does not cover lot size %d" % size)


def assess_examination(lot_size, examined):
    """Compare the elements actually examined with the plan the lot size sets."""
    planned = sample_size(lot_size)
    count = _require_int(examined, "examined")
    if count < 0:
        raise ValueError("examined must not be negative, got %d" % count)
    if count > lot_size:
        raise ValueError(
            "examined %d exceeds the lot size %d" % (count, lot_size)
        )
    sufficient = count >= planned
    return {
        "lot_size": lot_size,
        "planned_sample": planned,
        "examined": count,
        "sufficient": sufficient,
        "finding": None
        if sufficient
        else "visual examination covered %d elements; the plan for a lot of %d is %d"
        % (count, lot_size, planned),
    }


def assess_source(source_kind, traceability_chain=True):
    """Judge the supply route the delivery arrived through."""
    kind = _require_text(source_kind, "source_kind").replace("_", "-").replace(" ", "-")
    if kind not in ("approved-manufacturer", "approved-distributor", "open-market"):
        raise ValueError(
            "source_kind %r must be approved-manufacturer, approved-distributor or open-market"
            % (source_kind,)
        )
    if not isinstance(traceability_chain, bool):
        raise ValueError("traceability_chain must be a boolean")
    if kind == "open-market":
        return {
            "source_kind": kind,
            "acceptable": False,
            "finding": "open-market supply carries no approved route back to the manufacturer",
        }
    if kind == "approved-distributor" and not traceability_chain:
        return {
            "source_kind": kind,
            "acceptable": False,
            "finding": "approved distributor supplied the lot without an unbroken traceability chain",
        }
    return {"source_kind": kind, "acceptable": True, "finding": None}


def assess_age(date_code, delivery_code, limit_months):
    """Compare the age of the delivered lot with the age limit it carries."""
    if not isinstance(limit_months, (int, float)) or isinstance(limit_months, bool):
        raise ValueError("limit_months must be a real number")
    limit = float(limit_months)
    if not math.isfinite(limit) or limit <= 0.0:
        raise ValueError("limit_months must be positive and finite, got %r" % (limit_months,))
    age = date_code_age_months(date_code, delivery_code)
    within = age < limit or math.isclose(age, limit, rel_tol=0.0, abs_tol=AGE_TOLERANCE_MONTHS)
    return {
        "age_months": age,
        "limit_months": limit,
        "within_limit": within,
        "finding": None
        if within
        else "lot is %.2f months old at delivery, past the %.2f month limit" % (age, limit),
    }


def assess_packaging(carrier, static_protected, moisture_sensitive, dry_packed):
    """Judge the carriage and the barrier the bare chips arrived in."""
    carrier_token = _require_text(carrier, "carrier").replace("_", "-").replace(" ", "-")
    for label, value in (
        ("static_protected", static_protected),
        ("moisture_sensitive", moisture_sensitive),
        ("dry_packed", dry_packed),
    ):
        if not isinstance(value, bool):
            raise ValueError("%s must be a boolean, got %r" % (label, value))
    findings = []
    if carrier_token not in ACCEPTABLE_CARRIERS:
        findings.append(
            "carrier %s does not hold bare chips apart; use %s"
            % (carrier_token, " or ".join(ACCEPTABLE_CARRIERS))
        )
    if not static_protected:
        findings.append("delivery arrived without static protection")
    if moisture_sensitive and not dry_packed:
        findings.append("moisture sensitive elements arrived without a dry pack")
    return {
        "carrier": carrier_token,
        "conforming": not findings,
        "findings": tuple(findings),
        "finding": findings[0] if findings else None,
    }


def assess_documents(declared_documents):
    """Return the baseline delivery documents that did not arrive."""
    if not isinstance(declared_documents, (list, tuple, set, frozenset)):
        raise ValueError("declared_documents must be a sequence of document names")
    declared = set()
    for item in declared_documents:
        declared.add(_require_text(item, "document").replace("_", "-").replace(" ", "-"))
    missing = tuple(sorted(set(REQUIRED_DOCUMENTS) - declared))
    return {
        "missing": missing,
        "complete": not missing,
        "finding": None if not missing else "delivery documents missing: %s" % ", ".join(missing),
    }


def assess_general_provisions(delivery):
    """Grade one passive chip delivery against the baseline conditions.

    delivery keys: source_kind, traceability_chain, lot_size, examined,
    date_code, delivery_code, age_limit_months, carrier, static_protected,
    moisture_sensitive, dry_packed, documents.
    """
    if not isinstance(delivery, dict):
        raise ValueError("delivery must be a mapping")
    for key in ("source_kind", "lot_size", "examined", "date_code", "delivery_code",
                "age_limit_months", "carrier", "static_protected", "moisture_sensitive",
                "dry_packed", "documents"):
        if key not in delivery:
            raise ValueError("delivery missing required key '%s'" % key)
    source = assess_source(delivery["source_kind"], delivery.get("traceability_chain", True))
    examination = assess_examination(delivery["lot_size"], delivery["examined"])
    age = assess_age(delivery["date_code"], delivery["delivery_code"],
                     delivery["age_limit_months"])
    packaging = assess_packaging(delivery["carrier"], delivery["static_protected"],
                                 delivery["moisture_sensitive"], delivery["dry_packed"])
    documents = assess_documents(delivery["documents"])

    findings = []
    disposition = "accept"
    if not source["acceptable"]:
        findings.append(source["finding"])
        disposition = "reject"
    if not packaging["conforming"]:
        findings.extend(packaging["findings"])
        disposition = "reject"
    if not age["within_limit"]:
        findings.append(age["finding"])
        if disposition == "accept":
            disposition = "conditional"
    if not examination["sufficient"]:
        findings.append(examination["finding"])
        if disposition == "accept":
            disposition = "conditional"
    if not documents["complete"]:
        findings.append(documents["finding"])
        if disposition == "accept":
            disposition = "conditional"
    return {
        "source": source,
        "examination": examination,
        "age": age,
        "packaging": packaging,
        "documents": documents,
        "disposition": disposition,
        "findings": tuple(findings),
        "governing_finding": findings[0] if findings else None,
        "acceptable": disposition == "accept",
    }
