"""
storage.py — JSON file persistence helper.

Provides a simple key-value store backed by a JSON file
for persisting data like welcomed viewer IDs across bot restarts.
"""

import json
import os
import logging

logger = logging.getLogger("aster")


class JsonStore:
    """
    A simple persistent store backed by a JSON file.
    Supports dict-like data with load/save operations.
    """

    def __init__(self, filepath):
        """
        Args:
            filepath: Path to the JSON file for storage.
        """
        self.filepath = filepath
        self._ensure_dir()

    def _ensure_dir(self):
        """Create the parent directory if it doesn't exist."""
        directory = os.path.dirname(self.filepath)
        if directory:
            os.makedirs(directory, exist_ok=True)

    def load(self, default=None):
        """
        Load data from the JSON file.

        Args:
            default: Default value if file doesn't exist. Defaults to empty dict.

        Returns:
            The loaded data (dict, list, etc).
        """
        if default is None:
            default = {}

        if not os.path.exists(self.filepath):
            return default

        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"⚠️  Could not load {self.filepath}: {e}")
            return default

    def save(self, data):
        """
        Save data to the JSON file.

        Args:
            data: The data to persist (must be JSON-serializable).
        """
        try:
            self._ensure_dir()
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except IOError as e:
            logger.error(f"❌ Could not save to {self.filepath}: {e}")

    def load_set(self) -> set:
        """Load a JSON array as a Python set."""
        data = self.load(default=[])
        return set(data)

    def save_set(self, data: set):
        """Save a Python set as a JSON array."""
        self.save(sorted(list(data)))
