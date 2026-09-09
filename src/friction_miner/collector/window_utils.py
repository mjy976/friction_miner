"""
Shared utility for reading OS-level foreground window info.
Used by multiple collectors (window_collector, interaction_collector, ...).
"""

from __future__ import annotations

from typing import Optional, Tuple

import psutil
import win32gui
import win32process


def get_foreground_window_info() -> Optional[Tuple[str, str]]:
    """Returns (process_name, window_title) for the current foreground window,
    or None if it cannot be determined (e.g. no window focused)."""
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

    return process_name, window_title