"""
Windows Active Window Collector — Phase 5 (Level 1 telemetry)

Polls the OS at a fixed interval to detect which window/application is
currently in the foreground. When the foreground window changes, emits
an APP_SWITCH Event with the duration the PREVIOUS window was active.

Privacy note: only captures application name + window title (metadata),
never file/document content, keystrokes, or clipboard contents.
"""

from __future__ import annotations

import time
from datetime import datetime
from typing import Optional, Tuple

import psutil
import win32gui
import win32process

from friction_miner.events.schema import Event, EventType
from friction_miner.storage.db import init_db, save_events

POLL_INTERVAL_SECONDS = 1.0
FLUSH_EVERY_N_EVENTS = 5  # write to DB in small batches, not one-by-one


def _get_foreground_window_info() -> Optional[Tuple[str, str]]:
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


def run_collector() -> None:
    """Main collection loop. Runs until interrupted with Ctrl+C."""
    init_db()

    print("Friction Miner collector started. Press Ctrl+C to stop.\n")

    last_app: Optional[str] = None
    last_title: Optional[str] = None
    last_switch_time: datetime = datetime.now()

    pending_events: list[Event] = []

    try:
        while True:
            info = _get_foreground_window_info()

            if info is not None:
                current_app, current_title = info

                if current_app != last_app or current_title != last_title:
                    now = datetime.now()

                    # Emit an event for the PREVIOUS window, now that we know
                    # how long it was active.
                    if last_app is not None:
                        duration = (now - last_switch_time).total_seconds()
                        event = Event(
                            timestamp=last_switch_time,
                            application=last_app,
                            event_type=EventType.APP_SWITCH,
                            window=last_title,
                            duration=duration,
                        )
                        pending_events.append(event)
                        print(f"{event.timestamp} | {event.application:20s} | {duration:6.1f}s | {event.window}")

                    last_app, last_title = current_app, current_title
                    last_switch_time = now

                    if len(pending_events) >= FLUSH_EVERY_N_EVENTS:
                        save_events(pending_events)
                        pending_events.clear()

            time.sleep(POLL_INTERVAL_SECONDS)

    except KeyboardInterrupt:
        print("\nStopping collector...")

        # Flush the final in-progress window as one last event
        if last_app is not None:
            now = datetime.now()
            duration = (now - last_switch_time).total_seconds()
            pending_events.append(Event(
                timestamp=last_switch_time,
                application=last_app,
                event_type=EventType.APP_SWITCH,
                window=last_title,
                duration=duration,
            ))

        if pending_events:
            save_events(pending_events)

        print("All events saved. Goodbye.")


if __name__ == "__main__":
    run_collector()