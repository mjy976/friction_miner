"""
Copy/Paste Interaction Collector — Phase 5, Level 2 telemetry (increment 1)

Detects real COPY (Ctrl+C) and PASTE (Ctrl+V) actions system-wide, and
pairs them with whatever application/window was in focus at that moment.

Privacy design:
- Never logs individual keystrokes. Only reacts to the exact Ctrl+C /
  Ctrl+V combination.
- Reads the clipboard ONLY to determine its type and length (for text) —
  the actual content is discarded immediately, never stored or printed.
"""

from __future__ import annotations
import threading
import time
from datetime import datetime

import win32clipboard
from pynput import keyboard

from friction_miner.collector.window_utils import get_foreground_window_info
from friction_miner.events.schema import Event, EventType
from friction_miner.storage.db import init_db, save_events

FLUSH_EVERY_N_EVENTS = 5
CLIPBOARD_READ_DELAY_SECONDS = 0.15  # let the source app finish writing to clipboard


def _get_clipboard_metadata() -> dict:
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


class CopyPasteCollector:
    def __init__(self) -> None:
        self._ctrl_pressed = False
        self._pending_events: list[Event] = []
        self._active_keys: set[str] = set()
        self._lock = threading.Lock()  # protects _pending_events across threads

    def _emit(self, event_type: EventType) -> None:
        # Capture timestamp/app/window IMMEDIATELY (accurate at press-time),
        # but defer the clipboard READ slightly so the source app has time
        # to actually finish writing to the clipboard.
        info = get_foreground_window_info()
        app_name, window_title = info if info else ("Unknown", None)
        timestamp = datetime.now()

        def _finish_emit() -> None:
            event = Event(
                timestamp=timestamp,
                application=app_name,
                event_type=event_type,
                window=window_title,
                metadata=_get_clipboard_metadata(),
            )
            print(f"{event.timestamp} | {event.application:15s} | {event.event_type.value:5s} | {event.metadata}")

            with self._lock:
                self._pending_events.append(event)
                if len(self._pending_events) >= FLUSH_EVERY_N_EVENTS:
                    save_events(self._pending_events)
                    self._pending_events.clear()

        threading.Timer(CLIPBOARD_READ_DELAY_SECONDS, _finish_emit).start()

    @staticmethod
    def _normalize_char(key) -> str | None:
        try:
            raw = key.char
        except AttributeError:
            return None

        if raw is None:
            return None

        code = ord(raw)
        if 1 <= code <= 26:
            return chr(code + 96)

        return raw.lower()

    def on_press(self, key) -> None:
        if key in (keyboard.Key.ctrl_l, keyboard.Key.ctrl_r):
            self._ctrl_pressed = True
            return

        if not self._ctrl_pressed:
            return

        char = self._normalize_char(key)
        if char is None:
            return

        if char in self._active_keys:
            return

        self._active_keys.add(char)

        if char == "c":
            self._emit(EventType.COPY)
        elif char == "v":
            self._emit(EventType.PASTE)

    def on_release(self, key) -> None:
        if key in (keyboard.Key.ctrl_l, keyboard.Key.ctrl_r):
            self._ctrl_pressed = False
            return

        char = self._normalize_char(key)
        if char is not None:
            self._active_keys.discard(char)

    def flush(self) -> None:
        with self._lock:
            if self._pending_events:
                save_events(self._pending_events)
                self._pending_events.clear()


def run_collector() -> None:
    init_db()
    collector = CopyPasteCollector()

    print("Copy/Paste collector started.")
    print("Try selecting some text anywhere and pressing Ctrl+C, then Ctrl+V somewhere else.")
    print("Press Ctrl+C in THIS terminal window to stop.\n")

    listener = keyboard.Listener(on_press=collector.on_press, on_release=collector.on_release)
    listener.start()

    try:
        while listener.running:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping collector...")
    finally:
        listener.stop()
        collector.flush()
        print("All events saved. Goodbye.")


if __name__ == "__main__":
    run_collector()