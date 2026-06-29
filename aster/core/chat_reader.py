"""
chat_reader.py — Quota-free live chat reader using YouTube's internal API.

Fetches live chat messages by scraping the video page for a continuation
token, then polling YouTube's internal `youtubei/v1/live_chat/get_live_chat`
endpoint. No API key or OAuth required for reading.

Messages are normalized to the same dict format the bot already uses,
so commands/welcome/polls continue working unchanged.
"""

import re
import time
import logging
import requests

logger = logging.getLogger("aster")

# Internal API endpoint
_LIVE_CHAT_URL = "https://www.youtube.com/youtubei/v1/live_chat/get_live_chat"

# Client context sent with every request
_CLIENT_CONTEXT = {
    "client": {
        "clientName": "WEB",
        "clientVersion": "2.20240101.00.00",
    }
}


class LiveChatReader:
    """
    Reads live chat messages using YouTube's unofficial internal API.
    Zero quota usage — only uses HTTP requests, no OAuth needed.
    """

    def __init__(self, video_id):
        self.video_id = video_id
        self._continuation = None
        self._seen_ids = set()
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        })

    def connect(self):
        """
        Fetch the video page and extract the initial continuation token.
        Must be called before poll().

        Raises:
            ConnectionError: If the page cannot be fetched or token not found.
        """
        logger.info(f"🔗 Connecting to live chat (quota-free reader)...")

        try:
            url = f"https://www.youtube.com/watch?v={self.video_id}"
            resp = self._session.get(url, timeout=15)
            resp.raise_for_status()
            html = resp.text

            # Extract initial continuation token from the page HTML
            match = re.search(r'"continuation":"(.*?)"', html)
            if not match:
                raise ConnectionError(
                    "Could not find live chat continuation token.\n"
                    "Make sure the stream is live and chat is enabled."
                )

            self._continuation = match.group(1)
            logger.info("✅ Live chat reader connected (quota-free mode)")
            return True

        except requests.RequestException as e:
            raise ConnectionError(f"Failed to fetch video page: {e}")

    def poll(self):
        """
        Fetch the next batch of live chat messages.

        Returns:
            Tuple of (messages, polling_interval_seconds)
            where messages is a list of normalized message dicts.
        """
        if not self._continuation:
            logger.error("❌ No continuation token. Call connect() first.")
            return [], 5

        try:
            payload = {
                "context": _CLIENT_CONTEXT,
                "continuation": self._continuation,
            }

            resp = self._session.post(_LIVE_CHAT_URL, json=payload, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            # Parse messages
            chat_data = (
                data.get("continuationContents", {})
                .get("liveChatContinuation", {})
            )

            actions = chat_data.get("actions", [])
            messages = []

            for action in actions:
                msg = self._parse_action(action)
                if msg and msg["id"] not in self._seen_ids:
                    self._seen_ids.add(msg["id"])
                    messages.append(msg)

            # Cap the seen IDs set to prevent memory growth
            if len(self._seen_ids) > 5000:
                # Keep the most recent 2000
                self._seen_ids = set(list(self._seen_ids)[-2000:])

            # Get next continuation token
            self._update_continuation(chat_data)

            # Determine polling interval
            interval = self._get_polling_interval(chat_data)

            return messages, interval

        except requests.RequestException as e:
            logger.warning(f"⚠️  Chat reader network error: {e}")
            return [], 5
        except Exception as e:
            logger.warning(f"⚠️  Chat reader error: {e}")
            return [], 5

    def _parse_action(self, action):
        """
        Parse a single action from the internal API response.

        Returns a normalized message dict matching the format from
        the v3 API, or None if not a text message.
        """
        try:
            add_action = action.get("addChatItemAction")
            if not add_action:
                return None

            item = add_action.get("item", {})

            # Handle regular text messages
            renderer = item.get("liveChatTextMessageRenderer")
            if not renderer:
                return None

            # Extract message text (may have multiple runs)
            message_runs = renderer.get("message", {}).get("runs", [])
            message_text = "".join(
                run.get("text", run.get("emoji", {}).get("emojiId", ""))
                for run in message_runs
            )

            if not message_text:
                return None

            # Extract author info
            author_name = renderer.get("authorName", {}).get("simpleText", "Unknown")
            channel_id = renderer.get("authorExternalChannelId", "")
            msg_id = renderer.get("id", "")
            timestamp = renderer.get("timestampUsec", "")

            # Extract badges (owner, moderator, member)
            badges = renderer.get("authorBadges", [])
            is_owner = False
            is_moderator = False
            is_member = False

            for badge in badges:
                badge_renderer = badge.get("liveChatAuthorBadgeRenderer", {})
                icon_type = badge_renderer.get("icon", {}).get("iconType", "")
                if icon_type == "OWNER":
                    is_owner = True
                elif icon_type == "MODERATOR":
                    is_moderator = True
                elif icon_type == "MEMBER":
                    is_member = True

            return {
                "id": msg_id,
                "channel_id": channel_id,
                "display_name": author_name,
                "message": message_text,
                "published_at": timestamp,
                "is_owner": is_owner,
                "is_moderator": is_moderator,
                "is_member": is_member,
            }

        except Exception:
            return None

    def _update_continuation(self, chat_data):
        """Extract the next continuation token from the response."""
        continuations = chat_data.get("continuations", [])
        for cont in continuations:
            # Try invalidation continuation (real-time)
            inv = cont.get("invalidationContinuationData", {})
            if inv.get("continuation"):
                self._continuation = inv["continuation"]
                return

            # Fall back to timed continuation
            timed = cont.get("timedContinuationData", {})
            if timed.get("continuation"):
                self._continuation = timed["continuation"]
                return

        logger.warning("⚠️  No continuation token in response, stream may have ended.")

    def _get_polling_interval(self, chat_data):
        """
        Extract the polling interval from the response.
        Returns seconds (default 5 if not found).
        """
        continuations = chat_data.get("continuations", [])
        for cont in continuations:
            for key in ("invalidationContinuationData", "timedContinuationData"):
                timeout_ms = cont.get(key, {}).get("timeoutMs")
                if timeout_ms:
                    return max(timeout_ms / 1000.0, 1.0)
        return 5.0

    def close(self):
        """Clean up the HTTP session."""
        self._session.close()
