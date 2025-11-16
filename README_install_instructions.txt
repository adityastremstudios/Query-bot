# Discord Bot Deployment Instructions

This bot is a Python-based Discord bot with:
- Q&A knowledge system (learns from your input)
- Slash commands and prefix commands
- Anti-spam and bad word filter
- Moderation and bot-manager controls

---------------------------------
1. Local Setup (On Your PC)
---------------------------------

Requirements:
- Python 3.10+ installed
- Git (optional but useful)

Steps:

1) Install dependencies:

   pip install -r requirements.txt

2) Open bot.py and make sure DISCORD_TOKEN is loaded, for example:

   import os
   DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

   Or hardcode it (not recommended for production):

   DISCORD_TOKEN = "YOUR_DISCORD_BOT_TOKEN_HERE"

3) Create a .env file (optional) and add:

   DISCORD_TOKEN=your_discord_token_here

4) Run the bot:

   python bot.py

You should see:
   Logged in as YourBotName
   Slash commands synced


---------------------------------
2. Hosting on GalaticHosting (Pterodactyl-style)
---------------------------------

1) Log into your GalaticHosting panel.

2) Create a new server:
   - Type: Python / Discord Bot
   - Choose Python 3.x

3) Upload these files to the server's file manager:
   - bot.py
   - knowledge.json (can be empty or will be created)
   - bot_config.json (optional, will be created automatically)
   - requirements.txt
   - Procfile (optional)
   - .env (optional, if you use env variables)

4) Install dependencies using the console:

   pip install -r requirements.txt

   Or:

   python3 -m pip install -r requirements.txt

5) Set startup command (if needed in panel Startup tab):

   python bot.py
   or
   python3 bot.py

6) Set environment variable for your token (preferred):

   DISCORD_TOKEN = your_discord_bot_token_here

   In bot.py, make sure you have:

   import os
   DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

7) Start the server in the panel ("Start" button).

You should see in console:

   🌍 Global slash commands synced: [...]
   ✅ Logged in as YourBotName


---------------------------------
3. Inviting the Bot (IMPORTANT)
---------------------------------

In the Discord Developer Portal:

1) Go to your application -> OAuth2 -> URL Generator
2) Under SCOPES, select:
   - bot
   - applications.commands
3) Under BOT PERMISSIONS, select at least:
   - Read Messages / View Channels
   - Send Messages
   - Manage Messages
   - Embed Links
   - Use Slash Commands
   (Plus Kick/Ban/Moderate if you use moderation commands.)
4) Copy the generated URL and open it in your browser.
5) Invite the bot to your server.

---------------------------------
4. Using the Bot
---------------------------------

Main slash commands:
/help              - Show full categorized help menu
/ask question      - Ask the Q&A system
/qa_add data       - Add Q&A (admins/managers)
/qa_list           - List all Q&A
/qa_search keyword - Search Q&A
/botaddrole        - Add a role that can manage the bot
/botadduser        - Add a specific bot manager
/botmanagers       - List bot managers
/mod ...           - Moderation commands (warn, mute, kick, ban, etc.)
/info ...          - Info commands (server, user, bot)
/rules             - Show rules embed

Prefix commands (if enabled):
!addqa, !editqa, !delqa, !listqa, !searchqa

---------------------------------
5. Notes
---------------------------------

- knowledge.json stores your Q&A data.
- bot_config.json stores who can manage the bot.
- Do NOT hardcode your token in public repos.
- Use environment variables on hosting when possible.
