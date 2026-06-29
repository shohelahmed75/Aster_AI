"""
commands.py — Slash command parser, router, and cooldown manager.

Loads command definitions from commands.json, matches incoming chat messages
against known commands and aliases, and enforces per-command cooldowns.
"""

import json
import time
import logging
import os

from aster.core.config import COMMANDS_FILE, BOT_PREFIX, COOLDOWN_SECONDS

logger = logging.getLogger("aster")


class CommandRouter:
    """
    Loads commands from JSON, matches messages, and enforces cooldowns.
    """

    def __init__(self, commands_file=None, prefix=None, cooldown_seconds=None):
        """
        Args:
            commands_file: Path to the commands JSON file.
            prefix: Command prefix (e.g., "/").
            cooldown_seconds: Seconds between repeated uses of the same command.
        """
        self._commands_file = commands_file or COMMANDS_FILE
        self._prefix = prefix or BOT_PREFIX
        self._cooldown_seconds = cooldown_seconds if cooldown_seconds is not None else COOLDOWN_SECONDS
        self._lookup = {}
        self._cooldowns = {}  # {command_key: last_used_timestamp}

        self.reload()

    def reload(self):
        """Reload commands from the JSON file."""
        self._lookup = _load_commands(self._commands_file)
        logger.info(f"Loaded {self.command_count} commands ({self.trigger_count} triggers)")

    def match(self, text):
        """
        Check if a chat message matches a known command.

        Returns the reply string if matched and not on cooldown,
        or None if no match or on cooldown.
        """
        text_clean = text.strip().lower()

        if not text_clean.startswith(self._prefix):
            return None

        # Extract the command word (first word)
        command_word = text_clean.split()[0] if text_clean.split() else ""
        reply = self._lookup.get(command_word)

        if reply is None:
            return None

        # Check cooldown
        if self._is_on_cooldown(command_word):
            logger.debug(f"Command '{command_word}' on cooldown, skipping")
            return None

        # Record usage time
        self._cooldowns[command_word] = time.time()
        return reply

    def _is_on_cooldown(self, command_key):
        """Check if a command was used within the cooldown window."""
        last_used = self._cooldowns.get(command_key)
        if last_used is None:
            return False
        return (time.time() - last_used) < self._cooldown_seconds

    @property
    def trigger_count(self):
        """Total number of triggers (actions + aliases)."""
        return len(self._lookup)

    @property
    def command_count(self):
        """Number of unique replies (de-duplicated)."""
        return len(set(id(v) for v in self._lookup.values())) if self._lookup else 0


def _load_commands(filepath):
    """
    Load command definitions from a JSON file.

    Returns a dict mapping every trigger (action + aliases) to its reply.
    """
    if not os.path.exists(filepath):
        logger.warning(f"⚠️  Commands file '{filepath}' not found. No commands loaded.")
        return {}

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            commands_data = json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"❌ Invalid JSON in '{filepath}': {e}")
        return {}

    lookup = {}
    for cmd in commands_data:
        reply = cmd.get("reply", "")
        action = cmd.get("action", "").lower().strip()
        aliases = cmd.get("aliases", [])

        if action:
            lookup[action] = reply

        for alias in aliases:
            alias_lower = alias.lower().strip()
            if alias_lower:
                lookup[alias_lower] = reply

    return lookup
