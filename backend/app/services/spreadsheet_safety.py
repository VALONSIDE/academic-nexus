"""Small safeguards for values written into downloadable spreadsheets."""

_FORMULA_PREFIXES = frozenset({"=", "+", "-", "@"})


def safe_spreadsheet_text(value: str) -> str:
    """Force untrusted text to remain text in Excel-compatible viewers.

    Prefixing with an apostrophe prevents formula interpretation while keeping
    the visible cell content unchanged for recipients.
    """
    return f"'{value}" if value.lstrip().startswith(tuple(_FORMULA_PREFIXES)) else value
