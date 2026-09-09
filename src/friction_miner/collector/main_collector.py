"""
Unified Activity Collector — Phase 5 (Level 1 + Level 2 telemetry)

Runs BOTH collectors concurrently in a single process, sharing one
timeline and one thread-safe write buffer:

  - WindowWatcher      -> APP_SWITCH events (foreground window polling)
  - CopyPasteWatcher   -> COPY / PASTE events (global keyboard hook)

Both feed into a single EventBuffer, which serializes all SQLite
writes behind one lock — this avoids "database is locked" errors
that could occur if two threads wrote at the exact same time.
"""

from __future__ import annotations

import threading
import time
from datetime import datetime
from typing import Optional

from pynput import keyboard

from friction_miner.collector.clipboard_utils import get_clipboard_metadata
from friction_miner.collector.window_utils import get_foreground_window_info
from friction_miner.events.schema import Event, EventType
from friction_miner.storage.db import init_db, save_events

POLL_INTERVAL_SECONDS = 1.0
FLUSH_EVERY_N_EVENTS = 5
CLIPBOARD_READ_DELAY_SECONDS = 0.15


class EventBuffer:
    """Thread-safe buffer shared across collectors. Guarantees only one
    thread writes to SQLite at a time, and events from different
    sources flush together on one consistent schedule."""

    def __init__(self, flush_threshold: int = FLUSH_EVERY_N_EVENTS) -> None:
        self._lock = threading.Lock()
        self._pending: list[Event] = []
        self._flush_threshold = flush_threshold

    def add(self, event: Event) -> None:
        with self._lock:
            self._pending.append(event)
            if len(self._pending) >= self._flush_threshold:
                self._flush_locked()

    def flush(self) -> None:
        with self._lock:
            self._flush_locked()

    def _flush_locked(self) -> None:
        if self._pending:
            save_events(self._pending)
            self._pending.clear()


class WindowWatcher:
    """Polls the foreground window and emits APP_SWITCH events on change."""

    def __init__(self, buffer: EventBuffer) -> None:
        self._buffer = buffer
        self._stop_flag = threading.Event()
        self._last_app: Optional[str] = None
        self._last_title: Optional[str] = None
        self._last_switch_time: datetime = datetime.now()

    def run(self) -> None:
        while not self._stop_flag.is_set():
            info = get_foreground_window_info()

            if info is not None:
                current_app, current_title = info

                if current_app != self._last_app or current_title != self._last_title:
                    now = datetime.now()

                    if self._last_app is not None:
                        duration = (now - self._last_switch_time).total_seconds()
                        event = Event(
                            timestamp=self._last_switch_time,
                            application=self._last_app,
                            event_type=EventType.APP_SWITCH,
                            window=self._last_title,
                            duration=duration,
                        )
                        self._buffer.add(event)
                        print(f"{event.timestamp} | {event.application:20s} | APP_SWITCH | {duration:6.1f}s | {event.window}")

                    self._last_app, self._last_title = current_app, current_title
                    self._last_switch_time = now

            time.sleep(POLL_INTERVAL_SECONDS)

    def stop(self) -> None:
        self._stop_flag.set()
        if self._last_app is not None:
            now = datetime.now()
            duration = (now - self._last_switch_time).total_seconds()
            self._buffer.add(Event(
                timestamp=self._last_switch_time,
                application=self._last_app,
                event_type=EventType.APP_SWITCH,
                window=self._last_title,
                duration=duration,
            ))


class CopyPasteWatcher:
    """Listens system-wide for Ctrl+C / Ctrl+V and emits COPY/PASTE events."""

    def __init__(self, buffer: EventBuffer) -> None:
        self._buffer = buffer
        self._ctrl_pressed = False
        self._active_keys: set[str] = set()
        self._listener: Optional[keyboard.Listener] = None

    def start(self) -> None:
        self._listener = keyboard.Listener(on_press=self._on_press, on_release=self._on_release)
        self._listener.start()

    def stop(self) -> None:
        if self._listener is not None:
            self._listener.stop()

    @staticmethod
    def _normalize_char(key) -> Optional[str]:
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

    def _emit(self, event_type: EventType) -> None:
        info = get_foreground_window_info()
        app_name, window_title = info if info else ("Unknown", None)
        timestamp = datetime.now()

        def _finish_emit() -> None:
            event = Event(
                timestamp=timestamp,
                application=app_name,
                event_type=event_type,
                window=window_title,
                metadata=get_clipboard_metadata(),
            )
            print(f"{event.timestamp} | {event.application:20s} | {event.event_type.value:9s} | {event.metadata}")
            self._buffer.add(event)

        threading.Timer(CLIPBOARD_READ_DELAY_SECONDS, _finish_emit).start()

    def _on_press(self, key) -> None:
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

    def _on_release(self, key) -> None:
        if key in (keyboard.Key.ctrl_l, keyboard.Key.ctrl_r):
            self._ctrl_pressed = False
            return
        char = self._normalize_char(key)
        if char is not None:
            self._active_keys.discard(char)


def run_collector() -> None:
    init_db()
    buffer = EventBuffer()

    window_watcher = WindowWatcher(buffer)
    copy_paste_watcher = CopyPasteWatcher(buffer)

    window_thread = threading.Thread(target=window_watcher.run, daemon=True)

    print("Friction Miner unified collector started. Press Ctrl+C to stop.\n")

    window_thread.start()
    copy_paste_watcher.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping collector...")
        window_watcher.stop()
        copy_paste_watcher.stop()
        buffer.flush()
        print("All events saved. Goodbye.")


if __name__ == "__main__":
    run_collector()