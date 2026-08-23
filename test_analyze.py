"""
Quick standalone test — no Frappe needed.
Run: python test_analyze.py
"""
import re, json

TRACEBACK_RE = re.compile(
    r"Traceback \(most recent call last\):(?:.*?\n)+?(\w[\w.]*:\s*[^\n]+)",
    re.DOTALL,
)
EXCEPTION_RE = re.compile(r"(?:\w+\.)*\w+:\s*.{5,}", re.MULTILINE)

KNOWN_ERRORS = {
    "ValidationError": ("Field validation failed.", "1. Check mandatory fields.\n2. Verify data types."),
    "DoesNotExist": ("Record not found in DB.", "1. Verify document name.\n2. Use frappe.db.exists() first."),
    "MandatoryError": ("Required field empty.", "1. Fill all mandatory fields before save."),
    "KeyError": ("Dict key missing.", "1. Use dict.get('key') instead of dict['key']."),
}

def _extract(text):
    try:
        data = json.loads(text.strip())
        if isinstance(data, dict) and "exc" in data:
            return {"type": "full", "content": data["exc"]}
    except Exception:
        pass
    m = TRACEBACK_RE.search(text)
    if m:
        return {"type": "full", "content": m.group(0)}
    m = EXCEPTION_RE.search(text)
    if m:
        return {"type": "partial", "content": m.group(0)}
    return None

def _parse_exception_class(traceback_text):
    last_line = traceback_text.strip().split("\n")[-1]
    exc_part = last_line.split(":")[0].strip()
    return exc_part.split(".")[-1]

# --- tests ---

FULL_TB = """
Some ticket text here.

Traceback (most recent call last):
  File "apps/frappe/frappe/model/document.py", line 847, in save
    self._validate()
  File "apps/frappe/frappe/model/document.py", line 231, in _validate
    self.validate_mandatory()
frappe.exceptions.MandatoryError: customer: Value missing for customer
"""

JSON_TB = json.dumps({
    "exc_type": "ValidationError",
    "exception": "frappe.exceptions.ValidationError: bad value",
    "exc": "Traceback (most recent call last):\n  File \"apps/frappe/frappe/model/document.py\", line 100, in save\n    self._validate()\nfrappe.exceptions.ValidationError: bad value",
})

PARTIAL = "frappe.exceptions.DoesNotExist: HD Ticket not found for name HD-0001"

EMPTY = "No error here, just a normal message from customer."

cases = [
    ("Full traceback", FULL_TB),
    ("JSON error response", JSON_TB),
    ("Partial (exception line only)", PARTIAL),
    ("No traceback", EMPTY),
]

for name, text in cases:
    extraction = _extract(text)
    if not extraction:
        print(f"[{name}] -> NOT FOUND")
        continue
    exc_class = _parse_exception_class(extraction["content"])
    known = exc_class in KNOWN_ERRORS
    root_cause, fix = KNOWN_ERRORS.get(exc_class, ("Unknown exception.", "Check Error Log."))
    print(f"[{name}]")
    print(f"  type={extraction['type']}  exception={exc_class}  known={known}")
    print(f"  root_cause: {root_cause}")
    print(f"  fix: {fix[:60]}...")
    print()
