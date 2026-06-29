# Aster Bot - YouTube Live Stream Moderator

Aster Bot is a Python-powered YouTube live stream moderator bot. It monitors your live chat in real-time and automates common tasks so you can focus on your content. The project features a premium, real-time React web dashboard (Aster UI) to let you control the bot, manage custom commands, launch polls, and view live logs directly from your browser.

---

## Features

| Feature | Description |
|---------|-------------|
| **React Web Dashboard** | A premium, dark-themed user interface to control, configure, and monitor your bot live |
| **Auto-Detect Stream** | Automatically finds your active live broadcast without requiring a manual Video ID |
| **Welcome Messages** | Greets first-time chatters with a customizable welcome message |
| **Persistent Welcomes** | Remembers welcomed chatters across bot restarts via disk storage |
| **Slash Commands** | Responds to custom commands (like /discord, /specs, /socials) with predefined replies |
| **Command Aliases** | Each command supports multiple aliases (for example, /dc mapping to /discord) |
| **Command Cooldowns** | Enforces a configurable cooldown period per command to prevent chat spam |
| **Poll Creation** | Allows launching native YouTube polls directly from chat or the web panel |
| **Hot Reload** | Save commands in the dashboard or type /reload in chat to refresh commands instantly |
| **Live Log Streaming** | Server-Sent Events (SSE) console logging stream directly in the web dashboard |

---

## Prerequisites

- **Python 3.10+**
- **Node.js 18+ and npm** (for the React web interface)
- **Google Cloud Project** with the **YouTube Data API v3** enabled
- **OAuth 2.0 Client ID** (Desktop application type)

---

## Setup Guide

### 1. Clone the Repository

```bash
git clone https://github.com/shohelahmed75/youtube_bot
cd youtube_bot
```

### 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 3. Build the React Frontend

To compile the Aster UI dashboard into static files that Flask can serve:

```bash
cd aster-ui
npm install
npm run build
cd ..
```

### 4. Enable YouTube Data API v3

1. Go to the Google Cloud Console
2. Create a new project or select an existing one
3. Navigate to APIs and Services, then open the Library
4. Search for YouTube Data API v3 and click Enable

### 5. Create OAuth 2.0 Credentials

1. In Google Cloud Console, go to APIs and Services, then open Credentials
2. Click Create Credentials and select OAuth client ID
3. If prompted, configure the OAuth consent screen first:
   - User type: External
   - Fill in the required application details
   - Add scope: https://www.googleapis.com/auth/youtube
   - Add your Google account as a test user
4. In Credentials, select Desktop app as the application type
5. Click Create and download the JSON file
6. Rename the downloaded file to client_secret.json and place it in the project root directory

### 6. Configure Environment Variables

Create a .env file in the project root and fill in your details:

```env
# YouTube Data API v3
API_KEY=your-api-key-here

# OAuth 2.0
CLIENT_SECRET_FILE=client_secret.json

# Bot Settings
VIDEO_ID=                  # Leave empty to auto-detect your active stream
BOT_PREFIX=/               # Command prefix (default: /)
WELCOME_MESSAGE=Welcome to the stream, {username}!
POLL_DURATION=5

# Spam Protection
COOLDOWN_SECONDS=5         # Seconds between repeated command replies

# Data Storage
DATA_DIR=data              # Directory for persistent data (welcomed users, logs)
```

---

## Running the Application

### Running with the Web Dashboard

Start the Flask server which serves the built React web dashboard at http://127.0.0.1:5000:

```bash
python run.py --web
```

Optionally specify a custom port:

```bash
python run.py --web --port 8080
```

### Running in CLI-Only Mode

Start the bot in the terminal without launching the dashboard:

```bash
python run.py
```

Or run via the module syntax:

```bash
python -m aster
```

CLI flags:

| Flag | Description |
|------|-------------|
| --verbose / -v | Enable debug-level logging |
| --video VIDEO_ID | Override the video ID from the configuration |

### Frontend Development Server

If you are developing the React interface and want live reloading, you can start the Vite dev server alongside the Flask server.

1. Start the backend Flask API:
   ```bash
   python run.py --web
   ```
2. Start the Vite dev server:
   ```bash
   cd aster-ui
   npm run dev
   ```
3. Open http://localhost:5173 in your browser. All API requests are proxied automatically to the backend on port 5000.

---

## Project Structure

```
youtube_bot/
├── .env                          # Environment variables
├── .gitignore
├── requirements.txt
├── client_secret.json            # OAuth 2.0 credentials (user-provided)
├── commands.json                 # Command definitions
├── run.py                        # Python entry point
├── README.md
├── data/                         # Auto-created persistent storage
│   ├── welcomed_*.json           # Welcomed viewer records per stream
│   └── bot.log                   # Persistent log file
├── aster/                        # Main Python package
│   ├── __init__.py               # Main CLI and entry point functions
│   ├── __main__.py               # Python module support
│   ├── bot.py                    # Core bot loop orchestrator
│   ├── core/
│   │   ├── auth.py               # OAuth 2.0 authentication flow
│   │   ├── chat.py               # YouTube API read/write services
│   │   ├── chat_reader.py        # Quota-free chat reader
│   │   └── config.py             # Settings loader
│   ├── features/
│   │   ├── commands.py           # Command routing and cooldowns
│   │   ├── welcome.py            # Welcome tracker
│   │   └── polls.py              # Poll parsing and creation
│   │   └── __init__.py
│   ├── utils/
│   │   ├── logger.py             # Console and file logger
│   │   └── storage.py            # JSON store utilities
│   │   └── __init__.py
│   └── web/
│       ├── app.py                # Flask server endpoints
│       ├── bot_manager.py        # Lifecycle thread coordinator
│       └── __init__.py
└── aster-ui/                     # React frontend dashboard
    ├── index.html
    ├── package.json
    ├── vite.config.js            # Vite configurations (with proxy setup)
    ├── src/
    │   ├── main.jsx
    │   ├── App.jsx               # React logic and component structure
    │   └── App.css               # Custom theme styles
    │   └── index.css             # Style resets
    └── dist/                     # Compiled production bundle
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| **Quota Exceeded (HttpError 403)** | YouTube API daily limit hit. Wait 24 hours or request a limit increase. |
| **No active live broadcast found** | Make sure your channel is currently live, or set a specific VIDEO_ID in the configuration. |
| **Bot welcomes users repeatedly** | Verify that the data/ directory exists and has write permissions so welcomed records persist. |
| **Commands do not respond** | Check the cooldown setting or type /reload in chat to reload configurations. |
| **ModuleNotFoundError** | Ensure you have activated your virtual environment and run: pip install -r requirements.txt |

---

## License

This project is for personal and educational use. Please respect the YouTube Terms of Service and YouTube API Services Terms of Service.
