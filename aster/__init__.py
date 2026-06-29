"""
Stryker Bot — YouTube Live Stream Moderator Bot.

Usage:
    python run.py                # CLI mode
    python run.py --web          # Web dashboard (http://localhost:5000)
    python run.py --web --port 8080
    python run.py --verbose      # Verbose CLI mode
"""

import sys
import argparse

from aster.core.config import VIDEO_ID, LOG_FILE


def main():
    """Main entry point for Stryker Bot."""
    # Parse CLI arguments
    parser = argparse.ArgumentParser(description="Aster Bot — YouTube Live Moderator")
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose (DEBUG) logging",
    )
    parser.add_argument(
        "--video",
        type=str,
        default="",
        help="YouTube video ID to monitor (overrides config.json)",
    )
    parser.add_argument(
        "--web",
        action="store_true",
        help="Start the web dashboard instead of CLI mode",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=5000,
        help="Port for the web dashboard (default: 5000)",
    )
    args = parser.parse_args()

    # ── Web Dashboard Mode ───────────────────────────────────────────
    if args.web:
        from aster.web.app import run_dashboard
        run_dashboard(port=args.port, debug=args.verbose)
        return

    # ── Classic CLI Mode ─────────────────────────────────────────────
    from aster.core.auth import get_authenticated_service
    from aster.utils.logger import setup_logging, print_banner
    from aster.bot import StrykerBot

    logger = setup_logging(verbose=args.verbose, log_file=LOG_FILE)
    print_banner()

    # Step 1: Authenticate
    logger.info("🔐 Authenticating with YouTube Data API...")
    try:
        youtube = get_authenticated_service()
        logger.info("✅ Authentication successful!\n")
    except FileNotFoundError as e:
        logger.error(str(e))
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Authentication failed: {e}")
        sys.exit(1)

    # Step 2: Determine video ID (CLI arg > config.json > auto-detect)
    video_id = args.video or VIDEO_ID or ""

    # Step 3: Start the bot
    bot = StrykerBot(youtube, video_id)
    try:
        bot.start()
    except KeyboardInterrupt:
        bot.stop()
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        bot.stop()
        sys.exit(1)
