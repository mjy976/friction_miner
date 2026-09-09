"""
Shared utility for reading OS-level foreground window info.
Used by multiple collectors (window_collector, interaction_collector, ...).

For SPA web apps (e.g. Google Sheets), the OS-level window title alone
cannot distinguish internal tab navigation, so the title is enriched
with a tab identifier where available (see browser_inspector).
"""

from __future__ import annotations

from typing import Optional, Tuple

import psutil
import win32gui
import win32process

from friction_miner.collector.browser_inspector import get_tab_suffix


def get_foreground_window_info() -> Optional[Tuple[str, str]]:
    """Returns (process_name, window_title) for the current foreground
    window, or None if it cannot be determined.

    The window title may be enriched with an internal-tab suffix for
    supported SPA web apps, so that switching worksheets inside one
    Google Sheet is detected as a real navigation event."""
    hwnd = win32gui.GetForegroundWindow()
    if hwnd == 0:
        return None

    window_title = win32gui.GetWindowText(hwnd)

    try:
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        process = psutil.Process(pid)
        process_name = process.name()
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        process_name = "Unknown"

    suffix = get_tab_suffix(process_name, window_title, hwnd)
    if suffix:
        window_title = f"{window_title}{suffix}"

    return process_name, window_title