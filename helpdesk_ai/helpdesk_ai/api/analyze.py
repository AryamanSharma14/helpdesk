import re
import json
import frappe

TRACEBACK_RE = re.compile(
    r"Traceback \(most recent call last\):(?:.*?\n)+?(\w[\w.]*:\s*[^\n]+)",
    re.DOTALL,
)
EXCEPTION_RE = re.compile(
    r"(?:\w+\.)*\w+:\s*.{5,}",
    re.MULTILINE,
)

KNOWN_ERRORS = {
    "ValidationError": (
        "A field value failed validation — value is missing, wrong format, or violates a constraint.",
        "1. Check all mandatory fields are filled.\n2. Verify data types and formats match field definitions.\n3. Look at the error message for the specific field name.",
    ),
    "MandatoryError": (
        "A required field was left empty when saving the document.",
        "1. Identify which field is mandatory from the error message.\n2. Ensure the field is populated before calling save().",
    ),
    "DoesNotExist": (
        "Code tried to fetch a document that doesn't exist in the database.",
        "1. Verify the document name/ID is correct.\n2. Use frappe.db.exists() to check before fetching.\n3. Handle the DoesNotExist exception gracefully if the record may not always exist.",
    ),
    "PermissionError": (
        "The current user doesn't have permission to perform this action on this doctype.",
        "1. Check the user's roles in User > Role Profile.\n2. Verify DocType permissions under Setup > Role Permissions Manager.\n3. If testing, use Administrator or a role with full access.",
    ),
    "DuplicateEntryError": (
        "A record with the same unique key already exists.",
        "1. Check for an existing record before creating a new one.\n2. Use frappe.db.exists() or handle the exception and update instead of insert.",
    ),
    "LinkValidationError": (
        "A Link field references a document that doesn't exist.",
        "1. Verify the linked document exists.\n2. Check spelling/case of the document name.\n3. Ensure the linked doctype is not filtered out by user permissions.",
    ),
    "TimestampMismatchError": (
        "Document was modified by someone else between when you loaded it and when you saved it.",
        "1. Reload the document and re-apply your changes.\n2. If programmatic, re-fetch the doc before saving: doc.reload() then modify and save.",
    ),
    "AuthenticationError": (
        "The request failed authentication — invalid credentials or session expired.",
        "1. Check API key/secret if using API access.\n2. Verify the session is active.\n3. Ensure the user account is not disabled.",
    ),
    "CSRFTokenError": (
        "CSRF token mismatch — request was rejected as potentially forged.",
        "1. Ensure requests include the X-Frappe-CSRF-Token header.\n2. Fetch a fresh token via /api/method/frappe.auth.get_logged_user.",
    ),
    "KeyError": (
        "Code accessed a dictionary key that doesn't exist.",
        "1. Use dict.get('key') instead of dict['key'] to avoid KeyError.\n2. Add a check: if 'key' in dict before accessing.\n3. Print/log the dict to see what keys are actually present.",
    ),
    "AttributeError": (
        "Code called a method or accessed an attribute on None or an unexpected object type.",
        "1. Add a null check before using the value (if obj is not None).\n2. Verify the variable is being assigned correctly earlier in the flow.\n3. Check if a frappe.get_doc() or similar call returned None.",
    ),
    "TypeError": (
        "A function received an argument of the wrong type.",
        "1. Check what types the function expects vs what is being passed.\n2. Look for None being passed where a string/int is expected.\n3. Verify data coming from request args or form fields is cast correctly.",
    ),
    "ImportError": (
        "A Python module or name could not be imported.",
        "1. Verify the module is installed in the bench environment.\n2. Check for typos in the import path.\n3. Run: bench pip install <package> if missing.",
    ),
    "IndexError": (
        "Code accessed a list index that is out of range.",
        "1. Check if the list is empty before accessing by index.\n2. Use len(list) > 0 or list[0] if list else default.\n3. Verify the expected number of results is actually being returned.",
    ),
}

UNKNOWN_ROOT_CAUSE = "Exception type not in known patterns."
UNKNOWN_FIX = (
    "1. Open Frappe Desk → Error Log → find this error for full context.\n"
    "2. Search the exception name in frappe/apps source code.\n"
    "3. Check the error message for field names or document names that can narrow down the cause."
)


@frappe.whitelist()
def run(ticket_name):
    ticket = frappe.get_doc("HD Ticket", ticket_name)

    parts = [frappe.utils.strip_html(ticket.description or "")]
    for c in frappe.get_all(
        "HD Ticket Comment",
        filters={"reference_ticket": ticket_name},
        fields=["content"],
    ):
        parts.append(frappe.utils.strip_html(c.content or ""))
    text = "\n\n".join(filter(None, parts))

    extraction = _extract(text)
    if not extraction:
        return {"found": False}

    exc_class = _parse_exception_class(extraction["content"])
    known = exc_class in KNOWN_ERRORS
    root_cause, fix = KNOWN_ERRORS.get(exc_class, (UNKNOWN_ROOT_CAUSE, UNKNOWN_FIX))

    return {
        "found": True,
        "partial": extraction["type"] == "partial",
        "exception_class": exc_class,
        "traceback": extraction["content"],
        "root_cause": root_cause,
        "fix": fix,
        "known": known,
    }


def _extract(text):
    # Pass 1: Frappe JSON error response {"exc_type": ..., "exc": ...}
    try:
        data = json.loads(text.strip())
        if isinstance(data, dict) and "exc" in data:
            return {"type": "full", "content": data["exc"]}
    except (json.JSONDecodeError, TypeError, ValueError):
        pass

    # Pass 2: standard Python traceback
    m = TRACEBACK_RE.search(text)
    if m:
        return {"type": "full", "content": m.group(0)}

    # Pass 3: exception line only (partial paste)
    m = EXCEPTION_RE.search(text)
    if m:
        return {"type": "partial", "content": m.group(0)}

    return None


def _parse_exception_class(traceback_text):
    last_line = traceback_text.strip().split("\n")[-1]
    exc_part = last_line.split(":")[0].strip()
    return exc_part.split(".")[-1]
