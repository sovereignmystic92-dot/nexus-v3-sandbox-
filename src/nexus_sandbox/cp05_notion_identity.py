"""Strict Notion source URL identity for CP05 read-only reconciliation.

Ignore display-only query parameters, but reject host/path substitution.
No provider calls or mutation capabilities.
"""
from urllib.parse import urlsplit

def notion_page_matches(display_url: str, expected_page_id: str) -> bool:
    if type(display_url) is not str or type(expected_page_id) is not str:
        return False
    if len(expected_page_id) != 32 or any(c not in "0123456789abcdef" for c in expected_page_id):
        return False
    try:
        parsed = urlsplit(display_url)
        return (
            parsed.scheme == "https"
            and parsed.netloc == "app.notion.com"
            and parsed.path == "/p/" + expected_page_id
            and not parsed.username
            and not parsed.password
            and not parsed.fragment
        )
    except ValueError:
        return False
