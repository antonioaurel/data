#!/usr/bin/env python3
"""Advisory sync check between the UI code and the component matrices.

Compares the testable elements in the two pages against the identification
matrix in Skills/COMPONENT-MATRICES.md, and reports:

  • drift  — testable elements in the code that the doc doesn't mention
  • stale  — id-like selectors the doc lists that no longer exist in the code

Report-only by default (exit 0). Pass --strict to exit 1 on drift — used by
CI or a stricter hook. The /sync-matrices skill runs this to get its worklist;
the pre-commit hook BLOCKS on change-detection, and prints this as guidance.

    python scripts/check_matrices.py [--strict]
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

PROJ = Path(__file__).resolve().parent.parent
DOC = PROJ / "Skills" / "COMPONENT-MATRICES.md"
PAGES = [PROJ / "app" / "index.html", PROJ / "reports" / "index.html"]

# Only these carry test/selector weight; structural divs/sections are ignored
# on purpose so the check stays low-noise.
TESTABLE_TAGS = ("input", "button", "select", "textarea", "svg")
ACTION_ATTRS = ("data-f", "data-reg", "data-del")
CLASSES = ("chip", "effect-row")


def tokens_from_html(text: str) -> set[str]:
    toks: set[str] = set()
    for m in re.finditer(r"<(\w+)([^>]*?)/?>", text):
        tag, attrs = m.group(1).lower(), m.group(2)
        has_action = any(a in attrs for a in ACTION_ATTRS)
        cls = re.search(r'class="([^"]*)"', attrs)
        classes = cls.group(1).split() if cls else []
        interesting = (
            tag in TESTABLE_TAGS
            or has_action
            or any(c in CLASSES for c in classes)
        )
        if not interesting:
            continue
        idm = re.search(r'\bid="([^"]+)"', attrs)
        if idm:
            toks.add(idm.group(1))
        for a in ACTION_ATTRS:
            if a in attrs:
                toks.add(a)
        for c in classes:
            if c in CLASSES:
                toks.add(c)
        if tag == "input" and 'type="radio"' in attrs:
            nm = re.search(r'\bname="([^"]+)"', attrs)
            if nm:
                toks.add("name=" + nm.group(1))
    # class assigned in JS (row.className = "efeito-row") — raw substring pass
    for c in CLASSES:
        if f'"{c}"' in text:
            toks.add(c)
    return toks


def doc_id_tokens(doc: str) -> set[str]:
    """DOM ids the identification matrix claims exist.

    Scoped to rows that carry an `eve-` testid (the identification tables), and
    to simple id-like tokens — so vocabulary codes (APP-EVT, C-BTN) and complex
    selectors ([data-go], .chip) don't masquerade as stale ids.
    """
    ids: set[str] = set()
    for line in doc.splitlines():
        if "eve-" not in line:
            continue
        for m in re.finditer(r"`([^`]+)`", line):
            t = m.group(1)
            if not t.startswith("eve-") and re.fullmatch(r"[a-z][A-Za-z0-9]+", t):
                ids.add(t)
    return ids


def main() -> int:
    strict = "--strict" in sys.argv[1:]
    if not DOC.exists():
        print(f"FAIL  matrices doc not found: {DOC.relative_to(PROJ)}")
        return 1

    doc = DOC.read_text(encoding="utf-8")
    code_tokens: set[str] = set()
    for page in PAGES:
        code_tokens |= tokens_from_html(page.read_text(encoding="utf-8"))

    drift = sorted(t for t in code_tokens if t not in doc)
    doc_ids = doc_id_tokens(doc)
    code_blob = "\n".join(p.read_text(encoding="utf-8") for p in PAGES)
    stale = sorted(t for t in doc_ids if t not in code_blob)

    if not drift and not stale:
        print("OK  matrices are in sync with the UI code.")
        return 0

    if drift:
        print("DRIFT — testable elements in code, missing from the matrices:")
        for t in drift:
            print(f"  + {t}")
    if stale:
        print("STALE — selectors in the matrices, not found in code:")
        for t in stale:
            print(f"  - {t}")
    print("\nRun  /sync-matrices  to reconcile, or edit "
          f"{DOC.relative_to(PROJ)} by hand.")
    return 1 if (strict and drift) else 0


if __name__ == "__main__":
    raise SystemExit(main())
