"""
Unified Activity Collector — Phase 5 (+ session tracking)

Two ways to stop this process, both supported at once:
  1. Ctrl+C in the terminal (manual/standalone use — unchanged).
  2. A stop-file appearing on disk (checked once per second) — this is
     how the FastAPI backend stops a collector it started on the
     person's behalf from the dashboard's "Stop observing" button.

Usage:
    python -m friction_miner.collector.main_collector [session_id] [stop_file_path]

Both arguments are optional — running with no arguments behaves
exactly as before (a random session_id, Ctrl+C to stop).
"""

from __future__ import annotations

import sys
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from pynput import keyboard

from friction_miner.collector.clipboard_utils import get_clipboard_metadata
from friction_miner.collector.window_utils import get_foreground_window_info
from friction_miner.events.schema import Event, EventType
from friction_miner.storage.db import init_db, save_events

POLL_INTERVAL_SECONDS = 1.0
FLUSH_EVERY_N_EVENTS = 5
CLIPBOARD_READ_DELAY_SECONDS = 0.15
DEFAULT_STOP_FILE = Path("data/.collector_stop_signal")


class EventBuffer:
    def __init__(self, session_id: str, flush_threshold: int = FLUSH_EVERY_N_EVENTS) -> None:
        self._session_id = session_id
        self._lock = threading.Lock()
        self._pending: list[Event] = []
        self._flush_threshold = flush_threshold
        self.total_saved = 0

    def add(self, event: Event) -> None:
        event.session_id = self._session_id
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
            self.total_saved += len(self._pending)
            self._pending.clear()


class WindowWatcher:
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


def run_collector(session_id: str, stop_file: Path) -> None:
    init_db()
    buffer = EventBuffer(session_id)

    window_watcher = WindowWatcher(buffer)
    copy_paste_watcher = CopyPasteWatcher(buffer)

    window_thread = threading.Thread(target=window_watcher.run, daemon=True)

    print(f"Friction Miner collector started. session_id={session_id}")
    print(f"Stop with Ctrl+C, or by creating: {stop_file}\n")

    window_thread.start()
    copy_paste_watcher.start()

    try:
        while True:
            if stop_file.exists():
                print("\nStop signal detected...")
                break
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping collector (Ctrl+C)...")
    finally:
        window_watcher.stop()
        copy_paste_watcher.stop()
        buffer.flush()
        if stop_file.exists():
            stop_file.unlink()
        print(f"All events saved ({buffer.total_saved} total this session). Goodbye.")


if __name__ == "__main__":
    arg_session_id = sys.argv[1] if len(sys.argv) > 1 else str(uuid.uuid4())
    arg_stop_file = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_STOP_FILE
    run_collector(arg_session_id, arg_stop_file)