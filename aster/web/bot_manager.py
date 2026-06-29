"""
bot_manager.py — Thread-based bot lifecycle manager.

Provides a singleton BotManager that:
  - Starts/stops the StrykerBot in a background daemon thread
  - Captures log output into a ring buffer for SSE streaming
  - Exposes status info (running, uptime, video_id)
"""

import time
import logging
import threading
import collections
from datetime import datetime

logger = logging.getLogger("aster")


class BufferedLogHandler(logging.Handler):
    """
    Custom logging handler that stores log records in a ring buffer.
    Used to stream logs to the web dashboard via SSE.
    """

    def __init__(self, max_lines=500):
        super().__init__()
        self._buffer = collections.deque(maxlen=max_lines)
        self._listeners = []
        self._lock = threading.Lock()

    def emit(self, record):
        try:
            timestamp = datetime.fromtimestamp(record.created).strftime("%H:%M:%S")
            level = record.levelname
            message = record.getMessage()
            entry = {"time": timestamp, "level": level, "message": message}

            with self._lock:
                self._buffer.append(entry)
                for listener in self._listeners:
                    try:
                        listener(entry)
                    except Exception:
                        pass
        except Exception:
            self.handleError(record)

    def get_history(self):
        """Return all buffered log entries."""
        with self._lock:
            return list(self._buffer)

    def add_listener(self, callback):
        """Add a callback that receives new log entries."""
        with self._lock:
            self._listeners.append(callback)

    def remove_listener(self, callback):
        """Remove a listener callback."""
        with self._lock:
            if callback in self._listeners:
                self._listeners.remove(callback)

    def clear(self):
        """Clear the log buffer."""
        with self._lock:
            self._buffer.clear()


class BotManager:
    """
    Singleton manager for the StrykerBot lifecycle.
    Handles starting/stopping the bot in a background thread.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        self._thread = None
        self._bot = None
        self._running = False
        self._start_time = None
        self._error = None
        self.log_handler = BufferedLogHandler()

        # Attach our handler to the aster logger
        aster_logger = logging.getLogger("aster")
        # Prevent duplicate handlers
        for h in aster_logger.handlers[:]:
            if isinstance(h, BufferedLogHandler):
                aster_logger.removeHandler(h)
        aster_logger.addHandler(self.log_handler)

    def start(self):
        """Start the bot in a background thread."""
        if self._running:
            return {"success": False, "error": "Bot is already running"}

        self._error = None
        self.log_handler.clear()

        def _run_bot():
            try:
                from aster.core.auth import get_authenticated_service
                from aster.core.config import VIDEO_ID
                from aster.bot import AsterBot

                # Force reload config module to pick up changes
                import importlib
                import aster.core.config as cfg_module
                importlib.reload(cfg_module)
                from aster.core.config import VIDEO_ID as fresh_video_id

                logger.info("🔐 Authenticating with YouTube Data API...")
                youtube = get_authenticated_service()
                logger.info("✅ Authentication successful!\n")

                self._bot = AsterBot(youtube, fresh_video_id)
                self._running = True
                self._start_time = time.time()
                self._bot.start()
            except Exception as e:
                self._error = str(e)
                logger.error(f"❌ Bot error: {e}")
            finally:
                self._running = False
                self._bot = None
                self._start_time = None

        self._thread = threading.Thread(target=_run_bot, daemon=True)
        self._thread.start()

        # Give the thread a moment to start
        time.sleep(0.5)
        return {"success": True}

    def stop(self):
        """Stop the bot gracefully."""
        if not self._running or not self._bot:
            return {"success": False, "error": "Bot is not running"}

        self._bot.stop()
        self._running = False

        # Wait for thread to finish (max 5 seconds)
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)

        return {"success": True}

    def status(self):
        """Return the current bot status."""
        uptime = None
        if self._start_time and self._running:
            uptime = int(time.time() - self._start_time)

        video_id = None
        welcomed = 0
        if self._bot:
            video_id = self._bot.video_id
            if self._bot.welcome_tracker:
                welcomed = self._bot.welcome_tracker.welcomed_count

        return {
            "running": self._running,
            "uptime": uptime,
            "video_id": video_id,
            "welcomed_count": welcomed,
            "error": self._error,
        }
