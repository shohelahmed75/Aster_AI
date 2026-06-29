"""
polls.py — YouTube live chat poll creation.

Provides functions to parse poll commands from chat and
create native YouTube polls via the API.
"""

import re
import logging
from googleapiclient.errors import HttpError

logger = logging.getLogger("aster")


def parse_poll_command(text):
    """
    Parse a /poll command from chat text.

    Expected format:
        /poll "Question?" "Option 1" "Option 2" "Option 3"

    Args:
        text: The raw chat message text.

    Returns:
        Tuple of (question, [options]) if valid, or (None, None) if invalid.
    """
    # Extract all quoted strings from the command
    parts = re.findall(r'"([^"]+)"', text)

    if len(parts) < 3:
        # Need at least a question + 2 options
        return None, None

    question = parts[0]
    options = parts[1:]

    # YouTube allows 2-4 options
    if len(options) < 2:
        logger.warning("⚠️  Poll needs at least 2 options.")
        return None, None
    if len(options) > 4:
        logger.warning("⚠️  Poll can have at most 4 options. Truncating to 4.")
        options = options[:4]

    return question, options


def create_poll(youtube, chat_id, question, options):
    """
    Create a native YouTube poll in the live chat.

    Args:
        youtube: Authenticated YouTube API service object.
        chat_id: The live chat ID.
        question: The poll question.
        options: List of option strings (2-4 items).

    Returns:
        True if the poll was created successfully, False otherwise.
    """
    try:
        poll_options = [{"optionText": opt} for opt in options]

        youtube.liveChatMessages().insert(
            part="snippet",
            body={
                "snippet": {
                    "liveChatId": chat_id,
                    "type": "pollEvent",
                    "pollDetails": {
                        "metadata": {
                            "options": {
                                "questionText": question,
                            }
                        },
                        "status": "active",
                    },
                    "textMessageDetails": {
                        "messageText": question,
                    }
                }
            }
        ).execute()

        logger.info(f"📊 Poll created: '{question}' with {len(options)} options")
        return True

    except HttpError as e:
        if e.resp.status == 403:
            logger.warning(
                "⚠️  Cannot create poll. Only the stream owner can create polls."
            )
        else:
            logger.error(f"❌ Failed to create poll: {e}")
        return False
