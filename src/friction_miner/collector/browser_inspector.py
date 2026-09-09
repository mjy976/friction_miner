"""
Browser internal-tab inspector — Phase 5 extension.

Some web apps are Single Page Applications (SPAs): switching between
internal tabs (e.g. worksheets inside one Google Sheet) does NOT
change the OS-level window title, so WindowWatcher alone is blind to
this kind of navigation.

PRIVACY-CRITICAL DESIGN:
UI Automation exposes accessible controls for BOTH the browser chrome
(address bar, toolbar) AND the actual page content — every
spreadsheet cell in Google Sheets is exposed as an "Edit" control too.
To guarantee cell content is NEVER read:

  1. Every candidate control's on-screen POSITION is checked first
     (BoundingRectangle) — reading a position never reveals any text.
  2. Only controls within the toolbar area (near the top of the
     window) are considered eligible.
  3. The actual text (window_text) is read ONLY on those already
     position-filtered toolbar controls. Content below the toolbar
     boundary is never touched at all.

This ordering — position check BEFORE content read — is what
enforces privacy here, not a filter applied after the fact.
"""

from __future__ import annotations

import re
from typing import Optional
from urllib.parse import urlparse

from pywinauto import Desktop

_GOOGLE_SHEETS_GID_RE = re.compile(r"gid=(\d+)")
_RELEVANT_TITLE_HINTS = ("Google Sheets",)

# Controls positioned below this (pixels from the window's top edge)
# are considered page content, not browser toolbar, and their text is
# never read. Calibrated from observed Chrome layout: address bar sits
# at ~59px, page content controls (formula bar, name box) at ~210px.
_TOOLBAR_MAX_RELATIVE_TOP = 150


def _find_address_bar_url(hwnd: int) -> Optional[str]:
    """Finds the Chrome address bar's current URL — without ever
    reading the text of any control outside the toolbar area."""
    try:
        window = Desktop(backend="uia").window(handle=hwnd)
        window_rect = window.rectangle()
        candidates = window.descendants(control_type="Edit")
    except Exception:
        return None

    for ctrl in candidates:
        try:
            rect = ctrl.rectangle()
        except Exception:
            continue

        relative_top = rect.top - window_rect.top
        if relative_top > _TOOLBAR_MAX_RELATIVE_TOP:
            continue  # page content area — text is never read

        try:
            text = ctrl.window_text()
        except Exception:
            continue

        if text.startswith("http") or "docs.google.com" in text:
            return text

    return None


def _normalize_url(raw: str) -> str:
    """Chrome hides the scheme in the address bar display, which makes
    urlparse treat the string as a relative path (empty netloc).
    Prepend a scheme so host/path parsing works as expected."""
    if "://" not in raw:
        return f"https://{raw}"
    return raw


def get_tab_suffix(process_name: str, window_title: str, hwnd: int) -> Optional[str]:
    """Returns a short suffix like ' [sheet_tab:123456]' identifying
    the active Google Sheets worksheet tab, or None if not applicable."""
    if process_name != "chrome.exe":
        return None
    if not any(hint in window_title for hint in _RELEVANT_TITLE_HINTS):
        return None

    raw_url = _find_address_bar_url(hwnd)
    if not raw_url:
        return None

    parsed = urlparse(_normalize_url(raw_url))
    if "docs.google.com" in parsed.netloc and "/spreadsheets/" in parsed.path:
        match = _GOOGLE_SHEETS_GID_RE.search(raw_url)
        if match:
            return f" [sheet_tab:{match.group(1)}]"

    return None