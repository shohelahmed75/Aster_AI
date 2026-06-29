"""
chat.py — YouTube live chat read/write operations.

Provides functions to:
  - Auto-detect the authenticated user's active live broadcast
  - Get the live chat ID from a video ID
  - Get the stream owner's channel ID
  - Fetch (poll) live chat messages
  - Send a text message to live chat
"""

import time
import logging
from googleapiclient.errors import HttpError

logger = logging.getLogger("aster")


# ─── Auto-Detection ─────────────────────────────────────────────────────────────


def get_active_broadcast(youtube, channel_id=None):
    """
    Auto-detect an active live broadcast on the given channel.

    Uses search.list with channelId + eventType=live to find
    the currently active stream. Falls back to the bot's own channel
    if no channel_id is provided.

    Args:
        youtube: Authenticated YouTube API service object.
        channel_id: YouTube channel ID to search for live streams.
                    If empty/None, detects the bot's own channel.

    Returns:
        Tuple of (video_id, title) for the active broadcast.

    Raises:
        ValueError: If no active broadcast is found.
    """
    try:
        # If no channel_id provided, detect the bot's own channel
        if not channel_id:
            ch_response = youtube.channels().list(
                part="id",
                mine=True,
            ).execute()
            ch_items = ch_response.get("items", [])
            if ch_items:
                channel_id = ch_items[0]["id"]
            else:
                raise ValueError(
                    "Could not detect your channel. "
                    "Set 'channel_id' in config.json."
                )

        logger.info(f"🔍 Searching for live stream on channel: {channel_id[:15]}...")

        # Use search.list which supports channelId + eventType
        response = youtube.search().list(
            part="id,snippet",
            channelId=channel_id,
            eventType="live",
            type="video",
            maxResults=1,
        ).execute()

        items = response.get("items", [])
        if not items:
            raise ValueError(
                f"No active live broadcast found on channel '{channel_id}'.\n"
                "Make sure the channel is currently live, or set 'video_id' in config.json."
            )

        video_id = items[0]["id"]["videoId"]
        title = items[0].get("snippet", {}).get("title", "Untitled Stream")

        logger.info(f"📡 Auto-detected live broadcast: \"{title}\"")
        logger.info(f"   Video ID: {video_id}")
        return video_id, title

    except HttpError as e:
        logger.error(f"❌ API error while detecting broadcast: {e}")
        raise


def get_stream_owner_channel(youtube, video_id):
    """
    Get the channel ID of the video owner (the streamer).

    Args:
        youtube: Authenticated YouTube API service object.
        video_id: The YouTube video ID of the live stream.

    Returns:
        The channel ID of the stream owner, or None if not found.
    """
    try:
        response = youtube.videos().list(
            part="snippet",
            id=video_id,
        ).execute()

        items = response.get("items", [])
        if items:
            channel_id = items[0].get("snippet", {}).get("channelId")
            if channel_id:
                logger.info(f"👑 Stream owner channel: {channel_id[:15]}...")
                return channel_id

    except HttpError as e:
        logger.warning(f"⚠️  Could not detect stream owner: {e}")

    return None


# ─── Live Chat Operations ────────────────────────────────────────────────────────


def get_live_chat_id(youtube, video_id):
    """
    Retrieve the active live chat ID for a given video.

    Args:
        youtube: Authenticated YouTube API service object.
        video_id: The YouTube video ID of the live stream.

    Returns:
        The activeLiveChatId string.

    Raises:
        ValueError: If the video is not a live stream or has no active chat.
    """
    try:
        response = youtube.videos().list(
            part="liveStreamingDetails",
            id=video_id,
        ).execute()

        items = response.get("items", [])
        if not items:
            raise ValueError(f"No video found with ID: {video_id}")

        live_details = items[0].get("liveStreamingDetails", {})
        chat_id = live_details.get("activeLiveChatId")

        if not chat_id:
            raise ValueError(
                f"Video '{video_id}' is not currently live or has no active chat.\n"
                f"Make sure your stream is live and chat is enabled."
            )

        logger.info(f"🔗 Connected to live chat: {chat_id[:20]}...")
        return chat_id

    except HttpError as e:
        logger.error(f"❌ API error while getting live chat ID: {e}")
        raise




def send_message(youtube, chat_id, text):
    """
    Send a text message to the live chat.

    Args:
        youtube: Authenticated YouTube API service object.
        chat_id: The live chat ID to send the message to.
        text: The message text to send.

    Returns:
        True if the message was sent successfully, False otherwise.
    """
    try:
        youtube.liveChatMessages().insert(
            part="snippet",
            body={
                "snippet": {
                    "liveChatId": chat_id,
                    "type": "textMessageEvent",
                    "textMessageDetails": {
                        "messageText": text
                    }
                }
            }
        ).execute()

        logger.info(f"💬 Sent: {text[:80]}{'...' if len(text) > 80 else ''}")
        return True

    except HttpError as e:
        if e.resp.status == 403:
            logger.warning(f"⚠️  Cannot send message (quota/permissions): {e}")
        else:
            logger.error(f"❌ Failed to send message: {e}")
        return False
