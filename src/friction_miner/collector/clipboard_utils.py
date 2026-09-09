"""
Shared utility for reading clipboard metadata (type + length only —
never the actual content). Used by any collector that needs to react
to copy/paste actions.
"""

from __future__ import annotations

import win32clipboard


def get_clipboard_metadata() -> dict:
    """Reads clipboard format/length only — never the actual content."""
    try:
        win32clipboard.OpenClipboard()
        if win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_UNICODETEXT):
            data = win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
            return {"content_type": "text", "content_length": len(data)}
        elif win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_HDROP):
            return {"content_type": "file"}
        elif win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_BITMAP):
            return {"content_type": "image"}
        else:
            return {"content_type": "unknown"}
    except Exception:
        return {"content_type": "unknown"}
    finally:
        try:
            win32clipboard.CloseClipboard()
        except Exception:
            pass