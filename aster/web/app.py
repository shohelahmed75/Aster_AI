"""
app.py — Flask web dashboard for Stryker Bot.

Provides REST API endpoints and SSE log streaming
to control the bot from a browser.
"""

import os
import json
import time
import queue
import logging
from pathlib import Path
from flask import Flask, request, jsonify, Response

from aster.web.bot_manager import BotManager

logger = logging.getLogger("aster")

# Resolve project root
_project_root = Path(__file__).resolve().parent.parent.parent

# Flask app
app = Flask(
    __name__,
    static_folder=str(_project_root / "aster-ui" / "dist"),
    static_url_path="",
)

# Singleton bot manager
manager = BotManager()


# ─── Dashboard Page ──────────────────────────────────────────────────────────────

@app.route("/")
def index():
    """Serve the dashboard HTML."""
    return app.send_static_file("index.html")


# ─── Bot Control ─────────────────────────────────────────────────────────────────

@app.route("/api/status")
def api_status():
    """Return the current bot status."""
    return jsonify(manager.status())


@app.route("/api/bot/start", methods=["POST"])
def api_bot_start():
    """Start the bot in a background thread."""
    result = manager.start()
    return jsonify(result)


@app.route("/api/bot/stop", methods=["POST"])
def api_bot_stop():
    """Stop the bot gracefully."""
    result = manager.stop()
    return jsonify(result)


# ─── Config Management ───────────────────────────────────────────────────────────

@app.route("/api/config")
def api_get_config():
    """Read config.json and return it."""
    config_path = _project_root / "config.json"
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        return jsonify(config)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/config", methods=["PUT"])
def api_set_config():
    """Update config.json with the provided data."""
    config_path = _project_root / "config.json"
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

        return jsonify({"success": True, "message": "Config saved. Restart bot to apply."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─── Commands Management ─────────────────────────────────────────────────────────

@app.route("/api/commands")
def api_get_commands():
    """Read commands.json and return it."""
    commands_path = _project_root / "commands.json"
    try:
        with open(commands_path, "r", encoding="utf-8") as f:
            commands = json.load(f)
        return jsonify(commands)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/commands", methods=["PUT"])
def api_set_commands():
    """Update commands.json with the provided data."""
    commands_path = _project_root / "commands.json"
    try:
        data = request.get_json()
        if data is None:
            return jsonify({"error": "No data provided"}), 400

        with open(commands_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        # If bot is running, hot-reload commands
        if manager._running and manager._bot:
            try:
                manager._bot.command_router.reload()
            except Exception:
                pass

        return jsonify({"success": True, "message": "Commands saved!"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ─── Polls ───────────────────────────────────────────────────────────────────────

@app.route("/api/poll", methods=["POST"])
def api_create_poll():
    """Create a live poll via the running bot."""
    if not manager._running or not manager._bot:
        return jsonify({"error": "Bot is not running. Start the bot first."}), 400

    data = request.get_json()
    question = data.get("question", "").strip()
    options = data.get("options", [])

    if not question:
        return jsonify({"error": "Question is required"}), 400
    if len(options) < 2:
        return jsonify({"error": "At least 2 options required"}), 400

    try:
        from aster.features.polls import create_poll
        chat_id = manager._bot.chat_id
        youtube = manager._bot.youtube
        create_poll(youtube, chat_id, question, options)
        return jsonify({"success": True, "message": f"Poll created: {question}"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─── Live Log Streaming (SSE) ────────────────────────────────────────────────────

@app.route("/api/logs/stream")
def api_log_stream():
    """
    Server-Sent Events endpoint for live log streaming.
    Sends existing history first, then streams new entries.
    """
    def generate():
        msg_queue = queue.Queue()

        def on_log(entry):
            msg_queue.put(entry)

        # Send history first
        history = manager.log_handler.get_history()
        for entry in history:
            data = json.dumps(entry)
            yield f"data: {data}\n\n"

        # Listen for new entries
        manager.log_handler.add_listener(on_log)
        try:
            while True:
                try:
                    entry = msg_queue.get(timeout=30)
                    data = json.dumps(entry)
                    yield f"data: {data}\n\n"
                except queue.Empty:
                    # Send keepalive comment
                    yield ": keepalive\n\n"
        except GeneratorExit:
            pass
        finally:
            manager.log_handler.remove_listener(on_log)

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ─── Entry Point ─────────────────────────────────────────────────────────────────

def run_dashboard(host="127.0.0.1", port=5000, debug=False):
    """Start the Flask dashboard server."""
    from aster.utils.logger import setup_logging, print_banner

    setup_logging(verbose=debug)
    print_banner()
    logger.info(f"🌐 Starting web dashboard at http://{host}:{port}")
    logger.info("   Open your browser to control the bot.\n")

    app.run(host=host, port=port, debug=debug, use_reloader=False, threaded=True)
