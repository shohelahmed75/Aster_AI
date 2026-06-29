"""
welcome.py — Persistent first-time viewer welcome system.

Tracks which viewers have already been welcomed using a JSON file
so that data survives bot restarts. Also supports seeding from
chat history to avoid re-welcoming people who chatted before the bot started.
"""

import os
import logging

from aster.core.config import WELCOME_MESSAGE, DATA_DIR
from aster.utils.storage import JsonStore

logger = logging.getLogger("aster")


class WelcomeTracker:
    """
    Tracks channel IDs of viewers who have already been welcomed.
    Persists to a JSON file so data survives restarts.
    """

    def __init__(self, chat_id=None):
        """
        Args:
            chat_id: The live chat ID (used to create a stream-specific data file).
                     If None, uses an in-memory-only tracker.
        """
        self._seen = set()
        self._bot_channel_id = None
        self._owner_channel_id = None
        self._store = None

        if chat_id:
            # Create a stream-specific data file
            safe_id = chat_id[:20].replace("/", "_").replace("\\", "_")
            filepath = os.path.join(DATA_DIR, f"welcomed_{safe_id}.json")
            self._store = JsonStore(filepath)
            self._seen = self._store.load_set()
            if self._seen:
                logger.info(f"📂 Loaded {len(self._seen)} previously welcomed viewer(s)")

    def is_new(self, channel_id):
        """
        Check if a viewer is new (hasn't been seen/welcomed before).

        Args:
            channel_id: The YouTube channel ID of the viewer.

        Returns:
            True if this is their first message, False otherwise.
        """
        # Don't welcome the bot itself or the stream owner
        if channel_id in (self._bot_channel_id, self._owner_channel_id):
            return False

        if channel_id in self._seen:
            return False

        self._seen.add(channel_id)
        self._persist()
        return True

    def seed_from_history(self, messages):
        """
        Bulk-add channel IDs from historical messages WITHOUT sending welcomes.
        This prevents re-welcoming people who chatted before the bot started.

        Args:
            messages: List of normalized message dicts from chat.fetch_messages().
        """
        new_ids = 0
        for msg in messages:
            channel_id = msg.get("channel_id", "")
            if channel_id and channel_id not in self._seen:
                self._seen.add(channel_id)
                new_ids += 1

        if new_ids > 0:
            self._persist()
            logger.info(f"📜 Seeded {new_ids} viewer(s) from chat history (won't be re-welcomed)")

    def get_welcome_message(self, display_name):
        """
        Format the welcome message template with the viewer's display name.

        Args:
            display_name: The viewer's display name.

        Returns:
            The formatted welcome message string.
        """
        try:
            return WELCOME_MESSAGE.format(username=display_name)
        except KeyError:
            return f"Welcome to the stream, {display_name}! 🎉"

    @property
    def welcomed_count(self):
        """Number of unique viewers tracked (welcomed + seeded)."""
        return len(self._seen)

    def set_bot_channel_id(self, channel_id):
        """Set the bot's channel ID after authentication."""
        self._bot_channel_id = channel_id
        self._seen.add(channel_id)
        self._persist()

    def set_owner_channel_id(self, channel_id):
        """Set the stream owner's channel ID."""
        self._owner_channel_id = channel_id
        self._seen.add(channel_id)
        self._persist()

    def _persist(self):
        """Save current state to disk if a store is configured."""
        if self._store:
            self._store.save_set(self._seen)
