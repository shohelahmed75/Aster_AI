"""
logger.py — Colored console logging setup for Stryker Bot.

Provides a setup function that configures:
  - Color-coded console output (INFO=green, WARN=yellow, ERROR=red)
  - Optional file logging to data/bot.log
  - Default level: INFO (use --verbose for DEBUG)
"""

import sys
import logging
from colorama import init as colorama_init, Fore, Style


class ColoredFormatter(logging.Formatter):
    """Custom formatter with ANSI color codes per log level."""

    COLORS = {
        logging.DEBUG: Fore.CYAN,
        logging.INFO: Fore.GREEN,
        logging.WARNING: Fore.YELLOW,
        logging.ERROR: Fore.RED,
        logging.CRITICAL: Fore.RED + Style.BRIGHT,
    }

    def format(self, record):
        color = self.COLORS.get(record.levelno, "")
        reset = Style.RESET_ALL
        timestamp = self.formatTime(record, "%H:%M:%S")
        return f"{Fore.WHITE}{timestamp}{reset} {color}{record.getMessage()}{reset}"


def setup_logging(verbose=False, log_file=None):
    """
    Configure the 'stryker' logger with colored console output.

    Args:
        verbose: If True, set log level to DEBUG. Otherwise INFO.
        log_file: Optional path to a log file for persistent logging.

    Returns:
        The configured logger.
    """
    colorama_init()

    logger = logging.getLogger("aster")
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)

    # Prevent duplicate handlers on re-init
    logger.handlers.clear()

    # Console handler (colored)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(ColoredFormatter())
    console_handler.setLevel(logging.DEBUG if verbose else logging.INFO)
    logger.addHandler(console_handler)

    # File handler (plain text, always DEBUG level)
    if log_file:
        try:
            import os
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            file_handler.setFormatter(
                logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
            )
            file_handler.setLevel(logging.DEBUG)
            logger.addHandler(file_handler)
        except Exception as e:
            logger.warning(f"⚠️  Could not set up file logging: {e}")

    return logger


def print_banner():
    """Print the startup banner."""
    banner = f"""
{Fore.CYAN}{Style.BRIGHT}
  ╔═══════════════════════════════════════════════╗
  ║           🤖  ASTER BOT  v2.0.0               ║
  ║     YouTube Live Stream Moderator Bot         ║
  ╚═══════════════════════════════════════════════╝
{Style.RESET_ALL}"""
    print(banner)
